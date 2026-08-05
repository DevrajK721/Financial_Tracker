from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.db import session_scope
from src.models.account import Account
from src.models.debt_profile import DebtProfile
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.services.dashboard_data import account_balances
from src.services.net_worth import calculate_net_worth_details


def test_net_worth_subtracts_debts() -> None:
    month = date(2026, 8, 1)

    with session_scope() as session:
        bank = Account(name="Monzo", account_type="bank", currency="GBP")
        debt = Account(name="Student Loan", account_type="debt", currency="GBP")
        session.add_all([bank, debt])
        session.flush()

        session.add_all(
            [
                MonthlyAccountSnapshot(
                    account_id=bank.id,
                    month=month,
                    balance=Decimal("1250.75"),
                    snapshot_type="end",
                ),
                MonthlyAccountSnapshot(
                    account_id=debt.id,
                    month=month,
                    balance=Decimal("5000.00"),
                    snapshot_type="end",
                ),
            ]
        )

    details = calculate_net_worth_details(month)

    assert details["total_assets"] == Decimal("1250.75")
    assert details["total_debts"] == Decimal("5000.00")
    assert details["net_worth"] == Decimal("-3749.25")


def test_net_worth_uses_start_snapshot_when_end_snapshot_is_missing() -> None:
    month = date(2026, 8, 1)

    with session_scope() as session:
        bank = Account(name="Monzo", account_type="bank", currency="GBP")
        session.add(bank)
        session.flush()
        session.add(
            MonthlyAccountSnapshot(
                account_id=bank.id,
                month=month,
                balance=Decimal("178.93"),
                snapshot_type="start",
            )
        )

    details = calculate_net_worth_details(month)
    balances = account_balances(month)

    assert details["total_assets"] == Decimal("178.93")
    assert details["net_worth"] == Decimal("178.93")
    assert balances[0]["snapshot_type"] == "start"


def test_net_worth_treats_debt_profile_account_as_debt_even_if_account_type_is_wrong() -> None:
    month = date(2026, 8, 1)

    with session_scope() as session:
        account = Account(name="Student Loan", account_type="bank", currency="GBP")
        session.add(account)
        session.flush()
        session.add_all(
            [
                DebtProfile(
                    account_id=account.id,
                    debt_type="student_loan",
                    interest_rate=Decimal("6.20"),
                    minimum_payment=Decimal("0.00"),
                    notes=None,
                ),
                MonthlyAccountSnapshot(
                    account_id=account.id,
                    month=month,
                    balance=Decimal("10000.00"),
                    snapshot_type="end",
                ),
            ]
        )

    details = calculate_net_worth_details(month)
    balances = account_balances(month)

    assert details["total_assets"] == Decimal("0.00")
    assert details["total_debts"] == Decimal("10000.00")
    assert details["net_worth"] == Decimal("-10000.00")
    assert balances[0]["is_debt"] is True
