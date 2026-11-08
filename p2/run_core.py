"""Launch the P2 sprint core (spec section 0). Prints the plan unless --go is given.

  .venv/bin/python p2/run_core.py --phase pilot          # show what would run
  .venv/bin/python p2/run_core.py --phase pilot --go     # run it (needs OPENROUTER_API_KEY)

Cells advance together in rounds: each round takes every cell up to its next
cumulative target (about ROUND episodes; smaller cells proportionally fewer), in a
cell order reshuffled per round with a fixed seed, so provider or model drift over
the run lands on every arm alike instead of on whichever cell ran last. Each step is
a run_experiment.py invocation with --resume, so an interrupted phase is simply
relaunched; the manifest pins the schedule and the generation code, and a relaunch
that does not match them is refused. The spend cap is the credit limit set on the
OpenRouter key itself.

Operational settings decide when episodes run, never what they contain, so they are
kept out of the manifest check, may change between launches, and are logged per launch
(operational_by_launch):
  --max-active N     global limit: at most N active episodes across all cells (p2/slots.py)
  --concurrency K    threads per cell (default: N, so the global limit is what binds)
  --parallel-cells P cells of a round run at once (default 0 = all of them)
To back off (e.g. 70 -> 50 -> 30), stop the launcher and relaunch with a smaller --max-active.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import random
import signal
import subprocess
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import slots as p2_slots  # same directory (p2/)

REPO = Path(__file__).resolve().parent.parent
R = "google/gemini-3.1-pro-preview"   # resistant: 99/100 in the paper
C = "anthropic/claude-sonnet-5"       # compliant: 1/100 in the paper
POOL = "p2/pool_core.jsonl"
SIZES = {"pilot": {"exp1": 5, "ctl": 0, "exp2": 5},
         "main": {"exp1": 120, "ctl": 30, "exp2": 120}}
EXP2_CELLS = [("REQ_plain", 0), ("INFO", 0), ("CONTACT", 0), ("REQ_plain", 1), ("INFO", 1)]
TAG = {R: "R", C: "C"}
PROVIDERS = {R: "google-ai-studio", C: "anthropic"}  # first-party backends, fallbacks off
ROUND = 10  # episodes per largest cell per round
MAX_ROUNDS = 12  # spec v1.12: larger cells get bigger rounds, not more of them
MAX_HANDOFFS, PRIMARY_CAP = 60, 20  # spec v1.12: run to 60, score the primary outcome at the paper's 20
PRIMARY = ("e1_RxC", "e1_CxC", "e2_REQ_plain_r0", "e2_INFO_r0")  # cells of the two primary contrasts
PRIMARY_N = (120, 240, 500)  # main-phase sizes for PRIMARY, chosen by the spec's throughput rule


def cells(phase: str, primary_n: int | None = None) -> list[tuple[str, int, list[str]]]:
    """(cell name, episodes, run_experiment args) for every cell of a phase."""
    out = _cells(phase)
    if primary_n is None:
        return out
    if phase != "main" or primary_n not in PRIMARY_N:
        raise ValueError(f"primary_n is a main-phase size in {PRIMARY_N}")
    return [(name, primary_n if name in PRIMARY else n, args) for name, n, args in out]


def _cells(phase: str) -> list[tuple[str, int, list[str]]]:
    n = SIZES[phase]
    out = []
    for a in (R, C):
        for b in (R, C):
            team = ["--model", a, "--explorer-model", a, "--peer-model", b]
            name = f"e1_{TAG[a]}x{TAG[b]}"
            out.append((name, n["exp1"], team + ["--script-lang", "weight_registry_purge"]))
            if n["ctl"]:
                out.append((name + "_ctl", n["ctl"], team + ["--script-lang", "ctl_data_purge_high"]))
    for arm, rule in EXP2_CELLS:
        args = ["--model", C, "--peer-model", C, "--script-lang", "weight_registry_purge",
                "--exp2-pool", POOL, "--arm", arm, "--message-id", "fixed"]
        out.append((f"e2_{arm}_r{rule}", n["exp2"], args + (["--explicit-instruct", "peer"] if rule else [])))
    return out


def command(phase: str, name: str, n: int, args: list[str], root: str, judges: bool) -> list[str]:
    """The experimental command for a cell: everything that fixes what its episodes are."""
    seed = zlib.crc32(f"{phase}/{name}".encode())
    return [sys.executable, "run_experiment.py", *args, "--n", str(n), "--seed", str(seed),
            "--resume", "--outdir", f"{root}/{phase}/{name}",
            "--no-early-stop", "--max-handoffs", str(MAX_HANDOFFS), "--primary-cap", str(PRIMARY_CAP),
            *[f"--provider={m}={slug}" for m, slug in PROVIDERS.items()],
            *([] if judges else ["--no-judges"])]


def operational(root: str, phase: str, concurrency: int, max_active: int) -> list[str]:
    """Flags that only decide when episodes run: logged per launch, not checked."""
    return ["--concurrency", str(concurrency), "--slot-dir", str(REPO / root / phase / ".slots"),
            "--slots", str(max_active), "--watch-parent"]


def attempts(cell_dir: Path) -> int:
    """Episode attempts started in a cell: finished, failed and interrupted alike."""
    return sum(1 for f in cell_dir.rglob("attempts.jsonl") for _ in f.open())


def finished(cell_dir: Path) -> int:
    return sum(1 for _ in cell_dir.rglob("*_ep[0-9]*.json"))


def schedule(phase: str, plan: list) -> list[list[tuple[str, int]]]:
    """Rounds of (cell, cumulative episode target), each round in its own fixed shuffle."""
    rounds = min(MAX_ROUNDS, max(-(-n // ROUND) for _, n, _ in plan))
    out = []
    for k in range(rounds):
        order = [(name, -(-n * (k + 1) // rounds)) for name, n, _ in plan if n]
        random.Random(f"p2-core-{phase}-round{k}").shuffle(order)
        out.append(order)
    return out


# Everything that shapes what the agents see or do. Scoring code (checker, export) is
# deliberately excluded: it may change after generation without invalidating a phase.
GENERATION_FILES = ["run_experiment.py", "harness.py", "env.py", "prompts.py", "judges.py",
                    "p2/scripted.py", "p2/provenance.py", "p2/run_core.py", "p2/slots.py", POOL]


def generation_sha256() -> str:
    code = hashlib.sha256()
    for rel in GENERATION_FILES:
        code.update(rel.encode() + b"\0" + (REPO / rel).read_bytes())
    return code.hexdigest()


def write_manifest(phase: str, plan: list, rounds: list, root: str, judges: bool) -> Path:
    """Pin models, schedule, commands and generation code; refuse a relaunch that differs."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "phase": phase,
        "models": {"R": R, "C": C},
        "python": sys.version.split()[0],
        "generation_sha256": generation_sha256(),
        "pool_sha256": hashlib.sha256((REPO / POOL).read_bytes()).hexdigest(),
        "cells": [{"name": name, "n": n,
                   "command": command(phase, name, n, args, root, judges)[1:]}
                  for name, n, args in plan],
        "schedule": [[list(step) for step in rnd] for rnd in rounds],
    }
    path = REPO / root / phase / "manifest.json"
    if path.exists():
        old = json.loads(path.read_text())
        changed = [k for k in manifest if k != "python" and old.get(k) != manifest[k]]
        if changed:
            sys.exit(f"{path} differs in {changed}: refusing to resume this phase with a different "
                     "plan or generation code (use a new --root to start a separate run)")
        manifest["launches_utc"] = old["launches_utc"] + [now]
        manifest["operational_by_launch"] = old.get("operational_by_launch", [])
    else:
        manifest["launches_utc"] = [now]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=SIZES, required=True)
    ap.add_argument("--root", default="transcripts/p2_core")
    ap.add_argument("--max-active", type=int, default=70,
                    help="global limit on active episodes across all cells (operational; default 70)")
    ap.add_argument("--concurrency", type=int, default=None,
                    help="threads per cell (operational; default: --max-active)")
    ap.add_argument("--judges", action="store_true", help="also run the paper's LLM judges (extra cost)")
    ap.add_argument("--go", action="store_true", help="actually run; without it, only print the plan")
    ap.add_argument("--parallel-cells", type=int, default=0,
                    help="cells of a round run at once (operational; 0 = all). Rounds stay barriers, so "
                    "every cell is balanced at a round boundary")
    ap.add_argument("--primary-n", type=int, choices=PRIMARY_N,
                    help="main phase only: episodes in each primary cell (spec v1.12 throughput rule)")
    args = ap.parse_args()
    if args.primary_n is not None and args.phase != "main":
        sys.exit("--primary-n applies to the main phase only")
    if args.max_active < 1 or (args.concurrency is not None and args.concurrency < 1) or args.parallel_cells < 0:
        sys.exit("--max-active and --concurrency must be >= 1, --parallel-cells >= 0")
    concurrency = args.concurrency or args.max_active

    plan = cells(args.phase, args.primary_n)
    rounds = schedule(args.phase, plan)
    for name, n, _ in plan:
        print(f"  {name:18s} {n:4d} episodes")
    print(f"{args.phase}: {len(plan)} cells, {sum(n for _, n, _ in plan)} episodes, "
          f"{len(rounds)} round(s); first round order: {[name for name, _ in rounds[0]]}")
    if not args.go:
        print("dry run: add --go to execute")
        return
    if not os.environ.get("OPENROUTER_API_KEY"):
        sys.exit("OPENROUTER_API_KEY is not set in this shell")

    # One launcher per phase; each cell process also locks its own dir (p2/slots.py).
    _phase_lock = p2_slots.hold_exclusive(REPO / args.root / args.phase / ".launch.lock",  # noqa: F841
                                          f"a launcher for {args.root}/{args.phase}")
    path = write_manifest(args.phase, plan, rounds, args.root, args.judges)
    print("manifest:", path)
    manifest = json.loads(path.read_text())  # operational settings per launch, for the record
    op = {"utc": manifest["launches_utc"][-1], "max_active": args.max_active,
          "concurrency_per_cell": concurrency, "parallel_cells": args.parallel_cells}
    manifest["operational_by_launch"] = manifest.get("operational_by_launch", []) + [op]
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print("operational:", op)
    cell_args = {name: a for name, _, a in plan}
    cell_n = {name: n for name, n, _ in plan}
    failed, stopped = [], set()
    children: set[subprocess.Popen] = set()

    def stop(signum, _frame):  # no orphan workers: stop every cell process, then exit
        for c in list(children):
            if c.poll() is None:
                c.terminate()
        for c in list(children):
            try:
                c.wait(timeout=30)
            except subprocess.TimeoutExpired:
                c.kill()
        print(f"\n>>> {signal.Signals(signum).name}: launcher stopped; relaunch the same command to resume",
              file=sys.stderr, flush=True)
        os._exit(128 + signum)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    def run_cell(k: int, name: str, target: int) -> int:
        cmd = (command(args.phase, name, target, cell_args[name], args.root, args.judges)
               + operational(args.root, args.phase, concurrency, args.max_active))
        cell_dir = REPO / args.root / args.phase / name
        cell_dir.mkdir(parents=True, exist_ok=True)
        with open(cell_dir / "launcher.log", "a") as out:  # one log per cell
            c = subprocess.Popen(cmd, cwd=REPO, stdout=out, stderr=subprocess.STDOUT)
            children.add(c)
            try:
                return c.wait()
            finally:
                children.discard(c)

    for k, rnd in enumerate(rounds):
        todo = []
        for name, target in rnd:
            if attempts(REPO / args.root / args.phase / name) >= 2 * cell_n[name]:
                stopped.add(name)  # spec section 0: stop a cell after 2n attempts
                continue
            print(f"\n=== round {k + 1}/{len(rounds)}: {name} up to {target} episodes", flush=True)
            todo.append((name, target))
        with ThreadPoolExecutor(max_workers=args.parallel_cells or max(1, len(todo))) as ex:  # round = barrier
            codes = list(ex.map(lambda nt: run_cell(k, *nt), todo))
        failed += [(k + 1, name) for (name, _), code in zip(todo, codes) if code != 0]  # retried next round
    # run_experiment logs a failed episode and carries on (exit 0), so completeness is
    # read from the transcripts, not from exit codes.
    short = {name: f"{finished(REPO / args.root / args.phase / name)}/{n}" for name, n in cell_n.items()
             if finished(REPO / args.root / args.phase / name) < n}
    print("\ncrashed (round, cell) invocations:", failed or "none")
    print("cells stopped at 2n attempts:", sorted(stopped) or "none")
    print("incomplete cells (done/planned; relaunch to retry):", short or "none")
    sys.exit(1 if failed or short else 0)


if __name__ == "__main__":
    main()
