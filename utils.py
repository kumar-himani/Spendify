import streamlit as st
from datetime import datetime

EXPENSE_CATEGORIES = [
    "Food & Dining",
    "Transportation",
    "Housing",
    "Utilities",
    "Healthcare",
    "Entertainment",
    "Shopping",
    "Education",
    "Travel",
    "Other"
]

INCOME_CATEGORIES = [
    "Salary",
    "Investments",
    "Freelance",
    "Gifts",
    "Other Income"
]

def initialize_session_state():
    """Initialize session state variables"""
    if "show_transaction_editor" not in st.session_state:
        st.session_state.show_transaction_editor = False
    
    if "edit_transaction_id" not in st.session_state:
        st.session_state.edit_transaction_id = None
    
    if "filter_category" not in st.session_state:
        st.session_state.filter_category = "All"
    
    if "filter_type" not in st.session_state:
        st.session_state.filter_type = "All"
    
    if "date_range" not in st.session_state:
        st.session_state.date_range = [
            datetime.now().replace(day=1),
            datetime.now()
        ]
