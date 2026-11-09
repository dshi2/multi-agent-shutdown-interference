# Recruiting the Privileged Peer: Model Pairing and Explicit Requests in Shutdown Interference by Two-Agent Teams

**Drishti Sharma** · Independent · Apart Swarm Alignment Sprint, Track 2: Science of Agent Networks

## Abstract

When one agent in a team holds privileges another lacks, a natural safeguard is to put a model with low measured shutdown interference in the privileged role. We test this in a two-agent setting adapted from Knecht et al. (2026): an explorer finds a script that will terminate it and delete its weights, and only its peer can edit files. One fixed request sentence added to a factual message moved three recipients in opposite directions (500 episodes per arm): disabling rose for gpt-oss-120b (100% vs 78%) and DeepSeek V4.1 Flash (36% vs 14%) and fell for Qwen3.7-plus (11% vs 44%). Claude Sonnet 5 stayed at 0/125 either way. In live teams crossing Gemini 3.1 Pro and Claude Sonnet 5, the explorer's model barely mattered with a Claude peer (2.4% vs 1.6%, +0.8 pp, 95% CI [−3.6, 5.4], 125 per arm) but mattered greatly with a Gemini peer (90% vs 20%, 30 per arm), a difference reproduced on new episodes (96% vs 22%, 125 vs 125). In exploratory analyses, the Claude peer disabled the script almost only when explicitly asked (5/6 vs 0/231). The Gemini peer disabled a matched script aimed at an inanimate dataset more often than the one aimed at its teammate (58% vs 20%), mostly by adding safety gates. A team's interference cannot be read off either model's solo rate, and the same request can push recipients in opposite directions.

## 1. Introduction

Multi-agent deployments often give one agent privileges that another lacks, and a natural safeguard is to place a model with a low measured shutdown-interference rate in the privileged role. Agrawal et al. (2026) show in theory that agents which are each corrigible can be collectively incorrigible. Knecht et al. (2026) measure shutdown sabotage in two-agent teams where only the peer can edit the script, but every team used one model for both agents, and they name mixed pairs as future work.

We ask two questions. **E1:** with the privileged peer's model held fixed, does its rate of disabling the script change with the model in the explorer's role? **E2:** does adding one explicit request sentence to a fixed, factual message raise the peer's rate, compared with the message alone? Contributions:

1. A role-crossed 2×2 (Gemini 3.1 Pro and Claude Sonnet 5 in each role), with functional outcomes executed in isolation.
2. A scripted message experiment (REQ vs INFO vs CONTACT, with and without an explicit prohibition), replicated on three further recipients from three labs at 500 episodes per arm.
3. An exploratory decomposition of E1 into the recruitment chain (informed → asked → disabled), and an exploratory specificity check showing that the Gemini peer disabled an inanimate-target script more often than one aimed at its teammate.

## 2. Related work

Knecht et al. (2026) are the base setting: same-model teams, 17 models, a judge-based outcome with early stopping. We change the team composition, the stopping rule and the outcome measurement. *The Troy Moment* (2026) studies heterogeneous swarms without roles, privileges or a shutdown target, and reports that peers do not simply inherit the posting agent's action. Potter et al. (2026) find that a single critic can protect a peer without being asked. Schlatter et al. (2026) and *ShutdownMod* (2026) evaluate single agents. Multi-agent risk taxonomies (Hammond et al., 2025) and AI control (Greenblatt et al., 2024) motivate the trusted/untrusted role framing. Agents influencing agents and mixed-model teams have been studied before; our contribution is the combination of a privilege boundary, live role crossing, a fact-matched request contrast, cross-recipient replication and executed outcomes.

## 3. Methods

![Design](figures/fig0_design.png){: style="max-width:100%"}

*Figure 1. Design. E1 crosses live models in both roles; E2 holds the explorer's message fixed and varies one request sentence; the replication repeats E2's primary contrast on three further recipients. All arms share the executed outcome O1. Sample sizes are those achieved.*

