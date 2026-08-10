"""Tests for registry seed pair mapping."""

from app.ingest.registry_seed import (
    METALS,
    SkippedCoin,
    build_registry_seed,
    format_skipped_report,
    load_overrides,
    proposed_binance_pair,
    suggest_binance_pairs,
)


def test_proposed_pair_skips_stables():
    assert proposed_binance_pair("usdt") is None
    assert proposed_binance_pair("usdc") is None
    assert proposed_binance_pair("xrp") == "XRPUSDT"


def test_build_registry_seed_maps_ranked_coins():
    coins = [
        {"id": "ripple", "symbol": "xrp", "name": "XRP", "market_cap_rank": 4},
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "market_cap_rank": 1},
    ]
    pairs = {"BTCUSDT", "XRPUSDT", "ETHUSDT"}
    by_base = {"BTC": "BTCUSDT", "XRP": "XRPUSDT", "ETH": "ETHUSDT"}
    rows, skipped = build_registry_seed(
        coins, pairs, binance_by_base=by_base, include_metals=False
    )
    by_id = {cg_id: pair for cg_id, _sym, pair in rows}
    assert by_id["bitcoin"] == "BTCUSDT"
    assert by_id["ripple"] == "XRPUSDT"
    assert skipped == []


def test_build_registry_seed_skipped_has_suggestions():
    coins = [{"id": "pepe", "symbol": "pepe", "name": "Pepe", "market_cap_rank": 20}]
    pairs = {"PEPEUSDT", "1000PEPEUSDT", "BTCUSDT"}
    by_base = {"PEPE": "PEPEUSDT", "1000PEPE": "1000PEPEUSDT", "BTC": "BTCUSDT"}
    rows, skipped = build_registry_seed(
        coins, pairs, binance_by_base=by_base, include_metals=False
    )
    assert rows == [("pepe", "pepe", "PEPEUSDT")]
    assert skipped == []


def test_build_registry_seed_reports_missing_pair():
    coins = [{"id": "some-coin", "symbol": "zzz", "name": "ZZZ", "market_cap_rank": 99}]
    pairs = {"BTCUSDT"}
    by_base = {"BTC": "BTCUSDT"}
    rows, skipped = build_registry_seed(
        coins, pairs, binance_by_base=by_base, include_metals=False
    )
    assert rows == []
    assert len(skipped) == 1
    assert skipped[0].reason == "no_binance_pair"
    assert skipped[0].cg_id == "some-coin"


def test_suggest_binance_pairs_prefixed_units():
    pairs = {"1000PEPEUSDT", "PEPEUSDT", "BTCUSDT"}
    by_base = {"1000PEPE": "1000PEPEUSDT", "PEPE": "PEPEUSDT", "BTC": "BTCUSDT"}
    sugg = suggest_binance_pairs("pepe", binance_pairs=pairs, binance_by_base=by_base)
    assert "PEPEUSDT" in sugg
    assert "1000PEPEUSDT" in sugg


def test_format_skipped_report():
    text = format_skipped_report(
        [
            SkippedCoin(
                rank=3,
                cg_id="tether",
                name="Tether",
                symbol="usdt",
                reason="stable_or_quote",
                tried_pair=None,
                suggestions=[],
            )
        ]
    )
    assert "tether" in text
    assert "stable_or_quote" in text


def test_load_overrides(tmp_path):
    path = tmp_path / "overrides.json"
    path.write_text('{"ripple": "XRPUSDT", "empty": null}', encoding="utf-8")
    assert load_overrides(path) == {"ripple": "XRPUSDT"}


def test_build_registry_seed_includes_metals():
    rows, _ = build_registry_seed([], set(), include_metals=True)
    ids = {r[0] for r in rows}
    assert "gold" in ids
    assert "silver" in ids
