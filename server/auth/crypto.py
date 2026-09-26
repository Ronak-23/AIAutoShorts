"""
server/auth/crypto.py
=====================
AES-256-GCM authenticated encryption engine for user BYOK credentials,
and preflight validation checkers for AI & stock media providers.
"""

import os
import json
import base64
import hashlib
import requests
from typing import Dict, Any, List, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config.settings import JWT_SECRET_KEY
from core.db.repository import get_raw_user_api_keys

# Master encryption key derived from environment
_ENCRYPTION_MASTER_KEY = os.getenv("ENCRYPTION_MASTER_KEY", JWT_SECRET_KEY)


def _get_cipher() -> AESGCM:
    """Derives a deterministic 256-bit key from the master secret using SHA-256."""
    key_32 = hashlib.sha256(_ENCRYPTION_MASTER_KEY.encode("utf-8")).digest()
    return AESGCM(key_32)


def make_key_preview(raw_key: str) -> str:
    """Generates a safe preview string (e.g. 'gsk_12...9a12') without leaking the secret."""
    cleaned = raw_key.strip()
    if len(cleaned) <= 8:
        return "..." + cleaned[-3:]
    return f"{cleaned[:5]}...{cleaned[-4:]}"


def encrypt_api_key(raw_key: str) -> Dict[str, Any]:
    """
    Encrypts an API key using AES-256-GCM.
    Returns:
        {
            'encrypted_key': bytes,
            'nonce': bytes (12 bytes),
            'tag': bytes (16 bytes),
            'key_preview': str
        }
    """
    cleaned = raw_key.strip()
    if not cleaned:
        raise ValueError("Cannot encrypt an empty API key.")

    cipher = _get_cipher()
    nonce = os.urandom(12)  # 96-bit standard GCM nonce
    # AESGCM encrypt produces ciphertext + 16-byte tag appended at the end
    ciphertext_with_tag = cipher.encrypt(nonce, cleaned.encode("utf-8"), None)
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]

    return {
        "encrypted_key": ciphertext,
        "nonce": nonce,
        "tag": tag,
        "key_preview": make_key_preview(cleaned)
    }


def decrypt_api_key(encrypted_key: bytes, nonce: bytes, tag: bytes) -> str:
    """Decrypts and verifies an AES-256-GCM encrypted key."""
    cipher = _get_cipher()
    full_payload = encrypted_key + tag
    decrypted_bytes = cipher.decrypt(nonce, full_payload, None)
    return decrypted_bytes.decode("utf-8")


def get_user_decrypted_keys(user_id: str, provider: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Loads and decrypts all active API keys for a user, grouped by provider.
    Returns:
        {'groq': ['gsk_...'], 'gemini': ['AIzaSy...'], 'pexels': ['...']}
    """
    raw_keys = get_raw_user_api_keys(user_id=user_id, provider=provider)
    grouped: Dict[str, List[str]] = {}

    for k in raw_keys:
        p = k["provider"]
        try:
            plain = decrypt_api_key(k["encrypted_key"], k["nonce"], k["tag"])
            if plain:
                grouped.setdefault(p, []).append(plain)
        except Exception as e:
            print(f"[Crypto] Failed to decrypt key id={k.get('id')}: {e}")

    return grouped


def validate_provider_key(provider: str, key: str) -> Tuple[bool, str]:
    """
    Lightweight preflight check against provider API endpoints to ensure key validity and quota.
    Returns:
        (is_valid: bool, error_message: str)
    """
    prov = provider.lower().strip()
    k = key.strip()

    if not k:
        return False, "API key cannot be blank."

    try:
        if prov == "groq":
            res = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {k}"},
                timeout=6
            )
            if res.status_code == 200:
                return True, "Groq API key verified successfully."
            elif res.status_code == 401:
                return False, "Invalid Groq API key: Unauthorized."
            else:
                return False, f"Groq verification returned status {res.status_code}."

        elif prov == "gemini":
            from google import genai
            client = genai.Client(api_key=k)
            # Fetch 1 model to verify credentials
            models = list(client.models.list(config={"page_size": 1}))
            if models is not None:
                return True, "Gemini API key verified successfully."
            return False, "Gemini verification did not return models."

        elif prov == "openrouter":
            res = requests.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {k}"},
                timeout=6
            )
            if res.status_code == 200:
                return True, "OpenRouter API key verified successfully."
            elif res.status_code == 401:
                return False, "Invalid OpenRouter API key: Unauthorized."
            else:
                return False, f"OpenRouter verification returned status {res.status_code}."

        elif prov == "pexels":
            res = requests.get(
                "https://api.pexels.com/v1/curated?per_page=1",
                headers={"Authorization": k},
                timeout=6
            )
            if res.status_code == 200:
                return True, "Pexels API key verified successfully."
            elif res.status_code in (401, 403):
                return False, "Invalid Pexels API key: Unauthorized."
            else:
                return False, f"Pexels verification returned status {res.status_code}."

        elif prov == "elevenlabs":
            res = requests.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": k},
                timeout=6
            )
            if res.status_code == 200:
                return True, "ElevenLabs API key verified successfully."
            return False, "Invalid ElevenLabs API key."

        else:
            return False, f"Unsupported provider '{provider}'."

    except Exception as e:
        return False, f"Verification failed: {str(e)}"


def encrypt_token_dict(token_data: Dict[str, Any]) -> str:
    """
    Encrypts an OAuth token dictionary using AES-256-GCM.
    Returns a URL-safe base64 string containing: nonce (12B) + ciphertext + tag (16B).
    """
    if not token_data:
        raise ValueError("Cannot encrypt empty token data.")
    raw_str = json.dumps(token_data)
    cipher = _get_cipher()
    nonce = os.urandom(12)
    ciphertext_with_tag = cipher.encrypt(nonce, raw_str.encode("utf-8"), None)
    combined = nonce + ciphertext_with_tag
    return base64.urlsafe_b64encode(combined).decode("ascii")


def decrypt_token_dict(encrypted_str: str) -> Dict[str, Any]:
    """
    Decrypts an AES-256-GCM encrypted token string back into a dictionary.
    """
    if not encrypted_str:
        return {}
    try:
        raw_combined = base64.urlsafe_b64decode(encrypted_str.encode("ascii"))
        if len(raw_combined) < 28:
            return {}
        nonce = raw_combined[:12]
        ciphertext_with_tag = raw_combined[12:]
        cipher = _get_cipher()
        decrypted_bytes = cipher.decrypt(nonce, ciphertext_with_tag, None)
        return json.loads(decrypted_bytes.decode("utf-8"))
    except Exception as e:
        print(f"[Crypto] Failed to decrypt token dict: {e}")
        return {}
