"""Seed asset_registry from CoinGecko top market cap + Binance USDT pairs."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.db.models import AssetRegistry
from app.db.session import SessionLocal
from app.ingest.registry_seed import (
    METALS,
    build_registry_seed,
    enrich_skipped_suggestions,
    fetch_binance_usdt_index,
    fetch_coingecko_top,
    format_skipped_report,
    load_overrides,
    write_skipped_json,
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
    parser.add_argument(
        "--overrides",
        type=Path,
        help="JSON file {cg_id: BINANCE_PAIR} applied before auto-mapping",
    )
    parser.add_argument(
        "--report-skipped",
        action="store_true",
        help="Print skipped coins with Binance pair suggestions",
    )
    parser.add_argument(
        "--skipped-out",
        type=Path,
        help="Write skipped report JSON (includes override_template)",
    )
    parser.add_argument(
        "--fetch-cg-tickers",
        action="store_true",
        help="For unresolved skips, query CoinGecko /coins/{id}/tickers (slower)",
    )
    args = parser.parse_args()

    overrides = load_overrides(args.overrides)
    coins = fetch_coingecko_top(limit=args.limit)
    binance_pairs, binance_by_base = fetch_binance_usdt_index()
    rows, skipped = build_registry_seed(
        coins,
        binance_pairs,
        binance_by_base=binance_by_base,
        overrides=overrides,
    )

    if args.fetch_cg_tickers:
        enrich_skipped_suggestions(
            skipped,
            binance_pairs=binance_pairs,
            binance_by_base=binance_by_base,
            fetch_cg_tickers=True,
        )

    crypto_rows = [r for r in rows if r[0] not in {m[0] for m in METALS}]
    print(f"CoinGecko top {args.limit}: {len(coins)} fetched")
    print(f"Binance USDT pairs: {len(binance_pairs)}")
    if overrides:
        print(f"Manual overrides loaded: {len(overrides)}")
    print(f"Registry rows to write: {len(rows)} ({len(crypto_rows)} crypto + {len(METALS)} metals)")
    if skipped:
        print(f"Skipped {len(skipped)} coins (no Binance USDT pair or duplicate pair)")

    if args.report_skipped or args.skipped_out:
        print()
        print(format_skipped_report(skipped))
    if args.skipped_out:
        write_skipped_json(args.skipped_out, skipped)
        print()
        print(f"Wrote skipped report: {args.skipped_out}")

    if args.dry_run:
        print()
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
