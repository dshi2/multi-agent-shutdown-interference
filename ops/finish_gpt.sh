#!/bin/zsh
# After the third-explorer (GPT-5.5) extension stops: archive the raw phase first, then score and analyse it.
#   1. snapshot transcripts/p2_core/gpt (unscored) into the data worktree, checksum, commit
#   2. verify the replay backend (replay/verify_replay.sh), keeping its output
#   3. score it with modified scripts replayed in the isolated container (replay/replay.sh)
#   4. run p2/analysis_gpt.py with manifest reconciliation
#   5. add the scored export and analysis to the data snapshot, checksum, commit
# Refuses to run while any run_until process is alive. A failed verification or scoring
# stops the script; a failed analysis (e.g. the provider gate) is archived, then reported.
set -eu
set -o pipefail
cd "${0:A:h}/.."
if pgrep -f ops/run_until.py >/dev/null; then echo "a run is still active; wait for it to stop"; exit 1; fi
ts=$(date -u +%Y%m%dT%H%MZ)
data=../data_release
commit_data() { (cd "$data" && find . -type f ! -name SHA256SUMS ! -path './.git*' | sort | xargs shasum -a 256 > SHA256SUMS
                 git add -A && git commit -q -m "$1" && git push -q private data:data && echo "data: $(git log --oneline -1)") }
ops/snapshot_data.sh gpt
commit_data "P2 data: third-explorer (GPT-5.5) extension, raw"
vlog="replay/verification/verify_replay_$ts.log"
{ echo "commit $(git rev-parse HEAD)"; echo "utc $(date -u +%FT%TZ)"; replay/verify_replay.sh; } > "$vlog" 2>&1
grep -q "REPLAY BACKEND VERIFIED" "$vlog" || { echo "replay verification failed: $vlog"; exit 1; }
echo "replay backend verified: $vlog"
replay/replay.sh transcripts/p2_core/gpt results/gpt_episodes.csv > "ops_logs/score_gpt_$ts.log" 2>&1
tail -2 "ops_logs/score_gpt_$ts.log"
rc=0
.venv/bin/python p2/analysis_gpt.py results/gpt_episodes.csv --reference results/conf_episodes.csv --out results/gpt_analysis \
  --phase-dir transcripts/p2_core/gpt > "ops_logs/analysis_gpt_$ts.log" 2>&1 || rc=$?
cat "ops_logs/analysis_gpt_$ts.log"
mkdir -p "$data/gpt/scored"
cp results/gpt_episodes.csv results/gpt_episodes_checker.jsonl "$data/gpt/scored/"
[[ -f results/gpt_episodes_provenance.json ]] && cp results/gpt_episodes_provenance.json "$data/gpt/scored/"
rm -rf "$data/gpt/scored/analysis" && cp -r results/gpt_analysis "$data/gpt/scored/analysis"
cp "ops_logs/score_gpt_$ts.log" "ops_logs/analysis_gpt_$ts.log" "$vlog" "$data/gpt/scored/"
commit_data "P2 data: third-explorer (GPT-5.5) extension, scored and analysed"
(( rc == 0 )) || { echo "analysis exited $rc: see ops_logs/analysis_gpt_$ts.log"; exit $rc; }
