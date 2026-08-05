from __future__ import annotations

# Streamlit dashboard for the monthly finance tracker.
# Run without auto-opening a browser:
# .venv/bin/python finance.py dashboard

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.account_types import ACCOUNT_TYPE_LABELS
from src.db import session_scope
from src.models.account import Account
from src.models.debt_profile import DebtProfile
from src.models.goal import Goal
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_goal_allocation import MonthlyGoalAllocation
from src.models.monthly_income import MonthlyIncome
from src.models.monthly_transfer import MonthlyTransfer
from src.models.subscription import Subscription
from src.reports.monthly_summary import build_monthly_summary
from src.services.dashboard_data import (
    account_balances,
    active_goals,
    active_subscriptions,
    available_months,
    expense_breakdown,
    net_worth_history,
    spending_by_category_history,
    spending_history,
)
from src.services.paye import STUDENT_LOAN_MONTHLY_THRESHOLDS, estimate_monthly_salary
from src.services.projections import latest_month


EXPENSE_CATEGORY_LABELS = {
    "rent": "Rent / Mortgage",
    "transport": "Transport",
    "food": "Food & Groceries",
    "gym": "Gym & Fitness",
    "clothing": "Clothing",
    "phone": "Phone",
    "subscriptions": "Subscriptions",
    "other": "Other Spending",
}
INCOME_TYPE_LABELS = {
    "salary": "Salary",
    "bonus": "Bonus",
    "family_support": "Family Support",
    "other": "Other Income",
}
SNAPSHOT_TYPE_LABELS = {
    "start": "Start of Month",
    "end": "End of Month",
}
BILLING_FREQUENCY_LABELS = {
    "monthly": "Monthly",
    "annual": "Annual",
    "weekly": "Weekly",
}
DEBT_TYPE_LABELS = {
    "student_loan": "🎓 Student Loan",
    "personal_debt": "🤝 Personal Debt",
    "credit_card": "💳 Credit Card",
    "loan": "🏛️ Loan",
    "mortgage": "🏠 Mortgage",
    "overdraft": "🏦 Overdraft",
    "other": "📌 Other Debt",
}
STUDENT_LOAN_LABELS = {
    "none": "No Student Loan",
    "plan_1": "🎓 Student Loan Plan 1",
    "plan_2": "🎓 Student Loan Plan 2",
    "plan_4": "🎓 Student Loan Plan 4",
    "plan_5": "🎓 Student Loan Plan 5",
}
ACCOUNT_TYPES = list(ACCOUNT_TYPE_LABELS)
EXPENSE_CATEGORIES = list(EXPENSE_CATEGORY_LABELS)
INCOME_TYPES = list(INCOME_TYPE_LABELS)
SNAPSHOT_TYPES = list(SNAPSHOT_TYPE_LABELS)
BILLING_FREQUENCIES = list(BILLING_FREQUENCY_LABELS)
PAGES = ["Entries", "Balances", "Statistics", "Spending", "Debts", "Goals", "Raw Data"]
PAGE_LABELS = {
    "Entries": "✍️ Entries",
    "Balances": "🏦 Balances",
    "Statistics": "📈 Statistics",
    "Spending": "🥧 Spending",
    "Debts": "📉 Debts",
    "Goals": "🎯 Goals",
    "Raw Data": "🧾 Records",
}
ENTRY_SECTIONS = {
    "add": "➕ Add",
    "edit": "🛠️ Edit",
    "delete": "🗑️ Delete",
}
EDIT_SECTIONS = {
    "accounts": "🏦 Accounts",
    "records": "📋 Monthly Records",
}
ADD_SECTION_LABELS = {
    "account": "🏦 Account",
    "snapshot": "📊 Account Balance Snapshot",
    "salary": "💷 Salary & PAYE/SFE",
    "income": "💰 Other Income",
    "expense": "🧾 Expense Entry",
    "transfer": "🔁 Transfer",
    "debt_profile": "📉 Debt Details & Balance",
    "goal": "🎯 Goal & Allocation",
    "subscription": "🔄 Subscription",
}
PAGE_SLUGS = {page: page.lower().replace(" ", "-") for page in PAGES}
PAGES_BY_SLUG = {slug: page for page, slug in PAGE_SLUGS.items()}
ACCENT_SEQUENCE = ["#ff6b6b", "#f2c875", "#8fb8ff", "#c68cff", "#f08ab8", "#a9a1b8"]


