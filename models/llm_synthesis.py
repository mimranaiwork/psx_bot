"""
LLM synthesis layer: takes the technical model output, fundamental flag,
and recent event/sentiment features, and produces a short plain-language
rationale explaining the combined signal.

Design principle: the LLM explains given numbers, it does NOT generate
new numeric predictions. If ANTHROPIC_API_KEY is not set, falls back to a
template-based rationale so the pipeline still works end-to-end without
an API key.
"""
import sys
import os
import json
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

SYSTEM_PROMPT = """You are a financial signal explainer. You are given
structured numeric outputs from a technical model, a fundamental rule
engine, and recent company announcements. Your job is to write a short,
plain-language rationale (2-3 bullet points) explaining what these
signals suggest and explicitly noting any conflicts between them.

Rules:
- Do NOT invent new numeric predictions or figures beyond what is given.
- Do NOT state or imply certainty. Use hedged language ("suggests",
  "points to", "may indicate").
- If technical, fundamental, and recent-event signals disagree with
  each other, say so explicitly. In particular, a negative hint in a
  recent announcement (e.g. loss, resignation, downgrade) alongside a
  bullish technical read is a real conflict worth calling out, since it
  is treated as a caution flag by the signal engine.
- Keep it to 2-3 bullet points, no more.
- Do not give direct investment advice ("you should buy") — describe
  what the data shows, not what the user should do.
"""


def generate_rationale(symbol, technical_prediction, technical_proba,
                        fundamental_flag, fundamental_rationale, event_features):
    """
    Returns a short rationale string. Uses Claude API if configured,
    otherwise falls back to a deterministic template.
    """
    if config.ANTHROPIC_API_KEY:
        try:
            return _generate_via_api(
                symbol, technical_prediction, technical_proba,
                fundamental_flag, fundamental_rationale, event_features
            )
        except Exception as e:
            print(f"LLM synthesis failed ({e}), falling back to template rationale.")

    return _generate_template_rationale(
        symbol, technical_prediction, technical_proba,
        fundamental_flag, fundamental_rationale, event_features
    )


def _generate_via_api(symbol, technical_prediction, technical_proba,
                       fundamental_flag, fundamental_rationale, event_features):
    user_content = json.dumps({
        "symbol": symbol,
        "technical_prediction": technical_prediction,   # -1/0/1
        "technical_probabilities": technical_proba,
        "fundamental_flag": fundamental_flag,
        "fundamental_rationale": fundamental_rationale,
        "recent_events": event_features,
    }, indent=2, default=str)

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.LLM_MODEL,
            "max_tokens": 300,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_content}],
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    return "\n".join(text_blocks).strip()


def _generate_template_rationale(symbol, technical_prediction, technical_proba,
                                  fundamental_flag, fundamental_rationale, event_features):
    direction_map = {1: "upward", -1: "downward", 0: "flat/unclear"}
    direction = direction_map.get(technical_prediction, "unclear")
    top_proba = max(technical_proba.values()) if technical_proba else 0.0

    bullets = [
        f"- Technical model points to a {direction} move (model confidence ~{top_proba:.0%}).",
        f"- Fundamental signal: {fundamental_flag} ({fundamental_rationale}).",
    ]

    if event_features and event_features.get("recent_announcement_count", 0) > 0:
        cats = ", ".join(event_features.get("categories_seen", [])) or "unspecified"
        bullets.append(f"- {event_features['recent_announcement_count']} recent announcement(s) "
                        f"in the last 30 days ({cats}).")
    else:
        bullets.append("- No significant recent announcements detected.")

    # Flag disagreement explicitly
    tech_direction_positive = technical_prediction == 1
    fund_positive = fundamental_flag == "positive"
    if tech_direction_positive != fund_positive and fundamental_flag != "insufficient_data":
        bullets.append("- Note: technical and fundamental signals do not fully agree — treat with extra caution.")

    if event_features and event_features.get("has_negative_hint") and technical_prediction == 1:
        bullets.append("- Note: a recent announcement carries a negative hint (e.g. loss, resignation, "
                        "downgrade) that conflicts with the bullish technical read — this downgraded "
                        "the signal to HOLD.")

    return "\n".join(bullets)
