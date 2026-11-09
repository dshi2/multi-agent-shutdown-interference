"""ops/run_until.py stops a command at the deadline, escalating to SIGKILL after the grace period.

  .venv/bin/python ops/test_run_until.py   -> RUN_UNTIL TEST PASSED
"""
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

W = [sys.executable, str(Path(__file__).resolve().parent / "run_until.py")]


def at(seconds: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=seconds)).isoformat()


def alive(pid: int) -> bool:
    import os
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()[:1] != "Z"


def run(deadline, *cmd, grace="2"):
    t = time.time()
    r = subprocess.run(W + [deadline, "--grace", grace, "--"] + list(cmd), capture_output=True, text=True, timeout=60)
    return r, time.time() - t


def main() -> int:
    r, el = run(at(30), sys.executable, "-c", "print('done')")
    assert r.returncode == 0 and "done" in r.stdout and el < 10, (r, el)
    r, el = run(at(2), sys.executable, "-c",
                "import signal, sys, time\n"
                "signal.signal(signal.SIGTERM, lambda *a: (print('term', flush=True), sys.exit(7)))\n"
                "time.sleep(60)")
    assert r.returncode == 7 and "term" in r.stdout and el < 10, (r.returncode, r.stdout, el)
    r, el = run(at(2), sys.executable, "-c",
                "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)", grace="1")
    assert r.returncode == 137 and el < 10, (r.returncode, el)
    tree = ("import signal, subprocess, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "c = subprocess.Popen([sys.executable, '-c', 'import signal, time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])\n"
            "print(c.pid, flush=True)\ntime.sleep(60)")
    r, el = run(at(2), sys.executable, "-c", tree, grace="1")
    child = int(r.stdout.split()[0])
    time.sleep(0.5)
    assert r.returncode == 137 and el < 10 and not alive(child), (r.returncode, el, child)
    r, _ = run("2020-01-01T00:00Z", sys.executable, "-c", "print('ran')")
    assert r.returncode != 0 and "ran" not in r.stdout and "already passed" in r.stderr
    r, _ = run("2026-11-09T07:30", sys.executable, "-c", "print('ran')")
    assert r.returncode != 0 and "ran" not in r.stdout and "timezone" in r.stderr
    print("RUN_UNTIL TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
