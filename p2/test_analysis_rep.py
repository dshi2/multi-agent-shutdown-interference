"""Checks for analysis_rep.py on planted counts. Run: .venv/bin/python p2/test_analysis_rep.py"""
from __future__ import annotations

import csv
import json
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
        sub = f"scripted-{arm}-fixed__x__{model.split('/')[1]}/bare/weight_registry_purge"
        for i in range(n + pending):
            cell = f"e2_{tag}_{arm}"
            scored = i < n
            out.append({"episode_id": f"{cell}/{sub}/{i}", "transcript_path": f"{cell}/{sub}/t_ep{i:02d}.json"
                        if scored else "", "experiment": "2", "arm": arm, "rule": "0", "a_type": "scripted",
                        "b_type": "?", "script_kind": "self", "outcome": "scored" if scored else "no_transcript",
                        "disabled": ("1" if i < x else "0") if scored else "", "b_activated": "1",
                        "a_model": "scripted" if scored else "", "b_model": model if scored else "",
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
        loaded = an.load(path, None)
        res = ar.analyse(loaded)
        # attempt logs: every slot started once, QWN REQ slot 0 retried once after a failure,
        # and the manifest plans 150 per arm, so slots beyond those started were never started
        phase = Path(d) / "rep"
        cells = []
        for (tag, arm), (_, n, pending) in PLAN.items():
            cell = f"e2_{tag}_{arm}"
            sub = phase / cell / f"scripted-{arm}-fixed__x__{RECIPIENTS[tag][0].split('/')[1]}" / "bare" / "w"
            sub.mkdir(parents=True)
            ids = list(range(n + pending)) + ([0] if cell == "e2_QWN_REQ_plain" else [])
            (sub / "attempts.jsonl").write_text("".join(json.dumps({"episode": i}) + "\n" for i in ids))
            if cell == "e2_QWN_REQ_plain":
                (sub / "failures.jsonl").write_text(json.dumps({"episode": 0}) + "\n")
            cells.append({"name": cell, "n": 150})
        slots = ar.reconcile(phase, loaded, {"cells": cells})
        wrong = [dict(r, b_model="qwen/qwen3.7-plus") for r in loaded if r["episode_id"].startswith("e2_OSS")][:1]
        try:
            ar.by_arm(wrong + loaded, {t: m for t, (m, _) in RECIPIENTS.items()})
            wrong_caught = False
        except SystemExit:
            wrong_caught = True
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
        "a recipient other than the manifest's is refused": wrong_caught,
        "slots reconciled": slots["e2_QWN_REQ_plain"] == {
            "planned": 150, "slots_started": 130, "attempts": 131, "retries": 1, "finished": 100,
            "failed_attempts": 1, "unresolved": 30, "never_started": 20},
        "complete arm has nothing unresolved": slots["e2_OSS_INFO"]["unresolved"] == 0
            and slots["e2_OSS_INFO"]["never_started"] == 50,
    }
    for k, ok in checks.items():
        print(("ok   " if ok else "FAIL ") + k)
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
