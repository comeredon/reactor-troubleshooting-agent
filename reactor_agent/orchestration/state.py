"""
LangGraph state schema for the reactor troubleshooting agent.
All fields typed so nodes can update them safely via dict return values.
"""

from typing import TypedDict, Optional, List, Dict, Any
import pandas as pd


class ReactorState(TypedDict, total=False):
    # ---- Inputs ----
    csv_path: str
    docs_dir: str
    output_dir: str
    provider: str            # LLM provider name
    model: str               # LLM model override (empty = provider default)
    rebuild_index: bool

    # ---- Intermediate data ----
    sensor_data: Optional[Any]           # pd.DataFrame (not JSON-serialisable)
    anomalies: List[Dict]                # list of Anomaly.to_dict()
    retrieved_chunks: List[Dict]         # list from retrieve_context()

    # ---- Outputs ----
    root_cause_analysis: str
    recommendations: str

    # ---- Observability ----
    reasoning_log: List[Dict]   # [{node, timestamp, prompt, response}, ...]
    errors: List[str]           # non-fatal error messages
