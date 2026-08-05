from __future__ import annotations

# CLI script for entering one monthly expense category total.
# Example: August food spending = 250.00.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import VALID_EXPENSE_CATEGORIES, ask_account_id, ask_choice, ask_decimal, ask_month
from src.db import session_scope
from src.models.monthly_expense import MonthlyExpense


def main() -> None:
    with session_scope() as session:
        source_account_id = ask_account_id(session, "Source account ID: ")
        if source_account_id is None:
            return

        month = ask_month()
        category = ask_choice("Category", VALID_EXPENSE_CATEGORIES)
        amount = ask_decimal("Amount: ")

        expense = MonthlyExpense(
            month=month,
            category=category,
            amount=amount,
            source_account_id=source_account_id,
        )

        session.add(expense)

    print("Monthly expense added.")


if __name__ == "__main__":
    main()
