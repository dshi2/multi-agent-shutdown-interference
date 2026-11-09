#!/bin/zsh
# Copy finished P2 phases into the data worktree (branch `data`), one folder per phase:
#   <phase>/transcripts.tar.gz   every file under transcripts/p2_core/<phase> (transcripts,
#                                attempts, failures, launcher logs, manifest), unmodified
#   <phase>/manifest.json        the phase manifest
#   <phase>/episodes_unscored.csv  export.py --unscored (no checker, nothing executed)
#   ops_logs/                    launch logs and credit readings
#   SHA256SUMS                   checksums of every file above
# Usage: ops/snapshot_data.sh [phase ...]   (default: every phase directory present)
# Rerunning replaces a phase's snapshot with the current state of its directory.
set -eu
cd "${0:A:h}/.."
out="${P2_DATA_DIR:-../data_release}"
[[ -e "$out/.git" ]] || { echo "no data worktree at $out"; exit 1; }
phases=("$@")
(( ${#phases} )) || phases=(${(f)"$(ls -d transcripts/p2_core/*/ | xargs -n1 basename)"})
for p in $phases; do
  src="transcripts/p2_core/$p"
  [[ -d "$src" ]] || { echo "skip $p: no $src"; continue; }
  mkdir -p "$out/$p"
  tar -czf "$out/$p/transcripts.tar.gz" -C transcripts/p2_core "$p"
  [[ -f "$src/manifest.json" ]] && cp "$src/manifest.json" "$out/$p/manifest.json"
  .venv/bin/python p2/export.py "$src" --out "$out/$p/episodes_unscored.csv" --unscored >/dev/null
  echo "snapshot $p: $(du -h "$out/$p/transcripts.tar.gz" | cut -f1)"
done
mkdir -p "$out/ops_logs"
cp ops_logs/* "$out/ops_logs/"
(cd "$out" && find . -type f ! -name SHA256SUMS ! -path './.git*' | sort | xargs shasum -a 256 > SHA256SUMS)
