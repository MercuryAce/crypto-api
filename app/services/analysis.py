"""Load OHLCV from Postgres and run comparative analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AssetRegistry, OHLCVBar
from app.services import statistics as stats

METAL_BASELINES = {"gold", "silver"}


@dataclass
class AssetRef:
    cg_id: str | None
    symbol: str | None
    binance_symbol: str


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def resolve_binance_symbol(db: Session, asset: str) -> AssetRef | None:
    key = (asset or "").strip().lower()
    if not key:
        return None

    if key in METAL_BASELINES:
        return AssetRef(cg_id=key, symbol=key, binance_symbol=key.upper())

    row = db.get(AssetRegistry, key)
    if row and row.binance_symbol:
        return AssetRef(cg_id=row.cg_id, symbol=row.symbol, binance_symbol=row.binance_symbol.upper())

    upper = asset.strip().upper()
    if upper.endswith("USDT"):
        return AssetRef(cg_id=None, symbol=None, binance_symbol=upper)

    return None


def load_closes(
    db: Session,
    binance_symbol: str,
    *,
    interval: str,
    window_days: int,
) -> tuple[list[str], list[float]]:
    stmt = (
        select(OHLCVBar.timestamp, OHLCVBar.close)
        .where(
            OHLCVBar.symbol == binance_symbol.upper(),
            OHLCVBar.interval == interval,
        )
        .order_by(OHLCVBar.timestamp.desc())
        .limit(window_days)
    )
    rows = db.execute(stmt).all()
    rows = list(reversed(rows))
    dates = [r[0].date().isoformat() for r in rows]
    closes = [float(r[1]) for r in rows]
    return dates, closes


def _unavailable(
    *,
    reason: str,
    asset: str,
    vs: str,
    window: int,
    interval: str,
    asset_ref: AssetRef | None = None,
    baseline_ref: AssetRef | None = None,
    observations: int = 0,
) -> dict:
    return {
        "available": False,
        "reason": reason,
        "min_observations": stats.MIN_OBSERVATIONS,
        "observations": observations,
        "window_days": window,
        "interval": interval,
        "asset": _asset_payload(asset_ref, asset),
        "baseline": _asset_payload(baseline_ref, vs),
    }


def _asset_payload(ref: AssetRef | None, fallback: str) -> dict:
    if ref is None:
        return {"cg_id": fallback, "symbol": None, "binance_symbol": None}
    return {
        "cg_id": ref.cg_id or fallback,
        "symbol": ref.symbol,
        "binance_symbol": ref.binance_symbol,
    }


def run_analysis(
    db: Session,
    *,
    asset: str,
    vs: str = "gold",
    window: int = 90,
    interval: str = "1d",
) -> dict:
    if interval != "1d":
        return _unavailable(
            reason="unsupported_interval",
            asset=asset,
            vs=vs,
            window=window,
            interval=interval,
        )

    asset_ref = resolve_binance_symbol(db, asset)
    if asset_ref is None:
        return _unavailable(
            reason="unknown_asset",
            asset=asset,
            vs=vs,
            window=window,
            interval=interval,
        )

    baseline_ref = resolve_binance_symbol(db, vs)
    if baseline_ref is None:
        return _unavailable(
            reason="unknown_baseline",
            asset=asset,
            vs=vs,
            window=window,
            interval=interval,
            asset_ref=asset_ref,
        )

    dates_a, closes_a = load_closes(db, asset_ref.binance_symbol, interval=interval, window_days=window)
    dates_b, closes_b = load_closes(db, baseline_ref.binance_symbol, interval=interval, window_days=window)

    dates, ca, cb = stats.align_series(dates_a, closes_a, dates_b, closes_b)
    n = len(dates)
    if n < stats.MIN_OBSERVATIONS:
        return _unavailable(
            reason="insufficient_observations",
            asset=asset,
            vs=vs,
            window=window,
            interval=interval,
            asset_ref=asset_ref,
            baseline_ref=baseline_ref,
            observations=n,
        )

    r_a = stats.log_returns(ca)
    r_b = stats.log_returns(cb)
    rel = stats.ols_beta(r_a, r_b)

    return {
        "available": True,
        "window_days": window,
        "interval": interval,
        "observations": n,
        "asset": _asset_payload(asset_ref, asset),
        "baseline": _asset_payload(baseline_ref, vs),
        "subject": {
            **stats.summary_stats(r_a),
            "cum_return": stats.cumulative_return(ca),
            "max_drawdown": stats.max_drawdown(ca),
        },
        "baseline_stats": {
            **stats.summary_stats(r_b),
            "cum_return": stats.cumulative_return(cb),
            "max_drawdown": stats.max_drawdown(cb),
        },
        "relative": {
            "correlation": stats.correlation(r_a, r_b),
            "beta": rel["beta"],
            "alpha": rel["alpha"],
            "r_squared": rel["r_squared"],
            "residual_std": rel["residual_std"],
            "tracking_error": stats.tracking_error(r_a, r_b),
            "cum_relative_return": stats.cum_relative_return(ca, cb),
            "inference": stats.inferential_summary(r_a, r_b),
        },
        "series": {
            "dates": dates,
            "subject_close": ca,
            "baseline_close": cb,
        },
    }