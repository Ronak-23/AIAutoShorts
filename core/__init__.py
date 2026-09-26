"""
AIAutoShorts Core Engine
========================
Autonomous video generation, multi-agent LangGraph orchestration,
and media rendering subsystem for AIAutoShorts.
"""

__version__ = "1.0.0"

from core.ai_client import generate_with_rotation, clean_json_output
from core.channel_context import ChannelContext

__all__ = [
    "ChannelContext",
    "generate_with_rotation",
    "clean_json_output",
    "__version__",
]
