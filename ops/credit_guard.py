"""Stop a running P2 phase cleanly before the OpenRouter balance runs out.

  .venv/bin/python ops/credit_guard.py --min 6 --log ops_logs/credits.jsonl

Polls the account balance (total credits minus total usage) every --every seconds and
appends each reading to --log. When the balance falls below --min dollars it sends SIGTERM
to every ops/run_until.py process, which stops the launcher the documented way: workers
stop and in-flight episodes are logged as interrupted attempts, to be rerun on resume.
Without it, an exhausted balance makes every new attempt fail and count as started.

It waits up to --wait seconds for a run_until process to appear and exits once none is
left. Needs OPENROUTER_API_KEY in the environment; the key is never logged.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

URL = "https://openrouter.ai/api/v1/credits"
TARGET = "ops/run_until.py"


def balance(key: str) -> float:
    req = urllib.request.Request(URL, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.load(r)["data"]
    return float(d["total_credits"]) - float(d["total_usage"])


def targets() -> list[int]:
    out = subprocess.run(["pgrep", "-f", TARGET], capture_output=True, text=True).stdout.split()
    return [int(p) for p in out if int(p) != os.getpid()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=6.0, help="stop below this balance in dollars")
    ap.add_argument("--every", type=float, default=20.0)
    ap.add_argument("--wait", type=float, default=120.0)
    ap.add_argument("--log", required=True)
    ap.add_argument("--once", action="store_true", help="print the balance and exit")
    a = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("OPENROUTER_API_KEY not set")
    if a.once:
        print(f"balance ${balance(key):.2f}")
        return 0
    t0 = time.time()
    while not targets():
        if time.time() - t0 > a.wait:
            print("[credit_guard] no run_until process appeared; exiting", file=sys.stderr)
            return 1
        time.sleep(2)
    while (pids := targets()):
        try:
            b = balance(key)
        except Exception as e:  # a failed poll never stops the run
            b = None
            print(f"[credit_guard] balance check failed: {e}", file=sys.stderr, flush=True)
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(a.log, "a") as f:
            f.write(json.dumps({"utc": now, "balance": b}) + "\n")
        if b is not None and b < a.min:
            print(f"[credit_guard] {now} balance ${b:.2f} < ${a.min:.2f}: stopping the run (SIGTERM to "
                  f"{pids}); add credits, then rerun ops/main_run.sh to resume", file=sys.stderr, flush=True)
            for p in pids:
                try:
                    os.kill(p, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            return 2
        time.sleep(a.every)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
