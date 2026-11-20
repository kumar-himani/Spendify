import pandas as pd
import os
from datetime import datetime

TRANSACTIONS_FILE = "data/transactions.csv"

def ensure_data_file():
    """Ensure the transactions CSV file exists"""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    if not os.path.exists(TRANSACTIONS_FILE):
        df = pd.DataFrame(columns=[
            "id", "date", "amount", "category", "description", "type"
        ])
        df.to_csv(TRANSACTIONS_FILE, index=False)

def load_transactions():
    """Load transactions from CSV file"""
    ensure_data_file()
    df = pd.read_csv(TRANSACTIONS_FILE)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df

def save_transaction(date, amount, category, description, transaction_type):
    """Save a new transaction to CSV file"""
    df = load_transactions()
    new_id = len(df) + 1
    
    new_transaction = pd.DataFrame([{
        "id": new_id,
        "date": date,
        "amount": amount if transaction_type == "Income" else -amount,
        "category": category,
        "description": description,
        "type": transaction_type
    }])
    
    df = pd.concat([df, new_transaction], ignore_index=True)
    df.to_csv(TRANSACTIONS_FILE, index=False)

def update_transaction(transaction_id, date, amount, category, description, transaction_type):
    """Update an existing transaction"""
    df = load_transactions()
    df.loc[df["id"] == transaction_id, "date"] = date
    df.loc[df["id"] == transaction_id, "amount"] = amount if transaction_type == "Income" else -amount
    df.loc[df["id"] == transaction_id, "category"] = category
    df.loc[df["id"] == transaction_id, "description"] = description
    df.loc[df["id"] == transaction_id, "type"] = transaction_type
    df.to_csv(TRANSACTIONS_FILE, index=False)

def delete_transaction(transaction_id):
    """Delete a transaction"""
    df = load_transactions()
    df = df[df["id"] != transaction_id]
    df.to_csv(TRANSACTIONS_FILE, index=False)
