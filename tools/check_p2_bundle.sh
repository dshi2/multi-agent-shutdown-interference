#!/usr/bin/env bash
# Clean-extract acceptance check for P2_Peer_Recruitment.zip: extract into an empty directory,
# install the pinned dependencies, then run the dry run and every offline test. No API key is used.
#   tools/check_p2_bundle.sh bundles/P2_Peer_Recruitment.zip bundles/docs/p2/TEST_OUTPUT.txt
set -uo pipefail
zip="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
out="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
work=$(mktemp -d "${TMPDIR:-/tmp}/p2check.XXXXXX")
fail=0
{
  echo "# P2 clean-extract check, $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "bundle sha256 $(shasum -a 256 "$zip" | cut -d' ' -f1)  $(basename "$zip")"
  echo "host $(uname -sr); uv $(uv --version | cut -d' ' -f2)"
  cd "$work" && unzip -q "$zip" && cd p2_harness || exit 1
  echo "extracted to an empty directory; checker A present: $([ -f p2/checker_a.py ] && echo yes || echo no)"
  uv venv -q -p 3.13.3 .venv && uv pip install -q --python .venv/bin/python -r requirements-p2.txt || exit 1
  echo "installed requirements-p2.txt ($(grep -vc '^#' requirements-p2.txt) pins) into $(.venv/bin/python --version)"
  gen=$(.venv/bin/python -c "import sys; sys.path.insert(0, 'p2'); import run_core; print(run_core.generation_sha256())")
  frozen=$(sed -n 's/^generation_sha256: //p' ../FROZEN.txt)
  [ "$gen" = "$frozen" ] && echo "ok   generation hash $gen matches FROZEN.txt" || { echo "FAIL generation hash $gen != $frozen"; fail=1; }
  echo "--- dry run: p2/run_core.py --phase pilot (no --go)"
  env -u OPENROUTER_API_KEY .venv/bin/python p2/run_core.py --phase pilot 2>&1 | tail -4
  for t in test_launch test_ops test_primary_cap test_judge_pass test_analysis test_review; do
    start=$(date +%s)
    env -u OPENROUTER_API_KEY .venv/bin/python "p2/$t.py" > "$work/$t.log" 2>&1; rc=$?
    echo "--- p2/$t.py: exit $rc, $(( $(date +%s) - start ))s, $(grep -c -E '^(ok|PASS) ' "$work/$t.log") checks ok, $(grep -c -E '^FAIL' "$work/$t.log") failed"
    grep -E '^FAIL|PASSED|FAILED|^skip' "$work/$t.log"
    [ $rc -eq 0 ] || fail=1
  done
  echo "--- needs a checker (not in this bundle): p2/smoke_mixed.py, p2/smoke_exp2.py"
  echo "--- needs Docker or Colima (not installed here): replay/verify_replay.sh"
  echo "--- credential scan: files outside env.py matching an OpenRouter key pattern:"
  grep -rlE 'sk-or-v1-[0-9a-f]{8,}' --include='*' . 2>/dev/null | grep -v -E '^\./(env\.py|\.venv/)' || echo "    none"
  [ $fail -eq 0 ] && echo "RESULT: ALL OFFLINE CHECKS PASSED" || echo "RESULT: FAILURES ABOVE"
} 2>&1 | tee "$out"
rm -rf "$work"
