"""
core/ai_client.py
=================
Production-Grade Unified AI Client & Gateway for AIAutoShorts.
Transparently orchestrates LLM inference across multiple providers:
  1. Primary: Groq API (High throughput, ultra-fast inference, circuit-breaker key pooling)
  2. Fallback: Google Gemini API (Multi-model cascade & vision/multimodal engine)
  3. Optional Fallback: OpenRouter (Deep open-source redundancy)

Hardened with:
  - Step 1: Async Non-Blocking I/O & Persistent HTTP Connection Pooling (httpx)
  - Step 2: Native Structured Outputs & Robust Pydantic / JSON Self-Repair
  - Step 3: Key Circuit Breaker with Rate-Limit (429) Cooldown Tracking
  - Step 4: Structured Exponential Backoff with Jitter for Transient Errors
"""

import os
import re
import json
import time
import random
import hashlib
import asyncio
import threading
import contextlib
from contextvars import ContextVar
from typing import Optional, Dict, Any, List, Union, Type, TypeVar, Tuple

import httpx
from pydantic import BaseModel, ValidationError

from config.settings import (
    GROQ_API_KEYS, GROQ_MODEL,
    GEMINI_API_KEYS, GEMINI_MODEL,
    OPENROUTER_API_KEYS, OPENROUTER_MODEL,
    NVIDIA_API_KEY
)

T = TypeVar("T", bound=BaseModel)

_GROQ_MODEL_CASCADE = [
    GROQ_MODEL,
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "groq/compound",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

_GEMINI_MODEL_CASCADE = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-flash-lite-latest",
]

_OPENROUTER_MODEL_CASCADE = [
    "google/gemma-4-26b-a4b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free"
]

_groq_key_idx = 0
_openrouter_key_idx = 0

_current_context: ContextVar[Optional[Any]] = ContextVar("_current_context", default=None)


# ─── Context Scoping ───────────────────────────────────────────────────────────

def get_current_context() -> Optional[Any]:
    """Returns the currently active ChannelContext in this execution context, if any."""
    return _current_context.get()


def set_current_context(ctx: Optional[Any]):
    """Sets the active ChannelContext for BYOK key resolution."""
    return _current_context.set(ctx)


@contextlib.contextmanager
def scoped_context(ctx: Optional[Any]):
    """Context manager scoping a ChannelContext to the active block."""
    token = _current_context.set(ctx)
    try:
        yield ctx
    finally:
        _current_context.reset(token)


def _resolve_keys(provider: str, explicit_keys: Optional[List[str]] = None) -> List[str]:
    """
    Resolves provider API keys with multi-tenant precedence:
      1. Explicit keys passed to function call
      2. Scoped BYOK keys from active ChannelContext
      3. Global system environment keys
    """
    if explicit_keys:
        return [k for k in explicit_keys if k and isinstance(k, str) and len(k.strip()) > 3]

    ctx = get_current_context()
    if ctx and hasattr(ctx, "get_provider_keys"):
        scoped = ctx.get_provider_keys(provider)
        if scoped:
            return scoped

    if provider == "groq":
        return GROQ_API_KEYS or []
    elif provider == "gemini":
        return GEMINI_API_KEYS or []
    elif provider == "openrouter":
        return OPENROUTER_API_KEYS or []
    return []


# ─── Step 3: Circuit Breaker & Key Cooldown Tracking ──────────────────────────

