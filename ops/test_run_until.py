"""ops/run_until.py: SIGTERM at deadline - grace, and nothing of the command alive after the deadline.

  .venv/bin/python ops/test_run_until.py   -> RUN_UNTIL TEST PASSED
"""
import datetime as dt
import os
import subprocess
import sys
import time
from pathlib import Path

W = [sys.executable, str(Path(__file__).resolve().parent / "run_until.py")]
SLACK = 1.5  # interpreter start-up and polling


def at(seconds: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=seconds)).isoformat()


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()[:1] != "Z"


def run(seconds, *cmd, grace="2", deadline=None):
    t = time.time()
    r = subprocess.run(W + [deadline or at(seconds), "--grace", grace, "--"] + list(cmd),
                       capture_output=True, text=True, timeout=60)
    return r, time.time() - t


def main() -> int:
    r, el = run(30, sys.executable, "-c", "print('done')")
    assert r.returncode == 0 and "done" in r.stdout and el < 10, (r, el)
    # handles SIGTERM: stops at deadline - grace
    r, el = run(4, sys.executable, "-c",
                "import signal, sys, time\n"
                "signal.signal(signal.SIGTERM, lambda *a: (print('term', flush=True), sys.exit(7)))\n"
                "time.sleep(60)")
    assert r.returncode == 7 and "term" in r.stdout and el < 4 - 2 + SLACK, (r.returncode, r.stdout, el)
    # ignores SIGTERM: killed at the deadline, not later
    r, el = run(3, sys.executable, "-c",
                "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)", grace="1")
    assert r.returncode == 137 and el < 3 + SLACK, (r.returncode, el)
    # a process tree where nobody handles SIGTERM: the whole group is gone by the deadline
    tree = ("import signal, subprocess, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "c = subprocess.Popen([sys.executable, '-c', 'import signal, time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])\n"
            "print(c.pid, flush=True)\ntime.sleep(60)")
    r, el = run(3, sys.executable, "-c", tree, grace="1")
    child = int(r.stdout.split()[0])
    time.sleep(0.3)
    assert r.returncode == 137 and el < 3 + SLACK and not alive(child), (r.returncode, el, child)
    # refusals: deadline passed, less than grace left, no timezone
    for args, msg in [(("2020-01-01T00:00Z", "2"), "less than"), ((at(1), "5"), "less than"),
                      (("2026-11-09T07:30", "2"), "timezone")]:
        r = subprocess.run(W + [args[0], "--grace", args[1], "--", sys.executable, "-c", "print('ran')"],
                           capture_output=True, text=True, timeout=30)
        assert r.returncode != 0 and "ran" not in r.stdout and msg in r.stderr, (args, r.stderr)
    print("RUN_UNTIL TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
