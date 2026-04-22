## Plan: Reactor Troubleshooting Agent (`reactor_agent/`)

**What:** A 3-layer LangGraph agent that detects temperature anomalies from sensor data, retrieves relevant documentation via FAISS RAG, and uses an LLM to synthesize root cause analysis — all grounded in the AGENTS.md architectural philosophy.

**How:** Deterministic Python handles all data and detection work; LLM handles only interpretation and synthesis; LangGraph orchestrates the flow.

---

### AGENTS.md Principle → Reactor Task Mapping

| AGENTS.md Principle | Applied Here |
|---|---|
| "LLMs probabilistic, business logic deterministic" | Anomaly detection = pure Python; root cause synthesis = LLM |
| "Errors compound: 90%×90%=59%" | CSV load, doc parsing, threshold checks all deterministic scripts |
| "Self-anneal when things break" | PDF load failure → log warning, continue; every LLM call logged |
| ".env for API tokens" | Provider, model, embedding choice all env vars |
| "Deliverables vs Intermediates" | FAISS index in `.tmp/`; `report.json` + `reasoning_log.json` are deliverables |

---

### Project Structure

```
reactor_agent/
├── directives/
│   └── troubleshoot_reactor.md       # Agent's own operating SOP (living document)
├── docs/                             # Source docs for RAG (Layer 1: knowledge)
│   ├── Runbook-TempControl.md
│   ├── Spec-Reactor-220B.md
│   ├── SOP12_Reactor_Temperature_Control.pdf
│   └── IncidentCaseStudy2019TempSpike.pdf
├── data/
│   └── reactor_sensors.csv
├── execution/                        # Layer 3: deterministic tools (no LLM)
│   ├── load_sensor_data.py
│   ├── detect_anomalies.py
│   ├── build_vectorstore.py
│   ├── retrieve_context.py
│   └── create_pdf_docs.py            # Setup helper: creates PDFs from text content
├── orchestration/                    # Layer 2: LangGraph + LLM
│   ├── state.py                      # Typed state schema (TypedDict)
│   ├── graph.py                      # StateGraph definition
│   ├── nodes.py                      # Node functions calling execution/ tools
│   └── llm_factory.py                # Multi-provider lazy-import factory
├── .tmp/                             # FAISS index, intermediates (gitignored)
├── output/
│   ├── report.json
│   └── reasoning_log.json
├── main.py                           # CLI (argparse)
├── config.py                         # Thresholds + constants
├── .env.example
├── requirements.txt
└── README.md                         # Setup + ADR
```

---

### Steps

**Phase 1: Setup & Data (parallel)**
1. `execution/create_pdf_docs.py` — uses `fpdf` to generate SOP-12 and IncidentCaseStudy as real PDFs in `docs/` from the text content in DATA_ARTIFACTS.md
2. Copy CSV (120 rows) into `data/reactor_sensors.csv`
3. Copy Markdown docs into `docs/`
4. `config.py` — thresholds dict: alarm=92°C, interlock=98°C, ramp=1.5°C/min, agitator_min=280 RPM, ΔT_max=15°C, feed_b_step=5 kg/h

**Phase 2: Execution Layer — deterministic tools (no LLM, each independently testable)**
5. `execution/load_sensor_data.py` — pandas load, column validation, returns DataFrame
6. `execution/detect_anomalies.py` — threshold checks returning `Anomaly` dataclass list: temp_alarm, temp_interlock, ramp_rate (|ΔT/Δt|>1.5/min over 2-min rows), agitator RPM, reactor−jacket ΔT, Feed B step change
7. `execution/build_vectorstore.py` — loads Markdown (direct read) + PDF (pdfplumber), chunks at 500/50 overlap, embeds via HuggingFace `all-MiniLM-L6-v2` (local) or OpenAI (env-controlled), saves FAISS to `.tmp/faiss_index`
8. `execution/retrieve_context.py` — query FAISS, return top-5 chunks with metadata

**Phase 3: Orchestration Layer — LangGraph (depends on Phase 2)**
9. `orchestration/state.py` — `ReactorState` TypedDict: csv_path, docs_dir, sensor_data, anomalies, retrieved_chunks, root_cause_analysis, recommendations, reasoning_log (list), errors (list)
10. `orchestration/llm_factory.py` — reads `LLM_PROVIDER` env var, lazy-imports groq/openai/anthropic/ollama, exposes `get_llm_response(prompt, system) → str`
11. `orchestration/nodes.py` — 5 node functions updating state: `ingest_node`, `detect_anomalies_node`, `retrieve_node`, `analyze_node`, `report_node`
12. `orchestration/graph.py` — LangGraph StateGraph: `ingest → detect → [Python conditional edge] → retrieve → analyze → report → END`, or `detect → report → END` if no anomalies

**Phase 4: Entry Point & Docs (depends on Phase 3)**
13. `main.py` — argparse: `--csv`, `--docs-dir`, `--output-dir`, `--provider`, `--model`, `--rebuild-index`
14. `.env.example`, `requirements.txt`, `directives/troubleshoot_reactor.md`, `README.md` with full ADR

---

### Answers to the Specific Challenges

| Challenge | Answer | AGENTS.md Basis |
|---|---|---|
| Anomaly detection | **Option B: Python** `temp > threshold` | "business logic is deterministic" |
| Root cause analysis | **Option A: LLM** (interprets patterns, cross-references retrieved docs) | LLM for synthesis/interpretation only |
| Workflow routing | **Option B: Python** `if anomalies_detected: retrieve_docs()` | "errors compound — push into deterministic code" |
| PDF load failure | **Option B: log warning, continue** | Self-annealing: log → continue → system stronger |

---

### Verification
1. `python execution/create_pdf_docs.py` → 2 PDFs created in `docs/`
2. `python execution/build_vectorstore.py` → `.tmp/faiss_index/` populated
3. `python main.py --csv data/reactor_sensors.csv --docs-dir docs/ --provider groq` → both JSON outputs written
4. Validate `report.json` shows ~81 anomalies, peak 101.24°C at 09:04, Feed B step at 08:44
5. Validate `reasoning_log.json` has at least 1 entry for `analyze_node` with full `prompt` and `response` fields

---

### Architecture Decision Record (6 decisions for README.md)

1. **Layer Separation**: `execution/` (deterministic) ↔ `orchestration/` (LLM+routing) ↔ `directives/`+`docs/` (knowledge)
2. **No LLM for anomaly detection**: `temp > 92` is not a question for a probabilistic model
3. **Python routing in graph**: `if anomalies_detected` is deterministic — same compounding error argument
4. **Graceful PDF failure**: log + continue; fatal only for missing CSV or no LLM key
5. **Reasoning log = self-annealing foundation**: full prompt+response enables future directive updates
6. **Thresholds in `config.py`, secrets in `.env`**: thresholds are domain knowledge (version-controlled), API keys are environment-specific
