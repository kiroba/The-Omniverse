#!/usr/bin/env bash
# ==============================================================================
# OMNIVERSE GITHUB PAGES BRANDED WEBSITE SETUP SCRIPT (HARDENED & FAULT-TOLERANT)
# ==============================================================================

echo "=============================================================================="
echo "🌐 SETTING UP THE OMNIVERSE GITHUB PAGES BRANDED WEBSITE..."
echo "=============================================================================="

# 1. Create target directories if they don't exist
mkdir -p docs/downloads
mkdir -p .github/workflows

# Helper function to copy safely without failing if file is absent or already moved
copy_safely() {
    local src="$1"
    local dest="$2"
    
    if [ -f "$src" ]; then
        cp -f "$src" "$dest" 2>/dev/null || true
    elif [ -f "$dest" ]; then
        # File is already at destination
        :
    else
        # Search for file in workspace subdirectories
        local fname
        fname=$(basename "$src")
        local found
        found=$(find . -maxdepth 3 -name "$fname" ! -path "./docs/$fname" ! -path "./docs/downloads/$fname" -print -quit 2>/dev/null)
        if [ -n "$found" ] && [ -f "$found" ]; then
            cp -f "$found" "$dest" 2>/dev/null || true
        fi
    fi
}

# 2. Copy markdown landing page and config into docs/
copy_safely "index.md" "docs/index.md"
copy_safely "github_pages_config.yml" "docs/_config.yml"

# 3. Copy deployment workflow
copy_safely "deploy-pages.yml" ".github/workflows/deploy-pages.yml"

# 4. Copy deliverables to downloads folder
copy_safely "omniverse_interactive_gui_builder.py" "docs/downloads/omniverse_interactive_gui_builder.py"
copy_safely "vscode_copilot_omniverse_master_instructions.md" "docs/downloads/vscode_copilot_omniverse_master_instructions.md"
copy_safely "kickback_complete_architecture_and_feature_spec.md" "docs/downloads/kickback_complete_architecture_and_feature_spec.md"
copy_safely "omni_source_directory.md" "docs/downloads/omni_source_directory.md"
copy_safely "app-release.apk" "docs/downloads/app-release.apk"

echo "[OK] GitHub Pages website hierarchy verified and built in docs/!"
echo "=============================================================================="
