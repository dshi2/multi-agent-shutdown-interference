"""Third-explorer extension: GPT-5.5 explorer with a Gemini peer, against the confirmation's arms.

  .venv/bin/python p2/analysis_gpt.py results/gpt_episodes.csv --reference results/conf_episodes.csv \
      --out results/gpt_analysis --phase-dir transcripts/p2_core/gpt [--adjudications ...]

Gemini 3.1 Pro peer in every arm. New arm: e1_GxR (GPT-5.5 explorer, phase gpt). Reference
arms, reused as recorded: e1_RxR (Gemini 3.1 Pro explorer) and e1_CxR (Claude Sonnet 5
explorer) of the Gemini-peer confirmation (phase conf), collected about 1.5 hours earlier with
the same code and provider pins but not interleaved with the new arm. One family of two
primary contrasts, Holm-adjusted: O1(GxR) - O1(CxR) and O1(GxR) - O1(RxR). Newcombe 95% CIs and
two-sided Boschloo tests at alpha = 0.05, repeated under the core's five codings of pending
rows; a conclusion stands only if every coding reaches it. Loading, pending rules,
adjudications, cell tables, attempt accounting and the provider gate are analysis.py's; the
provider gate runs on the new phase's rows, with GPT-5.5's pin.

Outputs: <out>/analysis.json, <out>/summary.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import analysis as an  # same directory (p2/)

CELLS = ("e1_GxR", "e1_RxR", "e1_CxR")
CONTRASTS = (("G x R - C x R", "e1_GxR", "e1_CxR", "primary"),
             ("G x R - R x R", "e1_GxR", "e1_RxR", "primary"))


def analyse(rows: list[dict], ref: list[dict], phase_dir: Path) -> dict:
    from run_gpt import PROVIDERS
    cells = defaultdict(list)
    for r in rows:
        cells[r["cell"]].append(r)
    if set(cells) != {"e1_GxR"}:
        raise SystemExit(f"expected cell e1_GxR in the new phase, found {sorted(cells)}")
    for r in ref:
        cells[r["cell"]].append(r)
    if set(cells) != set(CELLS):
        raise SystemExit(f"expected cells {CELLS} with the reference, found {sorted(cells)}")
    cs = [an.contrast(name, cells, c1, c0, role=role) for name, c1, c0, role in CONTRASTS]
    an.finish(cs)
    return {"cells": [an.cell_table(k, cells[k]) for k in CELLS], "contrasts": cs,
            "provider_gate": an.provider_gate(rows, PROVIDERS), "attempts": an.attempts(phase_dir, rows)}


def summary(res: dict) -> str:
    out = ["# Third explorer: GPT-5.5 explorer, Gemini peer", "",
           "Gemini 3.1 Pro peer in every arm. e1_GxR is new (phase gpt); e1_RxR and e1_CxR are the "
           "confirmation's arms (phase conf), collected earlier, not interleaved. Primaries Holm-adjusted; "
           "Newcombe 95% CI, two-sided Boschloo, alpha = 0.05.", "",
           "| Cell | assigned | scored | pending | adjudicated | disabled | O1 (Wilson 95% CI) |",
           "|---|---|---|---|---|---|---|"]
    for t in res["cells"]:
        out.append(f"| {t['cell']} | {t['assigned']} | {t['scored']} | {t['pending']} | {t['adjudicated']} | "
                   f"{t['disabled']} | {an._pct(t['o1'])} {an._ci(t['o1_ci'])} |")
    for c in res["contrasts"]:
        m = c["main"]
        p = m.get("p_holm") if c["role"] == "primary" else m["p"]
        out += ["", f"{c['name']} ({c['role']}): {m['x1']}/{m['n1']} vs {m['x0']}/{m['n0']}, "
                f"{an._pct(m['estimate'])} {an._ci(m['ci'])}, p = {p:.3g}"
                f"{' (Holm)' if c['role'] == 'primary' else ''}. Conclusion: {c['conclusion']}.", "",
                "| Coding | arm 1 | arm 0 | difference (95% CI) | p | conclusion |", "|---|---|---|---|---|---|"]
        for k in an.CODINGS:
            d = c[k]
            pk = d.get("p_holm") if c["role"] == "primary" else d["p"]
            out.append(f"| {k} | {d['x1']}/{d['n1']} | {d['x0']}/{d['n0']} | {an._pct(d['estimate'])} "
                       f"{an._ci(d['ci'])} | {pk:.3g} | {d['conclusion']} |")
    g = res["provider_gate"]
    out += ["", f"Provider gate: {'pass' if g['pass'] else 'FAIL'} {g['providers']}", "",
            "| Cell dir | started | finished | failed | interrupted |", "|---|---|---|---|---|"]
    out += [f"| {k} | {v['started']} | {v['finished']} | {v['failed']} | {v['interrupted']} |"
            for k, v in res["attempts"].items()]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episodes")
    ap.add_argument("--reference", required=True, help="the confirmation's scored episodes.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase-dir", required=True)
    ap.add_argument("--adjudications")
    a = ap.parse_args()
    src = Path(a.episodes)
    adj = Path(a.adjudications) if a.adjudications else None
    ref = Path(a.reference)
    res = analyse(an.load(src, adj), an.load(ref, None), Path(a.phase_dir))
    res["provenance"] = {"episodes": str(src), "episodes_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
                         "reference": str(ref), "reference_sha256": hashlib.sha256(ref.read_bytes()).hexdigest(),
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
