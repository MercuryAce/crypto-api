"""Pure stats on aligned daily close series."""

from __future__ import annotations

import math
from statistics import mean, pstdev, stdev

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


def _align_returns(r_a: list[float], r_b: list[float]) -> tuple[list[float], list[float], int]:
    n = min(len(r_a), len(r_b))
    if n < 2:
        return [], [], 0
    return r_a[:n], r_b[:n], n


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1.0 - x) - ln_beta) / a

    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    f = d

    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((a + m2 - 1) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        f *= d * c
        aa = -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        f *= delta
        if abs(delta - 1.0) < 1e-10:
            break

    return front * f


def _student_t_cdf(t: float, df: int) -> float:
    if df <= 0:
        return 0.5
    x = df / (df + t * t)
    ib = _regularized_incomplete_beta(df / 2.0, 0.5, x)
    if t >= 0:
        return 1.0 - 0.5 * ib
    return 0.5 * ib


def _student_t_pvalue_two_tailed(t_stat: float, df: int) -> float | None:
    if df < 1:
        return None
    return max(0.0, min(1.0, 2.0 * (1.0 - _student_t_cdf(abs(t_stat), df))))


def _student_t_critical(alpha: float, df: int) -> float | None:
    if df < 1:
        return None
    target = 1.0 - (1.0 - alpha) / 2.0
    lo, hi = 0.0, 10.0
    while _student_t_cdf(hi, df) < target:
        hi *= 2.0
        if hi > 1e6:
            return None
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if _student_t_cdf(mid, df) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _normal_cdf_inv(p: float) -> float:
    p = max(1e-12, min(1.0 - 1e-12, p))
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285084469e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447143061497942e01,
        1.615858368580409e02,
        -1.556989844598459e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964792424684e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709091636e-03,
        3.224671290700398e-01,
        2.445875785344406e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    if p > 1.0 - plow:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )


def _chi2_pvalue(chi2: float, df: int) -> float | None:
    if df < 1 or chi2 < 0:
        return None
    if df == 1:
        return max(0.0, min(1.0, 2.0 * (1.0 - _normal_cdf(math.sqrt(chi2)))))
    x = chi2 / 2.0
    return max(0.0, min(1.0, 1.0 - _regularized_incomplete_beta(df / 2.0, 0.5, x)))


def _f_pvalue(f_stat: float, df1: int, df2: int) -> float | None:
    if f_stat < 0 or df1 < 1 or df2 < 1:
        return None
    x = (df1 * f_stat) / (df1 * f_stat + df2)
    return max(0.0, min(1.0, 1.0 - _regularized_incomplete_beta(df1 / 2.0, df2 / 2.0, x)))


def correlation_inference(
    r_a: list[float],
    r_b: list[float],
    *,
    alpha: float = 0.95,
) -> dict:
    rs, rb, n = _align_returns(r_a, r_b)
    if n < 3:
        return {"p_value": None, "ci": None}
    r = correlation(rs, rb)
    if r is None:
        return {"p_value": None, "ci": None}
    df = n - 2
    denom = max(1e-15, 1.0 - r * r)
    t_stat = r * math.sqrt(df / denom)
    p_value = _student_t_pvalue_two_tailed(t_stat, df)
    if abs(r) >= 1.0:
        ci = (-1.0, 1.0)
    elif n <= 3:
        ci = None
    else:
        z = 0.5 * math.log((1.0 + r) / (1.0 - r))
        se = 1.0 / math.sqrt(n - 3)
        z_crit = _normal_cdf_inv(1.0 - (1.0 - alpha) / 2.0)
        ci = (math.tanh(z - z_crit * se), math.tanh(z + z_crit * se))
    return {"p_value": p_value, "ci": ci}


