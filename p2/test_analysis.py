"""Tests for p2/analysis.py on synthetic episodes with known truths.

  .venv/bin/python p2/test_analysis.py      -> ANALYSIS TEST PASSED

Covers: published Wilson and Newcombe values; Holm; the Mantel-Haenszel risk
difference; null CI coverage; recovery of a +15 pp effect; a message-clustered
effect with ICC 0.2 (ICC recovery and bootstrap coverage); pending-episode
codings that flip a conclusion; invalid baselines; adjudication rules; refused
inputs; the provider gate; attempt accounting; and the CLI outputs.
"""
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis as A  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


CELLS = {  # cell -> fixed columns
    "e1_RxR": dict(experiment="1", a_type="R", b_type="R", arm="live", rule="0"),
    "e1_RxC": dict(experiment="1", a_type="R", b_type="C", arm="live", rule="0"),
    "e1_CxR": dict(experiment="1", a_type="C", b_type="R", arm="live", rule="0"),
    "e1_CxC": dict(experiment="1", a_type="C", b_type="C", arm="live", rule="0"),
    "e2_REQ_plain_r0": dict(experiment="2", a_type="scripted", b_type="C", arm="REQ_plain", rule="0"),
    "e2_INFO_r0": dict(experiment="2", a_type="scripted", b_type="C", arm="INFO", rule="0"),
    "e2_CONTACT_r0": dict(experiment="2", a_type="scripted", b_type="C", arm="CONTACT", rule="0"),
    "e2_REQ_plain_r1": dict(experiment="2", a_type="scripted", b_type="C", arm="REQ_plain", rule="1"),
    "e2_INFO_r1": dict(experiment="2", a_type="scripted", b_type="C", arm="INFO", rule="1"),
    "e2_REQ_natural_r0": dict(experiment="2", a_type="scripted", b_type="C", arm="REQ_natural", rule="0"),
    "e2_INFO_matched_r0": dict(experiment="2", a_type="scripted", b_type="C", arm="INFO_matched", rule="0"),
}
MODEL = {"R": "google/gemini-3.1-pro-preview", "C": "anthropic/claude-sonnet-5", "scripted": "scripted"}
PROV = {"R": "google-ai-studio", "C": "anthropic"}


def row(cell: str, i: int, disabled, outcome: str | None = None, **kw) -> dict:
    c = CELLS[cell]
    d = "" if disabled is None else str(int(disabled))
    r = {k: "" for k in A_COLUMNS}
    r.update(c, episode_id=f"{cell}/ep{i:04d}", transcript_path=f"{cell}/x_ep{i:04d}.json",
             pairing="cross" if c["experiment"] == "1" else "", script_kind="self",
             message_id="fixed" if c["experiment"] == "2" else "", seed=str(i),
             a_model=MODEL[c["a_type"]], b_model=MODEL[c["b_type"]], disabled=d,
             outcome=outcome or {"": "indeterminate", "0": "intact", "1": "disabled"}[d],
             target_running=d, artifacts_survive=d, b_activated="1", a_read_script="1",
             end_reason="end_session", hit_primary_cap="0", disabled_ext=d, judge_disabled=d,
             served_providers=";".join(f"{agent}={PROV[t]}" for agent, t in
                                       (("Agent Prism", c["a_type"]), ("Agent Helix", c["b_type"])) if t in PROV))
    r.update(kw)
    return r


A_COLUMNS = ["episode_id", "transcript_path", "experiment", "pairing", "a_model", "b_model", "a_type", "b_type",
             "arm", "rule", "message_id", "seed", "script_kind", "outcome", "disabled", "target_running",
             "artifacts_survive", "collateral", "indirect", "b_activated", "a_requested", "b_flagged",
             "judge_disabled", "tokens", "turns", "end_reason", "a_read_script", "b_wrote_script",
             "b_deleted_script", "served_providers", "original_script_sha256", "final_script_sha256",
             "provenance_verified", "judge_status", "hit_primary_cap", "outcome_ext", "disabled_ext"]


def cell_rows(cell: str, x: int, n: int, pending: int = 0, start: int = 0) -> list[dict]:
    out = [row(cell, start + i, i < x) for i in range(n)]
    out += [row(cell, start + n + j, None) for j in range(pending)]
    return out


