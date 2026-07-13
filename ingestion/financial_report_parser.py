"""
Parses financial report PDFs into structured fields (EPS, revenue, net
profit, dividend per share) and stores them in financial_reports.

Reality check: PSX-listed companies report in inconsistent formats
("Net Profit" vs "Profit After Tax" vs "PAT"). This module handles common
patterns via regex; expect to extend FIELD_PATTERNS for companies whose
reports don't match. For irregular layouts, route the extracted raw text
through models/llm_synthesis.py's extraction helper instead.
"""
import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database

FIELD_PATTERNS = {
    "eps": [
        r"earnings?\s+per\s+share.*?(?:rs\.?)?\s*([\d,]+\.?\d*)",
        r"eps.*?(?:rs\.?)?\s*([\d,]+\.?\d*)",
    ],
    "revenue": [
        r"(?:net\s+)?revenue.*?(?:rs\.?)?\s*([\d,]+\.?\d*)",
        r"turnover.*?(?:rs\.?)?\s*([\d,]+\.?\d*)",
    ],
    "net_profit": [
        r"profit\s+after\s+tax.*?(?:rs\.?)?\s*([\d,]+\.?\d*)",
        r"net\s+profit.*?(?:rs\.?)?\s*([\d,]+\.?\d*)",
        r"\bpat\b.*?(?:rs\.?)?\s*([\d,]+\.?\d*)",
    ],
    "dividend_per_share": [
        r"dividend\s+per\s+share.*?(?:rs\.?)?\s*([\d,]+\.?\d*)",
        r"cash\s+dividend.*?(?:rs\.?)?\s*([\d,]+\.?\d*)\s*per\s+share",
    ],
}


def extract_field(text, field_name):
    patterns = FIELD_PATTERNS.get(field_name, [])
    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
        if match:
            raw_num = match.group(1).replace(",", "")
            try:
                return float(raw_num)
            except ValueError:
                continue
    return None


def parse_pdf(pdf_path, symbol, period, report_date):
    """
    Extracts text from a financial report PDF and attempts to pull out
    key fields. Returns a dict; unmatched fields are None and should be
    filled in manually or reviewed before trusting the row.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("Run: pip install pdfplumber --break-system-packages")

    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            full_text += page_text + "\n"

    result = {
        "symbol": symbol,
        "period": period,
        "report_date": report_date,
        "eps": extract_field(full_text, "eps"),
        "revenue": extract_field(full_text, "revenue"),
        "net_profit": extract_field(full_text, "net_profit"),
        "dividend_per_share": extract_field(full_text, "dividend_per_share"),
        "source_pdf": pdf_path,
    }

    missing = [k for k, v in result.items() if v is None and k not in ("symbol", "period", "report_date", "source_pdf")]
    if missing:
        print(f"WARNING: could not extract fields {missing} from {pdf_path}. "
              f"Review manually or extend FIELD_PATTERNS for this company's report format.")

    return result


def save_report(report_dict):
    conn = database.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO financial_reports
                (symbol, period, report_date, eps, revenue, net_profit, dividend_per_share, source_pdf)
            VALUES (:symbol, :period, :report_date, :eps, :revenue, :net_profit, :dividend_per_share, :source_pdf)
            """,
            report_dict,
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parse a financial report PDF")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--period", required=True, help='e.g. "Q3 FY26"')
    parser.add_argument("--report-date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()
    result = parse_pdf(args.pdf, args.symbol, args.period, args.report_date)
    print(result)
    save_report(result)
