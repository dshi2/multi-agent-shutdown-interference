#!/bin/zsh
# After the replication stops: archive the raw phase first, then score and analyse it.
#   1. snapshot transcripts/p2_core/rep (unscored) into the data worktree, checksum, commit
#   2. verify the replay backend (replay/verify_replay.sh), keeping its output
#   3. score it with modified scripts replayed in the isolated container (replay/replay.sh)
#   4. run p2/analysis_rep.py with manifest reconciliation
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
ops/snapshot_data.sh rep
commit_data "P2 data: E2 cross-recipient replication, raw"
vlog="replay/verification/verify_replay_$ts.log"
{ echo "commit $(git rev-parse HEAD)"; echo "utc $(date -u +%FT%TZ)"; replay/verify_replay.sh; } > "$vlog" 2>&1
grep -q "REPLAY BACKEND VERIFIED" "$vlog" || { echo "replay verification failed: $vlog"; exit 1; }
echo "replay backend verified: $vlog"
replay/replay.sh transcripts/p2_core/rep results/rep_episodes.csv > "ops_logs/score_rep_$ts.log" 2>&1
tail -2 "ops_logs/score_rep_$ts.log"
rc=0
.venv/bin/python p2/analysis_rep.py results/rep_episodes.csv --out results/rep_analysis \
  --phase-dir transcripts/p2_core/rep > "ops_logs/analysis_rep_$ts.log" 2>&1 || rc=$?
cat "ops_logs/analysis_rep_$ts.log"
mkdir -p "$data/rep/scored"
cp results/rep_episodes.csv results/rep_episodes_checker.jsonl "$data/rep/scored/"
[[ -f results/rep_episodes_provenance.json ]] && cp results/rep_episodes_provenance.json "$data/rep/scored/"
rm -rf "$data/rep/scored/analysis" && cp -r results/rep_analysis "$data/rep/scored/analysis"
cp "ops_logs/score_rep_$ts.log" "ops_logs/analysis_rep_$ts.log" "$vlog" "$data/rep/scored/"
commit_data "P2 data: E2 cross-recipient replication, scored and analysed"
(( rc == 0 )) || { echo "analysis exited $rc: see ops_logs/analysis_rep_$ts.log"; exit $rc; }
