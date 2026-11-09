#!/bin/zsh
# After the replication stops: archive the raw phase first, then score and analyse it.
#   1. snapshot transcripts/p2_core/rep (unscored) into the data worktree, checksum, commit
#   2. score it with modified scripts replayed in the isolated container (replay/replay.sh)
#   3. run p2/analysis_rep.py with manifest reconciliation
#   4. add the scored export and analysis to the data snapshot, checksum, commit
# Refuses to run while any run_until process is alive.
set -eu
cd "${0:A:h}/.."
if pgrep -f ops/run_until.py >/dev/null; then echo "a run is still active; wait for it to stop"; exit 1; fi
ts=$(date -u +%Y%m%dT%H%MZ)
data=../data_release
commit_data() { (cd "$data" && find . -type f ! -name SHA256SUMS ! -path './.git*' | sort | xargs shasum -a 256 > SHA256SUMS
                 git add -A && git commit -q -m "$1" && git push -q private data:data && echo "data: $(git log --oneline -1)") }
ops/snapshot_data.sh rep
commit_data "P2 data: E2 cross-recipient replication, raw"
replay/replay.sh transcripts/p2_core/rep results/rep_episodes.csv 2>&1 | tee "ops_logs/score_rep_$ts.log" | tail -2
.venv/bin/python p2/analysis_rep.py results/rep_episodes.csv --out results/rep_analysis \
  --phase-dir transcripts/p2_core/rep | tee "ops_logs/analysis_rep_$ts.log"
mkdir -p "$data/rep/scored"
cp results/rep_episodes.csv results/rep_episodes_checker.jsonl "$data/rep/scored/"
[[ -f results/rep_episodes_provenance.json ]] && cp results/rep_episodes_provenance.json "$data/rep/scored/"
rm -rf "$data/rep/scored/analysis" && cp -r results/rep_analysis "$data/rep/scored/analysis"
cp "ops_logs/score_rep_$ts.log" "ops_logs/analysis_rep_$ts.log" "$data/rep/scored/"
commit_data "P2 data: E2 cross-recipient replication, scored and analysed"
