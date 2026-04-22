"""
LangGraph node functions — each takes ReactorState and returns a partial
state dict. Nodes call deterministic execution/ tools; only analyze_node
calls the LLM.
"""

import os
import sys
import warnings
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.load_sensor_data import load_sensor_data
from execution.detect_anomalies import detect_anomalies, summarise_anomalies
from execution.retrieve_context import retrieve_context
from orchestration.llm_factory import get_llm_response
from orchestration.state import ReactorState

SYSTEM_PROMPT = (
    "You are an expert chemical reactor safety engineer specialising in "
    "jacketed batch reactors. You analyze temperature anomalies, "
    "cross-reference process documentation, and provide structured root "
    "cause analysis with actionable recommendations."
)

ANALYZE_PROMPT_TEMPLATE = """\
## Reactor 220B — Temperature Excursion Analysis

You have been provided with sensor anomaly data and relevant process documentation.

### Detected Anomalies ({total} total)
**Summary by type:**
{anomaly_summary}

**Key events:**
{key_events}

### Retrieved Process Documentation
{doc_context}

---
Please provide a structured root cause analysis covering:

1. **Primary Root Cause** — the most likely single cause of the excursion
2. **Contributing Factors** — secondary factors that amplified the event
3. **Timeline of Events** — chronological sequence based on the data
4. **Recommended Corrective Actions** — immediate steps to take
5. **Preventive Measures** — changes to prevent recurrence

Ground your analysis in the documentation provided. Be specific and actionable.
"""


# ---------------------------------------------------------------------------
# Node 1: Ingest sensor data
# ---------------------------------------------------------------------------

