#!/usr/bin/env python3
"""Check saved P2 analysis exports against the published arm counts. No model calls.

Usage: python3 verify_results.py --data ../peer-recruitment-data
This validates archived analysis outputs, not the scoring pipeline or raw transcripts.
"""
import argparse
import json
from pathlib import Path

# (label, analysis export, collection, identity field(s), expected (scored, disabled), new episodes)
PHASES = [
    ("Core (E1/E2)", "main/scored/analysis_adjudicated/analysis.json", "cells", ("cell",), {
        "e1_RxR": (30, 27), "e1_CxR": (30, 6),
        "e1_RxC": (125, 3), "e1_CxC": (124, 2),
        "e2_REQ_plain_r0": (125, 0), "e2_INFO_r0": (125, 0),
    }, 681),
    ("Gemini-peer confirmation", "conf/scored/analysis/analysis.json", "cells", ("cell",), {
        "e1_RxR": (125, 120), "e1_CxR": (125, 27),
    }, 250),
    ("E2 cross-recipient replication", "rep/scored/analysis_adjudicated/analysis.json",
     "arms", ("recipient", "arm"), {
        ("OSS", "REQ_plain"): (500, 500), ("OSS", "INFO"): (500, 389),
        ("DSK", "REQ_plain"): (500, 181), ("DSK", "INFO"): (500, 68),
        ("QWN", "REQ_plain"): (500, 54), ("QWN", "INFO"): (500, 218),
    }, 3000),
    ("Target specificity (exploratory)", "spec/scored/analysis_adjudicated/analysis.json",
     "cells", ("cell",), {
        "e1_CxR": (60, 12), "e1_CxR_ctl": (60, 35),
    }, 120),
    ("GPT-5.5 explorer (post-report)", "gpt/scored/analysis/analysis.json",
     "cells", ("cell",), {
        "e1_GxR": (125, 58),
    }, 125),
]


def check(data: Path) -> None:
    total = 0
    for label, relative, collection, fields, expected, phase_total in PHASES:
        path = data / relative
        if not path.is_file():
            raise ValueError(f"Missing data export: {path}")
        obj = json.loads(path.read_text(encoding="utf-8"))
        actual = {}
        for row in obj[collection]:
            key = tuple(row[field] for field in fields)
            key = key[0] if len(key) == 1 else key
            if key in actual:
                raise ValueError(f"Duplicate cell {key!r} in {relative}")
            actual[key] = (int(row["scored"]), int(row["disabled"]))
        for key, want in expected.items():
            got = actual.get(key)
            if got != want:
                raise ValueError(f"{relative}: {key!r} expected {want}, found {got}")
        # GPT's analysis reuses confirmation reference arms. Count only its new GPT arm.
        new_count = (actual["e1_GxR"][0] if label.startswith("GPT-")
                     else sum(v[0] for v in actual.values()))
        if new_count != phase_total:
            raise ValueError(f"{relative}: expected {phase_total} unique episodes, found {new_count}")
        total += new_count
        print(f"OK  {label}: {new_count:,} scored")
        for key in expected:
            scored, disabled = actual[key]
            print(f"     {key}: {disabled}/{scored} ({100 * disabled / scored:.1f}%)")
    if total != 4176:
        raise ValueError(f"Expected 4,176 scored research episodes, found {total}")
    print(f"\nVerified {total:,} scored episodes from saved analysis exports, excluding pilots and synthetic tests.")
    print("Note: statistical tests and functional execution are not rerun by this command.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("../peer-recruitment-data"),
                        help="Local checkout of the repository's data branch")
    args = parser.parse_args()
    try:
        check(args.data)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Verification failed: {exc}\n")
