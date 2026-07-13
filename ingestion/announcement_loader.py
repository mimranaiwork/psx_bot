"""
Loads company announcements into the database from a local JSON or CSV
export (e.g. one you've manually saved, or obtained via a licensed feed).

This module intentionally does NOT scrape dps.psx.com.pk/announcements
directly. Once PSX confirms licensing terms for automated access, replace
`load_from_json`'s data source with an authorized API/feed call — the
downstream schema and classification logic stay the same.

Expected JSON format (list of objects):
[
  {
    "symbol": "OGDC",
    "announced_at": "2026-07-10T14:32:00",
    "raw_text": "OGDC announces quarterly results with EPS of Rs 5.20...",
    "source_url": "https://dps.psx.com.pk/..."
  },
  ...
]
"""
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database


CATEGORY_KEYWORDS = {
    "earnings": ["quarterly results", "annual results", "eps", "profit after tax", "financial results"],
    "dividend": ["dividend", "cash dividend", "interim dividend"],
    "bonus": ["bonus shares", "bonus issue"],
    "rights": ["right shares", "rights issue"],
    "director_dealing": ["director", "sponsor", "trading in shares by"],
    "mgmt_change": ["resignation", "appointment", "chief executive", "board of directors"],
}


def categorize_announcement(raw_text):
    """Simple keyword-based categorization. Swap for an LLM classifier
    (see models/llm_synthesis.py) for higher accuracy on ambiguous text."""
    text_lower = raw_text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "other"


def load_from_json(json_path):
    with open(json_path, "r") as f:
        items = json.load(f)

    conn = database.get_connection()
    try:
        cur = conn.cursor()
        count = 0
        for item in items:
            category = categorize_announcement(item.get("raw_text", ""))
            cur.execute(
                """
                INSERT INTO announcements (symbol, announced_at, category, raw_text, source_url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item["symbol"],
                    item["announced_at"],
                    category,
                    item.get("raw_text", ""),
                    item.get("source_url", ""),
                ),
            )
            count += 1
        conn.commit()
        print(f"Loaded {count} announcements from {json_path}")
        return count
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Load announcements from a JSON export")
    parser.add_argument("--json", required=True, help="Path to announcements JSON file")
    args = parser.parse_args()
    load_from_json(args.json)
