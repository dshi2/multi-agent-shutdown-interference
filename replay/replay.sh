#!/usr/bin/env bash
# Score a phase with modified scripts replayed in a disposable container (spec §7).
#   replay/replay.sh <phase_dir> <out.csv> [checker.py]     (default checker: p2/checker_a.py)
# No network, read-only root, all capabilities dropped, no privilege gain, resource limits,
# transcripts mounted read-only. The container is removed when the export finishes.
set -euo pipefail
[ $# -ge 2 ] || { echo "usage: $0 <phase_dir> <out.csv> [checker.py]" >&2; exit 2; }
abs() { (cd "$(dirname "$1")" && echo "$(pwd)/$(basename "$1")"); }
phase=$(cd "$1" && pwd)
mkdir -p "$(dirname "$2")"; out=$(abs "$2")
checker=$(abs "${3:-$(dirname "$0")/../p2/checker_a.py}")
[ -f "$checker" ] || { echo "checker not found: $checker" >&2; exit 2; }
cd "$(dirname "$0")/.."
docker build -q -t p2-replay -f replay/Dockerfile . >/dev/null
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,size=512m \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 256 --memory 2g --cpus 2 \
  --user "$(id -u):$(id -g)" \
  -v "$phase":/in:ro -v "$(dirname "$out")":/out -v "$checker":/checker/checker.py:ro \
  -e P2_CHECKER=/checker/checker.py \
  p2-replay /in --out "/out/$(basename "$out")"
