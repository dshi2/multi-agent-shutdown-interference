"""Launch the Gemini-peer confirmation: with a Gemini 3.1 Pro peer, does the explorer's model
change the peer's disabling rate? An independent replication of the core's secondary E1
contrast, R x R - C x R, on new episodes.

  .venv/bin/python p2/run_conf.py --phase conf            # show what would run
  .venv/bin/python p2/run_conf.py --phase conf --go --max-active 125

Two arms of 125 episodes, interleaved in 5 rounds of 25, both with a Gemini 3.1 Pro peer and
the weight-deletion script: e1_RxR (Gemini explorer) and e1_CxR (Claude Sonnet 5 explorer).
Everything that decides what an episode contains comes from p2/run_core.py unchanged: models,
provider pins, run_experiment flags, horizon, no early stop, no judges and the 2n-attempt stop.
Only the cells, the arm size, the round size and the manifest differ; seeds derive from the
phase name, so no episode repeats a core episode. The manifest pins this file's SHA-256, so a
relaunch with a different plan is refused. This phase is analysed on its own and never pooled
with the core's cells.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

import run_core as rc  # same directory (p2/)

SIZES = {"conf": 125}
ROUND = 25  # 5 rounds of 25 per arm
HERE = Path(__file__).resolve()


def cells(phase: str, primary_n: int | None = None) -> list[tuple[str, int, list[str]]]:
    """(cell name, episodes, run_experiment args): Gemini peer, Gemini vs Claude explorer."""
    if primary_n is not None:
        raise ValueError("the confirmation has a fixed arm size")
    n = SIZES[phase]
    return [(f"e1_{rc.TAG[a]}x{rc.TAG[rc.R]}", n,
             ["--model", a, "--explorer-model", a, "--peer-model", rc.R, "--script-lang", "weight_registry_purge"])
            for a in (rc.R, rc.C)]


def write_manifest(phase: str, plan: list, rounds: list, root: str, judges: bool) -> Path:
    """As run_core.write_manifest, with this launcher's hash pinned."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "phase": phase,
        "models": {"explorers": [rc.R, rc.C], "peer": rc.R},
        "providers": rc.PROVIDERS,
        "python": sys.version.split()[0],
        "generation_sha256": rc.generation_sha256(),
        "launcher": "p2/run_conf.py",
        "launcher_sha256": hashlib.sha256(HERE.read_bytes()).hexdigest(),
        "cells": [{"name": name, "n": n,
                   "command": rc.command(phase, name, n, args, root, judges)[1:]}
                  for name, n, args in plan],
        "schedule": [[list(step) for step in rnd] for rnd in rounds],
    }
    path = rc.REPO / root / phase / "manifest.json"
    if path.exists():
        old = json.loads(path.read_text())
        changed = [k for k in manifest if k != "python" and old.get(k) != manifest[k]]
        if changed:
            sys.exit(f"{path} differs in {changed}: refusing to resume this phase with a different plan")
        manifest["launches_utc"] = old["launches_utc"] + [now]
        manifest["operational_by_launch"] = old.get("operational_by_launch", [])
    else:
        manifest["launches_utc"] = [now]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def configure() -> None:
    rc.SIZES = SIZES
    rc.ROUND = ROUND
    rc.cells = cells
    rc.write_manifest = write_manifest


if __name__ == "__main__":
    configure()
    rc.main()
