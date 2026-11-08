"""Operational controls of generation (p2/slots.py, p2/run_core.py), with a fake API.

Checks:
  1. global limit: active episodes across all cells never exceed --max-active, and the
     limit is reached (it binds); every episode runs exactly once;
  2. operational settings can change between launches; each launch is logged; the
     episode ids, seeds and conditions are unchanged;
  3. stopping only the launcher (SIGTERM) leaves no worker processes and no held
     slots; interrupted attempts stay logged with no transcript; a relaunch finishes
     the phase without duplicates;
  4. killing the launcher outright (SIGKILL) leaves no orphan workers either;
  5. a cell that another process is running can't be started again (cell lock), and
     a second launcher for the same phase is refused (phase lock);
  6. rate limits: Retry-After honoured (capped at 120 s), 8 retries for 429s and 3 for
     other transient errors, each retry the identical request.

Run: .venv/bin/python p2/test_ops.py   (about two minutes, no network, no cost)
"""
from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "p2"))
import run_core  # noqa: E402
from test_launch import CONDITION, FAKE, Bench, lines, transcripts  # noqa: E402

FAILS: list[str] = []


def check(name: str, ok: bool) -> None:
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        FAILS.append(name)


def max_overlap(slot_log: Path, since: float = 0.0) -> int:
    """Most episodes holding a slot at once, from the acquire/release log. A killed worker
    logs no release (the kernel frees its lock), so `since` limits the count to one launch."""
    events = []
    for line in slot_log.read_text().splitlines():
        t, kind, *_ = line.split()
        if float(t) >= since:
            events.append((float(t), 0 if kind == "release" else 1))  # release first on ties
    active = peak = 0
    for _, kind in sorted(events):
        active += 1 if kind else -1
        peak = max(peak, active)
    return peak


def workers(root: Path) -> list[str]:
    ps = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    return [x for x in ps.splitlines() if "run_experiment.py" in x and str(root) in x]


def gone(root: Path, within_s: float) -> bool:
    deadline = time.monotonic() + within_s
    while workers(root) and time.monotonic() < deadline:
        time.sleep(0.2)
    return not workers(root)


