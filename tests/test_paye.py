from __future__ import annotations

from decimal import Decimal

from src.services.paye import estimate_monthly_salary


def test_taxable_benefits_increase_taxable_income_without_adding_cash() -> None:
    without_benefits = estimate_monthly_salary(
        gross_monthly=Decimal("3000"),
        pension_salary_sacrifice=Decimal("100"),
        taxable_benefits_monthly=Decimal("0"),
        student_loan_plan="plan_2",
    )
    with_benefits = estimate_monthly_salary(
        gross_monthly=Decimal("3000"),
        pension_salary_sacrifice=Decimal("100"),
        taxable_benefits_monthly=Decimal("200"),
        student_loan_plan="plan_2",
    )

    assert with_benefits.taxable_monthly == Decimal("3100.00")
    assert without_benefits.taxable_monthly == Decimal("2900.00")
    assert with_benefits.income_tax > without_benefits.income_tax
    assert with_benefits.net_monthly < without_benefits.net_monthly


def test_one_off_bonus_is_not_treated_as_permanent_monthly_salary() -> None:
    regular = estimate_monthly_salary(
        gross_monthly=Decimal("3000"),
        pension_salary_sacrifice=Decimal("100"),
        taxable_benefits_monthly=Decimal("0"),
        one_off_bonus=Decimal("0"),
        student_loan_plan="plan_2",
    )
    bonus_month = estimate_monthly_salary(
        gross_monthly=Decimal("3000"),
        pension_salary_sacrifice=Decimal("100"),
        taxable_benefits_monthly=Decimal("0"),
        one_off_bonus=Decimal("1000"),
        student_loan_plan="plan_2",
    )

    assert bonus_month.one_off_bonus == Decimal("1000.00")
    assert bonus_month.taxable_monthly == Decimal("3900.00")
    assert bonus_month.income_tax > regular.income_tax
    assert bonus_month.national_insurance > regular.national_insurance
    assert bonus_month.student_loan > regular.student_loan
    assert bonus_month.net_monthly > regular.net_monthly


def test_voluntary_student_loan_payment_reduces_net_cash_only() -> None:
    regular = estimate_monthly_salary(
        gross_monthly=Decimal("3000"),
        pension_salary_sacrifice=Decimal("100"),
        taxable_benefits_monthly=Decimal("0"),
        one_off_bonus=Decimal("0"),
        student_loan_plan="plan_2",
        voluntary_student_loan_payment=Decimal("0"),
    )
    voluntary = estimate_monthly_salary(
        gross_monthly=Decimal("3000"),
        pension_salary_sacrifice=Decimal("100"),
        taxable_benefits_monthly=Decimal("0"),
        one_off_bonus=Decimal("0"),
        student_loan_plan="plan_2",
        voluntary_student_loan_payment=Decimal("50"),
    )

    assert voluntary.student_loan == regular.student_loan
    assert voluntary.income_tax == regular.income_tax
    assert voluntary.voluntary_student_loan_payment == Decimal("50.00")
    assert voluntary.net_monthly == regular.net_monthly - Decimal("50.00")
