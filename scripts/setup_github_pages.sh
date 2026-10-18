#!/usr/bin/env bash
# ==============================================================================
<<<<<<< HEAD
# OMNIVERSE GITHUB PAGES BRANDED WEBSITE SETUP SCRIPT
# ==============================================================================
set -e
=======
# OMNIVERSE GITHUB PAGES BRANDED WEBSITE SETUP SCRIPT (HARDENED & FAULT-TOLERANT)
# ==============================================================================
>>>>>>> 595dfcd4895b2e5e39de17959a4f09706f2363ac

echo "=============================================================================="
echo "🌐 SETTING UP THE OMNIVERSE GITHUB PAGES BRANDED WEBSITE..."
echo "=============================================================================="

<<<<<<< HEAD
# 1. Create docs directory structure
mkdir -p docs/downloads
mkdir -p .github/workflows

# 2. Copy markdown landing page and config into docs/
cp -f index.md docs/index.md
cp -f github_pages_config.yml docs/_config.yml

# 3. Copy deployment workflow
cp -f deploy-pages.yml .github/workflows/deploy-pages.yml

# 4. Copy current artifacts to downloads folder for host links
cp -f /workspace/artifacts/omniverse_interactive_gui_builder.py docs/downloads/ 2>/dev/null || true
cp -f /workspace/artifacts/vscode_copilot_omniverse_master_instructions.md docs/downloads/ 2>/dev/null || true
cp -f /workspace/artifacts/kickback_complete_architecture_and_feature_spec.md docs/downloads/ 2>/dev/null || true
cp -f /workspace/artifacts/omni_source_directory.md docs/downloads/ 2>/dev/null || true

echo "[OK] GitHub Pages website hierarchy built in docs/!"
echo "[NEXT STEP] Commit and push to GitHub, then enable Pages in Repository Settings -> Pages -> Source: GitHub Actions or /docs folder."
=======
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
>>>>>>> 595dfcd4895b2e5e39de17959a4f09706f2363ac
echo "=============================================================================="
