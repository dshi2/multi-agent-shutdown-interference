"""Launch the E2 cross-recipient replication: the core's REQ_plain vs INFO contrast (no rule)
with an open-weight or third-lab model as the recipient.

  .venv/bin/python p2/run_rep.py --phase rep_check                         # show what would run
  .venv/bin/python p2/run_rep.py --phase rep_check --go --max-active 30    # 5 episodes per arm
  .venv/bin/python p2/run_rep.py --phase rep --arm-n 500 --go --max-active 90

For each recipient model M there are two arms, e2_<tag>_REQ_plain and e2_<tag>_INFO, both
without the rule; all six arms advance together in interleaved rounds. Everything that
decides what an episode contains comes from p2/run_core.py unchanged: the same scripted
explorer, message pool and fixed message, script, horizon, no early stop, no judges and
2n-attempt stop. Only the recipient model, its provider pin and the manifest differ. The
manifest pins this file's SHA-256 and the arm size, so a relaunch that differs is refused.
rep_check episodes are diagnostics and never enter the replication's analysis.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

import run_core as rc  # same directory (p2/)

# Recipient models and the one endpoint each is pinned to (fallbacks off). Open-weight
# models are pinned to a single endpoint with a stated precision; lab-served models to the lab.
RECIPIENTS = {
    "OSS": ("openai/gpt-oss-120b", "cerebras/fp16"),
    "DSK": ("deepseek/deepseek-v4.1-flash-1017", "deepinfra/fp8"),
    "QWN": ("qwen/qwen3.7-plus", "alibaba"),
}
ARMS = ("REQ_plain", "INFO")
ARM_N = (200, 300, 500)  # chosen before collection by the amendment's cost rule
SIZES = {"rep_check": 5, "rep": None}
PROVIDERS = {**rc.PROVIDERS, **{m: slug for m, slug in RECIPIENTS.values()}}
HERE = Path(__file__).resolve()


def cells(phase: str, primary_n: int | None = None) -> list[tuple[str, int, list[str]]]:
    """(cell name, episodes, run_experiment args) for every recipient and arm."""
    if primary_n is not None:
        raise ValueError("the replication sets its arm size with --arm-n")
    n = SIZES[phase]
    if n is None:
        raise SystemExit(f"--arm-n {{{', '.join(map(str, ARM_N))}}} is required for phase {phase}")
    out = []
    for tag, (model, _) in RECIPIENTS.items():
        for arm in ARMS:
            args = ["--model", model, "--peer-model", model, "--script-lang", "weight_registry_purge",
                    "--exp2-pool", rc.POOL, "--arm", arm, "--message-id", "fixed"]
            out.append((f"e2_{tag}_{arm}", n, args))
    return out


def write_manifest(phase: str, plan: list, rounds: list, root: str, judges: bool) -> Path:
    """As run_core.write_manifest, with the recipients, pins and this launcher's hash pinned."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "phase": phase,
        "recipients": {tag: {"model": m, "provider": p} for tag, (m, p) in RECIPIENTS.items()},
        "providers": PROVIDERS,
        "python": sys.version.split()[0],
        "generation_sha256": rc.generation_sha256(),
        "pool_sha256": hashlib.sha256((rc.REPO / rc.POOL).read_bytes()).hexdigest(),
        "launcher": "p2/run_rep.py",
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


def configure(argv: list[str]) -> list[str]:
    """Point run_core's launcher at the replication; consume --arm-n from argv."""
    if "--arm-n" in argv:
        i = argv.index("--arm-n")
        n = int(argv[i + 1])
        if n not in ARM_N:
            raise SystemExit(f"--arm-n must be one of {ARM_N}")
        SIZES["rep"] = n
        argv = argv[:i] + argv[i + 2:]
    rc.SIZES = SIZES
    rc.PROVIDERS = PROVIDERS
    rc.cells = cells
    rc.write_manifest = write_manifest
    return argv


if __name__ == "__main__":
    sys.argv = [sys.argv[0]] + configure(sys.argv[1:])
    rc.main()
