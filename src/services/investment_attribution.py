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
from src.services.fx import convert_to_gbp, money_decimal
from src.services.projections import add_months


def investment_account_history() -> list[dict[str, Decimal | str]]:
    """Return monthly investment balances, contributions, withdrawals, and growth.

    Contributions and withdrawals come from transfers involving investment-like
    accounts. Performance/growth is only calculated when both start and end
    snapshots exist for the account in the same month.
    """
    with session_scope() as session:
        accounts = session.scalars(
            select(Account)
            .where(Account.account_type.in_(GROWTH_ACCOUNT_TYPES))
            .order_by(Account.name)
        ).all()
        snapshots = session.scalars(select(MonthlyAccountSnapshot)).all()
        transfers = session.scalars(select(MonthlyTransfer)).all()

    account_names = {account.id: account.name for account in accounts}
    account_types = {account.id: account.account_type for account in accounts}
    account_currencies = {account.id: account.currency for account in accounts}
    investment_account_ids = set(account_names)

    snapshot_map: dict[tuple[int, date], dict[str, Decimal]] = {}
    months: set[date] = set()
    for snapshot in snapshots:
        if snapshot.account_id not in investment_account_ids:
            continue
        key = (snapshot.account_id, snapshot.month)
        snapshot_map.setdefault(key, {})[snapshot.snapshot_type] = convert_to_gbp(
            snapshot.balance,
            account_currencies[snapshot.account_id],
        ).gbp_amount
        months.add(snapshot.month)

    transfer_in: dict[tuple[int, date], Decimal] = {}
    transfer_out: dict[tuple[int, date], Decimal] = {}
    for transfer in transfers:
        if transfer.to_account_id in investment_account_ids:
            key = (transfer.to_account_id, transfer.month)
            amount = convert_to_gbp(transfer.amount, account_currencies[transfer.to_account_id]).gbp_amount
            transfer_in[key] = transfer_in.get(key, Decimal("0.00")) + amount
            months.add(transfer.month)
        if transfer.from_account_id in investment_account_ids:
            key = (transfer.from_account_id, transfer.month)
            amount = convert_to_gbp(transfer.amount, account_currencies[transfer.from_account_id]).gbp_amount
            transfer_out[key] = transfer_out.get(key, Decimal("0.00")) + amount
            months.add(transfer.month)

    rows: list[dict[str, Decimal | str]] = []
    for account_id in sorted(investment_account_ids, key=lambda value: account_names[value].lower()):
        for month in sorted(months):
            key = (account_id, month)
            account_snapshots = snapshot_map.get(key, {})
            start_balance = account_snapshots.get("start")
            end_balance = account_snapshots.get("end")
            contributions = transfer_in.get(key, Decimal("0.00"))
            withdrawals = transfer_out.get(key, Decimal("0.00"))
            net_contributions = contributions - withdrawals

            if start_balance is None and end_balance is None and net_contributions == 0:
                continue

            performance_growth: Decimal | None = None
            if start_balance is not None and end_balance is not None:
                performance_growth = end_balance - start_balance - net_contributions

            current_balance = end_balance if end_balance is not None else start_balance
            rows.append(
                {
                    "month": month.isoformat(),
                    "account": account_names[account_id],
                    "account_type": account_types[account_id],
                    "start_balance": start_balance,
                    "end_balance": end_balance,
                    "current_balance": current_balance or Decimal("0.00"),
                    "contributions": contributions,
                    "withdrawals": withdrawals,
                    "net_contributions": net_contributions,
                    "performance_growth": performance_growth,
                    "has_contribution": net_contributions != 0,
                    "has_full_snapshot": start_balance is not None and end_balance is not None,
                }
            )

    return rows


