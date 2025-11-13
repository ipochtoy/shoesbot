#!/bin/bash
# Safe git pull: abort if local branch ahead or worktree dirty
set -e

REMOTE=${1:-origin}
BRANCH=${2:-main}

STATUS=$(git status -sb)
DIRTY=$(git status --porcelain)

if [ -n "$DIRTY" ]; then
  echo "⚠️  Cannot pull: working tree has uncommitted changes." >&2
  exit 1
fi

if echo "$STATUS" | grep -q "ahead"; then
  echo "⚠️  Branch ahead of $REMOTE/$BRANCH. Push or reset before pulling." >&2
  exit 1
fi

echo "📥 git pull $REMOTE $BRANCH"
git pull "$REMOTE" "$BRANCH"
