import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import EXPENSE_CATEGORIES, INCOME_CATEGORIES, validate_transaction
from database import (
    save_transaction,
    load_transactions,
    save_budget_limits,
    load_budget_limits
)

def render_sidebar():
    """Render the sidebar filters"""
    with st.sidebar:
        st.header("Filters")

        st.session_state.filter_type = st.selectbox(
            "Transaction Type",
            ["All", "Income", "Expense"]
        )

        categories = ["All"] + INCOME_CATEGORIES + EXPENSE_CATEGORIES
        st.session_state.filter_category = st.selectbox(
            "Category",
            categories
        )

        st.session_state.date_range = st.date_input(
            "Date Range",
            value=st.session_state.date_range,
            key="date_range_picker"
        )

def render_transaction_form(user_id):
    """Render the transaction input form"""
    with st.form("transaction_form"):
        transaction_type = st.selectbox(
            "Type",
            ["Expense", "Income"]
        )

        categories = INCOME_CATEGORIES if transaction_type == "Income" else EXPENSE_CATEGORIES
        category = st.selectbox("Category", categories)

        amount = st.number_input("Amount ($)", min_value=0.01, format="%f")
        date = st.date_input("Date", datetime.now())
        description = st.text_input("Description")

        submitted = st.form_submit_button("Add Transaction")

        if submitted:
            valid, error_message = validate_transaction(amount, category, date, description)
            if valid:
                try:
                    save_transaction(
                        user_id,
                        date.strftime("%Y-%m-%d"),
                        amount if transaction_type == "Income" else -amount,
                        category,
                        description,
                        transaction_type
                    )
                    st.success("Transaction added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save transaction: {str(e)}")
            else:
                st.error(error_message)

def render_transaction_table(user_id):
    """Render the transactions table with edit/delete functionality"""
    try:
        transactions = load_transactions(user_id)

        if transactions.empty:
            st.info("No transactions found. Add some transactions to get started!")
            return

        # Convert date column to datetime for proper comparison
        transactions['date'] = pd.to_datetime(transactions['date'])

        # Apply filters
        if st.session_state.filter_type != "All":
            transactions = transactions[transactions["type"] == st.session_state.filter_type]

        if st.session_state.filter_category != "All":
            transactions = transactions[transactions["category"] == st.session_state.filter_category]

        if len(st.session_state.date_range) == 2:
            start_date, end_date = pd.to_datetime(st.session_state.date_range[0]), pd.to_datetime(st.session_state.date_range[1])
            transactions = transactions[
                (transactions["date"].dt.date >= start_date.date()) &
                (transactions["date"].dt.date <= end_date.date())
            ]

        # Format date for display
        transactions['date'] = transactions['date'].dt.strftime('%Y-%m-%d')

        # Display table
        if not transactions.empty:
            for _, row in transactions.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    st.write(f"**{row['description']}**\n{row['date']}")

                with col2:
                    st.write(f"**{row['category']}**\n{row['type']}")

                with col3:
                    amount_color = "green" if row["amount"] > 0 else "red"
                    st.markdown(f"<h3 style='color: {amount_color}'>${abs(row['amount']):,.2f}</h3>", unsafe_allow_html=True)

                st.divider()
        else:
            st.info("No transactions found for the selected filters.")
    except Exception as e:
        st.error(f"Failed to load transactions: {str(e)}")

