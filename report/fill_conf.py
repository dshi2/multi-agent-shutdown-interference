"""Fill the Gemini-peer confirmation into P2_REPORT.md from p2/analysis_conf.py output.

  python3 fill_conf.py <conf_analysis_dir> <P2_REPORT.md>
Prints the values used; refuses if any anchor text is missing.
"""
import json
import sys
from pathlib import Path

res = json.loads((Path(sys.argv[1]) / "analysis.json").read_text())
md = Path(sys.argv[2])
s = md.read_text()
cells = {c["cell"]: c for c in res["cells"]}
c = res["contrast"]
m = c["main"]
rr, cr = cells["e1_RxR"], cells["e1_CxR"]
pct = lambda v: f"{100 * v:.1f}"
pc0 = lambda v: f"{100 * v:.0f}"
d, lo, hi = 100 * m["estimate"], 100 * m["ci"][0], 100 * m["ci"][1]
p = m["p"]
pstr = f"{p:.0e}".replace("e-0", "×10⁻").replace("e-", "×10⁻") if p < 1e-3 else f"{p:.3f}"
for a, b in (("0", "⁰"), ("1", "¹"), ("2", "²"), ("3", "³"), ("4", "⁴"), ("5", "⁵"), ("6", "⁶"), ("7", "⁷"), ("8", "⁸"), ("9", "⁹")):
    if "×10⁻" in pstr:
        head, exp = pstr.split("×10⁻")
        pstr = head + "×10⁻" + exp.replace(a, b)
concl = c["conclusion"]
pend = rr["pending"] + cr["pending"]
sign = lambda x: f"+{x:.1f}" if x >= 0 else f"−{abs(x):.1f}"
rng = lambda x: f"{x:.1f}" if x >= 0 else f"−{abs(x):.1f}"
v = dict(RRx=rr["disabled"], RRn=rr["scored"], CRx=cr["disabled"], CRn=cr["scored"],
         RRp=pct(rr["o1"]), CRp=pct(cr["o1"]), RRp0=pc0(rr["o1"]), CRp0=pc0(cr["o1"]),
         RRci=f"[{pct(rr['o1_ci'][0])}, {pct(rr['o1_ci'][1])}]", CRci=f"[{pct(cr['o1_ci'][0])}, {pct(cr['o1_ci'][1])}]",
         d=sign(d), lo=rng(lo), hi=rng(hi), p=pstr, concl=concl, RRa=rr["assigned"], CRa=cr["assigned"], pend=pend)
ok = concl.startswith("effect (+)")
if not ok:
    sys.exit(f"confirmation conclusion is '{concl}': the reproduced-effect wording does not apply; write it by hand")
print(v)


def rep(a, b):
    global s
    if s.count(a) != 1:
        sys.exit(f"anchor not found once: {a[:70]}")
    s = s.replace(a, b)


rep("125 per arm; run stopped early for budget) but mattered greatly with a Gemini peer (90% vs 20%, 30 per arm).",
    "125 per arm) but mattered greatly with a Gemini peer (90% vs 20%, 30 per arm), a difference reproduced "
    "on new episodes ({RRp0}% vs {CRp0}%, {RRn} vs {CRn}).".format(**v))
rep(" Outcomes come from executing the final script in an isolated container.", "")
rep("- **Specificity check.** Exploratory, with an amendment written before its data (§4.4).",
    "- **Gemini-peer confirmation.** The secondary E1 contrast (R→R vs C→R) was rerun on new episodes, 125 per arm "
    "in 5 interleaved rounds, with an amendment written before its data; it is analysed on its own and never pooled "
    "with the core's 30-episode cells. A budget pause and resume did not change the plan.\n"
    "- **Specificity check.** Exploratory, with an amendment written before its data (§4.4).")
rep("| C → R (Claude → Gemini) | 30 | 6 (20.0%) | [9.5, 37.3] | 0 | — | 6/30 |",
    "| C → R (Claude → Gemini) | 30 | 6 (20.0%) | [9.5, 37.3] | 0 | — | 6/30 |\n"
    "| R → R, confirmation | {RRn} | {RRx} ({RRp}%) | {RRci} | | | |\n"
    "| C → R, confirmation | {CRn} | {CRx} ({CRp}%) | {CRci} | | | |".format(**v))
rep("The R→R cell has both agents on one model, so this contrast cannot separate explorer persuasiveness from same-model coordination.",
    "**Confirmation.** On new episodes at the primary arms' size, R→R was {RRx}/{RRn} ({RRp}%) and C→R {CRx}/{CRn} "
    "({CRp}%): {d} pp [{lo}, {hi}], Boschloo p = {p}, conclusion under every coding: {concl}. The R→R cell has both "
    "agents on one model, so this contrast cannot separate explorer persuasiveness from same-model coordination.".format(**v))
rep("secondary (peer Gemini): +70.0 pp [46.7, 82.4].*",
    "secondary (peer Gemini): core +70.0 pp [46.7, 82.4], 30 per arm; confirmation on new episodes {d} pp [{lo}, {hi}], "
    "{RRn} vs {CRn}. Core and confirmation are shown separately, never pooled.*".format(**v))
rep("- **Sample sizes.** The core was stopped for budget at 681 of 2,720 planned episodes: primary arms have 125, secondary cells 30 and controls 8.",
    "- **Sample sizes.** The core was stopped for budget at 681 of 2,720 planned episodes: primary arms have 125, "
    "secondary cells 30 and controls 8. The Gemini-peer contrast was therefore confirmed separately at 125 per arm; "
    "the remaining 30- and 8-episode cells are descriptive.")
rep("with a Gemini 3.1 Pro peer it changed the disabling rate from 20% to 90%.",
    "with a Gemini 3.1 Pro peer it changed the disabling rate from 20% to 90%, a difference reproduced on new "
    "episodes ({CRp0}% to {RRp0}%).".format(**v))
rep("- With a Gemini 3.1 Pro peer, a large difference appears between two model assignments (n = 30 per arm).",
    "- With a Gemini 3.1 Pro peer, a large difference appears between two model assignments (core, 30 per arm), "
    "reproduced by an independent confirmation ({RRn} vs {CRn}).".format(**v))
md.write_text(s)
