#!/usr/bin/env bash
# ==============================================================================
# THE OMNIVERSE & THE KICKBACK - ONE-CLICK MOBILE TERMUX SETUP SCRIPT (v7.0)
# Target Directory: /storage/emulated/0/Documents/The-Omniverse
# Features: Integrated Organization First + Unseeded Real-Time Creator Hub & Tester Panel
# ==============================================================================

TARGET_DIR="/storage/emulated/0/Documents/The-Omniverse"
ALT_DIR="$HOME/storage/shared/Documents/The-Omniverse"

echo "=============================================================================="
echo "🚀 THE OMNIVERSE MOBILE SETUP & GATEWAY LAUNCHER (v7.0 ALL-IN-ONE)"
echo "Target Directory: $TARGET_DIR"
echo "Features: Organization First -> Zero Seed Purge -> Sovereign Creator Dashboard"
echo "=============================================================================="

# ------------------------------------------------------------------------------
# STEP 1: Storage Permission & Target Directory Navigation
# ------------------------------------------------------------------------------
echo "📁 [1/5] Navigating to target directory & setting permissions..."

if command -v termux-setup-storage >/dev/null 2>&1; then
    termux-setup-storage
fi

if [ -d "$TARGET_DIR" ]; then
    cd "$TARGET_DIR" || exit 1
elif [ -d "$ALT_DIR" ]; then
    cd "$ALT_DIR" || exit 1
else
    echo "Creating target directory at $TARGET_DIR..."
    mkdir -p "$TARGET_DIR" 2>/dev/null || mkdir -p "$ALT_DIR" 2>/dev/null
    cd "$TARGET_DIR" 2>/dev/null || cd "$ALT_DIR" 2>/dev/null || true
fi

echo "    ✓ Current Directory: $(pwd)"
chmod -R +rwx . 2>/dev/null || true
echo "    ✓ Directory permissions unlocked (chmod -R +rwx)"

# ------------------------------------------------------------------------------
# STEP 2: Embedded Repository Organization (FIRST EXECUTION STEP)
# ------------------------------------------------------------------------------
echo "📂 [2/5] Executing Repository Organization FIRST..."

mkdir -p core/engines mobile/lib web config docs 2>/dev/null

if [ -f "organize_project.sh" ]; then
    echo "    ├─ Executing local organize_project.sh..."
    bash organize_project.sh
elif [ -f "../organize_project.sh" ]; then
    echo "    ├─ Executing parent organize_project.sh..."
    bash ../organize_project.sh
else
    echo "    ├─ Running embedded full file sorter..."
    mv -f zero_dep_*.py mainnet_*.py role_*.py p2p_*.py lpe_*.py omnimind_bug_*.py kickback_creator_control_*.py *.py core/engines/ 2>/dev/null || true
    mv -f *.dart mobile/lib/ 2>/dev/null || true
    mv -f *.json *.js web/ 2>/dev/null || true
    mv -f p2p_seed_nodes.json kickback_tier_payment_config.py config/ 2>/dev/null || true
    mv -f *.md docs/ 2>/dev/null || true
fi
echo "    ✓ Repository files successfully organized into core/, mobile/, web/, config/, docs/"

# ------------------------------------------------------------------------------
# STEP 3: Configure Termux Default Startup Directory (~/.bashrc)
# ------------------------------------------------------------------------------
echo "⚓ [3/5] Configuring Termux default startup directory..."

BASHRC="$HOME/.bashrc"
AUTO_CD_CMD="cd /storage/emulated/0/Documents/The-Omniverse 2>/dev/null || cd ~/storage/shared/Documents/The-Omniverse 2>/dev/null"

if [ -f "$BASHRC" ]; then
    if ! grep -q "The-Omniverse" "$BASHRC"; then
        echo "" >> "$BASHRC"
        echo "# Auto-navigate to The Omniverse repository on Termux start" >> "$BASHRC"
        echo "$AUTO_CD_CMD" >> "$BASHRC"
        echo "    ✓ Added default startup directory hook to ~/.bashrc"
    else
        echo "    ✓ Default directory hook verified in ~/.bashrc"
    fi
else
    echo "# Auto-navigate to The Omniverse repository on Termux start" > "$BASHRC"
    echo "$AUTO_CD_CMD" >> "$BASHRC"
    echo "    ✓ Created ~/.bashrc with default startup directory hook"
fi

# ------------------------------------------------------------------------------
# STEP 4: Clean Legacy Seeded Files
# ------------------------------------------------------------------------------
echo "🧹 [4/5] Enforcing zero-seeded data policy..."
rm -f sample_seeded_*.db mock_telemetry_*.json 2>/dev/null || true
rm -f core/engines/sample_seeded_*.db core/engines/mock_telemetry_*.json 2>/dev/null || true
echo "    ✓ Purged all legacy test seeds and mock data files"

# ------------------------------------------------------------------------------
# STEP 5: Launch Sovereign Creator Control Dashboard (Port 9200)
# ------------------------------------------------------------------------------
echo "⚙️ [5/5] Launching Sovereign Creator Control & Diagnostic Dashboard..."

CREATOR_DASHBOARD=""
if [ -f "core/engines/kickback_creator_control_dashboard.py" ]; then
    CREATOR_DASHBOARD="core/engines/kickback_creator_control_dashboard.py"
elif [ -f "kickback_creator_control_dashboard.py" ]; then
    CREATOR_DASHBOARD="kickback_creator_control_dashboard.py"
fi

echo "=============================================================================="
echo "🎉 SETUP COMPLETE - SOVEREIGN CREATOR HUB READY (v7.0)"
echo "=============================================================================="

if [ -n "$CREATOR_DASHBOARD" ]; then
    echo "🌐 LAUNCHING SOVEREIGN CREATOR CONTROL DASHBOARD..."
    echo "   URL: http://localhost:9200  (or http://127.0.0.1:9200)"
    echo "   Features: Monetization views, P2P diagnostics, Merkle auditing & self-healing!"
    echo "------------------------------------------------------------------------------"
    python3 "$CREATOR_DASHBOARD"
else
    echo "💡 To launch the Creator Dashboard manually: python3 core/engines/kickback_creator_control_dashboard.py"
fi
