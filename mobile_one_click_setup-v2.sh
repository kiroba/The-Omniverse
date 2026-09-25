#!/usr/bin/env bash
# ==============================================================================
# THE OMNIVERSE & THE KICKBACK - ZERO-DEPENDENCY ONE-CLICK MOBILE SETUP
# Run this inside Termux on your Android device for 100% automated setup.
# Requires NO pip packages, NO Rust/clang compilers, and NO external build tools.
# ==============================================================================

set -e

echo "🚀 [1/5] Requesting storage access & updating Termux packages..."
if command -v termux-setup-storage &>/dev/null; then
    termux-setup-storage || true
fi

if command -v pkg &>/dev/null; then
    pkg update -y && pkg upgrade -y
else
    echo "    (Non-Termux host environment; skipping pkg update)"
fi

echo "📦 [2/5] Installing lightweight core tools (Python, Git, SQLite, Micro)..."
if command -v pkg &>/dev/null; then
    pkg install git python sqlite micro -y
fi

echo "🔓 [3/5] Unlocking directory permissions..."
chmod -R +rwx . 2>/dev/null || true

echo "📂 [4/5] Organizing repository structure..."
if [ -f "organize_project.sh" ]; then
    bash organize_project.sh
elif [ -f "/workspace/scratch/organize_project.sh" ]; then
    bash /workspace/scratch/organize_project.sh
else
    mkdir -p core/engines mobile/lib config docs web
    mv zero_dep_*.py core/engines/ 2>/dev/null || true
    mv *.dart mobile/lib/ 2>/dev/null || true
    mv *.json web/ 2>/dev/null || true
    mv *.md docs/ 2>/dev/null || true
fi

echo "⚙️ [5/5] Verifying zero-dependency Python runtime..."
python3 -c "import dataclasses, hashlib, hmac, sqlite3, json, secrets; print('✅ Pure Python Standard Library Runtime Verified!')"

echo "=============================================================================="
echo "🎉 ZERO-DEPENDENCY MOBILE ENVIRONMENT READY!"
echo "Running master verification suite..."
echo "=============================================================================="

if [ -f "core/engines/zero_dep_master_runner.py" ]; then
    python3 core/engines/zero_dep_master_runner.py
elif [ -f "zero_dep_master_runner.py" ]; then
    python3 zero_dep_master_runner.py
elif [ -f "/workspace/scratch/zero_dep_master_runner.py" ]; then
    python3 /workspace/scratch/zero_dep_master_runner.py
else
    echo "💡 Execute master suite with: python3 core/engines/zero_dep_master_runner.py"
fi