def beta_inference(
    r_a: list[float],
    r_b: list[float],
    *,
    alpha: float = 0.95,
) -> dict:
    rs, rb, n = _align_returns(r_a, r_b)
    if n < 3:
        return {"p_value": None, "ci": None}
    rel = ols_beta(rs, rb)
    beta = rel["beta"]
    alpha_intercept = rel["alpha"]
    if beta is None or alpha_intercept is None:
        return {"p_value": None, "ci": None}
    mb = mean(rb)
    ss_b = sum((b - mb) ** 2 for b in rb)
    if ss_b == 0:
        return {"p_value": None, "ci": None}
    residuals = [s - (alpha_intercept + beta * b) for s, b in zip(rs, rb, strict=False)]
    if len(residuals) < 2:
        return {"p_value": None, "ci": None}
    res_std = stdev(residuals)
    se_beta = res_std / math.sqrt(ss_b)
    # Perfect OLS fit → SE(beta)=0; treat nonzero beta as infinitely significant.
    if se_beta == 0:
        if beta == 0:
            return {"p_value": None, "ci": None}
        return {"p_value": 0.0, "ci": (beta, beta)}
    df = n - 2
    t_stat = beta / se_beta
    p_value = _student_t_pvalue_two_tailed(t_stat, df)
    t_crit = _student_t_critical(alpha, df)
    if t_crit is None:
        return {"p_value": p_value, "ci": None}
    return {"p_value": p_value, "ci": (beta - t_crit * se_beta, beta + t_crit * se_beta)}


def regression_f_test(r_a: list[float], r_b: list[float]) -> dict:
    rs, rb, n = _align_returns(r_a, r_b)
    if n < 3:
        return {"f_stat": None, "p_value": None}
    rel = ols_beta(rs, rb)
    r_sq = rel["r_squared"]
    if r_sq is None:
        return {"f_stat": None, "p_value": None}
    df2 = n - 2
    if df2 < 1 or r_sq >= 1.0:
        return {"f_stat": None, "p_value": None}
    f_stat = (r_sq / max(1e-15, 1.0 - r_sq)) * df2
    return {"f_stat": f_stat, "p_value": _f_pvalue(f_stat, 1, df2)}


def regime_chi_square(r_a: list[float], r_b: list[float]) -> dict:
    rs, rb, n = _align_returns(r_a, r_b)
    if n < 4:
        return {"chi2": None, "df": None, "p_value": None}
    a = b = c = d = 0
    for sa, sb in zip(rs, rb, strict=False):
        if sa >= 0 and sb >= 0:
            a += 1
        elif sa >= 0:
            b += 1
        elif sb >= 0:
            c += 1
        else:
            d += 1
    row1 = a + b
    row2 = c + d
    col1 = a + c
    col2 = b + d
    denom = row1 * row2 * col1 * col2
    if denom == 0:
        return {"chi2": None, "df": None, "p_value": None}
    chi2 = n * (a * d - b * c) ** 2 / denom
    return {"chi2": chi2, "df": 1, "p_value": _chi2_pvalue(chi2, 1)}


def variance_ratio_f_test(r_a: list[float], r_b: list[float]) -> dict:
    rs, rb, n = _align_returns(r_a, r_b)
    if n < 3:
        return {"f_stat": None, "p_value": None}
    var_a = stdev(rs) ** 2
    var_b = stdev(rb) ** 2
    if var_b == 0:
        return {"f_stat": None, "p_value": None}
    f_stat = var_a / var_b
    df1 = df2 = n - 1
    return {"f_stat": f_stat, "p_value": _f_pvalue(f_stat, df1, df2)}


def inferential_summary(
    r_a: list[float],
    r_b: list[float],
    *,
    alpha: float = 0.95,
) -> dict:
    corr_inf = correlation_inference(r_a, r_b, alpha=alpha)
    beta_inf = beta_inference(r_a, r_b, alpha=alpha)
    f_test = regression_f_test(r_a, r_b)
    regime = regime_chi_square(r_a, r_b)
    var_f = variance_ratio_f_test(r_a, r_b)
    corr_ci = corr_inf.get("ci")
    beta_ci = beta_inf.get("ci")
    return {
        "alpha": alpha,
        "tails": "two",
        "correlation_p_value": corr_inf.get("p_value"),
        "correlation_ci_95": list(corr_ci) if corr_ci else None,
        "beta_p_value": beta_inf.get("p_value"),
        "beta_ci_95": list(beta_ci) if beta_ci else None,
        "regression_f_stat": f_test.get("f_stat"),
        "regression_f_p_value": f_test.get("p_value"),
        "regime_chi2": {
            "chi2": regime.get("chi2"),
            "df": regime.get("df"),
            "p_value": regime.get("p_value"),
        },
        "variance_ratio_f": {
            "f_stat": var_f.get("f_stat"),
            "p_value": var_f.get("p_value"),
        },
    }