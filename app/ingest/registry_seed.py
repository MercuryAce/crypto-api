"""Build asset_registry rows from CoinGecko top market cap + Binance USDT pairs."""

from __future__ import annotations

import httpx

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
BINANCE_EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"

METALS = [
    ("gold", "xau", "GOLD"),
    ("silver", "xag", "SILVER"),
]

# Skip stables / quote assets — never map to SYMBOLUSDT.
SKIP_SYMBOLS = frozenset(
    {
        "usdt",
        "usdc",
        "usde",
        "dai",
        "fdusd",
        "tusd",
        "busd",
        "usdp",
        "pyusd",
        "eurc",
        "usd1",
    }
)


def fetch_coingecko_top(*, limit: int = 100, timeout: float = 30.0) -> list[dict]:
    per_page = min(max(limit, 1), 250)
    response = httpx.get(
        COINGECKO_MARKETS_URL,
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": 1,
            "sparkline": "false",
        },
        timeout=timeout,
        headers={"accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("unexpected CoinGecko markets payload")
    return payload[:limit]


def fetch_binance_usdt_pairs(*, timeout: float = 30.0) -> set[str]:
    """Return set of Binance spot USDT pair symbols (e.g. BTCUSDT)."""
    response = httpx.get(BINANCE_EXCHANGE_INFO_URL, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    symbols = payload.get("symbols") or []
    out: set[str] = set()
    for row in symbols:
        if row.get("status") != "TRADING":
            continue
        if row.get("quoteAsset") != "USDT":
            continue
        if row.get("isSpotTradingAllowed") is False:
            continue
        sym = row.get("symbol")
        if sym:
            out.add(str(sym).upper())
    return out


def proposed_binance_pair(symbol: str) -> str | None:
    sym = (symbol or "").strip().lower()
    if not sym or sym in SKIP_SYMBOLS:
        return None
    return f"{sym.upper()}USDT"


def build_registry_seed(
    coins: list[dict],
    binance_pairs: set[str],
    *,
    include_metals: bool = True,
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """
    Return (rows, skipped_notes).
    rows: (cg_id, symbol, binance_symbol)
    """
    rows: list[tuple[str, str, str]] = []
    skipped: list[str] = []
    used_pairs: set[str] = set()

    if include_metals:
        rows.extend(METALS)

    for coin in coins:
        cg_id = (coin.get("id") or "").strip().lower()
        symbol = (coin.get("symbol") or "").strip().lower()
        rank = coin.get("market_cap_rank")
        if not cg_id or not symbol:
            skipped.append(f"rank {rank}: missing id/symbol")
            continue

        pair = proposed_binance_pair(symbol)
        if pair is None:
            skipped.append(f"{cg_id} ({symbol}): skipped symbol")
            continue
        if pair not in binance_pairs:
            skipped.append(f"{cg_id} ({symbol}): no Binance pair {pair}")
            continue
        if pair in used_pairs:
            skipped.append(f"{cg_id} ({symbol}): pair {pair} already assigned")
            continue

        rows.append((cg_id, symbol, pair))
        used_pairs.add(pair)

    return rows, skipped
