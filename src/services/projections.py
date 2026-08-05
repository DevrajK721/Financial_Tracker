from __future__ import annotations

# Projection services turn your monthly history into simple forward-looking signals.
# These are deliberately simple estimates, not promises.

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select

from src.account_types import GROWTH_ACCOUNT_TYPES
from src.db import session_scope
from src.models.account import Account
from src.models.debt_profile import DebtProfile
from src.models.goal import Goal
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_goal_allocation import MonthlyGoalAllocation
from src.models.monthly_income import MonthlyIncome
from src.models.monthly_transfer import MonthlyTransfer
from src.services.fx import convert_to_gbp
from src.services.net_worth import calculate_net_worth
from src.services.snapshot_balances import monthly_account_balances
from src.services.spending_baseline import previous_months


MONEY = Decimal("0.01")


def money_decimal(amount: Decimal) -> Decimal:
    """Round projected money values to pounds and pence."""
    return amount.quantize(MONEY, rounding=ROUND_HALF_UP)


def average_monthly_savings(month: date, lookback_months: int = 6) -> Decimal:
    """Estimate average savings using net income minus expenses over previous months."""
    months = previous_months(month, lookback_months)

    with session_scope() as session:
        incomes = session.scalars(select(MonthlyIncome).where(MonthlyIncome.month.in_(months))).all()
        expenses = session.scalars(select(MonthlyExpense).where(MonthlyExpense.month.in_(months))).all()
        accounts = session.scalars(select(Account)).all()

    months_with_data = {income.month for income in incomes} | {expense.month for expense in expenses}
    if not months_with_data:
        return Decimal("0.00")

    currencies = {account.id: account.currency for account in accounts}
    total_income = sum(
        (
            convert_to_gbp(income.net_amount, currencies.get(income.target_account_id, "GBP")).gbp_amount
            for income in incomes
        ),
        Decimal("0.00"),
    )
    total_expenses = sum(
        (
            convert_to_gbp(expense.amount, currencies.get(expense.source_account_id, "GBP")).gbp_amount
            for expense in expenses
        ),
        Decimal("0.00"),
    )
    return (total_income - total_expenses) / Decimal(len(months_with_data))


def project_net_worth(month: date, months_forward: int = 12) -> list[dict[str, Decimal | str]]:
    """Project net worth using savings, investment performance, and debt interest."""
    current_net_worth = calculate_net_worth(month)
    monthly_savings = average_monthly_savings(month)
    monthly_investment_performance = average_monthly_investment_performance(month)
    debt_projection = project_total_debt(month, months_forward)
    current_debt = current_total_debt(month)
    projection = []

    for index in range(1, months_forward + 1):
        projected_month = add_months(month, index)
        projected_debt = debt_projection[index - 1]["projected_debt"] if debt_projection else current_debt
        debt_change = projected_debt - current_debt
        projected_net_worth = (
            current_net_worth
            + (monthly_savings * Decimal(index))
            + (monthly_investment_performance * Decimal(index))
            - debt_change
        )
        projection.append(
            {
                "month": projected_month.isoformat(),
                "projected_net_worth": money_decimal(projected_net_worth),
            }
        )

    return projection


def current_total_debt(month: date) -> Decimal:
    """Return current total debt using the same snapshot rules as net worth."""
    return sum(
        (balance.balance for balance in monthly_account_balances(month) if balance.is_debt),
        Decimal("0.00"),
    )


def project_total_debt(month: date, months_forward: int = 12) -> list[dict[str, Decimal | str]]:
    """Project total debt using monthly interest and expected/minimum payments."""
    with session_scope() as session:
        profiles = session.scalars(select(DebtProfile)).all()
        accounts = session.scalars(select(Account)).all()

    rows = [balance for balance in monthly_account_balances(month) if balance.is_debt]
    balances = {balance.account_id: balance.balance for balance in rows}
    profiles_by_account = {profile.account_id: profile for profile in profiles}
    currencies = {account.id: account.currency for account in accounts}
    if not balances:
        return []

    projection = []
    for index in range(1, months_forward + 1):
        total = Decimal("0.00")
        for account_id, balance in list(balances.items()):
            profile = profiles_by_account.get(account_id)
            monthly_rate = Decimal("0.00")
            monthly_payment = Decimal("0.00")
            if profile is not None:
                monthly_rate = (profile.interest_rate / Decimal("100")) / Decimal("12")
                monthly_payment = convert_to_gbp(
                    profile.minimum_payment or Decimal("0.00"),
                    currencies.get(profile.account_id, "GBP"),
                ).gbp_amount

            next_balance = money_decimal(
                max(Decimal("0.00"), (balance * (Decimal("1") + monthly_rate)) - monthly_payment)
            )
            balances[account_id] = next_balance
            total += next_balance

        projection.append({"month": add_months(month, index).isoformat(), "projected_debt": money_decimal(total)})

    return projection


