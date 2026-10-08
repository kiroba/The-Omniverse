#!/usr/bin/env bash
# ==============================================================================
# THE OMNIVERSE & THE KICKBACK - ONE-CLICK MOBILE TERMUX SETUP SCRIPT (v6.0)
# Target Directory: /storage/emulated/0/Documents/The-Omniverse
# Direct Engine Execution Mode: Zero Verification Suites, Pure Real-Time Runtime
# ==============================================================================

TARGET_DIR="/storage/emulated/0/Documents/The-Omniverse"
ALT_DIR="$HOME/storage/shared/Documents/The-Omniverse"

echo "=============================================================================="
echo "THE OMNIVERSE MOBILE SETUP & GATEWAY LAUNCHER (v6.0 DIRECT ENGINE RUNNER)"
echo "Target Directory: $TARGET_DIR"
echo "Execution Mode: Direct Engine Execution (Verification Suites Omitted)"
echo "=============================================================================="

# ------------------------------------------------------------------------------
# STEP 1: Storage Permission & Target Directory Navigation
# ------------------------------------------------------------------------------
echo "[1/5] Navigating to target directory & setting permissions..."

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
echo "[2/5] Executing Repository Organization FIRST..."

# Create directory structure
mkdir -p core/engines mobile/lib web config docs 2>/dev/null

# Execute organize_project.sh if available, or run embedded organization
if [ -f "organize_project.sh" ]; then
    echo "    ├─ Executing local organize_project.sh..."
    bash organize_project.sh
elif [ -f "../organize_project.sh" ]; then
    echo "    ├─ Executing parent organize_project.sh..."
    bash ../organize_project.sh
else
    echo "    ├─ Running embedded full file sorter..."
    # Core Python Engines
    mv -f zero_dep_*.py mainnet_*.py role_*.py p2p_*.py lpe_*.py *.py core/engines/ 2>/dev/null || true
    # Mobile Flutter UI Components
    mv -f *.dart mobile/lib/ 2>/dev/null || true
    # Web PWA Assets
    mv -f *.json *.js web/ 2>/dev/null || true
    # Config Files
    mv -f p2p_seed_nodes.json kickback_tier_payment_config.py config/ 2>/dev/null || true
    # Documentation & Build Guides
    mv -f *.md docs/ 2>/dev/null || true
fi
echo "    ✓ Repository files successfully organized into core/, mobile/, web/, config/, docs/"

# ------------------------------------------------------------------------------
# STEP 3: Configure Termux Default Startup Directory (~/.bashrc)
# ------------------------------------------------------------------------------
echo "[3/5] Configuring Termux default startup directory..."

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
# STEP 4: Enforce Zero-Seeded Data & Clean Runtime
# ------------------------------------------------------------------------------
echo "[4/5] Enforcing zero-seeded data policy..."
rm -f sample_seeded_*.db mock_telemetry_*.json 2>/dev/null || true
rm -f core/engines/sample_seeded_*.db core/engines/mock_telemetry_*.json 2>/dev/null || true
echo "    ✓ Purged all legacy test seeds and mock data files"

# ------------------------------------------------------------------------------
# STEP 5: Direct Core Engine Execution & Web Admin Dashboard Launch
# ------------------------------------------------------------------------------
echo "[5/5] Launching Core Systems directly (Verification Suite Skipped)..."

DASHBOARD=""
if [ -f "core/engines/external_admin_monitoring_dashboard.py" ]; then
    DASHBOARD="core/engines/external_admin_monitoring_dashboard.py"
elif [ -f "external_admin_monitoring_dashboard.py" ]; then
    DASHBOARD="external_admin_monitoring_dashboard.py"
fi

echo "=============================================================================="
echo "SETUP & DIRECT ENGINE LAUNCH COMPLETE (v6.0)"
echo "=============================================================================="

if [ -n "$DASHBOARD" ]; then
    echo "LAUNCHING CORE TELEMETRY ENGINE & ADMIN DASHBOARD..."
    echo "   URL: http://localhost:9100  (or http://127.0.0.1:9100)"
    echo "   Open Google Chrome or phone browser for live engine monitoring!"
    echo "------------------------------------------------------------------------------"
    python3 "$DASHBOARD"
else
    echo "Dashboard engine script not found. Run: python3 core/engines/external_admin_monitoring_dashboard.py"
fi
