from __future__ import annotations

# CLI script for entering monthly transfers between your own accounts.
# Example: Monzo to Cash ISA = 500.00.
# Remember: transfers should not count as income or expenses.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import ask_account_id, ask_decimal, ask_month, ask_optional_text
from src.db import session_scope
from src.models.monthly_transfer import MonthlyTransfer


def main() -> None:
    with session_scope() as session:
        from_account_id = ask_account_id(session, "From account ID: ")
        if from_account_id is None:
            return
        to_account_id = ask_account_id(session, "To account ID: ")
        if to_account_id is None:
            return

        month = ask_month()
        amount = ask_decimal("Amount: ")
        label = ask_optional_text("Label [optional]: ")

        transfer = MonthlyTransfer(
            month=month,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            label=label,
        )

        session.add(transfer)

    print("Monthly transfer added.")


if __name__ == "__main__":
    main()
