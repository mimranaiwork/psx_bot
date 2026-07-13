import config
from models import fundamental_rules


def test_none_input_is_insufficient_data():
    assert fundamental_rules.get_fundamental_flag(None) == "insufficient_data"


def test_missing_eps_growth_yoy_is_insufficient_data():
    feats = {"eps_growth_yoy": None, "margin_trend": 0.0}
    assert fundamental_rules.get_fundamental_flag(feats) == "insufficient_data"


def test_positive_eps_growth_with_stable_margin_is_positive():
    feats = {"eps_growth_yoy": config.EPS_GROWTH_POSITIVE_THRESHOLD + 0.05, "margin_trend": 0.0}
    assert fundamental_rules.get_fundamental_flag(feats) == "positive"


def test_positive_eps_growth_with_deteriorating_margin_is_downgraded_to_neutral():
    feats = {"eps_growth_yoy": config.EPS_GROWTH_POSITIVE_THRESHOLD + 0.05, "margin_trend": -0.10}
    assert fundamental_rules.get_fundamental_flag(feats) == "neutral"


def test_negative_eps_growth_is_negative():
    feats = {"eps_growth_yoy": config.EPS_GROWTH_NEGATIVE_THRESHOLD - 0.05, "margin_trend": 0.0}
    assert fundamental_rules.get_fundamental_flag(feats) == "negative"


def test_mid_range_eps_growth_is_neutral():
    feats = {"eps_growth_yoy": 0.0, "margin_trend": 0.0}
    assert fundamental_rules.get_fundamental_flag(feats) == "neutral"


def test_rationale_for_insufficient_data():
    text = fundamental_rules.get_fundamental_rationale({}, "insufficient_data")
    assert "Insufficient" in text


def test_rationale_includes_eps_and_revenue_when_available():
    feats = {"eps_growth_yoy": 0.2, "revenue_growth_yoy": 0.1}
    text = fundamental_rules.get_fundamental_rationale(feats, "positive")
    assert "EPS" in text
    assert "revenue" in text
