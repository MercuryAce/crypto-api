#!/usr/bin/env python3
"""Backfill gold/silver daily bars from Alpha Vantage GOLD_SILVER_HISTORY."""

from __future__ import annotations

import sys
import time

from app.db.session import SessionLocal
from app.ingest import av_client
from app.ingest.metals import DEFAULT_METALS, ingest_metal_history

# Usage: PYTHONPATH=. python scripts/backfill_metals.py [GOLD SILVER]


def main() -> None:
    symbols = [s.upper() for s in sys.argv[1:]] or list(DEFAULT_METALS)
    db = SessionLocal()
    try:
        total = 0
        for i, av_symbol in enumerate(symbols):
            if i:
                time.sleep(av_client.REQUEST_GAP_SECONDS)
            n = ingest_metal_history(db, av_symbol, interval="daily")
            total += n
            print(f"{av_symbol}: upserted {n} daily bars")
        print(f"Done — {total} rows reported inserted (conflicts may show 0)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
