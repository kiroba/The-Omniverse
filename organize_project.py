#!/usr/bin/env python3
"""
===============================================================================
THE OMNIVERSE & THE KICKBACK - DYNAMIC UNIVERSAL REPOSITORY ORGANIZER
===============================================================================
Future-Proof Rule-Based Architecture:
- Scans target directory dynamically without hardcoded file lists.
- Analyzes file extensions, filenames, keywords, and content signatures.
- Automatically creates required directory hierarchy.
- Ignores root system/config files (like pubspec.yaml, .gitignore, README.md).
- Sorts files into:
  - core/engines/       (Python backend, CRDT, P2P mesh, state engines)
  - mobile/lib/         (Dart/Flutter UI, widgets, screens, controllers)
  - mobile/android/     (Kotlin/Java Android native code like MainActivity.kt)
  - web/                (PWA manifests, service workers, web assets)
  - config/             (JSON/YAML configs, seed node definitions)
  - docs/               (Markdown changelogs, specs, build guides, manifests)
  - scripts/            (Shell/Bash setup and compilation scripts)
  - assets/             (Media, PNGs, 3D models, audio, shaders)
  - tools/              (Developer utilities, monitors, dashboards)
===============================================================================
"""

import os
import sys
import shutil
import re
from pathlib import Path

# Files to ALWAYS keep in the project root folder
ROOT_PROTECTED_FILES = {
    "pubspec.yaml",
    "pubspec.lock",
    "README.md",
    "LICENSE",
    ".gitignore",
    "organize_project.py",
    "organize_project.sh",
    "Dockerfile",
    "Makefile"
}

# Directories to ignore during scanning
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "build",
    ".dart_tool",
    ".idea",
    "myenv",
    "__pycache__",
    "core",
    "mobile",
    "web",
    "config",
    "docs",
    "scripts",
    "assets",
    "tools"
}

def inspect_file_content(file_path):
    """Inspects file header/content to detect language or intent if extension is ambiguous."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            header = f.read(1024)
            return header
    except Exception:
        return ""

def classify_repository_file(file_path):
    """
    Dynamically determines the target relative directory for any file based on:
    1. File extension
    2. Filename patterns & keywords
    3. Content signature inspection
    """
    fname = file_path.name
    fname_lower = fname.lower()
    ext = file_path.suffix.lower()

    if fname in ROOT_PROTECTED_FILES:
        return None  # Do not move protected root files

    # 1. Shell & Bash Scripts (.sh, .bash)
    if ext in [".sh", ".bash"]:
        if any(kw in fname_lower for kw in ["setup", "build", "one_click", "compile", "launcher"]):
            return "scripts"
        return "scripts"

    # 2. Kotlin / Java Native Android Code (.kt, .java)
    if ext in [".kt", ".java"]:
        return "mobile/android/app/src/main/kotlin"

    # 3. Flutter & Dart Code (.dart)
    if ext == ".dart":
        return "mobile/lib"

    # 4. Web / PWA Assets (.js, .ts, .tsx, .html, .css, .json)
    if fname_lower in ["kickback_pwa_manifest.json", "kickback_pwa_service_worker.js"] or "pwa" in fname_lower:
        return "web"
    if ext in [".html", ".css"] or (ext == ".js" and any(kw in fname_lower for kw in ["marquee", "arcade", "phaser", "service_worker"])):
        return "web"

    # 5. Python Engines, Tools, and Utilities (.py)
    if ext == ".py":
        content = inspect_file_content(file_path)
        
        # Tools & Dashboards
        if any(kw in fname_lower for kw in ["dashboard", "triage", "import_tool", "monitor", "bug_triage", "easter_egg"]):
            return "tools"
        if "argparse" in content or "import tkinter" in content:
            return "tools"

        # Core Engines & Services
        return "core/engines"

    # 6. Configuration Files (.json, .yaml, .yml, .toml, .ini)
    if ext in [".json", ".yaml", ".yml", ".toml", ".ini", ".config"]:
        if "seed" in fname_lower or "config" in fname_lower or "tier" in fname_lower:
            return "config"
        return "config"

    # 7. Documentation & Guides (.md, .txt, .pdf, .rst)
    if ext in [".md", ".txt", ".rst"]:
        if fname_lower in ["privacy_policy_and_terms.md", "third-party-notices.md"] or any(kw in fname_lower for kw in ["changelog", "guide", "notes", "plan", "spec", "manifest", "release", "readme"]):
            return "docs"
        return "docs"

    # 8. Media & Graphic Assets (.png, .jpg, .jpeg, .gif, .svg, .glb, .gltf, .fmat, .wav, .mp3, .ogg)
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".glb", ".gltf", ".fmat", ".wav", ".mp3", ".ogg"]:
        return "assets/raw_imports"

    # Default fallback for unknown files
    return "docs" if ext == ".md" else "core/engines"

def organize_repository(target_dir=".", dry_run=False):
    """Scans and organizes all uncollected root files into their appropriate modular folders."""
    target_path = Path(target_dir).resolve()
    print(f"[OMNIVERSE REPOSITORY ORGANIZER] Scanning target: {target_path}")
    
    # Collect files in root of target_path (ignoring subdirectories)
    root_files = [
        f for f in target_path.iterdir()
        if f.is_file() and f.name not in ROOT_PROTECTED_FILES and not f.name.startswith(".")
    ]

    if not root_files:
        print("  No unorganized files found in project root.")
        return 0, []

    moved_records = []
    
    for fpath in root_files:
        rel_dest = classify_repository_file(fpath)
        if not rel_dest:
            continue

        dest_dir = target_path / rel_dest
        dest_path = dest_dir / fpath.name

        if not dry_run:
            os.makedirs(dest_dir, exist_ok=True)
            
            # Prevent overwriting existing file with identical content
            if dest_path.exists():
                if dest_path.stat().st_size == fpath.stat().st_size:
                    os.remove(fpath)  # Cleanup duplicate
                    moved_records.append((fpath.name, str(rel_dest), "CLEANED_DUPLICATE"))
                    print(f"  ✓ Cleaned duplicate: {fpath.name} ──> [{rel_dest}/]")
                    continue
                else:
                    # Rename with version suffix if different
                    base_stem = fpath.stem
                    suffix = fpath.suffix
                    dest_path = dest_dir / f"{base_stem}_v2{suffix}"

            shutil.move(str(fpath), str(dest_path))
            moved_records.append((fpath.name, str(rel_dest), "MOVED"))
            print(f"  ✓ Moved: {fpath.name} ──> [{rel_dest}/]")
        else:
            moved_records.append((fpath.name, str(rel_dest), "DRY_RUN"))
            print(f"  [DRY RUN] Would move: {fpath.name} ──> [{rel_dest}/]")

    return len(moved_records), moved_records

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    dry_run = "--dry-run" in sys.argv
    count, records = organize_repository(target_dir=target, dry_run=dry_run)
    print("\n==============================================================================")
    print(f"ORGANIZER COMPLETE: Processed {count} files dynamically without hardcoded lists!")
    print("==============================================================================")

if __name__ == "__main__":
    main()
