from __future__ import annotations

# PAYE estimate service.
# This is deliberately separate from MonthlyIncome so tax rules can change
# without changing how monthly income rows are stored.

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


MONEY = Decimal("0.01")

PERSONAL_ALLOWANCE = Decimal("12570")
PERSONAL_ALLOWANCE_TAPER_START = Decimal("100000")
PERSONAL_ALLOWANCE_TAPER_END = Decimal("125140")

ENGLAND_WALES_NI_TAX_BANDS = (
    (Decimal("37700"), Decimal("0.20")),
    (Decimal("87440"), Decimal("0.40")),
    (None, Decimal("0.45")),
)

NI_PRIMARY_THRESHOLD_MONTHLY = Decimal("1048")
NI_UPPER_EARNINGS_LIMIT_MONTHLY = Decimal("4189")
NI_MAIN_RATE = Decimal("0.08")
NI_ADDITIONAL_RATE = Decimal("0.02")

STUDENT_LOAN_MONTHLY_THRESHOLDS = {
    "plan_1": Decimal("2241.66"),
    "plan_2": Decimal("2448.75"),
    "plan_4": Decimal("2816.25"),
    "plan_5": Decimal("2083.33"),
}
STUDENT_LOAN_RATE = Decimal("0.09")
POSTGRADUATE_LOAN_MONTHLY_THRESHOLD = Decimal("1750")
POSTGRADUATE_LOAN_RATE = Decimal("0.06")


@dataclass(frozen=True)
class PayeEstimate:
    gross_monthly: Decimal
    one_off_bonus: Decimal
    pension_salary_sacrifice: Decimal
    taxable_benefits_monthly: Decimal
    taxable_monthly: Decimal
    income_tax: Decimal
    national_insurance: Decimal
    student_loan: Decimal
    voluntary_student_loan_payment: Decimal
    postgraduate_loan: Decimal
    net_monthly: Decimal


def money(value: Decimal) -> Decimal:
    """Round money to pennies."""
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def calculate_personal_allowance(annual_income: Decimal) -> Decimal:
    """Apply the standard personal allowance taper above 100,000."""
    if annual_income <= PERSONAL_ALLOWANCE_TAPER_START:
        return PERSONAL_ALLOWANCE

    if annual_income >= PERSONAL_ALLOWANCE_TAPER_END:
        return Decimal("0")

    reduction = (annual_income - PERSONAL_ALLOWANCE_TAPER_START) / Decimal("2")
    return max(Decimal("0"), PERSONAL_ALLOWANCE - reduction)


def calculate_income_tax_annual(taxable_annual_income: Decimal) -> Decimal:
    """Estimate annual income tax for England, Wales, and Northern Ireland bands."""
    personal_allowance = calculate_personal_allowance(taxable_annual_income)
    remaining = max(Decimal("0"), taxable_annual_income - personal_allowance)
    total_tax = Decimal("0")

    for band_width, rate in ENGLAND_WALES_NI_TAX_BANDS:
        if remaining <= 0:
            break

        taxable_in_band = remaining if band_width is None else min(remaining, band_width)
        total_tax += taxable_in_band * rate
        remaining -= taxable_in_band

    return money(total_tax)


def calculate_employee_ni_monthly(niable_monthly_income: Decimal) -> Decimal:
    """Estimate employee Class 1 National Insurance for category A."""
    if niable_monthly_income <= NI_PRIMARY_THRESHOLD_MONTHLY:
        return Decimal("0.00")

    main_band = min(niable_monthly_income, NI_UPPER_EARNINGS_LIMIT_MONTHLY) - NI_PRIMARY_THRESHOLD_MONTHLY
    additional_band = max(Decimal("0"), niable_monthly_income - NI_UPPER_EARNINGS_LIMIT_MONTHLY)

    return money((main_band * NI_MAIN_RATE) + (additional_band * NI_ADDITIONAL_RATE))


def calculate_student_loan_monthly(monthly_income: Decimal, plan: str | None) -> Decimal:
    """Estimate monthly student loan repayment for one plan."""
    if not plan:
        return Decimal("0.00")

    threshold = STUDENT_LOAN_MONTHLY_THRESHOLDS[plan]
    return money(max(Decimal("0"), monthly_income - threshold) * STUDENT_LOAN_RATE)


def calculate_postgraduate_loan_monthly(monthly_income: Decimal, has_postgraduate_loan: bool) -> Decimal:
    """Estimate monthly postgraduate loan repayment."""
    if not has_postgraduate_loan:
        return Decimal("0.00")

    return money(max(Decimal("0"), monthly_income - POSTGRADUATE_LOAN_MONTHLY_THRESHOLD) * POSTGRADUATE_LOAN_RATE)


def estimate_monthly_salary(
    gross_monthly: Decimal,
    pension_salary_sacrifice: Decimal = Decimal("0.00"),
    taxable_benefits_monthly: Decimal = Decimal("0.00"),
    one_off_bonus: Decimal = Decimal("0.00"),
    student_loan_plan: str | None = None,
    voluntary_student_loan_payment: Decimal = Decimal("0.00"),
    has_postgraduate_loan: bool = False,
) -> PayeEstimate:
    """Estimate monthly take-home pay from gross monthly salary."""
    regular_taxable_monthly = gross_monthly - pension_salary_sacrifice + taxable_benefits_monthly
    taxable_monthly = regular_taxable_monthly + one_off_bonus
    regular_taxable_annual = regular_taxable_monthly * Decimal("12")
    taxable_annual_with_bonus = regular_taxable_annual + one_off_bonus

    regular_annual_tax = calculate_income_tax_annual(regular_taxable_annual)
    annual_tax_with_bonus = calculate_income_tax_annual(taxable_annual_with_bonus)
    bonus_tax = annual_tax_with_bonus - regular_annual_tax
    income_tax = money((regular_annual_tax / Decimal("12")) + bonus_tax)
    national_insurance = calculate_employee_ni_monthly(taxable_monthly)
    student_loan = calculate_student_loan_monthly(taxable_monthly, student_loan_plan)
    voluntary_student_loan_payment = money(voluntary_student_loan_payment)
    postgraduate_loan = calculate_postgraduate_loan_monthly(taxable_monthly, has_postgraduate_loan)
    net_monthly = money(
        gross_monthly
        + one_off_bonus
        - pension_salary_sacrifice
        - income_tax
        - national_insurance
        - student_loan
        - voluntary_student_loan_payment
        - postgraduate_loan
    )

    return PayeEstimate(
        gross_monthly=money(gross_monthly),
        one_off_bonus=money(one_off_bonus),
        pension_salary_sacrifice=money(pension_salary_sacrifice),
        taxable_benefits_monthly=money(taxable_benefits_monthly),
        taxable_monthly=money(taxable_monthly),
        income_tax=income_tax,
        national_insurance=national_insurance,
        student_loan=student_loan,
        voluntary_student_loan_payment=voluntary_student_loan_payment,
        postgraduate_loan=postgraduate_loan,
        net_monthly=net_monthly,
    )
