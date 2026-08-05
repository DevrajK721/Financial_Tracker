from __future__ import annotations

# Focused edit command for account details.
# Most monthly records are easier to delete and re-add; accounts are worth editing.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import ask_account_id, ask_account_type, ask_yes_no
from src.db import session_scope
from src.models.account import Account


def main() -> None:
    with session_scope() as session:
        account_id = ask_account_id(session)
        if account_id is None:
            return

        account = session.get(Account, account_id)
        if account is None:
            print("Account not found.")
            return

        print("Leave a field blank to keep the current value.")
        name = input(f"Name [{account.name}]: ").strip()
        currency = input(f"Currency [{account.currency}]: ").strip().upper()

        if ask_yes_no("Change account type?"):
            account.account_type = ask_account_type()
        if name:
            account.name = name
        if currency:
            account.currency = currency

        account.is_active = ask_yes_no("Is this account active?", default=account.is_active)
        account.is_emergency_fund = ask_yes_no(
            "Is this an emergency fund?",
            default=account.is_emergency_fund,
        )

    print("Account updated.")


if __name__ == "__main__":
    main()
