from __future__ import annotations

# CLI script for viewing accounts already stored in the database.

import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db import session_scope
from src.models.account import Account


def main() -> None:
    with session_scope() as session:
        accounts = session.scalars(select(Account).order_by(Account.name)).all()

    if not accounts:
        print("No accounts found.")
        return

    for account in accounts:
        print(
            f"{account.id}: {account.name} | "
            f"type={account.account_type} | "
            f"currency={account.currency} | "
            f"active={account.is_active} | "
            f"emergency_fund={account.is_emergency_fund}"
        )


if __name__ == "__main__":
    main()
