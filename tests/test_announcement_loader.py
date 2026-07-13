import json

import pytest

from db import database
from ingestion import announcement_loader


@pytest.mark.parametrize("text,expected_category", [
    ("Company announces quarterly results with EPS of Rs 5", "earnings"),
    ("Board declares interim dividend of Rs 2 per share", "dividend"),
    ("Company announces bonus shares issue", "bonus"),
    ("Rights issue announced at Rs 10 per share", "rights"),
    ("Trading in shares by director disclosed", "director_dealing"),
    ("Resignation of Chief Executive Officer announced", "mgmt_change"),
    ("Company signs new supply agreement", "other"),
])
def test_categorize_announcement(text, expected_category):
    assert announcement_loader.categorize_announcement(text) == expected_category


def test_load_from_json_inserts_and_categorizes(test_db, tmp_path):
    items = [
        {"symbol": "SYM", "announced_at": "2026-07-01T10:00:00",
         "raw_text": "quarterly results announced", "source_url": "http://x"},
        {"symbol": "SYM", "announced_at": "2026-07-02T10:00:00",
         "raw_text": "unrelated corporate news"},
    ]
    json_path = tmp_path / "announcements.json"
    json_path.write_text(json.dumps(items))

    count = announcement_loader.load_from_json(str(json_path))
    assert count == 2

    conn = database.get_connection()
    rows = conn.execute(
        "SELECT symbol, category, raw_text FROM announcements ORDER BY id"
    ).fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0]["category"] == "earnings"
    assert rows[1]["category"] == "other"
    assert rows[0]["symbol"] == "SYM"
