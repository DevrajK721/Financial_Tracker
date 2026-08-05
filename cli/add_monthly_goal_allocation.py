from __future__ import annotations

# CLI script for assigning part of an account balance to a goal for a month.
# Example: 800 in Cash ISA is allocated to "holiday" for 2026-08.

import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import ask_account_id, ask_decimal, ask_month
from src.db import session_scope
from src.models.goal import Goal
from src.models.monthly_goal_allocation import MonthlyGoalAllocation


def main() -> None:
    with session_scope() as session:
        account_id = ask_account_id(session)
        goals = session.scalars(select(Goal).order_by(Goal.name)).all()

        if account_id is None:
            return

        if not goals:
            print("No goals found. Add a goal first with cli/add_goal.py.")
            return

        print("Goals:")
        for goal in goals:
            print(f"{goal.id}: {goal.name} (target {goal.target_amount})")

        month = ask_month()
        goal_id = int(input("Goal ID: "))
        allocated_amount = ask_decimal("Allocated amount: ")

        allocation = MonthlyGoalAllocation(
            month=month,
            goal_id=goal_id,
            account_id=account_id,
            allocated_amount=allocated_amount,
        )

        session.add(allocation)

    print("Monthly goal allocation added.")


if __name__ == "__main__":
    main()
