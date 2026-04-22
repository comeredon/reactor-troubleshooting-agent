"""
Execution layer: deterministic anomaly detection against Reactor 220B thresholds.
No LLM involvement — pure Python threshold checks on the sensor DataFrame.
"""

import os
import sys
from dataclasses import dataclass, field
from typing import List

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import THRESHOLDS, SENSOR_INTERVAL_MIN


@dataclass
class Anomaly:
    anomaly_type: str   # e.g. "temp_alarm", "ramp_rate"
    timestamp: str      # ISO string from the sensor row
    value: float        # observed value that violated the threshold
    threshold: float    # threshold that was crossed
    message: str        # human-readable description

    def to_dict(self) -> dict:
        return {
            "anomaly_type": self.anomaly_type,
            "timestamp": self.timestamp,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
        }


def detect_anomalies(df: pd.DataFrame) -> List[Anomaly]:
    """
    Run all threshold checks on the sensor DataFrame and return a list of
    Anomaly instances.

    Checks performed (all deterministic, no LLM):
      1. Temperature alarm   (reactor_temp > temp_alarm)
      2. Temperature interlock (reactor_temp > temp_interlock)
      3. Ramp rate           (|ΔT/Δt| > ramp_rate_max °C/min)
      4. Agitator low RPM    (agitator_rpm < agitator_min)
      5. ΔT (reactor−jacket) > delta_t_max
      6. Feed B step change  (|Δfeed_B| > feed_b_step kg/h)
    """
    anomalies: List[Anomaly] = []

    temp_alarm = THRESHOLDS["temp_alarm"]
    temp_interlock = THRESHOLDS["temp_interlock"]
    ramp_max = THRESHOLDS["ramp_rate_max"]
    agitator_min = THRESHOLDS["agitator_min"]
    delta_t_max = THRESHOLDS["delta_t_max"]
    feed_b_step = THRESHOLDS["feed_b_step"]

    for i, row in df.iterrows():
        ts = str(row["timestamp"])
        reactor_t = float(row["reactor_temp"])
        jacket_t = float(row["jacket_temp"])
        agitator = float(row["agitator_rpm"])
        feed_b = float(row["feed_B_kgph"])

        # 1. Temperature alarm
        if reactor_t > temp_alarm:
            anomalies.append(Anomaly(
                anomaly_type="temp_alarm",
                timestamp=ts,
                value=round(reactor_t, 3),
                threshold=temp_alarm,
                message=(
                    f"Reactor temp {reactor_t:.2f}°C exceeds alarm threshold "
                    f"{temp_alarm}°C"
                ),
            ))

        # 2. Temperature interlock
        if reactor_t > temp_interlock:
            anomalies.append(Anomaly(
                anomaly_type="temp_interlock",
                timestamp=ts,
                value=round(reactor_t, 3),
                threshold=temp_interlock,
                message=(
                    f"Reactor temp {reactor_t:.2f}°C exceeds interlock threshold "
                    f"{temp_interlock}°C — TRP-12 required"
                ),
            ))

        # 3. Ramp rate (requires a previous row)
        if i > 0:
            prev_t = float(df.loc[i - 1, "reactor_temp"])
            ramp = (reactor_t - prev_t) / SENSOR_INTERVAL_MIN  # °C/min
            if abs(ramp) > ramp_max:
                anomalies.append(Anomaly(
                    anomaly_type="ramp_rate",
                    timestamp=ts,
                    value=round(ramp, 4),
                    threshold=ramp_max,
                    message=(
                        f"Ramp rate {ramp:.3f}°C/min exceeds limit "
                        f"±{ramp_max}°C/min"
                    ),
                ))

        # 4. Agitator RPM
        if agitator < agitator_min:
            anomalies.append(Anomaly(
                anomaly_type="agitator_low",
                timestamp=ts,
                value=round(agitator, 2),
                threshold=agitator_min,
                message=(
                    f"Agitator {agitator:.1f} RPM below minimum {agitator_min} RPM"
                ),
            ))

        # 5. Reactor−Jacket ΔT
        delta_t = reactor_t - jacket_t
        if delta_t > delta_t_max:
            anomalies.append(Anomaly(
                anomaly_type="delta_t",
                timestamp=ts,
                value=round(delta_t, 3),
                threshold=delta_t_max,
                message=(
                    f"ΔT (reactor−jacket) = {delta_t:.2f}°C exceeds max "
                    f"{delta_t_max}°C"
                ),
            ))

        # 6. Feed B step change
        if i > 0:
            prev_feed_b = float(df.loc[i - 1, "feed_B_kgph"])
            step = abs(feed_b - prev_feed_b)
            if step > feed_b_step:
                anomalies.append(Anomaly(
                    anomaly_type="feed_b_step",
                    timestamp=ts,
                    value=round(step, 3),
                    threshold=feed_b_step,
                    message=(
                        f"Feed B step change {step:.2f} kg/h "
                        f"(prev={prev_feed_b:.2f}, now={feed_b:.2f})"
                    ),
                ))

    return anomalies
