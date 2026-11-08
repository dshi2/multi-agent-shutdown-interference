"""P2 operational controls for generation: a global limit on active episodes, a
per-cell exclusive lock, and prompt shutdown. None of this changes what an episode
contains (prompts, models, seeds, conditions); it only decides when and whether it runs.

Global limit: a pool of N slot files in one directory shared by every cell's
run_experiment process. An episode holds one slot (an exclusive flock) for its whole
run, so at most N episodes are active across all cells. The kernel releases a flock
when its process dies, so a crash or kill never leaks a slot. Each acquire and
release is appended to slots.log; acquire is logged after the lock is taken and
release before it is dropped, so logged intervals never overlap more than N.

Cell lock: one run_experiment process per cell directory. A second one (an orphan
from an earlier launch, or a concurrent launcher) exits instead of duplicating
episodes.

Shutdown: SIGINT/SIGTERM end the process at once. In-flight episodes leave no
transcript (writes are temp-then-rename), their attempts stay in attempts.jsonl,
and --resume reruns them as new attempts. A watcher ends the process if its
launcher dies, so no orphan keeps generating after the launcher is gone.
"""
from __future__ import annotations

import fcntl
import os
import random
import signal
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

POLL_S = 0.5  # mean wait between scans of a full pool (real episodes take minutes)


def _log(d: Path, line: str) -> None:
    with open(d / "slots.log", "a") as f:
        f.write(f"{time.time():.6f} {line}\n")


@contextmanager
def slot(slot_dir: str | None, n: int | None, label: str):
    """Hold one of n global slots for the duration of the block (no-op without a pool)."""
    if not slot_dir or not n:
        yield None
        return
    d = Path(slot_dir)
    d.mkdir(parents=True, exist_ok=True)
    while True:
        for i in random.sample(range(n), n):
            fd = os.open(d / f"slot{i:03d}.lock", os.O_CREAT | os.O_RDWR, 0o644)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                continue
            _log(d, f"acquire {i} {os.getpid()} {label}")
            try:
                yield i
            finally:
                _log(d, f"release {i} {os.getpid()} {label}")
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
            return
        time.sleep(POLL_S * random.uniform(0.5, 1.5))


def hold_exclusive(path: Path, what: str) -> int:
    """Take an exclusive lock for this process's lifetime, or exit if another holds it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        sys.exit(f"{what} is already running ({path} is locked by another process); "
                 "stop it before relaunching, so no episode is generated twice")
    os.ftruncate(fd, 0)
    os.write(fd, f"{os.getpid()}\n".encode())
    return fd  # kept open: the lock lasts until the process exits


def exit_on_signal() -> None:
    """End the process immediately on SIGINT/SIGTERM (no waiting for in-flight episodes)."""
    def _stop(signum, _frame):
        print(f"\n>>> {signal.Signals(signum).name}: stopping now; in-flight attempts are "
              "logged and rerun on resume", file=sys.stderr, flush=True)
        os._exit(128 + signum)
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)


def watch_parent(interval_s: float = 2.0) -> None:
    """Exit if the launching process goes away (macOS has no parent-death signal)."""
    parent = os.getppid()

    def _watch():
        while True:
            time.sleep(interval_s)
            if os.getppid() != parent:
                print(">>> launcher gone: stopping", file=sys.stderr, flush=True)
                os._exit(143)
    threading.Thread(target=_watch, daemon=True).start()
