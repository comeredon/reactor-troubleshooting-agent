"""
Execution layer: load and validate sensor CSV data.
Returns a validated pandas DataFrame; raises on missing columns or empty data.
No LLM involvement.
"""

import os
import sys
import pandas as pd

# Allow running as a script from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import REQUIRED_COLUMNS


def load_sensor_data(csv_path: str) -> pd.DataFrame:
    """
    Load and validate the reactor sensor CSV.

    Parameters
    ----------
    csv_path : str
        Absolute or relative path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Validated DataFrame with a parsed datetime index.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    ValueError
        If required columns are missing or the file is empty.
    """
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Sensor CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError(f"Sensor CSV is empty: {csv_path}")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# CLI smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load and validate sensor CSV")
    parser.add_argument(
        "--csv",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "reactor_sensors.csv",
        ),
        help="Path to sensor CSV",
    )
    args = parser.parse_args()

    df = load_sensor_data(args.csv)
    print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")
    print(df.head(3))
    print(f"Time range: {df['timestamp'].min()} → {df['timestamp'].max()}")
