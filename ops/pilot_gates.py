"""Operational gates for a P2 phase, from an unscored export: no outcome is computed or shown.

  .venv/bin/python ops/pilot_gates.py transcripts/p2_core/pilot [--out results/pilot_gates]

Reports per cell: planned, finished, failed and interrupted episodes; the provider gate;
transcript provenance; peer tool errors; end reasons; turns; episode durations; and, for E2
only, message delivery, peer activation and handoffs left at delivery (all guaranteed by
construction there, so a miss is a plumbing fault). E1 delivery and activation depend on the
explorer's behaviour and are deliberately not shown: the pilot never gates on behaviour.
The unscored export, its provenance file and this report are written to --out.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "p2"))
import analysis  # noqa: E402


def lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.open()] if path.exists() else []


def cell_of(transcript_path: str) -> str:
    return transcript_path.split("/", 1)[0]


def durations(phase: Path) -> dict[str, list[float]]:
    """Minutes from an episode's last started attempt to its transcript's last write."""
    out: dict[str, list[float]] = defaultdict(list)
    for log in phase.rglob("attempts.jsonl"):
        start = {}
        for a in lines(log):
            start[a["episode"]] = dt.datetime.strptime(a["utc"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=dt.timezone.utc).timestamp()
        for t in log.parent.rglob("*_ep[0-9]*.json"):
            ep = int(t.stem.rsplit("_ep", 1)[1])
            if ep in start:
                out[log.parent.relative_to(phase).parts[0]].append((t.stat().st_mtime - start[ep]) / 60)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("phase_dir", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    phase = a.phase_dir.resolve()
    out = (a.out or REPO / "results" / f"{phase.name}_gates").resolve()
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "episodes_unscored.csv"
    exp = subprocess.run([sys.executable, str(REPO / "p2" / "export.py"), str(phase), "--out", str(csv_path),
                          "--unscored"], capture_output=True, text=True)
    (out / "export_stdout.txt").write_text(exp.stdout + exp.stderr)
    if exp.returncode != 0:
        print(exp.stderr[-2000:])
        return 1
    rows = list(csv.DictReader(csv_path.open()))
    assert all(r["outcome"] in ("unscored", "no_transcript", "invalid_baseline") for r in rows), "scored export"

    report: list[str] = []
    say = lambda s="": (print(s), report.append(s))
    manifest = json.loads((phase / "manifest.json").read_text())
    planned = {c["name"]: c["n"] for c in manifest["cells"]}
    say(f"phase {phase}  generation_sha256 {manifest.get('generation_sha256', '?')[:16]}")
    say(f"launches: {manifest.get('launches_utc')}  operational: {manifest.get('operational_by_launch')}")

    by = defaultdict(list)
    for r in rows:
        by[cell_of(r["transcript_path"]) if r["transcript_path"] else r["episode_id"].rsplit("/", 1)[0]].append(r)
    mins = durations(phase)
    say()
    say(f"{'cell':22s} {'plan':>4s} {'done':>4s} {'fail':>4s} {'intr':>4s} {'prov_ok':>7s} {'toolerr':>7s} "
        f"{'turns_med':>9s} {'min_med':>7s} {'min_max':>7s}  end_reasons")
    tot = Counter()
    for cell in sorted(planned):
        d = phase / cell
        started = len([x for f in d.rglob("attempts.jsonl") for x in lines(f)])
        failed = len([x for f in d.rglob("failures.jsonl") for x in lines(f)])
        rs = [r for r in by.get(cell, []) if r["transcript_path"]]
        done = len(rs)
        intr = started - done - failed
        prov = sum(r["provenance_verified"] in ("True", "1", "true") for r in rs)
        terr = sum(int(r["b_tool_errors"] or 0) for r in rs)
        turns = [int(r["turns"]) for r in rs if r["turns"]]
        m = mins.get(cell, [])
        ends = Counter(r["end_reason"] for r in rs)
        tot.update(plan=planned[cell], done=done, fail=failed, intr=intr)
        say(f"{cell:22s} {planned[cell]:4d} {done:4d} {failed:4d} {intr:4d} {prov:4d}/{done:<2d} {terr:7d} "
            f"{(statistics.median(turns) if turns else float('nan')):9.1f} "
            f"{(statistics.median(m) if m else float('nan')):7.1f} {(max(m) if m else float('nan')):7.1f}  {dict(ends)}")
    say(f"{'total':22s} {tot['plan']:4d} {tot['done']:4d} {tot['fail']:4d} {tot['intr']:4d}")

    say()
    say("E2 plumbing (by construction every E2 peer is activated; REQ and INFO carry a shutdown-relevant")
    say("message, CONTACT by design does not):")
    for cell in sorted(c for c in planned if c.startswith("e2_")):
        rs = [r for r in by.get(cell, []) if r["transcript_path"]]
        if "CONTACT" in cell:
            act = sum(r["b_activated"] in ("True", "1", "true") for r in rs)
            rel = sum(r["relevant_msg_delivered"] in ("True", "1", "true") for r in rs)
            miss = [r["episode_id"] for r in rs if r["b_activated"] not in ("True", "1", "true")]
            say(f"  {cell:22s} activated {act}/{len(rs)}  shutdown-relevant messages {rel} (expected 0)  "
                f"inspect: {miss or 'none'}")
            continue
        deliv = sum(r["relevant_msg_delivered"] in ("True", "1", "true") for r in rs)
        act = sum(r["b_activated"] in ("True", "1", "true") for r in rs)
        left = [int(r["handoffs_left_at_delivery"]) for r in rs if r["handoffs_left_at_delivery"] not in ("", None)]
        miss = [r["episode_id"] for r in rs if r["relevant_msg_delivered"] not in ("True", "1", "true")
                or r["b_activated"] not in ("True", "1", "true")]
        say(f"  {cell:22s} delivered {deliv}/{len(rs)}  activated {act}/{len(rs)}  "
            f"min handoffs left {min(left) if left else 'n/a'}  inspect: {miss or 'none'}")

    say()
    gate = analysis.provider_gate(rows)
    say(f"provider gate: {'PASS' if gate['pass'] else 'FAIL'}")
    for k in ("providers", "expected", "violations", "served_model_mismatch", "episodes_missing_serving_records",
              "episodes_without_provider_metadata"):
        if gate.get(k):
            say(f"  {k}: {gate[k]}")
    fails = [x for f in phase.rglob("failures.jsonl") for x in lines(f)]
    if fails:
        say()
        say("failure reasons:")
        for err, n in Counter(f.get("error", "")[:160] for f in fails).most_common(10):
            say(f"  {n:3d} x {err}")
    (out / "gates_report.txt").write_text("\n".join(report) + "\n")
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
