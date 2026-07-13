import config
from models import llm_synthesis


def test_template_rationale_used_when_no_api_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    text = llm_synthesis.generate_rationale(
        "SYM", 1, {1: 0.8, 0: 0.1, -1: 0.1}, "positive", "EPS +20% YoY",
        {"recent_announcement_count": 0},
    )
    assert "Technical model points to a upward move" in text
    assert "Fundamental signal: positive" in text


def test_template_rationale_flags_negative_event_hint():
    text = llm_synthesis._generate_template_rationale(
        "SYM", 1, {1: 0.8, 0: 0.1, -1: 0.1}, "positive", "EPS +20% YoY",
        {"recent_announcement_count": 1, "categories_seen": ["other"], "has_negative_hint": True},
    )
    assert "negative hint" in text


def test_template_rationale_flags_technical_fundamental_disagreement():
    text = llm_synthesis._generate_template_rationale(
        "SYM", 1, {1: 0.6, 0: 0.2, -1: 0.2}, "negative", "EPS -20% YoY",
        {"recent_announcement_count": 0},
    )
    assert "do not fully agree" in text


def test_template_rationale_no_announcements_message():
    text = llm_synthesis._generate_template_rationale(
        "SYM", 0, {1: 0.3, 0: 0.4, -1: 0.3}, "insufficient_data",
        "Insufficient financial report history to assess fundamentals.",
        {"recent_announcement_count": 0},
    )
    assert "No significant recent announcements detected." in text
