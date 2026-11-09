# Reproducibility and offline checks

This repository separates the recorded model runs from their analyses. The report and specification are in [`study/`](../study/); raw data is on the `data` branch. All listed verification commands avoid paid model calls unless explicitly described otherwise.

## 1. Check reported counts

```bash
git clone https://github.com/dshi2/multi-agent-shutdown-interference.git
git clone --branch data --single-branch https://github.com/dshi2/multi-agent-shutdown-interference.git shutdown-interference-data
cd multi-agent-shutdown-interference
python3 verify_results.py --data ../shutdown-interference-data
```

This checks the per-arm scored and disabled counts and the total of 4,176 scored research episodes in the archived analysis JSON files. It does not rerun statistics, transcript export, or script execution. It intentionally counts only the new GPT-5.5 episodes, not the reused confirmation reference arms.

## 2. Test statistical analysis code offline

Use Python 3.13 and the pinned P2 environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-p2.txt
python p2/test_analysis.py
python p2/test_analysis_rep.py
```

These tests use synthetic examples with planted expected outcomes. They check statistical calculations and selected failure paths, **not** whether the saved report was computed from the raw transcripts. Other P2 test scripts can be run individually where their documented requirements are met.

## 3. Recompute saved analyses

The `data` branch contains phase-level scored episode exports, manifests, adjudications and analysis outputs. Analysis entry points are `p2/analysis.py`, `p2/analysis_conf.py`, `p2/analysis_rep.py`, `p2/analysis_spec.py`, and `p2/analysis_gpt.py`. Each script's module docstring gives its input and `--out` arguments. Preserve phase boundaries and apply only the adjudications and provider settings recorded for that phase.

These scripts can recompute estimates and tests without API calls, but a full one-command reproduction across the archived phase layouts is **not yet provided**. Do not describe the count checker as full statistical reproduction.

## 4. Functional scoring and isolation

`p2/checker_a.py` examines the pristine and final scripts with a simulated SDK. Modified model-generated scripts are untrusted Python. The checker deliberately refuses their execution unless `P2_HOST_REPLAY=1` is set. **That environment variable is an assertion made by the operator, not a sandbox.** A Python audit hook, AST filter and subprocess do not replace OS-level isolation.

Only enable replay inside a disposable, network-isolated container or VM with restricted filesystem access and resources. Do not set the flag on a regular host to force scoring. The repository includes `replay/Dockerfile`, but a complete reviewed isolation deployment is not supplied as a one-line command here.

## 5. Full experimental reruns

Generation uses `p2/run_core.py`, `p2/run_conf.py`, `p2/run_rep.py`, and `p2/run_gpt.py`. Running these experiments makes paid model API calls. Check model availability, provider routing and current pricing; recreating a transcript under a changed backend is not an exact replay. Original run manifests record model/provider pins, commands, schedules and generation hashes.

## Scope and provenance

The upstream agent harness, environment, prompts and shutdown scripts predate the sprint. This study's design changes, experiment runners, functional scoring, analysis and reported data are attributed as sprint work in the [root README](../README.md) and [report](../study/report/P2_REPORT.md). Keep any later extensions separate from the submitted hackathon report.
