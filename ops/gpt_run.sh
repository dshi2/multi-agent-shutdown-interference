#!/bin/zsh
# Launch or resume the third-explorer (GPT-5.5) phase (p2/run_gpt.py) under its hard stop,
# with the credit guard. Rerunning resumes; the manifest refuses any change to the plan.
set -u
cd "${0:A:h}/.."
export OPENROUTER_API_KEY="$(security find-generic-password -s openrouter-research -w)"
ts=$(date -u +%Y%m%dT%H%MZ)
.venv/bin/python ops/credit_guard.py --min "${P2_MIN_BALANCE:-2}" --log "ops_logs/gpt_credits_$ts.jsonl" &
guard=$!
.venv/bin/python ops/run_until.py 2026-11-09T13:50Z -- \
  .venv/bin/python p2/run_gpt.py --phase gpt --go --max-active "${P2_MAX_ACTIVE:-125}" \
  2>&1 | tee -i "ops_logs/gpt_launch_$ts.log"
kill "$guard" 2>/dev/null
wait "$guard" 2>/dev/null
echo "[gpt_run] stopped at $(date -u +%H:%M:%S) UTC; rerun ops/gpt_run.sh to resume"