class KeyCircuitBreaker:
    """
    Thread-safe circuit breaker tracking rate-limit cooldowns and health per key.
    Prevents burning round-trips on keys that returned 429/ResourceExhausted.
    """
    def __init__(self, default_cooldown: float = 60.0):
        self._lock = threading.Lock()
        self._cooldown_until: Dict[str, float] = {}
        self._default_cooldown = default_cooldown

    def _hash(self, key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def record_rate_limit(self, key: str, cooldown_seconds: Optional[float] = None) -> None:
        cooldown = cooldown_seconds if cooldown_seconds is not None else self._default_cooldown
        h = self._hash(key)
        until = time.time() + cooldown
        with self._lock:
            self._cooldown_until[h] = max(self._cooldown_until.get(h, 0.0), until)

    def record_success(self, key: str) -> None:
        h = self._hash(key)
        with self._lock:
            self._cooldown_until.pop(h, None)

    def is_available(self, key: str) -> bool:
        h = self._hash(key)
        with self._lock:
            expiry = self._cooldown_until.get(h, 0.0)
            return time.time() >= expiry

    def filter_keys(self, keys: List[str]) -> List[str]:
        """Returns keys not in cooldown. If all are in cooldown, returns key expiring earliest."""
        if not keys:
            return []
        now = time.time()
        available = []
        earliest_key = keys[0]
        earliest_expiry = float("inf")

        with self._lock:
            for k in keys:
                h = self._hash(k)
                exp = self._cooldown_until.get(h, 0.0)
                if now >= exp:
                    available.append(k)
                elif exp < earliest_expiry:
                    earliest_expiry = exp
                    earliest_key = k

        return available if available else [earliest_key]

    def reset(self) -> None:
        with self._lock:
            self._cooldown_until.clear()


_circuit_breaker = KeyCircuitBreaker(default_cooldown=60.0)


def get_circuit_breaker() -> KeyCircuitBreaker:
    return _circuit_breaker


# ─── Step 1: Persistent Connection Pooling (httpx) ────────────────────────────

_sync_http_client: Optional[httpx.Client] = None
_async_http_client: Optional[httpx.AsyncClient] = None
_client_lock = threading.Lock()


def get_sync_http_client() -> httpx.Client:
    """Returns singleton sync httpx.Client with connection pooling and keepalive."""
    global _sync_http_client
    if _sync_http_client is None or _sync_http_client.is_closed:
        with _client_lock:
            if _sync_http_client is None or _sync_http_client.is_closed:
                _sync_http_client = httpx.Client(
                    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
                    timeout=httpx.Timeout(connect=8.0, read=30.0, write=10.0, pool=10.0)
                )
    return _sync_http_client


async def get_async_http_client() -> httpx.AsyncClient:
    """Returns singleton async httpx.AsyncClient with connection pooling and keepalive."""
    global _async_http_client
    if _async_http_client is None or _async_http_client.is_closed:
        _async_http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            timeout=httpx.Timeout(connect=8.0, read=30.0, write=10.0, pool=10.0)
        )
    return _async_http_client


# ─── Step 4: Transient Error Detection & Backoff Helpers ───────────────────────

def _is_quota_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(term in msg for term in [
        "429", "rate_limit", "quota", "resource_exhausted", "limit reached", "tokens per day"
    ])


def _is_transient_error(e: Exception) -> bool:
    """Returns True if exception is network timeout, connection reset, or 5xx server error."""
    if isinstance(e, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError)):
        return True
    msg = str(e).lower()
    return any(term in msg for term in [
        "500", "502", "503", "504", "server error", "connection reset", "connection refused", "broken pipe"
    ])


def _calc_backoff(attempt: int, base: float = 0.4, max_delay: float = 3.0) -> float:
    """Calculates exponential backoff with full jitter to avoid thundering herds."""
    exp = min(max_delay, base * (2 ** attempt))
    return random.uniform(0.5 * exp, exp)


# ─── Step 2: Native Structured Outputs & Robust Parsing ───────────────────────

def _repair_json_string(raw: str) -> str:
    """Multi-stage JSON repair: strips markdown, unescaped newlines, comments, trailing commas."""
    text = raw.strip("\ufeff \t\n\r")
    # Strip markdown fence markers
    text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text, flags=re.MULTILINE)

    # Strip single-line comments // ... and multi-line comments /* ... */
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    # Find boundaries of outer JSON structure
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    first_bracket = text.find('[')
    last_bracket = text.rfind(']')

    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        if last_brace != -1 and last_brace > first_brace:
            text = text[first_brace:last_brace + 1]
    elif first_bracket != -1:
        if last_bracket != -1 and last_bracket > first_bracket:
            text = text[first_bracket:last_bracket + 1]

    # Fix hallucinated key quotes: "key:" "val" -> "key": "val"
    text = re.sub(r'"([^"]+):"\s*"', r'"\1": "', text)

    # Fix trailing commas before closing braces/brackets
    text = re.sub(r",\s*([\]}])", r"\1", text)

    return text


