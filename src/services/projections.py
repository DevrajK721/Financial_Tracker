from __future__ import annotations

# Projection services turn your monthly history into simple forward-looking signals.
# These are deliberately simple estimates, not promises.

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from src.db import session_scope
from src.models.goal import Goal
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_goal_allocation import MonthlyGoalAllocation
from src.models.monthly_income import MonthlyIncome
from src.services.net_worth import calculate_net_worth
from src.services.spending_baseline import previous_months


def average_monthly_savings(month: date, lookback_months: int = 6) -> Decimal:
    """Estimate average savings using net income minus expenses over previous months."""
    months = previous_months(month, lookback_months)

    with session_scope() as session:
        incomes = session.scalars(select(MonthlyIncome).where(MonthlyIncome.month.in_(months))).all()
        expenses = session.scalars(select(MonthlyExpense).where(MonthlyExpense.month.in_(months))).all()

    months_with_data = {income.month for income in incomes} | {expense.month for expense in expenses}
    if not months_with_data:
        return Decimal("0.00")

    total_income = sum((income.net_amount for income in incomes), Decimal("0.00"))
    total_expenses = sum((expense.amount for expense in expenses), Decimal("0.00"))
    return (total_income - total_expenses) / Decimal(len(months_with_data))


def project_net_worth(month: date, months_forward: int = 12) -> list[dict[str, Decimal | str]]:
    """Project net worth by adding average monthly savings to current net worth."""
    current_net_worth = calculate_net_worth(month)
    monthly_savings = average_monthly_savings(month)
    projection = []

    for index in range(1, months_forward + 1):
        projected_month = add_months(month, index)
        projection.append(
            {
                "month": projected_month.isoformat(),
                "projected_net_worth": current_net_worth + (monthly_savings * Decimal(index)),
            }
        )

    return projection


def project_goal_completion(month: date) -> dict[str, dict[str, Decimal | int]]:
    """Estimate months remaining for each goal using recent average savings."""
    monthly_savings = average_monthly_savings(month)

    with session_scope() as session:
        goals = session.scalars(select(Goal).where(Goal.is_active.is_(True))).all()
        allocations = session.scalars(
            select(MonthlyGoalAllocation).where(MonthlyGoalAllocation.month == month)
        ).all()

    allocated_by_goal: dict[int, Decimal] = {}
    for allocation in allocations:
        allocated_by_goal[allocation.goal_id] = (
            allocated_by_goal.get(allocation.goal_id, Decimal("0.00")) + allocation.allocated_amount
        )

    result: dict[str, dict[str, Decimal | int]] = {}
    for goal in goals:
        allocated = allocated_by_goal.get(goal.id, Decimal("0.00"))
        remaining = max(Decimal("0.00"), goal.target_amount - allocated)
        months_remaining = -1
        if monthly_savings > 0:
            months_remaining = int((remaining / monthly_savings).to_integral_value(rounding="ROUND_CEILING"))

        result[goal.name] = {
            "allocated": allocated,
            "remaining": remaining,
            "months_remaining": months_remaining,
        }

    return result


def latest_month() -> date | None:
    """Return the latest month with any entered monthly data."""
    with session_scope() as session:
        months = [
            *session.scalars(select(MonthlyAccountSnapshot.month)).all(),
            *session.scalars(select(MonthlyIncome.month)).all(),
            *session.scalars(select(MonthlyExpense.month)).all(),
        ]

    return max(months) if months else None


def add_months(month: date, count: int) -> date:
    """Add count months to a month-start date."""
    month_index = month.month - 1 + count
    year = month.year + month_index // 12
    month_number = month_index % 12 + 1
    return date(year, month_number, 1)
