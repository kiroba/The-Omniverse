#!/usr/bin/env bash
# ==============================================================================
# OMNIVERSE TERMUX ENVIRONMENT APPLETS & ALIASES SETUP (v2.0.0)
# ==============================================================================

echo "=================================================================="
echo "🚀 INSTALLING OMNIVERSE TERMUX ENVIRONMENT APPLETS & ALIASES..."
echo "=================================================================="

# Determine Project Root Directory
PROJECT_DIR="$(pwd)"
BASHRC="$HOME/.bashrc"

# Ensure ~/.bashrc exists
touch "$BASHRC"

echo "[i] Project Directory: $PROJECT_DIR"
echo "[i] Target Bash Config: $BASHRC"

# 1. Add auto-cd to project directory in ~/.bashrc if not present
AUTO_CD_LINE="cd \"$PROJECT_DIR\""
if ! grep -Fq "$AUTO_CD_LINE" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# Auto-navigate to Omniverse Project Root on Termux launch" >> "$BASHRC"
    echo "$AUTO_CD_LINE" >> "$BASHRC"
    echo "[✓] Added auto-cd to $PROJECT_DIR in ~/.bashrc"
else
    echo "[✓] Auto-cd for $PROJECT_DIR already exists in ~/.bashrc"
fi

# Function to safely add alias to ~/.bashrc
add_alias() {
    local alias_name="$1"
    local alias_cmd="$2"
    local alias_line="alias ${alias_name}='${alias_cmd}'"

    if ! grep -Fq "alias ${alias_name}=" "$BASHRC" 2>/dev/null; then
        echo "$alias_line" >> "$BASHRC"
        echo "[✓] Added alias: $alias_name -> $alias_cmd"
    else
        echo "[✓] Alias '$alias_name' already exists in ~/.bashrc"
    fi
}

# 2. Add useful project aliases
echo ""
echo "Adding CLI Shortcuts to ~/.bashrc..."
add_alias "organize" "python3 organize_projects-v9.py"
add_alias "gitsync" "bash scripts/gitsync_repair_and_push-v2.sh"
add_alias "studio" "python3 Admin/gui_tools/omniverse_interactive_gui_builder-v4.py"
add_alias "daemon" "python3 Admin/omni_live_daemon_server.py"
add_alias "buildsuite" "python3 build_multi_app_suite-v12.py"

# 3. Create bin and shortcuts directory if needed
mkdir -p "$HOME/bin" "$HOME/.shortcuts"

if [ -f "termux_mesh_applet.py" ]; then
    cp termux_mesh_applet.py "$HOME/bin/mesh-stats" 2>/dev/null || true
    chmod +x "$HOME/bin/mesh-stats" 2>/dev/null || true
    echo "[✓] Installed ~/bin/mesh-stats executable"
fi

echo "=================================================================="
echo "[✓] TERMUX ENVIRONMENT SETUP COMPLETE!"
echo "To apply changes immediately in your current session, run:"
echo "  source ~/.bashrc"
echo "=================================================================="
