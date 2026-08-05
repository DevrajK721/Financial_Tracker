from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.db import session_scope
from src.models.account import Account
from src.models.debt_profile import DebtProfile
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.services.debt_analytics import calculate_debt_summary, estimate_debt_payoff


def test_debt_summary_treats_missing_minimum_payment_as_zero() -> None:
    month = date(2026, 8, 1)

    with session_scope() as session:
        debt = Account(name="Student Loan", account_type="debt", currency="GBP")
        session.add(debt)
        session.flush()

        session.add(
            MonthlyAccountSnapshot(
                account_id=debt.id,
                month=month,
                balance=Decimal("5000.00"),
                snapshot_type="end",
            )
        )
        session.add(
            DebtProfile(
                account_id=debt.id,
                debt_type="student_loan",
                interest_rate=Decimal("7.90"),
                minimum_payment=None,
                notes=None,
            )
        )

    summary = calculate_debt_summary(month)
    payoff = estimate_debt_payoff(month)

    assert summary["total_debt"] == Decimal("5000.00")
    assert summary["minimum_payments"] == Decimal("0.00")
    assert payoff["Student Loan"]["minimum_payment"] == Decimal("0.00")
    assert payoff["Student Loan"]["payoff_months"] == -1
