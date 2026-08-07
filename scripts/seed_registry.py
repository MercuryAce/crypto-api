"""Seed asset_registry from CoinGecko top market cap + Binance USDT pairs."""

from __future__ import annotations

import argparse

from app.db.models import AssetRegistry
from app.db.session import SessionLocal
from app.ingest.registry_seed import (
    METALS,
    build_registry_seed,
    fetch_binance_usdt_pairs,
    fetch_coingecko_top,
)


def seed_registry(
    db,
    rows: list[tuple[str, str, str]],
) -> int:
    for cg_id, symbol, pair in rows:
        row = db.get(AssetRegistry, cg_id) or AssetRegistry(cg_id=cg_id)
        row.symbol = symbol
        row.binance_symbol = pair
        db.merge(row)
    db.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed asset_registry from CoinGecko top N.")
    parser.add_argument("--limit", type=int, default=100, help="Top coins by market cap (default 100)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned rows without writing to Postgres",
    )
    args = parser.parse_args()

    coins = fetch_coingecko_top(limit=args.limit)
    binance_pairs = fetch_binance_usdt_pairs()
    rows, skipped = build_registry_seed(coins, binance_pairs)

    crypto_rows = [r for r in rows if r[0] not in {m[0] for m in METALS}]
    print(f"CoinGecko top {args.limit}: {len(coins)} fetched")
    print(f"Binance USDT pairs: {len(binance_pairs)}")
    print(f"Registry rows to write: {len(rows)} ({len(crypto_rows)} crypto + {len(METALS)} metals)")
    if skipped:
        print(f"Skipped {len(skipped)} coins (no Binance USDT pair or duplicate pair)")

    if args.dry_run:
        for cg_id, symbol, pair in rows[:20]:
            print(f"  {cg_id:20} {symbol:8} -> {pair}")
        if len(rows) > 20:
            print(f"  ... and {len(rows) - 20} more")
        return

    db = SessionLocal()
    try:
        n = seed_registry(db, rows)
        print(f"Seeded {n} assets")
    finally:
        db.close()


if __name__ == "__main__":
    main()
