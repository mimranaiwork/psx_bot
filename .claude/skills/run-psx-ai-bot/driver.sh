#!/usr/bin/env bash
# Smoke-drives the psx_ai_bot CLI end-to-end. Run from the repo root
# (the directory containing main.py).
set -euo pipefail

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

echo "=== init-db ==="
python main.py init-db

echo "=== demo (synthetic data, full pipeline) ==="
python main.py demo

echo "=== train --symbol DEMO ==="
python main.py train --symbol DEMO

echo "=== backtest --symbol DEMO ==="
python main.py backtest --symbol DEMO

echo "=== signal --symbol DEMO ==="
python main.py signal --symbol DEMO

echo "=== update-outcomes --symbol DEMO ==="
python main.py update-outcomes --symbol DEMO

echo "=== load-prices from a sample CSV ==="
tmp_csv=$(mktemp /tmp/psx_sample_XXXX.csv)
cat > "$tmp_csv" <<'EOF'
date,open,high,low,close,volume
2024-01-02,100.00,101.50,99.50,101.00,500000
2024-01-03,101.00,102.00,100.50,101.75,450000
2024-01-04,101.75,103.00,101.00,102.50,600000
EOF
python main.py load-prices --symbol TEST --csv "$tmp_csv"
rm -f "$tmp_csv"

echo "=== smoke run complete ==="
