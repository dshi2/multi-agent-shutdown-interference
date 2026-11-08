"""Calibration and power of candidate tests for the E2-GLM recipient comparison
(P2_E2gen_spec.md): H0: (REQ - INFO) for GLM equals (REQ - INFO) for Sonnet.
Two-sided, alpha = 0.05: a single secondary test outside the core's Holm family.

  p2_harness/.venv/bin/python tools/ext_calibration.py

Candidates, all computed on the same simulated data:
  wald      Wald z on the difference of differences, unpooled variances
  wald_adj  the same with (x + 0.5) / (n + 1) in every arm
  mover     MOVER interval (Zou & Donner 2008) from four 95% Wilson intervals;
            reject when it excludes 0

Choice rule, fixed before looking at the results: keep the tests whose worst-case
size over the null grid is not significantly above 0.05 (the lower end of the worst
scenario's 95% Monte Carlo interval stays at or below 0.05, after a 200,000-run rerun
of each test's five worst scenarios). Among those, take the one with the highest mean
power over the planning scenarios. "Less conservative" alone is no reason to prefer
a test.
"""
from __future__ import annotations

import random
from math import sqrt

Z = 1.959964
GRID_SIMS, WORST_SIMS = 20000, 200000
N_GLM = 240
TESTS = ("wald", "wald_adj", "mover")


def wilson(x: int, n: int) -> tuple[float, float]:
    p, d = x / n, 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return c - h, c + h


def rejects(xs: list[int], ns: list[int]) -> dict[str, bool]:
    """xs, ns: Sonnet INFO, Sonnet REQ, GLM INFO, GLM REQ."""
    out = {}
    p = [x / n for x, n in zip(xs, ns)]
    did = (p[3] - p[2]) - (p[1] - p[0])
    var = sum(q * (1 - q) / n for q, n in zip(p, ns))
    out["wald"] = var > 0 and abs(did) / sqrt(var) > Z
    pa = [(x + 0.5) / (n + 1) for x, n in zip(xs, ns)]
    da = (pa[3] - pa[2]) - (pa[1] - pa[0])
    va = sum(q * (1 - q) / (n + 1) for q, n in zip(pa, ns))
    out["wald_adj"] = va > 0 and abs(da) / sqrt(va) > Z
    ci = [wilson(x, n) for x, n in zip(xs, ns)]
    sign = (1, -1, -1, 1)  # did = +p0 - p1 - p2 + p3
    lo = did - sqrt(sum((p[i] - ci[i][0]) ** 2 if sign[i] > 0 else (ci[i][1] - p[i]) ** 2 for i in range(4)))
    hi = did + sqrt(sum((ci[i][1] - p[i]) ** 2 if sign[i] > 0 else (p[i] - ci[i][0]) ** 2 for i in range(4)))
    out["mover"] = lo > 0 or hi < 0
    return out


def rates(scn: tuple, sims: int, rng: random.Random) -> dict[str, float]:
    s0, s1, n_s, g0, g1 = scn
    ns = [n_s, n_s, N_GLM, N_GLM]
    hits = dict.fromkeys(TESTS, 0)
    for _ in range(sims):
        xs = [rng.binomialvariate(n, q) for n, q in zip(ns, (s0, s1, g0, g1))]
        for k, v in rejects(xs, ns).items():
            hits[k] += v
    return {k: v / sims for k, v in hits.items()}


def mc(p: float, sims: int) -> tuple[float, float]:
    h = Z * sqrt(p * (1 - p) / sims)
    return p - h, p + h


def label(scn: tuple) -> str:
    s0, s1, n_s, g0, g1 = scn
    return (f"Sonnet INFO {s0:.0%} REQ {s1:.0%} (n {n_s}); GLM INFO {g0:.0%} REQ {g1:.0%} (n {N_GLM})")


def main() -> None:
    rng = random.Random(20261109)
    nulls = [(s0, s0 + e, n_s, g0, g0 + e) for s0 in (0.01, 0.02, 0.05, 0.10, 0.20)
             for g0 in (0.01, 0.05, 0.10, 0.30) for e in (0.0, 0.10) for n_s in (120, 240, 500)]
    grid = {scn: rates(scn, GRID_SIMS, rng) for scn in nulls}
    print(f"Null grid: {len(nulls)} scenarios x {GRID_SIMS} runs; 95% Monte Carlo half-width at 0.05 "
          f"is {Z * sqrt(0.05 * 0.95 / GRID_SIMS):.4f}")
    keep = []
    for t in TESTS:
        ranked = sorted(nulls, key=lambda s: -grid[s][t])
        print(f"\n{t}: size over the grid {min(grid[s][t] for s in nulls):.4f} to {grid[ranked[0]][t]:.4f}")
        worst_lo = 0.0
        for scn in ranked[:5]:
            r = rates(scn, WORST_SIMS, rng)[t]
            lo, hi = mc(r, WORST_SIMS)
            worst_lo = max(worst_lo, lo)
            print(f"  worst-5 rerun ({WORST_SIMS} runs): {r:.4f} [{lo:.4f}, {hi:.4f}]  {label(scn)}")
        ok = worst_lo <= 0.05
        print(f"  size controlled (worst lower MC bound <= 0.05): {'yes' if ok else 'NO'}")
        if ok:
            keep.append(t)

    planning = [(0.05, 0.05, n_s, 0.10, 0.10 + d) for d in (0.10, 0.15, 0.20) for n_s in (120, 240, 500)]
    planning += [(0.05, 0.15, n_s, 0.10, 0.20 + d) for d in (0.10, 0.15, 0.20) for n_s in (120, 240, 500)]
    power = {scn: rates(scn, GRID_SIMS, rng) for scn in planning}
    print("\nPower (difference of effects d), Sonnet n = 120 / 240 / 500, GLM n = 240")
    for t in TESTS:
        print(f"  {t}:")
        for base, sname in ((0.05, "Sonnet effect 0"), (0.15, "Sonnet effect 10 pp")):
            for d in (0.10, 0.15, 0.20):
                row = [power[(0.05, base, n_s, 0.10, (0.10 if base == 0.05 else 0.20) + d)][t]
                       for n_s in (120, 240, 500)]
                print(f"    {sname}, d = {d:.0%}: " + " / ".join(f"{x:.2f}" for x in row))
    mean_power = {t: sum(power[s][t] for s in planning) / len(planning) for t in TESTS}
    print("\nMean power over the planning scenarios:", {t: round(v, 3) for t, v in mean_power.items()})
    choice = max(keep, key=mean_power.get) if keep else "mover"
    print(f"Size-controlled tests: {keep or 'none'}; chosen by the rule: {choice}")


if __name__ == "__main__":
    main()
