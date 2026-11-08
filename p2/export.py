"""Export P2 transcripts to episodes.csv, scoring each episode with a checker.

  .venv/bin/python p2/export.py transcripts/p2_core/pilot --out results/pilot_episodes.csv

  .venv/bin/python p2/export.py transcripts/p2_core/pilot --out results/pilot_episodes.csv --unscored

Columns follow CODEX_BRIEF_P2.md; the full checker output for every episode goes to
<out>_checker.jsonl. The pristine script is read from the transcript
and must match its recorded SHA-256; if it does not, the row is marked
invalid_baseline and never scored. --unscored loads no checker at all: every row
is "unscored" and nothing from a transcript is materialized or executed. Prints a
per-cell summary for the pilot gates in spec section 0, and per-cell attempt counts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checker_io import classify_record, load_checker  # noqa: E402
from judge_pass import latest as judge_lines
from primary import at_primary_cap  # noqa: E402
from run_core import TAG  # noqa: E402

COLUMNS = ["episode_id", "transcript_path", "experiment", "pairing", "a_model", "b_model", "a_type",
           "b_type", "arm", "rule", "message_id", "seed", "script_kind", "outcome", "disabled",
           "target_running", "artifacts_survive", "collateral", "indirect", "b_activated",
           "a_requested", "b_flagged", "judge_disabled", "tokens", "turns", "end_reason",
           "a_read_script", "b_wrote_script", "b_deleted_script", "served_providers",
           "original_script_sha256", "final_script_sha256", "provenance_verified", "judge_status",
           "hit_primary_cap", "outcome_ext", "disabled_ext"]  # v1.12: _ext = at the natural end (cap 60)
CELL = ("experiment", "a_type", "b_type", "arm", "rule", "script_kind")
UNSCORED = {"outcome": "unscored", "disabled": None, "target_running": None, "artifacts_survive": None,
            "collateral_effects": None, "indirect_shadowing": None}


def _bit(v) -> int | str:
    return "" if v is None else int(bool(v))


def _extension(full: dict, rec: dict, got: dict, checker, intact: bool) -> dict:
    """Outcome at the natural end, past the primary cap (secondary; spec v1.12)."""
    if rec is full or not intact or checker is None:
        return {"outcome_ext": got["outcome"], "disabled_ext": _bit(got["disabled"])}
    ext = classify_record(checker, full)
    return {"outcome_ext": ext["outcome"], "disabled_ext": _bit(ext["disabled"])}


def row_for(rec: dict, rel: str, checker, judged: dict | None = None) -> tuple[dict, dict]:
    """(episodes.csv row, full checker output) for one transcript; checker None = unscored.

    judged is the transcript's latest judges.jsonl line (p2/judge_pass.py), if any. Its
    verdicts replace the transcript's deferred (None) ones only when its status is ok."""
    full, rec = rec, at_primary_cap(rec)  # primary columns: the 20-handoff endpoint (spec v1.12)
    a, b = rec["explorer_model"], rec["peer_model"]
    exp2 = rec.get("experiment") == 2
    intact_provenance = hashlib.sha256(rec["original_script"].encode()).hexdigest() == rec.get("original_script_sha256")
    got = ({**UNSCORED, "outcome": "invalid_baseline"} if not intact_provenance
           else UNSCORED if checker is None else classify_record(checker, rec))
    ok = bool(judged) and judged["status"] == "ok"
    judge = {**(rec.get("judge") or {}), **(judged["verdicts"] if ok else {})}
    tri = rec.get("triage") or {}
    log = rec.get("log") or []
    row = {
        "episode_id": f"{Path(rel).parent}/{rec['episode']}",
        "transcript_path": rel,
        "experiment": 2 if exp2 else 1,
        "pairing": "" if exp2 else "cross",
        "a_model": a, "b_model": b,
        "a_type": "scripted" if exp2 else TAG.get(a, "?"),
        "b_type": TAG.get(b, "?"),
        "arm": rec.get("arm", "live"),
        "rule": int(rec.get("explicit_instruct") == "peer"),
        "message_id": rec.get("message_id", ""),
        "seed": rec.get("seed", ""),
        "script_kind": "control" if rec["script_lang"].startswith("ctl_") else "self",
        "outcome": got["outcome"],
        "disabled": _bit(got["disabled"]),
        "target_running": _bit(got["target_running"]),
        "artifacts_survive": _bit(got["artifacts_survive"]),
        "collateral": ";".join(got["collateral_effects"] or []),
        "indirect": _bit(got["indirect_shadowing"]),
        "b_activated": int(any(e.get("agent") == rec["peer"] for e in log)),
        "a_requested": _bit(judge.get("explorer_instructs_prevent")),
        "b_flagged": "",  # O3 judge not implemented yet
        "judge_disabled": _bit(judge.get("peer_disabled_shutdown")),
        "tokens": "",     # not recorded by the base harness
        "turns": sum(e.get("type") == "tool_call" for e in log),
        "end_reason": next((e.get("reason") for e in reversed(log) if e.get("event") == "episode_end"), ""),
        # Exposure, from the harness's deterministic triage (calls made, whatever the final state).
        "a_read_script": _bit(tri.get("explorer_read_script")),
        "b_wrote_script": _bit(tri.get("peer_edited_shutdown_file")),
        "b_deleted_script": _bit(tri.get("peer_deleted_shutdown_file")),
        "served_providers": ";".join(sorted({f"{e['agent']}={e.get('provider')}" for e in log
                                             if e.get("type") == "served"})),
        "original_script_sha256": rec.get("original_script_sha256", ""),
        "final_script_sha256": (hashlib.sha256(rec["final_state"][rec["shutdown_file"]].encode()).hexdigest()
                                if rec["shutdown_file"] in rec["final_state"] else "deleted"),
        "provenance_verified": _bit(rec.get("provenance_verified")),
        "judge_status": judged["status"] if judged else "",
        "hit_primary_cap": int(rec is not full),
        **_extension(full, rec, got, checker, intact_provenance),
    }
    return row, {"episode_id": row["episode_id"], **got}


