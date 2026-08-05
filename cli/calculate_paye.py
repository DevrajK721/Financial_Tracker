from __future__ import annotations

# Standalone PAYE calculator for quick checks without saving income rows.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import ask_decimal, ask_optional_text
from src.services.paye import STUDENT_LOAN_MONTHLY_THRESHOLDS, estimate_monthly_salary


def main() -> None:
    gross_monthly = ask_decimal("Gross monthly salary: ")
    one_off_bonus = ask_decimal("One-off bonus in this payroll [0 if none]: ")
    pension_salary_sacrifice = ask_decimal("Pension salary sacrifice [0 if none]: ")
    taxable_benefits_monthly = ask_decimal("Taxable benefits monthly [0 if none]: ")
    student_loan_plan = ask_optional_text("Student loan plan [plan_1/plan_2/plan_4/plan_5, optional]: ")
    voluntary_student_loan_payment = ask_decimal("Additional voluntary SFE/student loan payment [0 if none]: ")
    has_postgraduate_loan = input("Postgraduate loan? [y/N]: ").strip().lower() in {"y", "yes"}

    if student_loan_plan and student_loan_plan not in STUDENT_LOAN_MONTHLY_THRESHOLDS:
        valid_plans = ", ".join(STUDENT_LOAN_MONTHLY_THRESHOLDS)
        raise ValueError(f"Unknown student loan plan. Use one of: {valid_plans}")

    estimate = estimate_monthly_salary(
        gross_monthly=gross_monthly,
        pension_salary_sacrifice=pension_salary_sacrifice,
        taxable_benefits_monthly=taxable_benefits_monthly,
        one_off_bonus=one_off_bonus,
        student_loan_plan=student_loan_plan,
        voluntary_student_loan_payment=voluntary_student_loan_payment,
        has_postgraduate_loan=has_postgraduate_loan,
    )

    print(f"Gross monthly: {estimate.gross_monthly}")
    print(f"One-off bonus: {estimate.one_off_bonus}")
    print(f"Pension salary sacrifice: {estimate.pension_salary_sacrifice}")
    print(f"Taxable benefits: {estimate.taxable_benefits_monthly}")
    print(f"Taxable monthly: {estimate.taxable_monthly}")
    print(f"Income tax: {estimate.income_tax}")
    print(f"National Insurance: {estimate.national_insurance}")
    print(f"SFE/student loan: {estimate.student_loan}")
    print(f"Voluntary SFE/student loan payment: {estimate.voluntary_student_loan_payment}")
    print(f"Postgraduate loan: {estimate.postgraduate_loan}")
    print(f"Estimated net monthly: {estimate.net_monthly}")


if __name__ == "__main__":
    main()
