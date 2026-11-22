"""Input validation for Spendify.

Each validator returns a list of error messages (an empty list means the input is valid).

Two kinds of checks:
- Syntactic: is the value the right shape? (a number, a non-empty string, a valid email format)
- Semantic: does the value make sense in context? (a category that matches the transaction
  type, a date that isn't in the future, budget limits that fit within income)
"""

import re
from datetime import date, datetime

from utils import EXPENSE_CATEGORIES, INCOME_CATEGORIES

MAX_AMOUNT = 1_000_000
MAX_DESCRIPTION_LENGTH = 200
EARLIEST_DATE = date(2000, 1, 1)

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,30}$")


def _to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def is_valid_email(email):
    return bool(EMAIL_PATTERN.match(str(email or "").strip()))


def validate_transaction(amount, category, transaction_date, description, transaction_type, today=None):
    """Validate a new or edited transaction."""
    errors = []
    today = today or date.today()

    # Syntactic checks
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        errors.append("Amount must be a number.")
        amount = None

    if amount is not None:
        if amount <= 0:
            errors.append("Amount must be greater than $0.")
        elif amount > MAX_AMOUNT:
            errors.append(f"Amount can't be more than ${MAX_AMOUNT:,}.")
        elif round(amount, 2) != round(amount, 6):
            errors.append("Amount can't have more than 2 decimal places.")

    description = str(description or "").strip()
    if not description:
        errors.append("Description is required.")
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer.")

    parsed_date = _to_date(transaction_date)
    if parsed_date is None:
        errors.append("Date must be a valid date.")

    if transaction_type not in ("Income", "Expense"):
        errors.append("Type must be Income or Expense.")

    # Semantic checks
    if transaction_type == "Income" and category not in INCOME_CATEGORIES:
        errors.append(f"'{category}' isn't an income category.")
    elif transaction_type == "Expense" and category not in EXPENSE_CATEGORIES:
        errors.append(f"'{category}' isn't an expense category.")

    if parsed_date is not None:
        if parsed_date > today:
            errors.append("Date can't be in the future.")
        elif parsed_date < EARLIEST_DATE:
            errors.append(f"Date can't be before {EARLIEST_DATE:%B %d, %Y}.")

    return errors


def password_errors(password, username=""):
    """Password rules shared by sign-up and change password."""
    password = password or ""
    username = str(username or "").strip()

    if len(password) < 8:
        return ["Password must be at least 8 characters."]
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        return ["Password must include at least one letter and one number."]
    if username and username.lower() in password.lower():
        return ["Password can't contain your username."]
    return []


def validate_signup(username, email, password, confirm_password):
    """Validate the sign-up form."""
    errors = []
    username = str(username or "").strip()

    if not USERNAME_PATTERN.match(username):
        errors.append("Username must be 3-30 characters: letters, numbers, or underscores.")
    if not is_valid_email(email):
        errors.append("Please enter a valid email address.")

    errors.extend(password_errors(password, username))

    if (password or "") != (confirm_password or ""):
        errors.append("Passwords do not match.")

    return errors


def validate_password_change(username, current_password, new_password, confirm_password):
    """Validate the change password form. Checking the current password happens in the database layer."""
    errors = []

    if not current_password:
        errors.append("Please enter your current password.")

    errors.extend(password_errors(new_password, username))

    if (new_password or "") != (confirm_password or ""):
        errors.append("New passwords do not match.")
    elif new_password and new_password == current_password:
        errors.append("Your new password must be different from your current one.")

    return errors


def validate_budget_limits(limits, monthly_income=None):
    """Validate budget limits.

    Returns (errors, warnings). Errors block saving; warnings are shown but allowed.
    """
    errors, warnings = [], []

    for category, amount in limits.items():
        if category not in EXPENSE_CATEGORIES:
            errors.append(f"'{category}' isn't an expense category.")
        try:
            value = float(amount)
        except (TypeError, ValueError):
            errors.append(f"{category} budget must be a number.")
            continue
        if value < 0:
            errors.append(f"{category} budget can't be negative.")

    if not errors and monthly_income:
        total = sum(float(v) for v in limits.values())
        if total > monthly_income:
            warnings.append(
                f"Your budgets add up to ${total:,.2f}, which is more than this month's "
                f"income of ${monthly_income:,.2f}."
            )

    return errors, warnings
