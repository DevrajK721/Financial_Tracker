from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.account_types import ACCOUNT_TYPE_LABELS, GROWTH_ACCOUNT_TYPES
from src.db import session_scope
from src.models.account import Account
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_transfer import MonthlyTransfer
from src.services.investment_attribution import estimate_investment_growth


def test_lisa_and_high_interest_savings_are_supported_account_types() -> None:
    assert ACCOUNT_TYPE_LABELS["lifetime_isa"] == "Lifetime ISA"
    assert ACCOUNT_TYPE_LABELS["high_interest_savings"] == "High-Interest Savings Account"
    assert "lifetime_isa" in GROWTH_ACCOUNT_TYPES
    assert "high_interest_savings" in GROWTH_ACCOUNT_TYPES


def test_growth_attribution_includes_lisa_and_high_interest_savings() -> None:
    month = date(2026, 8, 1)

    with session_scope() as session:
        lisa = Account(name="Moneybox LISA", account_type="lifetime_isa", currency="GBP")
        savings = Account(name="Marcus Saver", account_type="high_interest_savings", currency="GBP")
        current = Account(name="Monzo", account_type="bank", currency="GBP")
        session.add_all([lisa, savings, current])
        session.flush()

        session.add_all(
            [
                MonthlyAccountSnapshot(
                    account_id=lisa.id,
                    month=month,
                    snapshot_type="start",
                    balance=Decimal("1000.00"),
                ),
                MonthlyAccountSnapshot(
                    account_id=lisa.id,
                    month=month,
                    snapshot_type="end",
                    balance=Decimal("1300.00"),
                ),
                MonthlyAccountSnapshot(
                    account_id=savings.id,
                    month=month,
                    snapshot_type="start",
                    balance=Decimal("5000.00"),
                ),
                MonthlyAccountSnapshot(
                    account_id=savings.id,
                    month=month,
                    snapshot_type="end",
                    balance=Decimal("5025.00"),
                ),
                MonthlyTransfer(
                    month=month,
                    from_account_id=current.id,
                    to_account_id=lisa.id,
                    amount=Decimal("200.00"),
                    label="LISA contribution",
                ),
            ]
        )

    growth = estimate_investment_growth(month)

    assert growth["Moneybox LISA"] == Decimal("100.00")
    assert growth["Marcus Saver"] == Decimal("25.00")
