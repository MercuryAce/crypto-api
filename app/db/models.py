from datetime import datetime, timezone
from typing import ClassVar

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OHLCVBar(Base):
    __tablename__ = "ohlcv_bars"
    # Trailing comma is required — (Index(...)) is an Index, not a tuple.
    __table_args__: ClassVar[tuple[Index, ...]] = (
        Index("ix_ohlcv_symbol_timestamp", "symbol", "timestamp"),
    )

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    interval: Mapped[str] = mapped_column(String(8), primary_key=True)

    open_: Mapped[float] = mapped_column("open", Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64), default="binance_vision")


class AssetRegistry(Base):
    __tablename__ = 'asset_registry'

    cg_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    binance_symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    binance_state: Mapped[str | None] = mapped_column(String(64), nullable=True)


class IngestState(Base):
    __tablename__ = 'ingest_state'

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_daily_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
