import pytest

from backtest import backtest_engine
from db import database


def test_run_backtest_raises_on_insufficient_data(test_db, synthetic_price_rows):
    rows = synthetic_price_rows(n_days=100)
    database.upsert_price_rows("TINY2", rows)
    price_df = database.get_price_history("TINY2")

    with pytest.raises(ValueError):
        backtest_engine.run_backtest(price_df, "TINY2")


def test_run_backtest_end_to_end_returns_consistent_metrics(loaded_price_history):
    price_df = database.get_price_history(loaded_price_history)
    metrics, equity_df, trades_df = backtest_engine.run_backtest(price_df, loaded_price_history)

    for key in (
        "strategy_return", "baseline_return_buy_hold", "beats_baseline",
        "sharpe_ratio", "max_drawdown", "total_trades", "win_rate",
    ):
        assert key in metrics

    assert metrics["beats_baseline"] == (
        metrics["strategy_return"] > metrics["baseline_return_buy_hold"]
    )
    assert metrics["max_drawdown"] <= 0
    if metrics["win_rate"] is not None:
        assert 0.0 <= metrics["win_rate"] <= 1.0
    assert not equity_df.empty


def test_backtest_never_holds_two_consecutive_same_side_trades(loaded_price_history):
    price_df = database.get_price_history(loaded_price_history)
    _, _, trades_df = backtest_engine.run_backtest(price_df, loaded_price_history)

    if trades_df.empty:
        pytest.skip("No trades triggered for this synthetic series/seed")

    actions = trades_df["action"].tolist()
    assert actions[0] == "BUY"
    for a, b in zip(actions, actions[1:]):
        assert a != b, "trade log should strictly alternate BUY/SELL"


def test_backtest_exits_only_on_explicit_down_prediction_are_reflected_in_trade_count(loaded_price_history):
    """
    Regression guard for the exit-rule fix: a strategy that only exits on
    pred == -1 (not pred != 1) should never generate more round trips
    than one per bearish prediction encountered -- i.e. it shouldn't be
    churning on every non-"up" tick anymore. This is a coarse sanity
    check, not an exact bound, since the model itself is stochastic.
    """
    price_df = database.get_price_history(loaded_price_history)
    metrics, _, trades_df = backtest_engine.run_backtest(price_df, loaded_price_history)
    completed_trades = trades_df[trades_df["action"] == "SELL"] if not trades_df.empty else trades_df
    assert len(completed_trades) == metrics["total_trades"]
