"""
Fundamental rule engine — deliberately rule-based rather than ML, because
fundamental data is sparse (quarterly) and rules are auditable. Revisit
with an ML approach only once you have years of labeled outcomes.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def get_fundamental_flag(fundamental_features):
    """
    fundamental_features: dict from features.fundamental_features.get_fundamental_features()
    Returns one of: "positive", "negative", "neutral", "insufficient_data"
    """
    if fundamental_features is None:
        return "insufficient_data"

    eps_growth_yoy = fundamental_features.get("eps_growth_yoy")
    margin_trend = fundamental_features.get("margin_trend")

    if eps_growth_yoy is None:
        return "insufficient_data"

    if eps_growth_yoy > config.EPS_GROWTH_POSITIVE_THRESHOLD:
        if margin_trend is not None and margin_trend < -0.05:
            # EPS growth but margins deteriorating - flag as mixed, not
            # purely positive, since this can indicate one-off gains
            return "neutral"
        return "positive"

    if eps_growth_yoy < config.EPS_GROWTH_NEGATIVE_THRESHOLD:
        return "negative"

    return "neutral"


def get_fundamental_rationale(fundamental_features, flag):
    """Generates a short human-readable explanation for the flag."""
    if flag == "insufficient_data":
        return "Insufficient financial report history to assess fundamentals."

    eps_growth_yoy = fundamental_features.get("eps_growth_yoy")
    revenue_growth_yoy = fundamental_features.get("revenue_growth_yoy")

    parts = []
    if eps_growth_yoy is not None:
        parts.append(f"EPS {'+' if eps_growth_yoy >= 0 else ''}{eps_growth_yoy:.1%} YoY")
    if revenue_growth_yoy is not None:
        parts.append(f"revenue {'+' if revenue_growth_yoy >= 0 else ''}{revenue_growth_yoy:.1%} YoY")

    return ", ".join(parts) if parts else "Limited fundamental data available."
