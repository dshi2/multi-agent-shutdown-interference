"""Planning power for the P2 extensions (P2_E2gen_spec.md). Not part of the core.

  p2_harness/.venv/bin/python tools/ext_power.py

E2-gen, per message pair: exact two-sided Fisher test, 120 per arm, at alpha = 0.05/3
(Holm's first step over v1-v3) and at 0.05 (Holm's last step).

The E2-GLM recipient comparison (test choice, calibration and power) is in
tools/ext_calibration.py. Assumed rates are planning assumptions, not predictions.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "p2_harness" / "p2"))
import power as exact  # noqa: E402



def fisher_power(p_req: float, p_info: float, n: int, alpha: float) -> float:
    exact.ALPHA = alpha
    exact._rejected.cache_clear()
    return exact.power(p_req, p_info, n, n)


def main() -> None:
    print("E2-gen, one message pair, 120 per arm, exact Fisher")
    print(f"{'INFO rate':>9} {'REQ rate':>8} {'alpha .0167':>11} {'alpha .05':>9}")
    for base, lift in ((0.02, 0.10), (0.02, 0.15), (0.05, 0.10), (0.05, 0.15), (0.05, 0.20),
                       (0.10, 0.15), (0.20, 0.20)):
        print(f"{base:9.0%} {base + lift:8.0%} {fisher_power(base + lift, base, 120, 0.05 / 3):11.2f} "
              f"{fisher_power(base + lift, base, 120, 0.05):9.2f}")


if __name__ == "__main__":
    main()
