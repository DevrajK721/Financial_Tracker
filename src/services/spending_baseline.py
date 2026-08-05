from __future__ import annotations

# Spending baseline compares this month against previous months.
# A good first version can use the average or median of the previous 3-6 months.

from datetime import date
from decimal import Decimal
from statistics import median

from sqlalchemy import select

from src.db import session_scope
from src.models.monthly_expense import MonthlyExpense


def previous_months(month: date, count: int = 6) -> list[date]:
    """Return the previous count month-start dates."""
    months = []
    year = month.year
    month_number = month.month

    for _ in range(count):
        month_number -= 1
        if month_number == 0:
            month_number = 12
            year -= 1
        months.append(date(year, month_number, 1))

    return months


def compare_spending_to_baseline(month: date, lookback_months: int = 6) -> dict[str, dict[str, Decimal]]:
    """Compare current category spend to the median of previous months."""
    baseline_months = previous_months(month, lookback_months)

    with session_scope() as session:
        current_expenses = session.scalars(
            select(MonthlyExpense).where(MonthlyExpense.month == month)
        ).all()
        baseline_expenses = session.scalars(
            select(MonthlyExpense).where(MonthlyExpense.month.in_(baseline_months))
        ).all()

    current_by_category: dict[str, Decimal] = {}
    for expense in current_expenses:
        current_by_category[expense.category] = current_by_category.get(expense.category, Decimal("0.00")) + expense.amount

    baseline_values: dict[str, list[Decimal]] = {}
    for expense in baseline_expenses:
        baseline_values.setdefault(expense.category, []).append(expense.amount)

    categories = set(current_by_category) | set(baseline_values)
    comparison: dict[str, dict[str, Decimal]] = {}

    for category in sorted(categories):
        current = current_by_category.get(category, Decimal("0.00"))
        baseline = Decimal("0.00")
        if baseline_values.get(category):
            baseline = Decimal(str(median(baseline_values[category])))

        comparison[category] = {
            "current": current,
            "baseline": baseline,
            "difference": current - baseline,
        }

    return comparison