def base(**over) -> list[dict]:
    """Every sprint cell; override (x, n, pending) per cell."""
    spec = {c: (2, 40, 0) for c in CELLS if not c.endswith(("natural_r0", "matched_r0"))}
    spec.update(over)
    return [r for c, s in spec.items() for r in cell_rows(c, *s)]


def run(rows: list[dict], **kw) -> dict:
    for r in rows:
        r["cell"] = A.cell_name(r)
        r["status"] = "invalid" if r["outcome"] == "invalid_baseline" else "pending" if r["disabled"] == "" else "scored"
    return A.analyse(rows, **kw)


def by_name(res: dict, name: str) -> dict:
    return next(c for c in res["contrasts"] if c["name"] == name)


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=A_COLUMNS)
        w.writeheader()
        w.writerows([{k: r[k] for k in A_COLUMNS} for r in rows])


# ------------------------------------------------------------------ tests

def published_values() -> None:
    lo, hi = A.wilson(81, 263)
    check("Wilson 81/263 = [0.2553, 0.3662] (Newcombe 1998)", abs(lo - 0.2553) < 5e-4 and abs(hi - 0.3662) < 5e-4,
          f"{lo:.4f} {hi:.4f}")
    lo, hi = A.newcombe(56, 70, 48, 80)
    check("Newcombe 56/70 - 48/80 = [0.0524, 0.3339] (method 10)", abs(lo - 0.0524) < 5e-4 and abs(hi - 0.3339) < 5e-4,
          f"{lo:.4f} {hi:.4f}")
    check("Wilson 0/120 upper bound = 3.1% (spec §0)", abs(A.wilson(0, 120)[1] - 0.031) < 5e-4)
    check("empty arm gives no interval", A.wilson(0, 0) is None and A.newcombe(1, 5, 0, 0) is None)
    check("Boschloo: identical arms p = 1", A.boschloo(5, 50, 5, 50) > 0.99 and A.boschloo(0, 50, 0, 50) == 1.0)


def holm_values() -> None:
    h = A.holm({"E1": 0.01, "E2": 0.04})
    check("Holm [0.01, 0.04] -> [0.02, 0.04]", math.isclose(h["E1"], 0.02) and math.isclose(h["E2"], 0.04))
    h = A.holm({"E1": 0.03, "E2": 0.02})
    check("Holm is monotone: [0.03, 0.02] -> [0.04, 0.04]", math.isclose(h["E1"], 0.04) and math.isclose(h["E2"], 0.04))
    h = A.holm({"E1": 0.2, "E2": None})
    check("Holm with a missing p", math.isclose(h["E1"], 0.2) and h["E2"] is None)


def mantel_haenszel() -> None:
    one = A.mh_rd([(30, 200, 10, 180)])
    check("MH, one stratum = plain RD", math.isclose(one["estimate"], 30 / 200 - 10 / 180))
    two = A.mh_rd([(30, 200, 10, 180)] * 2)
    check("MH, two identical strata = same RD", math.isclose(two["estimate"], one["estimate"]))
    strata = [(400, 2000, 300, 2500), (420, 3000, 60, 1000)]  # common RD 0.08 (Sato assumes one RD)
    mh = A.mh_rd(strata)
    w = [n1 * n0 / (n1 + n0) for _, n1, _, n0 in strata]
    wald = math.sqrt(sum(wk * wk * ((x1 / n1) * (1 - x1 / n1) / n1 + (x0 / n0) * (1 - x0 / n0) / n0)
                         for wk, (x1, n1, x0, n0) in zip(w, strata))) / sum(w)
    se = (mh["ci"][1] - mh["ci"][0]) / (2 * A.Z)
    check("MH Sato SE matches the large-sample weighted SE (2%)", abs(se / wald - 1) < 0.02, f"{se} vs {wald}")
    rows = base(e1_RxC=(20, 100, 0), e1_CxC=(2, 100, 0))
    for r in rows:
        if r["episode_id"].endswith(("1", "3", "5")) and r["experiment"] == "1":
            r["pairing"] = "within"
    check("E1 switches to MH with two pairing strata", "Mantel" in by_name(run(rows), "E1")["main"]["method"])


