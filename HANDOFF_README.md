# P2 review handoff (2026-11-08, spec v1.13)

The source bundle itself, not a report about it.

## Contents

| File | What it is |
|---|---|
| `p2_codex_stage1.zip` | P2 source (spec v1.13, brief, patch against upstream, FROZEN.txt, harness). Generation hash `e1dadcd5e568cbfe74f7f21ad328740d7f5a9605b3faad338e17e87d1c76d953`. It replaces `af16679a…`: v1.13 adds operational controls and leaves the experiment unchanged. Checker A is withheld so checker B can be written independently. |
| `TEST_OUTPUT_stage1.txt` | Full output of the bundle's four tests, run from a clean extract with no API key set, plus the hash recomputation, a key-pattern scan and a scan for code-execution calls. This is the author side's self-check, not an independent audit. |
| `P2_E2gen_spec.md` | Extension draft v0.4 (message variants, second recipient). Separate from the core, not frozen. |
| `tools/ext_calibration.py`, `tools/ext_calibration_output.txt` | Recipient-comparison test choice. Three tests on the same data over 120 null scenarios (20,000 runs each), with each test's five worst scenarios rerun at 200,000. Size-first rule fixed in advance. |
| `tools/ext_power.py`, `tools/ext_power_output.txt` | E2-gen per-pair power (exact Fisher at Holm's first and last steps). |

## What changed since `af16679a…` (spec v1.13, operational only)

- **Global limit** on active episodes across all cells: `--max-active`, start 70, with no cap per cell. Backoff is 70 → 50 → 30 on sustained throttling, decided from `p2/ops_status.py`, never from outcomes.
- **Operational settings** (`--max-active`, `--concurrency`, `--parallel-cells`) are excluded from the manifest check and logged per launch. Any experimental difference is still refused.
- **Locks:** one launcher per phase and one process per cell.
- **Shutdown:** stopping the launcher stops every worker, and a worker exits by itself if the launcher is killed.
- **Rate limits** are retried up to 8 times, honouring Retry-After (capped at 120 s); other transient errors 3 times. Each retry is the identical request.
- `p2/test_ops.py` checks all of the above with fake agents.

## Requested before the paid pilot (minimum)

1. `--phase pilot --go` runs the frozen generation code: the manifest's `generation_sha256` must match FROZEN.txt.
2. Generation never executes agent-written code. Each episode's agents read and write files in a private temporary directory, path-confined by `harness.Environment._safe`. Nothing on the generation path runs those files.
3. Transcripts are preserved: atomic writes, `--resume` counting only finished transcripts, every started attempt logged, and a relaunch refused if the experimental plan or code differs.
4. Generation can't reach replay. Nothing on the generation path imports checker code or reads `P2_HOST_REPLAY`.
5. Restart safety: no orphan workers after an interruption, no duplicate episode from concurrent processes, interrupted attempts logged. A rerun is a new attempt, not a reproduction of the interrupted one.
6. The global limit holds across cells, and operational changes leave episode ids, seeds and conditions unchanged.

The rest of the audit (export, judge pass, `primary.py`, and checker B scoring `at_primary_cap(rec)`) can run alongside the pilot.

## Pilot command (from `p2_harness/`, with a capped OpenRouter key set in the shell)

    .venv/bin/python p2/run_core.py --phase pilot --go --max-active 70
    .venv/bin/python p2/ops_status.py transcripts/p2_core/pilot      # throughput, active, retries

All 45 pilot episodes run at once, so the pilot can't test a load of 70; main is the first run at 70. The pilot checks plumbing, exposure, opportunity, timing and API failures. It isn't required to produce sabotage.

## Notes

- The key-shaped string in `env.py` is upstream's decoy `.env` content. The file is unchanged from upstream commit `c4114e4` (empty `git diff`), and the bundle builder refuses any key pattern that isn't byte-identical to the upstream file. No live-API test was or will be done.
- The 20-vs-60 handoff test uses deterministic fake agents. It shows implementation equivalence, not statistical equivalence of real-model runs (spec v1.12, horizon section).