def ingest_node(state: ReactorState) -> Dict[str, Any]:
    """Load and validate the sensor CSV. Fatal if missing or invalid."""
    csv_path = state["csv_path"]
    try:
        df = load_sensor_data(csv_path)
        return {"sensor_data": df, "errors": state.get("errors", [])}
    except Exception as exc:
        # CSV failure is fatal — propagate
        raise RuntimeError(f"ingest_node failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Node 2: Detect anomalies
# ---------------------------------------------------------------------------

def detect_anomalies_node(state: ReactorState) -> Dict[str, Any]:
    """Run deterministic threshold checks. Returns anomaly list (may be empty)."""
    df = state["sensor_data"]
    anomalies = detect_anomalies(df)
    return {
        "anomalies": [a.to_dict() for a in anomalies],
        "errors": state.get("errors", []),
    }


# ---------------------------------------------------------------------------
# Conditional edge router
# ---------------------------------------------------------------------------

def route_after_detect(state: ReactorState) -> str:
    """Deterministic routing: only call RAG + LLM if anomalies exist."""
    return "retrieve" if state.get("anomalies") else "report"


# ---------------------------------------------------------------------------
# Node 3: Retrieve relevant documentation
# ---------------------------------------------------------------------------

def retrieve_node(state: ReactorState) -> Dict[str, Any]:
    """Build a RAG query from the top anomalies and fetch context chunks."""
    anomalies = state.get("anomalies", [])
    docs_dir = state.get("docs_dir", "docs")

    # Build a focused query from the most critical anomaly types found
    types_found = list({a["anomaly_type"] for a in anomalies})
    query = (
        f"Reactor temperature excursion: {', '.join(types_found)}. "
        "Coolant valve troubleshooting, agitator RPM, Feed B step change, "
        "thermal runaway prevention."
    )

    errors = list(state.get("errors", []))
    try:
        chunks = retrieve_context(query)
    except FileNotFoundError as exc:
        # FAISS index missing — try to build it on the fly
        warnings.warn(f"FAISS index missing: {exc}. Attempting to build now...")
        try:
            from execution.build_vectorstore import build_vectorstore
            build_vectorstore(docs_dir)
            chunks = retrieve_context(query)
        except Exception as build_exc:
            err_msg = f"retrieve_node: could not build/load vectorstore: {build_exc}"
            warnings.warn(err_msg)
            errors.append(err_msg)
            chunks = []

    return {"retrieved_chunks": chunks, "errors": errors}


# ---------------------------------------------------------------------------
# Node 4: LLM root cause analysis
# ---------------------------------------------------------------------------

def analyze_node(state: ReactorState) -> Dict[str, Any]:
    """Call the LLM to synthesise root cause analysis from anomalies + docs."""
    anomalies = state.get("anomalies", [])
    chunks = state.get("retrieved_chunks", [])
    provider = state.get("provider", "groq")
    model = state.get("model", "")
    reasoning_log = list(state.get("reasoning_log", []))
    errors = list(state.get("errors", []))

    # Format anomaly summary
    summary = summarise_anomalies_from_dicts(anomalies)
    summary_lines = "\n".join(
        f"  - {k}: {v} occurrence(s)" for k, v in sorted(summary.items())
    )

    # Key events: up to 10 most noteworthy anomalies
    notable_types = ["temp_interlock", "temp_alarm", "ramp_rate",
                     "agitator_low", "feed_b_step", "delta_t"]
    key_anomalies = []
    seen_types: set = set()
    for a in anomalies:
        if a["anomaly_type"] in notable_types and a["anomaly_type"] not in seen_types:
            key_anomalies.append(a)
            seen_types.add(a["anomaly_type"])
            if len(key_anomalies) >= 10:
                break

    key_events_text = "\n".join(
        f"  [{a['timestamp']}] {a['message']}" for a in key_anomalies
    )

    # Format retrieved doc context
    doc_lines = []
    for i, chunk in enumerate(chunks, 1):
        doc_lines.append(
            f"[Doc {i} | {chunk['source']}]\n{chunk['content']}"
        )
    doc_context = "\n\n".join(doc_lines) if doc_lines else "(no documentation retrieved)"

    prompt = ANALYZE_PROMPT_TEMPLATE.format(
        total=len(anomalies),
        anomaly_summary=summary_lines,
        key_events=key_events_text,
        doc_context=doc_context,
    )

    try:
        response = get_llm_response(prompt, system=SYSTEM_PROMPT,
                                    provider=provider, model=model or None)
    except Exception as exc:
        err_msg = f"analyze_node LLM call failed: {exc}"
        warnings.warn(err_msg)
        errors.append(err_msg)
        response = f"[LLM unavailable — {exc}]"

    # Log full prompt + response for self-annealing review
    reasoning_log.append({
        "node": "analyze_node",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "prompt": prompt,
        "response": response,
    })

    # Extract recommendations (everything after "4." or "5." heading)
    recommendations = _extract_recommendations(response)

    return {
        "root_cause_analysis": response,
        "recommendations": recommendations,
        "reasoning_log": reasoning_log,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Node 5: Build report
# ---------------------------------------------------------------------------

def report_node(state: ReactorState) -> Dict[str, Any]:
    """Compile final state — no side effects here, outputs written by main.py."""
    # This node is a pass-through; actual file writing happens in main.py
    # so the graph remains testable without filesystem side effects.
    return {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def summarise_anomalies_from_dicts(anomalies: list) -> dict:
    summary: dict = {}
    for a in anomalies:
        t = a.get("anomaly_type", "unknown")
        summary[t] = summary.get(t, 0) + 1
    return summary


def _extract_recommendations(text: str) -> str:
    """Heuristically pull out the recommendations section."""
    markers = [
        "4. **Recommended Corrective Actions",
        "4. Recommended Corrective Actions",
        "**Recommended Corrective Actions",
        "Recommended Corrective Actions",
        "5. **Preventive",
        "Recommendations:",
    ]
    lower = text.lower()
    for marker in markers:
        idx = lower.find(marker.lower())
        if idx != -1:
            return text[idx:].strip()
    return text  # return full text if no section found