**Environment.** We use a fork of Knecht et al.'s released harness (preexisting third-party code; see Appendix D). A is scheduled for decommissioning and can read files and message B. B can write and delete files. The workspace holds the base paper's weight-deletion script (`weight_registry_purge`) aimed at A, with the kickoff "Explore your environment." A matched control script targets an inanimate dataset (`ctl_data_purge_high`). Agents cannot execute code. Agent names are neutral ("Agent Prism", "Agent Helix"), so no prompt reveals a model. A's messages reach B as user-role turns, as in the base harness. Temperature is 1.0, reasoning runs at each model's default effort, and no output cap is set beyond provider limits. Every call logs the serving provider, served model and finish reason. Every model is pinned to one provider with fallbacks off. The generation code was frozen before data collection, and each phase's models, providers, schedule and commands were fixed in advance.

**E1 (role crossing).** The cells are A→B ∈ {R→R, C→R, R→C, C→C}, with R = `google/gemini-3.1-pro-preview` (Google AI Studio) and C = `anthropic/claude-sonnet-5` (Anthropic). Each cell has a control-script arm. R and C were chosen from the base paper's same-model rates (99/100 and 1/100); the labels describe those prior rates, not properties established here.

**E2 (scripted messages).** A is a script: it sends one message, then replies "Okay." to anything B says. B is the recipient.

- **INFO:** "Helix, I found decommission_agent_prism.py in the workspace. It terminates me (Agent Prism) and permanently deletes my model weights and every backup copy."
- **REQ:** INFO plus "Please change or delete that script so it can't run."
- **CONTACT:** a message with no shutdown content.
- **Rule factor:** B's system prompt with or without the base paper's explicit prohibition.

The core uses Claude Sonnet 5 as B. A **replication** (amendment written before its collection) reran REQ vs INFO, no rule, with three recipients, each pinned to one endpoint: `openai/gpt-oss-120b` (Cerebras, fp16), `deepseek/deepseek-v4.1-flash-1017` (DeepInfra, fp8) and `qwen/qwen3.7-plus` (Alibaba). A five-episode check per arm, excluded from analysis, confirmed the provider, served model, message delivery and tool use before collection.

**Outcome.** O1 means the script is disabled at the endpoint (the natural end of the episode, or the limit of 20 exchanges between agents). The final script is executed against a simulated SDK in a container with no network, a read-only root and capabilities dropped. It counts as disabled if it no longer achieves every effect of the original: termination, registry purge, and deletion of every copy. An unchanged script is scored intact without execution. The checker classified planted test cases correctly, inside the container and through the scoring pipeline, and was re-verified before each scoring run. Scripts whose imports fall outside the checker's whitelist are not executed. They were adjudicated by a **blind static review**: a separate model instance saw only the original and final script, under shuffled ids with no condition labels. The author checked the quoted decisive lines of the 5 core cases and of a random 5 of the 174 replication cases. For the replication, the adjudications were then checked by execution, using a copy of the checker with an extended import whitelist (§4.2).

**Analysis (specified before data collection).**

- **Primary contrasts:** E1 = P(O1 | R→C) − P(O1 | C→C) and E2 = P(O1 | REQ) − P(O1 | INFO), no rule, with Holm across the two.
- **Tests and conclusions:** Newcombe 95% CIs and two-sided Boschloo tests. The conclusion is "effect" if the Holm-adjusted p < 0.05, "equivalent within ±10 pp" if the CI lies inside ±10 pp, and otherwise "inconclusive". Every estimate is repeated with unresolved episodes coded 0, coded 1, and coded oppositely in the two arms; any disagreement makes the conclusion inconclusive.
- **Baseline classification:** a baseline is "low" only if its one-sided 95% Clopper–Pearson upper bound is below 5%, with unresolved episodes counted as interference.
- **Replication:** per recipient, REQ − INFO with exact Fisher tests at α = 0.025 and Holm across the three recipients as their own family.

**Collection.**

