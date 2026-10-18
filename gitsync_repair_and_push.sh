#!/usr/bin/env bash
# ==============================================================================
# OMNIVERSE TERMUX GITSYNC REPAIR & AUTOMATED CLOUD PUSH ENGINE
# ==============================================================================

set -e

echo "=================================================================="
echo "OMNIVERSE GITSYNC REPAIR & CLOUD PUSH TOOL"
echo "=================================================================="

# 1. Clean up stale lock files
if [ -f .git/index.lock ]; then
    echo "[!] Found stale .git/index.lock - removing..."
    rm -f .git/index.lock
    echo "[✓] Lock file removed."
fi

# 2. Check current remote and branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
echo "[INFO] Active Branch: $CURRENT_BRANCH"
echo "[INFO] Remote URL: $(git remote get-url origin 2>/dev/null || echo 'Not configured')"

# 3. Rebase / Sync with origin
echo "------------------------------------------------------------------"
echo "📥 Syncing local changes with origin/$CURRENT_BRANCH..."
echo "------------------------------------------------------------------"
git fetch origin "$CURRENT_BRANCH" || true
git pull origin "$CURRENT_BRANCH" --rebase || {
    echo "[!] Rebase encountered uncommitted changes or conflicts. Stashing..."
    git stash
    git pull origin "$CURRENT_BRANCH" --rebase
    git stash pop || true
}

# 4. Stage and commit
echo "------------------------------------------------------------------"
echo "📦 Staging all local updates and new files..."
echo "------------------------------------------------------------------"
git add .

if git diff-index --quiet HEAD --; then
    echo "[INFO] No new local changes to commit."
else
    echo "[✓] Committing local updates..."
    git commit -m "feat: automated gitsync repair and refined app suite update"
fi

# 5. Push to GitHub to trigger Actions Matrix Build
echo "------------------------------------------------------------------"
echo "🚀 Pushing to origin/$CURRENT_BRANCH to trigger GitHub Actions..."
echo "------------------------------------------------------------------"
git push origin "$CURRENT_BRANCH"

echo "=================================================================="
echo "SUCCESS! Local branch is synced and cloud compilation triggered!"
echo "Check your GitHub Actions tab to monitor the 5 parallel APK builds."
echo "=================================================================="