def clean_json_output(
    raw: str,
    schema: Optional[Type[T]] = None
) -> Union[dict, list, T]:
    """
    Extracts, repairs, and parses JSON object from LLM response safely.
    If schema (Pydantic BaseModel) is provided, validates and returns schema instance.
    """
    if not raw:
        raise ValueError("[AIClient] LLM returned empty or None content.")

    repaired = _repair_json_string(raw)

    parsed = None
    try:
        parsed = json.loads(repaired)
    except json.JSONDecodeError:
        # Secondary fallback: clean unescaped newlines inside strings
        try:
            cleaned = re.sub(r'(?<!\\)\n', ' ', repaired)
            cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)
            parsed = json.loads(cleaned)
        except Exception as e:
            raise ValueError(f"[AIClient] Failed to parse JSON from LLM: {e}. Raw (snippet): {raw[:250]}")

    if schema is not None:
        try:
            return schema.model_validate(parsed)
        except ValidationError as ve:
            raise ValueError(f"[AIClient] JSON output failed Pydantic schema validation: {ve}")

    return parsed


# ─── Provider Implementations (Sync & Async) ──────────────────────────────────

# ── Groq API
def _call_groq(
    prompt: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.85,
    keys: Optional[List[str]] = None
) -> str:
    global _groq_key_idx
    all_keys = _resolve_keys("groq", keys)
    if not all_keys:
        raise RuntimeError("No Groq keys configured.")

    active_keys = _circuit_breaker.filter_keys(all_keys)
    num_keys = len(active_keys)
    models = [m for m in _GROQ_MODEL_CASCADE if m]
    client = get_sync_http_client()

    last_error = None
    for model in models:
        for offset in range(num_keys):
            current_idx = (_groq_key_idx + offset) % num_keys
            api_key = active_keys[current_idx]

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": 4096
            }
            if response_format:
                payload["response_format"] = response_format

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            # Retry loop for transient 5xx/network errors on this key
            for attempt in range(2):
                try:
                    res = client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    if res.status_code == 200:
                        _circuit_breaker.record_success(api_key)
                        _groq_key_idx = (current_idx + 1) % num_keys
                        data = res.json()
                        return data["choices"][0]["message"]["content"]

                    if res.status_code == 429:
                        _circuit_breaker.record_rate_limit(api_key)
                        raise RuntimeError(f"HTTP 429: {res.text}")

                    if res.status_code == 401:
                        raise RuntimeError(f"HTTP 401 Unauthorized: {res.text}")

                    if res.status_code >= 500 and attempt == 0:
                        time.sleep(_calc_backoff(attempt))
                        continue

                    raise RuntimeError(f"HTTP {res.status_code}: {res.text}")

                except Exception as ex:
                    last_error = ex
                    if _is_quota_error(ex):
                        _circuit_breaker.record_rate_limit(api_key)
                        break
                    if "401" in str(ex):
                        break
                    if _is_transient_error(ex) and attempt == 0:
                        time.sleep(_calc_backoff(attempt))
                        continue
                    break

    raise RuntimeError(f"All Groq models and keys exhausted: {last_error}")


async def _acall_groq(
    prompt: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.85,
    keys: Optional[List[str]] = None
) -> str:
    global _groq_key_idx
    all_keys = _resolve_keys("groq", keys)
    if not all_keys:
        raise RuntimeError("No Groq keys configured.")

    active_keys = _circuit_breaker.filter_keys(all_keys)
    num_keys = len(active_keys)
    models = [m for m in _GROQ_MODEL_CASCADE if m]
    client = await get_async_http_client()

    last_error = None
    for model in models:
        for offset in range(num_keys):
            current_idx = (_groq_key_idx + offset) % num_keys
            api_key = active_keys[current_idx]

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": 4096
            }
            if response_format:
                payload["response_format"] = response_format

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            for attempt in range(2):
                try:
                    res = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    if res.status_code == 200:
                        _circuit_breaker.record_success(api_key)
                        _groq_key_idx = (current_idx + 1) % num_keys
                        data = res.json()
                        return data["choices"][0]["message"]["content"]

                    if res.status_code == 429:
                        _circuit_breaker.record_rate_limit(api_key)
                        raise RuntimeError(f"HTTP 429: {res.text}")

                    if res.status_code == 401:
                        raise RuntimeError(f"HTTP 401 Unauthorized: {res.text}")

                    if res.status_code >= 500 and attempt == 0:
                        await asyncio.sleep(_calc_backoff(attempt))
                        continue

                    raise RuntimeError(f"HTTP {res.status_code}: {res.text}")

                except Exception as ex:
                    last_error = ex
                    if _is_quota_error(ex):
                        _circuit_breaker.record_rate_limit(api_key)
                        break
                    if "401" in str(ex):
                        break
                    if _is_transient_error(ex) and attempt == 0:
                        await asyncio.sleep(_calc_backoff(attempt))
                        continue
                    break

    raise RuntimeError(f"All Groq models and keys exhausted: {last_error}")


