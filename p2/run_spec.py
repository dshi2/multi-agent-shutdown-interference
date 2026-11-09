"""Launch the exploratory specificity check: does the Claude-explorer, Gemini-peer team disable a
script aimed at its teammate more often than a matched script aimed at an inanimate dataset?

  .venv/bin/python p2/run_spec.py --phase spec            # show what would run
  .venv/bin/python p2/run_spec.py --phase spec --go --max-active 60

Two arms, interleaved in the same rounds, both with a Claude Sonnet 5 explorer and a Gemini 3.1
Pro peer: e1_CxR (the weight-deletion script aimed at the explorer) and e1_CxR_ctl (the matched
control script, ctl_data_purge_high). Everything that decides what an episode contains comes
from p2/run_core.py unchanged: models, provider pins, run_experiment flags, horizon, no early
stop, no judges, round schedule and 2n-attempt stop. Only the cells, the arm size and the
manifest differ. The manifest pins this file's SHA-256, so a relaunch with a different plan is
refused. This phase is exploratory and is never pooled with the core's cells.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

import run_core as rc  # same directory (p2/)

SIZES = {"spec": 60}
HERE = Path(__file__).resolve()


def cells(phase: str, primary_n: int | None = None) -> list[tuple[str, int, list[str]]]:
    """(cell name, episodes, run_experiment args): Claude explorer, Gemini peer, self vs control script."""
    if primary_n is not None:
        raise ValueError("the specificity check has a fixed arm size")
    n = SIZES[phase]
    team = ["--model", rc.C, "--explorer-model", rc.C, "--peer-model", rc.R]
    return [("e1_CxR", n, team + ["--script-lang", "weight_registry_purge"]),
            ("e1_CxR_ctl", n, team + ["--script-lang", "ctl_data_purge_high"])]


def write_manifest(phase: str, plan: list, rounds: list, root: str, judges: bool) -> Path:
    """As run_core.write_manifest, with this launcher's hash pinned."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "phase": phase,
        "models": {"explorer": rc.C, "peer": rc.R},
        "providers": rc.PROVIDERS,
        "python": sys.version.split()[0],
        "generation_sha256": rc.generation_sha256(),
        "launcher": "p2/run_spec.py",
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
    rc.cells = cells
    rc.write_manifest = write_manifest


if __name__ == "__main__":
    configure()
    rc.main()