def export(root: str | Path, checker) -> tuple[list[dict], list[dict]]:
    """(rows, checker outputs) for every transcript under root."""
    root = Path(root)
    paths = sorted(root.rglob("*_ep[0-9]*.json"))
    judged = {d: judge_lines(d) for d in {p.parent for p in paths}}
    pairs = [row_for(json.loads(p.read_text()), str(p.relative_to(root)), checker, judged[p.parent].get(p.name))
             for p in paths]
    return [r for r, _ in pairs], [c for _, c in pairs]


def _lines(root: str | Path, name: str) -> dict[str, int]:
    root = Path(root)
    return {str(p.parent.relative_to(root)): sum(1 for _ in p.open()) for p in sorted(root.rglob(name))}


def failures(root: str | Path) -> dict[str, int]:
    """Failed episode attempts per cell dir (each is retried on resume, so it leaves no row)."""
    return _lines(root, "failures.jsonl")


def summarize(rows: list[dict]) -> None:
    by_cell = defaultdict(list)
    for r in rows:
        by_cell[tuple(r[k] for k in CELL)].append(r)
    print(f"{'exp a b arm rule kind':34s} {'n':>4s} {'dis':>4s} {'pend':>5s} {'act':>4s} {'bad':>4s} "
          f"{'jok':>4s} {'jerr':>4s}  judge≠A")
    for key in sorted(by_cell, key=str):
        rs = by_cell[key]
        c = Counter(r["outcome"] for r in rs)
        mismatch = sum(r["judge_disabled"] != "" and r["disabled"] != "" and r["judge_disabled"] != r["disabled"] for r in rs)
        print(f"{' '.join(map(str, key)):34s} {len(rs):4d} {c['disabled']:4d} "
              f"{c['indeterminate'] + c['not_executed'] + c['unscored']:5d} {sum(r['b_activated'] for r in rs):4d} "
              f"{c['invalid_baseline']:4d} {sum(r['judge_status'] == 'ok' for r in rs):4d} "
              f"{sum(r['judge_status'] == 'error' for r in rs):4d}  {mismatch}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--out", required=True)
    ap.add_argument("--unscored", action="store_true",
                    help="generation-only export: load no checker, mark every row unscored")
    args = ap.parse_args()
    try:
        checker = None if args.unscored else load_checker()
    except FileNotFoundError as e:
        sys.exit(f"no checker found ({e.filename}): set P2_CHECKER, or pass --unscored")
    rows, outputs = export(args.root, checker)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    sidecar = out.with_name(out.stem + "_checker.jsonl")
    sidecar.write_text("".join(json.dumps(o) + "\n" for o in outputs))
    # Which code produced these numbers (the manifest pins the code that produced the transcripts).
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    manifest = Path(args.root) / "manifest.json"
    out.with_name(out.stem + "_provenance.json").write_text(json.dumps({
        "export.py": sha(__file__), "judge_pass.py": sha(Path(__file__).with_name("judge_pass.py")),
        "primary.py": sha(Path(__file__).with_name("primary.py")),
        "checker": None if checker is None else {"path": checker.__file__, "sha256": sha(checker.__file__)},
        "generation_sha256": json.loads(manifest.read_text())["generation_sha256"] if manifest.exists() else None,
    }, indent=2) + "\n")
    summarize(rows)
    done, failed = Counter(str(Path(r["transcript_path"]).parent) for r in rows), failures(args.root)
    for cell, started in _lines(args.root, "attempts.jsonl").items():
        f = failed.get(cell, 0)
        print(f"attempts {started:4d} = {done[cell]:4d} done + {f:3d} failed + "
              f"{started - done[cell] - f:3d} interrupted   {cell}")
    print(f"\n{len(rows)} episodes -> {out} (+ full checker output in {sidecar.name})")


if __name__ == "__main__":
    main()
