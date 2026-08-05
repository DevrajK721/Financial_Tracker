from __future__ import annotations

# MonthlyAccountSnapshot stores what an account was worth in a month.
# Example: Monzo end balance for August 2026 = 1250.75.
# Use this for net worth, investment growth, pension growth, and debt tracking.

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class MonthlyAccountSnapshot(Base):
    __tablename__ = "monthly_account_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False) 
    month: Mapped[date] = mapped_column(Date, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    snapshot_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "start" or "end"
