"""
core/gemini_client.py
=====================
Backward compatibility shim re-exporting the canonical unified AI client
from core.ai_client.
"""

from core.ai_client import (
    clean_json_output,
    generate_with_rotation,
    agenerate_with_rotation,
    generate_with_gemini,
    agenerate_with_gemini,
    get_current_context,
    set_current_context,
    scoped_context,
    _GROQ_MODEL_CASCADE,
    _GEMINI_MODEL_CASCADE,
    _OPENROUTER_MODEL_CASCADE,
)

__all__ = [
    "clean_json_output",
    "generate_with_rotation",
    "agenerate_with_rotation",
    "generate_with_gemini",
    "agenerate_with_gemini",
    "get_current_context",
    "set_current_context",
    "scoped_context",
]
