from __future__ import annotations

# Service files contain calculations, not database table definitions.
# This file should calculate:
# monthly_savings = total_net_income - total_expenses
# savings_rate = monthly_savings / total_net_income

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from src.db import session_scope
from src.models.account import Account
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_income import MonthlyIncome
from src.services.fx import convert_to_gbp


def calculate_savings_details(month: date) -> dict[str, Decimal]:
    """Return income, expenses, savings, and savings rate for a month."""
    with session_scope() as session:
        incomes = session.scalars(select(MonthlyIncome).where(MonthlyIncome.month == month)).all()
        expenses = session.scalars(select(MonthlyExpense).where(MonthlyExpense.month == month)).all()
        accounts = session.scalars(select(Account)).all()

    currencies = {account.id: account.currency for account in accounts}
    total_net_income = sum(
        (
            convert_to_gbp(income.net_amount, currencies.get(income.target_account_id, "GBP")).gbp_amount
            for income in incomes
        ),
        Decimal("0.00"),
    )
    total_expenses = sum(
        (
            convert_to_gbp(expense.amount, currencies.get(expense.source_account_id, "GBP")).gbp_amount
            for expense in expenses
        ),
        Decimal("0.00"),
    )
    monthly_savings = total_net_income - total_expenses

    savings_rate = Decimal("0.00")
    if total_net_income:
        savings_rate = monthly_savings / total_net_income

    return {
        "total_net_income": total_net_income,
        "total_expenses": total_expenses,
        "monthly_savings": monthly_savings,
        "savings_rate": savings_rate,
    }


def calculate_savings_rate(month: date) -> Decimal:
    """Return just the savings rate for callers that only need one number."""
    return calculate_savings_details(month)["savings_rate"]
