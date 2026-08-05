from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.db import session_scope
from src.models.account import Account
from src.models.monthly_expense import MonthlyExpense
from src.services.spending_baseline import compare_spending_to_baseline


def test_spending_baseline_compares_current_to_previous_median() -> None:
    with session_scope() as session:
        account = Account(name="Monzo", account_type="bank", currency="GBP")
        session.add(account)
        session.flush()

        session.add_all(
            [
                MonthlyExpense(
                    month=date(2026, 6, 1),
                    category="food",
                    amount=Decimal("200.00"),
                    source_account_id=account.id,
                ),
                MonthlyExpense(
                    month=date(2026, 7, 1),
                    category="food",
                    amount=Decimal("300.00"),
                    source_account_id=account.id,
                ),
                MonthlyExpense(
                    month=date(2026, 8, 1),
                    category="food",
                    amount=Decimal("350.00"),
                    source_account_id=account.id,
                ),
            ]
        )

    comparison = compare_spending_to_baseline(date(2026, 8, 1), lookback_months=2)

    assert comparison["food"]["baseline"] == Decimal("250.00")
    assert comparison["food"]["difference"] == Decimal("100.00")
