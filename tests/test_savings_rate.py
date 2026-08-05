from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.db import session_scope
from src.models.account import Account
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_income import MonthlyIncome
from src.services.savings_rate import calculate_savings_details


def test_savings_rate_uses_net_income_and_expenses() -> None:
    month = date(2026, 8, 1)

    with session_scope() as session:
        account = Account(name="Monzo", account_type="bank", currency="GBP")
        session.add(account)
        session.flush()

        session.add(
            MonthlyIncome(
                month=month,
                income_type="salary",
                label="Main salary",
                gross_amount=Decimal("3000"),
                net_amount=Decimal("2400"),
                target_account_id=account.id,
            )
        )
        session.add(
            MonthlyExpense(
                month=month,
                category="rent",
                amount=Decimal("800"),
                source_account_id=account.id,
            )
        )

    details = calculate_savings_details(month)

    assert details["total_net_income"] == Decimal("2400.00")
    assert details["total_expenses"] == Decimal("800.00")
    assert details["monthly_savings"] == Decimal("1600.00")
    assert details["savings_rate"] == Decimal("1600.00") / Decimal("2400.00")