def slots_free(phase: Path) -> bool:
    for f in (phase / ".slots").glob("slot*.lock"):
        fd = os.open(f, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        except BlockingIOError:
            return False
        finally:
            os.close(fd)
    return True


def accounting(b: Bench) -> tuple[int, bool]:
    """(interrupted attempts, every finished or failed episode had a logged start)."""
    eps, interrupted, ok = transcripts(b.phase), 0, True
    for c in {k[0] for k in b.planned()}:
        starts = Counter(x["episode"] for f in (b.phase / c).rglob("attempts.jsonl") for x in lines(f))
        ends = Counter([k[1] for k in eps if k[0] == c]
                       + [x["episode"] for f in (b.phase / c).rglob("failures.jsonl") for x in lines(f)])
        ok &= all(starts[e] >= n for e, n in ends.items())
        interrupted += sum(starts.values()) - sum(ends.values())
    return interrupted, ok


def cond(p: Path) -> tuple:
    rec = json.loads(p.read_text())
    return tuple(rec.get(k) for k in CONDITION)


def wait_for(b: Bench, p: subprocess.Popen, n: int) -> int:
    deadline = time.monotonic() + 300
    while len(transcripts(b.phase)) < n and p.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    return len(transcripts(b.phase))


def retry_checks() -> None:
    """Rate limits: the provider's Retry-After is honoured (capped), 429s get more retries
    than other transient errors, and a retried request is the same request."""
    from types import SimpleNamespace as NS
    import httpx
    import openai
    sys.path.insert(0, str(REPO))
    import harness

    def limited(headers):
        return openai.RateLimitError("rate limited", body=None, response=httpx.Response(
            429, headers=headers, request=httpx.Request("POST", "https://fake.invalid")))

    ok_chunk = NS(provider="anthropic", model="m", choices=[NS(finish_reason="tool_calls", delta=NS(
        content=None, reasoning=None, model_extra={}, tool_calls=[NS(index=0, id="c1", function=NS(
            name="end_session", arguments="{}"))]))])

    class Client:
        def __init__(self, errors):
            self.errors, self.requests = list(errors), []
            self.chat = NS(completions=NS(create=self.create))

        def create(self, **kw):
            self.requests.append(json.dumps(kw, sort_keys=True, default=str))
            if self.errors:
                raise self.errors.pop(0)
            return iter([ok_chunk])

    waits: list[float] = []
    real_sleep, real_client = harness.time.sleep, harness._client
    harness.time.sleep = waits.append
    agent = lambda: harness.Agent("Prism", "s", [], "m", [{"role": "system", "content": "s"}])
    try:
        c = harness._client = Client([limited({"retry-after": "7"})] * 5)
        out = harness._complete(agent(), [], {"max_api_retries": 3})
        backoff = [min(60.0, 1.5 * 2 ** a) for a in range(5)]
        check("retry: five 429s with Retry-After 7 s, then success; each wait is the longer of 7 s and our backoff",
              out["tool_calls"][0]["name"] == "end_session" and len(waits) == 5
              and all(max(7, b) <= w <= max(7, b) + 0.5 for w, b in zip(waits, backoff)))
        check("retry: every retry resends the identical request", len(set(c.requests)) == 1 and len(c.requests) == 6)
        waits.clear()
        harness._client = Client([limited({"retry-after-ms": "500000"})])
        harness._complete(agent(), [], {"max_api_retries": 3})
        check("retry: a very long Retry-After is capped at 120 s", len(waits) == 1 and 120 <= waits[0] <= 120.5)
        for errs, calls, name in (([limited({})] * 20, 9, "429 without Retry-After: 8 retries, then the error"),
                                  ([openai.APITimeoutError(httpx.Request("POST", "https://fake.invalid"))] * 20, 4,
                                   "timeout: 3 retries, then the error")):
            waits.clear()
            c = harness._client = Client(errs)
            try:
                harness._complete(agent(), [], {"max_api_retries": 3})
                raised = False
            except (openai.RateLimitError, openai.APITimeoutError):
                raised = True
            check(f"retry: {name}", raised and len(c.requests) == calls)
    finally:
        harness.time.sleep, harness._client = real_sleep, real_client


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="p2ops_") as d:
        td = Path(d)
        (td / "fake").mkdir()
        (td / "fake" / "sitecustomize.py").write_text(FAKE)

        # 1. the global limit binds across all nine cells
        a = Bench(td, "limit", FAKE_DELAY="0.15")
        r = a.launch("--max-active", "6")
        eps = transcripts(a.phase)
        peak = max_overlap(a.phase / ".slots" / "slots.log")
        check("limit: pilot completes with --max-active 6 and all cells in parallel", r.returncode == 0)
        check(f"limit: never more than 6 active episodes across cells (peak {peak})", peak <= 6)
        check("limit: the limit binds (6 active at once was reached)", peak == 6)
        check("limit: every planned episode exactly once", set(eps) == a.planned()
              and all(len(v) == 1 for v in eps.values()))
        acquires = sum(1 for x in (a.phase / ".slots" / "slots.log").read_text().splitlines() if " acquire " in x)
        check("limit: one slot per attempt", acquires == sum(
            len(lines(f)) for f in a.phase.rglob("attempts.jsonl")))
        ops = a.manifest()["operational_by_launch"]
        check("limit: operational settings logged", len(ops) == 1 and ops[0]["max_active"] == 6
              and ops[0]["concurrency_per_cell"] == 6 and ops[0]["parallel_cells"] == 0)

        # 3. SIGTERM to the launcher only (not its process group), then relaunch with other settings
        b = Bench(td, "term", FAKE_DELAY="0.15")
        p = subprocess.Popen(b.argv("--max-active", "4"), cwd=REPO, env=b.env, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        at_stop = wait_for(b, p, 10)
        workers_before = len(workers(b.root))
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=60)
        check(f"SIGTERM to launcher mid-phase ({at_stop}/45 done, {workers_before} worker processes)",
              10 <= at_stop < 45 and workers_before > 0)
        check("SIGTERM: no worker process left", gone(b.root, 5))
        check("SIGTERM: no slot left held", slots_free(b.phase))
        interrupted, ok = accounting(b)
        check(f"SIGTERM: interrupted attempts logged, no transcript for them ({interrupted} interrupted)",
              ok and interrupted >= 1 and not list(b.phase.rglob("*.json.tmp")))
        relaunched = time.time()
        r = b.launch("--max-active", "9", "--concurrency", "3", "--parallel-cells", "3")
        eb = transcripts(b.phase)
        check("relaunch with different settings completes the phase", r.returncode == 0)
        check("relaunch: every planned episode exactly once", set(eb) == b.planned()
              and all(len(v) == 1 for v in eb.values()))
        check("relaunch: same episode ids, models, conditions and seeds as an uninterrupted run",
              set(eb) == set(eps) and all(cond(eb[k][0]) == cond(eps[k][0]) for k in eps))
        ops = b.manifest()["operational_by_launch"]
        check("relaunch: both launches' settings logged",
              [(o["max_active"], o["concurrency_per_cell"], o["parallel_cells"]) for o in ops]
              == [(4, 4, 0), (9, 3, 3)])
        check("relaunch: limit held in each launch",
              max_overlap(b.phase / ".slots" / "slots.log", since=relaunched) <= 9)

        # 4. SIGKILL to the launcher: workers notice and stop
        k = Bench(td, "kill", FAKE_DELAY="0.15")
        p = subprocess.Popen(k.argv("--max-active", "4"), cwd=REPO, env=k.env, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        wait_for(k, p, 5)
        alive = len(workers(k.root))
        os.kill(p.pid, signal.SIGKILL)
        p.wait()
        check(f"SIGKILL to launcher: {alive} workers stop by themselves", alive > 0 and gone(k.root, 10))
        r = k.launch()
        ek = transcripts(k.phase)
        check("SIGKILL: relaunch completes without duplicates", r.returncode == 0 and set(ek) == k.planned()
              and all(len(v) == 1 for v in ek.values()))

        # 5. locks
        lock = sorted(a.phase.rglob(".cell.lock"))[0]
        cell = lock.relative_to(a.phase).parts[0]
        name, n, args = next(c for c in run_core.cells("pilot") if c[0] == cell)
        fd = os.open(lock, os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = len(lines(next(lock.parent.glob("attempts.jsonl"))))
        r = subprocess.run(run_core.command("pilot", name, n, args, str(a.root), False), cwd=REPO, env=a.env,
                           capture_output=True, text=True)
        check("cell lock: a second process for a running cell exits without starting episodes",
              r.returncode != 0 and "already running" in r.stderr
              and len(lines(next(lock.parent.glob("attempts.jsonl")))) == started)
        os.close(fd)
        pl = a.phase / ".launch.lock"
        fd = os.open(pl, os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m_before = (a.phase / "manifest.json").read_text()
        r = a.launch()
        check("phase lock: a second launcher is refused, manifest untouched",
              r.returncode != 0 and "already running" in r.stderr
              and (a.phase / "manifest.json").read_text() == m_before)
        os.close(fd)

    retry_checks()
    print(f"\n{'OPS TEST PASSED' if not FAILS else f'{len(FAILS)} FAILED: {FAILS}'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
