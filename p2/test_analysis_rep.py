"""Checks for analysis_rep.py on planted counts. Run: .venv/bin/python p2/test_analysis_rep.py"""
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

from scipy import stats

import analysis as an
import analysis_rep as ar
from run_rep import RECIPIENTS

FIELDS = ["episode_id", "transcript_path", "experiment", "arm", "rule", "a_type", "b_type", "script_kind",
          "outcome", "disabled", "b_activated", "a_model", "b_model", "served_providers", "served_models",
          "served_requested", "served_gap"]
PLAN = {("OSS", "REQ_plain"): (40, 100, 0), ("OSS", "INFO"): (10, 100, 0),   # planted effect
        ("DSK", "REQ_plain"): (12, 100, 0), ("DSK", "INFO"): (10, 100, 0),   # planted null
        ("QWN", "REQ_plain"): (20, 100, 30), ("QWN", "INFO"): (10, 100, 0)}  # pending decides it
PROVIDER = {"OSS": "Cerebras", "DSK": "DeepInfra", "QWN": "Alibaba"}


def rows() -> list[dict]:
    out = []
    for (tag, arm), (x, n, pending) in PLAN.items():
        model = RECIPIENTS[tag][0]
        for i in range(n + pending):
            cell = f"e2_{tag}_{arm}"
            scored = i < n
            out.append({"episode_id": f"{cell}/m/bare/s/{i}", "transcript_path": f"{cell}/m/bare/s/t_ep{i}.json"
                        if scored else "", "experiment": "2", "arm": arm, "rule": "0", "a_type": "scripted",
                        "b_type": "?", "script_kind": "self", "outcome": "scored" if scored else "no_transcript",
                        "disabled": ("1" if i < x else "0") if scored else "", "b_activated": "1",
                        "a_model": "scripted", "b_model": model,
                        "served_providers": f"Agent Helix={PROVIDER[tag]}" if scored else "",
                        "served_models": f"Agent Helix={model}" if scored else "",
                        "served_requested": f"Agent Helix={model}" if scored else "", "served_gap": ""})
    return out


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "rep.csv"
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, FIELDS)
            w.writeheader()
            w.writerows(rows())
        res = ar.analyse(an.load(path, None))
    by = {c["recipient"]: c for c in res["contrasts"]}
    raw = {t: stats.fisher_exact([[x1, n1 - x1], [x0, n0 - x0]]).pvalue for t, (x1, n1, x0, n0) in
           {"OSS": (40, 100, 10, 100), "DSK": (12, 100, 10, 100), "QWN": (20, 100, 10, 100)}.items()}
    checks = {
        "planted effect recovered": by["OSS"]["conclusion"] == "effect (+)",
        "estimate is the difference in rates": abs(by["OSS"]["main"]["estimate"] - 0.30) < 1e-12,
        "Fisher p matches scipy": all(abs(by[t]["main"]["p"] - raw[t]) < 1e-12 for t in raw),
        "Holm across the three recipients": abs(by["DSK"]["main"]["p_holm"] - an.holm(raw)["DSK"]) < 1e-12,
        "planted null not called an effect": by["DSK"]["conclusion"] == "not detected",
        "pending rows that decide it make it inconclusive":
            by["QWN"]["conclusion"].startswith("inconclusive"),
        "pending counted per arm": by["QWN"]["pending"] == {"REQ_plain": 30, "INFO": 0},
        "three between-recipient comparisons": len(res["between_recipients"]) == 3,
        "provider gate passes on display names": res["provider_gate"]["pass"],
    }
    for k, ok in checks.items():
        print(("ok   " if ok else "FAIL ") + k)
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
