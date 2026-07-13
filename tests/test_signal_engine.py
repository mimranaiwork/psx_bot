from datetime import timedelta

import pandas as pd
import pytest

import config
from db import database
from models import technical_model
from signals import signal_engine

HIGH = config.CONFIDENCE_HIGH
MOD = config.CONFIDENCE_MODERATE


def _proba(p_up):
    """tech_proba dict where the 'up' class carries probability p_up."""
    rest = (1 - p_up) / 2
    return {1: p_up, 0: rest, -1: rest}


# --- _combine_to_signal decision table -------------------------------

@pytest.mark.parametrize("tech_pred,fund_flag,expected_signal", [
    (1, "positive", "BUY"),
    (1, "neutral", "BUY"),
    (-1, "negative", "SELL"),
    (-1, "neutral", "SELL"),
    (1, "negative", "HOLD"),      # conflict
    (-1, "positive", "HOLD"),     # conflict
    (0, "positive", "HOLD"),
    (0, "negative", "HOLD"),
    (1, "insufficient_data", "HOLD"),
    (-1, "insufficient_data", "HOLD"),
])
def test_combine_to_signal_decision_table(tech_pred, fund_flag, expected_signal):
    signal, _ = signal_engine._combine_to_signal(tech_pred, _proba(HIGH + 0.05), fund_flag)
    assert signal == expected_signal


def test_conflicting_signals_force_low_confidence():
    _, confidence = signal_engine._combine_to_signal(1, _proba(HIGH + 0.05), "negative")
    assert confidence == "Low"


@pytest.mark.parametrize("p_up,expected_confidence", [
    (HIGH + 0.05, "High"),
    (MOD + 0.02, "Moderate"),
    (MOD - 0.05, "Low"),
])
def test_confidence_bands(p_up, expected_confidence):
    _, confidence = signal_engine._combine_to_signal(1, _proba(p_up), "positive")
    assert confidence == expected_confidence


# --- events veto (new logic) ------------------------------------------

def test_events_negative_hint_downgrades_buy_to_hold_low():
    signal, confidence = signal_engine._combine_to_signal(
        1, _proba(HIGH + 0.05), "positive", events={"has_negative_hint": True}
    )
    assert signal == "HOLD"
    assert confidence == "Low"


def test_events_without_negative_hint_do_not_change_buy():
    signal, _ = signal_engine._combine_to_signal(
        1, _proba(HIGH + 0.05), "positive", events={"has_negative_hint": False}
    )
    assert signal == "BUY"


def test_events_none_is_safe_and_does_not_change_buy():
    signal, _ = signal_engine._combine_to_signal(1, _proba(HIGH + 0.05), "positive", events=None)
    assert signal == "BUY"


def test_events_empty_dict_is_safe():
    signal, _ = signal_engine._combine_to_signal(1, _proba(HIGH + 0.05), "positive", events={})
    assert signal == "BUY"


def test_events_negative_hint_does_not_override_sell():
    signal, confidence = signal_engine._combine_to_signal(
        -1, _proba(HIGH + 0.05), "negative", events={"has_negative_hint": True}
    )
    assert signal == "SELL"


def test_events_negative_hint_does_not_manufacture_a_signal_from_hold():
    signal, _ = signal_engine._combine_to_signal(
        0, _proba(HIGH + 0.05), "neutral", events={"has_negative_hint": True}
    )
    assert signal == "HOLD"


# --- generate_signal / update_signal_outcomes integration --------------

def test_generate_signal_end_to_end(loaded_price_history, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODELS_DIR", str(tmp_path))
    price_df = database.get_price_history(loaded_price_history)
    technical_model.train_walk_forward(price_df, loaded_price_history)

    record = signal_engine.generate_signal(loaded_price_history)

    assert record["signal"] in ("BUY", "HOLD", "SELL")
    assert record["confidence"] in ("High", "Moderate", "Low")
    assert record["symbol"] == loaded_price_history
    assert record["id"] is not None

    logged = database.get_signals_log(loaded_price_history)
    assert len(logged) == 1
    assert logged.iloc[0]["signal"] == record["signal"]


def test_generate_signal_raises_without_price_data(test_db):
    with pytest.raises(ValueError):
        signal_engine.generate_signal("NOPRICE")


def test_update_signal_outcomes_backfills_correct_return(loaded_price_history):
    price_df = database.get_price_history(loaded_price_history)
    price_df["trade_date"] = pd.to_datetime(price_df["trade_date"])

    horizon = config.PREDICTION_HORIZON_DAYS
    signal_row_idx = len(price_df) - horizon - 10
    signal_row = price_df.iloc[signal_row_idx]
    signal_date = signal_row["trade_date"].strftime("%Y-%m-%d")
    entry_price = signal_row["close"]

    target_date = signal_row["trade_date"] + timedelta(days=horizon)
    exit_row = price_df[price_df["trade_date"] >= target_date].iloc[0]
    expected_return = (exit_row["close"] - entry_price) / entry_price

    record = {
        "symbol": loaded_price_history, "signal_date": signal_date, "signal": "BUY",
        "confidence": "High", "model_probability": 0.8, "fundamental_flag": "neutral",
        "rationale": "test", "horizon_days": horizon,
    }
    database.insert_signal(record)

    updated = signal_engine.update_signal_outcomes(loaded_price_history)
    assert updated == 1

    logged = database.get_signals_log(loaded_price_history)
    row = logged.iloc[0]
    assert row["actual_forward_return"] == pytest.approx(expected_return, rel=1e-6)
    assert row["outcome_correct"] == (1 if expected_return > 0 else 0)


def test_update_signal_outcomes_skips_signals_whose_horizon_has_not_elapsed(loaded_price_history):
    price_df = database.get_price_history(loaded_price_history)
    last_date = pd.to_datetime(price_df["trade_date"]).iloc[-1]

    record = {
        "symbol": loaded_price_history, "signal_date": last_date.strftime("%Y-%m-%d"),
        "signal": "BUY", "confidence": "High", "model_probability": 0.8,
        "fundamental_flag": "neutral", "rationale": "test",
        "horizon_days": config.PREDICTION_HORIZON_DAYS,
    }
    database.insert_signal(record)

    updated = signal_engine.update_signal_outcomes(loaded_price_history)
    assert updated == 0