def average_monthly_investment_performance(month: date, lookback_months: int = 6) -> Decimal:
    """Estimate monthly investment performance, excluding contributions/withdrawals."""
    months = set(previous_months(month, lookback_months))
    months.add(month)

    with session_scope() as session:
        accounts = session.scalars(select(Account).where(Account.account_type.in_(GROWTH_ACCOUNT_TYPES))).all()
        snapshots = session.scalars(select(MonthlyAccountSnapshot).where(MonthlyAccountSnapshot.month.in_(months))).all()
        transfers = session.scalars(select(MonthlyTransfer).where(MonthlyTransfer.month.in_(months))).all()

    investment_account_ids = {account.id for account in accounts}
    account_currencies = {account.id: account.currency for account in accounts}
    if not investment_account_ids:
        return Decimal("0.00")

    snapshot_map: dict[tuple[int, date], dict[str, Decimal]] = {}
    for snapshot in snapshots:
        if snapshot.account_id in investment_account_ids:
            converted = convert_to_gbp(snapshot.balance, account_currencies[snapshot.account_id]).gbp_amount
            snapshot_map.setdefault((snapshot.account_id, snapshot.month), {})[snapshot.snapshot_type] = converted

    transfer_in: dict[tuple[int, date], Decimal] = {}
    transfer_out: dict[tuple[int, date], Decimal] = {}
    for transfer in transfers:
        if transfer.to_account_id in investment_account_ids:
            key = (transfer.to_account_id, transfer.month)
            amount = convert_to_gbp(transfer.amount, account_currencies[transfer.to_account_id]).gbp_amount
            transfer_in[key] = transfer_in.get(key, Decimal("0.00")) + amount
        if transfer.from_account_id in investment_account_ids:
            key = (transfer.from_account_id, transfer.month)
            amount = convert_to_gbp(transfer.amount, account_currencies[transfer.from_account_id]).gbp_amount
            transfer_out[key] = transfer_out.get(key, Decimal("0.00")) + amount

    performance_values = []
    for key, account_snapshots in snapshot_map.items():
        start_balance = account_snapshots.get("start")
        end_balance = account_snapshots.get("end")
        if start_balance is None or end_balance is None:
            continue
        net_contributions = transfer_in.get(key, Decimal("0.00")) - transfer_out.get(key, Decimal("0.00"))
        performance_values.append(end_balance - start_balance - net_contributions)

    if not performance_values:
        return Decimal("0.00")

    return sum(performance_values, Decimal("0.00")) / Decimal(len(performance_values))


def project_goal_completion(month: date) -> dict[str, dict[str, Decimal | int]]:
    """Estimate months remaining for each goal using recent average savings."""
    monthly_savings = average_monthly_savings(month)

    with session_scope() as session:
        goals = session.scalars(select(Goal).where(Goal.is_active.is_(True))).all()
        allocations = session.scalars(
            select(MonthlyGoalAllocation).where(MonthlyGoalAllocation.month == month)
        ).all()
        accounts = session.scalars(select(Account)).all()

    currencies = {account.id: account.currency for account in accounts}
    allocated_by_goal: dict[int, Decimal] = {}
    for allocation in allocations:
        allocated_amount = convert_to_gbp(
            allocation.allocated_amount,
            currencies.get(allocation.account_id, "GBP"),
        ).gbp_amount
        allocated_by_goal[allocation.goal_id] = (
            allocated_by_goal.get(allocation.goal_id, Decimal("0.00")) + allocated_amount
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
