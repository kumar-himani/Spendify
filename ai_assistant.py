"""Spendify's AI financial assistant.

The assistant uses the OpenAI API to answer budgeting and tax questions and to write budget
recommendations based on the user's own data.

Privacy: only an aggregated summary (monthly totals by category and budget progress) is sent
to OpenAI. Individual transaction descriptions, usernames, and emails never leave the app.

If no OPENAI_API_KEY is set, recommendations fall back to rule-based suggestions computed from
the same summary, so the app still works without a key.
"""

import os

import pandas as pd

from utils import EXPENSE_CATEGORIES

DEFAULT_MODEL = "gpt-4o-mini"
MAX_HISTORY_MESSAGES = 10

NEEDS_CATEGORIES = {"Housing", "Utilities", "Healthcare", "Transportation", "Food & Dining", "Education"}

SYSTEM_PROMPT = """You are Spendify's financial assistant, built for students and young adults \
who are learning to manage money.

- Answer questions about budgeting, saving, spending habits, and basic US taxes \
(W-2s, 1099s, filing status, standard deductions, and similar topics).
- When the question is about the user's own money, use the financial summary you are given and \
refer to their actual numbers. Never invent numbers that aren't in the summary.
- Keep answers short and practical: a few sentences or a short bulleted list.
- You give general education, not professional financial or tax advice. For complicated tax \
situations, suggest a tax professional or the IRS website.
- If a question has nothing to do with personal finance, say briefly that you can only help \
with money and tax questions."""

RECOMMENDATIONS_PROMPT = """Based on this user's financial summary, write personalized budget \
recommendations in Markdown:
1. Three to five specific recommendations that reference their actual numbers (categories \
they overspend in, their savings rate, budgets they're close to exceeding).
2. A suggested monthly budget for each expense category they spend in, as a short table.
Keep it under 250 words."""


class AssistantError(Exception):
    """Raised with a user-friendly message when the AI service can't answer."""


# ---------------------------------------------------------------------------
# Summarizing the user's data
# ---------------------------------------------------------------------------

def _prepare(transactions):
    df = transactions.copy()
    df["amount"] = df["amount"].astype(float)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    return df


def available_months(transactions):
    """Months that have transactions, newest first."""
    if transactions is None or transactions.empty:
        return []
    return sorted(_prepare(transactions)["month"].unique(), reverse=True)


def summarize_finances(transactions, budget_limits=None, month=None):
    """Build an aggregated summary of one month of the user's finances.

    month is a "YYYY-MM" string. If it's not given, the most recent month with data is used.
    """
    budget_limits = budget_limits or {}

    if transactions is None or transactions.empty:
        return None

    df = _prepare(transactions)
    month = month or df["month"].max()
    current = df[df["month"] == month]

    income = current.loc[current["amount"] > 0, "amount"].sum()
    expenses = -current.loc[current["amount"] < 0, "amount"].sum()
    net = income - expenses
    savings_rate = (net / income * 100) if income > 0 else None

    expense_rows = current[current["amount"] < 0]
    expenses_by_category = (-expense_rows.groupby("category")["amount"].sum()).round(2).to_dict()
    income_by_category = (
        current[current["amount"] > 0].groupby("category")["amount"].sum().round(2).to_dict()
    )

    budgets = []
    for category in EXPENSE_CATEGORIES:
        limit = float(budget_limits.get(category, 0) or 0)
        spent = float(expenses_by_category.get(category, 0))
        if limit <= 0 and spent == 0:
            continue
        budgets.append({
            "category": category,
            "limit": limit,
            "spent": spent,
            "remaining": limit - spent if limit > 0 else None,
            "percent_used": (spent / limit * 100) if limit > 0 else None,
        })

    monthly = df.groupby("month")["amount"]
    monthly_income = df[df["amount"] > 0].groupby("month")["amount"].sum()
    monthly_expenses = -df[df["amount"] < 0].groupby("month")["amount"].sum()

    return {
        "month": month,
        "transaction_count": int(len(current)),
        "income": round(float(income), 2),
        "expenses": round(float(expenses), 2),
        "net": round(float(net), 2),
        "savings_rate": round(float(savings_rate), 1) if savings_rate is not None else None,
        "expenses_by_category": expenses_by_category,
        "income_by_category": income_by_category,
        "budgets": budgets,
        "over_budget": [b["category"] for b in budgets if b["limit"] > 0 and b["spent"] > b["limit"]],
        "months_of_data": int(monthly.ngroups),
        "avg_monthly_income": round(float(monthly_income.mean()), 2) if not monthly_income.empty else 0.0,
        "avg_monthly_expenses": round(float(monthly_expenses.mean()), 2) if not monthly_expenses.empty else 0.0,
    }


