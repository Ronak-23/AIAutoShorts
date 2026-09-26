"""
core/graph/workflow.py
======================
Assembles and compiles the AutoReel LangGraph StateGraph, wiring up
cyclic self-correction loops, parallel asset production, and optional
Human-in-the-Loop (HITL) checkpoints.
"""

from typing import Optional, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from core.graph.state import VideoProductionState
from core.graph.nodes import (
    init_pipeline_node,
    scout_trend_node,
    scriptwriter_node,
    legal_check_node,
    quality_control_node,
    voiceover_node,
    visual_curator_node,
    music_director_node,
    thumbnail_node,
    video_assembler_node,
    video_qc_node,
    youtube_publisher_node
)


def should_revise_script(state: VideoProductionState) -> str:
    """
    Evaluates whether the script needs to loop back to the scriptwriter
    or proceed to parallel media production.
    """
    if state.get("error"):
        return "proceed_to_production"

    qc_approved = state.get("qc_approved", False)
    retries = state.get("script_retry_count", 0)
    max_retries = state.get("max_script_retries", 3)

    if not qc_approved and retries < max_retries:
        return "revise_script"
    
    return "proceed_to_production"


def route_after_qc(state: VideoProductionState) -> List[str]:
    """
    Evaluates whether the script needs to loop back to the scriptwriter
    or proceed to parallel media production workers.
    """
    decision = should_revise_script(state)
    if decision == "revise_script":
        return ["scriptwriter"]
    return ["voiceover", "visual_curator", "music_director", "thumbnail"]


def build_aiautoshorts_graph(
    start_from_node: str = "init_pipeline",
    checkpointer: Optional[Any] = None,
    interrupt_before: Optional[List[str]] = None,
    interrupt_after: Optional[List[str]] = None
):
    """
    Constructs and compiles the full AIAutoShorts video generation graph.
    
    Args:
        start_from_node: Node to wire to START (e.g. 'init_pipeline' for full run, 'assemble_video' for assembly only)
        checkpointer: Optional LangGraph checkpointer (e.g., MemorySaver, SqliteSaver)
        interrupt_before: List of node names to pause execution before (HITL)
        interrupt_after: List of node names to pause execution after (HITL)
    """
    workflow = StateGraph(VideoProductionState)

    # ── 1. Register Nodes ──
    workflow.add_node("init_pipeline", init_pipeline_node)
    workflow.add_node("scout_trend", scout_trend_node)
    workflow.add_node("scriptwriter", scriptwriter_node)
    workflow.add_node("legal_check", legal_check_node)
    workflow.add_node("quality_control", quality_control_node)

    # Parallel Production Workers
    workflow.add_node("voiceover", voiceover_node)
    workflow.add_node("visual_curator", visual_curator_node)
    workflow.add_node("music_director", music_director_node)
    workflow.add_node("thumbnail", thumbnail_node)

    # Assembly & Publishing
    workflow.add_node("assemble_video", video_assembler_node)
    workflow.add_node("video_qc", video_qc_node)
    workflow.add_node("publish_youtube", youtube_publisher_node)

    # ── 2. Wire Graph Topology ──
    if start_from_node == "init_pipeline":
        workflow.add_edge(START, "init_pipeline")
        workflow.add_edge("init_pipeline", "scout_trend")
        workflow.add_edge("scout_trend", "scriptwriter")
        workflow.add_edge("scriptwriter", "legal_check")
        workflow.add_edge("legal_check", "quality_control")

        # Cyclic Self-Correction Gate: Conditional fan-out to parallel workers
        workflow.add_conditional_edges(
            "quality_control",
            route_after_qc,
            ["scriptwriter", "voiceover", "visual_curator", "music_director", "thumbnail"]
        )

        # Fan-in all parallel assets into Video Assembly
        workflow.add_edge("voiceover", "assemble_video")
        workflow.add_edge("visual_curator", "assemble_video")
        workflow.add_edge("music_director", "assemble_video")
        workflow.add_edge("thumbnail", "assemble_video")
    else:
        # Direct entry into a specific node (e.g. assemble_video)
        workflow.add_edge(START, start_from_node)

    # Assembly -> QC -> YouTube -> END
    workflow.add_edge("assemble_video", "video_qc")
    workflow.add_edge("video_qc", "publish_youtube")
    workflow.add_edge("publish_youtube", END)

    # ── 3. Compile Graph ──
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after
    )

    return app


# Backward compatibility alias
build_autoreel_graph = build_aiautoshorts_graph
