#!/usr/bin/env python3
"""
===============================================================================
THE OMNIVERSE & THE KICKBACK - DYNAMIC UNIVERSAL REPOSITORY ORGANIZER (v3)
===============================================================================
Living Automation & Codebase Pruning Architecture:
- Scans target directory dynamically and purges non-project / system / SDK junk.
- Strips OS temporary files, IDE caches, build outputs, and non-integral blobs.
- Sorts integral project source files, assets, configs, and docs into modular folders.
- Keeps repository lightweight, secure, and ready for instant CI/CD compilation.
===============================================================================
"""

import os
import sys
import shutil
import re
from pathlib import Path

# Files to ALWAYS preserve in the project root folder
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

# System / SDK junk patterns to automatically PURGE to keep codebase small
JUNK_EXTENSIONS = {
    ".tmp", ".bak", ".swp", ".swo", ".log", ".pyc", ".pyo", ".class", 
    ".dex", ".o", ".a", ".so", ".dylib", ".orig", ".rej", ".DS_Store"
}

JUNK_FILENAMES = {
    ".ds_store", "thumbs.db", "desktop.ini", "ehthumbs.db", 
    "npm-debug.log", "yarn-debug.log", "yarn-error.log"
}

JUNK_DIR_NAMES = {
    "__pycache__", ".pytest_cache", ".dart_tool", ".gradle", 
    ".idea", ".vscode", "node_modules", "Pods", ".cache", 
    "build_cache", ".flutter-plugins", ".flutter-plugins-dependencies"
}

# Valid project extensions to retain
INTEGRAL_EXTENSIONS = {
    ".dart", ".py", ".kt", ".java", ".js", ".ts", ".tsx", ".html", ".css", 
    ".json", ".yaml", ".yml", ".toml", ".ini", ".sh", ".bash", ".md", ".txt",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".glb", ".gltf", 
    ".fmat", ".wav", ".mp3", ".ogg"
}

def is_junk_file(file_path: Path) -> bool:
    """Checks if a file is an OS, SDK, IDE, or temporary junk file that should be purged."""
    fname_lower = file_path.name.lower()
    ext_lower = file_path.suffix.lower()

    if fname_lower in JUNK_FILENAMES:
        return True
    if ext_lower in JUNK_EXTENSIONS:
        return True
    if fname_lower.startswith("._") or fname_lower.endswith("~"):
        return True
    return False

def purge_junk_files(target_path: Path) -> int:
    """Scans and purges system, SDK, IDE, and temporary junk across the repository."""
    purged_count = 0
    print("🧹 [LIVING AUTOMATION] Scanning for system/SDK junk & non-integral files...")

    # 1. Purge junk directories
    for root, dirs, files in os.walk(target_path, topdown=True):
        dirs[:] = [d for d in dirs if d not in {".git", "mobile", "core", "web", "config", "docs", "scripts", "assets", "tools"}]
        for dname in list(dirs):
            if dname.lower() in JUNK_DIR_NAMES or dname.startswith("."):
                dp = Path(root) / dname
                try:
                    shutil.rmtree(dp)
                    purged_count += 1
                    print(f"  ❌ Purged Junk Directory: {dp.relative_to(target_path)}")
                except Exception as e:
                    pass

    # 2. Purge junk files in root
    for fpath in target_path.iterdir():
        if fpath.is_file():
            if is_junk_file(fpath):
                try:
                    fpath.unlink()
                    purged_count += 1
                    print(f"  ❌ Purged Junk File: {fpath.name}")
                except Exception:
                    pass

    return purged_count

