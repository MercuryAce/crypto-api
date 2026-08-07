"""Ingest daily gold/silver prices from Alpha Vantage into OHLCVBar."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.ingest import av_client
from app.ingest.store import upsert_bars
from app.db.models import IngestState

# AV symbol -> OHLCVBar symbol (matches analysis METAL_BASELINES)
AV_TO_BAR_SYMBOL = {
    "GOLD": "GOLD",
    "XAU": "GOLD",
    "SILVER": "SILVER",
    "XAG": "SILVER",
}

DEFAULT_METALS = ("GOLD", "SILVER")


def _parse_day(raw: str) -> date:
    return date.fromisoformat(raw[:10])


def _day_to_ts(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)


def history_to_bars(payload: dict, *, av_symbol: str) -> list[dict]:
    """Convert GOLD_SILVER_HISTORY JSON to OHLCVBar row dicts."""
    bar_symbol = AV_TO_BAR_SYMBOL.get(av_symbol.upper())
    if bar_symbol is None:
        raise ValueError(f"Unsupported AV metal symbol: {av_symbol}")

    observations = payload.get("data")
    if not isinstance(observations, list):
        raise ValueError("GOLD_SILVER_HISTORY response missing data list")

    bars: list[dict] = []
    for obs in observations:
        if not isinstance(obs, dict):
            continue
        day_raw = obs.get("date")
        # AV JSON uses "price"; some docs/examples use "value"
        value = obs.get("price", obs.get("value"))
        if not day_raw or value in (None, "", "."):
            continue
        try:
            close = float(value)
            day = _parse_day(str(day_raw))
        except (TypeError, ValueError):
            continue
        if close <= 0:
            continue
        bars.append({
            "symbol": bar_symbol,
            "timestamp": _day_to_ts(day),
            "interval": "1d",
            "open_": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 0.0,
            "source": "alphavantage",
        })
    return bars


def ingest_metal_history(
    db: Session,
    av_symbol: str,
    *,
    interval: str = "daily",
) -> int:
    """Fetch AV history for one metal and upsert daily bars."""
    payload = av_client.get_gold_silver_history(av_symbol, interval=interval)
    bars = history_to_bars(payload, av_symbol=av_symbol)
    if not bars:
        keys = list(payload.keys()) if isinstance(payload, dict) else []
        sample = payload.get("data", [])[:1] if isinstance(payload, dict) else []
        raise ValueError(
            f"No bars parsed for {av_symbol}; response keys={keys!r}, "
            f"data_len={len(payload.get('data', [])) if isinstance(payload, dict) else 0}, "
            f"sample={sample!r}"
        )
    count = upsert_bars(db, bars)

    bar_symbol = AV_TO_BAR_SYMBOL[av_symbol.upper()]
    if bars:
        last_ts = max(b["timestamp"] for b in bars)
        state = db.get(IngestState, bar_symbol)
        if state is None:
            state = IngestState(symbol=bar_symbol, last_daily_date=last_ts)
            db.add(state)
        elif state.last_daily_date is None or last_ts > state.last_daily_date:
            state.last_daily_date = last_ts
        db.commit()

    return count


def ingest_all_metals(db: Session, *, interval: str = "daily") -> dict[str, int]:
    """Refresh gold and silver; respects AV rate limits between calls."""
    import time

    results: dict[str, int] = {}
    for i, av_symbol in enumerate(DEFAULT_METALS):
        if i:
            time.sleep(av_client.REQUEST_GAP_SECONDS)
        results[av_symbol] = ingest_metal_history(db, av_symbol, interval=interval)
    return results
