"""Pydantic request/response models for the API layer."""
from typing import Any, Optional

from pydantic import BaseModel


class SymbolSummary(BaseModel):
    symbol: str
    row_count: int
    latest_date: Optional[str] = None


class SignalRecord(BaseModel):
    id: Optional[int] = None
    symbol: str
    signal_date: str
    signal: str
    confidence: str
    model_probability: Optional[float] = None
    fundamental_flag: Optional[str] = None
    rationale: Optional[str] = None
    horizon_days: Optional[int] = None
    actual_forward_return: Optional[float] = None
    outcome_correct: Optional[int] = None


class BacktestRunRecord(BaseModel):
    id: Optional[int] = None
    symbol: str
    run_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_trades: Optional[int] = None
    win_rate: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    strategy_return: Optional[float] = None
    baseline_return: Optional[float] = None
    notes: Optional[str] = None


class LoadPricesRequest(BaseModel):
    yf_ticker: Optional[str] = None
    period: str = "5y"


class LoadTickerRequest(BaseModel):
    yf_ticker: Optional[str] = None


class ActionResult(BaseModel):
    symbol: str
    detail: str
    data: Optional[dict[str, Any]] = None


class PriceRowIn(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


class ImportPricesRequest(BaseModel):
    rows: list[PriceRowIn]


class FundamentalRowIn(BaseModel):
    period: Optional[str] = None
    report_date: Optional[str] = None
    eps: Optional[float] = None
    revenue: Optional[float] = None
    net_profit: Optional[float] = None
    dividend_per_share: Optional[float] = None


class ImportFundamentalsRequest(BaseModel):
    rows: list[FundamentalRowIn]


class BacktestRunIn(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_trades: Optional[int] = None
    win_rate: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    strategy_return: Optional[float] = None
    baseline_return: Optional[float] = None
    notes: Optional[str] = None


class ImportBacktestRunsRequest(BaseModel):
    rows: list[BacktestRunIn]


class SignalRowIn(BaseModel):
    signal_date: str
    signal: str
    confidence: str
    model_probability: Optional[float] = None
    fundamental_flag: Optional[str] = None
    rationale: Optional[str] = None
    horizon_days: Optional[int] = None
    actual_forward_return: Optional[float] = None
    outcome_correct: Optional[int] = None


class ImportSignalsRequest(BaseModel):
    rows: list[SignalRowIn]