def inspect_file_content(file_path: Path) -> str:
    """Inspects header to determine file intent when extension is ambiguous."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(1024)
    except Exception:
        return ""

def classify_repository_file(file_path: Path):
    """
    Classifies integral project files into target directories or marks them for purging.
    """
    fname = file_path.name
    fname_lower = fname.lower()
    ext = file_path.suffix.lower()

    if fname in ROOT_PROTECTED_FILES:
        return None  # Preserve root protected config files

    # Reject non-integral extensions
    if ext not in INTEGRAL_EXTENSIONS and not ext == "":
        return "PURGE"

    # 1. Workflows & CI/CD
    if ext in [".yml", ".yaml"] and ("build" in fname_lower or "deploy" in fname_lower or "action" in fname_lower):
        return ".github/workflows"

    # 2. Shell & Bash Scripts (.sh, .bash)
    if ext in [".sh", ".bash"]:
        return "scripts"

    # 3. Native Android Code (.kt, .java)
    if ext in [".kt", ".java"]:
        return "mobile/android/app/src/main/kotlin"

    # 4. Flutter / Dart Code (.dart)
    if ext == ".dart":
        return "mobile/lib"

    # 5. Web & PWA Assets (.js, .html, .css)
    if fname_lower in ["kickback_pwa_manifest.json", "kickback_pwa_service_worker.js"] or "pwa" in fname_lower:
        return "web"
    if ext in [".html", ".css"] or (ext == ".js" and any(kw in fname_lower for kw in ["marquee", "arcade", "phaser", "service_worker"])):
        return "web"

    # 6. Python Core Engines, Services, & Developer Tools (.py)
    if ext == ".py":
        content = inspect_file_content(file_path)
        if any(kw in fname_lower for kw in ["dashboard", "triage", "import_tool", "monitor", "bug_triage", "easter_egg"]):
            return "tools"
        if "argparse" in content or "import tkinter" in content:
            return "tools"
        return "core/engines"

    # 7. Configuration Files & Starter Templates (.json, .toml, .ini)
    if ext in [".json", ".toml", ".ini", ".config"]:
        if "template" in fname_lower or "mod" in fname_lower:
            return "assets/mods"
        return "config"

    # 8. Documentation & Specs (.md, .txt)
    if ext in [".md", ".txt"]:
        if fname_lower in ["privacy_policy_and_terms.md", "third-party-notices.md"] or any(kw in fname_lower for kw in ["changelog", "guide", "notes", "plan", "spec", "manifest", "release", "readme"]):
            return "docs"
        return "docs"

    # 9. Media & Graphic Assets (.png, .jpg, .svg, .glb, .ogg, etc.)
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".glb", ".gltf", ".fmat", ".wav", ".mp3", ".ogg"]:
        return "assets/raw_imports"

    return "PURGE"

def organize_repository(target_dir=".", dry_run=False):
    """Scans, cleans junk, and organizes uncollected root files into modular folders."""
    target_path = Path(target_dir).resolve()
    print(f"🚀 [OMNIVERSE LIVING AUTOMATION ORGANIZER v3] Target: {target_path}")

    # Step 1: Purge system/SDK junk
    junk_purged = purge_junk_files(target_path)

    # Step 2: Collect remaining root files
    root_files = [
        f for f in target_path.iterdir()
        if f.is_file() and f.name not in ROOT_PROTECTED_FILES and not f.name.startswith(".")
    ]

    if not root_files:
        print("  ℹ No unorganized root files found. Repository is clean & modular.")
        return junk_purged, 0, []

    moved_records = []
    
    for fpath in root_files:
        rel_dest = classify_repository_file(fpath)
        
        if rel_dest == "PURGE":
            if not dry_run:
                try:
                    fpath.unlink()
                    moved_records.append((fpath.name, "PURGED_NON_INTEGRAL", "REMOVED"))
                    print(f"  ❌ Purged Non-Integral File: {fpath.name}")
                except Exception:
                    pass
            continue

        if not rel_dest:
            continue

        dest_dir = target_path / rel_dest
        dest_path = dest_dir / fpath.name

        if not dry_run:
            os.makedirs(dest_dir, exist_ok=True)
            
            # Idempotent overwrite update
            if dest_path.exists():
                os.remove(dest_path)
                
            shutil.move(str(fpath), str(dest_path))
            moved_records.append((fpath.name, str(rel_dest), "UPDATED_LIVING_FILE"))
            print(f"  ✓ Organised: {fpath.name} ──> [{rel_dest}/]")
        else:
            moved_records.append((fpath.name, str(rel_dest), "DRY_RUN"))
            print(f"  [DRY RUN] Would move: {fpath.name} ──> [{rel_dest}/]")

    return junk_purged, len(moved_records), moved_records

def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    target = args[0] if args else "."
    dry_run = "--dry-run" in sys.argv
    junk_count, moved_count, records = organize_repository(target_dir=target, dry_run=dry_run)
    print("\n==============================================================================")
    print(f"🎉 LIVING AUTOMATION & PRUNING COMPLETE:")
    print(f"   • Purged Junk / Non-Integral Files: {junk_count}")
    print(f"   • Organized Integral Source Files:   {moved_count}")
    print("==============================================================================")

if __name__ == "__main__":
    main()
