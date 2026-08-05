from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.db import session_scope
from src.models.account import Account
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_income import MonthlyIncome
from src.services.projections import average_monthly_savings, project_net_worth


def test_average_savings_and_net_worth_projection() -> None:
    current_month = date(2026, 8, 1)
    previous_month = date(2026, 7, 1)

    with session_scope() as session:
        account = Account(name="Monzo", account_type="bank", currency="GBP")
        session.add(account)
        session.flush()

        session.add_all(
            [
                MonthlyIncome(
                    month=previous_month,
                    income_type="salary",
                    label="Salary",
                    gross_amount=Decimal("3000.00"),
                    net_amount=Decimal("2400.00"),
                    target_account_id=account.id,
                ),
                MonthlyExpense(
                    month=previous_month,
                    category="rent",
                    amount=Decimal("1000.00"),
                    source_account_id=account.id,
                ),
                MonthlyAccountSnapshot(
                    account_id=account.id,
                    month=current_month,
                    balance=Decimal("5000.00"),
                    snapshot_type="end",
                ),
            ]
        )

    assert average_monthly_savings(current_month, lookback_months=1) == Decimal("1400.00")
    projection = project_net_worth(current_month, months_forward=2)
    assert projection[0]["projected_net_worth"] == Decimal("6400.00")
    assert projection[1]["projected_net_worth"] == Decimal("7800.00")
