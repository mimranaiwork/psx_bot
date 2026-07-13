import pytest

from features import fundamental_features
from ingestion.financial_report_parser import save_report


def _insert_reports(symbol, quarters):
    for q in quarters:
        save_report({"symbol": symbol, "source_pdf": "test", **q})


def test_none_returned_with_fewer_than_two_reports(test_db):
    _insert_reports("SYM", [
        {"period": "Q1", "report_date": "2025-01-01", "eps": 1.0, "revenue": 100,
         "net_profit": 10, "dividend_per_share": 0.5},
    ])
    assert fundamental_features.get_fundamental_features("SYM") is None


def test_qoq_growth_with_two_reports_and_no_yoy_yet(test_db):
    _insert_reports("SYM", [
        {"period": "Q1", "report_date": "2025-01-01", "eps": 1.0, "revenue": 100,
         "net_profit": 10, "dividend_per_share": 0.5},
        {"period": "Q2", "report_date": "2025-04-01", "eps": 1.5, "revenue": 150,
         "net_profit": 20, "dividend_per_share": 0.6},
    ])
    feats = fundamental_features.get_fundamental_features("SYM")
    assert feats is not None
    assert feats["eps_growth_qoq"] == pytest.approx(0.5)
    assert feats["revenue_growth_qoq"] == pytest.approx(0.5)
    assert feats["eps_growth_yoy"] is None  # needs 5 periods


def test_yoy_growth_with_five_reports(test_db):
    quarters = [
        {"period": f"Q{i}", "report_date": f"2025-0{i}-01", "eps": eps, "revenue": rev,
         "net_profit": np_, "dividend_per_share": 0.5}
        for i, (eps, rev, np_) in enumerate(
            [(1.0, 100, 10), (1.1, 110, 11), (1.2, 120, 12), (1.3, 130, 13), (1.5, 150, 15)],
            start=1,
        )
    ]
    _insert_reports("SYM", quarters)
    feats = fundamental_features.get_fundamental_features("SYM")

    assert feats["eps_growth_yoy"] == pytest.approx((1.5 - 1.0) / 1.0)
    assert feats["revenue_growth_yoy"] == pytest.approx((150 - 100) / 100)


def test_net_margin_and_margin_trend(test_db):
    _insert_reports("SYM", [
        {"period": "Q1", "report_date": "2025-01-01", "eps": 1.0, "revenue": 100,
         "net_profit": 10, "dividend_per_share": 0.5},
        {"period": "Q2", "report_date": "2025-04-01", "eps": 1.1, "revenue": 100,
         "net_profit": 5, "dividend_per_share": 0.5},
    ])
    feats = fundamental_features.get_fundamental_features("SYM")
    assert feats["net_margin"] == pytest.approx(0.05)
    assert feats["margin_trend"] == pytest.approx(0.05 - 0.10)


def test_safe_pct_change_edge_cases():
    assert fundamental_features._safe_pct_change(0, 10) is None
    assert fundamental_features._safe_pct_change(None, 10) is None
    assert fundamental_features._safe_pct_change(10, 15) == pytest.approx(0.5)


def test_safe_div_edge_cases():
    assert fundamental_features._safe_div(10, 0) is None
    assert fundamental_features._safe_div(10, None) is None
    assert fundamental_features._safe_div(10, 4) == pytest.approx(2.5)
