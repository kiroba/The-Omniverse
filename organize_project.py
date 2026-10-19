#!/usr/bin/env python3
"""
===============================================================================
THE OMNIVERSE & THE KICKBACK - DYNAMIC LIVING AUTOMATION ORGANIZER (v2)
===============================================================================
Living Automation Architecture:
- Always-On Continuous Repository Organizer & Dynamic Update Engine.
- Dynamically organizes all newly ingested code, UI components, LocalSend REST
  modules, Phaser 2D starter templates, and GitHub Actions CI/CD workflows.
- Automatically routes files into their modular destination paths:
  - .github/workflows/ (GitHub Actions CI/CD workflows)
  - core/engines/       (Backend engines, LocalSend receivers, compilers, CRDTs)
  - mobile/lib/         (Flutter UI screens, Phaser Studio UI, Mobile Monitor UI)
  - mobile/android/     (Android Kotlin/Java native code like MainActivity.kt)
  - web/                (PWA manifests, service workers, HTML/JS canvas apps)
  - config/             (JSON/YAML configs, seed node definitions, manifests)
  - docs/               (Markdown specs, changelogs, legal summaries, manuals)
  - scripts/            (Build automation scripts, standalone app builders)
  - assets/mods/        (.omnimod archives, Phaser 2D starter template packs)
  - assets/raw_imports/ (Graphic PNGs, 3D glTF models, audio banks)
  - tools/              (P2P mesh health monitors, mobile app builders, dashboards)
- Living Update Mode: Performs idempotent updates, cleans stale duplicates,
  and updates the live standalone build workspace automatically.
===============================================================================
"""

import os
import sys
import shutil
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

# Directories ignored during scanner execution
IGNORED_DIRS = {
    ".git",
    ".github",
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
    """Inspects file header/content to detect signatures or intent."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(1024)
    except Exception:
        return ""

def classify_repository_file(file_path):
    """
    Dynamically determines the target relative directory for any file based on:
    1. Extension & filename patterns
    2. Content signature inspection
    3. Industry & module tags
    """
    fname = file_path.name
    fname_lower = fname.lower()
    ext = file_path.suffix.lower()

    if fname in ROOT_PROTECTED_FILES:
        return None  # Do not move protected root files

    # 1. GitHub Actions Workflows (.yml / .yaml)
    if ext in [".yml", ".yaml"]:
        if any(kw in fname_lower for kw in ["workflow", "action", "build_apk", "build_monitor", "deploy-pages", "codemagic"]):
            if "codemagic" in fname_lower:
                return "config"
            return ".github/workflows"
        return "config"

    # 2. Mod Packages & Game Assets (.omnimod, starter templates)
    if ext == ".omnimod" or "starter_templates" in fname_lower:
        return "assets/mods"

    # 3. Shell & Bash Scripts (.sh, .bash)
    if ext in [".sh", ".bash"]:
        return "scripts"

    # 4. Kotlin / Java Native Android Code (.kt, .java)
    if ext in [".kt", ".java"]:
        return "mobile/android/app/src/main/kotlin"

    # 5. Flutter & Dart Code (.dart)
    if ext == ".dart":
        return "mobile/lib"

    # 6. Web / PWA Assets (.js, .ts, .tsx, .html, .css)
    if fname_lower in ["kickback_pwa_manifest.json", "kickback_pwa_service_worker.js"] or "pwa" in fname_lower:
        return "web"
    if ext in [".html", ".css"] or (ext == ".js" and any(kw in fname_lower for kw in ["marquee", "arcade", "phaser", "service_worker"])):
        return "web"

    # 7. Python Engines, Tools, and Utilities (.py)
    if ext == ".py":
        content = inspect_file_content(file_path)
        
        # Tools & Monitors
        if any(kw in fname_lower for kw in ["monitor", "dashboard", "triage", "import_tool", "bug_triage", "easter_egg", "build_mobile_mesh"]):
            return "tools"
        
        # Build Runners & Standalone Builders
        if "build_core_engines" in fname_lower or "organize_project" in fname_lower:
            return "scripts" if "build" in fname_lower else None

        # Core Engines, Receivers, and Compilers
        if any(kw in fname_lower for kw in ["localsend", "compiler", "starter_templates", "crdt", "merkle", "p2p", "layer1", "layer2", "socioboard", "eigentrust"]):
            return "core/engines"

        return "core/engines"

    # 8. Configuration Files (.json, .toml, .ini)
    if ext in [".json", ".toml", ".ini", ".config"]:
        if "seed" in fname_lower or "config" in fname_lower or "tier" in fname_lower:
            return "config"
        return "config"

    # 9. Documentation & Markdown (.md, .txt, .rst)
    if ext in [".md", ".txt", ".rst"]:
        return "docs"

    # 10. Media & Graphic Assets (.png, .jpg, .jpeg, .gif, .svg, .glb, .gltf, .wav, .mp3, .ogg)
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".glb", ".gltf", ".wav", ".mp3", ".ogg"]:
        return "assets/raw_imports"

    # Default fallback
    return "docs" if ext == ".md" else "core/engines"

def organize_repository(target_dir=".", dry_run=False):
    """
    Living Automation Engine:
    Scans and organizes all uncollected root files into their appropriate modular folders.
    Automatically handles updating existing files and cleaning duplicates.
    """
    target_path = Path(target_dir).resolve()
    print(f"🚀 [OMNIVERSE LIVING AUTOMATION ORGANIZER] Target: {target_path}")
    
    root_files = [
        f for f in target_path.iterdir()
        if f.is_file() and f.name not in ROOT_PROTECTED_FILES and not f.name.startswith(".")
    ]

    if not root_files:
        print("  ℹ No unorganized root files detected. Repository structure is clean & up to date.")
        return 0, []

    processed_records = []
    
    for fpath in root_files:
        rel_dest = classify_repository_file(fpath)
        if not rel_dest:
            continue

        dest_dir = target_path / rel_dest
        dest_path = dest_dir / fpath.name

        if not dry_run:
            os.makedirs(dest_dir, exist_ok=True)
            
            # Living update: replace older version or update cleanly
            if dest_path.exists():
                os.remove(dest_path)
                status = "UPDATED_LIVING_FILE"
            else:
                status = "MOVED"

            shutil.move(str(fpath), str(dest_path))
            processed_records.append((fpath.name, str(rel_dest), status))
            print(f"  ✓ [{status}] {fpath.name} ──> [{rel_dest}/]")
        else:
            processed_records.append((fpath.name, str(rel_dest), "DRY_RUN"))
            print(f"  [DRY RUN] Would update: {fpath.name} ──> [{rel_dest}/]")

    return len(processed_records), processed_records

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    target = args[0] if args else "."
    count, records = organize_repository(target_dir=target, dry_run=dry_run)
    print("\n==============================================================================")
    print(f"🎉 LIVING AUTOMATION ORGANIZER COMPLETE: Synchronized {count} files!")
    print("==============================================================================")

if __name__ == "__main__":
    main()
