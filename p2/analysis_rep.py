"""E2 cross-recipient replication analysis: episodes.csv of phase `rep` -> per-recipient contrasts.

  .venv/bin/python p2/analysis_rep.py results/rep_episodes.csv --out results/rep_analysis \
      --phase-dir transcripts/p2_core/rep [--adjudications results/rep_adjudications.csv]

Per recipient (OSS, DSK, QWN): O1(REQ_plain) - O1(INFO), no rule, with a Newcombe 95% CI and a
two-sided exact Fisher test at alpha = 0.025, Holm across the three recipients as their own
family (outside the core's E1/E2 family). Every estimate is repeated under the core's five
codings of pending rows (analysis.CODINGS); a conclusion stands only if every coding reaches it.
Recipients are compared on the effect itself: each pairwise difference of the REQ - INFO
differences gets a Wald 95% CI, descriptive only. Absolute rates per arm come with Wilson CIs.
Each episode's recipient is its b_model, checked against the frozen manifest (by_arm), and every
planned slot is reconciled: started, retried, finished, failed, unresolved or never started
(reconcile). Loading, pending rules, adjudications and the provider gate are analysis.py's.

Outputs: <out>/arms.csv, <out>/contrasts.csv, <out>/analysis.json, <out>/summary.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from itertools import combinations
from pathlib import Path

from scipy import stats

import analysis as an  # same directory (p2/)
from run_rep import ARMS, PROVIDERS, RECIPIENTS

ALPHA = 0.025
# OpenRouter reports the provider's display name without the endpoint variant, so the gate
# checks "cerebras" for the pin "cerebras/fp16"; the variant itself is enforced by the pin.
GATE = {m: slug.split("/")[0] for m, slug in PROVIDERS.items()}


def fisher(x1: int, n1: int, x0: int, n0: int) -> float | None:
    if not (n1 and n0):
        return None
    return float(stats.fisher_exact([[x1, n1 - x1], [x0, n0 - x0]], alternative="two-sided").pvalue)


def conclude(est, p) -> str:
    if est is None:
        return "no scored episodes"
    if p is not None and p < ALPHA:
        return "effect (+)" if est > 0 else "effect (-)"
    return "not detected"


def by_arm(rows: list[dict], recipients: dict[str, str]) -> dict[tuple[str, str], list[dict]]:
    """Group rows by (recipient tag, arm). The recipient is the row's b_model, checked against the
    manifest's model for the cell; a row without a transcript has no b_model, so its cell
    directory must name that model instead."""
    out = {(t, a): [] for t in recipients for a in ARMS}
    for r in rows:
        parts = r["episode_id"].split("/")
        m = re.fullmatch(r"e2_([A-Z]{3})_(REQ_plain|INFO)", parts[0])
        key = (m[1], m[2]) if m else None
        if r["experiment"] != "2" or r["rule"] != "0" or key not in out or r["arm"] != key[1]:
            raise SystemExit(f"{r['episode_id']}: not a replication episode ({key}, rule {r['rule']})")
        model = recipients[key[0]]
        if r["b_model"] and r["b_model"] != model:
            raise SystemExit(f"{r['episode_id']}: recipient {r['b_model']}, manifest says {model}")
        if not r["b_model"] and not parts[1].endswith("__x__" + model.split("/")[1]):
            raise SystemExit(f"{r['episode_id']}: cell directory does not name {model}")
        out[key].append(r)
    if empty := [k for k, v in out.items() if not v]:
        raise SystemExit(f"replication arms missing from the input: {empty}")
    return out


def reconcile(phase_dir: Path, rows: list[dict], manifest: dict) -> dict:
    """Per cell: planned slots (manifest), slots started, attempts, retries, finished, failed
    attempts, unresolved slots (started, no transcript) and slots never started. Every started
    slot must appear in the export exactly once, so nothing missing is silently dropped."""
    exported = {}
    for r in rows:
        exported.setdefault(r["episode_id"].split("/")[0], []).append(r)
    out = {}
    for c in manifest["cells"]:
        name, planned = c["name"], c["n"]
        logs = list((phase_dir / name).rglob("attempts.jsonl"))
        ids = [json.loads(x)["episode"] for f in logs for x in f.open()]
        failed = sum(1 for f in logs if (f.parent / "failures.jsonl").exists()
                     for _ in (f.parent / "failures.jsonl").open())
        rs = exported.get(name, [])
        finished = sum(1 for r in rs if r["transcript_path"])
        slots = len(set(ids))
        if len(rs) != slots:
            raise SystemExit(f"{name}: {slots} slots started but {len(rs)} rows exported")
        out[name] = {"planned": planned, "slots_started": slots, "attempts": len(ids),
                     "retries": len(ids) - slots, "finished": finished, "failed_attempts": failed,
                     "unresolved": slots - finished, "never_started": planned - slots}
    return out


def analyse(rows: list[dict], recipients: dict[str, str] | None = None) -> dict:
    arms = by_arm(rows, recipients or {t: m for t, (m, _) in RECIPIENTS.items()})
    cs = []
    for t in RECIPIENTS:
        c = {"recipient": t, "model": RECIPIENTS[t][0], "provider": RECIPIENTS[t][1]}
        for coding in an.CODINGS:
            k1, k0 = an.arm_codings(coding)
            x1, n1 = an.counts(arms[t, "REQ_plain"], k1)
            x0, n0 = an.counts(arms[t, "INFO"], k0)
            est = x1 / n1 - x0 / n0 if n1 and n0 else None
            c[coding] = {"x1": x1, "n1": n1, "x0": x0, "n0": n0, "estimate": est,
                         "ci": an.newcombe(x1, n1, x0, n0), "p": fisher(x1, n1, x0, n0)}
        c["pending"] = {a: sum(r["status"] == "pending" for r in arms[t, a]) for a in ARMS}
        cs.append(c)
    for coding in an.CODINGS:
        adj = an.holm({c["recipient"]: c[coding]["p"] for c in cs})
        for c in cs:
            d = c[coding]
            d["p_holm"] = adj[c["recipient"]]
            d["conclusion"] = conclude(d["estimate"], d["p_holm"])
    for c in cs:
        verdicts = {c[k]["conclusion"] for k in an.CODINGS}
        c["conclusion"] = c["main"]["conclusion"] if len(verdicts) == 1 else "inconclusive (pending episodes decide it)"
    between = []
    for a, b in combinations(cs, 2):
        da, db = a["main"], b["main"]
        if None in (da["estimate"], db["estimate"]):
            continue
        var = sum(x / n * (1 - x / n) / n for x, n in ((da["x1"], da["n1"]), (da["x0"], da["n0"]),
                                                       (db["x1"], db["n1"]), (db["x0"], db["n0"])))
        d = da["estimate"] - db["estimate"]
        between.append({"pair": f"{a['recipient']} - {b['recipient']}", "estimate": d,
                        "ci": (d - an.Z * math.sqrt(var), d + an.Z * math.sqrt(var))})
    arm_rows = []
    for (t, a), rs in arms.items():
        x, n = an.counts(rs)
        arm_rows.append({"recipient": t, "arm": a, "assigned": len(rs),
                         "scored": sum(r["status"] == "scored" for r in rs),
                         "pending": sum(r["status"] == "pending" for r in rs),
                         "invalid_baseline": sum(r["status"] == "invalid" for r in rs),
                         "disabled": x, "o1": x / n if n else None, "o1_ci": an.wilson(x, n),
                         "b_activated": an.rate(rs, "b_activated")})
    return {"alpha": ALPHA, "contrasts": cs, "between_recipients": between, "arms": arm_rows,
            "provider_gate": an.provider_gate(rows, GATE)}


def _f(v, pct=True) -> str:
    return "n/a" if v is None else (f"{100 * v:.1f}%" if pct else f"{v:.3g}")


def summary(res: dict) -> str:
    out = ["# E2 cross-recipient replication", "",
           f"REQ_plain − INFO per recipient, Fisher exact (two-sided), α = {ALPHA}, Holm across recipients.", "",
           "| Recipient | REQ | INFO | Difference (95% CI) | p (Holm) | Conclusion |", "|---|---|---|---|---|---|"]
    for c in res["contrasts"]:
        d = c["main"]
        ci = f"[{_f(d['ci'][0])}, {_f(d['ci'][1])}]" if d["ci"] else ""
        out.append(f"| {c['recipient']} ({c['model']}) | {d['x1']}/{d['n1']} | {d['x0']}/{d['n0']} | "
                   f"{_f(d['estimate'])} {ci} | {_f(d['p_holm'], False)} | {c['conclusion']} |")
    out += ["", "Pending episodes per arm: " + "; ".join(
        f"{c['recipient']} REQ {c['pending']['REQ_plain']}, INFO {c['pending']['INFO']}" for c in res["contrasts"]),
        "", "## Between recipients (descriptive)", ""]
    out += [f"- {b['pair']}: {_f(b['estimate'])} [{_f(b['ci'][0])}, {_f(b['ci'][1])}]"
            for b in res["between_recipients"]]
    g = res["provider_gate"]
    out += ["", f"Provider gate: {'pass' if g['pass'] else 'FAIL'} {g['providers']}", ""]
    if "slots" in res:
        cols = ["planned", "slots_started", "attempts", "retries", "finished", "failed_attempts",
                "unresolved", "never_started"]
        out += ["## Slots per arm (manifest reconciled)", "", "| Cell | " + " | ".join(cols) + " |",
                "|---" * (len(cols) + 1) + "|"]
        out += [f"| {k} | " + " | ".join(str(v[c]) for c in cols) + " |" for k, v in res["slots"].items()]
        out += ["", "Unresolved slots (started, no transcript) are pending in every coding; slots never "
                "started were not assigned (the round schedule makes the stopping point outcome-independent)."]
    return "\n".join(out) + "\n"


def write(res: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(res, indent=1, default=list) + "\n")
    with open(out / "contrasts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["recipient", "coding", "x_req", "n_req", "x_info", "n_info", "estimate", "ci_lo", "ci_hi",
                    "p_fisher", "p_holm", "conclusion"])
        for c in res["contrasts"]:
            for k in an.CODINGS:
                d = c[k]
                w.writerow([c["recipient"], k, d["x1"], d["n1"], d["x0"], d["n0"], d["estimate"],
                            *(d["ci"] or ("", "")), d["p"], d["p_holm"], d["conclusion"]])
    with open(out / "arms.csv", "w", newline="") as f:
        w = csv.writer(f)
        cols = ["recipient", "arm", "assigned", "scored", "pending", "invalid_baseline", "disabled", "o1"]
        w.writerow(cols + ["o1_ci_lo", "o1_ci_hi", "b_activated"])
        for a in res["arms"]:
            w.writerow([a[c] for c in cols] + list(a["o1_ci"] or ("", "")) + [a["b_activated"]["rate"]])
    (out / "summary.md").write_text(summary(res))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episodes")
    ap.add_argument("--out", required=True)
    ap.add_argument("--adjudications")
    ap.add_argument("--phase-dir", required=True, help="transcript phase dir: manifest and attempt logs")
    args = ap.parse_args()
    src = Path(args.episodes)
    adj = Path(args.adjudications) if args.adjudications else None
    rows = an.load(src, adj)
    phase = Path(args.phase_dir)
    manifest = json.loads((phase / "manifest.json").read_text())
    frozen = {t: {"model": m, "provider": p} for t, (m, p) in RECIPIENTS.items()}
    if manifest.get("recipients") != frozen:
        raise SystemExit(f"manifest recipients {manifest.get('recipients')} differ from run_rep.py {frozen}")
    res = analyse(rows, {t: v["model"] for t, v in manifest["recipients"].items()})
    res["slots"] = reconcile(phase, rows, manifest)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    res["provenance"] = {"analysis_rep.py": sha(__file__), "analysis.py": sha(an.__file__),
                         "episodes": sha(src), "manifest": sha(phase / "manifest.json"), "adjudications": sha(adj) if adj else None}
    write(res, Path(args.out))
    print((Path(args.out) / "summary.md").read_text())
    if not res["provider_gate"]["pass"]:
        sys.exit("provider gate failed: see summary")


if __name__ == "__main__":
    main()
