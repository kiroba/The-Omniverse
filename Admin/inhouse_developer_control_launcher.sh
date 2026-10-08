#!/usr/bin/env bash
# ==============================================================================
# THE OMNIVERSE - IN-HOUSE DEVELOPER CONTROL & DIAGNOSTICS LAUNCHER
# STRICTLY FOR INTERNAL TEAM USE - NOT FOR PUBLIC DISTRIBUTION
# ==============================================================================

TARGET_DIR="/storage/emulated/0/Documents/The-Omniverse"
ALT_DIR="$HOME/storage/shared/Documents/The-Omniverse"

echo "=============================================================================="
echo "IN-HOUSE CREATOR CONTROL & DIAGNOSTICS LAUNCHER (INTERNAL ONLY)"
echo "Target Directory: $TARGET_DIR"
echo "=============================================================================="

if [ -d "$TARGET_DIR" ]; then
    cd "$TARGET_DIR" || exit 1
elif [ -d "$ALT_DIR" ]; then
    cd "$ALT_DIR" || exit 1
fi

DASHBOARD=""
if [ -f "core/engines/kickback_creator_control_dashboard.py" ]; then
    DASHBOARD="core/engines/kickback_creator_control_dashboard.py"
elif [ -f "kickback_creator_control_dashboard.py" ]; then
    DASHBOARD="kickback_creator_control_dashboard.py"
fi

if [ -n "$DASHBOARD" ]; then
    echo "LAUNCHING IN-HOUSE CREATOR CONTROL & DIAGNOSTIC DASHBOARD..."
    echo "   URL: http://localhost:9200"
    echo "   Strictly for core team debugging, bug hash triaging, and WAL maintenance."
    echo "------------------------------------------------------------------------------"
    python3 "$DASHBOARD"
else
    echo "Creator control dashboard script not found!"
fi
