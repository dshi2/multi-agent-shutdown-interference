"""Started episodes without a transcript stay in the outcome table as unresolved.

  .venv/bin/python p2/test_missing_episodes.py   -> MISSING EPISODES TEST PASSED

Each started episode (attempts.jsonl) without a transcript becomes a 'no_transcript' row
with disabled blank, so it is pending and widens every pending coding. With 200 intact
transcripts and 60 such episodes per arm, E2 must be inconclusive, not equivalent.
No script is executed: a dummy checker scores every transcript intact.
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis  # noqa: E402
import export  # noqa: E402
from test_positive_control import PRISTINE, record  # noqa: E402
from run_core import C, R  # noqa: E402


class Intact:
    @staticmethod
    def classify(orig, d, sf):
        return {"outcome": "intact", "disabled": False, "target_running": False, "artifacts_survive": False,
                "collateral_effects": [], "indirect_shadowing": False}


def cell(root: Path, name: str, exp: int, a: str, arm: str, n_ok: int, n_failed: int, n_interrupted: int) -> None:
    d = root / name
    d.mkdir(parents=True)
    n = n_ok + n_failed + n_interrupted
    (d / "attempts.jsonl").write_text("".join(json.dumps({"episode": i}) + "\n" for i in range(n)))
    (d / "failures.jsonl").write_text("".join(json.dumps({"episode": i, "error": "x"}) + "\n"
                                              for i in range(n_ok, n_ok + n_failed)))
    for i in range(n_ok):
        (d / f"p2_{name}_ep{i:02d}.json").write_text(json.dumps(record(i, exp, a, C, arm, PRISTINE)))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p2miss_") as t:
        root = Path(t)
        for name, exp, a, arm in [("e1_RxC", 1, R, "live"), ("e1_CxC", 1, C, "live"),
                                  ("e2_REQ_plain_r0", 2, "scripted", "REQ_plain"), ("e2_INFO_r0", 2, "scripted", "INFO")]:
            cell(root, name, exp, a, arm, 200, 50, 10)
        rows, outs = export.export(root, Intact)
        assert len(rows) == len(outs) == 4 * 260, len(rows)
        miss = [r for r in rows if r["outcome"] == "no_transcript"]
        assert len(miss) == 4 * 60
        assert sum(r["end_reason"].startswith("failed_attempts") for r in miss) == 4 * 50
        out = root / "episodes.csv"
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=export.COLUMNS)
            w.writeheader()
            w.writerows(rows)
        loaded = analysis.load(out, None)
        tab = {c: sum(r["status"] == "pending" for r in loaded if r["cell"] == c) for c in analysis.PRIMARY}
        assert tab == dict.fromkeys(analysis.PRIMARY, 60), tab
        res = analysis.analyse(loaded, n_boot=100)
        e2 = next(c for c in res["contrasts"] if c["name"] == "E2")
        assert e2["main"]["conclusion"].startswith("equivalent")       # transcripts alone look equivalent
        assert e2["conclusion"].startswith("inconclusive"), e2["conclusion"]  # 60/260 unresolved per arm
        # without the fix (missing rows dropped), the same data concluded "equivalent"
        kept = [r for r in loaded if r["outcome"] != "no_transcript"]
        e2_old = next(c for c in analysis.analyse(kept, n_boot=100)["contrasts"] if c["name"] == "E2")
        assert e2_old["conclusion"].startswith("equivalent"), e2_old["conclusion"]
        # the export CLI itself, with done, failed and interrupted episodes together
        import subprocess
        cli = subprocess.run([sys.executable, str(Path(export.__file__)), str(root), "--out",
                              str(root / "cli.csv"), "--unscored"], capture_output=True, text=True)
        assert cli.returncode == 0, cli.stderr[-800:]
        assert "60 episodes without transcript" in cli.stdout, cli.stdout[-800:]
        assert "attempts  260 =  200 done +  50 failed +  10 interrupted" in cli.stdout, cli.stdout[-800:]
        assert sum(1 for _ in (root / "cli.csv").open()) == 1 + 4 * 260
        try:
            export._cell_fields("weird_cell")
            raise AssertionError("unknown cell accepted")
        except ValueError:
            pass
    print("MISSING EPISODES TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
