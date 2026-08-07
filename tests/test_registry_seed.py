"""Tests for registry seed pair mapping."""

from app.ingest.registry_seed import build_registry_seed, proposed_binance_pair


def test_proposed_pair_skips_stables():
    assert proposed_binance_pair("usdt") is None
    assert proposed_binance_pair("usdc") is None
    assert proposed_binance_pair("xrp") == "XRPUSDT"


def test_build_registry_seed_maps_ranked_coins():
    coins = [
        {"id": "ripple", "symbol": "xrp", "market_cap_rank": 4},
        {"id": "bitcoin", "symbol": "btc", "market_cap_rank": 1},
    ]
    pairs = {"BTCUSDT", "XRPUSDT", "ETHUSDT"}
    rows, skipped = build_registry_seed(coins, pairs, include_metals=False)
    by_id = {cg_id: pair for cg_id, _sym, pair in rows}
    assert by_id["bitcoin"] == "BTCUSDT"
    assert by_id["ripple"] == "XRPUSDT"
    assert skipped == []


def test_build_registry_seed_skips_missing_binance_pair():
    coins = [{"id": "some-coin", "symbol": "zzz", "market_cap_rank": 99}]
    rows, skipped = build_registry_seed(coins, {"BTCUSDT"}, include_metals=False)
    assert rows == []
    assert len(skipped) == 1


def test_build_registry_seed_includes_metals():
    rows, _ = build_registry_seed([], set(), include_metals=True)
    ids = {r[0] for r in rows}
    assert "gold" in ids
    assert "silver" in ids
