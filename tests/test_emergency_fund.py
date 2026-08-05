from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.db import session_scope
from src.models.account import Account
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_expense import MonthlyExpense
from src.services.emergency_fund import calculate_emergency_fund_details


def test_emergency_fund_uses_emergency_accounts_and_core_expenses() -> None:
    current_month = date(2026, 8, 1)
    previous_month = date(2026, 7, 1)

    with session_scope() as session:
        emergency = Account(
            name="Emergency Savings",
            account_type="bank",
            currency="GBP",
            is_emergency_fund=True,
        )
        current = Account(name="Monzo", account_type="bank", currency="GBP")
        session.add_all([emergency, current])
        session.flush()

        session.add(
            MonthlyAccountSnapshot(
                account_id=emergency.id,
                month=current_month,
                balance=Decimal("3000.00"),
                snapshot_type="end",
            )
        )
        session.add_all(
            [
                MonthlyExpense(
                    month=previous_month,
                    category="rent",
                    amount=Decimal("1000.00"),
                    source_account_id=current.id,
                ),
                MonthlyExpense(
                    month=previous_month,
                    category="clothing",
                    amount=Decimal("200.00"),
                    source_account_id=current.id,
                ),
            ]
        )

    details = calculate_emergency_fund_details(current_month, lookback_months=1)

    assert details["emergency_fund_balance"] == Decimal("3000.00")
    assert details["average_core_expenses"] == Decimal("1000.00")
    assert details["emergency_fund_months"] == Decimal("3")
