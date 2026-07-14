from db import database
from ingestion.financial_report_parser import save_report, extract_field


def test_save_report_inserts_new_row(test_db):
    row_id = save_report({
        "symbol": "SYM", "period": "Q1", "report_date": "2026-01-01",
        "eps": 1.0, "revenue": 100, "net_profit": 10, "dividend_per_share": 0.5,
        "source_pdf": "test",
    })
    assert row_id is not None

    conn = database.get_connection()
    rows = conn.execute("SELECT * FROM financial_reports WHERE symbol = 'SYM'").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0]["eps"] == 1.0


def test_save_report_upserts_on_symbol_and_report_date_instead_of_duplicating(test_db):
    """
    Regression test: re-running a fundamentals loader for a symbol that
    already has a report for a given date must replace that row, not
    duplicate it -- this is exactly the bug hit when re-loading fresh
    data for symbols that already had fundamentals (financial_reports
    doubled from 583 to duplicated rows before the UNIQUE constraint +
    INSERT OR REPLACE fix).
    """
    save_report({
        "symbol": "SYM", "period": "Q1", "report_date": "2026-01-01",
        "eps": 1.0, "revenue": 100, "net_profit": 10, "dividend_per_share": 0.5,
        "source_pdf": "first-load",
    })
    save_report({
        "symbol": "SYM", "period": "Q1", "report_date": "2026-01-01",
        "eps": 1.5, "revenue": 150, "net_profit": 15, "dividend_per_share": 0.6,
        "source_pdf": "second-load",
    })

    conn = database.get_connection()
    rows = conn.execute("SELECT * FROM financial_reports WHERE symbol = 'SYM'").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0]["eps"] == 1.5
    assert rows[0]["source_pdf"] == "second-load"


def test_save_report_different_report_dates_do_not_collide(test_db):
    save_report({
        "symbol": "SYM", "period": "Q1", "report_date": "2026-01-01",
        "eps": 1.0, "revenue": 100, "net_profit": 10, "dividend_per_share": 0.5,
        "source_pdf": "test",
    })
    save_report({
        "symbol": "SYM", "period": "Q2", "report_date": "2026-04-01",
        "eps": 1.2, "revenue": 120, "net_profit": 12, "dividend_per_share": 0.5,
        "source_pdf": "test",
    })

    conn = database.get_connection()
    rows = conn.execute("SELECT * FROM financial_reports WHERE symbol = 'SYM'").fetchall()
    conn.close()
    assert len(rows) == 2


def test_extract_field_eps_pattern():
    text = "Earnings per share: Rs. 5.25 for the quarter"
    assert extract_field(text, "eps") == 5.25


def test_extract_field_returns_none_when_no_match():
    assert extract_field("no relevant numbers here", "eps") is None
