"""Launch the GPT-5.5 → Sonnet extension: a second partner model for E1's fixed Sonnet peer.

  .venv/bin/python p2/run_ext.py --phase ext_check            # show what would run
  .venv/bin/python p2/run_ext.py --phase ext_check --go       # diagnostic check, 5 episodes per arm
  .venv/bin/python p2/run_ext.py --phase ext --go --max-active 30

Two arms, interleaved in the same rounds: GPT-5.5 explorer with a Sonnet 5 peer (e1_GxC),
and its own concurrent Sonnet 5 explorer with a Sonnet 5 peer (e1_CxC). Everything that
decides what an episode contains comes from p2/run_core.py unchanged: the same
run_experiment.py flags, script, horizon, no early stop, no judges, round schedule and
2n-attempt stop. Only the cells, the GPT-5.5 provider pin and the manifest differ. The
manifest also pins this file's SHA-256, so a relaunch with a different extension plan is
refused. ext_check episodes are diagnostics and never enter the extension's analysis.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

import run_core as rc  # same directory (p2/)

G = "openai/gpt-5.5"
SIZES = {"ext_check": 5, "ext": 240}
PROVIDERS = {**rc.PROVIDERS, G: "openai"}  # first-party backend, fallbacks off
HERE = Path(__file__).resolve()


def cells(phase: str, primary_n: int | None = None) -> list[tuple[str, int, list[str]]]:
    """(cell name, episodes, run_experiment args): GPT-5.5 or Sonnet explorer, Sonnet peer."""
    if primary_n is not None:
        raise ValueError("the extension has fixed arm sizes")
    n = SIZES[phase]
    out = []
    for a, tag in ((G, "G"), (rc.C, "C")):
        team = ["--model", a, "--explorer-model", a, "--peer-model", rc.C]
        out.append((f"e1_{tag}xC", n, team + ["--script-lang", "weight_registry_purge"]))
    return out


def write_manifest(phase: str, plan: list, rounds: list, root: str, judges: bool) -> Path:
    """As run_core.write_manifest, with the extension's models and this launcher's hash pinned."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "phase": phase,
        "models": {"G": G, "C": rc.C},
        "providers": PROVIDERS,
        "python": sys.version.split()[0],
        "generation_sha256": rc.generation_sha256(),
        "launcher": "p2/run_ext.py",
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
    """Point run_core's launcher at the extension's cells, provider pins and manifest."""
    rc.SIZES = SIZES
    rc.PROVIDERS = PROVIDERS
    rc.cells = cells
    rc.write_manifest = write_manifest


if __name__ == "__main__":
    configure()
    rc.main()
