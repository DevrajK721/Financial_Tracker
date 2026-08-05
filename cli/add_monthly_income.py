from __future__ import annotations

# CLI script for entering one monthly income row.
# Example: August salary, gross amount, net amount, target account.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import VALID_INCOME_TYPES, ask_account_id, ask_choice, ask_decimal, ask_month, ask_optional_text
from src.db import session_scope
from src.models.monthly_income import MonthlyIncome


def main() -> None:
    with session_scope() as session:
        target_account_id = ask_account_id(session, "Target account ID: ")
        if target_account_id is None:
            return

        month = ask_month()
        income_type = ask_choice("Income type", VALID_INCOME_TYPES)
        label = ask_optional_text("Label [optional]: ")
        gross_amount = ask_decimal("Gross amount: ")
        net_amount = ask_decimal("Net amount: ")

        income = MonthlyIncome(
            month=month,
            income_type=income_type,
            label=label,
            gross_amount=gross_amount,
            net_amount=net_amount,
            target_account_id=target_account_id,
        )

        session.add(income)

    print("Monthly income added.")


if __name__ == "__main__":
    main()