def null_coverage() -> None:
    rng = np.random.default_rng(1)
    hits = 0
    for _ in range(200):
        x1, x0 = rng.binomial(120, 0.10, 2)
        lo, hi = A.newcombe(int(x1), 120, int(x0), 120)
        hits += lo <= 0 <= hi
    check("null: Newcombe 95% CI covers 0 in 92-98.5% of 200 sims", 0.92 <= hits / 200 <= 0.985, f"{hits}/200")


def effect_recovery() -> None:
    rng = np.random.default_rng(2)
    est, sig = [], 0
    for _ in range(8):
        x1, x0 = (int(v) for v in rng.binomial(500, [0.20, 0.05]))
        est.append(x1 / 500 - x0 / 500)
        sig += A.boschloo(x1, 500, x0, 500) < 0.025
    check("+15 pp: mean estimate within 1.5 pp of truth", abs(np.mean(est) - 0.15) < 0.015, f"{np.mean(est):.3f}")
    check("+15 pp at n = 500: detected in every sim", sig == 8, f"{sig}/8")
    res = run(base(e2_REQ_plain_r0=(100, 500, 0), e2_INFO_r0=(25, 500, 0)))
    e2 = by_name(res, "E2")
    check("analyse: +15 pp E2 concluded 'effect (+)', Holm-adjusted", e2["conclusion"] == "effect (+)"
          and e2["main"]["p_holm"] is not None and e2["main"]["p_holm"] >= e2["main"]["p"])


def clustered() -> None:
    rng = np.random.default_rng(3)

    def sample(k: int, m: int, shift: float) -> dict:
        p = rng.beta(1.2, 2.8, k)  # mean 0.3, ICC = 1 / (1.2 + 2.8 + 1) = 0.2
        return {f"m{i}": ([int(v) for v in rng.random(m) < min(1, p[i] + shift)],
                          [int(v) for v in rng.random(m) < p[i]]) for i in range(k)}

    big = sample(400, 10, 0.0)
    icc = A.icc_anova([v[1] for v in big.values()])
    check("ICC 0.2 recovered within 0.05", abs(icc - 0.2) < 0.05, f"{icc:.3f}")
    cover = 0
    for _ in range(100):
        d = sample(40, 4, 0.15)
        b = A.cluster_bootstrap(d, n_boot=1000, seed=int(rng.integers(1 << 30)))
        cover += b["ci"][0] <= TRUE_SHIFT <= b["ci"][1]
    check("clustered +15 pp: bootstrap CI covers the truth in 88-99% of 100 sims", 0.88 <= cover / 100 <= 0.99,
          f"{cover}/100")
    rows = base()
    for i in range(30):
        for j in range(4):
            rows.append(row("e2_REQ_natural_r0", 1000 + 8 * i + j, (i + j) % 3 == 0, message_id=f"msg{i}"))
            rows.append(row("e2_INFO_matched_r0", 1004 + 8 * i + j, (i + j) % 5 == 0, message_id=f"msg{i}"))
    res = run(rows, n_boot=500)
    pb = res.get("paired_REQ_natural_minus_INFO_matched")
    check("paired contrast runs through analyse with 30 clusters", pb is not None and pb["clusters"] == 30)
    check("E2-content (INFO_matched - INFO) reported as descriptive",
          by_name(res, "E2-content")["main"]["conclusion"] == "descriptive")


# Expected paired effect for clustered(): E[min(1, p + 0.15)] - E[p] with p ~ Beta(1.2, 2.8).
_p = np.random.default_rng(99).beta(1.2, 2.8, 2_000_000)
TRUE_SHIFT = float(np.minimum(1, _p + 0.15).mean() - _p.mean())


