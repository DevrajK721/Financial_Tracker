from __future__ import annotations

# Debt analytics should explain how debts are changing over time.
# Start simple: current balance, previous balance, and monthly change.

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from src.db import session_scope
from src.models.account import Account
from src.models.debt_profile import DebtProfile
from src.services.fx import convert_to_gbp
from src.services.snapshot_balances import MonthlyAccountBalance, monthly_account_balances
from src.services.spending_baseline import previous_months
from src.services.projections import project_total_debt


def calculate_total_debt(month: date) -> Decimal:
    """Sum monthly debt balances."""
    return calculate_debt_summary(month)["total_debt"]


def debt_balances_for_month(month: date) -> list[MonthlyAccountBalance]:
    """Return monthly balances that should be treated as debts."""
    return [balance for balance in monthly_account_balances(month) if balance.is_debt]


def calculate_debt_summary(month: date) -> dict[str, Decimal]:
    """Return simple debt totals and month-on-month debt movement."""
    previous_month = previous_months(month, 1)[0]

    current_rows = debt_balances_for_month(month)
    previous_rows = debt_balances_for_month(previous_month)

    with session_scope() as session:
        profiles = session.scalars(select(DebtProfile)).all()
        accounts = session.scalars(select(Account)).all()

    total_debt = sum((balance.balance for balance in current_rows), Decimal("0.00"))
    previous_total_debt = sum((balance.balance for balance in previous_rows), Decimal("0.00"))
    currencies = {account.id: account.currency for account in accounts}
    minimum_payments = sum(
        (
            convert_to_gbp(
                profile.minimum_payment or Decimal("0.00"),
                currencies.get(profile.account_id, "GBP"),
            ).gbp_amount
            for profile in profiles
        ),
        Decimal("0.00"),
    )

    return {
        "total_debt": total_debt,
        "previous_total_debt": previous_total_debt,
        "debt_change": total_debt - previous_total_debt,
        "minimum_payments": minimum_payments,
    }


def estimate_debt_payoff(month: date) -> dict[str, dict[str, Decimal | int]]:
    """Estimate payoff months for each debt using simple monthly compounding."""
    with session_scope() as session:
        profiles = session.scalars(select(DebtProfile)).all()
        accounts = session.scalars(select(Account)).all()

    rows = debt_balances_for_month(month)
    profiles_by_account = {profile.account_id: profile for profile in profiles}
    currencies = {account.id: account.currency for account in accounts}
    payoff: dict[str, dict[str, Decimal | int]] = {}

    for balance in rows:
        profile = profiles_by_account.get(balance.account_id)
        if profile is None:
            payoff[balance.account_name] = {
                "balance": balance.balance,
                "monthly_interest_estimate": Decimal("0.00"),
                "minimum_payment": Decimal("0.00"),
                "payoff_months": -1,
            }
            continue

        monthly_rate = (profile.interest_rate / Decimal("100")) / Decimal("12")
        monthly_interest = balance.balance * monthly_rate
        minimum_payment = convert_to_gbp(
            profile.minimum_payment or Decimal("0.00"),
            currencies.get(profile.account_id, "GBP"),
        ).gbp_amount
        payoff_months = estimate_payoff_months(balance.balance, monthly_rate, minimum_payment)

        payoff[balance.account_name] = {
            "balance": balance.balance,
            "monthly_interest_estimate": monthly_interest,
            "minimum_payment": minimum_payment,
            "payoff_months": payoff_months,
        }

    return payoff


def estimate_payoff_months(balance: Decimal, monthly_rate: Decimal, monthly_payment: Decimal) -> int:
    """Return months to repay, or -1 when the payment will not clear the debt."""
    if balance <= 0:
        return 0
    if monthly_payment <= 0:
        return -1
    if monthly_payment <= balance * monthly_rate:
        return -1

    remaining = balance
    months = 0
    while remaining > 0 and months < 1200:
        remaining = (remaining * (Decimal("1") + monthly_rate)) - monthly_payment
        months += 1

    return months if remaining <= 0 else -1


def project_debt_balance(month: date, months_forward: int = 12) -> list[dict[str, Decimal | str]]:
    """Project total debt using the same logic as net-worth projections."""
    return project_total_debt(month, months_forward)
