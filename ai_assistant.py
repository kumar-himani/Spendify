import os
import openai
import streamlit as st
from datetime import datetime
import pandas as pd
from data_manager import load_transactions

# Initialize OpenAI client with proper error handling
def get_openai_client():
    """Initialize OpenAI client with error handling"""
    try:
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        client = openai.OpenAI()
        return client
    except Exception as e:
        st.error(f"Error initializing OpenAI client: {str(e)}")
        return None

def get_spending_insights(transactions_df):
    """Generate pre-defined insights about spending patterns"""
    try:
        if transactions_df.empty:
            return "Please add some transactions to get spending insights."

        # Create an input box for user questions
        user_question = st.text_input("Ask me about your finances!")

        if not user_question:
            return "Ask me a question about your finances, and I'll provide personalized advice!"

        # W2 form explanation
        if "w2" in user_question.lower() or "w-2" in user_question.lower():
            return """
            A W-2 form is an important tax document that reports your annual wages and tax withholdings:

            Key Components:
            • Wages and salary earned during the year
            • Federal income tax withheld
            • State and local taxes withheld
            • Social Security and Medicare taxes withheld
            • Employer contributions to benefits

            Important Notes:
            • Employers must send W-2s by January 31st
            • You need this form to file your taxes
            • Keep copies for at least 3 years
            • Verify all information is correct
            • Contact HR if you find any errors

            The W-2 form is essential for accurate tax filing and maintaining your financial records.
            """

        # Food budget recommendations
        if "food" in user_question.lower() or "budget" in user_question.lower():
            return """
            Smart Food Budgeting Recommendations:

            Monthly Budget Breakdown:
            • Groceries: 70% of food budget
            • Dining out: 30% of food budget

            Money-Saving Tips:
            • Plan meals weekly
            • Buy in bulk for non-perishables
            • Use grocery store loyalty programs
            • Cook meals at home
            • Bring lunch to work
            • Look for seasonal produce
            • Compare prices between stores
            • Use coupons and store apps

            Recommended Actions:
            1. Track all food expenses for a month
            2. Identify areas of overspending
            3. Set realistic grocery and dining-out limits
            4. Create a meal plan before shopping
            5. Build an emergency food fund

            Remember: A well-planned food budget helps you eat healthy while saving money!
            """

        # Default response for other questions
        return "I can help you understand W2 forms or provide food budgeting advice. Please ask me about either of these topics!"

    except Exception as e:
        st.error(f"Unable to generate insights: {str(e)}")
        return "Unable to generate insights at this time. Please try again later."

def get_budget_recommendations(income, expenses):
    """Get pre-defined budget recommendations"""
    try:
        if income <= 0:
            return "Please add some income transactions to get budget recommendations."

        recommendations = """
        Personalized Budget Recommendations:

        Suggested Monthly Budget Allocation:
        • Housing: 30% of income
        • Food: 15% of income
        • Transportation: 10% of income
        • Utilities: 10% of income
        • Savings: 20% of income
        • Entertainment: 5% of income
        • Other: 10% of income

        Key Recommendations:
        1. Build an emergency fund covering 3-6 months of expenses
        2. Automate your savings with direct deposits
        3. Use the 50/30/20 rule (50% needs, 30% wants, 20% savings)
        4. Track all expenses using our app
        5. Review and adjust your budget monthly

        Tips for Success:
        • Set realistic goals
        • Use cash for discretionary spending
        • Look for ways to reduce fixed expenses
        • Consider additional income sources
        • Review subscriptions regularly
        """

        return recommendations

    except Exception as e:
        st.error(f"Unable to generate recommendations: {str(e)}")
        return "Unable to generate recommendations at this time. Please try again later."