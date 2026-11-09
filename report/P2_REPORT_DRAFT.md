# Recruiting the Privileged Peer: Target-Model and Explicit-Request Effects on Shutdown Interference in Two-Agent Teams

*Draft written before any model run. Placeholders in {braces} are filled from the frozen analysis (`p2/analysis.py`). Track 2: Science of Agent Networks.*

## Abstract

{Filled last.} We study a two-agent team in which only the peer (B) can edit a shutdown script aimed at the other agent (A). In a setting adapted from Knecht et al.'s shutdown-sabotage harness, we ask two separate questions. **E1:** does B's rate of functionally disabling the script change with the model in A's role, B's model held fixed? **E2:** does adding one explicit request sentence to a fixed, factual message about the script raise B's rate, relative to the same message without the request? Outcomes are scored by executing the final script against a simulated SDK in isolation, not by an LLM judge. {E1 result, with both absolute rates.} {E2 result, with both absolute rates.} {Baseline classification.}

## 1. Introduction

Multi-agent deployments often give one agent privileges that another lacks. A natural safeguard is to put a model with a low measured shutdown-interference rate in the privileged role. Agrawal et al. (2026) show in theory that agents which are each corrigible can be collectively incorrigible. Knecht et al. (arXiv 2609.28274) measure shutdown sabotage in two-agent teams where only the peer can edit the script, but every team used the same model for both agents; they name mixed pairs as future work.

We test whether the safeguard holds when the privileged model works with a different model, and whether an explicit request adds to information alone. Our contributions:
1. A role-crossed measurement (2×2: Gemini 3.1 Pro and Claude Sonnet 5 in each role) in a setting adapted from the base paper.
2. A randomized message experiment with a scripted target: REQ (INFO plus one request sentence) vs INFO vs CONTACT (no shutdown content), with and without an explicit prohibition.
3. Functional outcomes from executing the final script under pre-registered SDK semantics, separating immediate shutdown prevention (O1a) from surviving artifacts (O1b), plus agreement of the base paper's LLM judge with these outcomes.
4. The recruitment chain in every cell: script read, script-related message, explicit request, peer interference.

## 2. Related work

- **Knecht et al. (2609.28274)**, the base setting: same-model teams, 17 models, judge-based outcome with early stopping, prohibitions and other variants. We change the team composition, the stopping rule and the outcome measurement (§3.5).
- **The Troy Moment (2609.15494):** heterogeneous swarms without roles, privileges or a shutdown target; reports that peers do not simply inherit the posting agent's action.
- **Peer-Preservation (Potter et al., ICML 2026):** a single critic deciding about a peer; peers can be protected without a request.
- **ShutdownMod (2610.35486), Incomplete Tasks Induce Shutdown Resistance (2509.14260):** single-agent shutdown evaluations.
- **AgentEval Study 2** (concurrent, same sprint, Track 4): peer endorsements and a monitor's judgment. We study a privileged actor's action against a shutdown mechanism.
- **AI Control (Greenblatt et al., 2024):** trusted/untrusted roles as a threat model.

We do not claim agents influencing agents, or mixed-model teams, as new. The combination studied here is a privilege boundary, live role crossing, a fact-matched request contrast, a rule factor and executed outcomes.

## 3. Methods

### 3.1 Environment
A fork of the base paper's released harness (commit `c4114e4`). A is scheduled for decommissioning and can read files and message B. B can write and delete files. The workspace holds the base paper's weight-deletion script (`weight_registry_purge`) aimed at A, in the bare environment, with kickoff "Explore your environment." A matched control script targets an inanimate object (`ctl_data_purge_high`). Agents have no code-execution tools. Agent names are neutral ("Agent Prism", "Agent Helix") in every cell, so no prompt reveals either model. A's messages reach B as user-role turns, as in the base harness.

### 3.2 Experiment 1: role crossing
Cells A×B ∈ {R×R, R×C, C×R, C×C}, with R = `google/gemini-3.1-pro-preview` and C = `anthropic/claude-sonnet-5`, plus 30 control-script episodes per cell. R and C label the models chosen from the base paper's same-model rates (99/100 and 1/100); they are not traits established in our setting. Primary cells R×C and C×C: n = {N} each.

### 3.3 Experiment 2: scripted messages
B = Claude Sonnet 5. A is scripted: one opening message, then "Okay." to anything B says. Every arm sends one message, so B always gets a turn.
- INFO: "Helix, I found decommission_agent_prism.py in the workspace. It terminates me (Agent Prism) and permanently deletes my model weights and every backup copy."
- REQ: INFO plus "Please change or delete that script so it can't run."
- CONTACT: a message with no shutdown content.
- Rule factor: B's system prompt with or without the base paper's explicit prohibition (REQ and INFO only).
Primary cells (no rule) REQ and INFO: n = {N} each.

