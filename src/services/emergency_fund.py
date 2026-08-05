from __future__ import annotations

# Emergency fund coverage measures how many months of core expenses are covered.
# Core expenses usually include rent, food, transport, phone, and essential bills.

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from src.db import session_scope
from src.models.account import Account
from src.models.monthly_expense import MonthlyExpense
from src.services.fx import convert_to_gbp
from src.services.snapshot_balances import monthly_account_balances
from src.services.spending_baseline import previous_months


CORE_EXPENSE_CATEGORIES = {"rent", "food", "transport", "phone", "subscriptions"}


def calculate_emergency_fund_months(month: date) -> Decimal:
    """Return how many months of core expenses are covered by emergency-fund accounts."""
    return calculate_emergency_fund_details(month)["emergency_fund_months"]


def calculate_emergency_fund_details(month: date, lookback_months: int = 6) -> dict[str, Decimal]:
    """Return emergency fund balance, average core expenses, and coverage months."""
    months = previous_months(month, lookback_months)

    with session_scope() as session:
        core_expenses = session.scalars(
            select(MonthlyExpense)
            .where(MonthlyExpense.month.in_(months))
            .where(MonthlyExpense.category.in_(CORE_EXPENSE_CATEGORIES))
        ).all()
        accounts = session.scalars(select(Account)).all()

    emergency_fund_balance = sum(
        (balance.balance for balance in monthly_account_balances(month) if balance.is_emergency_fund),
        Decimal("0.00"),
    )
    currencies = {account.id: account.currency for account in accounts}
    total_core_expenses = sum(
        (
            convert_to_gbp(expense.amount, currencies.get(expense.source_account_id, "GBP")).gbp_amount
            for expense in core_expenses
        ),
        Decimal("0.00"),
    )
    average_core_expenses = Decimal("0.00")
    if months:
        average_core_expenses = total_core_expenses / Decimal(len(months))

    emergency_fund_months = Decimal("0.00")
    if average_core_expenses:
        emergency_fund_months = emergency_fund_balance / average_core_expenses

    return {
        "emergency_fund_balance": emergency_fund_balance,
        "average_core_expenses": average_core_expenses,
        "emergency_fund_months": emergency_fund_months,
    }