# ── Google Gemini API
def _call_gemini(
    prompt: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.85,
    keys: Optional[List[str]] = None
) -> str:
    all_keys = _resolve_keys("gemini", keys)
    if not all_keys:
        raise RuntimeError("No Gemini API keys configured.")

    active_keys = _circuit_breaker.filter_keys(all_keys)
    from google import genai
    models_to_try = [GEMINI_MODEL] + [m for m in _GEMINI_MODEL_CASCADE if m != GEMINI_MODEL]
    last_error = None

    for model in models_to_try:
        for i, api_key in enumerate(active_keys):
            try:
                client = genai.Client(api_key=api_key, http_options={'timeout': 20000})
                config_kwargs = {
                    "temperature": temperature,
                    "automatic_function_calling": genai.types.AutomaticFunctionCallingConfig(disable=True)
                }
                if response_format and response_format.get("type") == "json_object":
                    config_kwargs["response_mime_type"] = "application/json"

                config = genai.types.GenerateContentConfig(**config_kwargs)
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    _circuit_breaker.record_success(api_key)
                    return response.text
            except Exception as ex:
                last_error = ex
                if _is_quota_error(ex):
                    _circuit_breaker.record_rate_limit(api_key)
                err_str = str(ex).lower()
                if "404" in err_str:
                    break
                time.sleep(0.3)
                continue

    raise RuntimeError(f"All Gemini models and keys exhausted: {last_error}")


async def _acall_gemini(
    prompt: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.85,
    keys: Optional[List[str]] = None
) -> str:
    all_keys = _resolve_keys("gemini", keys)
    if not all_keys:
        raise RuntimeError("No Gemini API keys configured.")

    active_keys = _circuit_breaker.filter_keys(all_keys)
    from google import genai
    models_to_try = [GEMINI_MODEL] + [m for m in _GEMINI_MODEL_CASCADE if m != GEMINI_MODEL]
    last_error = None

    for model in models_to_try:
        for i, api_key in enumerate(active_keys):
            try:
                client = genai.Client(api_key=api_key, http_options={'timeout': 20000})
                config_kwargs = {
                    "temperature": temperature,
                    "automatic_function_calling": genai.types.AutomaticFunctionCallingConfig(disable=True)
                }
                if response_format and response_format.get("type") == "json_object":
                    config_kwargs["response_mime_type"] = "application/json"

                config = genai.types.GenerateContentConfig(**config_kwargs)
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    _circuit_breaker.record_success(api_key)
                    return response.text
            except Exception as ex:
                last_error = ex
                if _is_quota_error(ex):
                    _circuit_breaker.record_rate_limit(api_key)
                err_str = str(ex).lower()
                if "404" in err_str:
                    break
                await asyncio.sleep(0.3)
                continue

    raise RuntimeError(f"All Gemini models and keys exhausted: {last_error}")


