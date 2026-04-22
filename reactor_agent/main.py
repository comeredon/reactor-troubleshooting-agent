"""
CLI entry point for the Reactor Troubleshooting Agent.

Usage:
    python main.py \\
        --csv data/reactor_sensors.csv \\
        --docs-dir docs/ \\
        --provider groq \\
        [--model llama-3.1-70b-versatile] \\
        [--rebuild-index]
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime, timezone

# Load .env before anything else
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv optional; env vars can be set manually

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reactor 220B Troubleshooting Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--csv",
        default=os.path.join(BASE_DIR, "data", "reactor_sensors.csv"),
        help="Path to sensor CSV (default: data/reactor_sensors.csv)",
    )
    parser.add_argument(
        "--docs-dir",
        default=os.path.join(BASE_DIR, "docs"),
        help="Directory with .md/.pdf documentation (default: docs/)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(BASE_DIR, "output"),
        help="Directory for report.json and reasoning_log.json (default: output/)",
    )
    parser.add_argument(
        "--provider",
        default=os.getenv("LLM_PROVIDER", "groq"),
        choices=["groq", "openai", "anthropic", "ollama"],
        help="LLM provider (default: groq)",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", ""),
        help="Model override (empty = provider default)",
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Force rebuild of FAISS vector store",
    )
    return parser.parse_args()


def build_index_if_needed(args: argparse.Namespace) -> None:
    from config import FAISS_INDEX_PATH
    index_path = os.path.join(BASE_DIR, FAISS_INDEX_PATH)

    needs_build = args.rebuild_index or not os.path.isdir(index_path)
    if needs_build:
        print("Building vector store...")
        from execution.build_vectorstore import build_vectorstore
        build_vectorstore(args.docs_dir, index_path)
    else:
        print(f"Using existing vector store at: {index_path}")


def write_outputs(state: dict, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    df = state.get("sensor_data")
    anomalies = state.get("anomalies", [])

    # Sensor summary (serialisable)
    sensor_summary = {}
    if df is not None:
        try:
            peak_idx = df["reactor_temp"].idxmax()
            sensor_summary = {
                "total_rows": len(df),
                "time_range": {
                    "start": str(df["timestamp"].min()),
                    "end": str(df["timestamp"].max()),
                },
                "peak_temp_celsius": round(float(df["reactor_temp"].max()), 3),
                "peak_temp_timestamp": str(df.loc[peak_idx, "timestamp"]),
            }
        except Exception as exc:
            warnings.warn(f"Could not compute sensor summary: {exc}")

    # Anomaly counts by type
    by_type: dict = {}
    for a in anomalies:
        t = a.get("anomaly_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    report = {
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "csv_file": state.get("csv_path", ""),
        "provider": state.get("provider", ""),
        "model": state.get("model", ""),
        "sensor_summary": sensor_summary,
        "anomalies": {
            "total": len(anomalies),
            "by_type": by_type,
            "details": anomalies,
        },
        "root_cause_analysis": state.get("root_cause_analysis", ""),
        "recommendations": state.get("recommendations", ""),
        "errors": state.get("errors", []),
    }

    report_path = os.path.join(output_dir, "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Report written: {report_path}")

    log_path = os.path.join(output_dir, "reasoning_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(state.get("reasoning_log", []), f, indent=2, default=str)
    print(f"Reasoning log written: {log_path}")


def main() -> None:
    args = parse_args()

    print(f"\n{'='*60}")
    print("  Reactor 220B Troubleshooting Agent")
    print(f"{'='*60}")
    print(f"  CSV:      {args.csv}")
    print(f"  Docs:     {args.docs_dir}")
    print(f"  Provider: {args.provider}")
    print(f"  Output:   {args.output_dir}")
    print(f"{'='*60}\n")

    # Step 1: build FAISS index if needed
    build_index_if_needed(args)

    # Step 2: run LangGraph pipeline
    from orchestration.graph import app

    initial_state: dict = {
        "csv_path": args.csv,
        "docs_dir": args.docs_dir,
        "output_dir": args.output_dir,
        "provider": args.provider,
        "model": args.model,
        "rebuild_index": args.rebuild_index,
        "anomalies": [],
        "retrieved_chunks": [],
        "root_cause_analysis": "",
        "recommendations": "",
        "reasoning_log": [],
        "errors": [],
    }

    print("Running LangGraph pipeline...\n")
    try:
        final_state = app.invoke(initial_state)
    except Exception as exc:
        print(f"\nPipeline error: {exc}")
        sys.exit(1)

    # Step 3: write outputs
    write_outputs(final_state, args.output_dir)

    # Step 4: print summary
    anomalies = final_state.get("anomalies", [])
    by_type: dict = {}
    for a in anomalies:
        t = a.get("anomaly_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    print(f"\n{'='*60}")
    print(f"  SUMMARY: {len(anomalies)} anomalies detected")
    for t, c in sorted(by_type.items()):
        print(f"    {t}: {c}")
    errors = final_state.get("errors", [])
    if errors:
        print(f"\n  Warnings ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
