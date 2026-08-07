"""Shared OHLCV persistence helpers."""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import OHLCVBar


def upsert_bars(db: Session, bars: list[dict]) -> int:
    if not bars:
        return 0
    stmt = insert(OHLCVBar).values(bars)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["symbol", "timestamp", "interval"],
    )
    result = db.execute(stmt)
    db.commit()
    return max(result.rowcount or 0, 0)
