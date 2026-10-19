#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE PROJECT ORGANIZER & AUTOMATED PRUNING ENGINE [v19.3.0]
==============================================================================
Module Version : 19.3.0 (Canonical Matrix Workflow & Workflow Pruner)
System Domain  : Repository Layout, Workflow Consolidation & Dependency Syncer
==============================================================================
"""

import os
import sys
import shutil
from pathlib import Path

__version__ = "19.3.0"
BUILD_REVISION = "2026-10-18.v19.3-canonical"

def resolve_base_dir() -> Path:
    env_dir = os.environ.get("OMNIVERSE_BUILD_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    if os.environ.get("OMNIVERSE_CLOUD_BUILD") == "1" or os.environ.get("CI") == "true":
        workspace_path = Path("/workspace")
        if workspace_path.exists():
            return workspace_path
    return Path.cwd().resolve()

# Canonical 4-App Mobile Matrix Workflow
BUILD_APK_YML = """name: Build Omniverse Mobile APK Suite

on:
  push:
    branches: [ main, master, desktop ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build-matrix:
    name: Build ${{ matrix.app.name }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        app:
          - folder: idle_plaza_standalone
            name: Idle Plaza & Brawler APK
          - folder: kickback_main_standalone
            name: The KickBack Main App APK
          - folder: mesh_monitor_standalone
            name: Mobile Mesh Monitor APK
          - folder: omniverse_superapp_master
            name: Omniverse Unified Superapp APK

    steps:
      - name: 📥 Checkout Repository
        uses: actions/checkout@v4

      - name: 🐍 Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: ⚙️ Organize Project & Generate Workspaces
        run: |
          python3 organize_project.py
          python3 build_multi_app_suite.py

      - name: ☕ Set up Java JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: 🦋 Set up Flutter SDK
        uses: subosito/flutter-action@v2
        with:
          channel: 'stable'

      - name: 🧹 Clean & Get Dependencies
        run: |
          cd apps/${{ matrix.app.folder }}/mobile
          flutter clean
          flutter pub get

      - name: 🔨 Build Release APK
        run: |
          cd apps/${{ matrix.app.folder }}/mobile
          flutter build apk --release --target-platform android-arm64

      - name: 📤 Upload Release APK
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.app.folder }}-release-apk
          path: apps/${{ matrix.app.folder }}/mobile/build/app/outputs/flutter-apk/app-release.apk
          if-no-files-found: error
"""

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
    print(f"OMNIVERSE PROJECT ORGANIZER & WORKFLOW PRUNER [v{__version__}]")
    print(f"Revision: {BUILD_REVISION}")
    print("==================================================================")
    
    # 1. Directory Tree
    workflows_dir = base_dir / ".github" / "workflows"
    mobile_lib = base_dir / "mobile" / "lib"
    scripts_dir = base_dir / "scripts"
    docs_dir = base_dir / "docs"

    for d in [workflows_dir, mobile_lib, scripts_dir, docs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 2. Enforce Canonical Workflow & Remove Legacy Workflows
    canonical_workflow_path = workflows_dir / "build_apk.yml"
    with open(canonical_workflow_path, "w", encoding="utf-8") as f:
        f.write(BUILD_APK_YML)
    print(f"[✓] Finalized canonical matrix workflow: .github/workflows/build_apk.yml")

    # Purge obsolete workflows that trigger build errors
    obsolete_workflows = ["build_monitor_apk.yml", "build_alpha_apk.yml", "deploy-pages.yml"]
    for wf in obsolete_workflows:
        target_wf = workflows_dir / wf
        if target_wf.exists():
            try:
                target_wf.unlink()
                print(f"[🧹] Pruned obsolete workflow: .github/workflows/{wf}")
            except Exception as e:
                print(f"[!] Notice pruning workflow {wf}: {e}")

    # Search paths for source files
    search_paths = [
        base_dir,
        base_dir / "mobile" / "lib",
        base_dir / "scripts",
        Path.cwd()
    ]
    if (Path("/workspace") / "artifacts").exists():
        search_paths.append(Path("/workspace") / "artifacts")
    if (Path("/workspace") / "scratch").exists():
        search_paths.append(Path("/workspace") / "scratch")
        
    mappings = [
        ("kickback_main_app_ui.dart", mobile_lib / "kickback_main_app_ui.dart"),
        ("halo_plaza_experience_ui.dart", mobile_lib / "halo_plaza_experience_ui.dart"),
        ("omni_mobile_mesh_monitor_ui.dart", mobile_lib / "omni_mobile_mesh_monitor_ui.dart"),
        ("omniverse_superapp_master_ui.dart", mobile_lib / "omniverse_superapp_master_ui.dart"),
        ("plaza_fighting_game_engine.dart", mobile_lib / "plaza_fighting_game_engine.dart"),
        ("continuity_token_service.dart", mobile_lib / "continuity_token_service.dart"),
        ("kickback_seamless_stripe_checkout.dart", mobile_lib / "kickback_seamless_stripe_checkout.dart"),
        ("build_multi_app_suite.py", scripts_dir / "build_multi_app_suite.py"),
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
    print(f"OMNIVERSE PROJECT ORGANIZATION COMPLETE [v{__version__}]")
    print("==================================================================")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        print(f"organize_project.py version {__version__} ({BUILD_REVISION})")
        sys.exit(0)
    organize_and_sync()
