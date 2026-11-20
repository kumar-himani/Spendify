import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import re

from utils import initialize_session_state, EXPENSE_CATEGORIES, INCOME_CATEGORIES
from database import (init_database, create_user, verify_user,
                      save_transaction, load_transactions, save_budget_limits,
                      load_budget_limits)
from components import (render_sidebar, render_transaction_form,
                        render_transaction_table, render_monthly_summary,
                        render_category_breakdown)
from ai_assistant import get_spending_insights, get_budget_recommendations
from budgeting import render_budget_settings, render_budget_overview

# Initialize database
init_database()

# Page config
st.set_page_config(page_title="Spendify", page_icon="💰", layout="wide")

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None


def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def login():
    """Handle user login"""
    try:
        user = verify_user(st.session_state.login_username,
                           st.session_state.login_password)
        if user:
            st.session_state.authenticated = True
            st.session_state.user_id = user['id']
            st.session_state.username = user['username']
            st.rerun()
        else:
            st.error("Invalid username or password")
    except Exception as e:
        st.error(f"Login failed: {str(e)}")


def signup():
    """Handle user signup"""
    try:
        if not is_valid_email(st.session_state.signup_email):
            st.error("Please enter a valid email address")
            return

        if st.session_state.signup_password != st.session_state.signup_confirm_password:
            st.error("Passwords do not match")
            return

        user_id = create_user(st.session_state.signup_username,
                              st.session_state.signup_password,
                              st.session_state.signup_email)
        st.session_state.authenticated = True
        st.session_state.user_id = user_id
        st.session_state.username = st.session_state.signup_username
        st.rerun()
    except Exception as e:
        st.error(f"Signup failed: {str(e)}")


# Authentication pages
if not st.session_state.authenticated:
    st.title("💰 Spendify")
    st.write(
        "Your Personal Finance Companion! This program will help you manage your personal finances by tracking income, expenses, and account balances. With clear instructions and intuitive features, you can easily input transaction details, view summaries over specified periods, categorize spending, and analyze your financial habits! We are helping to solve the problem of financial literacy and helping you achieve financial independence. 💰!"
    )

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        with st.form("login_form"):
            st.text_input("Username", key="login_username")
            st.text_input("Password", type="password", key="login_password")
            if st.form_submit_button("Login"):
                login()

    with tab2:
        with st.form("signup_form"):
            st.text_input("Username", key="signup_username")
            st.text_input("Email",
                          key="signup_email",
                          help="Please enter a valid email address")
            st.text_input("Password", type="password", key="signup_password")
            st.text_input("Confirm Password",
                          type="password",
                          key="signup_confirm_password")
            if st.form_submit_button("Sign Up"):
                signup()

else:
    # Main app after authentication
    initialize_session_state()

    # Sidebar with navigation
    with st.sidebar:
        st.title(f"Welcome to Spendify!")
        st.write(f"Hello, {st.session_state.username}!")

        # Navigation menu
        page = st.radio("Navigation", [
            "Dashboard", "Transactions", "Reports", "Budgeting",
            "AI Assistant", "Account Settings"
        ])

        st.divider()
        render_sidebar()  # Original filters

        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    # Main content based on navigation
    if page == "Dashboard":
        st.title("💰 Dashboard")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Quick Add Transaction")
            render_transaction_form(st.session_state.user_id)

        with col2:
            st.subheader("Current Balance")
            transactions = load_transactions(st.session_state.user_id)
            if not transactions.empty:
                balance = transactions["amount"].sum()
                today_transactions = transactions[transactions['date'] ==
                                                  datetime.now().strftime(
                                                      '%Y-%m-%d')]
                st.metric(
                    "Total Balance",
                    f"${balance:,.2f}",
                    delta=f"${today_transactions['amount'].sum():,.2f} today")
            else:
                st.metric("Total Balance", "$0.00", delta="$0.00 today")

    elif page == "Transactions":
        st.title("📝 Transactions")
        render_transaction_table(st.session_state.user_id)

    elif page == "Reports":
        st.title("📊 Financial Reports")
        col1, col2 = st.columns(2)
        with col1:
            render_monthly_summary(st.session_state.user_id)
        with col2:
            render_category_breakdown(st.session_state.user_id)

    elif page == "Budgeting":
        st.title("🎯 Budgeting")

        tab1, tab2 = st.tabs(["Budget Overview", "Budget Settings"])

        with tab1:
            render_budget_overview(st.session_state.user_id)

        with tab2:
            render_budget_settings(st.session_state.user_id)

    elif page == "AI Assistant":
        st.title("🤖 AI Financial Assistant")

        # Load and analyze transactions
        transactions = load_transactions(st.session_state.user_id)
        if not transactions.empty:
            current_month = datetime.now().strftime("%Y-%m")
            monthly_transactions = transactions[pd.to_datetime(
                transactions['date']).dt.strftime("%Y-%m") == current_month]

            # Calculate monthly totals
            monthly_income = monthly_transactions[
                monthly_transactions['amount'] > 0]['amount'].sum()
            monthly_expenses = monthly_transactions[
                monthly_transactions['amount'] < 0]['amount'].sum()

            # Display insights
            with st.expander("💡 Spending Insights", expanded=True):
                insights = get_spending_insights(monthly_transactions)
                if insights:
                    st.write(insights)

            with st.expander("📊 Budget Recommendations", expanded=True):
                recommendations = get_budget_recommendations(
                    monthly_income, monthly_expenses)
                if recommendations:
                    st.write(recommendations)
        else:
            st.info("Add some transactions to get AI-powered insights!")

    elif page == "Account Settings":
        st.title("⚙️ Account Settings")

        # Profile Settings
        st.header("Profile Settings")
        with st.form("profile_settings"):
            display_name = st.text_input("Display Name",
                                         st.session_state.username)
            email = st.text_input("Email Address")
            st.form_submit_button("Update Profile")

        # Notification Settings
        st.header("Notification Settings")
        st.checkbox("Email notifications for budget alerts", value=True)
        st.checkbox("Monthly spending report", value=True)
        st.checkbox("Bill payment reminders", value=True)

        # Data Export
        st.header("Data Management")
        if st.button("Export Transactions (CSV)"):
            transactions = load_transactions(st.session_state.user_id)
            if not transactions.empty:
                transactions.to_csv("transactions_export.csv", index=False)
                st.success("Data exported successfully!")
            else:
                st.info("No transactions to export")

        # Account Security
        st.header("Security")
        if st.button("Change Password"):
            st.info("Password change functionality coming soon!")
