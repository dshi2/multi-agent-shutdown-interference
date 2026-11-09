#!/bin/zsh
# Launch or resume the E2 cross-recipient replication under the 10:00 UTC hard stop, with the credit guard.
# Rerunning it resumes: finished episodes are kept, interrupted attempts are rerun under
# their own ids, and the manifest refuses any change to cells, sizes or generation code.
set -u
cd "${0:A:h}/.."
export OPENROUTER_API_KEY="$(security find-generic-password -s openrouter-research -w)"
ts=$(date -u +%Y%m%dT%H%MZ)
.venv/bin/python ops/credit_guard.py --min "${P2_MIN_BALANCE:-1.5}" --log "ops_logs/rep_credits_$ts.jsonl" &
guard=$!
.venv/bin/python ops/run_until.py 2026-11-09T10:00Z -- \
  .venv/bin/python p2/run_rep.py --phase rep --arm-n 500 --go --max-active "${P2_MAX_ACTIVE:-90}" \
  2>&1 | tee -i "ops_logs/rep_launch_$ts.log"
kill "$guard" 2>/dev/null
wait "$guard" 2>/dev/null
echo "[rep_run] stopped at $(date -u +%H:%M:%S) UTC; rerun ops/rep_run.sh to resume"
