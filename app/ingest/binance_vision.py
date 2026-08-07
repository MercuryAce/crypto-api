import io
import zipfile
from datetime import date, datetime, timedelta, timezone

import httpx
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import IngestState
from app.ingest.store import upsert_bars

BASE_URL = "https://data.binance.vision/data/spot/daily/klines"

def _day_url(symbol: str, day: date) -> str:
    d = day.isoformat()
    sym = symbol.upper()
    return f"{BASE_URL}/{sym}/1d/{sym}-1d-{d}.zip"

def fetch_daily_bars(symbol: str, day: date) -> list[dict]:
    url = _day_url(symbol, day)
    response = httpx.get(url, timeout=60.0)
    if response.status_code == 404:
        return []
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        csv_name = zf.namelist()[0]
        with zf.open(csv_name) as csv_file:
            df = pd.read_csv(
                csv_file,
                header=None,
                names=[
                    "open_time", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume", "trades",
                    "taker_buy_base", "taker_buy_quote", "ignore",
                ],
            )

    rows = []
    for _, r in df.iterrows():
        try:
            ts = _open_time_to_datetime(r["open_time"])
            rows.append({
                "symbol": symbol.upper(),
                "timestamp": ts,
                "interval": "1d",
                "open_": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["volume"]),
                "source": "binance_vision",
            })
        except (ValueError, OverflowError, TypeError):
            continue
    return rows

def ingest_symbol_day(db: Session, symbol: str, day: date) -> int:
    bars = fetch_daily_bars(symbol, day)
    count = upsert_bars(db, bars)

    state = db.get(IngestState, symbol)
    day_dt = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    if state is None:
        state = IngestState(symbol=symbol, last_daily_date=day_dt)
        db.add(state)
    elif state.last_daily_date is None or day_dt > state.last_daily_date:
        state.last_daily_date = day_dt
    db.commit()

    return count

def ingest_symbol_range(db: Session, symbol: str, start: date, end: date) -> int:
    total = 0
    day = start
    while day <= end:
        total += ingest_symbol_day(db, symbol, day)
        day += timedelta(days=1)
    return total

def _open_time_to_datetime(raw) -> datetime:
    v = int(float(raw))
    if v >= 10**14: # BV microseconds format
        v //= 1000  # -> milliseconds
    return datetime.fromtimestamp(v / 1000, tz=timezone.utc)
