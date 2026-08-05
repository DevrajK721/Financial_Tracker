from __future__ import annotations

# CLI script for adding one account from the terminal.
# This is your first command-line workflow.
# It should ask the user for account details, create Account(...),
# add it to the database session, and commit automatically.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db import session_scope
from src.models.account import Account
from src.account_types import account_type_label
from cli.helpers import ask_account_type, ask_currency, ask_yes_no


def main() -> None:
    name = input("Account name: ").strip()
    account_type = ask_account_type()
    currency = ask_currency(default="GBP")

    is_emergency_fund = ask_yes_no("Is this an emergency fund?")
    account = Account(
        name=name,
        account_type=account_type,
        currency=currency,
        is_emergency_fund=is_emergency_fund,
    )
    with session_scope() as session:
        session.add(account)
        # The session will automatically commit or rollback when the context manager exits. 

    print(f"Added {name} ({account_type_label(account_type)}) in {currency}.")


if __name__ == "__main__":
    main()
