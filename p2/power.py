"""Exact power and precision for P2's two-cell comparisons (spec section 0).

  .venv/bin/python p2/power.py

Power is for a two-sided Fisher exact test at alpha = 0.025 (Holm's first step over
E1 and E2), which is conservative: the analysis uses Boschloo's test, which is at
least as powerful. Precision is the expected 95% Newcombe half-width when both cells
share the same true rate. Results are symmetric: a base rate p behaves like 1 - p.
"""
from __future__ import annotations

from functools import lru_cache
from math import comb, sqrt

Z = 1.959964
N = 120         # episodes per cell
ALPHA = 0.025   # Holm's first step
NEGLIGIBLE = 1e-12


def wilson(x: int, n: int) -> tuple[float, float]:
    p, d = x / n, 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / d
    half = Z * sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return centre - half, centre + half


def newcombe(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    """95% CI for p1 - p2 (Newcombe's hybrid score method)."""
    p1, p2 = x1 / n1, x2 / n2
    (l1, u1), (l2, u2) = wilson(x1, n1), wilson(x2, n2)
    d = p1 - p2
    return d - sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def _pmf(n: int, p: float) -> list[float]:
    return [comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]


@lru_cache(maxsize=None)
def _rejected(n1: int, n2: int, m: int) -> frozenset[int]:
    """Counts a in cell 1 (given m events overall) where the two-sided Fisher p < ALPHA."""
    lo, hi = max(0, m - n2), min(n1, m)
    prob = {a: comb(n1, a) * comb(n2, m - a) / comb(n1 + n2, m) for a in range(lo, hi + 1)}
    ordered = sorted(prob.values())
    out = set()
    for a, q in prob.items():
        p_value = sum(v for v in ordered if v <= q * (1 + 1e-9))
        if p_value < ALPHA:
            out.add(a)
    return frozenset(out)


def power(p1: float, p2: float, n1: int = N, n2: int = N) -> float:
    f1, f2 = _pmf(n1, p1), _pmf(n2, p2)
    return sum(f1[x] * f2[y] for x in range(n1 + 1) for y in range(n2 + 1)
               if f1[x] * f2[y] > NEGLIGIBLE and x in _rejected(n1, n2, x + y))


def null_halfwidth(p: float, n1: int = N, n2: int = N) -> float:
    f1, f2 = _pmf(n1, p), _pmf(n2, p)
    total = 0.0
    for x in range(n1 + 1):
        for y in range(n2 + 1):
            if f1[x] * f2[y] > NEGLIGIBLE:
                lo, hi = newcombe(x, n1, y, n2)
                total += f1[x] * f2[y] * (hi - lo) / 2
    return total


def mde(base: float, target: float = 0.80) -> float:
    """Smallest increase over base, in 1 pp steps, detected with at least `target` power."""
    for step in range(1, 100):
        if base + step / 100 < 1 and power(base + step / 100, base) >= target:
            return step / 100
    return float("nan")


def main() -> None:
    print(f"n = {N} per cell, two-sided Fisher exact test at alpha = {ALPHA}")
    print(f"{'base rate':>9}  {'power, +10 pp':>13}  {'80% MDE':>7}  {'null CI half-width':>18}")
    for base in (0.01, 0.05, 0.10, 0.20, 0.30, 0.50):
        print(f"{base:9.0%}  {power(base + 0.10, base):13.2f}  {mde(base):6.0%}   "
              f"{null_halfwidth(base) * 100:>14.1f} pp")
    print(f"upper 95% bound for 0/{N}: {wilson(0, N)[1]:.1%}")


if __name__ == "__main__":
    main()
