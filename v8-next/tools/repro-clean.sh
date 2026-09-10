#!/usr/bin/env bash
# Clean-checkout reproduction of the delivered commit (item 1).
# Proves the canonical flow works from history alone, not the dirty tree.
# Usage: bash v8-next/tools/repro-clean.sh [REV]  (default: HEAD)
set -euo pipefail

REV="${1:-HEAD}"
WT=/tmp/v8-clean-repro
rm -rf "$WT"
git worktree add --detach "$WT" "$REV"
cd "$WT"
# Market data is local and gitignored (22MB+ per tape); the worktree links the
# canonical data checkout. Declared dependency, not hidden state.
if [[ ! -e research/tape ]]; then
  mkdir -p research
  ln -s ~/src/v8/research/tape research/tape
fi
bash v8-next/tools/preflight.sh --bars 385 --smoke
uv run --project v8-next --extra research python -m v8_next.app.cli benchmark-portfolio \
  --tape-path research/tape/quad-1h-12m --bars 385 \
  --output-dir /tmp/v8-clean-artifacts --primary equal_weight
echo "CLEAN REPRO PASS at $REV"
