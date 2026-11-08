"""Operational status of a running P2 phase: throughput, active episodes, retries, failures.
Read-only; for deciding whether to back off --max-active (e.g. 70 -> 50 -> 30).

  .venv/bin/python p2/ops_status.py transcripts/p2_core/pilot [--window 15]

Back off when completed episodes per minute stop rising (or fall) while rate-limit
retries, timeouts or failures climb. Never on behavioural outcomes.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import time
from collections import Counter
from pathlib import Path

RETRY = re.compile(r"\[harness\] (\w+):.*retry (\d+)/(\d+)")


def held_slots(phase: Path) -> tuple[int, int]:
    files = sorted((phase / ".slots").glob("slot*.lock"))
    held = 0
    for f in files:
        fd = os.open(f, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        except BlockingIOError:
            held += 1
        finally:
            os.close(fd)
    return held, len(files)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phase_dir", type=Path)
    ap.add_argument("--window", type=float, default=15.0, help="minutes for rates")
    a = ap.parse_args()
    now, win = time.time(), a.window * 60
    done = [p.stat().st_mtime for p in a.phase_dir.rglob("*_ep[0-9]*.json")]
    recent = [t for t in done if now - t <= win]
    started = sum(1 for f in a.phase_dir.rglob("attempts.jsonl") for _ in f.open())
    failures = [json.loads(x) for f in a.phase_dir.rglob("failures.jsonl") for x in f.open()]
    retries, recent_retries = Counter(), Counter()
    for log in a.phase_dir.rglob("launcher.log"):
        fresh = now - log.stat().st_mtime <= win
        for line in log.open(errors="replace"):
            m = RETRY.search(line)
            if m:
                retries[m.group(1)] += 1
                if fresh:
                    recent_retries[m.group(1)] += 1
    held, pool = held_slots(a.phase_dir)
    ops = json.loads((a.phase_dir / "manifest.json").read_text()).get("operational_by_launch", [])
    print(f"phase: {a.phase_dir}")
    print(f"current settings: {ops[-1] if ops else 'none logged'}")
    limit = ops[-1]["max_active"] if ops else pool  # slot files are created on demand
    print(f"active episodes (held slots): {held}; global limit {limit}")
    print(f"finished: {len(done)}   started attempts: {started}   failed attempts: {len(failures)}   "
          f"interrupted or running: {started - len(done) - len(failures)}")
    print(f"throughput, last {a.window:g} min: {len(recent) / a.window:.2f} episodes/min")
    print(f"retries, all: {dict(retries) or 'none'}")
    print(f"retries in logs written in the last {a.window:g} min (approximate): {dict(recent_retries) or 'none'}")
    if failures:
        print("recent failures:", [f["error"][:120] for f in failures[-3:]])


if __name__ == "__main__":
    main()