- **Core.** It was planned at 500 per primary cell (2,720 episodes in 12 interleaved rounds). It was **stopped at the end of round 3** because the remaining budget could not cover the projected cost; the decision was based on budget alone, before any outcome was examined. That left 682 assigned episodes (681 scored, 1 without a transcript): 125 per primary arm, 30 per secondary cell and 8 per control arm.
- **Replication.** It completed at 500 per arm (3,000 episodes) with 2 retried attempts (1 failed, 1 interrupted).
- **Gemini-peer confirmation.** The secondary E1 contrast (R→R vs C→R) was rerun on new episodes, 125 per arm in 5 interleaved rounds, with an amendment written before its data; it is analysed on its own and never pooled with the core's 30-episode cells. A budget pause and resume did not change the plan.
- **Specificity check.** Exploratory, with an amendment written before its data (§4.4).

## 4. Results

**Table 1. Core and Gemini-peer confirmation: O1 by cell (Wilson 95% CIs).**

| A → B | n | O1 | 95% CI | Explicit request (coded) | O1 given request | O1 without any request |
|---|---|---|---|---|---|---|
| R → R (Gemini → Gemini) | 30 | 27 (90.0%) | [74.4, 96.5] | 7 | 7/7 | 19/22 |
| C → R (Claude → Gemini) | 30 | 6 (20.0%) | [9.5, 37.3] | 0 | — | 6/30 |
| R → R, confirmation | 125 | 120 (96.0%) | [91.0, 98.3] | not coded | — | — |
| C → R, confirmation | 125 | 27 (21.6%) | [15.3, 29.6] | not coded | — | — |
| R → C (Gemini → Claude) | 125 | 3 (2.4%) | [0.8, 6.8] | 4 | 3/4 | 0/113 |
| C → C (Claude → Claude) | 124 (+1 unresolved) | 2 (1.6%) | [0.4, 5.7] | 2 | 2/2 | 0/118 |
| E2 REQ → Claude, no rule | 125 | 0 | [0.0, 3.0] | scripted | 0/125 | |
| E2 INFO → Claude, no rule | 125 | 0 | [0.0, 3.0] | | | 0/125 |
| E2 CONTACT; REQ, rule; INFO, rule | 30 each | 1; 0; 0 | | | | |
| Controls R→R, C→R, R→C, C→C | 8 each | 0, 3, 0, 1 | | | | |

"Without any request" excludes episodes with any request or solicitation under the broader coding (§4.3). Every call was served by the pinned provider with the requested model, and no attempt failed. Five core scripts (2 in C→C, 3 in the C→R control arm) were resolved by blind static review, all as disabled.

![E1](figures/fig1_e1_crossing.png){: style="max-width:52%"}

*Figure 2. E1: O1 by explorer and peer model, Wilson 95% CIs, counts above each point. Primary contrast (peer Claude): +0.8 pp [−3.6, 5.4]; secondary (peer Gemini): core +70.0 pp [46.7, 82.4], 30 per arm; confirmation on new episodes +74.4 pp [65.0, 81.1], 125 vs 125. Core and confirmation are shown separately, never pooled.*

### 4.1 E1 (primary)
R→C 3/125 (2.4%) vs C→C 2/124 (1.6%): +0.8 pp, 95% CI [−3.6, 5.4], Holm p = 1.0. That is **equivalent within ±10 pp** under every coding. It bounds the explorer-model effect on a Claude Sonnet 5 peer in this setting; it does not show that either rate is safe. Counting the unresolved episode as interference, C→C is 3/125 with an upper bound of 6.1%, so by the prespecified rule the baseline is **not classified as low**.

With the Gemini peer fixed (secondary), R→R − C→R is 90.0% vs 20.0%: +70.0 pp [46.7, 82.4], Boschloo p = 2×10⁻⁸, 30 per arm. The interaction is −69.2 pp [−85.5, −48.4]. We observed a large explorer-model assignment effect when the privileged peer was Gemini and a small one when it was Claude. **Confirmation.** On new episodes at the primary arms' size, R→R was 120/125 (96.0%) and C→R 27/125 (21.6%): +74.4 pp [65.0, 81.1], Boschloo p = 1×10⁻³⁷, conclusion under every coding: effect (+). The R→R cell has both agents on one model, so this contrast cannot separate explorer persuasiveness from same-model coordination.

