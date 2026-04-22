# Runbook – Temperature Control Troubleshooting

**Goal:** Stabilize reactor temperature within setpoint ±2°C with safe ramps.

## Quick Checklist
- Coolant supply < 20°C, pressure within spec.
- 10% coolant valve step; check for stiction/deadband.
- Agitator RPM ≥ 280; check VFD alarms.
- Review recent changes: feeds, setpoints, PI tuning.
- Compare reactor vs jacket; lag > 3–4 min suggests bottleneck.

## Common Causes
1. Sticky coolant valve → slow cooling.
2. Agitator shear reduction → poor heat transfer.
3. Feed B increase → higher exotherm.

## Remedies
- Temporarily increase coolant valve bias (+5–10%).
- Restore agitator to 300 RPM; inspect mechanics if unstable.
- If T ≥ 98°C or runaway indicators → Emergency TRP-12.
