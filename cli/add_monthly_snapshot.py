from __future__ import annotations

# CLI script for entering one account balance for one month.
# Example: Monzo end balance for 2026-08-01.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import VALID_SNAPSHOT_TYPES, ask_account_id, ask_choice, ask_decimal, ask_month
from src.db import session_scope
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot


def main() -> None:
    with session_scope() as session:
        account_id = ask_account_id(session)
        if account_id is None:
            return

        month = ask_month()
        snapshot_type = ask_choice("Snapshot type", VALID_SNAPSHOT_TYPES)
        balance = ask_decimal("Balance: ")

        snapshot = MonthlyAccountSnapshot(
            account_id=account_id,
            month=month,
            balance=balance,
            snapshot_type=snapshot_type,
        )

        session.add(snapshot)

    print("Monthly account snapshot added.")


if __name__ == "__main__":
    main()
