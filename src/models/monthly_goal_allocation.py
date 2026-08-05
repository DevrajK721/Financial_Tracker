from __future__ import annotations

# MonthlyGoalAllocation says how much of an account balance is assigned to a goal.
# Example: 800 of your Cash ISA is mentally assigned to "holiday".
# This prevents goal tracking from needing separate fake accounts.

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class MonthlyGoalAllocation(Base):
    __tablename__ = "monthly_goal_allocations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)