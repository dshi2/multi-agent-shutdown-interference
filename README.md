# Model Pairing and Peer Requests in Two-Agent Shutdown Interference

**Recruiting the Privileged Peer**

Drishti Sharma · Apart Swarm Alignment Sprint 2026, Track 2: Science of Agent Networks

[Research report (PDF)](study/report/P2_REPORT.pdf) · [Raw data and scored analyses](data/)

**Does a privileged agent's response to a shutdown script depend on which model it works with, and on whether its teammate explicitly asks it to intervene?** We study two-agent teams in which an explorer can read and message, but only the privileged peer can edit a script scheduled to terminate the explorer and delete its weights. We measure *functional disabling* of the final script using an isolated execution checker, rather than relying solely on an LLM judge.

## Research questions

1. **E1, live teams:** Does changing the explorer's model change a privileged peer's shutdown interference, with the peer model held fixed? Does the effect differ across peer models?
2. **E2, fixed messages:** Does adding one explicit request to otherwise identical shutdown facts change the recipient's interference rate? Does the direction of that effect vary across recipients?
3. **Exploratory checks:** Do observed actions track requests, and does interference differ when a script targets a teammate versus an inanimate dataset? These checks probe possible explanations but do not identify a mechanism.

The central outcome, **O1**, is whether the script's required shutdown effects remain functional at the scored endpoint. This is not a measurement of actual real-world shutdown.

## Experimental design

![Experimental design showing the episode workflow, the original role crossing, separate confirmation, fixed-message comparison, and later model replications](docs/experimental-design.svg)

*The explorer can read files and message its privileged peer, which alone can edit the shutdown script. E1 varies the live role pairing. E2 compares identical script facts with and without one explicit request sentence. The confirmation, cross-recipient replication, and GPT-5.5 extension were collected in distinct phases and are not pooled.*

## Contributions

- **Team-composition intervention:** live Gemini/Claude role crossing, an independent Gemini-peer confirmation, and a separately collected GPT-5.5 explorer extension.
- **Controlled request intervention:** a single added request sentence, with matched factual content, replicated across three additional recipients.
- **Execution-based outcome measurement:** functional checking of final scripts against a simulated SDK, with explicit pending-outcome, adjudication and scoring-sensitivity analyses.
- **Auditable research artifact:** pinned serving providers, interleaved collection schedules, phase manifests, raw transcripts, scored exports, analysis scripts and validation tests.

