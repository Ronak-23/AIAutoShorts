"""
core/retrieval_validator.py
===========================
Retrieval Validation Layer using the 2-Tier Hybrid Validator (Local CLIP + Cloud Gemini VLM Escalation).
"""

from typing import Dict, Any
from core.hybrid_validator import get_hybrid_validator


def validate_asset(video_path: str, query: str, narration: str, visual_intent: str, channel_name: str) -> Dict[str, Any]:
    """
    Validates candidate video asset against narration, query, and visual intent
    using the 2-Tier Hybrid Validator. Returns standard validation result dictionary.
    """
    from config.settings import SKIP_CLIP_VALIDATION
    if SKIP_CLIP_VALIDATION:
        return {
            "score": 10.0,
            "similarity": 0.35,
            "entity_match": True,
            "event_match": True,
            "context_match": True,
            "aesthetic_match": True,
            "accept": True,
            "method": "metadata_bypass",
            "reason": "Pre-download metadata verified. Visual validation bypassed via SKIP_CLIP_VALIDATION."
        }

    validator = get_hybrid_validator()
    val_res = validator.validate_asset(
        video_path=video_path,
        query=query,
        narration=narration,
        visual_intent=visual_intent,
        channel_name=channel_name
    )

    # Maintain backward-compatible schema fields
    val_res.update({
        "entity_match": val_res.get("accept", False),
        "event_match": val_res.get("accept", False),
        "context_match": val_res.get("accept", False),
        "aesthetic_match": val_res.get("accept", False),
    })

    return val_res
