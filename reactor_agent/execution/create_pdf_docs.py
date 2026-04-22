"""
Setup helper: generates the two PDFs required for RAG and the complete
120-row sensor CSV. Run once before building the vector store.

Usage:
    python execution/create_pdf_docs.py
"""

import math
import os
import csv
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

SOP12_TEXT = """SOP-12: Reactor Temperature Control

Applies to: Reactor 220B and similar jacketed vessels

1. Purpose
Define procedures to maintain reactor temperature within safe limits and
respond to excursions.

2. Operating Limits
Setpoints: Nominal 85 degrees C; Alarm 92 degrees C; Interlock 98 degrees C.
Recommended |dT/dt| <= 1.5 degrees C/min (normal).
Maintain delta T = (reactor minus jacket) within 5-15 degrees C in
steady-state.

3. Controls and Instrumentation
Primary loop: Reactor_T -> PID -> Coolant_Valve (% open).
Agitator RPM sustains heat transfer coefficient U.

4. Troubleshooting Thermal Excursions
If reactor temperature rises > 3 degrees C above setpoint or
dT/dt > 1.5 degrees C/min:

1. Verify coolant supply pressure and temperature (< 20 degrees C).
2. Check coolant valve for stiction; command a 10% step test.
3. Confirm agitator RPM >= 280; inspect VFD and coupling if low.
4. Correlate with feed composition changes
   (increase in Feed B exotherm).
5. If reactor_temp >= 98 degrees C or runaway suspected,
   trigger interlock TRP-12.

5. Verification and Documentation
1. Record commanded vs observed valve position.
2. Log RPM trend and any VFD trips.
3. Capture reactor, jacket, pressure, and pH trends.

Appendix A: Known Failure Modes
1. Coolant valve sticking near 30-40% open.
2. Agitator shear reduction -> jacket lag.
3. Mis-tuned PID oscillations (4-6 min).

Note: An older note links pressure spikes to pH probe faults -
ignore (intentional distractor).
"""

INCIDENT_TEXT = """Incident Case Study - 2019 Temperature Spike

Summary:
Temperature excursion approximately 55 minutes after a feed change
increasing Feed B by approximately 10 kg/h.

Root Cause:
Coolant valve stiction near 35% open combined with temporary agitator
shear drop of approximately 40 RPM.

Evidence:
1. Jacket temperature lagged reactor by approximately 4 minutes.
2. Valve command vs position hysteresis on 10% step test.
3. Agitator RPM dips correlate with rising reactor temperature.

Corrective Actions:
1. Service valve trim and actuator; clean strainer.
2. Verify VFD parameters and mechanical coupling.

Lessons Learned:
- Feed B step changes greater than 5 kg/h require enhanced monitoring
  for at least 30 minutes post-change.
- Agitator RPM below 280 during a thermal excursion significantly
  reduces heat transfer and amplifies the temperature rise.
- Jacket temperature lag is an early indicator of coolant valve issues.
- Response time from alarm (92 degrees C) to interlock (98 degrees C)
  can be under 4 minutes under worst-case conditions.
"""


def create_pdf(filepath: str, title: str, content: str) -> None:
    """Create a PDF from text content using fpdf2."""
    try:
        from fpdf import FPDF
    except ImportError:
        print("WARNING: fpdf2 not installed. Run: pip install fpdf2")
        print(f"Skipping PDF creation for: {filepath}")
        return

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", size=14)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.ln(4)

    for line in content.strip().split("\n"):
        # Handle long lines by wrapping
        pdf.multi_cell(0, 6, line if line.strip() else "")

    pdf.output(filepath)
    print(f"Created: {filepath}")


# ---------------------------------------------------------------------------
# CSV generation: 44 known rows + 76 generated rows = 120 total
# ---------------------------------------------------------------------------

