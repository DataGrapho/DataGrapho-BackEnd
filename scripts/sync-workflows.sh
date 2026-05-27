#!/usr/bin/env bash
set -euo pipefail

SOURCE_BRANCH="infra/backend-cicd"
REMOTE="origin"

echo "Fetching all remote branches..."
git fetch --all --prune

echo "Checking out source branch: $SOURCE_BRANCH"
git checkout "$SOURCE_BRANCH"
git pull "$REMOTE" "$SOURCE_BRANCH"

feature_branches=$(git branch -r \
  | grep "$REMOTE/feature/" \
  | sed "s|$REMOTE/||" \
  | tr -d ' ')

if [ -z "$feature_branches" ]; then
  echo "No feature/* branches found. Exiting."
  exit 0
fi

echo "Found branches:"
echo "$feature_branches"
echo ""

success=()
failed=()

for branch in $feature_branches; do
  echo "── processing: $branch"

  git checkout "$branch"
  git pull "$REMOTE" "$branch" --ff-only

  if git merge "$SOURCE_BRANCH" --no-edit -m "chore: merge $SOURCE_BRANCH into $branch"; then
    git push "$REMOTE" "$branch"
    echo "  ✓ merged and pushed"
    success+=("$branch")
  else
    echo "  ✗ merge conflict on $branch — aborting merge, skipping"
    git merge --abort
    failed+=("$branch")
  fi

  git checkout "$SOURCE_BRANCH"
  echo ""
done

echo "══════════════════════════════"
echo "Done."
echo "  Succeeded (${#success[@]}): ${success[*]:-none}"
echo "  Failed    (${#failed[@]}): ${failed[*]:-none}"
