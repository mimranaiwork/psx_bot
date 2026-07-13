"""
Signal engine — combines technical model, fundamental rules, and event
features into a single Buy/Hold/Sell signal with a confidence band and
plain-language rationale. This is the top-level entrypoint most callers
(CLI, dashboard) should use.
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from db import database
from models import technical_model, fundamental_rules, llm_synthesis
from features import fundamental_features, event_features


def generate_signal(symbol):
    """
    Returns a dict with the full signal output, and logs it to signals_log
    for later accuracy tracking. Raises if no trained model exists yet.
    """
    price_df = database.get_price_history(symbol)
    if price_df.empty:
        raise ValueError(f"No price history found for {symbol}. Load data first.")

    tech_pred, tech_proba = technical_model.predict_latest(symbol, price_df)

    fund_features = fundamental_features.get_fundamental_features(symbol)
    fund_flag = fundamental_rules.get_fundamental_flag(fund_features)
    fund_rationale = fundamental_rules.get_fundamental_rationale(fund_features, fund_flag)

    events = event_features.get_event_features(symbol)

    rationale = llm_synthesis.generate_rationale(
        symbol, tech_pred, tech_proba, fund_flag, fund_rationale, events
    )

    signal, confidence = _combine_to_signal(tech_pred, tech_proba, fund_flag, events)

    record = {
        "symbol": symbol,
        "signal_date": datetime.now().strftime("%Y-%m-%d"),
        "signal": signal,
        "confidence": confidence,
        "model_probability": float(max(tech_proba.values())) if tech_proba else None,
        "fundamental_flag": fund_flag,
        "rationale": rationale,
        "horizon_days": config.PREDICTION_HORIZON_DAYS,
    }
    signal_id = database.insert_signal(record)
    record["id"] = signal_id

    return record


def _combine_to_signal(tech_pred, tech_proba, fund_flag, events=None):
    """
    Combines technical prediction + fundamental flag into a final signal,
    then applies recent event/announcement data as a caution veto.
    Equal-weighted starting point — re-tune only after backtesting shows
    which component actually adds predictive value for a given symbol.

    Events are treated as a veto, not a third equal vote: announcement
    data is sparse/noisy (see event_features.py), so a negative hint can
    downgrade a BUY to HOLD, but the absence of events never manufactures
    a signal, and events never override a SELL (a negative hint agrees
    with, rather than conflicts with, a bearish call).
    """
    top_proba = max(tech_proba.values()) if tech_proba else 0.0

    if top_proba >= config.CONFIDENCE_HIGH:
        confidence = "High"
    elif top_proba >= config.CONFIDENCE_MODERATE:
        confidence = "Moderate"
    else:
        confidence = "Low"

    if tech_pred == 1 and fund_flag in ("positive", "neutral"):
        signal = "BUY"
    elif tech_pred == -1 and fund_flag in ("negative", "neutral"):
        signal = "SELL"
    elif tech_pred == 1 and fund_flag == "negative":
        signal = "HOLD"   # conflicting signals -> don't force a call
        confidence = "Low"
    elif tech_pred == -1 and fund_flag == "positive":
        signal = "HOLD"
        confidence = "Low"
    else:
        signal = "HOLD"

    if signal == "BUY" and events and events.get("has_negative_hint"):
        signal = "HOLD"
        confidence = "Low"

    return signal, confidence


def update_signal_outcomes(symbol):
    """
    Backfills actual_forward_return and outcome_correct for past signals
    whose prediction horizon has now elapsed. Run this periodically
    (e.g. daily) to keep the accuracy log current.
    """
    import pandas as pd
    from datetime import timedelta

    price_df = database.get_price_history(symbol)
    if price_df.empty:
        return 0

    price_df["trade_date"] = pd.to_datetime(price_df["trade_date"])
    signals_df = database.get_signals_log(symbol)
    signals_df = signals_df[signals_df["actual_forward_return"].isna()]

    conn = database.get_connection()
    updated = 0
    try:
        cur = conn.cursor()
        for _, sig in signals_df.iterrows():
            sig_date = pd.to_datetime(sig["signal_date"])
            target_date = sig_date + timedelta(days=sig["horizon_days"])

            entry_rows = price_df[price_df["trade_date"] <= sig_date]
            exit_rows = price_df[price_df["trade_date"] >= target_date]

            if entry_rows.empty or exit_rows.empty:
                continue  # horizon hasn't elapsed yet or data gap

            entry_price = entry_rows.iloc[-1]["close"]
            exit_price = exit_rows.iloc[0]["close"]
            forward_return = (exit_price - entry_price) / entry_price

            predicted_up = sig["signal"] == "BUY"
            predicted_down = sig["signal"] == "SELL"
            correct = None
            if predicted_up:
                correct = 1 if forward_return > 0 else 0
            elif predicted_down:
                correct = 1 if forward_return < 0 else 0
            # HOLD signals aren't scored as correct/incorrect directionally

            cur.execute(
                "UPDATE signals_log SET actual_forward_return = ?, outcome_correct = ? WHERE id = ?",
                (float(forward_return), correct, int(sig["id"])),
            )
            updated += 1
        conn.commit()
    finally:
        conn.close()

    return updated
