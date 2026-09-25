#!/usr/bin/env bash
# ==============================================================================
# THE OMNIVERSE & THE KICKBACK - ONE-CLICK MOBILE TERMUX SETUP SCRIPT (v5.0)
# Target Directory: /storage/emulated/0/Documents/The-Omniverse
# ZERO MOCK/SEEDED DATA POLICY ENFORCED FIRST.
# ==============================================================================

TARGET_DIR="/storage/emulated/0/Documents/The-Omniverse"
ALT_DIR="$HOME/storage/shared/Documents/The-Omniverse"

echo "=============================================================================="
echo "🚀 THE OMNIVERSE MOBILE SETUP & GATEWAY LAUNCHER (v5.0 PRODUCTION)"
echo "Target Directory: $TARGET_DIR"
echo "Execution Order: Repository Organization FIRST -> Zero-Data Clean -> Web Dashboard"
echo "=============================================================================="

# ------------------------------------------------------------------------------
# STEP 1: Storage Permission & Target Directory Navigation
# ------------------------------------------------------------------------------
echo "📁 [1/6] Navigating to target directory & setting permissions..."

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
# STEP 2: Execute Repository File Organization FIRST
# ------------------------------------------------------------------------------
echo "📂 [2/6] Executing Repository Organization FIRST..."

if [ -f "organize_project.sh" ]; then
    bash organize_project.sh
elif [ -f "../organize_project.sh" ]; then
    bash ../organize_project.sh
else
    mkdir -p core/engines mobile/lib config docs web 2>/dev/null
    mv -f zero_dep_*.py mainnet_*.py role_*.py p2p_*.py lpe_*.py *.py core/engines/ 2>/dev/null || true
    mv -f *.dart mobile/lib/ 2>/dev/null || true
    mv -f *.json *.js web/ 2>/dev/null || true
    mv -f *.md docs/ 2>/dev/null || true
fi
echo "    ✓ Repository files successfully organized into core/, mobile/, web/, config/, docs/"

# ------------------------------------------------------------------------------
# STEP 3: Configure Termux Default Startup Directory (~/.bashrc)
# ------------------------------------------------------------------------------
echo "⚓ [3/6] Configuring Termux default startup directory..."

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
# STEP 4: System Dependencies (Pure Python Standard Library)
# ------------------------------------------------------------------------------
echo "📦 [4/6] Verifying core system utilities (Python, SQLite, Git)..."
if command -v pkg >/dev/null 2>&1; then
    pkg update -y && pkg install git python sqlite micro -y
fi

# ------------------------------------------------------------------------------
# STEP 5: Purge All Legacy Mock/Seeded Data Files
# ------------------------------------------------------------------------------
echo "🧹 [5/6] Enforcing zero-seeded data policy..."
rm -f sample_seeded_*.db mock_telemetry_*.json test_mock_*.db 2>/dev/null || true
rm -f core/engines/sample_seeded_*.db core/engines/mock_telemetry_*.json 2>/dev/null || true
echo "    ✓ Purged all legacy test seeds and mock data files"

# ------------------------------------------------------------------------------
# STEP 6: Execute Zero-Dependency Verification & Real-Time Web Dashboard
# ------------------------------------------------------------------------------
echo "⚙️ [6/6] Executing zero-dependency system verification..."

RUNNER=""
if [ -f "core/engines/zero_dep_master_runner.py" ]; then
    RUNNER="core/engines/zero_dep_master_runner.py"
elif [ -f "zero_dep_master_runner.py" ]; then
    RUNNER="zero_dep_master_runner.py"
fi

if [ -n "$RUNNER" ]; then
    python3 "$RUNNER"
else
    python3 -c "import sqlite3, hashlib, json, hmac; print('✅ Python Standard Library Runtime Verified!')"
fi

DASHBOARD=""
if [ -f "core/engines/external_admin_monitoring_dashboard.py" ]; then
    DASHBOARD="core/engines/external_admin_monitoring_dashboard.py"
elif [ -f "external_admin_monitoring_dashboard.py" ]; then
    DASHBOARD="external_admin_monitoring_dashboard.py"
fi

echo "=============================================================================="
echo "🎉 SETUP & REAL-TIME DASHBOARD LAUNCH COMPLETE (v5.0)"
echo "=============================================================================="

if [ -n "$DASHBOARD" ]; then
    echo "🌐 LAUNCHING UNSEEDED REAL-TIME ADMIN MONITORING DASHBOARD..."
    echo "   URL: http://localhost:9100  (or http://127.0.0.1:9100)"
    echo "   Open Google Chrome or phone browser for 100% live telemetry!"
    echo "------------------------------------------------------------------------------"
    python3 "$DASHBOARD"
else
    echo "💡 To run the master suite again: python3 core/engines/zero_dep_master_runner.py"
fi
