"""
PROTOTYPE-ONLY data loader using Yahoo Finance.

PSX-listed large caps are sometimes available on Yahoo Finance under a
`.KA` suffix (e.g. "OGDC.KA"), but this coverage is unofficial, patchy,
and NOT guaranteed accurate for Pakistani equities. Use this only to:
  - test the ingestion/feature/model pipeline end-to-end
  - prototype before official/licensed PSX data is available

Do NOT use this as the data source for real trading decisions.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database


def load_yfinance_to_db(symbol, yf_ticker=None, period="5y"):
    """
    Fetches historical data via yfinance and loads it into price_history.
    yf_ticker: override the Yahoo ticker string if it differs from `symbol`
               (e.g. symbol="OGDC", yf_ticker="OGDC.KA")
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("Run: pip install yfinance --break-system-packages")

    ticker_str = yf_ticker or symbol
    print(f"[PROTOTYPE DATA] Fetching {ticker_str} from Yahoo Finance "
          f"(unofficial source, verify before production use)")

    ticker = yf.Ticker(ticker_str)
    hist = ticker.history(period=period)

    if hist.empty:
        print(f"No data returned for {ticker_str}. Ticker may not exist on Yahoo Finance.")
        return 0

    rows = []
    for date_idx, row in hist.iterrows():
        rows.append({
            "date": date_idx.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
        })

    database.upsert_price_rows(symbol, rows)
    print(f"Loaded {len(rows)} rows for {symbol} (as {ticker_str}) from Yahoo Finance")
    return len(rows)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="[Prototype only] Load data via Yahoo Finance")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--yf-ticker", required=False, default=None)
    parser.add_argument("--period", default="5y")
    args = parser.parse_args()
    load_yfinance_to_db(args.symbol, args.yf_ticker, args.period)
