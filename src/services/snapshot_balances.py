from __future__ import annotations

# Shared snapshot selection rules.
# For a month, prefer an end-of-month balance. If only a start-of-month balance
# exists, use that rather than hiding the account from net worth and balances.

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from src.db import session_scope
from src.models.account import Account
from src.models.debt_profile import DebtProfile
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.services.fx import convert_to_gbp


@dataclass(frozen=True)
class MonthlyAccountBalance:
    account_id: int
    account_name: str
    account_type: str
    currency: str
    native_balance: Decimal
    balance: Decimal
    snapshot_type: str
    is_debt: bool
    is_emergency_fund: bool
    fx_rate_to_gbp: Decimal
    fx_rate_date: str


def monthly_account_balances(month: date) -> list[MonthlyAccountBalance]:
    """Return one chosen balance per account for a month.

    Selection rule:
    - use the end-of-month snapshot when present
    - otherwise use the start-of-month snapshot

    Debt rule:
    - an account is debt if its account type is "debt"
    - or if a DebtProfile is attached to it, which protects against old data
      where a debt profile was accidentally linked to a bank account.
    """
    with session_scope() as session:
        rows = session.execute(
            select(MonthlyAccountSnapshot, Account)
            .join(Account, MonthlyAccountSnapshot.account_id == Account.id)
            .where(MonthlyAccountSnapshot.month == month)
            .order_by(Account.name, MonthlyAccountSnapshot.snapshot_type)
        ).all()
        debt_account_ids = set(session.scalars(select(DebtProfile.account_id)).all())

    preferred: dict[int, MonthlyAccountBalance] = {}
    snapshot_priority = {"start": 1, "end": 2}

    for snapshot, account in rows:
        existing = preferred.get(account.id)
        if existing and snapshot_priority.get(existing.snapshot_type, 0) >= snapshot_priority.get(snapshot.snapshot_type, 0):
            continue

        account_type = account.account_type.lower()
        converted = convert_to_gbp(snapshot.balance, account.currency)
        preferred[account.id] = MonthlyAccountBalance(
            account_id=account.id,
            account_name=account.name,
            account_type=account.account_type,
            currency=converted.native_currency,
            native_balance=converted.native_amount,
            balance=converted.gbp_amount,
            snapshot_type=snapshot.snapshot_type,
            is_debt=account_type == "debt" or account.id in debt_account_ids,
            is_emergency_fund=account.is_emergency_fund,
            fx_rate_to_gbp=converted.rate_to_gbp,
            fx_rate_date=converted.rate_date,
        )

    return sorted(preferred.values(), key=lambda balance: balance.account_name.lower())
