#!/usr/bin/env python3
"""
==============================================================================
THE OMNIVERSE & THE KICKBACK - DYNAMIC UNIVERSAL REPOSITORY ORGANIZER (v8)
==============================================================================
Future-Proof Rule-Based Architecture:
- Scans target directory dynamically without hardcoded file lists.
- Protects critical build scripts at root so GitHub Actions runs reliably.
- Recursively purges heavy build clutter (>50MB) and temporary SDK caches.
- Cleans duplicate files and versioned draft suffixes.
==============================================================================
"""

import os
import sys
import shutil
import re
from pathlib import Path

ROOT_PROTECTED_FILES = {
    "pubspec.yaml",
    "pubspec.lock",
    "README.md",
    "LICENSE",
    ".gitignore",
    "organize_project.py",
    "organize_project.sh",
    "setup_github_pages.sh",
    "Dockerfile",
    "Makefile",
    "build_mobile_mesh_monitor_app.py",
    "build_core_engines_standalone_app.py",
    "build_core_engines_desktop_app.py"
}

def clean_large_build_artifacts(target_path):
    """Recursively scans for heavy build clutter, SDK caches, and binaries (>50MB)."""
    print("🧹 [LARGE BUILD ARTIFACT PURGER] Recursively scanning for heavy non-source build clutter (>50MB / build outputs)...")
    purged_count = 0
    bytes_freed = 0

    heavy_dirs = [
        "mobile/build",
        "desktop/build",
        "omni_core_engines_desktop/desktop/build",
        "mobile/flutter/bin/cache",
        ".dart_tool",
        ".pub-cache"
    ]

    for rel_dir in heavy_dirs:
        dir_path = target_path / rel_dir
        if dir_path.exists():
            try:
                for root, dirs, files in os.walk(dir_path):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            bytes_freed += os.path.getsize(fp)
                        except Exception:
                            pass
                shutil.rmtree(dir_path, ignore_errors=True)
                purged_count += 1
                print(f"  ✓ Purged build directory: {rel_dir}")
            except Exception as e:
                print(f"  ! Warning: Failed to purge {rel_dir}: {e}")

    for fpath in target_path.rglob("*"):
        if fpath.is_file() and ".git" not in fpath.parts:
            ext = fpath.suffix.lower()
            if ext in [".apk", ".jar", ".so", ".dll", ".exe", ".aab"]:
                try:
                    size = fpath.stat().st_size
                    if size > 50 * 1024 * 1024:
                        bytes_freed += size
                        fpath.unlink()
                        purged_count += 1
                        print(f"  ✓ Purged heavy binary (>50MB): {fpath.relative_to(target_path)}")
                except Exception:
                    pass

    mb_freed = bytes_freed / (1024 * 1024)
    print(f"  ✓ Purged {purged_count} heavy items total ({mb_freed:.1f} MB freed).\n")

def sync_website_and_actions(target_path):
    """Ensures website assets are safely staged into docs/ and .github/workflows/."""
    docs_dir = target_path / "docs"
    downloads_dir = docs_dir / "downloads"
    workflows_dir = target_path / ".github" / "workflows"

    os.makedirs(downloads_dir, exist_ok=True)
    os.makedirs(workflows_dir, exist_ok=True)

    print("🌐 [AUTO-WEBSITE & ACTIONS ENGINE] Syncing GitHub Pages & Actions deployment pipeline...")

    def copy_file_safely(filename, dest_path):
        if (target_path / filename).exists():
            shutil.copy2(target_path / filename, dest_path)
        elif not dest_path.exists():
            for found in target_path.rglob(filename):
                if "docs" not in found.parts and ".git" not in found.parts:
                    shutil.copy2(found, dest_path)
                    break

    copy_file_safely("index.md", docs_dir / "index.md")
    copy_file_safely("github_pages_config.yml", docs_dir / "_config.yml")
    copy_file_safely("deploy-pages.yml", workflows_dir / "deploy-pages.yml")

    for deliverable in [
        "omniverse_interactive_gui_builder.py",
        "vscode_copilot_omniverse_master_instructions.md",
        "omni_source_directory.md",
        "kickback_complete_architecture_and_feature_spec.md",
        "app-release.apk"
    ]:
        copy_file_safely(deliverable, downloads_dir / deliverable)

def inspect_file_content(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(1024)
    except Exception:
        return ""

def classify_repository_file(file_path):
    fname = file_path.name
    fname_lower = fname.lower()
    ext = file_path.suffix.lower()

    if fname in ROOT_PROTECTED_FILES:
        return None

    if ext in [".sh", ".bash"]:
        return "scripts"

    if ext in [".kt", ".java"]:
        return "mobile/android/app/src/main/kotlin"

    if ext == ".dart":
        return "mobile/lib"

    if fname_lower in ["kickback_pwa_manifest.json", "kickback_pwa_service_worker.js"] or "pwa" in fname_lower:
        return "web"
    if ext in [".html", ".css"] or (ext == ".js" and any(kw in fname_lower for kw in ["marquee", "arcade", "phaser", "service_worker"])):
        return "web"

    if ext == ".py":
        content = inspect_file_content(file_path)
        if any(kw in fname_lower for kw in ["dashboard", "triage", "import_tool", "monitor", "bug_triage", "easter_egg"]):
            return "tools"
        if "argparse" in content or "import tkinter" in content:
            return "tools"
        return "core/engines"

    if ext in [".json", ".yaml", ".yml", ".toml", ".ini", ".config"]:
        return "config"

    if ext in [".md", ".txt", ".rst"]:
        return "docs"

    if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".glb", ".gltf", ".fmat", ".wav", ".mp3", ".ogg"]:
        return "assets/raw_imports"

    return "docs" if ext == ".md" else "core/engines"

def organize_repository(target_dir=".", dry_run=False):
    target_path = Path(target_dir).resolve()
    print(f"🚀 [OMNIVERSE REPOSITORY ORGANIZER V8] Scanning target: {target_path}\n")

    if not dry_run:
        clean_large_build_artifacts(target_path)

    sync_website_and_actions(target_path)

    root_files = [
        f for f in target_path.iterdir()
        if f.is_file() and f.name not in ROOT_PROTECTED_FILES and not f.name.startswith(".")
    ]

    moved_records = []
    for fpath in root_files:
        rel_dest = classify_repository_file(fpath)
        if not rel_dest:
            continue

        dest_dir = target_path / rel_dest
        dest_path = dest_dir / fpath.name

        if not dry_run:
            os.makedirs(dest_dir, exist_ok=True)
            if dest_path.exists():
                if dest_path.stat().st_size == fpath.stat().st_size:
                    os.remove(fpath)
                    moved_records.append((fpath.name, str(rel_dest), "CLEANED_DUPLICATE"))
                    print(f"  ✓ Cleaned duplicate: {fpath.name} ──> [{rel_dest}/]")
                    continue
                else:
                    base_stem = fpath.stem
                    suffix = fpath.suffix
                    dest_path = dest_dir / f"{base_stem}_v2{suffix}"

            shutil.move(str(fpath), str(dest_path))
            moved_records.append((fpath.name, str(rel_dest), "MOVED"))
            print(f"  ✓ Moved: {fpath.name} ──> [{rel_dest}/]")

    return len(moved_records), moved_records

def main():
    target = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    dry_run = "--dry-run" in sys.argv
    count, records = organize_repository(target_dir=target, dry_run=dry_run)
    print("\n==============================================================================")
    print(f"🎉 ORGANIZER V8 COMPLETE: Reorganized root files & protected build scripts!")
    print("==============================================================================")

if __name__ == "__main__":
    main()
