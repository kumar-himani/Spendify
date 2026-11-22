import os
import pandas as pd
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from security import hash_password, verify_password, needs_rehash

# Get database connection details from environment variables
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Create a database connection"""
    try:
        return psycopg2.connect(DATABASE_URL)
    except psycopg2.Error as e:
        raise Exception(f"Failed to connect to database: {str(e)}")

def init_database():
    """Initialize database tables"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # First check if the tables exist
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            );
        """)
        users_exists = cur.fetchone()[0]

        if not users_exists:
            # Create users table
            cur.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(256) NOT NULL,
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

        # Check for transactions table
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'transactions'
            );
        """)
        transactions_exists = cur.fetchone()[0]

        if not transactions_exists:
            # Create transactions table with user_id
            cur.execute("""
            CREATE TABLE transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                date DATE NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                category VARCHAR(50) NOT NULL,
                description TEXT,
                type VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

        # Check for budget_limits table
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'budget_limits'
            );
        """)
        budget_limits_exists = cur.fetchone()[0]

        if not budget_limits_exists:
            # Create budget_limits table
            cur.execute("""
            CREATE TABLE budget_limits (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                category VARCHAR(50) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category)
            )
            """)

        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def create_user(username, password, email=None):
    """Create a new user with a salted password hash"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s) RETURNING id",
            (username, hash_password(password), email)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return user_id
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise ValueError("That username is already taken.")
    except psycopg2.Error as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def verify_user(username, password):
    """Verify user credentials. Upgrades older unsalted hashes after a successful login."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            (username,)
        )
        user = cur.fetchone()
        if not user or not verify_password(password, user['password_hash']):
            return None

        if needs_rehash(user['password_hash']):
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (hash_password(password), user['id'])
            )
            conn.commit()

        return {'id': user['id'], 'username': user['username']}
    finally:
        cur.close()
        conn.close()

def change_password(user_id, current_password, new_password):
    """Change a user's password. Returns False if the current password is wrong."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user or not verify_password(current_password, user['password_hash']):
            return False

        cur.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(new_password), user_id)
        )
        conn.commit()
        return True
    except psycopg2.Error as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def save_transaction(user_id, date, amount, category, description, transaction_type):
    """Save a transaction for a specific user"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            INSERT INTO transactions 
            (user_id, date, amount, category, description, type)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, date, amount, category, description, transaction_type)
        )
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def load_transactions(user_id):
    """Load transactions for a specific user"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute(
            "SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC",
            (user_id,)
        )
        transactions = cur.fetchall()
        return pd.DataFrame(transactions)
    finally:
        cur.close()
        conn.close()

def save_budget_limits(user_id, budget_limits):
    """Save budget limits for a specific user"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # First delete existing limits
        cur.execute("DELETE FROM budget_limits WHERE user_id = %s", (user_id,))
        
        # Insert new limits
        for category, amount in budget_limits.items():
            cur.execute(
                """
                INSERT INTO budget_limits (user_id, category, amount)
                VALUES (%s, %s, %s)
                """,
                (user_id, category, amount)
            )
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def load_budget_limits(user_id):
    """Load budget limits for a specific user"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute(
            "SELECT category, amount FROM budget_limits WHERE user_id = %s",
            (user_id,)
        )
        limits = cur.fetchall()
        return {limit['category']: float(limit['amount']) for limit in limits}
    finally:
        cur.close()
        conn.close()