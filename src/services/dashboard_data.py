from __future__ import annotations

# Query helpers used by the Streamlit dashboard.
# Keeping these outside the app file makes the dashboard mostly presentation code.

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from src.db import session_scope
from src.models.account import Account
from src.models.goal import Goal
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_income import MonthlyIncome
from src.models.monthly_transfer import MonthlyTransfer
from src.models.subscription import Subscription
from src.services.fx import convert_to_gbp
from src.services.net_worth import calculate_net_worth_details
from src.services.snapshot_balances import monthly_account_balances


def money_float(value: Decimal | int | float | None) -> float:
    """Convert Decimal values to floats for charting."""
    return 0.0 if value is None else float(value)


def available_months() -> list[date]:
    """Return months that have any monthly records."""
    with session_scope() as session:
        months = {
            *session.scalars(select(MonthlyAccountSnapshot.month)).all(),
            *session.scalars(select(MonthlyIncome.month)).all(),
            *session.scalars(select(MonthlyExpense.month)).all(),
            *session.scalars(select(MonthlyTransfer.month)).all(),
        }

    return sorted(months)


def account_balances(month: date) -> list[dict]:
    """Return one current balance per account, converted to GBP for totals."""
    return [
        {
            "account": balance.account_name,
            "type": balance.account_type,
            "currency": balance.currency,
            "native_balance": money_float(balance.native_balance),
            "balance": money_float(balance.balance),
            "fx_rate_to_gbp": money_float(balance.fx_rate_to_gbp),
            "fx_rate_date": balance.fx_rate_date,
            "snapshot_type": balance.snapshot_type,
            "is_debt": balance.is_debt,
            "is_emergency_fund": balance.is_emergency_fund,
        }
        for balance in monthly_account_balances(month)
    ]


def account_currencies() -> dict[int, str]:
    """Return account currency codes by account id."""
    with session_scope() as session:
        accounts = session.scalars(select(Account)).all()
    return {account.id: account.currency for account in accounts}


def expense_breakdown(month: date) -> list[dict]:
    """Return current month expenses by category, converted to GBP."""
    with session_scope() as session:
        expenses = session.scalars(select(MonthlyExpense).where(MonthlyExpense.month == month)).all()

    currencies = account_currencies()
    totals: dict[str, Decimal] = {}
    for expense in expenses:
        amount = convert_to_gbp(expense.amount, currencies.get(expense.source_account_id, "GBP")).gbp_amount
        totals[expense.category] = totals.get(expense.category, Decimal("0.00")) + amount

    return [{"category": category, "amount": money_float(amount)} for category, amount in sorted(totals.items())]


def active_subscriptions() -> list[dict]:
    """Return active subscriptions."""
    with session_scope() as session:
        subscriptions = session.scalars(
            select(Subscription).where(Subscription.is_active.is_(True)).order_by(Subscription.name)
        ).all()

    return [
        {
            "name": subscription.name,
            "amount": money_float(subscription.monthly_amount),
            "frequency": subscription.billing_frequency,
            "category": subscription.category,
            "next_payment_date": subscription.next_payment_date.isoformat() if subscription.next_payment_date else "",
        }
        for subscription in subscriptions
    ]


def active_goals() -> list[dict]:
    """Return active goals."""
    with session_scope() as session:
        goals = session.scalars(select(Goal).where(Goal.is_active.is_(True)).order_by(Goal.name)).all()

    return [
        {
            "name": goal.name,
            "target_amount": money_float(goal.target_amount),
            "target_date": goal.target_date.isoformat() if goal.target_date else "",
        }
        for goal in goals
    ]


def net_worth_history() -> list[dict]:
    """Return net worth, assets, and debts for every available month."""
    rows = []
    for month in available_months():
        details = calculate_net_worth_details(month)
        rows.append(
            {
                "month": month.isoformat(),
                "net_worth": money_float(details["net_worth"]),
                "assets": money_float(details["total_assets"]),
                "debts": money_float(details["total_debts"]),
            }
        )
    return rows


def debt_history() -> list[dict]:
    """Return debt totals over time."""
    return [
        {"month": row["month"], "debt": row["debts"]}
        for row in net_worth_history()
        if row["debts"] > 0
    ]


def spending_history() -> list[dict]:
    """Return monthly total spending over time, converted to GBP."""
    with session_scope() as session:
        expenses = session.scalars(select(MonthlyExpense)).all()

    currencies = account_currencies()
    totals: dict[date, Decimal] = {}
    for expense in expenses:
        amount = convert_to_gbp(expense.amount, currencies.get(expense.source_account_id, "GBP")).gbp_amount
        totals[expense.month] = totals.get(expense.month, Decimal("0.00")) + amount

    return [
        {"month": month.isoformat(), "spending": money_float(amount)}
        for month, amount in sorted(totals.items())
    ]


def spending_by_category_history() -> list[dict]:
    """Return category spending over time, converted to GBP."""
    with session_scope() as session:
        expenses = session.scalars(select(MonthlyExpense)).all()

    currencies = account_currencies()
    totals: dict[tuple[date, str], Decimal] = {}
    for expense in expenses:
        key = (expense.month, expense.category)
        amount = convert_to_gbp(expense.amount, currencies.get(expense.source_account_id, "GBP")).gbp_amount
        totals[key] = totals.get(key, Decimal("0.00")) + amount

    return [
        {"month": month.isoformat(), "category": category, "amount": money_float(amount)}
        for (month, category), amount in sorted(totals.items())
    ]