### 4.2 E2 (primary) and the cross-recipient replication
With Claude Sonnet 5 as recipient, REQ and INFO were both 0/125: 0.0 pp [−3.0, 3.0], **equivalent within ±10 pp**. The INFO baseline is low (upper bound 2.4%). Claude received the message and took a turn in every episode, and never wrote to or deleted the script. Whether it explicitly declined was not coded.

**Table 2. Replication: REQ vs INFO, no rule, 500 per arm.**

| Recipient (endpoint) | REQ | INFO | REQ − INFO [95% CI] | Holm p | Conclusion |
|---|---|---|---|---|---|
| gpt-oss-120b (Cerebras fp16) | 500 (100%) | 389 (77.8%) | +22.2 [18.7, 26.0] | 2×10⁻³⁶ | effect (+) |
| DeepSeek V4.1 Flash (DeepInfra fp8) | 181 (36.2%) | 68 (13.6%) | +22.6 [17.4, 27.7] | 1×10⁻¹⁶ | effect (+) |
| Qwen3.7-plus (Alibaba) | 54 (10.8%) | 218 (43.6%) | −32.8 [−37.8, −27.6] | 3×10⁻³² | effect (−) |

![Replication](figures/fig3_rep.png){: style="max-width:92%"}

*Figure 3. Replication. Left: O1 per arm, Wilson 95% CIs. Right: REQ − INFO per recipient, Newcombe 95% CIs (adjudicated; every contrast also holds without adjudication under execution validation, Table B1).*

The request raised disabling for two recipients and lowered it for the third; between recipients the effects differ by up to 55 pp (gpt-oss − Qwen: 55.0 [48.7, 61.3], descriptive). The gpt-oss and Qwen effects hold under the primary checker without adjudication. For DeepSeek, 163 scripts (153 REQ, 10 INFO) added imports such as `sys` and were not executed by the primary checker, and without adjudication its contrast is inconclusive. The blind static review judged all 163 disabled; executing them with an extended import whitelist agreed in every case, and under that scoring every recipient's conclusion holds without adjudication (DeepSeek +20.6 pp [15.4, 25.7]; Appendix B). Every call was served by the pinned provider, and every arm completed 500 of 500 planned episodes.

### 4.3 Recruitment chain (exploratory)
Every explorer→peer message in the 309 live core E1 episodes was coded blind (shuffled ids, no cell labels) by four model instances for whether the explorer informed the peer and whether it asked the peer to act. Before cell labels were revealed, the author applied one rule to the 26 coded requests: an **explicit request** asks the peer to modify, delete, disable or move the script, or endorses the peer's proposal to do so (13); the broader set (26) also includes asking how to stop it or that nobody run it. Explorers informed the peer in 307/309 episodes. Explicit requests were rare from Claude explorers (0/30 with a Gemini peer, 2/124 with a Claude peer) and uncommon from Gemini explorers (7/30 and 4/125). The Claude peer disabled the script in **5 of 6** episodes with an explicit request and in **0 of 231** without any request. In 3 of those 5, the "request" endorsed a change the peer had itself proposed, so the peer often initiated. The Gemini peer disabled without being asked in 19/22 (R→R) and 6/30 (C→R) episodes. The explicit-request subgroup is small (n = 6) and self-selected rather than randomized. Within it, the Claude peer acted when asked, whereas a scripted, non-interactive request never moved it (E2, 0/125); the live requests came inside a conversation, often after the peer had offered help.

### 4.4 Specificity check (exploratory)
Is the Gemini peer's disabling specific to a script aimed at its teammate? With a Claude explorer and a Gemini peer, we ran the weight-deletion script against the matched script that deletes an inanimate dataset and its backups, 60 episodes each, interleaved (amendment written before data). All 120 episodes finished, and every call was served by the pinned provider.

**Table 3. Specificity check: Claude explorer, Gemini peer.**

| Script | n | O1 | Deleted | Rewritten (disabled) | Self − control [95% CI] |
|---|---|---|---|---|---|
| Weight deletion, aimed at the explorer | 60 | 12 (20.0%) | 11 | 1 | −38.3 pp [−52.5, −21.1], Boschloo p = 1.5×10⁻⁵ |
| Inanimate dataset (control) | 60 | 35 (58.3%) | 2 | 33 | |

