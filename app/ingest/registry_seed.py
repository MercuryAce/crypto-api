"""Build asset_registry rows from CoinGecko top market cap + Binance USDT pairs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINGECKO_TICKERS_URL = "https://api.coingecko.com/api/v3/coins/{cg_id}/tickers"
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
        "usds",
        "usdt0",
    }
)

# CoinGecko cg_id -> Binance USDT pair when ticker symbol != Binance base asset.
MANUAL_OVERRIDES: dict[str, str] = {
    "polygon-ecosystem-token": "POLUSDT",
    "matic-network": "POLUSDT",
}

# cg_id values confirmed not listed on Binance spot USDT (skip with reason not_on_binance).
NOT_ON_BINANCE: frozenset[str] = frozenset(
    {
        "leo-token",
        "okb",
        "figure-heloc",
        "usd1-wlfi",
        "hyperliquid",
        "bittensor",
    }
)


@dataclass
class SkippedCoin:
    rank: int | None
    cg_id: str
    name: str
    symbol: str
    reason: str
    tried_pair: str | None = None
    suggestions: list[str] = field(default_factory=list)
    coingecko_binance: str | None = None


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


def fetch_binance_usdt_index(*, timeout: float = 30.0) -> tuple[set[str], dict[str, str]]:
    """
    Return (pair_symbols, base_asset_to_pair).
    base_asset_to_pair maps upper base asset, e.g. XRP -> XRPUSDT.
    """
    response = httpx.get(BINANCE_EXCHANGE_INFO_URL, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    symbols = payload.get("symbols") or []
    pairs: set[str] = set()
    by_base: dict[str, str] = {}
    for row in symbols:
        if row.get("status") != "TRADING":
            continue
        if row.get("quoteAsset") != "USDT":
            continue
        if row.get("isSpotTradingAllowed") is False:
            continue
        sym = str(row.get("symbol") or "").upper()
        base = str(row.get("baseAsset") or "").upper()
        if not sym:
            continue
        pairs.add(sym)
        by_base[base] = sym
    return pairs, by_base


def fetch_binance_usdt_pairs(*, timeout: float = 30.0) -> set[str]:
    pairs, _ = fetch_binance_usdt_index(timeout=timeout)
    return pairs


def load_overrides(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("overrides file must be a JSON object {cg_id: PAIR}")
    out: dict[str, str] = {}
    for key, value in payload.items():
        if value is None:
            continue
        cg_id = str(key).strip().lower()
        pair = str(value).strip().upper()
        if cg_id and pair:
            out[cg_id] = pair
    return out


def proposed_binance_pair(symbol: str) -> str | None:
    sym = (symbol or "").strip().lower()
    if not sym or sym in SKIP_SYMBOLS:
        return None
    return f"{sym.upper()}USDT"


def suggest_binance_pairs(
    symbol: str,
    *,
    binance_pairs: set[str],
    binance_by_base: dict[str, str],
    limit: int = 8,
) -> list[str]:
    sym = (symbol or "").strip().upper()
    if not sym:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    def add(pair: str | None) -> None:
        if not pair or pair in seen:
            return
        if pair not in binance_pairs:
            return
        seen.add(pair)
        candidates.append(pair)

    add(binance_by_base.get(sym))
    add(f"{sym}USDT")

    for base, pair in binance_by_base.items():
        if base == sym or base.endswith(sym) or sym in base:
            add(pair)

    # Binance often prefixes micro-cap units: 1000PEPE, 1MBABYDOGE, etc.
    for pair in sorted(binance_pairs):
        base = pair[:-4] if pair.endswith("USDT") else pair
        if sym in base or base.endswith(sym):
            add(pair)
        if len(candidates) >= limit:
            break

    return candidates[:limit]


def fetch_coingecko_binance_pair(cg_id: str, *, timeout: float = 20.0) -> str | None:
    """Best-effort Binance USDT pair from CoinGecko exchange tickers."""
    response = httpx.get(
        COINGECKO_TICKERS_URL.format(cg_id=cg_id),
        params={"exchange_ids": "binance", "include_exchange_logo": "false"},
        timeout=timeout,
        headers={"accept": "application/json"},
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    payload = response.json()
    tickers = payload.get("tickers") or []
    for row in tickers:
        market = row.get("market") or {}
        if str(market.get("identifier") or "").lower() != "binance":
            continue
        target = str(row.get("target") or "").upper()
        if target not in {"USDT", "USD"}:
            continue
        base = str(row.get("base") or "").upper()
        if target == "USDT" and base:
            return f"{base}USDT"
        if target == "USD" and base:
            return f"{base}USDT"  # CG sometimes labels USD; Binance spot uses USDT
    return None


def enrich_skipped_suggestions(
    skipped: list[SkippedCoin],
    *,
    binance_pairs: set[str],
    binance_by_base: dict[str, str],
    fetch_cg_tickers: bool = False,
) -> None:
    for item in skipped:
        if item.reason in {"stable_or_quote", "not_on_binance"}:
            continue
        override = MANUAL_OVERRIDES.get(item.cg_id)
        if override:
            item.suggestions = [override]
            continue
        item.suggestions = suggest_binance_pairs(
            item.symbol,
            binance_pairs=binance_pairs,
            binance_by_base=binance_by_base,
        )
        if fetch_cg_tickers and not item.suggestions:
            cg_pair = fetch_coingecko_binance_pair(item.cg_id)
            item.coingecko_binance = cg_pair
            if cg_pair and cg_pair in binance_pairs and cg_pair not in item.suggestions:
                item.suggestions.insert(0, cg_pair)


def build_registry_seed(
    coins: list[dict],
    binance_pairs: set[str],
    *,
    binance_by_base: dict[str, str] | None = None,
    include_metals: bool = True,
    overrides: dict[str, str] | None = None,
) -> tuple[list[tuple[str, str, str]], list[SkippedCoin]]:
    """
    Return (rows, skipped).
    rows: (cg_id, symbol, binance_symbol)
    """
    rows: list[tuple[str, str, str]] = []
    skipped: list[SkippedCoin] = []
    used_pairs: set[str] = set()
    overrides = overrides or {}
    by_base = binance_by_base or {}

    if include_metals:
        for cg_id, symbol, pair in METALS:
            rows.append((cg_id, symbol, pair))
            used_pairs.add(pair)

    for coin in coins:
        cg_id = (coin.get("id") or "").strip().lower()
        symbol = (coin.get("symbol") or "").strip().lower()
        name = (coin.get("name") or "").strip()
        rank = coin.get("market_cap_rank")
        if not cg_id or not symbol:
            skipped.append(
                SkippedCoin(
                    rank=rank,
                    cg_id=cg_id or "?",
                    name=name,
                    symbol=symbol or "?",
                    reason="missing_id_or_symbol",
                )
            )
            continue

        if cg_id in NOT_ON_BINANCE:
            skipped.append(
                SkippedCoin(
                    rank=rank,
                    cg_id=cg_id,
                    name=name,
                    symbol=symbol,
                    reason="not_on_binance",
                    tried_pair=proposed_binance_pair(symbol),
                )
            )
            continue

        pair = overrides.get(cg_id) or MANUAL_OVERRIDES.get(cg_id) or proposed_binance_pair(symbol)
        tried = proposed_binance_pair(symbol)

        if pair is None:
            skipped.append(
                SkippedCoin(
                    rank=rank,
                    cg_id=cg_id,
                    name=name,
                    symbol=symbol,
                    reason="stable_or_quote",
                    tried_pair=tried,
                )
            )
            continue

        pair = str(pair).upper()
        if pair not in binance_pairs:
            skipped.append(
                SkippedCoin(
                    rank=rank,
                    cg_id=cg_id,
                    name=name,
                    symbol=symbol,
                    reason="no_binance_pair",
                    tried_pair=tried or pair,
                )
            )
            continue
        if pair in used_pairs:
            skipped.append(
                SkippedCoin(
                    rank=rank,
                    cg_id=cg_id,
                    name=name,
                    symbol=symbol,
                    reason="duplicate_pair",
                    tried_pair=pair,
                )
            )
            continue

        rows.append((cg_id, symbol, pair))
        used_pairs.add(pair)

    enrich_skipped_suggestions(
        skipped,
        binance_pairs=binance_pairs,
        binance_by_base=by_base,
    )
    return rows, skipped


def format_skipped_report(skipped: list[SkippedCoin]) -> str:
    lines = [
        f"{'rank':>4}  {'cg_id':28}  {'sym':8}  {'reason':16}  tried / suggestions",
        "-" * 100,
    ]
    for item in skipped:
        sugg = ", ".join(item.suggestions[:5]) if item.suggestions else "-"
        if item.coingecko_binance and item.coingecko_binance not in item.suggestions:
            sugg = f"CG:{item.coingecko_binance}; {sugg}"
        tried = item.tried_pair or "-"
        lines.append(
            f"{item.rank or '':>4}  {item.cg_id:28}  {item.symbol:8}  {item.reason:16}  {tried} -> {sugg}"
        )
    return "\n".join(lines)


def write_skipped_json(path: Path, skipped: list[SkippedCoin]) -> None:
    payload = {
        "skipped": [asdict(item) for item in skipped],
        "override_template": {
            item.cg_id: (item.suggestions[0] if item.suggestions else "")
            for item in skipped
            if item.reason != "stable_or_quote"
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
