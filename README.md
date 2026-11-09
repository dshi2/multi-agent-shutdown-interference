# P2 Peer Recruitment: data

Raw episode data for the P2 experiments, kept apart from the harness code (branch `main`).
Every folder is a snapshot of one phase, written by `ops/snapshot_data.sh` in the harness.

| Folder | What it is |
| --- | --- |
| `pilot/` | Pilot, 45 episodes, generation only |
| `main/` | Core run (E1 2×2 crossing and E2 arms), stopped at the end of round 3 |
| `rep_check_1/`, `rep_check/` | Diagnostic checks for the E2 cross-recipient replication; never analysed |
| `ext_check/` | Diagnostic check for the withdrawn GPT-5.5 extension; never analysed |
| `rep/` | E2 cross-recipient replication (gpt-oss-120b, DeepSeek V4.1 Flash, Qwen3.7-plus) |
| `ops_logs/` | Launch logs and account-balance readings |

Each phase folder holds:

- `transcripts.tar.gz`: the phase directory as generated (transcripts, `attempts.jsonl`,
  `failures.jsonl`, per-cell launcher logs, manifest), unmodified.
- `manifest.json`: models, provider pins, schedule, commands and the generation code hash.
- `episodes_unscored.csv`: one row per started episode from `p2/export.py --unscored`. No
  checker runs and nothing from a transcript is executed; outcomes are `unscored`.

Scored exports and analysis outputs are added when scoring has run in the isolated backend.
`SHA256SUMS` lists a checksum for every file.
