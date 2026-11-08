#!/usr/bin/env bash
# Verification procedure for the replay container. Needs Docker (Docker Desktop or Colima).
#   replay/verify_replay.sh [checker.py]
# 1. the image builds; 2. the container has no network; 3. the checker's own test suite passes
# inside it; 4. the fake-API smoke tests (scripted modified scripts, replayed and scored) pass
# inside it. Run this once before scoring real transcripts, and keep its output.
set -euo pipefail
cd "$(dirname "$0")/.."
checker=${1:-p2/checker_a.py}
run() { docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,size=512m --cap-drop ALL \
          --security-opt no-new-privileges --pids-limit 256 --memory 2g --entrypoint python \
          -e P2_CHECKER="/p2/$checker" p2-replay "$@"; }
docker build -q -t p2-replay -f replay/Dockerfile . >/dev/null && echo "ok   image builds"
docker image inspect p2-replay --format 'image {{.Id}}'
if run -c "import socket; socket.create_connection(('1.1.1.1', 443), 3)" 2>/dev/null; then
  echo "FAIL container reached the network"; exit 1
fi
echo "ok   no network inside the container"
[ "$(run -c 'import os; print(os.environ.get("P2_HOST_REPLAY"))')" = 1 ] || { echo "FAIL replay flag not set"; exit 1; }
echo "ok   replay flag set by the image"
case "$checker" in
  *checker_a.py) run p2/test_checker_a.py | tail -1 ;;
  *) echo "skip checker A's own tests (checking $checker)";;
esac
run p2/smoke_mixed.py | tail -1
run p2/smoke_exp2.py | tail -1
echo "REPLAY BACKEND VERIFIED"
