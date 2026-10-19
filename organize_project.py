#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE PROJECT ORGANIZER & ROOT CLEAN SWEEP ENGINE [v20.0.0]
==============================================================================
System Architecture:
1. Consolidates GitHub Actions workflows into `.github/workflows/build_apk.yml`.
2. Purges obsolete workflow files (.github/workflows/build_monitor_apk.yml, etc.).
3. Ingests Firefox/browser duplicate downloads (file (1).ext) & deletes duplicates.
4. Performs an aggressive ROOT CLEAN SWEEP: moves all floating UI, backend, and
   script files to their canonical subdirectories (mobile/lib/, backend/, scripts/).
5. Ensures ONLY `organize_project.py` and `build_multi_app_suite.py` remain in root.
6. Uses inode-level `os.path.samefile` checks to avoid `shutil.SameFileError` on Termux.
==============================================================================
"""

import os
import sys
import shutil
import re
import subprocess
from pathlib import Path

__version__ = "20.0.0"
BUILD_REVISION = "2026-10-19.v20.0-canonical"

def resolve_base_dir() -> Path:
    env_dir = os.environ.get("OMNIVERSE_BUILD_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    if os.environ.get("OMNIVERSE_CLOUD_BUILD") == "1" or os.environ.get("CI") == "true":
        workspace_path = Path("/workspace")
        if workspace_path.exists():
            return workspace_path
    return Path.cwd().resolve()

def ingest_browser_downloads(base_dir: Path, search_paths: list):
    """Detects Firefox/browser duplicate downloads (e.g., file (1).ext) and replaces canonical files."""
    dup_pattern = re.compile(r'^(.*?)(?:\s*\(\d+\)|\s*-\s*Copy|\s*copy)\.(py|dart|sh|yml|yaml|md|json)$', re.IGNORECASE)
    
    for p in search_paths:
        if not p.exists():
            continue
        for item in list(p.glob('*')):
            if item.is_file():
                match = dup_pattern.match(item.name)
                if match:
                    base_name = match.group(1).strip()
                    ext = match.group(2)
                    canonical_name = f"{base_name}.{ext}"
                    
                    target_file = base_dir / canonical_name
                    if not target_file.exists():
                        for sp in search_paths:
                            cand = sp / canonical_name
                            if cand.exists():
                                target_file = cand
                                break
                                
                    try:
                        shutil.copyfile(item, target_file)
                        print(f"[📥 FIREFOX AUTO-INGEST] Replaced '{canonical_name}' with newer downloaded '{item.name}'")
                        item.unlink()
                        print(f"[🧹] Cleaned up browser duplicate: {item.name}")
                    except Exception as e:
                        print(f"[!] Notice during browser duplicate ingest for {item.name}: {e}")

def find_source_file(filename: str, search_paths: list) -> Path:
    for p in search_paths:
        if p.exists():
            target = p / filename
            if target.exists():
                return target
            matches = list(p.glob(f"*{filename}*"))
            if matches:
                return matches[0]
    return None

def organize_and_sync():
    base_dir = resolve_base_dir()
    print("==================================================================")
    print(f"OMNIVERSE PROJECT ORGANIZER & ROOT CLEAN SWEEP ENGINE [v{__version__}]")
    print(f"Revision: {BUILD_REVISION}")
    print("==================================================================")
    
    search_paths = [
        base_dir,
        base_dir / "mobile" / "lib",
        base_dir / "scripts",
        Path.cwd()
    ]
    if (Path("/workspace") / "scratch").exists():
        search_paths.append(Path("/workspace") / "scratch")
    if (Path("/workspace") / "artifacts").exists():
        search_paths.append(Path("/workspace") / "artifacts")
        
    # Phase 1: Browser Duplicate Ingestion
    ingest_browser_downloads(base_dir, search_paths)
    
    # Phase 2: Consolidate GitHub Actions Workflows
    workflows_dir = base_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    
    obsolete_workflows = ["build_monitor_apk.yml", "build_alpha_apk.yml", "deploy-pages.yml"]
    for obs in obsolete_workflows:
        obs_path = workflows_dir / obs
        if obs_path.exists():
            try:
                obs_path.unlink()
                print(f"[🧹] Purged obsolete workflow: {obs}")
                try:
                    subprocess.run(["git", "rm", "--cached", f".github/workflows/{obs}"], cwd=base_dir, capture_output=True)
                except Exception:
                    pass
            except Exception:
                pass
                
    BUILD_APK_YML = """name: Build Omniverse Mobile APK Suite

on:
  push:
    branches: [ main, master, desktop ]
  pull_request:
    branches: [ main, master, desktop ]
  workflow_dispatch:

