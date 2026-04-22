# Directive: Troubleshoot Reactor 220B Temperature Excursion

**Version:** 1.0  
**Last updated:** 2025-01-15  
**Agent:** Reactor Troubleshooting Agent (`reactor_agent/`)

---

## Purpose

Detect temperature anomalies in Reactor 220B sensor data, retrieve relevant
process documentation via RAG, and synthesise a root cause analysis using
an LLM — all grounded in the 3-layer AGENTS.md architecture.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| Sensor CSV | `data/reactor_sensors.csv` | 120-row, 2-min intervals |
| Process docs | `docs/` | Markdown + PDF |
| LLM provider | `.env` → `LLM_PROVIDER` | groq / openai / anthropic / ollama |
| Thresholds | `config.py` | Version-controlled domain knowledge |

---

## Execution Tools

| Script | Purpose | Layer |
|---|---|---|
| `execution/create_pdf_docs.py` | Generate PDFs + full 120-row CSV | Setup |
| `execution/load_sensor_data.py` | Validate and parse sensor CSV | 3 |
| `execution/detect_anomalies.py` | Threshold-based anomaly detection | 3 |
| `execution/build_vectorstore.py` | Build FAISS index from docs | 3 |
| `execution/retrieve_context.py` | Query FAISS, return top-5 chunks | 3 |

---

## Workflow

```
1. python execution/create_pdf_docs.py       # one-time setup
2. python execution/build_vectorstore.py     # one-time setup
3. python main.py --csv data/reactor_sensors.csv --provider groq
```

The LangGraph flow: `ingest → detect → [branch] → retrieve → analyze → report`

Branching rule (deterministic Python):
- **anomalies found** → retrieve docs → LLM analysis → report
- **no anomalies** → skip LLM → report directly

---

## Outputs

| File | Description |
|---|---|
| `output/report.json` | Full report: sensor summary, anomalies, RCA, recommendations |
| `output/reasoning_log.json` | Full prompt + LLM response for each `analyze_node` call |

---

## Thresholds (from `config.py`)

| Parameter | Value | Unit |
|---|---|---|
| Temperature alarm | 92 | °C |
| Temperature interlock | 98 | °C |
| Max ramp rate | 1.5 | °C/min |
| Agitator minimum | 280 | RPM |
| ΔT max (reactor−jacket) | 15 | °C |
| Feed B step threshold | 5 | kg/h |

---

## Error Handling (Self-Annealing)

| Error | Response |
|---|---|
| CSV missing or invalid | **Fatal** — raise and stop |
| PDF load failure | **Warn + continue** — log to `state["errors"]` |
| FAISS index missing | **Auto-rebuild** from `docs/` |
| LLM API error | **Warn + continue** — log to `errors`, write placeholder to report |
| Empty docs directory | **Fatal** — raise RuntimeError |

---

## Known Constraints & Learnings

- HuggingFace `all-MiniLM-L6-v2` first run downloads ~90MB model weights.
  Subsequent runs use the cached model.
- FAISS `load_local` requires `allow_dangerous_deserialization=True` in
  LangChain >= 0.2.0.
- Groq free tier: ~30 req/min; use `llama-3.1-70b-versatile` for best
  reasoning quality.
- The Feed B step change at 08:44 (Δ≈10 kg/h) precedes the temperature
  spike by ~6 minutes — use this as a diagnostic marker in the prompt.

---

## Verification Checklist

- [ ] `python execution/create_pdf_docs.py` → 2 PDFs + 120-row CSV created
- [ ] `python execution/build_vectorstore.py` → `.tmp/faiss_index/` populated
- [ ] `python main.py ...` → `output/report.json` and `reasoning_log.json` written
- [ ] `report.json` → `anomalies.total` > 0, peak temp ~101.24°C at 09:04
- [ ] `reasoning_log.json` → ≥1 entry with `node: "analyze_node"`, has `prompt` and `response`
