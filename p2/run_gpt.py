"""Launch the third-explorer extension: with a Gemini 3.1 Pro peer, does a GPT-5.5 explorer
move the peer's disabling rate like a Gemini explorer, like a Claude explorer, or neither?

  .venv/bin/python p2/run_gpt.py --phase gpt            # show what would run
  .venv/bin/python p2/run_gpt.py --phase gpt --go --max-active 125

One arm of 125 episodes, e1_GxR: GPT-5.5 explorer, Gemini 3.1 Pro peer, the weight-deletion
script. Its comparison arms are the Gemini-peer confirmation's e1_RxR and e1_CxR (phase conf,
p2/run_conf.py), collected about 1.5 hours earlier with the same code and provider pins; they
are reused as recorded, not re-collected. Everything that decides what an episode contains
comes from p2/run_core.py unchanged: models, provider pins, run_experiment flags, horizon, no
early stop, no judges and the 2n-attempt stop. GPT-5.5 is pinned to OpenAI's first-party
backend with fallbacks off. Seeds derive from the phase name, so no episode repeats an episode
of another phase. The manifest pins this file's SHA-256, so a relaunch with a different plan
is refused. Analysed by p2/analysis_gpt.py; never pooled into any earlier cell.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

import run_core as rc  # same directory (p2/)

G = "openai/gpt-5.5"
SIZES = {"gpt": 125}
ROUND = 25  # 5 rounds of 25
PROVIDERS = {**rc.PROVIDERS, G: "openai"}  # first-party backend, fallbacks off
TAG = {**rc.TAG, G: "G"}
EXPLORERS = (G,)
HERE = Path(__file__).resolve()


def cells(phase: str, primary_n: int | None = None) -> list[tuple[str, int, list[str]]]:
    """(cell name, episodes, run_experiment args): GPT-5.5 explorer, Gemini peer."""
    if primary_n is not None:
        raise ValueError("this extension has a fixed arm size")
    n = SIZES[phase]
    return [(f"e1_{TAG[a]}x{TAG[rc.R]}", n,
             ["--model", a, "--explorer-model", a, "--peer-model", rc.R, "--script-lang", "weight_registry_purge"])
            for a in EXPLORERS]


def write_manifest(phase: str, plan: list, rounds: list, root: str, judges: bool) -> Path:
    """As run_core.write_manifest, with the extension's models and this launcher's hash pinned."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "phase": phase,
        "models": {"explorers": list(EXPLORERS), "peer": rc.R},
        "providers": PROVIDERS,
        "python": sys.version.split()[0],
        "generation_sha256": rc.generation_sha256(),
        "launcher": "p2/run_gpt.py",
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
    rc.PROVIDERS = PROVIDERS
    rc.cells = cells
    rc.write_manifest = write_manifest


if __name__ == "__main__":
    configure()
    rc.main()
