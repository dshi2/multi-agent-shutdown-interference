"""The deadline wrapper on the real launcher (p2/run_core.py and its run_experiment.py workers),
with test_launch's fake API: no network, no cost.

  .venv/bin/python ops/test_deadline_live.py   -> DEADLINE LIVE TEST PASSED

A pilot launched through ops/run_until.py is stopped at a deadline mid-phase. Checks: no process
of the launch survives; every started attempt is logged; a plain relaunch completes exactly the
planned episodes, none duplicated, no half-written transcript.
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "p2"))
import test_launch as T  # noqa: E402


def group_members(pgid: int) -> list[str]:
    out = subprocess.run(["ps", "-axo", "pid=,pgid=,stat=,command="], capture_output=True, text=True).stdout
    return [ln for ln in out.splitlines()
            if len(f := ln.split(None, 3)) == 4 and f[1] == str(pgid) and not f[2].startswith("Z")]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p2deadline_") as d:
        td = Path(d)
        (td / "fake").mkdir()
        (td / "fake" / "sitecustomize.py").write_text(T.FAKE)
        b = T.Bench(td, "deadline", FAKE_DELAY="1.0")
        deadline = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=16)).isoformat()
        t0 = time.time()
        r = subprocess.run([sys.executable, str(HERE / "run_until.py"), deadline, "--grace", "4", "--",
                            *b.argv("--max-active", "4")], cwd=T.REPO, env=b.env,
                           capture_output=True, text=True, timeout=300)
        el = time.time() - t0
        pid = int(re.search(r"\[run_until\] pid (\d+)", r.stderr).group(1))
        time.sleep(1)
        survivors = group_members(pid) + [ln for ln in subprocess.run(
            ["ps", "-axo", "command="], capture_output=True, text=True).stdout.splitlines() if str(b.root) in ln]
        done = len(T.transcripts(b.phase))
        T.check(f"stopped by the deadline mid-phase ({done}/45 transcripts, {el:.0f}s)",
                "stopping the command" in r.stderr and 0 < done < 45 and el < 16 + 2)
        T.check("no launcher or worker process survives the deadline", not survivors)
        starts = sum(1 for f in b.phase.rglob("attempts.jsonl") for _ in open(f))
        T.check(f"every started attempt logged ({starts} started, {done} finished)", starts >= done)
        T.check("relaunch after the deadline stop completes", b.launch().returncode == 0)
        e = T.transcripts(b.phase)
        T.check("exactly the planned episodes, none duplicated",
                set(e) == b.planned() and all(len(v) == 1 for v in e.values()))
        T.check("no half-written transcript left", not list(b.phase.rglob("*.tmp")))
        per_cell = Counter(k[0] for k in e)
        T.check("every cell complete after resume", set(per_cell.values()) == {5})
    print("DEADLINE LIVE TEST " + ("PASSED" if not T.FAILS else f"FAILED: {T.FAILS}"))
    return 1 if T.FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
