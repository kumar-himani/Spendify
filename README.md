# Spendify 💰

A personal finance web app for students and young adults. Track income and expenses, set monthly budgets, see where your money goes, and ask an AI assistant budgeting and tax questions grounded in your own spending.

Built by [Himani Kumar](https://github.com/kumar-himani) and [Nikita Nayunipati](https://github.com/nikitavn) for FBLA Coding & Programming (National Qualifier, 2025). Features were prioritized around pain points from a 73-person user survey.

<img width="1203" height="974" alt="Screenshot 2026-11-20 at 5 04 55 AM" src="https://github.com/user-attachments/assets/3ac00f17-f829-4cde-9a10-03bfc73b78cc" />

<img width="1203" height="974" alt="Screenshot 2026-11-20 at 5 09 12 AM" src="https://github.com/user-attachments/assets/8b755ce8-9c7b-4ea3-b970-0b63f65d2fb4" />

<img width="1207" height="972" alt="Screenshot 2026-11-20 at 5 03 57 AM" src="https://github.com/user-attachments/assets/7709ab85-d81b-4841-b891-b70293ef479d" />



## Features
- **Accounts:** sign up and log in, with salted PBKDF2 password hashing
- **Transactions:** add income and expenses with validation, then filter by type, category, and date
- **Reports:** monthly net income charts, category breakdowns, savings rate, and trend analysis
- **Budgeting:** monthly limits per category with progress bars and over-budget warnings
- **AI assistant:** personalized budget recommendations and a chat for budgeting and tax questions (see below)
- **Export:** download your transactions as a CSV

## How the AI assistant works
`ai_assistant.py` builds a summary of the selected month from the user's data: income, expenses, savings rate, spending by category, and budget progress. That summary is sent to the OpenAI API along with the user's question, so answers refer to their real numbers.

- **Privacy:** only aggregated totals are sent. Transaction descriptions, usernames, and emails never leave the app.
- **No API key?** Recommendations fall back to rule-based suggestions (50/30/20 rule, over-budget categories, savings rate) computed from the same summary, and the chat is turned off.
- **Testing:** the tests use a fake OpenAI client, so they run without a key or network access.

## Input validation
`validation.py` checks both the format of the input and whether it makes sense:
- **Syntactic:** amounts are positive numbers with at most two decimal places, descriptions are 1-200 characters, emails and usernames have a valid format, and passwords are at least 8 characters with a letter and a number
- **Semantic:** the category matches the transaction type, dates aren't in the future, and budget limits are checked against your income for the month

## Tech
Python, Streamlit, PostgreSQL (psycopg2), pandas, Plotly, OpenAI API, pytest, GitHub Actions

## Running it
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Set environment variables (see `.env.example`):
   ```
   export DATABASE_URL=postgresql://user:password@localhost:5432/spendify
   export OPENAI_API_KEY=sk-...        # optional
   ```
3. Start the app. Tables are created automatically on first run.
   ```
   streamlit run main.py
   ```

Run the tests with `pip install -r requirements-dev.txt` and then `pytest`.

## History
- **2025:** Built for FBLA Coding & Programming. It started as an earlier TypeScript prototype (FinancialWizard) and was rebuilt in Python and Streamlit as Spendify. Some early scaffolding was generated with Replit Agent.
- **2026 updates:**
  - Connected the AI assistant to the OpenAI API. It previously returned prewritten answers.
  - Added syntactic and semantic validation.
  - Upgraded password storage from unsalted SHA-256 to salted PBKDF2, with automatic upgrades for older accounts.
  - Fixed the category list not updating when switching between income and expense.
  - Replaced the server-side export with a CSV download.
  - Added tests and CI.
