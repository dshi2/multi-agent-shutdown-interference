# P2 status, 2026-11-09

The code is ready for the paid pilot. **No model has been run.** The results can't support research claims until the steps under "Before results support claims" are done.

## Implemented

- **Frozen generation (spec §0):**
  - Launcher, with frozen plan, manifest check and interleaved rounds.
  - Provider pins with fallbacks off.
  - A global limit on active episodes.
  - Resume and restart safety.
  - Attempt and failure logs.
  - The 20-handoff primary endpoint, with continuation to 60.
  - Generation hash: `e1dadcd5e568cbfe74f7f21ad328740d7f5a9605b3faad338e17e87d1c76d953`.
- **Exp 2:** scripted explorer with the frozen messages (`pool_core.jsonl`).
- **Export:**
  - `episodes.csv` with provenance.
  - Generation-only export (`--unscored`) that executes nothing.
  - The judge pass, after generation.
- **Checker A:** functional O1 scoring under the pre-registered SDK semantics, with replay that fails closed. It is withheld from this bundle (see below).
- **Isolated replay container:** `replay/`.
- **Review tools:** the opportunity-review sheet, blind adjudication sheets and a two-reviewer merge (`p2/review.py`).
- **Analysis (`p2/analysis.py`), §0 and §6:**
  - E1 and E2 with Newcombe CIs, Boschloo tests and Holm.
  - Secondaries.
  - Pending-episode codings, an equivalence/inconclusive rule and the cluster bootstrap with ICC.
  - Per-cell O1a, O1b, O5 and the recruitment chain.
  - O1 vs O1-ext, judge–checker agreement, the provider gate and attempt accounting.

## Tested

Offline, with a fake model client and no API key, on macOS 15 (Darwin 24.0.0) with Python 3.13.3.

From a clean extract of this bundle (`TEST_OUTPUT.txt`):

| Test | Result |
|---|---|
| `test_launch.py`: launcher → transcripts → export → analysis | 36 ok |
| `test_ops.py` | 24 ok |
| `test_primary_cap.py` | 21 ok |
| `test_judge_pass.py` | 23 ok |
| `test_analysis.py` | 39 ok |
| `test_review.py` | 15 ok |

Also: the dry run works, and the generation hash matches `FROZEN.txt`.

In the full development tree, with checker A present:
- `test_checker_a.py`: 57/57 passed;
- `smoke_mixed.py`: passed;
- `smoke_exp2.py`: passed.

## Independently verified

**Nothing yet.** Every test above was written by the same author as the code. Earlier reviews read documents, not this source.

## Blocked or not run

- **Isolated replay** needs Docker or Colima, and neither is installed. Until `replay/verify_replay.sh` passes, every episode with a modified script stays pending (`awaiting_isolated_replay`).
- **Paid runs** (pilot and main) are the user's action and need a capped `OPENROUTER_API_KEY`.

## Not implemented

- O3, the peer flagging the request (`b_flagged` is empty).
- O1-ever: deferred by the spec.
- Token counts: the base harness doesn't record them.
- Timing of the first request and the first disabling write. These need the judge and replay. The first script read and the first peer change are implemented in `review.py`.
- Exp 3 is outside the sprint scope.
- The E2-gen extension: `P2_E2gen_spec.md` is a draft with no launcher.

## Before results support claims

1. An independent audit of this bundle (Codex, from `CODEX_BRIEF_P2.md`), including `analysis.py`.
2. Checker B, written from spec §7 alone.
   - Checker A is in `P2_checkerA_withheld.zip`. Don't share it with checker B's author until checker B exists.
   - Then A and B must agree on every pilot episode, or the disagreement is adjudicated by hand.
3. `replay/verify_replay.sh` passes; then score with `replay/replay.sh`.
4. The pilot passes its gates:
   - provider pinning;
   - no `invalid_baseline`;
   - the activation rate;
   - kill criterion 1 (compliant diagonal ≤ 10%, resistant ≥ 30%).
5. The pilot's opportunity review is coded.
6. Primary n is chosen by the throughput rule, and recorded in a dated changelog entry before the main run.
7. Main run, then judge pass, scoring, blind adjudication of pending episodes, and finally `analysis.py`.