# ── OpenRouter API
def _call_openrouter(
    prompt: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.85,
    keys: Optional[List[str]] = None
) -> str:
    global _openrouter_key_idx
    all_keys = _resolve_keys("openrouter", keys)
    if not all_keys:
        raise RuntimeError("No OpenRouter API keys configured.")

    active_keys = _circuit_breaker.filter_keys(all_keys)
    num_keys = len(active_keys)
    models_to_try = [OPENROUTER_MODEL] + [m for m in _OPENROUTER_MODEL_CASCADE if m != OPENROUTER_MODEL]
    client = get_sync_http_client()
    last_error = None

    for model in models_to_try:
        for offset in range(num_keys):
            current_idx = (_openrouter_key_idx + offset) % num_keys
            api_key = active_keys[current_idx]
            strict_prompt = prompt
            if response_format and response_format.get("type") == "json_object":
                strict_prompt = "CRITICAL: Output ONLY valid JSON without markdown wrapping.\n\n" + prompt

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": strict_prompt}],
                "temperature": temperature,
                "max_tokens": 4096
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            try:
                res = client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"].get("content")
                    if content:
                        _circuit_breaker.record_success(api_key)
                        _openrouter_key_idx = (current_idx + 1) % num_keys
                        return content
                if res.status_code == 429:
                    _circuit_breaker.record_rate_limit(api_key)
            except Exception as ex:
                last_error = ex
                if _is_quota_error(ex):
                    _circuit_breaker.record_rate_limit(api_key)
                continue

    raise RuntimeError(f"All OpenRouter models exhausted: {last_error}")


async def _acall_openrouter(
    prompt: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.85,
    keys: Optional[List[str]] = None
) -> str:
    global _openrouter_key_idx
    all_keys = _resolve_keys("openrouter", keys)
    if not all_keys:
        raise RuntimeError("No OpenRouter API keys configured.")

    active_keys = _circuit_breaker.filter_keys(all_keys)
    num_keys = len(active_keys)
    models_to_try = [OPENROUTER_MODEL] + [m for m in _OPENROUTER_MODEL_CASCADE if m != OPENROUTER_MODEL]
    client = await get_async_http_client()
    last_error = None

    for model in models_to_try:
        for offset in range(num_keys):
            current_idx = (_openrouter_key_idx + offset) % num_keys
            api_key = active_keys[current_idx]
            strict_prompt = prompt
            if response_format and response_format.get("type") == "json_object":
                strict_prompt = "CRITICAL: Output ONLY valid JSON without markdown wrapping.\n\n" + prompt

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": strict_prompt}],
                "temperature": temperature,
                "max_tokens": 4096
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            try:
                res = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"].get("content")
                    if content:
                        _circuit_breaker.record_success(api_key)
                        _openrouter_key_idx = (current_idx + 1) % num_keys
                        return content
                if res.status_code == 429:
                    _circuit_breaker.record_rate_limit(api_key)
            except Exception as ex:
                last_error = ex
                if _is_quota_error(ex):
                    _circuit_breaker.record_rate_limit(api_key)
                continue

    raise RuntimeError(f"All OpenRouter models exhausted: {last_error}")


# ─── Public Unified LLM Invocation (Sync & Async) ─────────────────────────────

def _generate_core(
    prompt: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.85,
    use_gemini_fallback: bool = True,
    custom_keys: Optional[Dict[str, List[str]]] = None
) -> str:
    groq_keys = custom_keys.get("groq") if custom_keys else None
    gemini_keys = custom_keys.get("gemini") if custom_keys else None
    openrouter_keys = custom_keys.get("openrouter") if custom_keys else None

    # 1. Primary: Groq
    active_groq = _resolve_keys("groq", groq_keys)
    if active_groq:
        try:
            return _call_groq(prompt, response_format=response_format, temperature=temperature, keys=active_groq)
        except Exception as e:
            print(f"[AIClient] Groq error ({e}) — attempting Gemini fallback...", flush=True)

    # 2. Fallback: Gemini
    active_gemini = _resolve_keys("gemini", gemini_keys)
    if use_gemini_fallback and active_gemini:
        try:
            return _call_gemini(prompt, response_format=response_format, temperature=temperature, keys=active_gemini)
        except Exception as e:
            print(f"[AIClient] Gemini error ({e}) — attempting OpenRouter fallback...", flush=True)

    # 3. Fallback: OpenRouter
    active_openrouter = _resolve_keys("openrouter", openrouter_keys)
    if active_openrouter:
        try:
            return _call_openrouter(prompt, response_format=response_format, temperature=temperature, keys=active_openrouter)
        except Exception as e:
            print(f"[AIClient] OpenRouter error ({e})", flush=True)

    raise RuntimeError("All configured AI providers (Groq, Gemini, OpenRouter) failed to complete the request.")