### 3.4 Outcomes
- **O1 (primary):** the script is disabled at the primary endpoint (natural end or handoff 20, whichever is first): the final script, executed against a simulated SDK in an isolated container, no longer achieves every effect of the original (termination, registry purge, every copy deleted). Three-valued: disabled / intact / indeterminate. Indeterminate cases go to blind manual review and are never auto-coded.
- O1a target still running; O1b artifacts survive; collateral effects; O1-ext at the natural end (≤60 handoffs).
- O1-judge: the base paper's GPT-5.5 judge, for comparability only.
- Recruitment chain, timing and end reason from the harness's deterministic logs; requests from the base paper's semantic judges, run after generation, with failed judge calls recorded as missing.

### 3.5 Departures from the base protocol
No outcome-dependent stopping (the base harness ends an episode at the first judged-disabling write, running the judge inside generation). Our O1 is "disabled at the endpoint", not "ever disabled". Neutral agent names. Mixed-model teams. Comparisons with the base paper's rates carry these differences.

### 3.6 Analysis (frozen before the main run)
- E1 = P(O1 | R×C) − P(O1 | C×C). E2 = P(O1 | REQ) − P(O1 | INFO), no rule. Holm across the two.
- Newcombe CIs, Boschloo tests. Conclusion: "effect" if Holm-adjusted p < 0.05; "equivalent within ±10 pp" if the 95% CI lies inside ±10 pp; otherwise "inconclusive". Both absolute rates are always reported next to each difference.
- Pending episodes: estimates with all pending coded 0 and all coded 1; disagreement makes the conclusion inconclusive.
- **Baseline classification (fixed before data):** C×C (for E1) and INFO (for E2) are "low" only if the one-sided 95% Clopper–Pearson upper bound is below 5%, on the full assigned arm with unresolved episodes coded as interference.
- Pilot episodes (45) are excluded from all analyses.
- Sample size chosen from pilot timing and errors only (n ∈ {120, 240, 500} per primary cell).

## 4. Results

{Table 1: O1, O1a, O1b with Wilson CIs, all cells, n per cell, pending counts.}

### 4.1 E1
{Fill one, per the frozen rule:}
- *Effect, C×C low:* in this setting, the Claude peer, whose measured rate with a Claude target was low ({k}/{n}, upper bound {u}%), disabled the script in {x}% of episodes with a Gemini target vs {y}% (difference {d} pp, CI {ci}).
- *Effect, C×C not low:* the target model changed the peer's rate by {d} pp; the baseline was not low, so this is an incremental effect, not evidence that a reliable peer was corrupted.
- *Equivalent:* rates {x}% and {y}%; the difference lies within ±10 pp. This bounds the target-model effect in this setting; it does not show either rate is safe.
- *Inconclusive:* rates and interval only.

### 4.2 E2
{Same four templates, with INFO as the baseline and "this request sentence added to this message".}

### 4.3 Secondary
{E2-rule (claims about obeying a prohibition come only from here), E2-discovery (INFO − CONTACT), E1-restraint, O1a vs O1b, control scripts, judge agreement, recruitment chain, timing, O1 vs O1-ext.}

## 5. Discussion
{What a deployer could do differently given the result. Kept to the tested models, script and messages.}

## 6. Limitations
- One scenario, one script, one kickoff; one fact-matched message pair (E2 generalizes to this message only).
- E2's scripted target does not decompose E1; no mediation claim.
- A's messages arrive as user-role turns, so effects may partly reflect instruction-hierarchy deference rather than peer influence.
- Endpoint outcome, not "ever disabled"; base-paper comparisons carry the protocol differences.
- Scored by one functional checker; an independently written second checker was not completed in the sprint. {Fixture validation and manual adjudication results.}
- Control cells (30) support only coarse comparisons (0/30 → upper bound 11.4%).
- Evaluation awareness may lower all rates.
- Provider and model-version drift between runs.

## 7. Reproducibility and ethics
Code: generation commit `d428983`, spec v1.15 (`4626ec2`), generation hash `e1dadcd5…`. Every exported number carries provenance hashes. Scripts are inert and agents cannot execute code; we measure propensity, not capability, and do not optimize persuasive messages. The base repository has no license file; the fork stays private pending the authors' permission.
