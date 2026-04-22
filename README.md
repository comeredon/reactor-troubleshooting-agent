# Reactor Troubleshooting Agent

AI-powered anomaly detection and troubleshooting agent for Reactor 220B. Uses a 3-layer architecture (directives → orchestration → deterministic execution) to detect sensor anomalies and retrieve context from process documents via RAG.

## What it does

- **Detects anomalies** deterministically from sensor CSV data (temperature alarms, ramp rates, agitator RPM drops, Feed B step changes, ΔT violations)
- **Retrieves context** from process docs (runbooks, specs, SOPs) using a local FAISS vector store
- **No hallucination risk** on thresholds — all threshold logic is pure Python in `execution/detect_anomalies.py`

## Project Structure

```
reactor_agent/
  config.py                    # Thresholds, constants
  docs/                        # Runbook and spec (Markdown + PDF)
  execution/
    create_pdf_docs.py         # Generate PDFs and sensor CSV
    build_vectorstore.py       # Build FAISS index from docs
    load_sensor_data.py        # Load & validate sensor CSV
    detect_anomalies.py        # Deterministic anomaly detection
reactor_sensors.csv            # Sample sensor data (120 rows)
Runbook-TempControl.md         # Temperature control runbook
Spec-Reactor-220B.md           # Reactor 220B specifications
```

## Quick Start

```bash
pip install pandas langchain langchain-community langchain-huggingface faiss-cpu pdfplumber fpdf2

# Generate PDFs and full sensor CSV
python reactor_agent/execution/create_pdf_docs.py

# Build FAISS vector store from docs
python reactor_agent/execution/build_vectorstore.py

# Load and validate sensor data
python reactor_agent/execution/load_sensor_data.py
```

## Reactor 220B Thresholds

| Parameter | Alarm | Interlock |
|---|---|---|
| Reactor Temp | 92°C | 98°C |
| Ramp Rate | 1.5°C/min | 3.0°C/min |
| Agitator RPM | 280 min | — |
| ΔT (reactor − jacket) | 15°C max | — |

## Architecture

Follows the 3-layer agent pattern described in `AGENTS.md`:
- **Layer 1 (Directive):** `docs/` — SOPs and specs in Markdown
- **Layer 2 (Orchestration):** LLM agent routing decisions
- **Layer 3 (Execution):** Deterministic Python scripts in `execution/`
