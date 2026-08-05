from __future__ import annotations

# MonthlyTransfer stores money moved between your own accounts.
# Transfers are not income and are not expenses.
# Example: 500 moved from Monzo to Cash ISA.

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class MonthlyTransfer(Base):
    __tablename__ = "monthly_transfers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    from_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    to_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Optional label for the transfer, e.g., "ISA contribution"
