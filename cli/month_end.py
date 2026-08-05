from __future__ import annotations

# Guided month-end workflow.
# This is the friendliest terminal flow: pick a month, then add the core rows
# in the order you would naturally update a spreadsheet.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import (
    VALID_EXPENSE_CATEGORIES,
    VALID_SNAPSHOT_TYPES,
    ask_account_id,
    ask_choice,
    ask_decimal,
    ask_month,
    ask_optional_text,
    ask_yes_no,
)
from src.db import session_scope
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_income import MonthlyIncome
from src.models.monthly_transfer import MonthlyTransfer
from src.reports.monthly_summary import build_monthly_summary


def add_snapshots(month) -> None:
    while ask_yes_no("Add an account balance snapshot?"):
        with session_scope() as session:
            account_id = ask_account_id(session)
            if account_id is None:
                return
            snapshot = MonthlyAccountSnapshot(
                account_id=account_id,
                month=month,
                snapshot_type=ask_choice("Snapshot type", VALID_SNAPSHOT_TYPES),
                balance=ask_decimal("Balance: "),
            )
            session.add(snapshot)
        print("Snapshot added.")


def add_income(month) -> None:
    while ask_yes_no("Add non-salary income?"):
        with session_scope() as session:
            target_account_id = ask_account_id(session, "Target account ID: ")
            if target_account_id is None:
                return
            income = MonthlyIncome(
                month=month,
                income_type=input("Income type [bonus/family_support/other]: ").strip().lower(),
                label=ask_optional_text("Label [optional]: "),
                gross_amount=ask_decimal("Gross amount: "),
                net_amount=ask_decimal("Net amount: "),
                target_account_id=target_account_id,
            )
            session.add(income)
        print("Income added.")


def add_expenses(month) -> None:
    while ask_yes_no("Add an expense category total?"):
        with session_scope() as session:
            source_account_id = ask_account_id(session, "Source account ID: ")
            if source_account_id is None:
                return
            expense = MonthlyExpense(
                month=month,
                category=ask_choice("Category", VALID_EXPENSE_CATEGORIES),
                amount=ask_decimal("Amount: "),
                source_account_id=source_account_id,
            )
            session.add(expense)
        print("Expense added.")


def add_transfers(month) -> None:
    while ask_yes_no("Add a transfer between accounts?"):
        with session_scope() as session:
            from_account_id = ask_account_id(session, "From account ID: ")
            if from_account_id is None:
                return
            to_account_id = ask_account_id(session, "To account ID: ")
            if to_account_id is None:
                return
            transfer = MonthlyTransfer(
                month=month,
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                amount=ask_decimal("Amount: "),
                label=ask_optional_text("Label [optional]: "),
            )
            session.add(transfer)
        print("Transfer added.")


def main() -> None:
    month = ask_month()
    print(f"Starting month-end entry for {month.isoformat()}.")

    add_snapshots(month)
    add_income(month)
    add_expenses(month)
    add_transfers(month)

    print("\nMonth-end summary:")
    summary = build_monthly_summary(month)
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
