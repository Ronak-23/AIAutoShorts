"""
core/hybrid_validator.py
========================
2-Tier Hybrid Retrieval Validator for AutoReel B-Roll Footage.

Tier 1: Fast Local CLIP (ViT-B/32) inference on CPU (0 tokens, ~30-50ms).
        - High match (similarity >= 0.25) -> Instant Auto-Approve (0 cloud tokens).
        - Clear mismatch (similarity < 0.16) -> Instant Auto-Reject (0 cloud tokens).
Tier 2: Cloud Gemini VLM Escalation.
        - Triggered ONLY on the ambiguous zone (0.16 <= similarity < 0.25).
        - Inspects 1 downscaled keyframe for fine-grained entity/cultural reasoning.
"""

import os
import json
import time
from typing import Dict, Any, Optional
from PIL import Image

from core.local_validator import get_local_validator, extract_mid_frame
from config.settings import GEMINI_API_KEYS


class HybridRetrievalValidator:
    """Hybrid 2-Tier Vision-Language retrieval validator."""

    def __init__(self, high_threshold: float = 0.25, low_threshold: float = 0.16):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.local_validator = get_local_validator()

    def validate_asset(
        self,
        video_path: str,
        query: str,
        narration: str = "",
        visual_intent: str = "",
        channel_name: str = "demo_channel"
    ) -> Dict[str, Any]:
        """
        Executes hybrid validation:
        1. Evaluates local CLIP cosine similarity.
        2. Auto-resolves obvious passes and rejects.
        3. Escalates ambiguous cases to Gemini Flash VLM.
        """
        # Step 1: Extract 1 mid-frame
        frame_path = extract_mid_frame(video_path)
        if not frame_path or not os.path.exists(frame_path):
            return {
                "score": 5.0,
                "similarity": 0.20,
                "accept": True,
                "method": "bypassed_missing_frame",
                "reason": "Frame extraction bypassed — accepted with default confidence."
            }

        # Step 2: Compute Tier 1 Local CLIP similarity
        target_text = visual_intent or query or narration
        clip_prompt = f"a high quality stock video clip showing {target_text}"

        try:
            with Image.open(frame_path) as img:
                sim = self.local_validator.compute_similarity(img.convert("RGB"), clip_prompt)
        except Exception as e:
            print(f"[HybridValidator] Local CLIP computation error: {e}")
            sim = 0.22

        # ── TIER 1A: Clear High Match (0 Cloud Tokens) ──
        if sim >= self.high_threshold:
            self._cleanup_frame(frame_path)
            return {
                "score": round(min(10.0, sim * 25.0), 1),
                "similarity": round(sim, 4),
                "accept": True,
                "method": "local_clip_pass",
                "reason": f"Tier 1 Local CLIP strong match (sim: {sim:.3f} >= {self.high_threshold:.2f}) for '{target_text[:40]}'."
            }

        # ── TIER 1B: Clear Mismatch (0 Cloud Tokens) ──
        if sim < self.low_threshold:
            self._cleanup_frame(frame_path)
            return {
                "score": round(max(0.0, sim * 25.0), 1),
                "similarity": round(sim, 4),
                "accept": False,
                "method": "local_clip_reject",
                "reason": f"Tier 1 Local CLIP clear mismatch (sim: {sim:.3f} < {self.low_threshold:.2f}) for '{target_text[:40]}'."
            }

        # ── TIER 2: Ambiguous Zone (0.16 <= sim < 0.25) -> Cloud Gemini VLM Escalation ──
        print(f"[HybridValidator] Ambiguous CLIP similarity ({sim:.3f}). Escalating to Tier 2 Gemini VLM...")
        vlm_res = self._escalate_to_gemini_vlm(frame_path, query, narration, target_text, channel_name, sim)
        self._cleanup_frame(frame_path)
        return vlm_res

    def _escalate_to_gemini_vlm(
        self,
        frame_path: str,
        query: str,
        narration: str,
        visual_intent: str,
        channel_name: str,
        local_sim: float
    ) -> Dict[str, Any]:
        """Calls Gemini Multimodal API on a single keyframe for fine-grained reasoning."""
        if not GEMINI_API_KEYS:
            # Fallback if no Gemini keys available
            accept = local_sim >= 0.20
            return {
                "score": round(local_sim * 25.0, 1),
                "similarity": round(local_sim, 4),
                "accept": accept,
                "method": "fallback_local_threshold",
                "reason": f"Gemini keys not configured. Fallback decision (sim: {local_sim:.3f} >= 0.20: {accept})."
            }

        try:
            from google import genai
            from google.genai import types as genai_types

            system_instruction = (
                "You are the visual retrieval validator for AutoReel video production. "
                "Inspect the provided keyframe and determine if it contextually matches the narration and visual intent. "
                "Respond strictly in JSON with keys 'score' (0-10 integer), 'accept' (true if score >= 7 else false), and 'reason' (brief 1 sentence)."
            )
            user_prompt = (
                f"Channel: {channel_name}\n"
                f"Query: {query}\n"
                f"Narration: {narration}\n"
                f"Visual Intent: {visual_intent}\n"
                "Does this single keyframe accurately represent the requested scene context?"
            )

            models_to_try = [
                "gemini-3.1-flash-lite",
                "gemini-3.5-flash-lite",
                "gemini-3.1-flash-lite-preview",
                "gemini-3.6-flash",
                "gemini-flash-lite-latest",
                "gemini-3-flash-preview"
            ]
            for key in GEMINI_API_KEYS:
                try:
                    client = genai.Client(api_key=key, http_options={"timeout": 15000})
                    with Image.open(frame_path) as img:
                        for model_name in models_to_try:
                            try:
                                response = client.models.generate_content(
                                    model=model_name,
                                    contents=[img, user_prompt],
                                    config=genai_types.GenerateContentConfig(
                                        system_instruction=system_instruction,
                                        response_mime_type="application/json",
                                        automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(disable=True)
                                    )
                                )
                                if response and response.text:
                                    break
                            except Exception as m_err:
                                print(f"[HybridValidator] Model {model_name} failed: {m_err}")
                                continue

                    if response and response.text:
                        data = json.loads(response.text.strip())
                        accept = bool(data.get("accept", data.get("score", 0) >= 7))
                        return {
                            "score": data.get("score", 7.0 if accept else 4.0),
                            "similarity": round(local_sim, 4),
                            "accept": accept,
                            "method": "gemini_vlm_evaluated",
                            "reason": f"Tier 2 Gemini VLM decision: {data.get('reason', 'Evaluated by VLM')}"
                        }
                except Exception as api_err:
                    print(f"[HybridValidator] Gemini key attempt error: {api_err}")
                    continue

        except Exception as e:
            print(f"[HybridValidator] Tier 2 escalation failed: {e}")

        # Graceful fallback if Gemini API fails
        accept = local_sim >= 0.20
        return {
            "score": round(local_sim * 25.0, 1),
            "similarity": round(local_sim, 4),
            "accept": accept,
            "method": "fallback_local_threshold",
            "reason": f"Gemini VLM unavailable. Fallback to local similarity {local_sim:.3f} >= 0.20."
        }

    @staticmethod
    def _cleanup_frame(frame_path: str):
        if frame_path and os.path.exists(frame_path):
            try:
                os.remove(frame_path)
            except Exception:
                pass


_hybrid_validator_instance: Optional[HybridRetrievalValidator] = None


def get_hybrid_validator() -> HybridRetrievalValidator:
    """Returns the singleton HybridRetrievalValidator instance."""
    global _hybrid_validator_instance
    if _hybrid_validator_instance is None:
        _hybrid_validator_instance = HybridRetrievalValidator()
    return _hybrid_validator_instance
