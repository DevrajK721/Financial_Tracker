from __future__ import annotations

# Generic delete command for correcting mistaken manual entries.
# Keep this small and explicit so deleting finance data stays intentional.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import ask_yes_no
from src.db import session_scope
from src.models.account import Account
from src.models.debt_profile import DebtProfile
from src.models.goal import Goal
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_goal_allocation import MonthlyGoalAllocation
from src.models.monthly_income import MonthlyIncome
from src.models.monthly_transfer import MonthlyTransfer
from src.models.subscription import Subscription


MODELS = {
    "account": Account,
    "snapshot": MonthlyAccountSnapshot,
    "income": MonthlyIncome,
    "expense": MonthlyExpense,
    "transfer": MonthlyTransfer,
    "debt_profile": DebtProfile,
    "goal": Goal,
    "goal_allocation": MonthlyGoalAllocation,
    "subscription": Subscription,
}


def main() -> None:
    print("Record types:")
    for record_type in sorted(MODELS):
        print(f"- {record_type}")

    record_type = input("Record type: ").strip().lower()
    model = MODELS.get(record_type)
    if model is None:
        print("Unknown record type.")
        return

    record_id = int(input("Record ID to delete: "))

    with session_scope() as session:
        record = session.get(model, record_id)
        if record is None:
            print("No matching record found.")
            return

        print(f"Found: {record!r}")
        if not ask_yes_no("Delete this record?"):
            print("Delete cancelled.")
            return

        session.delete(record)

    print("Record deleted.")


if __name__ == "__main__":
    main()
