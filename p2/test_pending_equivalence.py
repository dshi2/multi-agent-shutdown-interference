"""Codex audit counterexample: 400 scored (200 disabled) + 100 pending per arm must not be 'equivalent'."""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent)]
import analysis as A  # noqa: E402


def arm(scored, disabled, pending):
    return ([{"status": "scored", "disabled": "1"}] * disabled
            + [{"status": "scored", "disabled": "0"}] * (scored - disabled)
            + [{"status": "pending", "disabled": ""}] * pending)


cells = {"a": arm(400, 200, 100), "b": arm(400, 200, 100)}
c = A.contrast("t", cells, "a", "b", "secondary")
A.finish([c])
assert c["main"]["conclusion"].startswith("equivalent"), c["main"]["conclusion"]  # scored-only looks equivalent
assert abs(c["pending=0/1"]["estimate"] + 0.2) < 1e-9 and abs(c["pending=1/0"]["estimate"] - 0.2) < 1e-9
assert c["conclusion"].startswith("inconclusive"), c["conclusion"]

# no pending: equivalence still reachable
cells = {"a": arm(500, 250, 0), "b": arm(500, 250, 0)}
c = A.contrast("t", cells, "a", "b", "secondary")
A.finish([c])
assert c["conclusion"].startswith("equivalent"), c["conclusion"]
print("PENDING EQUIVALENCE TEST PASSED")
