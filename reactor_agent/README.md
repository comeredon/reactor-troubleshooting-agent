# Reactor Troubleshooting Agent

A 3-layer LangGraph agent that detects temperature anomalies in Reactor 220B
sensor data, retrieves relevant process documentation via FAISS RAG, and uses
an LLM to synthesise a root cause analysis.

---

## Quick Start

```bash
cd reactor_agent

# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy .env.example → .env and add your API key
cp .env.example .env
# Edit .env: set GROQ_API_KEY=... (or OPENAI_API_KEY etc.)

# 3. Generate PDFs + full sensor CSV
python execution/create_pdf_docs.py

# 4. Build FAISS vector store
python execution/build_vectorstore.py

# 5. Run the agent
python main.py --csv data/reactor_sensors.csv --docs-dir docs/ --provider groq
```

Outputs are written to `output/report.json` and `output/reasoning_log.json`.

---

## Architecture (3 Layers)

```
┌─────────────────────────────────────────────┐
│  Layer 1: Directives (What to do)           │
│  directives/troubleshoot_reactor.md         │
│  docs/ (Runbook, Spec, SOP, CaseStudy)      │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│  Layer 2: Orchestration (Decision making)   │
│  orchestration/graph.py  — LangGraph flow   │
│  orchestration/nodes.py  — node functions   │
│  orchestration/llm_factory.py — LLM calls  │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│  Layer 3: Execution (Deterministic tools)   │
│  execution/load_sensor_data.py              │
│  execution/detect_anomalies.py              │
│  execution/build_vectorstore.py             │
│  execution/retrieve_context.py              │
└─────────────────────────────────────────────┘
```

### LangGraph Flow

```
ingest → detect → ┬─(anomalies)─→ retrieve → analyze → report → END
                  └─(none)──────────────────────────→ report → END
```

---

## Project Structure

```
reactor_agent/
├── directives/
│   └── troubleshoot_reactor.md     # Agent SOP (living document)
├── docs/                           # RAG knowledge base
│   ├── Runbook-TempControl.md
│   ├── Spec-Reactor-220B.md
│   ├── SOP12_Reactor_Temperature_Control.pdf
│   └── IncidentCaseStudy2019TempSpike.pdf
├── data/
│   └── reactor_sensors.csv         # 120-row sensor log
├── execution/                      # Deterministic tools (no LLM)
│   ├── create_pdf_docs.py
│   ├── load_sensor_data.py
│   ├── detect_anomalies.py
│   ├── build_vectorstore.py
│   └── retrieve_context.py
├── orchestration/                  # LangGraph + LLM
│   ├── state.py                    # ReactorState TypedDict
│   ├── graph.py                    # StateGraph definition
│   ├── nodes.py                    # Node functions
│   └── llm_factory.py              # Multi-provider LLM factory
├── .tmp/                           # FAISS index (gitignored)
├── output/
│   ├── report.json                 # Deliverable
│   └── reasoning_log.json          # Deliverable
├── main.py                         # CLI entry point
├── config.py                       # Thresholds + constants
├── .env.example                    # Environment template
└── requirements.txt
```

---

## Configuration

All thresholds are in `config.py` (version-controlled):

| Parameter | Value |
|---|---|
| Temperature alarm | 92°C |
| Temperature interlock | 98°C |
| Max ramp rate | 1.5°C/min |
| Agitator minimum | 280 RPM |
| ΔT max (reactor−jacket) | 15°C |
| Feed B step threshold | 5 kg/h |

API keys and runtime config go in `.env` (never committed):

```
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
EMBEDDING_PROVIDER=huggingface
```

---

## CLI Options

```
python main.py [options]

  --csv         Path to sensor CSV (default: data/reactor_sensors.csv)
  --docs-dir    Docs directory (default: docs/)
  --output-dir  Output directory (default: output/)
  --provider    LLM provider: groq | openai | anthropic | ollama
  --model       Model override (empty = provider default)
  --rebuild-index  Force rebuild of FAISS vector store
```

---

## Architecture Decision Record

1. **Layer separation** — `execution/` (deterministic) / `orchestration/` (LLM + routing) / `directives/` + `docs/` (knowledge). Errors compound: 90%⁵ = 59%. Pushing complexity into deterministic code keeps reliability high.

2. **No LLM for anomaly detection** — `temp > 92` is a mathematical fact, not a probabilistic question. Python is the right tool.

3. **Python routing in graph** — The `if anomalies_detected` branch is deterministic. Using an LLM to decide whether to retrieve docs would be fragile and wasteful.

4. **Graceful PDF failure** — If a PDF fails to load, the agent logs a warning and continues with remaining docs. Only a missing CSV or missing LLM key is fatal.

5. **Reasoning log = self-annealing foundation** — Every LLM call is logged with its full `prompt` and `response`. This enables reviewing and improving prompts without re-running the pipeline, and updating directives when new patterns emerge.

6. **Thresholds in `config.py`, secrets in `.env`** — Thresholds are domain knowledge (should be reviewed by engineers, version-controlled, diff-able). API keys are environment-specific and must not be committed.
