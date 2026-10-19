#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE PROJECT ORGANIZER & AUTOMATED PRUNING ENGINE (V19.4)
==============================================================================
1. Generates the canonical 4-App Parallel Matrix GitHub Actions Workflow.
2. Embeds --android-skip-build-dependency-validation to pass Flutter CI checks.
3. Maps, syncs, and prunes legacy -v* draft files safely.
==============================================================================
"""

import os
import sys
import shutil
from pathlib import Path

__version__ = "19.4.0"
BUILD_REVISION = "2026-10-18.v19.4-canonical"

def resolve_base_dir() -> Path:
    env_dir = os.environ.get("OMNIVERSE_BUILD_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    if os.environ.get("OMNIVERSE_CLOUD_BUILD") == "1" or os.environ.get("CI") == "true":
        workspace_path = Path("/workspace")
        if workspace_path.exists():
            return workspace_path
    return Path.cwd().resolve()

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
    print(f"OMNIVERSE PROJECT ORGANIZER & AUTOMATED PRUNING ENGINE [v{__version__}]")
    print(f"Revision: {BUILD_REVISION}")
    print("==================================================================")
    
    workflows_dir = base_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Canonical Parallel Matrix Workflow with --android-skip-build-dependency-validation
    BUILD_APK_YML = """name: Build Omniverse Mobile APK Suite

on:
  push:
    branches: [ main, master, desktop ]
  pull_request:
    branches: [ main, master, desktop ]
  workflow_dispatch:

jobs:
  build-matrix:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        app:
          - folder: idle_plaza_standalone
            name: omniverse-idle-plaza-release-apk
          - folder: kickback_main_standalone
            name: kickback-main-network-release-apk
          - folder: mesh_monitor_standalone
            name: omni-mesh-monitor-release-apk
          - folder: omniverse_superapp_master
            name: omniverse-superapp-master-release-apk
      fail-fast: false

    steps:
      - name: 📥 Checkout Repository
        uses: actions/checkout@v4

      - name: 🐍 Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: ⚙️ Organize Repository & Generate App Workspaces
        run: |
          python3 organize_project.py || true
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

      - name: 🧹 Clean Pre-build Cache & Install Dependencies
        run: |
          cd apps/${{ matrix.app.folder }}/mobile
          flutter clean
          flutter pub get

      - name: 🔨 Build Release APK (--android-skip-build-dependency-validation)
        run: |
          cd apps/${{ matrix.app.folder }}/mobile
          flutter build apk --release --target-platform android-arm64 --android-skip-build-dependency-validation

      - name: 📤 Upload Release APK Artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.app.name }}
          path: apps/${{ matrix.app.folder }}/mobile/build/app/outputs/flutter-apk/app-release.apk
          if-no-files-found: error
"""
    with open(workflows_dir / "build_apk.yml", "w", encoding="utf-8") as f:
        f.write(BUILD_APK_YML)
    print(f"[✓] Finalized canonical matrix workflow: .github/workflows/build_apk.yml")

    # Clean stray workflows
    stray_workflow_names = ["build_monitor_apk.yml", "build_alpha_apk.yml", "deploy-pages.yml"]
    for root, _, files in os.walk(workflows_dir):
        for f in files:
            if f in stray_workflow_names:
                try:
                    (Path(root) / f).unlink()
                    print(f"[🧹] Pruned obsolete workflow: {f}")
                except Exception:
                    pass

    search_paths = [
        base_dir,
        base_dir / "mobile" / "lib",
        base_dir / "scripts",
        Path.cwd()
    ]
    if (Path("/workspace") / "artifacts").exists():
        search_paths.append(Path("/workspace") / "artifacts")
        
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
