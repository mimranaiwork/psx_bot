"""
PROTOTYPE-ONLY fundamentals loader using Yahoo Finance.

Pulls quarterly EPS/revenue/net income for PSX-listed large caps that are
unofficially covered on Yahoo Finance under a `.KA` suffix (e.g.
"OGDC.KA"). Same caveats as ingestion/yfinance_loader.py: unofficial,
patchy, NOT guaranteed accurate for Pakistani equities, and typically
only the last 4-6 quarters are available (Yahoo does not backfill PSX
financials the way it does for US equities).

Do NOT use this as the data source for real trading decisions. It exists
to unblock the fundamental_features/fundamental_rules pipeline for
prototyping until real (manually obtained or licensed) financial report
PDFs are fed through ingestion/financial_report_parser.py instead.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingestion.financial_report_parser import save_report


def load_yfinance_fundamentals(symbol, yf_ticker=None):
    """
    Fetches quarterly_financials via yfinance and inserts one
    financial_reports row per quarter with non-null EPS.
    Returns the number of rows written.
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("Run: pip install yfinance --break-system-packages")

    ticker_str = yf_ticker or symbol
    print(f"[PROTOTYPE DATA] Fetching {ticker_str} quarterly fundamentals from "
          f"Yahoo Finance (unofficial source, verify before production use)")

    ticker = yf.Ticker(ticker_str)
    qf = ticker.quarterly_financials

    if qf is None or qf.empty:
        print(f"No quarterly financials returned for {ticker_str}.")
        return 0

    def _row(label):
        return qf.loc[label] if label in qf.index else None

    eps_row = _row("Basic EPS")
    revenue_row = _row("Total Revenue")
    if revenue_row is None:
        revenue_row = _row("Operating Revenue")
    net_income_row = _row("Net Income")

    written = 0
    for report_date in qf.columns:
        eps = eps_row.get(report_date) if eps_row is not None else None
        if eps is None or eps != eps:  # NaN check
            continue

        revenue = revenue_row.get(report_date) if revenue_row is not None else None
        net_profit = net_income_row.get(report_date) if net_income_row is not None else None

        report = {
            "symbol": symbol,
            "period": f"Q ending {report_date.strftime('%Y-%m-%d')}",
            "report_date": report_date.strftime("%Y-%m-%d"),
            "eps": round(float(eps), 4),
            "revenue": float(revenue) if revenue is not None and revenue == revenue else None,
            "net_profit": float(net_profit) if net_profit is not None and net_profit == net_profit else None,
            "dividend_per_share": None,
            "source_pdf": f"yfinance:{ticker_str}",
        }
        save_report(report)
        written += 1

    print(f"Loaded {written} quarterly financial_reports rows for {symbol} (as {ticker_str})")
    return written


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="[Prototype only] Load quarterly fundamentals via Yahoo Finance")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--yf-ticker", required=False, default=None)
    args = parser.parse_args()
    load_yfinance_fundamentals(args.symbol, args.yf_ticker)
