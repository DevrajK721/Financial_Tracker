from __future__ import annotations

# DebtProfile stores extra information for accounts whose account_type is "debt".
# The actual debt balance still comes from MonthlyAccountSnapshot.
# This file stores metadata like interest rate and minimum payment.

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class DebtProfile(Base):
    __tablename__ = "debt_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    debt_type: Mapped[str] = mapped_column(String(100), nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # Percentage, e.g., 7.90
    minimum_payment: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # notes can be optional.
    notes: Mapped[str | None] = mapped_column(String(200), nullable=True)
