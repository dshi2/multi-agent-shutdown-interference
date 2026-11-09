"""Run a command and stop it at a fixed UTC time.

  .venv/bin/python ops/run_until.py 2026-11-09T07:30Z -- .venv/bin/python p2/run_core.py --phase pilot --go --max-active 20

The deadline is when every process of the command is gone. The command runs in its own
process group; --grace seconds before the deadline (default 120) it gets SIGTERM
(p2/run_core.py then stops every worker and logs interrupted attempts); when it exits, or at
the deadline at the latest, every process left in its group gets SIGKILL. Ctrl-C starts the
same shutdown at once. A command is not started if less than --grace seconds remain. The exit
status is the command's (128 + N if it died from signal N).
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import signal
import subprocess
import sys
import time


def parse_utc(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("deadline must carry a timezone, e.g. 2026-11-09T07:30Z")
    return t


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def stop(p: subprocess.Popen, by: dt.datetime) -> None:
    """SIGTERM, then SIGKILL to the whole group once the command exits or `by` arrives."""
    if p.poll() is None:
        p.send_signal(signal.SIGTERM)
        try:
            p.wait(timeout=max(0.0, (by - now()).total_seconds()))
        except subprocess.TimeoutExpired:
            pass
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    p.wait()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--" not in argv:
        sys.exit("usage: run_until.py DEADLINE_UTC [--grace S] -- COMMAND ...")
    i = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("deadline")
    ap.add_argument("--grace", type=float, default=120.0)
    a = ap.parse_args(argv[:i])
    cmd = argv[i + 1:]
    deadline = parse_utc(a.deadline)
    if not cmd:
        sys.exit("no command given")
    term_at = deadline - dt.timedelta(seconds=a.grace)
    if now() >= term_at:
        sys.exit(f"less than {a.grace:g}s before the deadline {deadline.isoformat()}; nothing started")
    p = subprocess.Popen(cmd, start_new_session=True)

    def on_signal(signum, frame):
        print(f"[run_until] signal {signum}: stopping the command", file=sys.stderr, flush=True)
        stop(p, min(deadline, now() + dt.timedelta(seconds=a.grace)))
        sys.exit(status(p.returncode))

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, on_signal)
    print(f"[run_until] pid {p.pid}; SIGTERM at {term_at.isoformat()}, all stopped by {deadline.isoformat()}",
          file=sys.stderr, flush=True)
    while p.poll() is None and now() < term_at:
        time.sleep(0.2)
    if p.poll() is None:
        print(f"[run_until] {term_at.isoformat()} reached: stopping the command (deadline {deadline.isoformat()})",
              file=sys.stderr, flush=True)
    stop(p, deadline)
    return status(p.returncode)


def status(rc: int | None) -> int:
    return 130 if rc is None else 128 - rc if rc < 0 else rc


if __name__ == "__main__":
    raise SystemExit(main())
