"""Unit tests for inferential statistics helpers."""

import math
import random

from app.services import statistics as stats


def _paired_returns(n: int = 30, rho: float = 0.5):
    """Synthetic correlated return series."""
    random.seed(42)
    r_b = [random.gauss(0, 0.02) for _ in range(n)]
    r_a = [rho * b + math.sqrt(1 - rho * rho) * random.gauss(0, 0.02) for b in r_b]
    return r_a, r_b


def test_inferential_summary_keys():
    r_a, r_b = _paired_returns(40, 0.6)
    out = stats.inferential_summary(r_a, r_b)
    assert out["alpha"] == 0.95
    assert out["tails"] == "two"
    assert out["correlation_p_value"] is not None
    assert out["beta_p_value"] is not None
    assert out["correlation_ci_95"] is not None
    assert len(out["correlation_ci_95"]) == 2
    assert out["regime_chi2"]["chi2"] is not None


def test_uncorrelated_series_high_pvalues():
    # Seed 7 yields a spurious ~0.04 correlation p-value at n=50; use a
    # clearly null draw so the test is deterministic, not Type-I flaky.
    random.seed(0)
    r_a = [random.gauss(0, 0.02) for _ in range(50)]
    r_b = [random.gauss(0, 0.02) for _ in range(50)]
    out = stats.inferential_summary(r_a, r_b)
    assert out["correlation_p_value"] > 0.05
    assert out["beta_p_value"] > 0.05


def test_perfect_correlation_significant():
    r_b = [0.01, -0.02, 0.015, -0.005, 0.02] * 6
    r_a = list(r_b)
    out = stats.inferential_summary(r_a, r_b)
    assert out["correlation_p_value"] is not None
    assert out["correlation_p_value"] < 0.05
    assert out["beta_p_value"] is not None
    assert out["beta_p_value"] < 0.05


def test_regime_chi_square_independence():
    r_a = [0.01, -0.01, 0.02, -0.02] * 10
    r_b = [-0.01, 0.01, -0.02, 0.02] * 10
    regime = stats.regime_chi_square(r_a, r_b)
    assert regime["chi2"] is not None
    assert regime["df"] == 1
    assert regime["p_value"] is not None


def test_insufficient_data_returns_none():
    out = stats.inferential_summary([0.01], [0.02])
    assert out["correlation_p_value"] is None
    assert out["beta_p_value"] is None
