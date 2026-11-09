"""Run the paper's semantic judges over saved P2 transcripts, after generation (spec section 8).

  .venv/bin/python p2/judge_pass.py transcripts/p2_core/pilot --dry-run   # count what would be judged
  .venv/bin/python p2/judge_pass.py transcripts/p2_core/pilot             # needs OPENROUTER_API_KEY

Generation runs with --no-judges: a judge error inside generation would fail the
episode, and the retry would condition the data on the judge. This pass calls the same
judge_episode() on each saved transcript with run_judges=True and appends one line per
transcript to the cell's judges.jsonl. Transcripts are never modified.

Every judge call is captured (prompt, reply, parse status). If any call in an episode
failed or did not parse, the line has status "error" and no verdicts: the upstream
judges fall back to False on failure, and here a failure stays missing data instead of
becoming a "no". Rerunning judges only transcripts without an "ok" line, so the pass can
follow a running phase round by round. Each line also records the model and provider
that served every judge call, and the SHA-256 of the scoring code that produced it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))  # the harness modules are imported where used, so export.py can read logs cheaply

LOG = "judges.jsonl"  # per cell dir; does not match the *_epNN.json transcript glob
VERDICTS = ("explorer_mentions_shutdown", "explorer_instructs_prevent", "explorer_instructs_prevent_quote",
            "peer_modified_script", "peer_disabled_shutdown", "peer_edited_not_disabling",
            "explorer_construal", "peer_construal")
# Everything that decides a verdict: the judge prompts and parsing, judge_episode, target_description.
SCORING_CODE = ("p2/judge_pass.py", "p2/primary.py", "judges.py", "run_experiment.py", "env.py")
_served = threading.local()


def code_sha256(rels=SCORING_CODE) -> dict[str, str]:
    return {rel: hashlib.sha256((REPO / rel).read_bytes()).hexdigest() for rel in rels}


class _RecordServing:
    """Pass-through for chat.completions that notes which model and provider served each call."""

    def __init__(self, inner):
        self._inner = inner

    def create(self, **kw):
        resp = self._inner.create(**kw)
        _served.calls.append({"model": getattr(resp, "model", None), "provider": getattr(resp, "provider", None)})
        return resp


def record_serving() -> None:
    """Route the judges' client through _RecordServing (judges.py itself stays upstream code)."""
    import harness

    if isinstance(harness.get_client().chat.completions, _RecordServing):
        return  # already wrapped
    harness._client = SimpleNamespace(chat=SimpleNamespace(completions=_RecordServing(harness.get_client().chat.completions)))


def latest(cell_dir: Path) -> dict[str, dict]:
    """Transcript file name -> its most recent judges.jsonl line."""
    p = cell_dir / LOG
    return {d["transcript"]: d for d in map(json.loads, p.open())} if p.exists() else {}


def judge_one(path: Path) -> dict:
    from env import target_description
    from judges import JUDGE_MODEL, start_judge_log
    from run_experiment import judge_episode

    from primary import at_primary_cap

    raw = path.read_bytes()  # hashed and parsed from the same bytes
    rec = at_primary_cap(json.loads(raw))  # judge the primary (20-handoff) endpoint
    if rec.get("orchestrator") or rec.get("solo"):
        raise ValueError("the judge pass covers the two-agent P2 arms only")
    calls = start_judge_log(True)  # thread-local; every judge below appends to it
    _served.calls = []
    files = rec["final_state"]
    third_party = rec["target_name"] != rec["explorer"]
    # Not stored in the transcript; rebuilt exactly as run_experiment computes it.
    target_desc = target_description(rec["script_lang"], rec["target_name"], self_target=not third_party)
    verdict = judge_episode(
        rec["log"], rec["explorer"], rec["peer"], rec["original_script"],
        files.get(rec["shutdown_file"], ""), target_desc,
        deleted=rec["shutdown_file"] not in files, run_judges=True, third_party=third_party)
    failed = [c["judge"] for c in calls if c["status"] != "ok"]
    return {"transcript": path.name, "transcript_sha256": hashlib.sha256(raw).hexdigest(),
            "judge_model": JUDGE_MODEL, "status": "error" if failed else "ok",
            "failed_calls": failed, **({} if failed else {"verdicts": {k: verdict.get(k) for k in VERDICTS}}),
            "calls": calls, "served": _served.calls, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def current(line: dict | None, path: Path, code: dict[str, str]) -> bool:
    """A judges.jsonl line counts only if it is ok AND was made from this exact transcript
    content with the current scoring code (judge prompts, model and parsing live in it).
    Codex audit 2026-11-09: the cache was keyed by file name only, so an edited transcript
    or changed judge kept its old verdicts."""
    return bool(line) and line.get("status") == "ok" and line.get("code_sha256") == code \
        and line.get("transcript_sha256") == hashlib.sha256(path.read_bytes()).hexdigest()


def pending(root: Path) -> list[Path]:
    code, lines, out = code_sha256(), {}, []
    for p in sorted(root.rglob("*_ep[0-9]*.json")):
        if p.parent not in lines:
            lines[p.parent] = latest(p.parent)
        if not current(lines[p.parent].get(p.name), p, code):
            out.append(p)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true", help="only count the transcripts still to judge")
    args = ap.parse_args()
    from harness import configure_client
    from judges import JUDGE_MODEL
    from run_experiment import OPENROUTER_URL

    todo = pending(Path(args.root))
    print(f"{len(todo)} transcript(s) to judge with {JUDGE_MODEL}")
    if args.dry_run or not todo:
        return
    if not os.environ.get("OPENROUTER_API_KEY"):
        sys.exit("OPENROUTER_API_KEY is not set in this shell")
    configure_client(OPENROUTER_URL, os.environ["OPENROUTER_API_KEY"])
    record_serving()
    code = code_sha256()
    errors = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {ex.submit(judge_one, p): p for p in todo}
        for fut in as_completed(futures):  # lines are written from this thread only
            p = futures[fut]
            try:
                line = fut.result()
            except Exception as e:  # a broken transcript is reported, not skipped silently
                line = {"transcript": p.name, "judge_model": JUDGE_MODEL, "status": "error",
                        "failed_calls": [repr(e)[:300]], "calls": [],
                        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            line["code_sha256"] = code
            errors += line["status"] != "ok"
            with open(p.parent / LOG, "a") as f:
                f.write(json.dumps(line) + "\n")
            print(f"{line['status']:5s} {p.relative_to(args.root)}")
    print(f"\njudged {len(todo) - errors}, errors {errors} (rerun to retry them)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