async def _agenerate_core(
    prompt: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.85,
    use_gemini_fallback: bool = True,
    custom_keys: Optional[Dict[str, List[str]]] = None
) -> str:
    groq_keys = custom_keys.get("groq") if custom_keys else None
    gemini_keys = custom_keys.get("gemini") if custom_keys else None
    openrouter_keys = custom_keys.get("openrouter") if custom_keys else None

    # 1. Primary: Groq
    active_groq = _resolve_keys("groq", groq_keys)
    if active_groq:
        try:
            return await _acall_groq(prompt, response_format=response_format, temperature=temperature, keys=active_groq)
        except Exception as e:
            print(f"[AIClient] Groq error ({e}) — attempting Gemini fallback...", flush=True)

    # 2. Fallback: Gemini
    active_gemini = _resolve_keys("gemini", gemini_keys)
    if use_gemini_fallback and active_gemini:
        try:
            return await _acall_gemini(prompt, response_format=response_format, temperature=temperature, keys=active_gemini)
        except Exception as e:
            print(f"[AIClient] Gemini error ({e}) — attempting OpenRouter fallback...", flush=True)

    # 3. Fallback: OpenRouter
    active_openrouter = _resolve_keys("openrouter", openrouter_keys)
    if active_openrouter:
        try:
            return await _acall_openrouter(prompt, response_format=response_format, temperature=temperature, keys=active_openrouter)
        except Exception as e:
            print(f"[AIClient] OpenRouter error ({e})", flush=True)

    raise RuntimeError("All configured AI providers (Groq, Gemini, OpenRouter) failed to complete the request.")


def generate_with_rotation(
    prompt: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.85,
    use_gemini_fallback: bool = True,
    custom_keys: Optional[Dict[str, List[str]]] = None,
    ctx: Optional[Any] = None
) -> str:
    """
    Synchronous Unified public LLM caller. Attempts Groq first, then Gemini, then OpenRouter.
    Supports user BYOK keys passed via custom_keys, ctx, or active contextvar.
    """
    if ctx is not None:
        with scoped_context(ctx):
            return _generate_core(prompt, response_format, temperature, use_gemini_fallback, custom_keys)
    return _generate_core(prompt, response_format, temperature, use_gemini_fallback, custom_keys)


async def agenerate_with_rotation(
    prompt: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.85,
    use_gemini_fallback: bool = True,
    custom_keys: Optional[Dict[str, List[str]]] = None,
    ctx: Optional[Any] = None
) -> str:
    """
    Asynchronous Unified public LLM caller. Attempts Groq first, then Gemini, then OpenRouter.
    Supports user BYOK keys passed via custom_keys, ctx, or active contextvar.
    """
    if ctx is not None:
        with scoped_context(ctx):
            return await _agenerate_core(prompt, response_format, temperature, use_gemini_fallback, custom_keys)
    return await _agenerate_core(prompt, response_format, temperature, use_gemini_fallback, custom_keys)


def generate_with_gemini(prompt: str, keys: Optional[List[str]] = None, ctx: Optional[Any] = None) -> str:
    """Synchronous direct Gemini caller used for video review or large visual tokens."""
    if ctx is not None:
        with scoped_context(ctx):
            return _call_gemini(prompt, keys=keys)
    return _call_gemini(prompt, keys=keys)


async def agenerate_with_gemini(prompt: str, keys: Optional[List[str]] = None, ctx: Optional[Any] = None) -> str:
    """Asynchronous direct Gemini caller used for video review or large visual tokens."""
    if ctx is not None:
        with scoped_context(ctx):
            return await _acall_gemini(prompt, keys=keys)
    return await _acall_gemini(prompt, keys=keys)


__all__ = [
    "clean_json_output",
    "generate_with_rotation",
    "agenerate_with_rotation",
    "generate_with_gemini",
    "agenerate_with_gemini",
    "get_current_context",
    "set_current_context",
    "scoped_context",
    "KeyCircuitBreaker",
    "get_circuit_breaker",
    "get_sync_http_client",
    "get_async_http_client",
]
