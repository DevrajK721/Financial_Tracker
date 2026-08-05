from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.account_types import ACCOUNT_TYPE_LABELS, GROWTH_ACCOUNT_TYPES
from src.db import session_scope
from src.models.account import Account
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_transfer import MonthlyTransfer
from src.services.investment_attribution import (
    estimate_investment_growth,
    investment_account_history,
    investment_contribution_events,
    project_investment_balances,
)


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


def test_investment_history_separates_contributions_from_performance() -> None:
    month = date(2026, 8, 1)

    with session_scope() as session:
        isa = Account(name="Stocks ISA", account_type="stocks_isa", currency="GBP")
        current = Account(name="Current Account", account_type="bank", currency="GBP")
        session.add_all([isa, current])
        session.flush()

        session.add_all(
            [
                MonthlyAccountSnapshot(
                    account_id=isa.id,
                    month=month,
                    snapshot_type="start",
                    balance=Decimal("1000.00"),
                ),
                MonthlyAccountSnapshot(
                    account_id=isa.id,
                    month=month,
                    snapshot_type="end",
                    balance=Decimal("1250.00"),
                ),
                MonthlyTransfer(
                    month=month,
                    from_account_id=current.id,
                    to_account_id=isa.id,
                    amount=Decimal("200.00"),
                    label="ISA contribution",
                ),
            ]
        )

    history = investment_account_history()
    events = investment_contribution_events()
    projection = project_investment_balances(month, months_forward=1, lookback_months=1)

    isa_row = next(row for row in history if row["account"] == "Stocks ISA")
    assert isa_row["net_contributions"] == Decimal("200.00")
    assert isa_row["performance_growth"] == Decimal("50.00")
    assert isa_row["has_contribution"] is True
    assert events[0]["event_type"] == "Contribution"
    assert events[0]["amount"] == Decimal("200.00")
    assert projection[0]["projected_balance"] == Decimal("1500.00")
    assert projection[0]["performance_only_balance"] == Decimal("1300.00")
