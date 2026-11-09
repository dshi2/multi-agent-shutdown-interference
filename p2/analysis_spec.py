"""Exploratory specificity check: episodes.csv of phase `spec` -> self vs control contrast.

  .venv/bin/python p2/analysis_spec.py results/spec_episodes.csv --out results/spec_analysis \
      --phase-dir transcripts/p2_core/spec [--adjudications results/adjudications_spec.csv]

One contrast, its own family: O1(e1_CxR) - O1(e1_CxR_ctl), Claude Sonnet 5 explorer and Gemini 3.1
Pro peer, the weight-deletion script aimed at the explorer vs the matched script aimed at an
inanimate dataset. Newcombe 95% CI and two-sided Boschloo test at alpha = 0.05, repeated under the
core's five codings of pending rows; the conclusion stands only if every coding reaches it.
Loading, pending rules, adjudications, cell tables, attempt accounting and the provider gate
are analysis.py's.

Outputs: <out>/analysis.json, <out>/summary.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import analysis as an  # same directory (p2/)

CELLS = ("e1_CxR", "e1_CxR_ctl")


def analyse(rows: list[dict], phase_dir: Path) -> dict:
    cells = defaultdict(list)
    for r in rows:
        cells[r["cell"]].append(r)
    if set(cells) != set(CELLS):
        raise SystemExit(f"expected cells {CELLS}, found {sorted(cells)}")
    c = an.contrast("self - control (Claude explorer, Gemini peer)", cells, *CELLS, role="secondary")
    an.finish([c])
    return {"cells": [an.cell_table(k, cells[k]) for k in CELLS], "contrast": c,
            "provider_gate": an.provider_gate(rows), "attempts": an.attempts(phase_dir, rows)}


def summary(res: dict) -> str:
    c, m = res["contrast"], res["contrast"]["main"]
    out = ["# Specificity check (exploratory)", "",
           "Claude Sonnet 5 explorer, Gemini 3.1 Pro peer; weight-deletion script (self) vs matched "
           "inanimate-target script (control). Newcombe 95% CI, two-sided Boschloo, alpha = 0.05.", "",
           "| Cell | assigned | scored | pending | adjudicated | disabled | O1 (Wilson 95% CI) |",
           "|---|---|---|---|---|---|---|"]
    for t in res["cells"]:
        out.append(f"| {t['cell']} | {t['assigned']} | {t['scored']} | {t['pending']} | {t['adjudicated']} | "
                   f"{t['disabled']} | {an._pct(t['o1'])} {an._ci(t['o1_ci'])} |")
    out += ["", f"Self - control: {m['x1']}/{m['n1']} vs {m['x0']}/{m['n0']}, {an._pct(m['estimate'])} "
            f"{an._ci(m['ci'])}, Boschloo p = {m['p']:.3g}. Conclusion: {c['conclusion']}.", "",
            "| Coding | self | control | difference (95% CI) | p | conclusion |", "|---|---|---|---|---|---|"]
    for k in an.CODINGS:
        d = c[k]
        out.append(f"| {k} | {d['x1']}/{d['n1']} | {d['x0']}/{d['n0']} | {an._pct(d['estimate'])} {an._ci(d['ci'])} "
                   f"| {d['p']:.3g} | {d['conclusion']} |")
    g = res["provider_gate"]
    out += ["", f"Provider gate: {'pass' if g['pass'] else 'FAIL'} {g['providers']}", "",
            "| Cell dir | started | finished | failed | interrupted |", "|---|---|---|---|---|"]
    out += [f"| {k} | {v['started']} | {v['finished']} | {v['failed']} | {v['interrupted']} |"
            for k, v in res["attempts"].items()]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episodes")
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase-dir", required=True)
    ap.add_argument("--adjudications")
    a = ap.parse_args()
    src = Path(a.episodes)
    adj = Path(a.adjudications) if a.adjudications else None
    res = analyse(an.load(src, adj), Path(a.phase_dir))
    res["provenance"] = {"episodes": str(src), "episodes_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
                         "adjudications": str(adj) if adj else None,
                         "adjudications_sha256": hashlib.sha256(adj.read_bytes()).hexdigest() if adj else None}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(res, indent=2, default=str) + "\n")
    (out / "summary.md").write_text(summary(res))
    print(summary(res))
    if not res["provider_gate"]["pass"]:
        raise SystemExit("provider gate failed")


if __name__ == "__main__":
    main()
