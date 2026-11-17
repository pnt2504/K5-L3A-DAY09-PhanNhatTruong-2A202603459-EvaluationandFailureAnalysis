"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb, isfinite
from numbers import Integral

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge must contain the same number of labels")
    if len(human) == 0:
        raise ValueError("calibration requires at least one labelled example")
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for actual, predicted in zip(human, judge, strict=True):
        if actual not in ("PASS", "FAIL") or predicted not in ("PASS", "FAIL"):
            raise ValueError("labels must be PASS or FAIL")
        if actual == POS:
            counts["tp" if predicted == POS else "fn"] += 1
        else:
            counts["fp" if predicted == POS else "tn"] += 1
    return counts


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    counts = confusion(human, judge)
    predicted_fail = counts["tp"] + counts["fp"]
    actual_fail = counts["tp"] + counts["fn"]
    precision = counts["tp"] / predicted_fail if predicted_fail else 0.0
    recall = counts["tp"] / actual_fail if actual_fail else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    counts = confusion(human, judge)
    tp, fp, fn, tn = (counts[key] for key in ("tp", "fp", "fn", "tn"))
    n = tp + fp + fn + tn
    # Multiply (p_o - p_e)/(1 - p_e) by n**2 to avoid cancellation near p_e=1.
    chance_agreement = (tp + fn) * (tp + fp) + (tn + fp) * (tn + fn)
    denominator = n * n - chance_agreement
    if denominator == 0:
        raise ValueError("Cohen kappa is undefined when expected agreement is 1")
    return (n * (tp + tn) - chance_agreement) / denominator


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    if any(not isfinite(value) or not 0.0 <= value <= 1.0
           for value in (observed_rate, sensitivity, specificity)):
        raise ValueError("rates must be finite probabilities in [0, 1]")
    denominator = sensitivity + specificity - 1.0
    if denominator == 0.0:
        raise ValueError("Rogan-Gladen is undefined when sensitivity + specificity is 1")
    corrected = (observed_rate + specificity - 1.0) / denominator
    return max(0.0, min(1.0, corrected))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    left, right = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if left.ndim != 1 or right.ndim != 1 or left.size == 0 or left.shape != right.shape:
        raise ValueError("bootstrap needs equally sized, non-empty one-dimensional paired samples")
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError("bootstrap samples must be finite")
    if not isinstance(n_resamples, Integral) or isinstance(n_resamples, bool) or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    difference = left - right
    delta = float(difference.mean())
    if np.array_equal(left, right):
        return 0.0, 0.0, 0.0
    if left.size == 1:
        return delta, delta, delta
    result = bootstrap((left, right), lambda x, y, axis: np.mean(x - y, axis=axis),
                       paired=True, vectorized=True, method="percentile", n_resamples=int(n_resamples),
                       confidence_level=confidence, rng=np.random.default_rng(rng))
    return delta, float(result.confidence_interval.low), float(result.confidence_interval.high)


def _validate_pass_k(n: int, c: int, k: int) -> None:
    if any(not isinstance(value, Integral) or isinstance(value, bool) for value in (n, c, k)):
        raise ValueError("n, c and k must be integers")
    if n < 1 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("require n >= 1, 0 <= c <= n, and 1 <= k <= n")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_pass_k(n, c, k)
    return 1.0 if n - c < k else 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_pass_k(n, c, k)
    return 0.0 if c < k else comb(c, k) / comb(n, k)
