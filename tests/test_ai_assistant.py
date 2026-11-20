from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

import ai_assistant
from ai_assistant import (AssistantError, ask_assistant, available_months, build_messages,
                          format_summary, generate_budget_recommendations,
                          rule_based_recommendations, summarize_finances)


@pytest.fixture
def transactions():
    # Amounts come back from PostgreSQL as Decimal, so the tests use Decimal too.
    return pd.DataFrame([
        {"date": "2025-03-01", "amount": Decimal("1000.00"), "category": "Salary", "description": "Pay day", "type": "Income"},
        {"date": "2025-03-03", "amount": Decimal("-400.00"), "category": "Housing", "description": "Rent", "type": "Expense"},
        {"date": "2025-03-10", "amount": Decimal("-150.00"), "category": "Food & Dining", "description": "Chipotle", "type": "Expense"},
        {"date": "2025-03-12", "amount": Decimal("-250.00"), "category": "Shopping", "description": "New shoes", "type": "Expense"},
        {"date": "2025-02-01", "amount": Decimal("800.00"), "category": "Salary", "description": "Pay day", "type": "Income"},
        {"date": "2025-02-05", "amount": Decimal("-300.00"), "category": "Housing", "description": "Rent", "type": "Expense"},
    ])


def test_summary_math(transactions):
    s = summarize_finances(transactions, {"Shopping": 200, "Housing": 500})
    assert s["month"] == "2025-03"
    assert s["income"] == 1000
    assert s["expenses"] == 800
    assert s["net"] == 200
    assert s["savings_rate"] == 20.0
    assert s["expenses_by_category"] == {"Food & Dining": 150, "Housing": 400, "Shopping": 250}
    assert s["over_budget"] == ["Shopping"]
    assert s["months_of_data"] == 2
    assert s["avg_monthly_income"] == 900


def test_summary_for_a_chosen_month(transactions):
    s = summarize_finances(transactions, month="2025-02")
    assert s["income"] == 800 and s["expenses"] == 300
    assert available_months(transactions) == ["2025-03", "2025-02"]


def test_empty_data():
    assert summarize_finances(pd.DataFrame()) is None
    assert "hasn't added" in format_summary(None)


def test_summary_text_has_numbers_but_no_descriptions(transactions):
    text = format_summary(summarize_finances(transactions, {"Shopping": 200}))
    assert "$1,000.00" in text and "Shopping: $250.00 / $200.00" in text
    # Privacy: individual transaction descriptions are never sent to the model.
    assert "Chipotle" not in text and "New shoes" not in text


def test_history_is_trimmed():
    history = [{"role": "user", "content": str(i)} for i in range(30)]
    messages = build_messages("summary", history, "question")
    assert messages[0]["role"] == "system"
    assert messages[-1] == {"role": "user", "content": "question"}
    assert len(messages) == 2 + ai_assistant.MAX_HISTORY_MESSAGES + 1


class FakeClient:
    """Stands in for the OpenAI client so tests don't call the real API."""

    def __init__(self, reply="Here's my advice."):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.reply = reply

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_ask_assistant_sends_summary_and_question(transactions):
    client = FakeClient("Cut back on shopping.")
    summary = summarize_finances(transactions)
    answer = ask_assistant("Where can I save?", summary, client=client)
    assert answer == "Cut back on shopping."
    sent = client.calls[0]["messages"]
    assert "Income: $1,000.00" in sent[1]["content"]
    assert sent[-1]["content"] == "Where can I save?"


def test_ask_assistant_needs_key_and_question(monkeypatch, transactions):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(AssistantError):
        ask_assistant("Hi", summarize_finances(transactions))
    with pytest.raises(AssistantError):
        ask_assistant("   ", summarize_finances(transactions), client=FakeClient())


def test_recommendations_use_ai_when_available(transactions):
    text, source = generate_budget_recommendations(summarize_finances(transactions), client=FakeClient("AI tips"))
    assert (text, source) == ("AI tips", "ai")


def test_recommendations_fall_back_to_rules(monkeypatch, transactions):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    text, source = generate_budget_recommendations(summarize_finances(transactions, {"Shopping": 200}))
    assert source == "rules"
    assert "$500.00 on needs" in text  # 50% of $1,000 income
    assert "Shopping** is over budget by $50.00" in text


def test_rule_based_handles_no_income():
    df = pd.DataFrame([{"date": "2025-03-01", "amount": -20.0, "category": "Shopping", "description": "x", "type": "Expense"}])
    text = rule_based_recommendations(summarize_finances(df))
    assert "haven't logged any income" in text