def format_summary(summary):
    """Turn the summary into plain text for the model."""
    if not summary:
        return "The user hasn't added any transactions yet."

    lines = [
        f"Month: {summary['month']} ({summary['transaction_count']} transactions)",
        f"Income: ${summary['income']:,.2f}",
        f"Expenses: ${summary['expenses']:,.2f}",
        f"Net: ${summary['net']:,.2f}",
    ]
    if summary["savings_rate"] is not None:
        lines.append(f"Savings rate: {summary['savings_rate']}%")

    if summary["expenses_by_category"]:
        lines.append("Spending by category:")
        for category, amount in sorted(summary["expenses_by_category"].items(), key=lambda kv: -kv[1]):
            lines.append(f"  - {category}: ${amount:,.2f}")

    if summary["income_by_category"]:
        lines.append("Income by category:")
        for category, amount in summary["income_by_category"].items():
            lines.append(f"  - {category}: ${amount:,.2f}")

    budgets_with_limits = [b for b in summary["budgets"] if b["limit"] > 0]
    if budgets_with_limits:
        lines.append("Budgets (spent / limit):")
        for b in budgets_with_limits:
            lines.append(f"  - {b['category']}: ${b['spent']:,.2f} / ${b['limit']:,.2f} ({b['percent_used']:.0f}%)")
    else:
        lines.append("The user hasn't set any budget limits.")

    lines.append(
        f"Across {summary['months_of_data']} month(s) of data: average monthly income "
        f"${summary['avg_monthly_income']:,.2f}, average monthly expenses ${summary['avg_monthly_expenses']:,.2f}."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Talking to OpenAI
# ---------------------------------------------------------------------------

def get_client():
    """Return an OpenAI client, or None if no API key is configured."""
    if not os.getenv("OPENAI_API_KEY"):
        return None
    from openai import OpenAI
    return OpenAI()


def get_model():
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


def build_messages(summary_text, history, question):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"The user's financial summary:\n{summary_text}"},
    ]
    for message in (history or [])[-MAX_HISTORY_MESSAGES:]:
        if message.get("role") in ("user", "assistant") and message.get("content"):
            messages.append({"role": message["role"], "content": message["content"]})
    messages.append({"role": "user", "content": question})
    return messages


def _complete(client, messages, max_tokens):
    try:
        from openai import APIConnectionError, AuthenticationError, OpenAIError, RateLimitError
    except ImportError:  # pragma: no cover
        raise AssistantError("The OpenAI package isn't installed.")

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=messages,
            temperature=0.4,
            max_tokens=max_tokens,
        )
    except AuthenticationError:
        raise AssistantError("The AI assistant isn't set up correctly (invalid API key).")
    except RateLimitError:
        raise AssistantError("The AI assistant is busy right now. Please try again in a minute.")
    except APIConnectionError:
        raise AssistantError("Couldn't reach the AI service. Check your internet connection.")
    except OpenAIError:
        raise AssistantError("The AI assistant ran into a problem. Please try again.")

    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise AssistantError("The AI assistant returned an empty answer. Please try again.")
    return content.strip()


def ask_assistant(question, summary, history=None, client=None):
    """Answer a question using the user's financial summary as context."""
    question = (question or "").strip()
    if not question:
        raise AssistantError("Please type a question.")

    client = client or get_client()
    if client is None:
        raise AssistantError(
            "The AI assistant needs an OpenAI API key. Set OPENAI_API_KEY to turn it on."
        )

    messages = build_messages(format_summary(summary), history, question)
    return _complete(client, messages, max_tokens=500)


def generate_budget_recommendations(summary, client=None):
    """Return (markdown, source) where source is "ai" or "rules"."""
    if not summary:
        return "Add some transactions to get budget recommendations.", "rules"

    client = client or get_client()
    if client is None:
        return rule_based_recommendations(summary), "rules"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{RECOMMENDATIONS_PROMPT}\n\nFinancial summary:\n{format_summary(summary)}"},
    ]
    return _complete(client, messages, max_tokens=700), "ai"


# ---------------------------------------------------------------------------
# Fallback when there's no API key
# ---------------------------------------------------------------------------

def rule_based_recommendations(summary):
    """Personalized recommendations computed from the summary using the 50/30/20 rule."""
    income = summary["income"] or summary["avg_monthly_income"]
    expenses = summary["expenses_by_category"]
    tips = []

    if income <= 0:
        tips.append(
            "- You haven't logged any income for this month. Add your income so Spendify can "
            "compare it to your spending."
        )
    else:
        needs = sum(v for k, v in expenses.items() if k in NEEDS_CATEGORIES)
        wants = sum(v for k, v in expenses.items() if k not in NEEDS_CATEGORIES)
        tips.append(
            f"- **50/30/20 check:** with ${income:,.2f} of income, aim for about ${income * 0.5:,.2f} "
            f"on needs, ${income * 0.3:,.2f} on wants, and ${income * 0.2:,.2f} in savings. "
            f"This month you spent ${needs:,.2f} on needs and ${wants:,.2f} on wants."
        )
        if wants > income * 0.3:
            tips.append(f"- Your wants spending is ${wants - income * 0.3:,.2f} over the 30% guideline.")

        rate = summary["savings_rate"]
        if rate is not None:
            if rate < 0:
                tips.append(f"- You spent ${-summary['net']:,.2f} more than you earned this month.")
            elif rate < 20:
                tips.append(f"- You saved {rate}% of your income. Try to work up to 20%.")
            else:
                tips.append(f"- You saved {rate}% of your income, which meets the 20% goal.")

    for b in summary["budgets"]:
        if b["limit"] > 0 and b["spent"] > b["limit"]:
            tips.append(f"- **{b['category']}** is over budget by ${b['spent'] - b['limit']:,.2f}.")
        elif b["limit"] > 0 and b["percent_used"] >= 80:
            tips.append(f"- **{b['category']}** has used {b['percent_used']:.0f}% of its budget.")

    if expenses:
        top_category, top_amount = max(expenses.items(), key=lambda kv: kv[1])
        share = top_amount / summary["expenses"] * 100 if summary["expenses"] else 0
        tips.append(f"- Your biggest category is **{top_category}** at {share:.0f}% of spending.")

    if not any(b["limit"] > 0 for b in summary["budgets"]):
        tips.append("- Set budget limits on the Budgeting page to get alerts before you overspend.")

    return "\n".join(tips)
