const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface SymbolSummary {
  symbol: string;
  row_count: number;
  latest_date: string | null;
}

export interface PriceRow {
  symbol: string;
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  ema_20: number | null;
  ema_50: number | null;
  rsi_14: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  bb_mid: number | null;
  bb_upper: number | null;
  bb_lower: number | null;
  bb_width: number | null;
  atr_14: number | null;
  volume_avg_30: number | null;
  volume_spike_ratio: number | null;
  roc_10: number | null;
  roc_20: number | null;
  price_vs_sma50: number | null;
  price_vs_sma200: number | null;
  sma20_vs_sma50: number | null;
}

export type SignalName = "BUY" | "HOLD" | "SELL";
export type Confidence = "High" | "Moderate" | "Low";

export interface SignalRecord {
  id: number;
  symbol: string;
  signal_date: string;
  signal: SignalName;
  confidence: Confidence;
  model_probability: number | null;
  fundamental_flag: string | null;
  rationale: string | null;
  horizon_days: number | null;
  actual_forward_return: number | null;
  outcome_correct: number | null;
}

export interface BacktestRun {
  id: number;
  symbol: string;
  run_date: string | null;
  start_date: string | null;
  end_date: string | null;
  total_trades: number | null;
  win_rate: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  strategy_return: number | null;
  baseline_return: number | null;
  notes: string | null;
}

export interface ActionResult<T = Record<string, unknown>> {
  symbol: string;
  detail: string;
  data: T | null;
}

export interface BreakoutCandidate {
  symbol: string;
  is_pre_breakout: boolean;
  reason?: string;
  checks_passed?: number;
  squeeze?: boolean;
  near_resistance?: boolean;
  volume_building?: boolean;
  momentum_ok?: boolean;
  bb_width_percentile?: number;
  pct_from_high?: number;
  volume_spike_ratio?: number;
  rsi_14?: number;
  close?: number;
  trade_date?: string;
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json();
}

export const api = {
  listSymbols: () => request<SymbolSummary[]>("/symbols"),
  getPrices: (symbol: string) => request<PriceRow[]>(`/symbols/${symbol}/prices`),

  latestSignals: () => request<SignalRecord[]>("/signals/latest"),
  signalsLog: (symbol?: string) =>
    request<SignalRecord[]>(`/signals-log${symbol ? `?symbol=${symbol}` : ""}`),
  latestSignalFor: (symbol: string) => request<SignalRecord>(`/symbols/${symbol}/signal`),

  backtests: (symbol?: string) =>
    request<BacktestRun[]>(`/backtests${symbol ? `?symbol=${symbol}` : ""}`),

  breakoutScreener: (flaggedOnly = true) =>
    request<BreakoutCandidate[]>(`/screener/breakouts?flagged_only=${flaggedOnly}`),

  loadPrices: (symbol: string, yfTicker: string, period = "5y") =>
    request<ActionResult>(`/symbols/${symbol}/load-prices`, {
      method: "POST",
      body: JSON.stringify({ yf_ticker: yfTicker, period }),
    }),
  loadFundamentals: (symbol: string, yfTicker: string) =>
    request<ActionResult>(`/symbols/${symbol}/load-fundamentals`, {
      method: "POST",
      body: JSON.stringify({ yf_ticker: yfTicker }),
    }),
  loadNews: (symbol: string, yfTicker: string) =>
    request<ActionResult>(`/symbols/${symbol}/load-news`, {
      method: "POST",
      body: JSON.stringify({ yf_ticker: yfTicker }),
    }),
  train: (symbol: string) =>
    request<ActionResult>(`/symbols/${symbol}/train`, { method: "POST" }),
  backtest: (symbol: string) =>
    request<ActionResult>(`/symbols/${symbol}/backtest`, { method: "POST" }),
  generateSignal: (symbol: string) =>
    request<ActionResult<SignalRecord>>(`/symbols/${symbol}/signal`, { method: "POST" }),
  updateOutcomes: (symbol: string) =>
    request<ActionResult>(`/symbols/${symbol}/update-outcomes`, { method: "POST" }),
};

export { ApiError };
