"""
PROTOTYPE-ONLY announcements loader using Yahoo Finance's news feed.

This is syndicated financial news aggregated by Yahoo Finance (headlines,
summaries, publish dates) for a ticker -- not PSX's own regulatory
announcements (dividends/bonus/rights/director dealings filed on
dps.psx.com.pk). Coverage for PSX-listed names is sparse and often not
recent. Use this only to exercise the announcements/event_features
pipeline end-to-end; do NOT treat it as a substitute for real PSX
disclosures.

Reuses the same category keyword classifier as
ingestion/announcement_loader.py so downstream features behave
identically regardless of data source.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database
from ingestion.announcement_loader import categorize_announcement


def load_yfinance_news(symbol, yf_ticker=None):
    """
    Fetches the current news feed via yfinance and inserts one
    announcements row per item. Returns the number of rows written.
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("Run: pip install yfinance --break-system-packages")

    ticker_str = yf_ticker or symbol
    print(f"[PROTOTYPE DATA] Fetching {ticker_str} news from Yahoo Finance "
          f"(unofficial, syndicated financial news -- not PSX regulatory "
          f"announcements)")

    ticker = yf.Ticker(ticker_str)
    news = ticker.news or []

    if not news:
        print(f"No news returned for {ticker_str}.")
        return 0

    conn = database.get_connection()
    written = 0
    try:
        cur = conn.cursor()
        for item in news:
            content = item.get("content", item)
            title = content.get("title", "")
            summary = content.get("summary") or content.get("description") or ""
            pub_date = content.get("pubDate")
            url = (content.get("canonicalUrl") or {}).get("url", "")

            if not title or not pub_date:
                continue

            raw_text = f"{title}. {summary}".strip()
            category = categorize_announcement(raw_text)
            announced_at = pub_date.replace("Z", "").replace("T", " ")

            cur.execute(
                """
                INSERT INTO announcements (symbol, announced_at, category, raw_text, source_url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (symbol, announced_at, category, raw_text, url),
            )
            written += 1
        conn.commit()
    finally:
        conn.close()

    print(f"Loaded {written} announcement rows for {symbol} (as {ticker_str})")
    return written


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="[Prototype only] Load news/announcements via Yahoo Finance")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--yf-ticker", required=False, default=None)
    args = parser.parse_args()
    load_yfinance_news(args.symbol, args.yf_ticker)
