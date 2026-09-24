#!/usr/bin/env bash
# Validate Conventional Commit subject lines (for PRs / pre-push).
set -euo pipefail

ROOT="${RELEASE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT"

RANGE="${1:-}"
if [[ -z "$RANGE" ]]; then
  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    RANGE="origin/main..HEAD"
  else
    RANGE="HEAD"
  fi
fi

PATTERN='^(feat|fix|perf|refactor|docs|chore|test|ci|build|style|revert)(\([^)]+\))?(!)?: .+'

if ! log_output="$(git log "$RANGE" --pretty=format:'%h %s')"; then
  echo "FAIL: cannot read commit range: $RANGE" >&2
  exit 2
fi

fail=0
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "$line" ]] && continue
  subj="$line"
  if [[ "$line" =~ ^[0-9a-f]+[[:space:]]+(.*)$ ]]; then
    subj="${BASH_REMATCH[1]}"
  fi
  if [[ "$subj" == chore\(release\):* ]]; then
    echo "OK: $subj"
    continue
  fi
  if [[ "$subj" == Merge\ pull\ request* || "$subj" == Merge\ branch* ]]; then
    echo "OK: $subj"
    continue
  fi
  if ! [[ "$subj" =~ $PATTERN ]]; then
    echo "FAIL: non-conventional commit subject: $subj"
    fail=1
  else
    echo "OK: $subj"
  fi
done <<< "$log_output"

if [[ "$fail" -ne 0 ]]; then
  echo
  echo "Use Conventional Commits, e.g.:"
  echo "  feat: add release workflow"
  echo "  fix: preserve existing BUGBOT files"
  echo "  feat!: rename plugin paths   # major"
  echo "  fix: ... + footer BREAKING CHANGE: ..."
  exit 1
fi
