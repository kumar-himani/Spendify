from datetime import date

from validation import validate_budget_limits, validate_signup, validate_transaction

TODAY = date(2025, 3, 16)


def check(**overrides):
    fields = dict(amount=25.50, category="Food & Dining", transaction_date=date(2025, 3, 1),
                  description="Groceries", transaction_type="Expense", today=TODAY)
    fields.update(overrides)
    return validate_transaction(**fields)


def test_valid_transaction_passes():
    assert check() == []


def test_amount_must_be_positive_number():
    assert check(amount=0)
    assert check(amount=-5)
    assert check(amount="abc")


def test_amount_limits_and_decimals():
    assert check(amount=2_000_000)
    assert check(amount=10.555)


def test_description_required_and_limited():
    assert check(description="   ")
    assert check(description="x" * 201)


def test_category_must_match_type():
    assert check(category="Salary", transaction_type="Expense")
    assert check(category="Shopping", transaction_type="Income")
    assert check(category="Salary", transaction_type="Income") == []


def test_date_cannot_be_in_future_or_too_old():
    assert check(transaction_date=date(2025, 3, 17))
    assert check(transaction_date=date(1999, 12, 31))
    assert check(transaction_date="2025-03-01") == []
    assert check(transaction_date="not a date")


def test_signup_rules():
    assert validate_signup("himani_k", "h@example.com", "budget2025", "budget2025") == []
    assert validate_signup("hk", "h@example.com", "budget2025", "budget2025")
    assert validate_signup("himani", "not-an-email", "budget2025", "budget2025")
    assert validate_signup("himani", "h@example.com", "short1", "short1")
    assert validate_signup("himani", "h@example.com", "allletters", "allletters")
    assert validate_signup("himani", "h@example.com", "himani123", "himani123")
    assert validate_signup("himani", "h@example.com", "budget2025", "budget2026")


def test_budget_limits():
    errors, warnings = validate_budget_limits({"Housing": 500, "Shopping": 100}, monthly_income=1000)
    assert errors == [] and warnings == []

    errors, _ = validate_budget_limits({"Housing": -1})
    assert errors

    errors, _ = validate_budget_limits({"Salary": 100})
    assert errors

    _, warnings = validate_budget_limits({"Housing": 900, "Shopping": 300}, monthly_income=1000)
    assert warnings
