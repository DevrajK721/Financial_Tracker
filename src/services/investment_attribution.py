from __future__ import annotations

# Investment attribution estimates how much account growth came from performance
# rather than contributions or withdrawals.

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from src.account_types import GROWTH_ACCOUNT_TYPES
from src.db import session_scope
from src.models.account import Account
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_transfer import MonthlyTransfer


def estimate_investment_growth(month: date) -> dict[str, Decimal]:
    """Estimate account growth after adjusting for transfers in and out."""
    with session_scope() as session:
        rows = session.execute(
            select(MonthlyAccountSnapshot, Account)
            .join(Account, MonthlyAccountSnapshot.account_id == Account.id)
            .where(MonthlyAccountSnapshot.month == month)
        ).all()
        transfers = session.scalars(select(MonthlyTransfer).where(MonthlyTransfer.month == month)).all()

    snapshots: dict[int, dict[str, Decimal]] = {}
    account_names: dict[int, str] = {}
    account_types: dict[int, str] = {}

    for snapshot, account in rows:
        snapshots.setdefault(account.id, {})[snapshot.snapshot_type] = snapshot.balance
        account_names[account.id] = account.name
        account_types[account.id] = account.account_type.lower()

    transfer_in: dict[int, Decimal] = {}
    transfer_out: dict[int, Decimal] = {}
    for transfer in transfers:
        transfer_in[transfer.to_account_id] = transfer_in.get(transfer.to_account_id, Decimal("0.00")) + transfer.amount
        transfer_out[transfer.from_account_id] = transfer_out.get(transfer.from_account_id, Decimal("0.00")) + transfer.amount

    growth: dict[str, Decimal] = {}
    for account_id, account_snapshots in snapshots.items():
        if account_types.get(account_id) not in GROWTH_ACCOUNT_TYPES:
            continue
        if "start" not in account_snapshots or "end" not in account_snapshots:
            continue

        net_transfers = transfer_in.get(account_id, Decimal("0.00")) - transfer_out.get(account_id, Decimal("0.00"))
        growth[account_names[account_id]] = account_snapshots["end"] - account_snapshots["start"] - net_transfers

    return growth