KNOWN_ROWS = [
    # fmt: off
    ["2025-01-15 08:00:00", 84.55, 69.12, 2.34, 145.2, 6.82, 299.35, 25.3, 19.8],
    ["2025-01-15 08:02:00", 84.73, 69.45, 2.36, 144.8, 6.84, 300.12, 25.1, 20.1],
    ["2025-01-15 08:04:00", 84.89, 69.78, 2.35, 145.5, 6.81, 298.76, 25.4, 19.9],
    ["2025-01-15 08:06:00", 85.02, 70.01, 2.37, 144.9, 6.83, 299.88, 25.2, 20.3],
    ["2025-01-15 08:08:00", 85.15, 70.23, 2.36, 145.3, 6.85, 300.45, 25.3, 20.0],
    ["2025-01-15 08:10:00", 85.21, 70.34, 2.38, 145.1, 6.84, 299.67, 25.5, 19.7],
    ["2025-01-15 08:12:00", 85.28, 70.51, 2.37, 144.7, 6.86, 300.23, 25.2, 20.2],
    ["2025-01-15 08:14:00", 85.34, 70.67, 2.39, 145.4, 6.83, 299.91, 25.4, 19.8],
    ["2025-01-15 08:16:00", 85.41, 70.82, 2.38, 145.0, 6.85, 300.56, 25.1, 20.4],
    ["2025-01-15 08:18:00", 85.47, 70.95, 2.40, 144.8, 6.87, 299.44, 25.3, 20.0],
    ["2025-01-15 08:20:00", 85.53, 71.09, 2.39, 145.2, 6.84, 300.78, 25.2, 19.9],
    ["2025-01-15 08:22:00", 85.59, 71.23, 2.41, 145.6, 6.86, 299.23, 25.5, 20.1],
    ["2025-01-15 08:24:00", 85.64, 71.36, 2.40, 144.9, 6.85, 300.34, 25.3, 20.3],
    ["2025-01-15 08:26:00", 85.70, 71.48, 2.42, 145.3, 6.88, 299.67, 25.4, 19.7],
    ["2025-01-15 08:28:00", 85.75, 71.61, 2.41, 145.1, 6.86, 300.89, 25.1, 20.0],
    ["2025-01-15 08:30:00", 85.80, 71.73, 2.43, 144.7, 6.87, 299.56, 25.6, 20.2],
    ["2025-01-15 08:32:00", 85.85, 71.84, 2.42, 145.5, 6.89, 300.12, 25.2, 19.8],
    ["2025-01-15 08:34:00", 85.90, 71.96, 2.44, 145.2, 6.85, 299.78, 25.3, 20.4],
    ["2025-01-15 08:36:00", 85.94, 72.07, 2.43, 144.8, 6.88, 300.45, 25.5, 20.1],
    ["2025-01-15 08:38:00", 85.98, 72.18, 2.45, 145.4, 6.86, 299.34, 25.1, 19.9],
    ["2025-01-15 08:40:00", 86.02, 72.28, 2.44, 145.1, 6.90, 300.67, 25.4, 20.0],
    ["2025-01-15 08:42:00", 86.06, 72.38, 2.46, 144.9, 6.87, 299.89, 25.2, 20.3],
    # Feed B step change at 08:44: ~20 → ~30.5 kg/h
    ["2025-01-15 08:44:00", 85.17, 69.81, 2.45, 145.3, 6.89, 299.35, 25.3, 30.49],
    ["2025-01-15 08:46:00", 85.34, 70.13, 2.47, 145.6, 6.88, 299.82, 25.5, 29.65],
    ["2025-01-15 08:48:00", 86.78, 71.45, 2.48, 144.7, 6.91, 298.56, 25.1, 30.12],
    # Temperature spike begins
    ["2025-01-15 08:50:00", 91.23, 74.89, 2.50, 145.2, 6.89, 275.34, 25.3, 29.87],
    ["2025-01-15 08:52:00", 96.93, 78.45, 2.52, 145.5, 6.92, 260.72, 25.6, 30.21],
    ["2025-01-15 08:54:00", 97.79, 79.12, 2.54, 144.8, 6.90, 259.63, 25.2, 29.94],
    ["2025-01-15 08:56:00", 98.46, 79.67, 2.56, 145.1, 6.93, 257.81, 25.4, 30.08],
    ["2025-01-15 08:58:00", 98.71, 80.01, 2.58, 145.4, 6.91, 256.45, 25.1, 30.33],
    ["2025-01-15 09:00:00", 100.01, 81.23, 2.60, 144.9, 6.94, 258.92, 25.5, 29.76],
    ["2025-01-15 09:02:00", 100.72, 82.14, 2.62, 145.3, 6.92, 255.72, 25.2, 30.15],
    # Peak temperature
    ["2025-01-15 09:04:00", 101.24, 82.68, 2.64, 145.6, 6.95, 265.16, 25.3, 30.42],
    # Recovery begins
    ["2025-01-15 09:06:00", 100.87, 82.91, 2.63, 144.7, 6.93, 279.34, 25.6, 29.88],
    ["2025-01-15 09:08:00", 99.45, 82.45, 2.61, 145.2, 6.91, 287.56, 25.1, 30.01],
    ["2025-01-15 09:10:00", 97.23, 81.34, 2.59, 145.5, 6.94, 293.78, 25.4, 30.19],
    ["2025-01-15 09:12:00", 94.67, 79.89, 2.57, 144.8, 6.92, 297.23, 25.2, 29.93],
    ["2025-01-15 09:14:00", 92.15, 78.12, 2.55, 145.1, 6.90, 299.45, 25.5, 30.27],
    ["2025-01-15 09:16:00", 89.78, 76.45, 2.53, 145.4, 6.93, 300.67, 25.3, 29.81],
    ["2025-01-15 09:18:00", 87.89, 74.89, 2.51, 144.9, 6.91, 299.89, 25.1, 30.08],
    ["2025-01-15 09:20:00", 86.45, 73.56, 2.49, 145.3, 6.94, 300.23, 25.6, 30.34],
    ["2025-01-15 09:22:00", 85.67, 72.67, 2.47, 145.6, 6.92, 299.78, 25.2, 29.95],
    ["2025-01-15 09:24:00", 85.23, 72.01, 2.45, 144.7, 6.90, 300.45, 25.4, 30.11],
    ["2025-01-15 09:26:00", 84.98, 71.56, 2.44, 145.2, 6.93, 299.56, 25.1, 30.23],
    # fmt: on
]


