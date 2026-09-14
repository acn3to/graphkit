#!/bin/bash
# Manual gate: install, verify, uninstall for each agent on a throwaway clone of a real repo.
# Usage: bash tests/e2e.sh <source-repo>
set -u
if [ -z "${1:-}" ]; then
  echo "usage: bash tests/e2e.sh <source-repo>" >&2
  exit 1
fi
SRC="$1"
KIT="$(cd "$(dirname "$0")/.." && pwd)/kit.py"
W=$(mktemp -d)
git clone -q "$SRC" "$W/repo" || { echo "clone failed"; exit 1; }
cd "$W/repo"
BASE=$(git status --porcelain | wc -l)
for a in copilot cursor claude-code; do
  echo "=================== $a"
  uv run --no-project "$KIT" install --agent "$a" --yes || echo "INSTALL FAILED: $a"
  uv run --no-project "$KIT" verify --agent "$a" || echo "VERIFY FAILED: $a"
  uv run --no-project "$KIT" uninstall --agent "$a" --purge
  AFTER=$(git status --porcelain | wc -l)
  [ "$AFTER" -eq "$BASE" ] && echo "CLEAN after uninstall: $a" || { echo "DIRTY after uninstall: $a"; git status --porcelain; }
done
echo "workdir: $W"
