"""
LangGraph StateGraph definition for the reactor troubleshooting agent.

Flow:
  ingest → detect → [Python routing] → retrieve → analyze → report → END
                                     ↘ report → END  (if no anomalies)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END

from orchestration.state import ReactorState
from orchestration.nodes import (
    ingest_node,
    detect_anomalies_node,
    route_after_detect,
    retrieve_node,
    analyze_node,
    report_node,
)


def build_graph() -> StateGraph:
    """Compile and return the reactor troubleshooting StateGraph."""
    workflow = StateGraph(ReactorState)

    # Register nodes
    workflow.add_node("ingest", ingest_node)
    workflow.add_node("detect", detect_anomalies_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("report", report_node)

    # Linear edges
    workflow.add_edge("ingest", "detect")
    workflow.add_edge("retrieve", "analyze")
    workflow.add_edge("analyze", "report")
    workflow.add_edge("report", END)

    # Conditional branch after detection
    workflow.add_conditional_edges(
        "detect",
        route_after_detect,
        {
            "retrieve": "retrieve",
            "report": "report",   # fast-path: no anomalies detected
        },
    )

    # Entry point
    workflow.set_entry_point("ingest")

    return workflow.compile()


# Module-level compiled app (imported by main.py)
app = build_graph()