def generate_remaining_rows() -> list:
    """
    Generate rows 45-120 (09:28 to 11:58) representing the new steady-state
    operating point after the Feed B step change and thermal excursion.
    """
    rows = []
    base_time = datetime(2025, 1, 15, 9, 28)

    for i in range(76):
        ts = base_time + timedelta(minutes=2 * i)
        frac = i / 75.0

        reactor = round(85.0 + 1.5 * frac + 0.09 * math.sin(i * 0.8), 2)
        jacket = round(71.0 - 1.2 * frac + 0.07 * math.cos(i * 1.1), 2)

        pressure = round(2.44 + 0.02 * math.sin(i * 0.5), 2)
        flow_rate = round(145.0 + 0.5 * math.sin(i * 0.3), 1)
        pH = round(6.91 + 0.01 * math.sin(i * 1.3), 2)
        agitator = round(300.0 + 0.6 * math.sin(i * 0.9), 2)
        feed_a = round(25.3 + 0.2 * math.sin(i * 0.6), 1)
        feed_b = round(30.1 + 0.25 * math.sin(i * 0.7), 2)

        rows.append([
            ts.strftime("%Y-%m-%d %H:%M:%S"),
            reactor, jacket, pressure, flow_rate, pH, agitator, feed_a, feed_b,
        ])

    return rows


def generate_csv(output_path: str) -> None:
    header = [
        "timestamp", "reactor_temp", "jacket_temp", "pressure",
        "flow_rate", "pH", "agitator_rpm", "feed_A_kgph", "feed_B_kgph",
    ]
    all_rows = KNOWN_ROWS + generate_remaining_rows()
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(all_rows)
    print(f"Created: {output_path}  ({len(all_rows)} rows)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 1. Generate full 120-row CSV
    csv_path = os.path.join(DATA_DIR, "reactor_sensors.csv")
    generate_csv(csv_path)

    # 2. Create PDFs
    create_pdf(
        os.path.join(DOCS_DIR, "SOP12_Reactor_Temperature_Control.pdf"),
        "SOP-12: Reactor Temperature Control",
        SOP12_TEXT,
    )
    create_pdf(
        os.path.join(DOCS_DIR, "IncidentCaseStudy2019TempSpike.pdf"),
        "Incident Case Study - 2019 Temperature Spike",
        INCIDENT_TEXT,
    )

    print("\nSetup complete. Ready to run build_vectorstore.py")