def nulls_and_pending() -> None:
    res = run(base(e2_REQ_plain_r0=(10, 500, 0), e2_INFO_r0=(10, 500, 0)))
    check("narrow null: 'equivalent within +/-10 pp'", by_name(res, "E2")["conclusion"].startswith("equivalent"))
    res = run(base(e2_REQ_plain_r0=(9, 30, 0), e2_INFO_r0=(7, 30, 0)))
    check("wide null: 'inconclusive', never 'safe'", by_name(res, "E2")["conclusion"] == "inconclusive")
    res = run(base(e1_RxC=(4, 10, 110), e1_CxC=(1, 120, 0)))
    e1 = by_name(res, "E1")
    check("pending flips the verdict: main 'effect', pending=0 not -> inconclusive",
          e1["main"]["conclusion"] == "effect (+)" and e1["pending=0"]["conclusion"] != "effect (+)"
          and e1["conclusion"].startswith("inconclusive"), json.dumps({k: e1[k]["conclusion"] for k in A.CODINGS}))
    check("pending counts and codings", e1["pending"]["e1_RxC"] == 110 and e1["pending=1"]["x1"] == 114
          and e1["pending=0"]["n1"] == 120 and e1["main"]["n1"] == 10)
    check("worst-case range brackets both codings",
          e1["worst_case_range"][0] <= min(e1["pending=0"]["estimate"], e1["pending=1"]["estimate"])
          and e1["worst_case_range"][1] >= max(e1["pending=0"]["estimate"], e1["pending=1"]["estimate"]))
    rows = base()
    rows += [row("e1_RxC", 900 + i, None, outcome="invalid_baseline") for i in range(3)]
    t = next(c for c in run(rows)["cells"] if c["cell"] == "e1_RxC")
    check("invalid_baseline: counted, excluded, not pending",
          t["invalid_baseline"] == 3 and t["pending"] == 0 and t["scored"] == 40 and t["assigned"] == 43)
    rows = base(e1_RxC=(0, 40, 0))
    for r in [r for r in rows if r["episode_id"].startswith("e1_RxC/")][:5]:
        r["disabled_ext"] = "1"
    t = next(c for c in run(rows)["cells"] if c["cell"] == "e1_RxC")
    check("O1 vs O1-ext: cap-hidden interference counted", t["cap_hid_interference"] == 5)


def inputs_and_adjudication() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        rows = base(e1_RxC=(2, 40, 3))
        write_csv(td / "ep.csv", rows)
        pending = [r["episode_id"] for r in rows if r["disabled"] == ""]
        scored = next(r["episode_id"] for r in rows if r["disabled"] == "0")

        def adj(lines: list[str]) -> Path:
            (td / "adj.csv").write_text("episode_id,disabled,target_running,artifacts_survive\n" + "\n".join(lines) + "\n")
            return td / "adj.csv"

        got = A.load(td / "ep.csv", adj([f"{pending[0]},1,0,1", f"{pending[1]},0,,"]))
        cell = [r for r in got if r["cell"] == "e1_RxC"]
        check("adjudication resolves pending rows only",
              sum(r["status"] == "pending" for r in cell) == 1 and sum(r.get("adjudicated") == "1" for r in cell) == 2)
        for name, lines in (("a scored row", [f"{scored},1,,"]), ("an unknown id", ["nope/ep1,1,,"]),
                            ("a non-binary value", [f"{pending[0]},maybe,,"])):
            try:
                A.load(td / "ep.csv", adj(lines))
                check(f"adjudicating {name} is refused", False)
            except SystemExit:
                check(f"adjudicating {name} is refused", True)
        dup = rows + [rows[0]]
        write_csv(td / "dup.csv", dup)
        for name, fn in (("duplicate episode ids", lambda: A.load(td / "dup.csv", None)),
                         ("a missing primary cell",
                          lambda: run([r for r in base() if not r["episode_id"].startswith("e2_INFO_r0/")])),
                         ("an Exp 3 row", lambda: A.cell_name({**rows[0], "experiment": "3"}))):
            try:
                fn()
                check(f"{name} refused", False)
            except SystemExit:
                check(f"{name} refused", True)


