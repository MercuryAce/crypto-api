from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import OHLCVBar
from app.db.session import get_db

from auth import require_api_key
router = APIRouter(
    prefix="/bars", tags=["bars"]
)

@router.get("/{symbol}")
async def get_bars(
        symbol: str,
        interval: str = Query(default="1d"),
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = Query(50, alias="limit", le=5000),
        db: Session = Depends(get_db),
        _key: str = Depends(require_api_key)
):
    stmt = (
        select(OHLCVBar)
        .where(OHLCVBar.symbol == symbol.upper(), OHLCVBar.interval == interval)
        .order_by(OHLCVBar.timestamp.desc())
        .limit(limit)
    )
    if start is not None:
        stmt = stmt.where(OHLCVBar.timestamp >= start)
    if end is not None:
        stmt = stmt.where(OHLCVBar.timestamp <= end)

    rows = db.scalars(stmt).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Bars not found")

    return [
        {
            "symbol": row.symbol,
            "timestamp": row.timestamp,
            "interval": row.interval,
            "open": row.open_,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume,
            "source": row.source,

        }
        for row in rows
    ]