import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException

from db import database
from api.schemas import LoadPricesRequest, LoadTickerRequest, ActionResult

router = APIRouter(tags=["pipeline"])


def _sanitize(value):
    """Recursively converts numpy/pandas scalar types (e.g. numpy.float64,
    numpy.bool_) to native Python types so FastAPI's JSON encoder doesn't
    choke on them -- backtest_engine metrics are full of these."""
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if hasattr(value, "item"):
        return value.item()
    return value


@router.post("/symbols/{symbol}/load-prices", response_model=ActionResult)
def load_prices(symbol: str, body: LoadPricesRequest):
    from ingestion import yfinance_loader
    database.init_db()
    n = yfinance_loader.load_yfinance_to_db(symbol, body.yf_ticker, body.period)
    return ActionResult(symbol=symbol, detail=f"Loaded {n} price rows.", data={"rows": n})


@router.post("/symbols/{symbol}/load-fundamentals", response_model=ActionResult)
def load_fundamentals(symbol: str, body: LoadTickerRequest):
    from ingestion import yfinance_fundamentals_loader
    database.init_db()
    n = yfinance_fundamentals_loader.load_yfinance_fundamentals(symbol, body.yf_ticker)
    return ActionResult(symbol=symbol, detail=f"Loaded {n} quarterly fundamentals rows.", data={"rows": n})


@router.post("/symbols/{symbol}/load-news", response_model=ActionResult)
def load_news(symbol: str, body: LoadTickerRequest):
    from ingestion import yfinance_news_loader
    database.init_db()
    n = yfinance_news_loader.load_yfinance_news(symbol, body.yf_ticker)
    return ActionResult(symbol=symbol, detail=f"Loaded {n} announcement rows.", data={"rows": n})


@router.post("/symbols/{symbol}/train", response_model=ActionResult)
def train(symbol: str):
    from models import technical_model
    price_df = database.get_price_history(symbol)
    if price_df.empty:
        raise HTTPException(status_code=400, detail=f"No data for {symbol}. Load prices first.")
    try:
        _, report = technical_model.train_walk_forward(price_df, symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ActionResult(
        symbol=symbol,
        detail=f"Out-of-sample accuracy: {report['accuracy']:.3f}",
        data=_sanitize({
            "accuracy": report["accuracy"],
            "train_rows": report["train_rows"],
            "test_rows": report["test_rows"],
        }),
    )


@router.post("/symbols/{symbol}/backtest", response_model=ActionResult)
def backtest(symbol: str):
    from backtest import backtest_engine
    price_df = database.get_price_history(symbol)
    if price_df.empty:
        raise HTTPException(status_code=400, detail=f"No data for {symbol}. Load prices first.")
    try:
        metrics, _, _ = backtest_engine.run_backtest(price_df, symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    database.insert_backtest_run({
        "symbol": symbol,
        "start_date": str(price_df["trade_date"].iloc[0]),
        "end_date": str(price_df["trade_date"].iloc[-1]),
        "total_trades": metrics.get("total_trades"),
        "win_rate": metrics.get("win_rate"),
        "sharpe_ratio": metrics.get("sharpe_ratio"),
        "max_drawdown": metrics.get("max_drawdown"),
        "strategy_return": metrics.get("strategy_return"),
        "baseline_return": metrics.get("baseline_return_buy_hold"),
        "notes": "via web portal",
    })
    return ActionResult(symbol=symbol, detail="Backtest complete.", data=_sanitize(metrics))


@router.post("/symbols/{symbol}/signal", response_model=ActionResult)
def generate_signal(symbol: str):
    from signals import signal_engine
    try:
        record = signal_engine.generate_signal(symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ActionResult(
        symbol=symbol,
        detail=f"Signal: {record['signal']} ({record['confidence']})",
        data=_sanitize(record),
    )


@router.post("/symbols/{symbol}/update-outcomes", response_model=ActionResult)
def update_outcomes(symbol: str):
    from signals import signal_engine
    updated = signal_engine.update_signal_outcomes(symbol)
    return ActionResult(symbol=symbol, detail=f"Updated {updated} past signals.", data={"updated": updated})