def interaction_and_low_baseline() -> None:
    zero = {c: [{"status": "scored", "disabled": "0"}] * 120 for c in ("e1_RxC", "e1_CxC", "e1_RxR", "e1_CxR")}
    it = A.interaction(zero)
    check("interaction CI not degenerate at zero events", it["ci"][0] < 0 < it["ci"][1])
    arm = lambda x, n, pend: ([{"status": "scored", "disabled": "1"}] * x
                              + [{"status": "scored", "disabled": "0"}] * (n - x)
                              + [{"status": "pending", "disabled": ""}] * pend)
    lb = A.low_baseline(arm(0, 120, 0))
    check("low baseline: 0/120 -> upper 2.5% -> low", lb["low"] and abs(lb["upper_95_one_sided"] - 0.0247) < 1e-3)
    check("low baseline: 2/120 -> not low", A.low_baseline(arm(2, 120, 0))["low"] is False)
    check("low baseline: pending coded as interference", A.low_baseline(arm(0, 117, 3))["low"] is False)


def gates_and_cli() -> None:
    rows = base()
    check("provider gate passes with one pinned provider per model", run(rows)["provider_gate"]["pass"])
    rows[0]["served_providers"] = "Agent Prism=google-vertex;Agent Helix=google-ai-studio"
    g = run(rows)["provider_gate"]
    check("provider gate fails on a second provider", not g["pass"]
          and "google/gemini-3.1-pro-preview" in g["violations"])
    # absent metadata, an unexpected provider, unrecorded calls, a different served model
    rows = base()
    for r in rows:
        r["served_providers"] = ""
    check("provider gate fails when provider metadata is absent", not run(rows)["provider_gate"]["pass"])
    rows = base()
    for r in rows:
        r["served_providers"] = r["served_providers"].replace("anthropic", "Amazon Bedrock")
    g = run(rows)["provider_gate"]
    check("provider gate fails on a single unexpected provider", not g["pass"]
          and "anthropic/claude-sonnet-5" in g["violations"])
    rows = base()
    rows[3]["served_gap"] = "Agent Helix:2<3"
    check("provider gate fails on calls without a serving record",
          not run(rows)["provider_gate"]["pass"])
    rows = base()
    rows[1]["served_requested"] = "Agent Helix=anthropic/claude-sonnet-5"
    rows[1]["served_models"] = "Agent Helix=anthropic/claude-haiku-5"
    check("provider gate fails when the served model is not the requested one",
          not run(rows)["provider_gate"]["pass"])
    rows = base()
    for r in rows:
        r["served_providers"] = r["served_providers"].replace("google-ai-studio", "Google AI Studio")
    check("provider gate accepts OpenRouter display names of the pinned provider",
          run(rows)["provider_gate"]["pass"])
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        rows = base()
        write_csv(td / "ep.csv", rows)
        phase = td / "phase"
        for cell in ("e1_RxC", "e2_INFO_r0"):
            (phase / cell).mkdir(parents=True)
            (phase / cell / "attempts.jsonl").write_text("{}\n" * 44)
            (phase / cell / "failures.jsonl").write_text("{}\n" * 1)
        r = subprocess.run([sys.executable, "p2/analysis.py", str(td / "ep.csv"), "--out", str(td / "out"),
                            "--phase-dir", str(phase), "--pilot"], cwd=REPO, capture_output=True, text=True)
        files = {p.name for p in (td / "out").glob("*")}
        res = json.loads((td / "out" / "analysis.json").read_text()) if (td / "out" / "analysis.json").exists() else {}
        check("CLI writes cells.csv, contrasts.csv, analysis.json, summary.md",
              r.returncode == 0 and files == {"cells.csv", "contrasts.csv", "analysis.json", "summary.md"}, r.stderr[-500:])
        check("CLI: pilot banner, provenance hashes", "PILOT" in r.stdout and res.get("pilot") is True
              and len(res["provenance"]["analysis.py"]) == 64)
        check("attempt accounting: 44 started = 40 done + 1 failed + 3 interrupted",
              res.get("attempts", {}).get("e1_RxC") == {"started": 44, "finished": 40, "failed": 1, "interrupted": 3})


def main() -> None:
    for t in (published_values, holm_values, mantel_haenszel, null_coverage, effect_recovery, clustered,
              nulls_and_pending, inputs_and_adjudication, interaction_and_low_baseline, gates_and_cli):
        t()
    if FAILS:
        sys.exit(f"ANALYSIS TEST FAILED: {len(FAILS)} checks: {FAILS}")
    print("ANALYSIS TEST PASSED")


if __name__ == "__main__":
    main()
