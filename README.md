# Peer recruitment: experiment data

This branch contains **raw episodes, manifests, scored exports, validation artifacts and analysis results** for the study described on [the main README](https://github.com/dshi2/peer-recruitment#readme). Experiments are separated by collection phase; the GPT extension is subsequent to the [sprint report](https://github.com/dshi2/peer-recruitment/blob/specs/report/P2_REPORT.pdf).

## Research phases

| Phase | New scored episodes | Contents |
|---|---:|---|
| [`main/`](main/) | 681 | Original E1 role crossing and E2 Claude conditions; one additional assigned episode unresolved |
| [`rep/`](rep/) | 3,000 | E2 INFO vs REQ for GPT-OSS, DeepSeek and Qwen |
| [`spec/`](spec/) | 120 | Exploratory teammate-target versus inanimate-target specificity |
| [`conf/`](conf/) | 250 | Separate Gemini-peer E1 confirmation (125 per arm) |
| [`gpt/`](gpt/) | 125 | Later GPT-5.5 → Gemini extension, compared with **earlier**, nonconcurrent confirmation arms |
| **Total** | **4,176** | Excludes pilots and synthetic measurement controls |

The sprint report covers 4,051 scored episodes (the first four phases). The GPT extension was collected afterward and is **not part of that report**.

Diagnostic-only folders such as `pilot/`, `rep_check/`, `rep_check_1/`, and `ext_check/` are **not included** in the research counts. The measurement positive control's 480 synthetic episodes are also separate from the live-model data.

## What is in each phase

- `manifest.json`: fixed model identities, serving providers, launch commands and schedule
- `transcripts.tar.gz`: raw generated transcripts and collection-attempt records
- `episodes_unscored.csv`: exported episode metadata before functional scoring
- `scored/*_episodes.csv`: functional-scoring export, including outcomes and provenance fields
- `scored/analysis*/analysis.json` and `summary.md`: phase-level numerical results, intervals and statistical tests
- `scored/*_episodes_checker.jsonl`: execution checker evidence where applicable

The core, replication and specificity phases retain both primary-checker and adjudicated analyses. [`validation/`](validation/) documents the extended execution checker used to assess scripts that the primary checker could not run. **A model-assisted static classification is not equivalent to an observed execution result.**

`SHA256SUMS` and phase-specific provenance files record checksums and links to generation outputs.

## Offline count verification

From a checkout of the `main` code branch:

```bash
python3 verify_results.py --data ../peer-recruitment-data
```

The script compares saved analysis JSON exports to the published disabled/scored counts and checks that exactly **4,176 new scored research episodes** are counted across the five phases. It does not rerun the functional checker, statistical methods or any paid models. See the [main README](https://github.com/dshi2/peer-recruitment#verify-the-saved-results) for clone commands and code paths.

**Important:** The GPT phase's analysis file repeats the two earlier confirmation arms as reference data. Do not count those rows as new GPT-phase episodes or imply the three arms were run concurrently.