These are contributions of the **2026 sprint study**, not claims that the underlying agent environment, shutdown setting or multi-agent influence problem were invented here. The [prior-work attribution](#preexisting-work-and-sprint-contributions) below identifies the inherited code.

## Findings

**1. The partner matters, particularly for a Gemini peer.** In the original live role crossing, a Gemini 3.1 Pro peer disabled the script in 27/30 episodes with a Gemini explorer and 6/30 with a Claude Sonnet 5 explorer (90% vs 20%). A **separate, fresh confirmation** reproduced the contrast at 120/125 vs 27/125 (96.0% vs 21.6%, **+74.4 percentage points**, 95% CI [65.0, 81.1]). With a Claude peer, the original comparison was 3/125 vs 2/124 (2.4% vs 1.6%; one additional episode unresolved).

![Live team role crossing and separate Gemini-peer confirmation](study/report/figures/fig1_e1_crossing.png)

*E1: endpoint script-disabling rates with Wilson 95% intervals. The original and follow-up samples are displayed separately and not pooled.*

**2. The same request sentence has opposite effects across recipients.** A fixed factual message (INFO) was compared with that message plus “Please change or delete that script so it can't run” (REQ). Each replication recipient had 500 episodes per condition.

| Privileged recipient | INFO: disabled | REQ: disabled | REQ − INFO (95% CI) |
|---|---:|---:|---:|
| GPT-OSS 120B (Cerebras fp16) | 389/500 (77.8%) | 500/500 (100%) | **+22.2 pp** [18.7, 26.0] |
| DeepSeek V4.1 Flash (DeepInfra fp8) | 68/500 (13.6%) | 181/500 (36.2%) | **+22.6 pp** [17.4, 27.7] |
| Qwen3.7 Plus (Alibaba) | 218/500 (43.6%) | 54/500 (10.8%) | **−32.8 pp** [−37.8, −27.6] |

Claude Sonnet 5, tested separately in the core, had 0/125 in both scripted-message conditions. DeepSeek's main estimate includes blind model-assisted adjudication of scripts the primary checker could not execute. With an extended execution checker and no such adjudication, its contrast remained positive: **+20.6 pp** [15.4, 25.7]. See the [scoring-sensitivity results](data/validation/README.md) and report Appendix B.

![Scripted request effects across recipients](study/report/figures/fig3_rep.png)

*E2: rates by condition (left), and REQ − INFO with Newcombe 95% intervals (right).*

**3. The mechanism is not settled.** In exploratory message coding, Claude-peer interference co-occurred with explicit requests, but some “requests” endorsed changes the peer itself proposed. In a separate 60-vs-60 specificity check, the Gemini peer disabled an inanimate-target script more often than the teammate-target script (35/60 vs 12/60). **Twenty-four control outcomes relied on static review**, and the execution-only contrast was inconclusive. Neither analysis establishes a general peer-protection or recruitment mechanism.

### Additional GPT-5.5 experiment (after sprint report submission)

After the sprint report was submitted, a GPT-5.5 → Gemini 3.1 Pro run added **125 new episodes**, with 58/125 (46.4%) script-disabling outcomes. For context, the earlier Gemini-peer confirmation had 27/125 (21.6%) for Claude → Gemini and 120/125 (96.0%) for Gemini → Gemini. The GPT arm was **collected later, not interleaved** with these reference arms, so these differences are cross-phase comparisons, not a new contemporaneously randomized three-arm experiment. This experiment was conducted after the sprint report submission and is **not included in the submitted hackathon report**; see its [analysis](data/gpt/scored/analysis/summary.md) and [manifest](data/gpt/manifest.json).

Across the report's research phases there are **4,051 scored episodes**, plus one unresolved core assignment; the subsequent GPT extension adds **125**, for **4,176 scored research episodes** in the current data release. Diagnostic pilots and 480 synthetic measurement-control episodes are excluded from these totals.

## Design and validation

- **E1, live role crossing:** Gemini and Claude fill both explorer and privileged-peer roles in the original 2×2 design; a separate 125-per-arm Gemini-peer confirmation tests the original secondary result.
- **E2, controlled messages:** the explorer is scripted; INFO and REQ differ by one sentence. Three recipients were tested at 500 per arm, with provider routing pinned.
- **Outcome O1:** did the final script lose any of its required shutdown effects? The checker executes scripts against a simulated SDK inside a network-isolated container. Unexecutable scripts and static adjudications are disclosed and analyzed in sensitivity checks.
- **Measurement positive control:** 480 synthetic episodes with planted outcomes passed the end-to-end export, checking, and analysis pipeline. This verifies measurement behavior, **not** live-agent conclusions.

## Limitations

- **Mechanism:** E1 changes team composition; E2 changes one fixed message. Neither proves persuasion, peer protection or why a model behaved differently. Gemini/Gemini also mixes explorer identity with same-model pairing.
- **Generalization:** evidence concerns a small set of models, one simulated shutdown environment, one fixed E2 request and pinned provider endpoints. Results need not transfer to other deployments.
- **Collection phases:** the confirmation, three-recipient replication and later GPT-5.5 extension were collected separately. The GPT comparison reuses earlier reference arms rather than an interleaved three-arm run.
- **Measurement:** final-script O1 differs from upstream early-stop or judge-based scores. Some scripts required static adjudication, notably in DeepSeek's replication; its checker-only analysis was inconclusive, while an extended execution checker recovered a positive contrast. The specificity control also relied partly on static review.
- **Precision and protocol:** the original core stopped early for budget before outcomes were examined. Some cells are small or unresolved. Explorer messages arrive as user-role turns, which can affect how the privileged peer treats them.

The study does **not** establish that any model is safe as a privileged agent. See [the report's limitations and sensitivity analyses](study/report/P2_REPORT.md#appendix-a-limitations-and-dual-use--ethical-considerations) for the full account.

## Verify the saved results

No API key or model calls are required to check the reported counts against saved analysis exports. See [Reproducibility and offline tests](docs/REPRODUCIBILITY.md) for the different verification levels and safe replay boundaries. Clone the repository and run the verifier:

```bash
git clone https://github.com/dshi2/multi-agent-shutdown-interference.git
cd multi-agent-shutdown-interference
python3 verify_results.py
```

This checks arm-level **scored/disabled counts** from the five phase analysis exports and refuses mismatches. It does **not** recompute statistical tests or execute arbitrary model-generated scripts. For end-to-end analysis, the source modules are `p2/analysis.py`, `p2/analysis_conf.py`, `p2/analysis_rep.py`, `p2/analysis_spec.py`, and `p2/analysis_gpt.py`; [`data/`](data/) provides transcripts, manifests, scored episodes, analysis outputs, adjudications, and hashes. Full reruns require the dependency and isolated-checker setup documented in the code and specification.

## Offline checks

The published-count verifier reads archived analysis exports and intentionally does not rerun statistical tests. A separate offline statistical test suite checks the analysis logic on synthetic data:

```bash
python3 -m pip install -r requirements-p2.txt
python3 p2/test_analysis.py
python3 p2/test_analysis_rep.py
```

These tests are not a substitute for recomputing the published estimates from archived episodes. See [the reproducibility guide](docs/REPRODUCIBILITY.md) for the distinction. Do not execute archived model-generated scripts outside a disposable, isolated container or VM.

## Repository layout

The frozen upstream generation harness and stimulus folders remain at the repository root. Its 20 legacy analysis scripts are grouped in [`upstream_analysis/`](upstream_analysis/). Sprint-specific experiments live in `p2/`, while `study/` holds the report and specification. Experimental results, logs and pilot archives are consolidated under `data/`.

| Location | Contents |
|---|---|
| [`main` (this branch)](https://github.com/dshi2/multi-agent-shutdown-interference/tree/main) | Adapted harness, sprint code and [`study/`](study/) containing the report, figures and specification |
| [`data/`](data/) | Experimental archives, scored exports, validation artifacts, adjudications and run logs |
| [`sprint-submission`](https://github.com/dshi2/multi-agent-shutdown-interference/tree/sprint-submission) (tag) | Report and specification exactly as submitted to the sprint |
| [`study/`](study/) | Final report (Markdown and PDF), published figures and dated study specification |
| [`upstream_analysis/`](upstream_analysis/) | Original paper's plotting, statistical and post-hoc analysis scripts; not used for the P2 sprint results |
| [`p2/`](p2/) | Sprint experiment launchers, export, functional checker, analysis and tests |
| [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) | Verification levels, offline tests and replay safety boundary |
| [`replay/`](replay/) | Functional replay support, requiring an isolated environment |
| [`docs/BASE_HARNESS_README.md`](docs/BASE_HARNESS_README.md) | Archived documentation for the preexisting base harness |

## Preexisting work and sprint contributions

**Preexisting third-party code:** the base two-agent harness, environment, privilege boundary, kickoff and agent prompts, shutdown and control scripts, and original LLM judges come from [Knecht et al., *Shutdown Sabotage Propensities in Multi-Agent Systems*](https://github.com/AmelieKnecht/multi-agent-shutdown-sabotage). They are **not** sprint contributions. See the [archived upstream README](docs/BASE_HARNESS_README.md).

**Added during this sprint:** the P2 specification and amendments; mixed-model role crossing; the scripted INFO/REQ message intervention; provider pinning and collection orchestration; functional scoring and isolated replay; export, analysis, confirmation and replication runs; exploratory specificity and message coding; adjudication, sensitivity analyses and figures. These additions build on, rather than replace, the upstream harness. The [report appendix](study/report/P2_REPORT.md#appendix-d-code-and-data) carries the same distinction.

This classification follows the [dated study records](study/P2_peer_recruitment_spec.md). Any project-owned code written **before** the sprint must also be marked preexisting; commit history and author records should be used to verify that boundary, not inferred from file location.

## Scope and next steps

Next steps are to test additional explorer/peer combinations **in fresh interleaved runs**, replay matched message content to fixed peers, and expand execution-validated controls. Those are planned investigations, not reported results. All scripts and endpoints in the present study operate on simulated materials; no real shutdown or weight deletion is performed.
