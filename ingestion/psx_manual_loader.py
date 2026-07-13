"""
Loads PSX price history from a CSV file YOU have already obtained legally —
via manual download from PSX's Historical Data page (personal/non-commercial
use, per their terms) or a licensed data feed.

This module does NOT scrape or automate collection from dps.psx.com.pk.
Automating collection from that site requires written permission from
marketdatarequest@psx.com.pk — see README.md.

Expected CSV format (data/prices/{SYMBOL}.csv):
    date,open,high,low,close,volume
    2024-01-02,101.50,103.00,101.00,102.75,1250000
    ...
"""
import os
import sys
import csv
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from db import database


def load_csv_to_db(symbol, csv_path=None):
    """
    Reads a CSV of OHLCV data for `symbol` and upserts it into price_history.
    Returns the number of rows written.
    """
    if csv_path is None:
        csv_path = os.path.join(config.PRICES_DIR, f"{symbol}.csv")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"No CSV found at {csv_path}. Place a manually-obtained/licensed "
            f"PSX historical export there first (see README.md)."
        )

    rows = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        required_cols = {"date", "open", "high", "low", "close", "volume"}
        if not required_cols.issubset({c.strip().lower() for c in reader.fieldnames}):
            raise ValueError(
                f"CSV must have columns: {required_cols}. Found: {reader.fieldnames}"
            )
        for r in reader:
            r = {k.strip().lower(): v for k, v in r.items()}
            try:
                # Normalize date to ISO format regardless of input format
                date_val = _parse_date(r["date"])
            except Exception as e:
                print(f"Skipping row with unparseable date '{r['date']}': {e}")
                continue
            rows.append({
                "date": date_val,
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": int(float(r["volume"])) if r["volume"] else 0,
            })

    if not rows:
        print(f"No valid rows found in {csv_path}")
        return 0

    written = database.upsert_price_rows(symbol, rows)
    print(f"Loaded {len(rows)} rows for {symbol} from {csv_path}")
    return len(rows)


def _parse_date(date_str):
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Load PSX price CSV into the database")
    parser.add_argument("--symbol", required=True, help="Stock symbol, e.g. OGDC")
    parser.add_argument("--csv", required=False, help="Path to CSV file (optional)")
    args = parser.parse_args()
    load_csv_to_db(args.symbol, args.csv)
