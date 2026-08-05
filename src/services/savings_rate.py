from __future__ import annotations

# Service files contain calculations, not database table definitions.
# This file should calculate:
# monthly_savings = total_net_income - total_expenses
# savings_rate = monthly_savings / total_net_income

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from src.db import session_scope
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_income import MonthlyIncome


def calculate_savings_details(month: date) -> dict[str, Decimal]:
    """Return income, expenses, savings, and savings rate for a month."""
    with session_scope() as session:
        incomes = session.scalars(select(MonthlyIncome).where(MonthlyIncome.month == month)).all()
        expenses = session.scalars(select(MonthlyExpense).where(MonthlyExpense.month == month)).all()

        total_net_income = sum((income.net_amount for income in incomes), Decimal("0.00"))
        total_expenses = sum((expense.amount for expense in expenses), Decimal("0.00"))
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
