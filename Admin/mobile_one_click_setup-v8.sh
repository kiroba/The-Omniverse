#!/usr/bin/env bash
# ==============================================================================
# THE OMNIVERSE & THE KICKBACK - PUBLIC TESTER & NODE LAUNCHER (v8.0)
# Target Directory: /storage/emulated/0/Documents/The-Omniverse
# Clean End-User Runtime: NO In-House Admin/Creator Dashboards Included
# ==============================================================================

TARGET_DIR="/storage/emulated/0/Documents/The-Omniverse"
ALT_DIR="$HOME/storage/shared/Documents/The-Omniverse"

echo "=============================================================================="
echo "THE OMNIVERSE PUBLIC TESTER & NODE LAUNCHER (v8.0 CLEAN RUNTIME)"
echo "Target Directory: $TARGET_DIR"
echo "Policy: Public Tester Build (In-House Creator Dashboards Excluded)"
echo "=============================================================================="

# 1. Target Directory Navigation
if command -v termux-setup-storage >/dev/null 2>&1; then
    termux-setup-storage
fi

if [ -d "$TARGET_DIR" ]; then
    cd "$TARGET_DIR" || exit 1
elif [ -d "$ALT_DIR" ]; then
    cd "$ALT_DIR" || exit 1
else
    mkdir -p "$TARGET_DIR" 2>/dev/null || mkdir -p "$ALT_DIR" 2>/dev/null
    cd "$TARGET_DIR" 2>/dev/null || cd "$ALT_DIR" 2>/dev/null || true
fi

chmod -R +rwx . 2>/dev/null || true

# 2. Embedded Repository Organization
mkdir -p core/engines mobile/lib web config docs 2>/dev/null
if [ -f "organize_project.sh" ]; then
    bash organize_project.sh
else
    mv -f zero_dep_*.py mainnet_*.py role_*.py p2p_*.py lpe_*.py *.py core/engines/ 2>/dev/null || true
    mv -f *.dart mobile/lib/ 2>/dev/null || true
    mv -f *.json *.js web/ 2>/dev/null || true
    mv -f *.md docs/ 2>/dev/null || true
fi

# 3. Clean Legacy Seeds
rm -f sample_seeded_*.db mock_telemetry_*.json 2>/dev/null || true
rm -f core/engines/sample_seeded_*.db core/engines/mock_telemetry_*.json 2>/dev/null || true

# 4. Verify Local Python Standard Library Runtime
python3 -c "import sqlite3, hashlib, json, hmac, socket; print('Local P2P Node Runtime & Merkle Engine Ready!')"

echo "=============================================================================="
echo "PUBLIC TESTER NODE ENVIRONMENT IS READY!"
echo "   In-house diagnostics and creator dashboards have been completely removed."
echo "=============================================================================="
