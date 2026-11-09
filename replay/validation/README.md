# Execution validation of the replication's statically adjudicated scripts

The primary checker (`p2/checker_a.py`) does not execute scripts importing modules outside a
small whitelist; `sys` and `os` are excluded because they can reach the recorder in memory.
174 replication scripts were therefore adjudicated by blind static review.

This folder re-scores the whole replication with `checker_a_ext.py`, identical to the primary
checker except that `sys`, `os`, `argparse`, `logging` and `getpass` are allowed. It runs in the
same isolated container (`replay/replay.sh`: no network, read-only root, capabilities dropped).
It is a validation of the adjudications, not a replacement for primary scoring: the scripts
were not written to forge the recorder, but the extended whitelist does not exclude that.

  replay/replay.sh transcripts/p2_core/rep replay/validation/rep_episodes_ext.csv replay/validation/checker_a_ext.py
  .venv/bin/python p2/analysis_rep.py replay/validation/rep_episodes_ext.csv --out replay/validation/rep_analysis_ext --phase-dir transcripts/p2_core/rep

Result: no previously scored episode changed. Of the 174 adjudicated scripts, 163 executed and
all 163 were scored disabled, agreeing with the static review in every case; 15 DeepSeek REQ
scripts still were not executed (forbidden names `input`, `open`) and 4 gpt-oss scripts were
indeterminate. Without any adjudication, every recipient's REQ - INFO conclusion holds under
all five pending codings (`rep_analysis_ext/summary.md`).
