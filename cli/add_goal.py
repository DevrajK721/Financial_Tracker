from __future__ import annotations

# CLI script for adding a savings goal.
# The actual money is allocated later from a real account.

import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import ask_decimal
from src.db import session_scope
from src.models.goal import Goal


def parse_optional_date(date_text: str) -> date | None:
    """Convert YYYY-MM-DD text into a date, or None if blank."""
    return None if not date_text else date.fromisoformat(date_text)


def main() -> None:
    name = input("Goal name: ").strip()
    target_amount = ask_decimal("Target amount: ")
    target_date = parse_optional_date(input("Target date [YYYY-MM-DD, optional]: ").strip())

    goal = Goal(
        name=name,
        target_amount=target_amount,
        target_date=target_date,
    )

    with session_scope() as session:
        session.add(goal)

    print("Goal added.")


if __name__ == "__main__":
    main()
