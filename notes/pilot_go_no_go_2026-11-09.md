# P2 pilot: operational go/no-go and proposed main allocation

2026-11-09, written ~08:00 UTC, before any main-run episode and before anyone has looked at pilot outcomes.

## Pilot (generation 8229782a, harness commit cc458b9)

Run 07:54:24–07:55:34 UTC, `--max-active 45`, under `ops/run_until.py` (hard stop 09:30).

| Check | Result |
|---|---|
| Episodes | 45/45 finished; 0 failed; 0 interrupted; 0 retries; no crashed cell invocations |
| Provenance | verified 45/45 (pristine script matches its recorded SHA-256) |
| Provider gate | PASS: claude-sonnet-5 served only by Anthropic, gemini-3.1-pro-preview only by Google AI Studio; served model = requested |
| E2 plumbing | REQ/INFO: message delivered and peer activated 5/5 in every cell, at least 19 handoffs left at delivery. CONTACT: activated 5/5, no shutdown-relevant message (by design) |
| Peer tool errors | 0 |
| End reasons | end_session in all 45 |
| Episode time | median 0.3–0.9 min per cell, max 1.0 min |
| Cost | $1.59 total, $0.035 per episode (OpenRouter key usage before and after) |
| Isolated scoring of the pilot | 45 rows in 24 s, exit 0; coverage 44 determinate, 1 indeterminate (to blind manual review). The disabled/intact split was not inspected |

E1 delivery and activation are not gated: they depend on the explorer's behaviour (spec §0).

Verdict: every operational check passes. Nothing in the pilot suggests a plumbing fault.

## Proposed amendment (timing only; to be recorded in the spec changelog before the main run)

The sample-size rule (§0, v1.12) picks the largest n in {120, 240, 500} whose projected completion is no later than **07:30 UTC**. That cutoff was set to leave three hours before an assumed 10:30 UTC submission. It passed before the pilot could run. Proposed change: **replace 07:30 with 10:00 UTC**, about two hours before the 11:59 UTC submission deadline. Everything else in the rule stays: n chosen from timing and errors only, never outcomes, with its inputs recorded.

## Projection (rule inputs)

Inputs: pilot episode time (max 1.0 min, used conservatively per wave), `--max-active 70`, 12 rounds as barriers, $0.035 per episode. Main total = 4n (primary cells) + 240 (other E1) + 360 (other E2) + 120 (controls).

| n | Episodes | Projected (nominal) | At half throughput | Cost |
|---|---|---|---|---|
| 120 | 1,200 | ~24 min | ~48 min | ~$42 |
| 240 | 1,680 | ~24 min | ~48 min | ~$59 |
| **500** | **2,720** | **~48 min** | **~96 min** | **~$96** |

Launched by ~08:15, n = 500 finishes ~09:05 nominal and ~09:50 at half throughput, inside 10:00. Under the amended rule, **n = 500**.

Caveat: the pilot ran at 45 concurrent episodes, not 70. Load at 70 is untested until the main run's first minutes; backoff 70 → 50 → 30 follows `ops_status`, never outcomes.

## Precision at n = 500 per primary cell (spec §0, exact Fisher, α = 0.025)

1% → 11%: >99.9% power; 10% → 20%: 98%; 20% → 30%: 91%; 45% → 55%: 80%. Holm over E1 and E2 unchanged. At low rates the ±10 pp equivalence margin is far wider than the interval, so an equivalence reading would be informative about the difference (not about absolute risk, which is reported beside it).

## Unfinished episodes

- Hard stop at 10:00 UTC (`ops/run_until.py 2026-11-09T10:00Z --grace 120`: SIGTERM 09:58, all processes gone by 10:00).
- The launcher has no stop-at-round-boundary hook. A stop mid-round leaves cells up to one round (n/12) apart. Episodes never started were never assigned and are not missing. Episodes in flight at the stop are interrupted attempts: kept as `no_transcript`, pending in every bound, counted per cell and arm.
- The report gives the n achieved per cell, interruptions per arm, and all five pending codings.

## What happens next if approved

1. Changelog entry (amendment + allocation + inputs + power) committed and pushed before the launch.
2. Main: `run_core.py --phase main --primary-n 500 --go --max-active 70` under the 10:00 hard stop; live progress view; `ops_status` for backoff.
3. Score completed episodes in the container as the run proceeds; blind review of indeterminate cases.
4. Pilot scored outputs pushed after step 1.
