"""Run a command and stop it at a fixed UTC time.

  .venv/bin/python ops/run_until.py 2026-11-09T07:30Z -- .venv/bin/python p2/run_core.py --phase pilot --go --max-active 20

At the deadline the command gets SIGTERM (p2/run_core.py then stops every worker and logs
interrupted attempts); if it is still alive after --grace seconds it gets SIGKILL. Ctrl-C is
passed to the command the same way. The exit status is the command's (128 + N if it died
from signal N).
"""
from __future__ import annotations

import argparse
import datetime as dt
import signal
import subprocess
import sys
import time


def parse_utc(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("deadline must carry a timezone, e.g. 2026-11-09T07:30Z")
    return t


def stop(p: subprocess.Popen, grace: float) -> None:
    if p.poll() is None:
        p.send_signal(signal.SIGTERM)
        try:
            p.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            p.kill()
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
    if dt.datetime.now(dt.timezone.utc) >= deadline:
        sys.exit(f"deadline {deadline.isoformat()} has already passed; nothing started")
    p = subprocess.Popen(cmd, start_new_session=True)

    def on_signal(signum, frame):
        print(f"[run_until] signal {signum}: stopping the command", file=sys.stderr, flush=True)
        stop(p, a.grace)
        sys.exit(status(p.returncode))

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, on_signal)
    print(f"[run_until] pid {p.pid}; hard stop at {deadline.isoformat()}", file=sys.stderr, flush=True)
    while p.poll() is None:
        if dt.datetime.now(dt.timezone.utc) >= deadline:
            print(f"[run_until] deadline {deadline.isoformat()} reached: stopping the command",
                  file=sys.stderr, flush=True)
            stop(p, a.grace)
            break
        time.sleep(1)
    return status(p.returncode)


def status(rc: int | None) -> int:
    return 130 if rc is None else 128 - rc if rc < 0 else rc


if __name__ == "__main__":
    raise SystemExit(main())
