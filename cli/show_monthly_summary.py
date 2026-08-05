from __future__ import annotations

# CLI script for printing a calculated monthly summary.
# This is useful before building the Streamlit dashboard.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import parse_month
from src.reports.monthly_summary import build_monthly_summary


def main() -> None:
    month = parse_month(input("Month [YYYY-MM]: ").strip())
    summary = build_monthly_summary(month)

    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
