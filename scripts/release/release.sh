#!/usr/bin/env bash
# Create a SemVer release from Conventional Commits since the last tag.
#
# Usage:
#   bash scripts/release/release.sh              # dry-run (default)
#   bash scripts/release/release.sh --apply      # local apply (no commit)
#   bash scripts/release/release.sh --ci         # CI: commit, tag, push, gh release
#
# Env:
#   FORCE_BUMP=major|minor|patch   override commit analysis
#   SKIP_RELEASE=1                 no-op exit 0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/scripts/release${PYTHONPATH:+:$PYTHONPATH}"

MODE="dry-run"
case "${1:-}" in
  --apply) MODE="apply" ;;
  --ci) MODE="ci" ;;
  --dry-run|"") MODE="dry-run" ;;
  -h|--help)
    sed -n '2,15p' "$0"
    exit 0
    ;;
  *)
    echo "Unknown arg: $1" >&2
    exit 1
    ;;
esac

if [[ "${SKIP_RELEASE:-0}" == "1" ]]; then
  echo "SKIP_RELEASE=1 — nothing to do"
  exit 0
fi

BOT_NAME="${GIT_AUTHOR_NAME:-github-actions[bot]}"
BOT_EMAIL="${GIT_AUTHOR_EMAIL:-41898282+github-actions[bot]@users.noreply.github.com}"

changelog_notes() {
  local version="$1"
  python3 - "$version" <<'PY'
import sys
from pathlib import Path
wanted = sys.argv[1].lstrip("v")
text = Path("CHANGELOG.md").read_text(encoding="utf-8")
parts = text.split("\n## ")
if len(parts) == 1:
    print(text)
    raise SystemExit(0)
for part in parts[1:]:
    heading, _, _rest = part.partition("\n")
    if heading.startswith(f"{wanted} ") or heading == wanted:
        print("## " + part)
        raise SystemExit(0)
print("## " + parts[1])
PY
}

ensure_github_release() {
  local version="$1"
  local tag="v${version}"
  if ! command -v gh >/dev/null; then
    echo "ERROR: gh is required to publish GitHub Release $tag" >&2
    exit 1
  fi
  if gh release view "$tag" >/dev/null 2>&1; then
    echo "GitHub Release $tag already exists"
    return 0
  fi
  gh release create "$tag" \
    --title "simplified-ai-dlc-lifecycle $version" \
    --notes "$(changelog_notes "$version")"
}

publish_tag_and_release() {
  local version="$1"
  git push origin HEAD
  git push origin "v${version}"
  ensure_github_release "$version"
}

# Retry path: previous CI pushed the release commit/tag but GitHub Release failed.
last_subj="$(git log -1 --pretty=%s 2>/dev/null || true)"
if [[ "$last_subj" =~ ^chore\(release\):\ ([0-9]+\.[0-9]+\.[0-9]+) ]]; then
  released="${BASH_REMATCH[1]}"
  echo "HEAD is chore(release): $released"
  if [[ "$MODE" == "ci" ]]; then
    ensure_github_release "$released"
  else
    echo "nothing to bump; GitHub Release retry only runs in --ci"
  fi
  exit 0
fi

json="$(python3 scripts/release/semver_from_commits.py --print json)"
echo "$json"

base="$(printf '%s' "$json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["base_version"])')"
tag="$(printf '%s' "$json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["latest_tag"] or "")')"
baseline="$(printf '%s' "$json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("baseline_tag") or "")')"

if [[ -n "${FORCE_BUMP:-}" ]]; then
  next="$(FORCE_BUMP="$FORCE_BUMP" BASE="$base" python3 -c '
import os
maj, mi, pa = map(int, os.environ["BASE"].split("."))
bump = os.environ["FORCE_BUMP"]
if bump == "major":
    print(f"{maj+1}.0.0")
elif bump == "minor":
    print(f"{maj}.{mi+1}.0")
elif bump == "patch":
    print(f"{maj}.{mi}.{pa+1}")
else:
    raise SystemExit(f"bad FORCE_BUMP={bump}")
')"
  bump="$FORCE_BUMP"
else
  bump="$(printf '%s' "$json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("bump") or "")')"
  next="$(printf '%s' "$json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("next_version") or "")')"
fi

if [[ -z "$tag" && -z "$next" ]]; then
  echo "→ will tag baseline $baseline from plugin.json (no history replay)"
  if [[ "$MODE" == "dry-run" ]]; then
    echo "dry-run only (pass --apply or --ci to write)"
    exit 0
  fi
  python3 - "$base" <<'PY'
import datetime as dt
import sys
from pathlib import Path
sys.path.insert(0, "scripts/release")
from changelog import prepend_changelog
version = sys.argv[1]
today = dt.datetime.now(dt.timezone.utc).date().isoformat()
entry = f"""## {version} — {today}

Initial tagged version matching `.cursor-plugin/plugin.json`. History before this tag is not replayed.
"""
prepend_changelog(entry)
print(f"• CHANGELOG.md baseline {version}")
PY
  git add CHANGELOG.md
  if [[ "$MODE" == "apply" ]]; then
    echo "Applied baseline locally (not committed). Review then:"
    echo "  git commit -m \"chore(release): $base [skip release]\""
    echo "  git tag -a v$base -m \"simplified-ai-dlc-lifecycle $base\""
    exit 0
  fi
  if [[ -z "$(git config user.email || true)" ]]; then
    git config user.name "$BOT_NAME"
    git config user.email "$BOT_EMAIL"
  fi
  git commit -m "chore(release): $base [skip release]"
  git tag -a "v$base" -m "simplified-ai-dlc-lifecycle $base"
  publish_tag_and_release "$base"
  echo "Released baseline $base"
  exit 0
fi

if [[ -z "$next" || -z "$bump" ]]; then
  echo "No releasable commits (need feat/fix/perf or BREAKING) — skip"
  exit 0
fi

echo "→ will release $next ($bump)"

if [[ "$MODE" == "dry-run" ]]; then
  echo "dry-run only (pass --apply or --ci to write)"
  exit 0
fi

python3 scripts/release/apply_version.py "$next"
prev="$(git describe --tags --abbrev=0 2>/dev/null || true)"
python3 scripts/release/changelog.py "$next" "$bump" --previous-tag "$prev" --write

git add .cursor-plugin/plugin.json CHANGELOG.md

if [[ "$MODE" == "apply" ]]; then
  echo "Applied locally (not committed). Review then:"
  echo "  git commit -m \"chore(release): $next [skip release]\""
  echo "  git tag -a v$next -m \"simplified-ai-dlc-lifecycle $next\""
  exit 0
fi

if [[ -z "$(git config user.email || true)" ]]; then
  git config user.name "$BOT_NAME"
  git config user.email "$BOT_EMAIL"
fi

git commit -m "chore(release): $next [skip release]"
git tag -a "v$next" -m "simplified-ai-dlc-lifecycle $next"

publish_tag_and_release "$next"
echo "Released $next"