def render_monthly_summary(user_id):
    """Render monthly summary charts"""
    try:
        transactions = load_transactions(user_id)

        if transactions.empty:
            st.info("Add some transactions to see your monthly summary!")
            return

        # Add date range selector
        st.subheader("Customize Time Range")
        col1, col2 = st.columns(2)

        # Convert dates for the selector
        transactions['date'] = pd.to_datetime(transactions['date'])
        min_date = transactions['date'].min().date()
        max_date = transactions['date'].max().date()

        with col1:
            start_date = st.date_input("Start Date", min_date)
        with col2:
            end_date = st.date_input("End Date", max_date)

        # Filter transactions by date range
        filtered_transactions = transactions[
            (transactions['date'].dt.date >= start_date) & 
            (transactions['date'].dt.date <= end_date)
        ]

        if filtered_transactions.empty:
            st.warning("No transactions found in the selected date range.")
            return

        # Add chart type selector
        chart_type = st.selectbox(
            "Select Chart Type",
            ["Bar Chart", "Line Chart", "Area Chart"]
        )

        # Calculate metrics
        total_income = filtered_transactions[filtered_transactions["amount"] > 0]["amount"].sum()
        total_expenses = abs(filtered_transactions[filtered_transactions["amount"] < 0]["amount"].sum())
        net_savings = total_income - total_expenses
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0

        # Display key metrics
        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
        with metrics_col1:
            st.metric("Total Income", f"${total_income:,.2f}")
        with metrics_col2:
            st.metric("Total Expenses", f"${total_expenses:,.2f}")
        with metrics_col3:
            st.metric("Net Savings", f"${net_savings:,.2f}")
        with metrics_col4:
            st.metric("Savings Rate", f"{savings_rate:.1f}%")

        # Prepare data for visualization
        monthly_summary = filtered_transactions.groupby(
            filtered_transactions['date'].dt.strftime('%Y-%m')
        )["amount"].sum().reset_index()

        # Create visualization based on selected chart type
        fig = go.Figure()

        if chart_type == "Bar Chart":
            fig.add_trace(go.Bar(
                x=monthly_summary["date"],
                y=monthly_summary["amount"],
                marker_color=["red" if x < 0 else "green" for x in monthly_summary["amount"]]
            ))
        elif chart_type == "Line Chart":
            fig.add_trace(go.Scatter(
                x=monthly_summary["date"],
                y=monthly_summary["amount"],
                mode='lines+markers'
            ))
        else:  # Area Chart
            fig.add_trace(go.Scatter(
                x=monthly_summary["date"],
                y=monthly_summary["amount"],
                fill='tozeroy'
            ))

        fig.update_layout(
            title="Monthly Net Income",
            xaxis_title="Month",
            yaxis_title="Amount ($)",
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        # Add trend analysis
        if len(monthly_summary) > 1:
            trend = "increasing" if monthly_summary["amount"].iloc[-1] > monthly_summary["amount"].iloc[0] else "decreasing"
            avg_monthly_change = monthly_summary["amount"].diff().mean()
            st.subheader("Trend Analysis")
            st.write(f"Your net income is {trend} with an average monthly change of ${abs(avg_monthly_change):,.2f}")

    except Exception as e:
        st.error(f"Failed to render monthly summary: {str(e)}")

def render_category_breakdown(user_id):
    """Render category breakdown pie charts"""
    try:
        transactions = load_transactions(user_id)

        if transactions.empty:
            st.info("Add some transactions to see your category breakdown!")
            return

        # Add time period selector
        st.subheader("Select Time Period")
        period = st.selectbox(
            "Analysis Period",
            ["All Time", "This Month", "Last Month", "Last 3 Months", "Last 6 Months", "This Year"]
        )

        # Convert date column to datetime
        transactions['date'] = pd.to_datetime(transactions['date'])

        # Filter transactions based on selected period
        if period != "All Time":
            today = pd.Timestamp.now()
            if period == "This Month":
                mask = transactions["date"].dt.to_period('M') == today.to_period('M')
            elif period == "Last Month":
                last_month = today - pd.DateOffset(months=1)
                mask = transactions["date"].dt.to_period('M') == last_month.to_period('M')
            elif period == "Last 3 Months":
                three_months_ago = today - pd.DateOffset(months=3)
                mask = transactions["date"] >= three_months_ago
            elif period == "Last 6 Months":
                six_months_ago = today - pd.DateOffset(months=6)
                mask = transactions["date"] >= six_months_ago
            elif period == "This Year":
                mask = transactions["date"].dt.year == today.year

            transactions = transactions[mask]

        if transactions.empty:
            st.warning("No transactions found for the selected time period.")
            return

        # Expenses breakdown
        expenses = transactions[transactions["amount"] < 0].copy()
        if not expenses.empty:
            st.subheader("Expense Analysis")

            # Calculate absolute values for expenses
            expenses["amount"] = expenses["amount"].abs()
            expense_by_category = expenses.groupby("category")["amount"].sum()

            # Calculate percentages
            total_expenses = expense_by_category.sum()
            expense_percentages = (expense_by_category / total_expenses * 100).round(1)

            # Create pie chart
            fig1 = px.pie(
                values=expense_by_category.values,
                names=expense_by_category.index,
                title=f"Expense Breakdown by Category (Total: ${total_expenses:,.2f})"
            )
            st.plotly_chart(fig1, use_container_width=True)

            # Display detailed breakdown
            st.write("Detailed Expense Breakdown:")
            for category, amount in expense_by_category.items():
                percentage = expense_percentages[category]
                st.write(f"- {category}: ${amount:,.2f} ({percentage}%)")

        # Income breakdown
        income = transactions[transactions["amount"] > 0]
        if not income.empty:
            st.subheader("Income Analysis")

            income_by_category = income.groupby("category")["amount"].sum()
            total_income = income_by_category.sum()
            income_percentages = (income_by_category / total_income * 100).round(1)

            fig2 = px.pie(
                values=income_by_category.values,
                names=income_by_category.index,
                title=f"Income Breakdown by Category (Total: ${total_income:,.2f})"
            )
            st.plotly_chart(fig2, use_container_width=True)

            st.write("Detailed Income Breakdown:")
            for category, amount in income_by_category.items():
                percentage = income_percentages[category]
                st.write(f"- {category}: ${amount:,.2f} ({percentage}%)")

    except Exception as e:
        st.error(f"Failed to render category breakdown: {str(e)}")