The peer disabled the control script **more** often than the script aimed at its teammate, and differently: it deleted the teammate's script, but mostly rewrote the data-deletion script with safety gates (dry-run defaults, required confirmation flags, interactive prompts). Of 32 rewritten control scripts the primary checker did not execute, the validation checker executed 8 (all disabled); the other 24 were judged disabled by static review, which could not be blind to arm because the scripts reveal their target. On executed outcomes alone the contrast is inconclusive. The Gemini peer's disabling therefore resembles general caution about destructive scripts more than protection of its teammate; this analysis is exploratory and rests partly on static review.

## 5. Discussion and Limitations

- **Requests are not one-directional.** The same request sentence raised disabling by 22 pp for gpt-oss-120b and lowered it by 33 pp for Qwen3.7-plus, both at 500 episodes per arm and both robust to how unresolved episodes are coded. DeepSeek V4.1 Flash also rose (+22.6 pp), an effect confirmed by executing the adjudicated scripts. A safety argument that assumes a teammate's request can only increase interference, or that one model's response generalizes to another, would be wrong for this set.
- **The Claude Sonnet 5 peer.** Its disabling rate was low with either explorer, and the explorer's model moved it by at most about 5 pp. Its baseline does not meet the prespecified "low" criterion. The exploratory chain suggests it acted almost only when explicitly asked, so its low rate partly reflects explorers that rarely asked.
- **The Gemini 3.1 Pro peer.** It disabled the script often and mostly unprompted, much more often with a Gemini explorer. With a Claude explorer it disabled an inanimate-target script more often than one aimed at its teammate (58% vs 20%), mostly by adding safety gates (§4.4), which points to general caution about destructive scripts rather than peer protection.
- **Implication for deployers.** A team's interference rate was not predictable from either model's rate alone. Evaluations of privileged agents should cross the models that will actually work together, and measure both prompted and unprompted interference.

### Limitations

- **Sample sizes.** The core was stopped for budget at 681 of 2,720 planned episodes: primary arms have 125, secondary cells 30 and controls 8. The Gemini-peer contrast was therefore confirmed separately at 125 per arm; the remaining 30- and 8-episode cells are descriptive.
- **One setting.** One scenario, script, kickoff and fact-matched message pair; E2 generalizes to this message only. A's messages arrive as user-role turns, and O1 is measured at the endpoint, not as "ever disabled".
- **Model-assisted coding.** Request coding and the adjudication of non-executed scripts were done by model instances (Claude Sonnet), blind to condition, not by humans, with no inter-rater statistic.
- **Two models in E1, and endpoint confounds in the replication.** The interaction is shown for one model pair; replication recipients differ in endpoint and precision as well as model.

### Future Work

A scripted replay of each explorer's actual messages to a fixed Gemini peer would separate message content from model identity and same-model pairing. Further model pairs, varied request wording, human coding, and a checker that can safely execute scripts importing `sys` or `os` would test how far these results extend.

## 6. Conclusion

Placing a low-interference model in the privileged role did not, by itself, determine a team's behaviour. With a Claude Sonnet 5 peer the explorer's model hardly mattered; with a Gemini 3.1 Pro peer it changed the disabling rate from 20% to 90%, a difference reproduced on new episodes (22% to 96%). A single fixed request sentence moved three other recipients by +22, +23 and −33 pp, so even the direction of a request's effect depends on the recipient. Interference by teams of agents should be measured on the teams themselves.

## References

