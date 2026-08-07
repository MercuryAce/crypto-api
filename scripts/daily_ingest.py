import sys
from datetime import date, timedelta

from app.db.session import SessionLocal
from app.ingest.binance_vision import ingest_symbol_day
from app.ingest.metals import ingest_all_metals

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]

def main():
    symbols = sys.argv[1:] or DEFAULT_SYMBOLS
    target_day = date.today() - timedelta(days=1)

    db = SessionLocal()
    try:
        for symbol in symbols:
            n = ingest_symbol_day(db, symbol.upper(), target_day)
            print(f"{symbol} {target_day}: inserted {n} rows")
        metals = ingest_all_metals(db, interval="daily")
        for av_symbol, n in metals.items():
            print(f"{av_symbol} metals refresh: upserted {n} rows")
    finally:
        db.close()

if __name__ == "__main__":
    main()