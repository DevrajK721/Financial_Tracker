from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.db import session_scope
from src.models.account import Account
from src.models.goal import Goal
from src.models.monthly_goal_allocation import MonthlyGoalAllocation
from src.services.goal_allocation import calculate_goal_progress


def test_goal_progress_uses_allocations_for_the_month() -> None:
    month = date(2026, 8, 1)

    with session_scope() as session:
        account = Account(name="Cash ISA", account_type="cash_isa", currency="GBP")
        goal = Goal(name="Holiday", target_amount=Decimal("2000.00"))
        session.add_all([account, goal])
        session.flush()

        session.add(
            MonthlyGoalAllocation(
                month=month,
                goal_id=goal.id,
                account_id=account.id,
                allocated_amount=Decimal("500.00"),
            )
        )

    progress = calculate_goal_progress(month)

    assert progress["Holiday"] == Decimal("0.25")