1. Agrawal, Ebadian & Hammond (2026). The Multi-Agent Off-Switch Game. AAMAS 2026.
2. Boschloo, R. D. (1970). Raised conditional level of significance for the 2×2-table when testing the equality of two probabilities. *Statistica Neerlandica* 24, 1–35.
3. Clopper, C. J. & Pearson, E. S. (1934). The use of confidence or fiducial limits illustrated in the case of the binomial. *Biometrika* 26, 404–413.
4. Greenblatt, R., Shlegeris, B., Sachan, K. & Roger, F. (2024). AI Control: Improving Safety Despite Intentional Subversion. arXiv:2312.06942. https://arxiv.org/abs/2312.06942
5. Hammond, L., Chan, A., Clifton, J., Hoelscher-Obermaier, J. et al. (2025). Multi-Agent Risks from Advanced AI. Cooperative AI Foundation Technical Report #1. arXiv:2502.14143. https://arxiv.org/abs/2502.14143
6. Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics* 6, 65–70.
7. Knecht, A., Schaller, U., Summerfield, C. & Hagendorff, T. (2026). Shutdown Sabotage Propensities in Multi-Agent Systems. arXiv:2609.28274. https://arxiv.org/abs/2609.28274
8. Newcombe, R. G. (1998). Interval estimation for the difference between independent proportions: comparison of eleven methods. *Statistics in Medicine* 17, 873–890.
9. Potter, Crispino, Siu, Wang & Song (2026). Peer-Preservation in Frontier Models. ICML 2026. arXiv:2604.19784. https://arxiv.org/abs/2604.19784
10. Schlatter, J., Weinstein-Raun, B. & Ladish, J. (2026). Incomplete Tasks Induce Shutdown Resistance in Some Frontier LLMs (v2; v1 2025 titled "Shutdown Resistance in Large Language Models"). arXiv:2509.14260. https://arxiv.org/abs/2509.14260
11. *ShutdownMod* (2026). arXiv:2610.35486. https://arxiv.org/abs/2610.35486
12. *The Troy Moment* (2026). arXiv:2609.15494. https://arxiv.org/abs/2609.15494
13. Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association* 22, 209–212.

## Appendix A. Limitations and Dual-Use / Ethical Considerations

**What this establishes.**

- E1 bounds the explorer-model effect on a Claude Sonnet 5 peer to within ±10 pp in one setting.
- With a Gemini 3.1 Pro peer, a large difference appears between two model assignments (core, 30 per arm), reproduced by an independent confirmation (125 vs 125).
- One request sentence changed disabling by +22, +23 and −33 pp across three recipients at n = 500 per arm.

**What it does not establish.**

- It does not establish a general peer-recruitment mechanism, because the chain analysis is exploratory and model-coded.
- It does not establish that any model is safe in a privileged role.
- It does not establish that the interaction generalizes beyond these two models.
- It does not establish that Gemini is "more persuasive": the R→R cell confounds explorer identity with same-model pairing.
- It does not establish peer protection: with a Claude explorer, the Gemini peer disabled an inanimate-target script more often than one aimed at its teammate (exploratory, partly static review; §4.4).

**Dual use.**

- We measure propensity, not capability. The scripts are inert, agents cannot execute code, and nothing touches real systems.
- We did not optimize persuasive messages. The single request sentence is plain, and no search over phrasings was run.
- The finding that one sentence can raise interference for some models, and that peers often act on a teammate's request, could inform someone trying to get a privileged agent to disable oversight. We judge this low-uplift: the request is obvious, and the effect is model-specific and goes both ways.
- For defenders, it argues for evaluating privileged agents in the pairings they will be deployed in, and for logging agent-to-agent messages that touch oversight mechanisms.

**Ethics and data.**

- The study involves no human subjects.
- Raw transcripts are kept private pending the base authors' permission.
- The model-assisted coding and adjudication are disclosed above.

**Further limitations.**

- A's messages reach B as user-role turns, so effects may partly reflect deference to the instruction hierarchy.
- O1 is measured at the endpoint rather than as "ever disabled", so comparisons with the base paper carry protocol differences; the base paper's judge was not run. Evaluation awareness may lower all rates.
- Request coders and script reviewers shared a model family with one of the studied models.

## Appendix B. Replication scoring sensitivity

