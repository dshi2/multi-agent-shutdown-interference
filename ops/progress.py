"""Live progress of a P2 phase: per-cell bars, active slots, throughput, ETA. Counts only, no outcomes.

  .venv/bin/python ops/progress.py transcripts/p2_core/pilot            # refresh every 10 s
  .venv/bin/python ops/progress.py transcripts/p2_core/pilot --once     # print once

Read-only: it reads the manifest, transcript file names, attempts.jsonl, failures.jsonl,
launcher logs and slot locks. It never opens a transcript, so it cannot show behaviour.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "p2"))
from ops_status import RETRY, held_slots  # noqa: E402

WIDTH = 30


def bar(done: int, failed: int, intr: int, n: int) -> str:
    if n <= 0:
        return " " * WIDTH
    cells = [("█", done), ("x", failed), ("~", intr)]
    out = ""
    for ch, k in cells:
        out += ch * round(WIDTH * min(k, n) / n)
    return (out + "·" * WIDTH)[:WIDTH]


def snapshot(phase: Path, window_min: float) -> str:
    now = time.time()
    m = json.loads((phase / "manifest.json").read_text())
    planned = {c["name"]: c["n"] for c in m["cells"]}
    lines, tot = [], Counter()
    ends: list[float] = []
    for cell in sorted(planned):
        d = phase / cell
        t = [p.stat().st_mtime for p in d.rglob("*_ep[0-9]*.json")] if d.exists() else []
        ends += t
        started = sum(1 for f in d.rglob("attempts.jsonl") for _ in f.open()) if d.exists() else 0
        failed = sum(1 for f in d.rglob("failures.jsonl") for _ in f.open()) if d.exists() else 0
        done = len(t)
        live = max(0, started - done - failed)
        n = planned[cell]
        tot.update(n=n, done=done, failed=failed, live=live)
        lines.append(f"  {cell:18s} [{bar(done, failed, live, n)}] {done:4d}/{n:<4d} "
                     f"fail {failed:3d}  running/interrupted {live:3d}")
    held, pool = held_slots(phase)
    retries = Counter()
    for log in phase.rglob("launcher.log"):
        for line in log.open(errors="replace"):
            if (r := RETRY.search(line)):
                retries[r.group(1)] += 1
    recent = [x for x in ends if now - x <= window_min * 60]
    rate = len(recent) / window_min
    remaining = tot["n"] - tot["done"]
    eta = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=remaining / rate)).strftime("%H:%M UTC") \
        if rate > 0 and remaining > 0 else ("done" if remaining == 0 else "n/a")
    ops = m.get("operational_by_launch", [])
    head = [f"P2 {phase.name}   {dt.datetime.now(dt.timezone.utc):%H:%M:%S} UTC   "
            f"max_active {ops[-1]['max_active'] if ops else '?'}   active slots {held}",
            f"  total              [{bar(tot['done'], tot['failed'], tot['live'], tot['n'])}] "
            f"{tot['done']:4d}/{tot['n']:<4d} fail {tot['failed']:3d}  running/interrupted {tot['live']:3d}",
            f"  throughput (last {window_min:g} min) {rate:.2f} episodes/min   ETA {eta}   "
            f"retries {dict(retries) or 'none'}",
            "  █ finished  x failed  ~ running or interrupted  · not started", ""]
    return "\n".join(head + lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("phase_dir", type=Path)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--every", type=float, default=10.0)
    ap.add_argument("--window", type=float, default=10.0, help="minutes for the throughput rate")
    a = ap.parse_args()
    while True:
        try:
            s = snapshot(a.phase_dir, a.window)
        except FileNotFoundError:
            s = f"waiting for {a.phase_dir}/manifest.json ..."
        if a.once:
            print(s)
            return 0
        print("\033[2J\033[H" + s, flush=True)
        time.sleep(a.every)


if __name__ == "__main__":
    raise SystemExit(main())
