#!/usr/bin/env bash
# ==============================================================================
# THE OMNIVERSE & THE KICKBACK - DYNAMIC UNIVERSAL REPOSITORY ORGANIZER (v3)
# Living Automation & Codebase Pruning Bash Script
# Purges system/SDK junk, removes non-integral files, and organizes source files.
# ==============================================================================

TARGET_DIR="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if python3 is available to run the intelligent dynamic organizer
if command -v python3 &>/dev/null && [ -f "$SCRIPT_DIR/organize_project.py" ]; then
    echo "🚀 Launching Python Living Automation & Pruning Organizer..."
    python3 "$SCRIPT_DIR/organize_project.py" "$TARGET_DIR"
    exit $?
fi

# Fallback Pure Bash Dynamic Pattern Matcher & Junk Cleaner
echo "🚀 [Fallback] Executing Pure Bash Dynamic Organizer & Junk Pruner on: $TARGET_DIR"

# 1. Purge OS, IDE, and SDK build caches
rm -rf "$TARGET_DIR"/__pycache__ "$TARGET_DIR"/.pytest_cache "$TARGET_DIR"/.dart_tool "$TARGET_DIR"/.gradle "$TARGET_DIR"/.idea "$TARGET_DIR"/.vscode "$TARGET_DIR"/node_modules "$TARGET_DIR"/.cache 2>/dev/null
find "$TARGET_DIR" -maxdepth 2 \( -name "*.tmp" -o -name "*.bak" -o -name "*.log" -o -name "*.pyc" -o -name ".DS_Store" -o -name "Thumbs.db" \) -delete 2>/dev/null

mkdir -p "$TARGET_DIR/.github/workflows"
mkdir -p "$TARGET_DIR/core/engines"
mkdir -p "$TARGET_DIR/mobile/lib"
mkdir -p "$TARGET_DIR/mobile/android/app/src/main/kotlin"
mkdir -p "$TARGET_DIR/web"
mkdir -p "$TARGET_DIR/config"
mkdir -p "$TARGET_DIR/docs"
mkdir -p "$TARGET_DIR/scripts"
mkdir -p "$TARGET_DIR/tools"
mkdir -p "$TARGET_DIR/assets/mods"
mkdir -p "$TARGET_DIR/assets/raw_imports"

# Move Workflows
find "$TARGET_DIR" -maxdepth 1 \( -name "*build*.yml" -o -name "*deploy*.yml" -o -name "*action*.yml" \) -exec mv {} "$TARGET_DIR/.github/workflows/" \; 2>/dev/null

# Move Android Kotlin/Java source files
find "$TARGET_DIR" -maxdepth 1 \( -name "*.kt" -o -name "*.java" \) -exec mv {} "$TARGET_DIR/mobile/android/app/src/main/kotlin/" \; 2>/dev/null

# Move Dart / Flutter UI components
find "$TARGET_DIR" -maxdepth 1 -name "*.dart" -exec mv {} "$TARGET_DIR/mobile/lib/" \; 2>/dev/null

# Move Web / PWA assets
find "$TARGET_DIR" -maxdepth 1 \( -name "*pwa*" -o -name "*.html" -o -name "*.css" \) -exec mv {} "$TARGET_DIR/web/" \; 2>/dev/null

# Move Configuration files & Starter Templates
find "$TARGET_DIR" -maxdepth 1 \( -name "*template*" -o -name "*mod*.json" \) -exec mv {} "$TARGET_DIR/assets/mods/" \; 2>/dev/null
find "$TARGET_DIR" -maxdepth 1 \( -name "*seed*" -o -name "*config*" -o -name "*.toml" \) -exec mv {} "$TARGET_DIR/config/" \; 2>/dev/null

# Move Documentation & Markdown guides
find "$TARGET_DIR" -maxdepth 1 \( -name "*.md" -o -name "*.txt" \) ! -name "README.md" -exec mv {} "$TARGET_DIR/docs/" \; 2>/dev/null

# Move Shell / Bash scripts
find "$TARGET_DIR" -maxdepth 1 -name "*.sh" ! -name "organize_project.sh" -exec mv {} "$TARGET_DIR/scripts/" \; 2>/dev/null

# Move Media & Graphic assets
find "$TARGET_DIR" -maxdepth 1 \( -name "*.png" -o -name "*.jpg" -o -name "*.glb" -o -name "*.gltf" -o -name "*.fmat" -o -name "*.wav" -o -name "*.gif" \) -exec mv {} "$TARGET_DIR/assets/raw_imports/" \; 2>/dev/null

# Move Tools & Dashboards Python scripts
find "$TARGET_DIR" -maxdepth 1 \( -name "*dashboard*" -o -name "*triage*" -o -name "*monitor*" -o -name "*tool*" -o -name "*easter_egg*" \) -name "*.py" -exec mv {} "$TARGET_DIR/tools/" \; 2>/dev/null

# Move remaining Python core engine scripts
find "$TARGET_DIR" -maxdepth 1 -name "*.py" ! -name "organize_project.py" -exec mv {} "$TARGET_DIR/core/engines/" \; 2>/dev/null

echo "=============================================================================="
echo "🎉 REPOSITORY STRUCTURE CLEANED & ORGANIZED DYNAMICALLY!"
echo "=============================================================================="