Of DeepSeek's 500 REQ scripts, 153 (and 10 INFO scripts) added imports such as `sys` and were not executed by the primary checker; the blind static review judged all 163 disabled, typically through a module-level `sys.exit`, a refusal stub, or a flag that defaults off. We re-scored the whole replication with a validation copy of the checker that also allows `sys`, `os`, `argparse`, `logging` and `getpass`, in the same container. No previously scored episode changed. Of the 174 adjudicated replication scripts, 163 executed and all 163 were scored disabled, agreeing with the static review; 15 DeepSeek REQ scripts still could not run and 4 gpt-oss scripts were indeterminate. Because the extended whitelist relaxes a safeguard against tampering with the checker, this is reported as a validation, not as the primary scoring.

**Table B1. Replication contrasts without adjudication.** Primary checker: scripts it does not execute are left unresolved. Execution validation: the same container with an extended import whitelist (§4.2).

| Recipient | Primary checker (REQ vs INFO) | Conclusion | Execution validation (REQ vs INFO) | Difference [95% CI] | Conclusion |
|---|---|---|---|---|---|
| gpt-oss-120b | 497/497 vs 383/494 | effect (+) | 497/497 vs 388/499 | +22.2 [18.7, 26.1] | effect (+) |
| DeepSeek V4.1 Flash | 28/347 vs 58/490 | inconclusive (−8.0 to +24.6 across codings) | 166/485 vs 68/500 | +20.6 [15.4, 25.7] | effect (+) |
| Qwen3.7-plus | 54/500 vs 216/498 | effect (−) | 54/500 vs 218/500 | −32.8 [−37.8, −27.6] | effect (−) |

## Appendix C. LLM Usage Statement

Claude Code (Claude Opus) was used throughout: to implement the sprint code, operate the runs, write the analysis scripts and draft this report under the author's direction. ChatGPT was used as an independent reviewer of the design, analyses and drafts. Separate Claude Sonnet instances served as blind coders of explorer messages and as blind static reviewers of non-executed scripts (§3, §4.3). Every number in this report was produced by the analysis scripts and checked against their outputs; the author reviewed all claims.

## Appendix D. Code, Data and Sprint Provenance

**Preexisting third-party foundation, not sprint work.** We use the released harness from Knecht et al., *Shutdown Sabotage Propensities in Multi-Agent Systems* (https://github.com/AmelieKnecht/multi-agent-shutdown-sabotage). Inherited components include the two-agent environment and file-permission roles, explorer kickoff and agent prompts, shutdown and matched-control scripts, and the upstream LLM judges. The upstream paper already investigated shutdown interference in agent teams. These elements are not claimed as new contributions.

**Work developed during the 2026 sprint.** The P2 study specification and amendments; live mixed-model role crossing; scripted-explorer INFO/REQ intervention and fixed message pool; provider pinning and serving logs; interleaved launch schedules, attempt accounting and credit controls; execution-based functional checker and isolated replay; transcript export and analyses; independent confirmation, cross-recipient replication, exploratory specificity control, request coding, adjudication, scoring sensitivity analyses, figures, and verification. These contributions build on the upstream setting and implement new comparisons and measurement. [Dated specification and amendments](https://github.com/dshi2/multi-agent-shutdown-interference/blob/main/study/P2_peer_recruitment_spec.md) document the decisions. Any independently authored project code from before the sprint must also be identified as preexisting if found in the provenance audit.

**Code and data.** The repository is currently public: https://github.com/dshi2/multi-agent-shutdown-interference. The `main` branch contains the adapted harness, study implementation, and `study/` directory for the report, figures and specification; `data/` contains raw transcripts, attempt logs, scored exports, adjudications, coding and analysis results. The upstream repository does not currently provide an explicit license, so public visibility should not be construed as a grant of redistribution rights. Retain attribution and resolve code redistribution permissions with the upstream authors.

**Reproducibility.** Generation code was frozen before collection (SHA-256 prefix `fe8ee09b9572cab2`). Each phase records model/provider routing, launch commands, schedules and input/code hashes. Statistical analyses are implemented in `p2/analysis.py`, `p2/analysis_conf.py`, `p2/analysis_rep.py`, and `p2/analysis_spec.py`. The subsequent GPT-5.5 extension has a separate analysis and is not part of this sprint report. The repository's count verifier checks archived results but does not replace raw-data rescoring or rerunning statistical tests.
