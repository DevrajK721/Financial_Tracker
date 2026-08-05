from __future__ import annotations

# Goal allocation tracks progress towards savings goals.
# The allocation records say how much money inside real accounts belongs to each goal.

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from src.db import session_scope
from src.models.goal import Goal
from src.models.monthly_goal_allocation import MonthlyGoalAllocation


def calculate_goal_progress(month: date) -> dict[str, Decimal]:
    """Return percentage progress for active goals."""
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

    progress: dict[str, Decimal] = {}
    for goal in goals:
        allocated = allocated_by_goal.get(goal.id, Decimal("0.00"))
        progress[goal.name] = Decimal("0.00") if goal.target_amount == 0 else allocated / goal.target_amount

    return progress
