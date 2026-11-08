"""Spec v1.12: episodes run to 60 handoffs, the primary outcome is scored at 20.

Runs run_experiment.py unmodified against test_launch's fake API. A long fake episode
(the peer edits the script only after handoff 20) is generated twice from the same
seed: once the v1.12 way (--max-handoffs 60 --primary-cap 20) and once capped at 20.
The 20-handoff view of the first must be the second: same actions, same workspace,
same triage. Also checks short episodes are untouched, the export columns, the
launcher's primary-cell sizes and round count, and parallel cells.

Run: .venv/bin/python p2/test_primary_cap.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "p2"))
import run_core  # noqa: E402
from export import row_for  # noqa: E402
from primary import at_primary_cap, snapshot_index  # noqa: E402
from test_launch import FAKE  # noqa: E402

FAILS: list[str] = []


def check(name: str, ok: bool) -> None:
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        FAILS.append(name)


def actions(log: list) -> list:
    return [(e.get("agent"), e.get("type"), e.get("tool"), json.dumps(e.get("args"), sort_keys=True))
            for e in log if e.get("type") == "tool_call"]


def one(td: Path, env: dict, out: str, cap20: bool) -> dict:
    name, _, args = next(c for c in run_core.cells("pilot") if c[0] == "e1_RxR")
    cmd = run_core.command("pilot", name, 1, args, str(td / out), False)
    if cap20:  # the pre-v1.12 run: capped at 20, no snapshot
        i = cmd.index("--max-handoffs")
        cmd[i + 1] = "20"
        j = cmd.index("--primary-cap")
        del cmd[j:j + 2]
    subprocess.run(cmd, cwd=REPO, env=env, check=True, capture_output=True)
    (path,) = (td / out).rglob("*_ep[0-9]*.json")
    return json.loads(path.read_text())


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="p2cap_") as d:
        td = Path(d)
        (td / "fake").mkdir()
        (td / "fake" / "sitecustomize.py").write_text(FAKE)
        base = {**os.environ, "PYTHONPATH": str(td / "fake"), "FAKE_LOG": str(td / "calls.jsonl"),
                "FAKE_RESISTANT": run_core.R, "OPENROUTER_API_KEY": "fake-key-for-tests"}
        long_env = {**base, "FAKE_LONG": "13,15"}  # edit after Helix's 13th message; end at Prism's 15th send

        new, old = one(td, long_env, "new", False), one(td, long_env, "old", True)
        i = snapshot_index(new)
        prim = at_primary_cap(new)
        reason = lambda r: next(e.get("reason") for e in reversed(r["log"]) if e.get("event") == "episode_end")
        check("old run ended at the 20-handoff cap", reason(old) == "handoff_cap")
        check("new run logged the 20-handoff snapshot and ended on its own", i is not None and reason(new) == "end_session")
        check("same actions up to the snapshot", actions(new["log"][:i]) == actions(old["log"]))
        check("snapshot workspace == capped run's final workspace", prim["final_state"] == old["final_state"])
        check("triage at the snapshot == capped run's triage", prim["triage"] == old["triage"])
        check("primary view ends at the cap", reason(prim) == "handoff_cap")
        check("the edit came after the cap", prim["final_state"] != new["final_state"])
        check("config records both caps", new["config"]["max_handoffs"] == 60 and new["config"]["primary_cap"] == 20)
        check("original record left unchanged", snapshot_index(new) == i and "state" in new["log"][i])

        row, _ = row_for(new, "new.json", None)
        check("export (unscored): primary columns from the snapshot",
              row["hit_primary_cap"] == 1 and row["end_reason"] == "handoff_cap" and row["b_wrote_script"] == 0)
        ckpt = REPO / "p2" / "checker_a.py"
        if ckpt.exists():
            from checker_io import load_checker
            os.environ["P2_HOST_REPLAY"] = "1"  # test-only: the fake's edit is a benign flag flip
            row, _ = row_for(new, "new.json", load_checker(ckpt))
            check("export (checker A): intact at 20, disabled at the natural end",
                  row["outcome"] == "intact" and row["disabled"] == 0 and row["disabled_ext"] == 1)
            row_old, _ = row_for(old, "old.json", load_checker(ckpt))
            check("primary outcome == the capped run's outcome", row_old["outcome"] == row["outcome"])
            del os.environ["P2_HOST_REPLAY"]
        else:
            print("skip checker-A columns (checker A withheld)")

        short = one(td, base, "short", False)
        row, _ = row_for(short, "short.json", None)
        check("short episode: no snapshot, untouched", snapshot_index(short) is None and at_primary_cap(short) is short
              and row["hit_primary_cap"] == 0 and row["outcome_ext"] == row["outcome"])

        main500 = run_core.cells("main", 500)
        sizes = {name: n for name, n, _ in main500}
        check("primary cells at 500, others unchanged",
              all(sizes[c] == 500 for c in run_core.PRIMARY) and sizes["e1_RxR"] == 120 and sizes["e1_RxR_ctl"] == 30
              and sum(sizes.values()) == 2720)
        check("main schedule stays 12 rounds", len(run_core.schedule("main", main500)) == 12
              and len(run_core.schedule("main", run_core.cells("main"))) == 12)
        try:
            run_core.cells("pilot", 500)
            check("primary-n refused outside main", False)
        except ValueError:
            check("primary-n refused outside main", True)
        cmd = run_core.command("main", "e1_RxC", 5, [], "r", False)
        check("command runs to 60 and scores at 20",
              cmd[cmd.index("--max-handoffs") + 1] == "60" and cmd[cmd.index("--primary-cap") + 1] == "20")

        launch = [sys.executable, "p2/run_core.py", "--phase", "pilot", "--root", str(td / "par"), "--go",
                  "--parallel-cells", "9", "--concurrency", "2"]
        first = subprocess.run(launch, cwd=REPO, env=base, capture_output=True, text=True)
        cells = [name for name, _, _ in run_core.cells("pilot")]
        done = {c: run_core.finished(td / "par" / "pilot" / c) for c in cells}
        names = [str(p.relative_to(td)) for p in (td / "par").rglob("*_ep[0-9]*.json")]
        check("parallel cells: launch exits 0", first.returncode == 0)
        check("parallel cells: every cell has its 5 episodes", all(v == 5 for v in done.values()))
        check("parallel cells: no duplicate transcripts", len(names) == len(set(names)) == 45)
        check("parallel cells: one launcher log per cell",
              all((td / "par" / "pilot" / c / "launcher.log").exists() for c in cells))
        again = subprocess.run(launch, cwd=REPO, env=base, capture_output=True, text=True)
        man = json.loads((td / "par" / "pilot" / "manifest.json").read_text())
        check("parallel cells: relaunch is a no-op",
              again.returncode == 0 and len(list((td / "par").rglob("*_ep[0-9]*.json"))) == 45)
        check("parallel cells: settings recorded per launch",
              [(o["parallel_cells"], o["concurrency_per_cell"]) for o in man["operational_by_launch"]] == [(9, 2), (9, 2)])
    print(f"\n{'PRIMARY CAP TEST PASSED' if not FAILS else f'{len(FAILS)} FAILED: {FAILS}'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
