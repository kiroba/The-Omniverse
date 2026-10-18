#!/usr/bin/env bash
# ==============================================================================
# OMNIVERSE TERMUX REPAIR, ORGANIZER & AUTO-PUSH SUITE
# ==============================================================================
# In-File Version : 5.0.0
# Description     : Clears Git index locks, executes canonical project organizer,
#                   generates all 5 standalone apps, and pushes cleanly to origin.
# ==============================================================================

echo "=================================================================="
echo "🚀 OMNIVERSE AUTO-SYNC & REPAIR ENGINE [v5.0.0]"
echo "=================================================================="

# 1. Clear stuck index locks
if [ -f ".git/index.lock" ]; then
    echo "[!] Removing stale .git/index.lock..."
    rm -f .git/index.lock
fi

# 2. Run canonical project organizer
if [ -f "organize_project.py" ]; then
    echo "[⚙️] Running organize_project.py..."
    python3 organize_project.py
fi

# 3. Re-generate multi-app standalone workspaces
if [ -f "build_multi_app_suite.py" ]; then
    echo "[⚙️] Running build_multi_app_suite.py..."
    python3 build_multi_app_suite.py
fi

# 4. Stage and commit changes
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "desktop")
echo "[📦] Staging files for commit on branch: $BRANCH..."
git add .
git commit -m "feat: canonical build suite and app workspaces [v5.0.0]" || echo "[i] No new changes to commit."

# 5. Push to remote
echo "[📤] Pushing to origin $BRANCH:main..."
git push origin "$BRANCH:main"

if [ $? -eq 0 ]; then
    echo "=================================================================="
    echo "[✓] SUCCESS: Changes synced to GitHub main branch!"
    echo "=================================================================="
else
    echo "=================================================================="
    echo "[!] NOTICE: Regular push rejected. Executing fast-forward pull/push..."
    git pull origin main --rebase
    git push origin "$BRANCH:main"
    echo "=================================================================="
fi