def investment_contribution_events() -> list[dict[str, Decimal | str]]:
    """Return investment transfer events for chart markers."""
    with session_scope() as session:
        accounts = session.scalars(select(Account).where(Account.account_type.in_(GROWTH_ACCOUNT_TYPES))).all()
        transfers = session.scalars(select(MonthlyTransfer).order_by(MonthlyTransfer.month)).all()

    account_names = {account.id: account.name for account in accounts}
    account_currencies = {account.id: account.currency for account in accounts}
    investment_account_ids = set(account_names)

    events: list[dict[str, Decimal | str]] = []
    for transfer in transfers:
        if transfer.to_account_id in investment_account_ids:
            amount = convert_to_gbp(transfer.amount, account_currencies[transfer.to_account_id]).gbp_amount
            events.append(
                {
                    "month": transfer.month.isoformat(),
                    "account": account_names[transfer.to_account_id],
                    "amount": amount,
                    "event_type": "Contribution",
                    "label": transfer.label or "Contribution",
                }
            )
        if transfer.from_account_id in investment_account_ids:
            amount = convert_to_gbp(transfer.amount, account_currencies[transfer.from_account_id]).gbp_amount
            events.append(
                {
                    "month": transfer.month.isoformat(),
                    "account": account_names[transfer.from_account_id],
                    "amount": -amount,
                    "event_type": "Withdrawal",
                    "label": transfer.label or "Withdrawal",
                }
            )

    return events


def project_investment_balances(month: date, months_forward: int = 12, lookback_months: int = 6) -> list[dict[str, Decimal | str]]:
    """Project investment balances using recent growth and contribution averages."""
    history = investment_account_history()
    rows_by_account: dict[str, list[dict[str, Decimal | str]]] = {}
    for row in history:
        if date.fromisoformat(str(row["month"])) <= month:
            rows_by_account.setdefault(str(row["account"]), []).append(row)

    projections: list[dict[str, Decimal | str]] = []
    for account, rows in rows_by_account.items():
        rows = sorted(rows, key=lambda row: str(row["month"]))
        current_rows = [row for row in rows if date.fromisoformat(str(row["month"])) == month]
        if current_rows:
            current_balance = Decimal(str(current_rows[-1]["current_balance"]))
        else:
            current_balance = Decimal(str(rows[-1]["current_balance"]))

        recent_rows = rows[-lookback_months:]
        performance_values = [
            Decimal(str(row["performance_growth"]))
            for row in recent_rows
            if row["performance_growth"] is not None
        ]
        contribution_values = [Decimal(str(row["net_contributions"])) for row in recent_rows]

        average_performance = Decimal("0.00")
        if performance_values:
            average_performance = sum(performance_values, Decimal("0.00")) / Decimal(len(performance_values))

        average_contribution = Decimal("0.00")
        if contribution_values:
            average_contribution = sum(contribution_values, Decimal("0.00")) / Decimal(len(contribution_values))

        projected_balance = current_balance
        performance_only_balance = current_balance
        for index in range(1, months_forward + 1):
            projected_month = add_months(month, index)
            projected_balance = money_decimal(projected_balance + average_performance + average_contribution)
            performance_only_balance = money_decimal(performance_only_balance + average_performance)
            projections.append(
                {
                    "month": projected_month.isoformat(),
                    "account": account,
                    "projected_balance": projected_balance,
                    "performance_only_balance": performance_only_balance,
                    "average_performance": average_performance,
                    "average_contribution": average_contribution,
                }
            )

    return projections


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
    account_currencies: dict[int, str] = {}

    for snapshot, account in rows:
        snapshots.setdefault(account.id, {})[snapshot.snapshot_type] = convert_to_gbp(
            snapshot.balance,
            account.currency,
        ).gbp_amount
        account_names[account.id] = account.name
        account_types[account.id] = account.account_type.lower()
        account_currencies[account.id] = account.currency

    transfer_in: dict[int, Decimal] = {}
    transfer_out: dict[int, Decimal] = {}
    for transfer in transfers:
        if transfer.to_account_id in account_currencies:
            amount = convert_to_gbp(transfer.amount, account_currencies[transfer.to_account_id]).gbp_amount
            transfer_in[transfer.to_account_id] = transfer_in.get(transfer.to_account_id, Decimal("0.00")) + amount
        if transfer.from_account_id in account_currencies:
            amount = convert_to_gbp(transfer.amount, account_currencies[transfer.from_account_id]).gbp_amount
            transfer_out[transfer.from_account_id] = transfer_out.get(transfer.from_account_id, Decimal("0.00")) + amount

    growth: dict[str, Decimal] = {}
    for account_id, account_snapshots in snapshots.items():
        if account_types.get(account_id) not in GROWTH_ACCOUNT_TYPES:
            continue
        if "start" not in account_snapshots or "end" not in account_snapshots:
            continue

        net_transfers = transfer_in.get(account_id, Decimal("0.00")) - transfer_out.get(account_id, Decimal("0.00"))
        growth[account_names[account_id]] = account_snapshots["end"] - account_snapshots["start"] - net_transfers

    return growth
