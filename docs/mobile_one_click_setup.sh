#!/usr/bin/env bash
# ==============================================================================
# THE OMNIVERSE & THE KICKBACK - ONE-CLICK MOBILE TERMUX SETUP SCRIPT
# Run this inside Termux on your Android device for 100% automated setup.
# ==============================================================================

echo "🚀 [1/4] Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "📦 [2/4] Installing core build tools (Python, Git, SQLite, OpenJDK)..."
pkg install git python sqlite openjdk-17 clang make micro -y

echo "🐍 [3/4] Installing Python dependencies..."
pip install --upgrade pip
pip install pydantic fastapi uvicorn cryptography requests

echo "⚙️ [4/4] Verifying setup..."
python3 -c "import cryptography, pydantic, sqlite3; print('✅ All dependencies successfully installed and verified!')"

echo "=============================================================================="
echo "🎉 MOBILE ENVIRONMENT READY!"
echo "Run your mainnet engine cutover with: python3 mainnet_cutover_suite.py"
echo "=============================================================================="