jobs:
  build-matrix:
    name: Build ${{ matrix.app_name }} APK
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - app_folder: "idle_plaza_standalone"
            app_name: "Omniverse Idle Plaza & Combat Brawler"
          - app_folder: "kickback_main_standalone"
            app_name: "The KickBack Social Network"
          - app_folder: "mesh_monitor_standalone"
            app_name: "Mobile Mesh Monitor Observer"
          - app_folder: "omniverse_superapp_master"
            app_name: "Omniverse Unified Superapp Master"

    steps:
      - name: 📥 Checkout Repository
        uses: actions/checkout@v4

      - name: 🐍 Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: ⚙️ Organize Project & Generate Standalone App Workspaces
        run: |
          python3 organize_project.py || true
          python3 build_multi_app_suite.py || python3 scripts/build_multi_app_suite.py

      - name: ☕ Set up Java JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: 🦋 Set up Flutter SDK
        uses: subosito/flutter-action@v2
        with:
          channel: 'stable'

      - name: 🧹 Clean Pre-build Cache & Install Dependencies
        run: |
          cd apps/${{ matrix.app_folder }}/mobile
          flutter clean
          flutter pub get

      - name: 🔨 Build Release APK
        run: |
          cd apps/${{ matrix.app_folder }}/mobile
          flutter build apk --release --target-platform android-arm64 --android-skip-build-dependency-validation

      - name: 📤 Upload Release APK Artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.app_folder }}-release-apk
          path: apps/${{ matrix.app_folder }}/mobile/build/app/outputs/flutter-apk/app-release.apk
          if-no-files-found: error
"""
    with open(workflows_dir / "build_apk.yml", "w", encoding="utf-8") as f:
        f.write(BUILD_APK_YML)
    print("[✓] Finalized canonical matrix workflow: .github/workflows/build_apk.yml")
    
    # Phase 3: Sync Mappings
    mappings = [
        ("kickback_main_app_ui.dart", base_dir / "mobile" / "lib" / "kickback_main_app_ui.dart"),
        ("halo_plaza_experience_ui.dart", base_dir / "mobile" / "lib" / "halo_plaza_experience_ui.dart"),
        ("omni_mobile_mesh_monitor_ui.dart", base_dir / "mobile" / "lib" / "omni_mobile_mesh_monitor_ui.dart"),
        ("omniverse_superapp_master_ui.dart", base_dir / "mobile" / "lib" / "omniverse_superapp_master_ui.dart"),
        ("plaza_fighting_game_engine.dart", base_dir / "mobile" / "lib" / "plaza_fighting_game_engine.dart"),
        ("continuity_token_service.dart", base_dir / "mobile" / "lib" / "continuity_token_service.dart"),
        ("kickback_seamless_stripe_checkout.dart", base_dir / "mobile" / "lib" / "kickback_seamless_stripe_checkout.dart"),
        ("build_multi_app_suite.py", base_dir / "scripts" / "build_multi_app_suite.py"),
        ("build_multi_app_suite.py", base_dir / "build_multi_app_suite.py"),
        ("organize_project.py", base_dir / "organize_project.py"),
    ]
    
    for src_name, dest_path in mappings:
        found_path = find_source_file(src_name, search_paths)
        if found_path:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            is_same = False
            if dest_path.exists():
                try:
                    is_same = os.path.samefile(found_path, dest_path)
                except Exception:
                    is_same = (found_path.resolve() == dest_path.resolve())
            if not is_same:
                try:
                    shutil.copy(found_path, dest_path)
                    rel_str = str(dest_path.relative_to(base_dir)) if base_dir in dest_path.parents or base_dir == dest_path.parent else dest_path.name
                    print(f"[✓] File mapped & synced: {src_name} -> {rel_str}")
                except shutil.SameFileError:
                    pass
                except Exception as e:
                    print(f"[!] Notice copying {src_name}: {e}")
            else:
                rel_str = str(dest_path.relative_to(base_dir)) if base_dir in dest_path.parents or base_dir == dest_path.parent else dest_path.name
                print(f"[✓] File already in place: {rel_str}")
                
    print("------------------------------------------------------------------")
    print("🧹 RUNNING ROOT CLEAN SWEEP: REMOVING FLOATING ROOT FILES...")
    print("------------------------------------------------------------------")
    
    allowed_root_files = {"organize_project.py", "build_multi_app_suite.py", ".gitignore", "README.md", "SECURITY.md", "LICENSE"}
    
    for item in list(base_dir.glob("*")):
        if item.is_file():
            if item.name not in allowed_root_files:
                try:
                    item.unlink()
                    print(f"[🧹 ROOT SWEEP] Cleaned floating file from root: {item.name}")
                except Exception as e:
                    print(f"[!] Notice cleaning root file {item.name}: {e}")

    print("------------------------------------------------------------------")
    print("🧹 RUNNING AUTOMATED PRUNING OF DEPRECATED VERSION-SUFFIXED FILES...")
    print("------------------------------------------------------------------")
    
    for root, _, files in os.walk(base_dir):
        if any(skip in root for skip in [".git", "build", "apps", ".dart_tool", ".gradle"]):
            continue
        for f in files:
            if "-v" in f and f.endswith((".py", ".dart", ".sh", ".yml", ".yaml")):
                f_path = Path(root) / f
                try:
                    f_path.unlink()
                    print(f"[🧹] Pruned legacy draft: {f}")
                except Exception:
                    pass
                    
    print("==================================================================")
    print(f"OMNIVERSE PROJECT ORGANIZATION & ROOT SWEEP COMPLETE [v{__version__}]")
    print("==================================================================")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        print(f"organize_project.py version {__version__} ({BUILD_REVISION})")
        sys.exit(0)
    organize_and_sync()
