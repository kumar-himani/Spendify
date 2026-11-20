import streamlit as st
import pandas as pd
from datetime import datetime
from utils import EXPENSE_CATEGORIES
from validation import validate_budget_limits
from database import (
    save_transaction,
    load_transactions,
    save_budget_limits,
    load_budget_limits
)

# Define the budgeting function
def save_budget_limits_for_user(user_id, budget_limits):
    """Save budget limits to database for specific user"""
    try:
        save_budget_limits(user_id, budget_limits) # Save budget limits to database
        st.success("Budget limits saved successfully!")
    except Exception as e: # Handle errors gracefully and provide user feedback
        st.error(f"Failed to save budget limits: {str(e)}")

def load_budget_limits_for_user(user_id):
    """Load budget limits from database for specific user"""
    try:
        return load_budget_limits(user_id) # Load budget limits from database
    except Exception as e:
        st.error(f"Failed to load budget limits: {str(e)}")
        return {category: 0.0 for category in EXPENSE_CATEGORIES} # Return default budget limits if loading fails

def render_budget_settings(user_id): 
    """Render budget limits settings form"""
    st.subheader("Set Monthly Budget Limits")
    budget_limits = load_budget_limits_for_user(user_id) # Load budget limits for user

    # Create a form to collect user input for budget limits
    col1, col2 = st.columns(2)
    new_limits = {}

    # Iterate over each category and collect user input for budget limits
    with col1:
        for category in EXPENSE_CATEGORIES[:len(EXPENSE_CATEGORIES)//2]:
            new_limits[category] = st.number_input(
                f"{category} ($)",
                value=float(budget_limits.get(category, 0.0)),
                min_value=0.0,
                key=f"budget_{category}"
            )

    with col2:
        for category in EXPENSE_CATEGORIES[len(EXPENSE_CATEGORIES)//2:]:
            new_limits[category] = st.number_input(
                f"{category} ($)",
                value=float(budget_limits.get(category, 0.0)),
                min_value=0.0,
                key=f"budget_{category}"
            )

    if st.button("Save Budget Limits"):
        errors, warnings = validate_budget_limits(new_limits, _this_month_income(user_id))
        for error in errors:
            st.error(error)
        for warning in warnings:
            st.warning(warning)
        if not errors:
            save_budget_limits_for_user(user_id, new_limits)


def _this_month_income(user_id):
    """Total income logged this month, used to sanity-check budget limits."""
    try:
        transactions = load_transactions(user_id)
    except Exception:
        return None
    if transactions.empty:
        return None
    current_month = datetime.now().strftime("%Y-%m")
    this_month = transactions[pd.to_datetime(transactions["date"]).dt.strftime("%Y-%m") == current_month]
    income = this_month.loc[this_month["amount"] > 0, "amount"].astype(float).sum()
    return income or None

def render_budget_overview(user_id):
    """Render budget overview with progress bars"""
    st.subheader("Budget Overview")

    # Load transactions and budget limits
    transactions = load_transactions(user_id)
    budget_limits = load_budget_limits_for_user(user_id)

    if transactions.empty:
        st.info("No transactions found. Add some transactions to see your budget overview!")
        return

    # Calculate current month's expenses
    current_month = datetime.now().strftime("%Y-%m")
    monthly_expenses = transactions[
        (transactions['amount'] < 0) & 
        (pd.to_datetime(transactions['date']).dt.strftime("%Y-%m") == current_month)
    ]

    # Group by category and calculate totals
    category_totals = monthly_expenses.groupby('category')['amount'].sum().abs()

    # Display budget progress for each category
    for category in EXPENSE_CATEGORIES:
        spent = category_totals.get(category, 0.0)
        budget = budget_limits.get(category, 0.0)

        # Create a container for each category
        with st.container():
            st.markdown(f"### {category}")  # Category name as header
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                if budget > 0:
                    # Convert both to float to avoid type issues
                    spent_float = float(spent)
                    progress = min(spent_float / budget, 1.0)
                    progress_color = "red" if progress >= 0.9 else "yellow" if progress >= 0.7 else "normal"
                    st.progress(progress, text=f"${spent:,.2f} / ${budget:,.2f}")
                else:
                    st.progress(0.0, text="No budget set")

            with col2:
                st.markdown(f"**Spent:** ${spent:,.2f}")

            with col3:
                # Convert the spent value to float to match budget type
                remaining = budget - float(spent)
                st.markdown(f"**Left:** ${remaining:,.2f}")

            # Warning if over budget
            if budget > 0 and spent > budget:
                st.warning(f"⚠️ Over budget by ${spent - budget:,.2f}")
            elif budget > 0 and (float(spent) / budget) >= 0.9:
                st.warning(f"⚠️ Near budget limit")

        st.divider()  # Visual separator between categories