# Data Artifacts for Reactor Troubleshooting Agent

This file contains all the data files needed to complete the reactor troubleshooting agent task. Copy each section into the appropriate file in your project structure.

---

## 1. Sensor Data: `data/reactor_sensors.csv`

See `reactor_sensors.csv` at the root (120-row sample) or run `python reactor_agent/execution/create_pdf_docs.py` to regenerate the full dataset.

**Key features in the data:**
- Feed B step change at 08:44 from ~20 to ~30.5 kg/h
- Temperature spike starting at 08:50, peaking at 101.24°C at 09:04
- Agitator RPM drops below 280 during spike (255–265 range)
- Jacket temperature lags reactor temperature during excursion

---

## 2. Runbook: `docs/Runbook-TempControl.md`

See `reactor_agent/docs/Runbook-TempControl.md`

---

## 3. Reactor Spec: `docs/Spec-Reactor-220B.md`

See `reactor_agent/docs/Spec-Reactor-220B.md`
