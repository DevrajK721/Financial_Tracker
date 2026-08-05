from __future__ import annotations

# Reports combine service calculations into something useful to print or display.
# Later, Streamlit can call this file to power the dashboard.

from datetime import date

from src.services.debt_analytics import calculate_debt_summary, estimate_debt_payoff, project_debt_balance
from src.services.emergency_fund import calculate_emergency_fund_details
from src.services.goal_allocation import calculate_goal_progress
from src.services.investment_attribution import estimate_investment_growth
from src.services.net_worth import calculate_net_worth_details
from src.services.projections import average_monthly_savings, project_goal_completion, project_net_worth
from src.services.savings_rate import calculate_savings_details
from src.services.spending_baseline import compare_spending_to_baseline


def build_monthly_summary(month: date) -> dict:
    """Build the main monthly finance summary used by CLI and dashboard code."""
    return {
        "month": month.isoformat(),
        "savings": calculate_savings_details(month),
        "net_worth": calculate_net_worth_details(month),
        "debt": calculate_debt_summary(month),
        "debt_payoff": estimate_debt_payoff(month),
        "debt_projection": project_debt_balance(month),
        "emergency_fund": calculate_emergency_fund_details(month),
        "goals": calculate_goal_progress(month),
        "spending_vs_baseline": compare_spending_to_baseline(month),
        "investment_growth": estimate_investment_growth(month),
        "average_monthly_savings": average_monthly_savings(month),
        "net_worth_projection": project_net_worth(month),
        "goal_projection": project_goal_completion(month),
    }
