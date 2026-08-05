from __future__ import annotations

# CLI script for adding debt details.
# This also asks for the current debt balance and saves it as an end-of-month
# account snapshot, because debt charts are powered by monthly snapshots.

import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import ask_account_id, ask_decimal, ask_month, ask_optional_text
from src.db import session_scope
from src.models.account import Account
from src.models.debt_profile import DebtProfile
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot


def main() -> None:
    with session_scope() as session:
        account_id = ask_account_id(session, "Debt account ID: ")
        if account_id is None:
            return

        account = session.get(Account, account_id)
        if account is None or account.account_type != "debt":
            print("Please choose an account whose account type is Debt Account.")
            print("If needed, create one first with: .venv/bin/python finance.py add account")
            return

        debt_type = input("Debt type [student_loan/personal_debt]: ").strip().lower()
        month = ask_month("Balance month [YYYY-MM]: ")
        current_balance = ask_decimal("Current outstanding debt balance: ")
        interest_rate = ask_decimal("Annual interest rate %: ")
        minimum_payment_text = input("Minimum monthly payment / expected repayment [0 if none/flexible]: ").strip()
        minimum_payment = Decimal("0.00") if not minimum_payment_text else Decimal(minimum_payment_text)
        notes = ask_optional_text("Notes [optional]: ")

        debt_profile = session.scalars(select(DebtProfile).where(DebtProfile.account_id == account_id)).first()
        if debt_profile is None:
            debt_profile = DebtProfile(account_id=account_id)
            session.add(debt_profile)

        debt_profile.debt_type = debt_type
        debt_profile.interest_rate = interest_rate
        debt_profile.minimum_payment = minimum_payment
        debt_profile.notes = notes

        snapshot = session.scalars(
            select(MonthlyAccountSnapshot)
            .where(MonthlyAccountSnapshot.account_id == account_id)
            .where(MonthlyAccountSnapshot.month == month)
            .where(MonthlyAccountSnapshot.snapshot_type == "end")
        ).first()
        if snapshot is None:
            session.add(
                MonthlyAccountSnapshot(
                    account_id=account_id,
                    month=month,
                    snapshot_type="end",
                    balance=current_balance,
                )
            )
        else:
            snapshot.balance = current_balance

    print("Debt profile and current balance saved.")


if __name__ == "__main__":
    main()
