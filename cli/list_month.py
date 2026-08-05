from __future__ import annotations

# CLI script for viewing the raw monthly rows entered for one month.

import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import parse_month
from src.db import session_scope
from src.models.account import Account
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_income import MonthlyIncome
from src.models.monthly_transfer import MonthlyTransfer


def main() -> None:
    month = parse_month(input("Month [YYYY-MM]: ").strip())

    with session_scope() as session:
        accounts_by_id = {account.id: account for account in session.scalars(select(Account)).all()}
        snapshots = session.scalars(
            select(MonthlyAccountSnapshot)
            .where(MonthlyAccountSnapshot.month == month)
            .order_by(MonthlyAccountSnapshot.account_id, MonthlyAccountSnapshot.snapshot_type)
        ).all()
        incomes = session.scalars(select(MonthlyIncome).where(MonthlyIncome.month == month)).all()
        expenses = session.scalars(select(MonthlyExpense).where(MonthlyExpense.month == month)).all()
        transfers = session.scalars(select(MonthlyTransfer).where(MonthlyTransfer.month == month)).all()

    print("Snapshots:")
    for snapshot in snapshots:
        account = accounts_by_id.get(snapshot.account_id)
        account_name = account.name if account else f"account {snapshot.account_id}"
        print(f"{account_name} | {snapshot.snapshot_type} | {snapshot.balance}")

    print("\nIncome:")
    for income in incomes:
        account = accounts_by_id.get(income.target_account_id)
        account_name = account.name if account else f"account {income.target_account_id}"
        print(f"{income.income_type} | {income.label or ''} | net={income.net_amount} | to={account_name}")

    print("\nExpenses:")
    for expense in expenses:
        account = accounts_by_id.get(expense.source_account_id)
        account_name = account.name if account else f"account {expense.source_account_id}"
        print(f"{expense.category} | {expense.amount} | from={account_name}")

    print("\nTransfers:")
    for transfer in transfers:
        from_account = accounts_by_id.get(transfer.from_account_id)
        to_account = accounts_by_id.get(transfer.to_account_id)
        from_name = from_account.name if from_account else f"account {transfer.from_account_id}"
        to_name = to_account.name if to_account else f"account {transfer.to_account_id}"
        print(f"{from_name} -> {to_name} | {transfer.amount} | {transfer.label or ''}")


if __name__ == "__main__":
    main()
