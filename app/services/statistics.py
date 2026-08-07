"""Pure stats on aligned daily close series."""

from __future__ import annotations

import math
from statistics import mean, pstdev

MIN_OBSERVATIONS = 20


def log_returns(closes: list[float]) -> list[float]:
    if len(closes) < 2:
        return []
    out: list[float] = []
    for i in range(1, len(closes)):
        if closes[i - 1] <= 0 or closes[i] <= 0:
            continue
        out.append(math.log(closes[i] / closes[i - 1]))
    return out


def summary_stats(returns: list[float]) -> dict:
    if not returns:
        return {"mean_return": None, "std_return": None}
    return {
        "mean_return": mean(returns),
        "std_return": pstdev(returns) if len(returns) > 1 else 0.0,
    }


def cumulative_return(closes: list[float]) -> float | None:
    if len(closes) < 2 or closes[0] <= 0:
        return None
    return (closes[-1] / closes[0]) - 1.0


def max_drawdown(closes: list[float]) -> float | None:
    if not closes:
        return None
    peak = closes[0]
    worst = 0.0
    for price in closes:
        peak = max(peak, price)
        if peak > 0:
            worst = min(worst, (price / peak) - 1.0)
    return worst


def align_series(
    dates_a: list[str],
    closes_a: list[float],
    dates_b: list[str],
    closes_b: list[float],
) -> tuple[list[str], list[float], list[float]]:
    map_b = dict(zip(dates_b, closes_b, strict=False))
    out_dates: list[str] = []
    out_a: list[float] = []
    out_b: list[float] = []
    for d, ca in zip(dates_a, closes_a, strict=False):
        cb = map_b.get(d)
        if cb is not None:
            out_dates.append(d)
            out_a.append(ca)
            out_b.append(cb)
    return out_dates, out_a, out_b


def correlation(r_a: list[float], r_b: list[float]) -> float | None:
    n = min(len(r_a), len(r_b))
    if n < 2:
        return None
    ra, rb = r_a[:n], r_b[:n]
    ma, mb = mean(ra), mean(rb)
    num = sum((a - ma) * (b - mb) for a, b in zip(ra, rb, strict=False))
    den_a = math.sqrt(sum((a - ma) ** 2 for a in ra))
    den_b = math.sqrt(sum((b - mb) ** 2 for b in rb))
    if den_a == 0 or den_b == 0:
        return None
    return num / (den_a * den_b)


def ols_beta(r_subject: list[float], r_baseline: list[float]) -> dict:
    n = min(len(r_subject), len(r_baseline))
    if n < 2:
        return {"beta": None, "alpha": None, "r_squared": None, "residual_std": None}
    rs, rb = r_subject[:n], r_baseline[:n]
    mb = mean(rb)
    var_b = sum((b - mb) ** 2 for b in rb)
    if var_b == 0:
        return {"beta": None, "alpha": None, "r_squared": None, "residual_std": None}
    ms = mean(rs)
    cov = sum((s - ms) * (b - mb) for s, b in zip(rs, rb, strict=False)) / n
    beta = cov / (var_b / n)
    alpha = ms - beta * mb
    residuals = [s - (alpha + beta * b) for s, b in zip(rs, rb, strict=False)]
    res_std = pstdev(residuals) if len(residuals) > 1 else 0.0
    corr = correlation(rs, rb)
    r_sq = (corr * corr) if corr is not None else None
    return {
        "beta": beta,
        "alpha": alpha,
        "r_squared": r_sq,
        "residual_std": res_std,
    }


def tracking_error(r_subject: list[float], r_baseline: list[float]) -> float | None:
    n = min(len(r_subject), len(r_baseline))
    if n < 2:
        return None
    diffs = [r_subject[i] - r_baseline[i] for i in range(n)]
    return pstdev(diffs)


def cum_relative_return(closes_a: list[float], closes_b: list[float]) -> float | None:
    cum_a = cumulative_return(closes_a)
    cum_b = cumulative_return(closes_b)
    if cum_a is None or cum_b is None:
        return None
    return (1.0 + cum_a) / (1.0 + cum_b) - 1.0