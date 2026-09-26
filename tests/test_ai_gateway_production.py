"""
tests/test_ai_gateway_production.py
===================================
Tests for Production-Grade LLM Gateway capabilities:
  1. Circuit Breaker rate-limit (429) cooldown tracking and key filtering
  2. Robust JSON extraction & multi-stage self-repair in clean_json_output
  3. Pydantic schema structured validation in clean_json_output
  4. Transient error detection and jittered exponential backoff
  5. Persistent HTTP connection pooling (httpx)
  6. Async LLM calling (agenerate_with_rotation)
"""

import os
import sys
import json
import time
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Optional
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_client import (
    KeyCircuitBreaker,
    clean_json_output,
    get_sync_http_client,
    get_async_http_client,
    _calc_backoff,
    _is_transient_error,
    _is_quota_error,
    generate_with_rotation,
    agenerate_with_rotation,
)


class ScriptTestSchema(BaseModel):
    title: str = Field(..., min_length=3)
    duration: int
    scenes: List[str]


class TestAIGatewayProduction(unittest.TestCase):

    # ── 1. Circuit Breaker & Key Cooldown ─────────────────────────────────────
    def test_01_circuit_breaker_cooldown(self):
        cb = KeyCircuitBreaker(default_cooldown=2.0)
        key_a = "gsk_key_alpha_111"
        key_b = "gsk_key_beta_222"

        self.assertTrue(cb.is_available(key_a))
        self.assertTrue(cb.is_available(key_b))

        # Key A hits rate limit (429)
        cb.record_rate_limit(key_a, cooldown_seconds=2.0)

        # Key A is in cooldown, Key B is available
        self.assertFalse(cb.is_available(key_a))
        self.assertTrue(cb.is_available(key_b))

        # Filter returns only healthy key B
        filtered = cb.filter_keys([key_a, key_b])
        self.assertEqual(filtered, [key_b])

        # Key A gets restored manually or via record_success
        cb.record_success(key_a)
        self.assertTrue(cb.is_available(key_a))
        self.assertEqual(len(cb.filter_keys([key_a, key_b])), 2)

    def test_02_circuit_breaker_all_exhausted_fallback(self):
        cb = KeyCircuitBreaker(default_cooldown=5.0)
        key_a = "gsk_key_1"
        key_b = "gsk_key_2"

        # Both keys hit 429
        cb.record_rate_limit(key_a, cooldown_seconds=10.0)
        cb.record_rate_limit(key_b, cooldown_seconds=3.0)  # expires sooner

        # When all keys are exhausted, returns the one expiring earliest
        filtered = cb.filter_keys([key_a, key_b])
        self.assertEqual(filtered, [key_b])

    # ── 2. Robust JSON Cleaning & Multi-Stage Repair ───────────────────────────
    def test_03_clean_json_repair_trailing_commas_and_comments(self):
        # LLM output with comments, markdown fence, and trailing commas
        raw_llm_response = """
        ```json
        {
            // Channel viral hook
            "title": "Quantum Computing Exposed",
            "duration": 55,
            /* Scenes breakdown */
            "scenes": [
                "scene 1: lab intro",
                "scene 2: qubit explanation",
            ],
        }
        ```
        """
        result = clean_json_output(raw_llm_response)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["title"], "Quantum Computing Exposed")
        self.assertEqual(result["duration"], 55)
        self.assertEqual(len(result["scenes"]), 2)

    def test_04_clean_json_repair_unescaped_newlines(self):
        raw_llm_response = '{\n"title": "Story Title",\n"body": "Line one of script\nLine two of script",\n"score": 98\n}'
        result = clean_json_output(raw_llm_response)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["score"], 98)
        self.assertIn("Line one", result["body"])

    # ── 3. Pydantic Structured Output Validation ──────────────────────────────
    def test_05_pydantic_schema_validation(self):
        raw_llm_response = """
        {
            "title": "AI Revolution",
            "duration": 60,
            "scenes": ["intro", "climax", "outro"]
        }
        """
        model_instance = clean_json_output(raw_llm_response, schema=ScriptTestSchema)
        self.assertIsInstance(model_instance, ScriptTestSchema)
        self.assertEqual(model_instance.title, "AI Revolution")
        self.assertEqual(model_instance.duration, 60)
        self.assertEqual(len(model_instance.scenes), 3)

    def test_06_pydantic_schema_validation_failure(self):
        # Missing required field "scenes"
        raw_llm_response = '{"title": "Valid Title", "duration": 50}'
        with self.assertRaises(ValueError) as ctx:
            clean_json_output(raw_llm_response, schema=ScriptTestSchema)
        self.assertIn("Pydantic schema validation", str(ctx.exception))

    # ── 4. Transient Errors & Exponential Backoff Helpers ─────────────────────
    def test_07_transient_error_detection(self):
        self.assertTrue(_is_transient_error(Exception("502 Bad Gateway from upstream")))
        self.assertTrue(_is_transient_error(Exception("HTTP 503 Service Unavailable")))
        self.assertTrue(_is_transient_error(Exception("Connection reset by peer")))
        self.assertFalse(_is_transient_error(Exception("HTTP 401 Unauthorized")))
        self.assertFalse(_is_transient_error(Exception("400 Bad Request")))

    def test_08_quota_error_detection(self):
        self.assertTrue(_is_quota_error(Exception("HTTP 429 Too Many Requests")))
        self.assertTrue(_is_quota_error(Exception("ResourceExhausted: rate limit reached")))
        self.assertFalse(_is_quota_error(Exception("500 Internal Server Error")))

    def test_09_backoff_calculation(self):
        for attempt in range(4):
            delay = _calc_backoff(attempt, base=0.4, max_delay=3.0)
            self.assertGreaterEqual(delay, 0.1)
            self.assertLessEqual(delay, 3.0)

    # ── 5. Persistent HTTP Connection Pooling ─────────────────────────────────
    def test_10_http_connection_pooling(self):
        client1 = get_sync_http_client()
        client2 = get_sync_http_client()
        self.assertIs(client1, client2)
        self.assertFalse(client1.is_closed)

    # ── 6. Async Execution API ────────────────────────────────────────────────
    @patch("core.ai_client._acall_groq", new_callable=AsyncMock)
    def test_11_agenerate_with_rotation(self, mock_acall):
        mock_acall.return_value = '{"success": true}'

        async def run_test():
            return await agenerate_with_rotation(
                "Write a short hook",
                custom_keys={"groq": ["gsk_dummy_test_key_12345"]}
            )

        res = asyncio.run(run_test())
        self.assertEqual(res, '{"success": true}')
        mock_acall.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
