#!/usr/bin/env bash
# ==============================================================================
# OMNIVERSE TERMUX ONE-LINE BUILD WRAPPER
# ==============================================================================
# Resolves local paths on Termux Android and executes the self-healing v4 standalone app build.
# ==============================================================================

set -e

echo "=================================================================="
echo "LAUNCHING OMNIVERSE TERMUX BUILD PROCESS"
echo "=================================================================="

# Ensure we are in a writable directory
if [ -d "/storage/emulated/0/Documents/The-Omniverse" ]; then
    cd "/storage/emulated/0/Documents/The-Omniverse"
fi

echo "[INFO] Current Working Directory: $(pwd)"

# Check Python environment
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install python in Termux using: pkg install python"
    exit 1
fi

echo "[INFO] Running build_core_engines_standalone_app-v4.py..."
python3 build_core_engines_standalone_app-v4.py

echo "=================================================================="
echo "TERMUX BUILD SUCCESSFUL!"
echo "Workspace output: $(pwd)/omni_core_engines_standalone"
echo "=================================================================="
