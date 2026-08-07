#!/usr/bin/env python3
"""Backfill gold/silver daily bars from Alpha Vantage GOLD_SILVER_HISTORY."""

from __future__ import annotations

import sys
import time

from sqlalchemy import func, select

from app.db.models import OHLCVBar
from app.db.session import SessionLocal
from app.ingest import av_client
from app.ingest.metals import AV_TO_BAR_SYMBOL, DEFAULT_METALS, ingest_metal_history

# Usage: PYTHONPATH=. python scripts/backfill_metals.py [GOLD SILVER]


def _bar_count(db, av_symbol: str) -> int:
    bar_symbol = AV_TO_BAR_SYMBOL[av_symbol.upper()]
    return db.scalar(
        select(func.count())
        .select_from(OHLCVBar)
        .where(OHLCVBar.symbol == bar_symbol, OHLCVBar.interval == "1d")
    ) or 0


def main() -> None:
    symbols = [s.upper() for s in sys.argv[1:]] or list(DEFAULT_METALS)
    db = SessionLocal()
    try:
        total = 0
        for i, av_symbol in enumerate(symbols):
            if i:
                time.sleep(av_client.REQUEST_GAP_SECONDS)
            bars_before = _bar_count(db, av_symbol)
            n = ingest_metal_history(db, av_symbol, interval="daily")
            bars_after = _bar_count(db, av_symbol)
            total += n
            print(
                f"{av_symbol}: upserted {n} rows "
                f"({bars_after - bars_before} new in DB, {bars_after} total)"
            )
        print(f"Done — {total} rows reported inserted (0 is normal if already backfilled)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