st.set_page_config(
    page_title="Finance Command Centre",
    page_icon="£",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def money(value: Decimal | float | int) -> str:
    return f"£{float(value):,.2f}"


def percent(value: Decimal | float | int) -> str:
    return f"{float(value) * 100:,.1f}%"


def months_label(value: Decimal | float | int) -> str:
    return f"{float(value):,.1f} mo"


def decimal_from_number(value: int | float | Decimal) -> Decimal:
    """Convert Streamlit numeric input into Decimal safely."""
    return Decimal(str(value))


def month_start(value: date) -> date:
    """Normalize a date input to the first day of its month."""
    return date(value.year, value.month, 1)


def display_label(value: str | None, labels: dict[str, str]) -> str:
    """Show a friendly label for an internal database value."""
    if value is None:
        return ""
    return labels.get(value, value.replace("_", " ").title())


def ensure_balance_columns(balances: pd.DataFrame) -> pd.DataFrame:
    """Keep balance rendering stable if Streamlit has stale in-memory rows."""
    if "type" not in balances.columns:
        balances["type"] = ""
    if "snapshot_type" not in balances.columns:
        balances["snapshot_type"] = "end"
    if "is_debt" not in balances.columns:
        balances["is_debt"] = balances["type"].astype(str).str.lower() == "debt"
    if "is_emergency_fund" not in balances.columns:
        balances["is_emergency_fund"] = False
    return balances


def reverse_labels(labels: dict[str, str]) -> dict[str, str]:
    return {display: value for value, display in labels.items()}


def select_from_labels(
    label: str,
    labels: dict[str, str],
    current_value: str | None = None,
    key: str | None = None,
) -> str:
    """Render a selectbox with professional labels but return the stored value."""
    display_options = list(labels.values())
    current_display = display_label(current_value, labels)
    display_to_value = reverse_labels(labels)
    if current_value and current_display not in display_to_value:
        display_options.append(current_display)
        display_to_value[current_display] = current_value
    index = display_options.index(current_display) if current_display in display_options else 0
    selected_display = st.selectbox(label, display_options, index=index, key=key)
    return display_to_value[selected_display]


def fetch_accounts() -> list[Account]:
    with session_scope() as session:
        return session.scalars(select(Account).order_by(Account.name)).all()


def fetch_goals() -> list[Goal]:
    with session_scope() as session:
        return session.scalars(select(Goal).order_by(Goal.name)).all()


def account_options(accounts: list[Account]) -> dict[str, int]:
    return {f"{account.name} - {display_label(account.account_type, ACCOUNT_TYPE_LABELS)}": account.id for account in accounts}


def goal_options(goals: list[Goal]) -> dict[str, int]:
    return {goal.name: goal.id for goal in goals}


def option_index(options: list[str], current_value: str | None) -> int:
    """Return a safe selectbox index even when older data has unexpected labels."""
    if current_value in options:
        return options.index(current_value)
    if current_value and current_value.lower() in options:
        return options.index(current_value.lower())
    return 0


def save_record(record) -> None:
    with session_scope() as session:
        session.add(record)


def fetch_end_snapshot_balance(account_id: int, month: date) -> Decimal:
    """Return an account's end-of-month balance, or zero if it has not been entered."""
    with session_scope() as session:
        snapshot = session.scalars(
            select(MonthlyAccountSnapshot)
            .where(MonthlyAccountSnapshot.account_id == account_id)
            .where(MonthlyAccountSnapshot.month == month)
            .where(MonthlyAccountSnapshot.snapshot_type == "end")
        ).first()

    return snapshot.balance if snapshot is not None else Decimal("0.00")


def save_debt_details(
    *,
    account_id: int,
    debt_type: str,
    interest_rate: Decimal,
    minimum_payment: Decimal,
    notes: str | None,
    month: date,
    current_balance: Decimal,
    profile_id: int | None = None,
) -> None:
    """Save debt metadata and the matching monthly debt balance together."""
    with session_scope() as session:
        if profile_id is None:
            profile = session.scalars(select(DebtProfile).where(DebtProfile.account_id == account_id)).first()
        else:
            profile = session.get(DebtProfile, profile_id)

        if profile is None:
            profile = DebtProfile(account_id=account_id)
            session.add(profile)

        profile.account_id = account_id
        profile.debt_type = debt_type
        profile.interest_rate = interest_rate
        profile.minimum_payment = minimum_payment
        profile.notes = notes

        snapshot = session.scalars(
            select(MonthlyAccountSnapshot)
            .where(MonthlyAccountSnapshot.account_id == account_id)
            .where(MonthlyAccountSnapshot.month == month)
            .where(MonthlyAccountSnapshot.snapshot_type == "end")
        ).first()

        if snapshot is None:
            session.add(
                MonthlyAccountSnapshot(
                    account_id=account_id,
                    month=month,
                    snapshot_type="end",
                    balance=current_balance,
                )
            )
        else:
            snapshot.balance = current_balance


def flash_success(message: str) -> None:
    """Show a success message after the next automatic rerun."""
    st.session_state["flash_success"] = message


def success_and_refresh(message: str) -> None:
    """Refresh the dashboard after a database write so visible data is current."""
    flash_success(message)
    st.rerun()


def render_flash_message() -> None:
    message = st.session_state.pop("flash_success", None)
    if message:
        st.success(message)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #08080a;
            --panel: #15151b;
            --panel-soft: #1e1d24;
            --line: #35323c;
            --text: #f7f1f1;
            --muted: #b8aeb0;
            --accent: #ff6b6b;
            --gold: #f2c875;
            --red: #ff8a8a;
            --blue: #8fb8ff;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(255, 107, 107, 0.12), transparent 30rem),
                linear-gradient(145deg, #08080a, #111116 52%, #070709);
            color: var(--text);
        }
        [data-testid="stSidebar"] {
            display: none;
        }
        h1, h2, h3 {
            color: var(--text);
            letter-spacing: 0;
        }
        .top-panel {
            border: 1px solid var(--line);
            background:
                linear-gradient(135deg, rgba(21, 21, 27, 0.98), rgba(30, 29, 36, 0.92));
            padding: 1.1rem 1.35rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .top-panel p {
            color: var(--muted);
            margin: 0.25rem 0 0;
        }
        [data-testid="stMetric"] {
            background: rgba(21, 21, 27, 0.94);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.85rem 1rem;
        }
        [data-testid="stMetricValue"] {
            color: var(--text);
            font-size: 1.75rem;
        }
        [data-testid="stMetricLabel"] {
            color: var(--muted);
        }
        .stDataFrame {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
        }
        div[data-testid="stAlert"] {
            background: rgba(21, 21, 27, 0.94);
            border: 1px solid var(--line);
            color: var(--text);
        }
        details:not([open]) {
            display: none;
        }
        .stButton > button,
        [data-testid="stFormSubmitButton"] button {
            border: 1px solid rgba(255, 107, 107, 0.65);
            background: rgba(255, 107, 107, 0.10);
            color: var(--text);
            border-radius: 8px;
        }
        .stButton > button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            border-color: rgba(255, 107, 107, 0.95);
            background: rgba(255, 107, 107, 0.18);
            color: var(--text);
        }
        .stButton > button:disabled,
        .stButton > button:disabled:hover {
            opacity: 1;
            border-color: rgba(255, 107, 107, 0.9);
            background: rgba(255, 107, 107, 0.24);
            color: var(--text);
        }
        .nav-shell {
            border: 1px solid var(--line);
            background: rgba(21, 21, 27, 0.76);
            border-radius: 12px;
            padding: 0.75rem;
            margin-bottom: 1rem;
        }
        .nav-row,
        .month-row,
        .subnav-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            align-items: center;
        }
        .month-row {
            margin-top: 0.65rem;
            padding-top: 0.65rem;
            border-top: 1px solid rgba(184, 174, 176, 0.14);
        }
        .nav-label {
            color: var(--muted);
            font-size: 0.82rem;
            margin-right: 0.35rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        .subnav-shell {
            border: 1px solid rgba(184, 174, 176, 0.14);
            background: rgba(21, 21, 27, 0.52);
            border-radius: 12px;
            padding: 0.65rem;
            margin: 0.75rem 0 1rem;
        }
        .nav-pill,
        .month-pill,
        .subnav-pill {
            border-radius: 999px;
            border: 1px solid rgba(255, 107, 107, 0.22);
            background: rgba(8, 8, 10, 0.38);
            color: var(--text) !important;
            display: inline-flex;
            padding: 0.38rem 0.78rem;
            text-decoration: none !important;
            transition: border-color 120ms ease, background 120ms ease, transform 120ms ease;
        }
        .nav-pill:hover,
        .month-pill:hover,
        .subnav-pill:hover {
            border-color: rgba(255, 107, 107, 0.78);
            background: rgba(255, 107, 107, 0.12);
            transform: translateY(-1px);
        }
        .nav-pill.active,
        .month-pill.active,
        .subnav-pill.active {
            border-color: rgba(255, 107, 107, 0.9);
            background: rgba(255, 107, 107, 0.18);
            color: var(--text);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def chart_theme(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f7f1f1",
        legend_title_text="",
        margin=dict(l=10, r=10, t=45, b=10),
    )
    fig.update_xaxes(gridcolor="rgba(184,174,176,0.16)", zerolinecolor="rgba(184,174,176,0.25)")
    fig.update_yaxes(gridcolor="rgba(184,174,176,0.16)", zerolinecolor="rgba(184,174,176,0.25)")
    return fig


def debt_history() -> list[dict]:
    """Build debt history from net worth history so the dashboard has fewer imports."""
    return [
        {"month": row["month"], "debt": row["debts"]}
        for row in net_worth_history()
        if row["debts"] > 0
    ]


def query_param(name: str) -> str | None:
    """Read one query parameter value from Streamlit's query param store."""
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def nav_href(page: str, month_label: str | None) -> str:
    """Create stable top-menu links instead of stateful Streamlit nav widgets."""
    href = f"?page={PAGE_SLUGS[page]}"
    if month_label is not None:
        href += f"&month={month_label}"
    return href


def entries_href(month_label: str, section: str, edit_section: str | None = None) -> str:
    """Create stable links for Entries sub-pages."""
    href = f"?page=entries&month={month_label}&section={section}"
    if edit_section is not None:
        href += f"&edit={edit_section}"
    return href


def selected_page() -> str:
    """Read the current page from session state, falling back to the URL."""
    session_page = st.session_state.get("selected_page")
    if session_page in PAGES:
        return session_page

    slug = query_param("page") or PAGE_SLUGS["Entries"]
    return PAGES_BY_SLUG.get(slug, "Entries")


def selected_entry_section() -> str:
    section = st.session_state.get("entry_section") or query_param("section") or "add"
    return section if section in ENTRY_SECTIONS else "add"


def selected_edit_section() -> str:
    section = st.session_state.get("edit_section") or query_param("edit") or "records"
    return section if section in EDIT_SECTIONS else "accounts"


def selected_month() -> tuple[date | None, list[str], str | None]:
    months = available_months()
    fallback = latest_month()
    if not months and fallback is None:
        return None, [], None

    options = months or [fallback]
    labels = [month.strftime("%Y-%m") for month in options if month is not None]
    selected = st.session_state.get("selected_month") or query_param("month")
    if selected not in labels:
        selected = labels[-1]
    return date.fromisoformat(f"{selected}-01"), labels, selected


def render_button_nav(
    *,
    label: str,
    options: list[str],
    current: str,
    state_key: str,
    key_prefix: str,
    format_func,
) -> str:
    """Render stable button navigation and disable the active option."""
    st.caption(label)
    columns = st.columns(len(options))
    for column, option in zip(columns, options, strict=True):
        button_label = format_func(option)
        is_active = option == current
        with column:
            if st.button(
                button_label,
                key=f"{key_prefix}_{option}",
                disabled=is_active,
                width="stretch",
            ):
                st.session_state[state_key] = option
                st.rerun()

    return st.session_state.get(state_key, current)


def render_top_nav(page: str, month_labels: list[str], selected_month_label: str | None) -> tuple[str, str | None]:
    """Render button navigation without full-page reloads or selected-pill clicks."""
    st.markdown('<div class="nav-shell">', unsafe_allow_html=True)
    selected_page_value = render_button_nav(
        label="View",
        options=PAGES,
        current=page,
        state_key="selected_page",
        key_prefix="page_nav",
        format_func=lambda option: PAGE_LABELS[option],
    )

    selected_month_value = selected_month_label
    if month_labels:
        selected_month_value = render_button_nav(
            label="Month",
            options=month_labels,
            current=selected_month_label or month_labels[-1],
            state_key="selected_month",
            key_prefix="month_nav",
            format_func=lambda option: option,
        )
    else:
        st.caption("No month yet")

    st.markdown("</div>", unsafe_allow_html=True)
    return selected_page_value, selected_month_value


def render_entries_subnav(section: str) -> str:
    return render_button_nav(
        label="Action",
        options=list(ENTRY_SECTIONS),
        current=section,
        state_key="entry_section",
        key_prefix="entry_nav",
        format_func=lambda option: ENTRY_SECTIONS[option],
    )


def render_edit_subnav(edit_section: str) -> str:
    return render_button_nav(
        label="Edit",
        options=list(EDIT_SECTIONS),
        current=edit_section,
        state_key="edit_section",
        key_prefix="edit_nav",
        format_func=lambda option: EDIT_SECTIONS[option],
    )


def page_header(month: date) -> None:
    st.markdown(
        f"""
        <div class="top-panel">
          <h1>Finance Command Centre</h1>
          <p>{month.strftime("%B %Y")} dashboard. Use the top menu to move between entries, balances, statistics, spending, debts, goals, and raw data.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def summary_metrics(summary: dict) -> None:
    savings = summary["savings"]
    net_worth = summary["net_worth"]
    debt = summary["debt"]
    emergency = summary["emergency_fund"]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Net Worth", money(net_worth["net_worth"]))
    col2.metric("Assets", money(net_worth["total_assets"]))
    col3.metric("Debt", money(debt["total_debt"]))
    col4.metric("Savings Rate", percent(savings["savings_rate"]))
    col5.metric("Emergency Cover", months_label(emergency["emergency_fund_months"]))


def render_balances(month: date) -> None:
    balances = pd.DataFrame(account_balances(month))
    st.subheader("🏦 Account Balances")
    if balances.empty:
        st.info("No account balance snapshots for this month yet.")
        return

    balances = ensure_balance_columns(balances)
    balances["signed_balance"] = balances.apply(lambda row: -row["balance"] if row["is_debt"] else row["balance"], axis=1)
    balances["Account"] = balances["account"]
    balances["Account Type"] = balances.apply(
        lambda row: "Debt Account" if row["is_debt"] else display_label(row["type"], ACCOUNT_TYPE_LABELS),
        axis=1,
    )
    balances["Balance"] = balances["balance"].apply(money)
    balances["Snapshot Used"] = balances["snapshot_type"].apply(lambda value: display_label(value, SNAPSHOT_TYPE_LABELS))
    balances["Emergency Fund"] = balances["is_emergency_fund"].map({True: "Yes", False: "No"})

    left, right = st.columns([1.3, 1])
    with left:
        fig = px.bar(
            balances,
            x="Account",
            y="signed_balance",
            color="Account Type",
            title="Balances by Account",
            color_discrete_sequence=ACCENT_SEQUENCE,
        )
        st.plotly_chart(chart_theme(fig), width="stretch")
    with right:
        by_type = balances.groupby("Account Type", as_index=False)["balance"].sum()
        fig = px.pie(
            by_type,
            names="Account Type",
            values="balance",
            title="Balance Mix",
            hole=0.45,
            color_discrete_sequence=ACCENT_SEQUENCE,
        )
        st.plotly_chart(chart_theme(fig), width="stretch")

    st.dataframe(
        balances[["Account", "Account Type", "Balance", "Snapshot Used", "Emergency Fund"]],
        width="stretch",
        hide_index=True,
    )


def render_statistics(summary: dict) -> None:
    st.subheader("📈 Statistics Over Time")
    net_worth = pd.DataFrame(net_worth_history())
    projection = pd.DataFrame(summary["net_worth_projection"])

    if not net_worth.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=net_worth["month"],
                y=net_worth["net_worth"],
                mode="lines+markers",
                name="Net Worth",
                line=dict(color="#ff6b6b", width=3),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=net_worth["month"],
                y=net_worth["assets"],
                mode="lines+markers",
                name="Assets",
                line=dict(color="#8fb8ff", width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=net_worth["month"],
                y=net_worth["debts"],
                mode="lines+markers",
                name="Debts",
                line=dict(color="#ff8a8a", width=2),
            )
        )
        if not projection.empty:
            fig.add_trace(
                go.Scatter(
                    x=projection["month"],
                    y=projection["projected_net_worth"].astype(float),
                    mode="lines+markers",
                    name="Projected Net Worth",
                    line=dict(color="#f2c875", width=3, dash="dash"),
                )
            )
        fig.update_layout(title="Net Worth Growth with Projection")
        st.plotly_chart(chart_theme(fig), width="stretch")
    else:
        st.info("Add end-of-month snapshots to build net worth history.")

    st.metric("Average Monthly Savings", money(summary["average_monthly_savings"]))


def render_spending(month: date, summary: dict) -> None:
    st.subheader("🥧 Spending")
    current = pd.DataFrame(expense_breakdown(month))
    history = pd.DataFrame(spending_history())
    category_history = pd.DataFrame(spending_by_category_history())
    baseline = pd.DataFrame(
        [{"category": category, **values} for category, values in summary["spending_vs_baseline"].items()]
    )

    left, right = st.columns(2)
    with left:
        if not current.empty:
            current["Category"] = current["category"].apply(lambda value: display_label(value, EXPENSE_CATEGORY_LABELS))
            fig = px.pie(
                current,
                names="Category",
                values="amount",
                title="This Month by Category",
                hole=0.45,
                color_discrete_sequence=ACCENT_SEQUENCE,
            )
            st.plotly_chart(chart_theme(fig), width="stretch")
        else:
            st.info("No expenses entered for this month.")
    with right:
        if not baseline.empty:
            baseline["Category"] = baseline["category"].apply(lambda value: display_label(value, EXPENSE_CATEGORY_LABELS))
            fig = px.bar(
                baseline,
                x="Category",
                y="difference",
                title="This Month vs Previous Median",
                color="difference",
                color_continuous_scale=["#ff6b6b", "#f2c875", "#ff8a8a"],
            )
            st.plotly_chart(chart_theme(fig), width="stretch")
        else:
            st.info("Add previous months to compare spending.")

    if not history.empty:
        fig = px.line(
            history,
            x="month",
            y="spending",
            markers=True,
            title="Total Spending Over Time",
            color_discrete_sequence=["#f2c875"],
        )
        st.plotly_chart(chart_theme(fig), width="stretch")

    if not category_history.empty:
        category_history["Category"] = category_history["category"].apply(
            lambda value: display_label(value, EXPENSE_CATEGORY_LABELS)
        )
        fig = px.bar(
            category_history,
            x="month",
            y="amount",
            color="Category",
            title="Category Spending Over Time",
            color_discrete_sequence=ACCENT_SEQUENCE,
        )
        st.plotly_chart(chart_theme(fig), width="stretch")


def render_debts(summary: dict) -> None:
    st.subheader("📉 Debts")
    debt = summary["debt"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Debt", money(debt["total_debt"]))
    col2.metric("Debt Change", money(debt["debt_change"]))
    col3.metric("Minimum Payments", money(debt["minimum_payments"]))

    history = pd.DataFrame(debt_history())
    projection = pd.DataFrame(summary["debt_projection"])
    if not history.empty or not projection.empty:
        fig = go.Figure()
        if not history.empty:
            fig.add_trace(
                go.Scatter(
                    x=history["month"],
                    y=history["debt"],
                    mode="lines+markers",
                    name="Actual Debt",
                    line=dict(color="#ff8a8a", width=3),
                )
            )
        if not projection.empty:
            fig.add_trace(
                go.Scatter(
                    x=projection["month"],
                    y=projection["projected_debt"].astype(float),
                    mode="lines+markers",
                    name="Projected Debt",
                    line=dict(color="#f2c875", width=3, dash="dash"),
                )
            )
        fig.update_layout(title="Debt Growth with Projection")
        st.plotly_chart(chart_theme(fig), width="stretch")
    else:
        st.info("Add debt snapshots to build debt history and projections.")

    debt_mix = pd.DataFrame(
        [
            {"debt": name, "balance": float(details["balance"])}
            for name, details in summary["debt_payoff"].items()
            if float(details["balance"]) > 0
        ]
    )
    if not debt_mix.empty:
        fig = px.pie(
            debt_mix,
            names="debt",
            values="balance",
            title="Debt Mix",
            hole=0.45,
            color_discrete_sequence=ACCENT_SEQUENCE,
        )
        st.plotly_chart(chart_theme(fig), width="stretch")

    payoff = pd.DataFrame(
        [
            {
                "Debt": name,
                "Balance": money(details["balance"]),
                "Monthly Interest Estimate": money(details["monthly_interest_estimate"]),
                "Minimum Payment": money(details["minimum_payment"]),
                "Estimated Payoff Months": details["payoff_months"],
            }
            for name, details in summary["debt_payoff"].items()
        ]
    )
    if not payoff.empty:
        st.dataframe(payoff, width="stretch", hide_index=True)
    else:
        st.caption("No debt payoff data for this month.")


def render_goals(summary: dict) -> None:
    st.subheader("🎯 Goals and Subscriptions")
    goal_projection = pd.DataFrame([{"goal": name, **details} for name, details in summary["goal_projection"].items()])
    subscriptions = pd.DataFrame(active_subscriptions())
    goals = pd.DataFrame(active_goals())

    if not goal_projection.empty:
        goal_projection = goal_projection.rename(
            columns={
                "goal": "Goal",
                "allocated": "Allocated",
                "remaining": "Remaining",
                "months_remaining": "Estimated Months Remaining",
            }
        )
        fig = px.bar(
            goal_projection,
            x="Goal",
            y=["Allocated", "Remaining"],
            title="Goal Funding",
            barmode="stack",
            color_discrete_sequence=["#ff6b6b", "#35323c"],
        )
        st.plotly_chart(chart_theme(fig), width="stretch")
        st.dataframe(goal_projection, width="stretch", hide_index=True)
    elif not goals.empty:
        goals = goals.rename(
            columns={
                "name": "Goal",
                "target_amount": "Target Amount",
                "target_date": "Target Date",
            }
        )
        st.dataframe(goals, width="stretch", hide_index=True)
    else:
        st.caption("No active goals entered yet.")

    st.subheader("Subscriptions")
    if not subscriptions.empty:
        subscriptions = subscriptions.rename(
            columns={
                "name": "Subscription",
                "amount": "Monthly Amount",
                "frequency": "Billing Frequency",
                "category": "Category",
                "next_payment_date": "Next Payment Date",
            }
        )
        subscriptions["Category"] = subscriptions["Category"].apply(
            lambda value: display_label(value, EXPENSE_CATEGORY_LABELS)
        )
        subscriptions["Billing Frequency"] = subscriptions["Billing Frequency"].apply(
            lambda value: display_label(value, BILLING_FREQUENCY_LABELS)
        )
        st.dataframe(subscriptions, width="stretch", hide_index=True)
    else:
        st.caption("No active subscriptions entered yet.")


def render_raw(month: date, summary: dict) -> None:
    st.subheader("🧾 Records")
    balances = pd.DataFrame(account_balances(month))
    expenses = pd.DataFrame(expense_breakdown(month))
    if not balances.empty:
        balances = ensure_balance_columns(balances)
        balances["Account Type"] = balances.apply(
            lambda row: "Debt Account" if row["is_debt"] else display_label(row["type"], ACCOUNT_TYPE_LABELS),
            axis=1,
        )
        balances["Balance"] = balances["balance"].apply(money)
        balances["Snapshot Used"] = balances["snapshot_type"].apply(lambda value: display_label(value, SNAPSHOT_TYPE_LABELS))
        balances["Emergency Fund"] = balances["is_emergency_fund"].map({True: "Yes", False: "No"})
        st.dataframe(
            balances.rename(columns={"account": "Account"})[
                ["Account", "Account Type", "Balance", "Snapshot Used", "Emergency Fund"]
            ],
            width="stretch",
            hide_index=True,
        )
    if not expenses.empty:
        expenses["Category"] = expenses["category"].apply(lambda value: display_label(value, EXPENSE_CATEGORY_LABELS))
        expenses["Amount"] = expenses["amount"].apply(money)
        st.dataframe(expenses[["Category", "Amount"]], width="stretch", hide_index=True)
    st.json(summary, expanded=False)


def render_add_entries(default_month: date) -> None:
    st.subheader("✍️ Add Records")
    accounts = fetch_accounts()
    goals = fetch_goals()
    account_map = account_options(accounts)
    goal_map = goal_options(goals)
    add_section = select_add_section()
    if not accounts:
        add_section = "account"

    with st.expander("🏦 Account", expanded=add_section == "account"):
        with st.form("add_account_form"):
            name = st.text_input("Account name")
            account_type = select_from_labels("Account type", ACCOUNT_TYPE_LABELS, key="add_account_type")
            currency = st.text_input("Currency", value="GBP", max_chars=3)
            is_emergency_fund = st.checkbox("Emergency fund account")
            submitted = st.form_submit_button("Add account")
            if submitted:
                if not name.strip():
                    st.error("Account name is required.")
                else:
                    save_record(
                        Account(
                            name=name.strip(),
                            account_type=account_type,
                            currency=currency.strip().upper() or "GBP",
                            is_emergency_fund=is_emergency_fund,
                        )
                    )
                    success_and_refresh("Account added.")

    if not accounts:
        st.info("Add at least one account before adding monthly finance entries.")
        return

    with st.expander("📊 Account Balance Snapshot", expanded=add_section == "snapshot"):
        with st.form("add_snapshot_form"):
            account_label = st.selectbox("Account", list(account_map))
            month = month_start(st.date_input("Month", value=default_month))
            snapshot_type = select_from_labels(
                "Snapshot type",
                SNAPSHOT_TYPE_LABELS,
                current_value="end",
                key="add_snapshot_type",
            )
            balance = st.number_input("Balance", step=0.01, format="%.2f")
            submitted = st.form_submit_button("Add snapshot")
            if submitted:
                save_record(
                    MonthlyAccountSnapshot(
                        account_id=account_map[account_label],
                        month=month,
                        snapshot_type=snapshot_type,
                        balance=decimal_from_number(balance),
                    )
                )
                success_and_refresh("Account balance snapshot added.")

    with st.expander("💷 Salary & PAYE/SFE Deductions", expanded=add_section == "salary"):
        with st.form("add_salary_form"):
            account_label = st.selectbox("🏦 Paid into account", list(account_map), key="salary_target")
            month = month_start(st.date_input("📅 Payroll month", value=default_month, key="salary_month"))
            label = st.text_input("📝 Salary description", value="Salary")
            gross_monthly = st.number_input("💷 Gross monthly salary", step=0.01, format="%.2f")
            one_off_bonus = st.number_input("🎁 One-off bonus in this payroll", step=0.01, format="%.2f")
            pension_salary_sacrifice = st.number_input("🏦 Pension salary sacrifice", step=0.01, format="%.2f")
            taxable_benefits = st.number_input("🎁 Taxable benefits", step=0.01, format="%.2f")
            student_loan_options = {
                key: value for key, value in STUDENT_LOAN_LABELS.items() if key == "none" or key in STUDENT_LOAN_MONTHLY_THRESHOLDS
            }
            student_loan_plan = select_from_labels(
                "🎓 SFE / Student Loan Plan",
                student_loan_options,
                key="add_salary_student_loan_plan",
            )
            voluntary_sfe = st.number_input("🎓 Additional voluntary SFE repayment", step=0.01, format="%.2f")
            has_postgraduate_loan = st.checkbox("🎓 Postgraduate loan")
            submitted = st.form_submit_button("Estimate and save salary")
            if submitted:
                estimate = estimate_monthly_salary(
                    gross_monthly=decimal_from_number(gross_monthly),
                    one_off_bonus=decimal_from_number(one_off_bonus),
                    pension_salary_sacrifice=decimal_from_number(pension_salary_sacrifice),
                    taxable_benefits_monthly=decimal_from_number(taxable_benefits),
                    student_loan_plan=None if student_loan_plan == "none" else student_loan_plan,
                    voluntary_student_loan_payment=decimal_from_number(voluntary_sfe),
                    has_postgraduate_loan=has_postgraduate_loan,
                )
                save_record(
                    MonthlyIncome(
                        month=month,
                        income_type="salary",
                        label=label.strip() or "Salary",
                        gross_amount=estimate.gross_monthly + estimate.one_off_bonus,
                        net_amount=estimate.net_monthly,
                        target_account_id=account_map[account_label],
                    )
                )
                success_and_refresh(
                    "Salary saved. "
                    f"Tax: {money(estimate.income_tax)}, NI: {money(estimate.national_insurance)}, "
                    f"🎓 SFE: {money(estimate.student_loan)}, voluntary repayment: {money(estimate.voluntary_student_loan_payment)}, "
                    f"net pay: {money(estimate.net_monthly)}."
                )

    with st.expander("💰 Other Income", expanded=add_section == "income"):
        with st.form("add_income_form"):
            account_label = st.selectbox("Target account", list(account_map), key="income_target")
            month = month_start(st.date_input("Month", value=default_month, key="income_month"))
            income_type = select_from_labels("Income type", INCOME_TYPE_LABELS, key="add_income_type")
            label = st.text_input("Label", key="income_label")
            gross_amount = st.number_input("Gross amount", step=0.01, format="%.2f", key="income_gross")
            net_amount = st.number_input("Net amount", step=0.01, format="%.2f", key="income_net")
            submitted = st.form_submit_button("Add income")
            if submitted:
                save_record(
                    MonthlyIncome(
                        month=month,
                        income_type=income_type,
                        label=label.strip() or None,
                        gross_amount=decimal_from_number(gross_amount),
                        net_amount=decimal_from_number(net_amount),
                        target_account_id=account_map[account_label],
                    )
                )
                success_and_refresh("Income entry added.")

    with st.expander("🧾 Expense Entry", expanded=add_section == "expense"):
        with st.form("add_expense_form"):
            account_label = st.selectbox("Source account", list(account_map), key="expense_source")
            month = month_start(st.date_input("Month", value=default_month, key="expense_month"))
            category = select_from_labels("Category", EXPENSE_CATEGORY_LABELS, key="add_expense_category")
            amount = st.number_input("Amount", step=0.01, format="%.2f", key="expense_amount")
            submitted = st.form_submit_button("Add expense")
            if submitted:
                save_record(
                    MonthlyExpense(
                        month=month,
                        category=category,
                        amount=decimal_from_number(amount),
                        source_account_id=account_map[account_label],
                    )
                )
                success_and_refresh("Expense entry added.")

    with st.expander("🔁 Transfer", expanded=add_section == "transfer"):
        with st.form("add_transfer_form"):
            from_account = st.selectbox("From account", list(account_map), key="transfer_from")
            to_account = st.selectbox("To account", list(account_map), key="transfer_to")
            month = month_start(st.date_input("Month", value=default_month, key="transfer_month"))
            amount = st.number_input("Amount", step=0.01, format="%.2f", key="transfer_amount")
            label = st.text_input("Label", key="transfer_label")
            submitted = st.form_submit_button("Add transfer")
            if submitted:
                if from_account == to_account:
                    st.error("Transfer accounts must be different.")
                else:
                    save_record(
                        MonthlyTransfer(
                            month=month,
                            from_account_id=account_map[from_account],
                            to_account_id=account_map[to_account],
                            amount=decimal_from_number(amount),
                            label=label.strip() or None,
                        )
                    )
                    success_and_refresh("Transfer added.")

    with st.expander("📉 Debt Details & Balance", expanded=add_section == "debt_profile"):
        debt_accounts = {
            label: account_id
            for label, account_id in account_map.items()
            if next((account.account_type == "debt" for account in accounts if account.id == account_id), False)
        }
        if not debt_accounts:
            st.warning(
                "Add a Debt Account first, then come back here to add its outstanding balance and repayment details."
            )
            st.caption("Go to Add -> Account and choose account type `Debt Account`, for example `Student Loan`.")
            return

        with st.form("add_debt_form"):
            account_label = st.selectbox("📉 Debt account", list(debt_accounts), key="debt_account")
            month = month_start(st.date_input("📅 Balance month", value=default_month, key="debt_balance_month"))
            current_balance = st.number_input(
                "💷 Current outstanding debt balance",
                step=0.01,
                format="%.2f",
                key="debt_current_balance",
            )
            debt_type = select_from_labels("📌 Debt type", DEBT_TYPE_LABELS, key="add_debt_type")
            interest_rate = st.number_input("📈 Annual interest rate %", step=0.01, format="%.2f")
            minimum_payment = st.number_input("🧾 Minimum monthly payment / expected repayment", step=0.01, format="%.2f")
            notes = st.text_input("📝 Notes")
            submitted = st.form_submit_button("Add debt profile")
            if submitted:
                save_debt_details(
                    account_id=debt_accounts[account_label],
                    debt_type=debt_type.strip().lower(),
                    interest_rate=decimal_from_number(interest_rate),
                    minimum_payment=decimal_from_number(minimum_payment),
                    notes=notes.strip() or None,
                    month=month,
                    current_balance=decimal_from_number(current_balance),
                )
                success_and_refresh("Debt profile and current balance saved.")

    with st.expander("🎯 Goal & Allocation", expanded=add_section == "goal"):
        goal_col, allocation_col = st.columns(2)
        with goal_col:
            with st.form("add_goal_form"):
                name = st.text_input("Goal name")
                target_amount = st.number_input("Target amount", step=0.01, format="%.2f")
                has_target_date = st.checkbox("Add target date")
                target_date = st.date_input("Target date") if has_target_date else None
                submitted = st.form_submit_button("Add goal")
                if submitted:
                    if not name.strip():
                        st.error("Goal name is required.")
                    else:
                        save_record(
                            Goal(
                                name=name.strip(),
                                target_amount=decimal_from_number(target_amount),
                                target_date=target_date,
                            )
                        )
                        success_and_refresh("Savings goal added.")
        with allocation_col:
            if not goals:
                st.info("Add a goal before allocating money to it.")
            else:
                with st.form("add_goal_allocation_form"):
                    goal_label = st.selectbox("Goal", list(goal_map))
                    account_label = st.selectbox("Account", list(account_map), key="goal_account")
                    month = month_start(st.date_input("Month", value=default_month, key="goal_month"))
                    amount = st.number_input("Allocated amount", step=0.01, format="%.2f")
                    submitted = st.form_submit_button("Add allocation")
                    if submitted:
                        save_record(
                            MonthlyGoalAllocation(
                                month=month,
                                goal_id=goal_map[goal_label],
                                account_id=account_map[account_label],
                                allocated_amount=decimal_from_number(amount),
                            )
                        )
                        success_and_refresh("Goal allocation added.")

    with st.expander("🔄 Subscription", expanded=add_section == "subscription"):
        with st.form("add_subscription_form"):
            name = st.text_input("Subscription name")
            amount = st.number_input("Monthly equivalent amount", step=0.01, format="%.2f")
            frequency = select_from_labels("Billing frequency", BILLING_FREQUENCY_LABELS, key="add_subscription_frequency")
            category = select_from_labels("Category", EXPENSE_CATEGORY_LABELS, key="subscription_category")
            has_next_payment_date = st.checkbox("Add next payment date")
            next_payment_date = st.date_input("Next payment date") if has_next_payment_date else None
            submitted = st.form_submit_button("Add subscription")
            if submitted:
                if not name.strip():
                    st.error("Subscription name is required.")
                else:
                    save_record(
                        Subscription(
                            name=name.strip(),
                            monthly_amount=decimal_from_number(amount),
                            billing_frequency=frequency,
                            category=category,
                            next_payment_date=next_payment_date,
                        )
                    )
                    success_and_refresh("Subscription added.")


RECORD_MODELS = {
    "account": Account,
    "snapshot": MonthlyAccountSnapshot,
    "income": MonthlyIncome,
    "expense": MonthlyExpense,
    "transfer": MonthlyTransfer,
    "debt_profile": DebtProfile,
    "goal": Goal,
    "goal_allocation": MonthlyGoalAllocation,
    "subscription": Subscription,
}
EDITABLE_ENTRY_MODELS = {key: value for key, value in RECORD_MODELS.items() if key != "account"}
RECORD_TYPE_LABELS = {
    "account": "🏦 Account",
    "snapshot": "📊 Account Balance Snapshot",
    "income": "💷 Income Entry",
    "expense": "🧾 Expense Entry",
    "transfer": "🔁 Transfer",
    "debt_profile": "📉 Debt Details & Balance",
    "goal": "🎯 Savings Goal",
    "goal_allocation": "🪙 Goal Allocation",
    "subscription": "🔄 Subscription",
}


def load_record(record_type: str, record_id: int):
    model = EDITABLE_ENTRY_MODELS[record_type]
    with session_scope() as session:
        return session.get(model, record_id)


def select_record_type(
    label: str,
    key: str,
    default: str = "expense",
    record_types: list[str] | None = None,
) -> str:
    """Select a record type with friendly labels, not internal model names."""
    options = record_types or list(RECORD_MODELS)
    display_options = [RECORD_TYPE_LABELS[option] for option in options]
    default_index = options.index(default) if default in options else 0
    selected_display = st.selectbox(label, display_options, index=default_index, key=key)
    return options[display_options.index(selected_display)]


def record_counts(record_types: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    with session_scope() as session:
        for record_type in record_types:
            counts[record_type] = len(session.scalars(select(RECORD_MODELS[record_type].id)).all())
    return counts


def select_record_type_with_counts(
    label: str,
    key: str,
    record_types: list[str],
    default: str | None = None,
) -> str:
    """Select a record type and show how many records exist for each type."""
    counts = record_counts(record_types)
    if default is None or default not in record_types:
        default = next((record_type for record_type in record_types if counts[record_type] > 0), record_types[0])

    display_options = [
        f"{RECORD_TYPE_LABELS[record_type]} ({counts[record_type]})"
        for record_type in record_types
    ]
    selected_display = st.selectbox(
        label,
        display_options,
        index=record_types.index(default),
        key=key,
    )
    return record_types[display_options.index(selected_display)]


def select_add_section() -> str:
    """Choose one Add form to focus on, instead of showing a wall of forms."""
    labels = list(ADD_SECTION_LABELS.values())
    selected = st.selectbox("What would you like to add?", labels, key="add_section_selector")
    reverse = {label: key for key, label in ADD_SECTION_LABELS.items()}
    return reverse[selected]


def render_edit_account() -> None:
    st.subheader("🏦 Edit Account")
    accounts = fetch_accounts()
    if not accounts:
        st.info("No accounts to edit.")
        return

    account_map = account_options(accounts)
    selected = st.selectbox("Account", list(account_map), key="edit_account_select")
    account_id = account_map[selected]
    account = next(account for account in accounts if account.id == account_id)

    with st.form("edit_account_form"):
        name = st.text_input("Name", value=account.name, key=f"edit_account_name_{account_id}")
        account_type = select_from_labels(
            "Account type",
            ACCOUNT_TYPE_LABELS,
            current_value=account.account_type,
            key=f"edit_account_type_{account_id}",
        )
        currency = st.text_input("Currency", value=account.currency, max_chars=3, key=f"edit_account_currency_{account_id}")
        is_active = st.checkbox("Active", value=account.is_active, key=f"edit_account_active_{account_id}")
        is_emergency_fund = st.checkbox(
            "Emergency fund",
            value=account.is_emergency_fund,
            key=f"edit_account_emergency_{account_id}",
        )
        submitted = st.form_submit_button("Save account changes")
        if submitted:
            account_updated = False
            with session_scope() as session:
                record = session.get(Account, account_id)
                if record is None:
                    st.error("Account no longer exists.")
                else:
                    record.name = name.strip()
                    record.account_type = account_type
                    record.currency = currency.strip().upper() or "GBP"
                    record.is_active = is_active
                    record.is_emergency_fund = is_emergency_fund
                    account_updated = True

            if account_updated:
                success_and_refresh("Account updated.")


def render_edit_monthly_record(default_month: date) -> None:
    st.subheader("🛠️ Edit Records")
    record_type = select_record_type_with_counts(
        "Entry type",
        key="edit_entry_type",
        record_types=list(EDITABLE_ENTRY_MODELS),
    )
    rows = record_rows(record_type)
    preview = record_preview(record_type)
    if not rows:
        st.info("No records of this type to edit.")
        return

    st.dataframe(preview, width="stretch", hide_index=True)
    record_choices = {row["Record"]: row["_record_id"] for row in rows}
    selected_record = st.selectbox("Record to edit", list(record_choices), key="edit_record_id")
    record_id = record_choices[selected_record]
    record = load_record(record_type, int(record_id))
    if record is None:
        st.error("Record not found.")
        return

    accounts = fetch_accounts()
    goals = fetch_goals()
    account_map = account_options(accounts)
    goal_map = goal_options(goals)
    account_labels = list(account_map)
    goal_labels = list(goal_map)

    with st.form("edit_monthly_record_form"):
        if record_type == "snapshot":
            current_account = next(
                (label for label, account_id in account_map.items() if account_id == record.account_id),
                account_labels[0],
            )
            account_label = st.selectbox("Account", account_labels, index=account_labels.index(current_account))
            month = month_start(st.date_input("Month", value=record.month or default_month))
            snapshot_type = select_from_labels(
                "Snapshot type",
                SNAPSHOT_TYPE_LABELS,
                current_value=record.snapshot_type,
                key="edit_snapshot_type",
            )
            balance = st.number_input("Balance", value=float(record.balance), step=0.01, format="%.2f")

        elif record_type == "income":
            current_account = next(
                (label for label, account_id in account_map.items() if account_id == record.target_account_id),
                account_labels[0],
            )
            account_label = st.selectbox("Target account", account_labels, index=account_labels.index(current_account))
            month = month_start(st.date_input("Month", value=record.month or default_month))
            income_type = select_from_labels(
                "Income type",
                INCOME_TYPE_LABELS,
                current_value=record.income_type,
                key="edit_income_type",
            )
            label = st.text_input("Label", value=record.label or "")
            gross_amount = st.number_input("Gross amount", value=float(record.gross_amount), step=0.01, format="%.2f")
            net_amount = st.number_input("Net amount", value=float(record.net_amount), step=0.01, format="%.2f")

        elif record_type == "expense":
            current_account = next(
                (label for label, account_id in account_map.items() if account_id == record.source_account_id),
                account_labels[0],
            )
            account_label = st.selectbox("Source account", account_labels, index=account_labels.index(current_account))
            month = month_start(st.date_input("Month", value=record.month or default_month))
            category = select_from_labels(
                "Category",
                EXPENSE_CATEGORY_LABELS,
                current_value=record.category,
                key="edit_expense_category",
            )
            amount = st.number_input("Amount", value=float(record.amount), step=0.01, format="%.2f")

        elif record_type == "transfer":
            current_from = next(
                (label for label, account_id in account_map.items() if account_id == record.from_account_id),
                account_labels[0],
            )
            current_to = next(
                (label for label, account_id in account_map.items() if account_id == record.to_account_id),
                account_labels[0],
            )
            from_account = st.selectbox("From account", account_labels, index=account_labels.index(current_from))
            to_account = st.selectbox("To account", account_labels, index=account_labels.index(current_to))
            month = month_start(st.date_input("Month", value=record.month or default_month))
            amount = st.number_input("Amount", value=float(record.amount), step=0.01, format="%.2f")
            label = st.text_input("Label", value=record.label or "")

        elif record_type == "debt_profile":
            debt_account_labels = [
                label
                for label, account_id in account_map.items()
                if next((account.account_type == "debt" for account in accounts if account.id == account_id), False)
            ]
            if not debt_account_labels:
                st.error("Add a Debt Account before editing debt details.")
                return

            current_account = next(
                (label for label, account_id in account_map.items() if account_id == record.account_id),
                debt_account_labels[0],
            )
            if current_account not in debt_account_labels:
                st.warning(
                    "This debt record is currently attached to a non-debt account. "
                    "Choose a real Debt Account below to fix it."
                )
                current_account = debt_account_labels[0]
            account_label = st.selectbox(
                "📉 Debt account",
                debt_account_labels,
                index=debt_account_labels.index(current_account),
            )
            debt_balance_month = month_start(
                st.date_input("📅 Balance month", value=default_month, key=f"edit_debt_balance_month_{record.id}")
            )
            existing_debt_balance = fetch_end_snapshot_balance(account_map[account_label], debt_balance_month)
            current_debt_balance = st.number_input(
                "💷 Current outstanding debt balance",
                value=float(existing_debt_balance),
                step=0.01,
                format="%.2f",
                key=f"edit_debt_current_balance_{record.id}_{account_map[account_label]}_{debt_balance_month.isoformat()}",
            )
            debt_type = select_from_labels(
                "📌 Debt type",
                DEBT_TYPE_LABELS,
                current_value=record.debt_type,
                key="edit_debt_type",
            )
            interest_rate = st.number_input("📈 Annual interest rate %", value=float(record.interest_rate), step=0.01, format="%.2f")
            minimum_payment = st.number_input(
                "🧾 Minimum monthly payment / expected repayment",
                value=float(record.minimum_payment or Decimal("0.00")),
                step=0.01,
                format="%.2f",
            )
            notes = st.text_input("📝 Notes", value=record.notes or "")

        elif record_type == "goal":
            name = st.text_input("Goal name", value=record.name)
            target_amount = st.number_input("Target amount", value=float(record.target_amount), step=0.01, format="%.2f")
            has_target_date = st.checkbox("Has target date", value=record.target_date is not None)
            target_date = st.date_input("Target date", value=record.target_date or default_month) if has_target_date else None
            is_active = st.checkbox("Active", value=record.is_active)

        elif record_type == "goal_allocation":
            if not goal_labels:
                st.error("Add a goal before editing allocations.")
                return
            current_goal = next(
                (label for label, goal_id in goal_map.items() if goal_id == record.goal_id),
                goal_labels[0],
            )
            current_account = next(
                (label for label, account_id in account_map.items() if account_id == record.account_id),
                account_labels[0],
            )
            goal_label = st.selectbox("Goal", goal_labels, index=goal_labels.index(current_goal))
            account_label = st.selectbox("Account", account_labels, index=account_labels.index(current_account))
            month = month_start(st.date_input("Month", value=record.month or default_month))
            amount = st.number_input("Allocated amount", value=float(record.allocated_amount), step=0.01, format="%.2f")

        else:
            name = st.text_input("Subscription name", value=record.name)
            monthly_amount = st.number_input(
                "Monthly equivalent amount",
                value=float(record.monthly_amount),
                step=0.01,
                format="%.2f",
            )
            billing_frequency = select_from_labels(
                "Billing frequency",
                BILLING_FREQUENCY_LABELS,
                current_value=record.billing_frequency,
                key="edit_subscription_frequency",
            )
            category = select_from_labels(
                "Category",
                EXPENSE_CATEGORY_LABELS,
                current_value=record.category,
                key="edit_subscription_category",
            )
            is_active = st.checkbox("Active", value=record.is_active)
            has_next_payment_date = st.checkbox("Has next payment date", value=record.next_payment_date is not None)
            next_payment_date = (
                st.date_input("Next payment date", value=record.next_payment_date or default_month)
                if has_next_payment_date
                else None
            )

        submitted = st.form_submit_button("Save changes")
        if submitted:
            record_updated = False
            with session_scope() as session:
                updated = session.get(EDITABLE_ENTRY_MODELS[record_type], int(record_id))
                if updated is None:
                    st.error("Record no longer exists.")
                    return

                if record_type == "snapshot":
                    updated.account_id = account_map[account_label]
                    updated.month = month
                    updated.snapshot_type = snapshot_type
                    updated.balance = decimal_from_number(balance)
                elif record_type == "income":
                    updated.target_account_id = account_map[account_label]
                    updated.month = month
                    updated.income_type = income_type
                    updated.label = label.strip() or None
                    updated.gross_amount = decimal_from_number(gross_amount)
                    updated.net_amount = decimal_from_number(net_amount)
                elif record_type == "expense":
                    updated.source_account_id = account_map[account_label]
                    updated.month = month
                    updated.category = category
                    updated.amount = decimal_from_number(amount)
                elif record_type == "transfer":
                    if from_account == to_account:
                        st.error("Transfer accounts must be different.")
                        return
                    updated.from_account_id = account_map[from_account]
                    updated.to_account_id = account_map[to_account]
                    updated.month = month
                    updated.amount = decimal_from_number(amount)
                    updated.label = label.strip() or None
                elif record_type == "debt_profile":
                    updated.account_id = account_map[account_label]
                    updated.debt_type = debt_type
                    updated.interest_rate = decimal_from_number(interest_rate)
                    updated.minimum_payment = decimal_from_number(minimum_payment)
                    updated.notes = notes.strip() or None
                    snapshot = session.scalars(
                        select(MonthlyAccountSnapshot)
                        .where(MonthlyAccountSnapshot.account_id == updated.account_id)
                        .where(MonthlyAccountSnapshot.month == debt_balance_month)
                        .where(MonthlyAccountSnapshot.snapshot_type == "end")
                    ).first()
                    if snapshot is None:
                        session.add(
                            MonthlyAccountSnapshot(
                                account_id=updated.account_id,
                                month=debt_balance_month,
                                snapshot_type="end",
                                balance=decimal_from_number(current_debt_balance),
                            )
                        )
                    else:
                        snapshot.balance = decimal_from_number(current_debt_balance)
                elif record_type == "goal":
                    updated.name = name.strip()
                    updated.target_amount = decimal_from_number(target_amount)
                    updated.target_date = target_date
                    updated.is_active = is_active
                elif record_type == "goal_allocation":
                    updated.goal_id = goal_map[goal_label]
                    updated.account_id = account_map[account_label]
                    updated.month = month
                    updated.allocated_amount = decimal_from_number(amount)
                else:
                    updated.name = name.strip()
                    updated.monthly_amount = decimal_from_number(monthly_amount)
                    updated.billing_frequency = billing_frequency
                    updated.category = category
                    updated.is_active = is_active
                    updated.next_payment_date = next_payment_date

                record_updated = True

            if record_updated:
                success_and_refresh("Record updated.")


def render_edit_entries(default_month: date) -> None:
    edit_section = selected_edit_section()
    edit_section = render_edit_subnav(edit_section)
    if edit_section == "accounts":
        render_edit_account()
    else:
        render_edit_monthly_record(default_month)


DELETE_MODELS = RECORD_MODELS


def lookup_names() -> tuple[dict[int, str], dict[int, str]]:
    """Return account and goal names for friendly record previews."""
    with session_scope() as session:
        accounts = session.scalars(select(Account)).all()
        goals = session.scalars(select(Goal)).all()

    account_names = {account.id: account.name for account in accounts}
    goal_names = {goal.id: goal.name for goal in goals}
    return account_names, goal_names


def name_for(lookup: dict[int, str], record_id: int | None) -> str:
    if record_id is None:
        return ""
    return lookup.get(record_id, f"Record {record_id}")


def record_summary(record_type: str, record, account_names: dict[int, str], goal_names: dict[int, str]) -> str:
    """Create a short, human-readable label for selecting records."""
    if record_type == "account":
        return f"{record.name} - {display_label(record.account_type, ACCOUNT_TYPE_LABELS)}"
    if record_type == "snapshot":
        return (
            f"{record.month:%B %Y} - {name_for(account_names, record.account_id)} - "
            f"{display_label(record.snapshot_type, SNAPSHOT_TYPE_LABELS)} - {money(record.balance)}"
        )
    if record_type == "income":
        label = record.label or display_label(record.income_type, INCOME_TYPE_LABELS)
        return f"{record.month:%B %Y} - {label} - Net {money(record.net_amount)}"
    if record_type == "expense":
        return f"{record.month:%B %Y} - {display_label(record.category, EXPENSE_CATEGORY_LABELS)} - {money(record.amount)}"
    if record_type == "transfer":
        return (
            f"{record.month:%B %Y} - {name_for(account_names, record.from_account_id)} to "
            f"{name_for(account_names, record.to_account_id)} - {money(record.amount)}"
        )
    if record_type == "debt_profile":
        return f"{name_for(account_names, record.account_id)} - {display_label(record.debt_type, DEBT_TYPE_LABELS)}"
    if record_type == "goal":
        return f"{record.name} - Target {money(record.target_amount)}"
    if record_type == "goal_allocation":
        return (
            f"{record.month:%B %Y} - {name_for(goal_names, record.goal_id)} from "
            f"{name_for(account_names, record.account_id)} - {money(record.allocated_amount)}"
        )
    return f"{record.name} - {money(record.monthly_amount)} per month"


def record_rows(record_type: str) -> list[dict]:
    """Return display rows with internal record IDs kept out of the table labels."""
    model = DELETE_MODELS[record_type]
    account_names, goal_names = lookup_names()
    with session_scope() as session:
        records = session.scalars(select(model).order_by(model.id)).all()

    rows = []
    for position, record in enumerate(records, start=1):
        summary = record_summary(record_type, record, account_names, goal_names)
        row = {"_record_id": record.id, "Record": f"Entry {position} - {summary}"}
        if record_type == "account":
            row.update(
                {
                    "Account Name": record.name,
                    "Account Type": display_label(record.account_type, ACCOUNT_TYPE_LABELS),
                    "Currency": record.currency,
                    "Status": "Active" if record.is_active else "Inactive",
                    "Emergency Fund": "Yes" if record.is_emergency_fund else "No",
                }
            )
        elif record_type == "snapshot":
            row.update(
                {
                    "Month": record.month.strftime("%B %Y"),
                    "Account": name_for(account_names, record.account_id),
                    "Snapshot": display_label(record.snapshot_type, SNAPSHOT_TYPE_LABELS),
                    "Balance": money(record.balance),
                }
            )
        elif record_type == "income":
            row.update(
                {
                    "Month": record.month.strftime("%B %Y"),
                    "Income Type": display_label(record.income_type, INCOME_TYPE_LABELS),
                    "Description": record.label or "",
                    "Gross Amount": money(record.gross_amount),
                    "Net Amount": money(record.net_amount),
                    "Paid Into": name_for(account_names, record.target_account_id),
                }
            )
        elif record_type == "expense":
            row.update(
                {
                    "Month": record.month.strftime("%B %Y"),
                    "Category": display_label(record.category, EXPENSE_CATEGORY_LABELS),
                    "Amount": money(record.amount),
                    "Paid From": name_for(account_names, record.source_account_id),
                }
            )
        elif record_type == "transfer":
            row.update(
                {
                    "Month": record.month.strftime("%B %Y"),
                    "From": name_for(account_names, record.from_account_id),
                    "To": name_for(account_names, record.to_account_id),
                    "Amount": money(record.amount),
                    "Description": record.label or "",
                }
            )
        elif record_type == "debt_profile":
            row.update(
                {
                    "Debt Account": name_for(account_names, record.account_id),
                    "Debt Type": display_label(record.debt_type, DEBT_TYPE_LABELS),
                    "Annual Interest Rate": f"{record.interest_rate}%",
                    "Minimum Payment": money(record.minimum_payment or Decimal("0.00")),
                    "Notes": record.notes or "",
                }
            )
        elif record_type == "goal":
            row.update(
                {
                    "Goal": record.name,
                    "Target Amount": money(record.target_amount),
                    "Target Date": record.target_date.isoformat() if record.target_date else "",
                    "Status": "Active" if record.is_active else "Inactive",
                }
            )
        elif record_type == "goal_allocation":
            row.update(
                {
                    "Month": record.month.strftime("%B %Y"),
                    "Goal": name_for(goal_names, record.goal_id),
                    "Account": name_for(account_names, record.account_id),
                    "Allocated Amount": money(record.allocated_amount),
                }
            )
        else:
            row.update(
                {
                    "Subscription": record.name,
                    "Monthly Amount": money(record.monthly_amount),
                    "Billing Frequency": display_label(record.billing_frequency, BILLING_FREQUENCY_LABELS),
                    "Category": display_label(record.category, EXPENSE_CATEGORY_LABELS),
                    "Status": "Active" if record.is_active else "Inactive",
                    "Next Payment": record.next_payment_date.isoformat() if record.next_payment_date else "",
                }
            )
        rows.append(row)

    return rows


def record_preview(record_type: str) -> pd.DataFrame:
    rows = record_rows(record_type)
    return pd.DataFrame([{key: value for key, value in row.items() if key != "_record_id"} for row in rows])


def render_delete_entries() -> None:
    st.subheader("🗑️ Delete Record")
    record_type = select_record_type("Record type", key="delete_record_type")
    rows = record_rows(record_type)
    if not rows:
        st.info("No records of this type.")
        return

    st.caption("Select one or more records, confirm, then delete them together.")
    display_rows = []
    record_ids_by_display_row = []
    for row in rows:
        record_ids_by_display_row.append(row["_record_id"])
        display_rows.append({"Select": False, **{key: value for key, value in row.items() if key != "_record_id"}})

    delete_table = pd.DataFrame(display_rows)
    edited_table = st.data_editor(
        delete_table,
        width="stretch",
        hide_index=True,
        key=f"delete_table_{record_type}",
        disabled=[column for column in delete_table.columns if column != "Select"],
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Tick every record you want to delete.",
            )
        },
    )

    selected_indexes = edited_table.index[edited_table["Select"]].tolist()
    selected_record_ids = [record_ids_by_display_row[index] for index in selected_indexes]
    if selected_record_ids:
        st.warning(f"{len(selected_record_ids)} record(s) selected for deletion.")

    confirm = st.checkbox("I understand this will permanently delete the selected record(s).")
    if st.button("Delete selected records", type="primary"):
        if not selected_record_ids:
            st.error("Select at least one record to delete.")
            return
        if not confirm:
            st.error("Tick the confirmation checkbox before deleting.")
            return

        with session_scope() as session:
            for record_id in selected_record_ids:
                record = session.get(DELETE_MODELS[record_type], int(record_id))
                if record is not None:
                    session.delete(record)

        success_and_refresh(f"Deleted {len(selected_record_ids)} record(s).")


def render_entries(month: date) -> None:
    st.subheader("✍️ Entries & Record Management")
    st.caption("Use these forms for normal manual entry. The terminal commands remain available for faster keyboard workflows.")
    section = selected_entry_section()
    section = render_entries_subnav(section)
    if section == "add":
        render_add_entries(month)
    elif section == "edit":
        render_edit_entries(month)
    else:
        render_delete_entries()


def main() -> None:
    inject_css()
    page = selected_page()
    month, month_labels, selected_month_label = selected_month()
    page, selected_month_label = render_top_nav(page, month_labels, selected_month_label)
    if selected_month_label is not None:
        month = date.fromisoformat(f"{selected_month_label}-01")
    render_flash_message()

    if month is None:
        default_month = date.today().replace(day=1)
        if page == "Entries":
            page_header(default_month)
            render_entries(default_month)
            return

        st.markdown(
            """
            <div class="top-panel">
              <h1>Finance Command Centre</h1>
              <p>No monthly data exists yet. Open Entries to add accounts, snapshots, income, expenses, debts, goals, and subscriptions.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    summary = build_monthly_summary(month)
    page_header(month)

    if page == "Entries":
        render_entries(month)
        return

    summary_metrics(summary)

    if page == "Balances":
        render_balances(month)
    elif page == "Statistics":
        render_statistics(summary)
    elif page == "Spending":
        render_spending(month, summary)
    elif page == "Debts":
        render_debts(summary)
    elif page == "Goals":
        render_goals(summary)
    else:
        render_raw(month, summary)


if __name__ == "__main__":
    main()
