import sys
from datetime import date

from app.db.session import SessionLocal
from app.ingest.binance_vision import ingest_symbol_range

# Usage: python scripts/backfill_monthly.py BTCUSDT 2024-01-01 2024-01-31


def main():
    symbol = sys.argv[1].upper()
    start = date.fromisoformat(sys.argv[2])
    end = date.fromisoformat(sys.argv[3])

    db = SessionLocal()
    try:
        n = ingest_symbol_range(db, symbol, start, end)
        print(f"Backfilled {n} rows for {symbol}")
    finally:
        db.close()


if __name__ == "__main__":
    main()