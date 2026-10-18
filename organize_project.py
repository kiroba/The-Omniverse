#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE PROJECT ORGANIZER & AUTOMATED PRUNING ENGINE
==============================================================================
Module Version : 19.0.0 (Canonical In-File Versioning)
System Domain  : Repository Layout Canonicalization, Workflow Sync & Pruning
==============================================================================
"""

import os
import sys
import shutil
import re
import argparse
from pathlib import Path

__version__ = "19.0.0"
BUILD_REVISION = "2026-10-18.v19-canonical"

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
    "build_apk.yml",
    "build_monitor_apk.yml",
    "build_multi_app_suite.py",
    "build_core_engines_standalone_app.py",
    "build_mobile_mesh_monitor_app.py",
    "plaza_fighting_game_engine.dart",
    "continuity_token_service.dart",
    "kickback_seamless_stripe_checkout.dart",
    "omni_crypto_payment_gateway.py",
    "build_termux.sh",
    "gitsync_repair_and_push.sh",
    "run_desktop.py",
    "run_desktop.bat",
    "run_desktop.sh"
}

WORKFLOW_PARALLEL_MATRIX_BUILD = """name: Build All Omniverse Standalone APKs

on:
  push:
    branches: [ main, master, desktop ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build-standalone-apks:
    name: Build ${{ matrix.app.name }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        app:
          - folder: "idle_plaza_standalone"
            name: "Idle Plaza & Combat Brawler"
            artifact: "idle-plaza-brawler-release-apk"
          - folder: "phaser_studio_standalone"
            name: "OmniPhaser 2D Studio"
            artifact: "phaser-2d-studio-release-apk"
          - folder: "kickback_main_standalone"
            name: "The KickBack Social Network"
            artifact: "kickback-social-main-release-apk"
          - folder: "mesh_monitor_standalone"
            name: "Mobile Mesh Monitor"
            artifact: "mobile-mesh-monitor-release-apk"
          - folder: "omniverse_superapp_master"
            name: "Omniverse Master Superapp"
            artifact: "omniverse-master-superapp-release-apk"

    steps:
      - name: 📥 Checkout Repository
        uses: actions/checkout@v4

      - name: 🐍 Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: ⚙️ Generate Multi-App Standalone Suite
        run: |
          if [ -f "build_multi_app_suite.py" ]; then
            python3 build_multi_app_suite.py
          elif [ -f "scripts/build_multi_app_suite.py" ]; then
            python3 scripts/build_multi_app_suite.py
          else
            echo "[!] Error: build_multi_app_suite.py not found in root or scripts/"
            exit 1
          fi

      - name: ☕ Set up Java JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: 🦋 Set up Flutter SDK
        uses: subosito/flutter-action@v2
        with:
          channel: 'stable'

      - name: 🧹 Clean Flutter Build Cache
        run: |
          cd apps/${{ matrix.app.folder }}/mobile
          flutter clean

      - name: 📦 Install Flutter Dependencies
        run: |
          cd apps/${{ matrix.app.folder }}/mobile
          flutter pub get

      - name: 🔨 Build Release APK
        run: |
          cd apps/${{ matrix.app.folder }}/mobile
          flutter build apk --release --target-platform android-arm64 --android-skip-build-dependency-validation

      - name: 📤 Upload APK Artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.app.artifact }}
          path: apps/${{ matrix.app.folder }}/mobile/build/app/outputs/flutter-apk/app-release.apk
          if-no-files-found: error
"""

DEPRECATED_FILE_PATTERNS = [
    r"build_core_engines_standalone_app-v[0-9]+\.py$",
    r"build_mobile_mesh_monitor_app[-_]v[0-9]+\.py$",
    r"build_multi_app_suite-v[0-9]+\.py$",
    r"organize_project-v[0-9]+\.py$",
    r"run_desktop-v[0-9]+\.(py|bat|sh)$",
    r"mobile_one_click_setup-v[0-9]+\.sh$",
    r"kickback_main_app_ui-v[0-9]+\.dart$",
    r"halo_plaza_experience_ui-v[0-9]+\.dart$",
    r"dev_blog_changelog-v[0-9]+\.md$",
    r"omniverse_commercial_business_plan-v[0-9]+\.md$"
]

CANONICAL_GITIGNORE_CONTENT = """# ==============================================================================
# THE OMNIVERSE & THE KICKBACK - CANONICAL MASTER .gitignore
# ==============================================================================

# Flutter, Dart & Native Build Outputs
.dart_tool/
.packages
.pub-cache/
.pub/
build/
**/build/
mobile/build/
ios/Pods/
android/.gradle/
.gradle/
*.apk
*.aab

# Binary Executables & Heavy Cache
*.jar
*.so
*.dll
*.dylib
*.exe
*.bin
*.iso

# Python & Daemon Caches
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.env
venv/
env/

# IDE & OS Settings
.DS_Store
Thumbs.db
.idea/

# Intermediate Scratch & Out Directories
scratch/
out/
"""

def prune_obsolete_versioned_files(base_dir: Path):
    print("------------------------------------------------------------------")
    print("🧹 RUNNING AUTOMATED PRUNING OF DEPRECATED VERSION-SUFFIXED FILES...")
    print("------------------------------------------------------------------")
    
    pruned_count = 0
    search_dirs = [base_dir, base_dir / "mobile", base_dir / "backend", base_dir / "scripts", base_dir / "docs", base_dir / "tools"]
    
    for sdir in search_dirs:
        if not sdir.exists():
            continue
            
        for item in sdir.iterdir():
            if item.is_file() and item.name not in ROOT_PROTECTED_FILES:
                for pattern in DEPRECATED_FILE_PATTERNS:
                    if re.search(pattern, item.name):
                        try:
                            item.unlink()
                            pruned_count += 1
                            print(f"[✓] Pruned obsolete versioned file: {item.name}")
                            break
                        except Exception as e:
                            print(f"[!] Warning: Could not prune {item.name}: {e}")
                            
    return pruned_count

def update_gitignore_file(base_dir: Path):
    gitignore_path = base_dir / ".gitignore"
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(CANONICAL_GITIGNORE_CONTENT)
    print("[✓] Updated canonical .gitignore (whitelists all canonical scripts)")

def organize_and_cleanup_project(base_dir: Path):
    print("==================================================================")
    print(f"OMNIVERSE PROJECT ORGANIZER & AUTOMATED PRUNING ENGINE [v{__version__}]")
    print(f"Revision: {BUILD_REVISION}")
    print("==================================================================")
    
    # 1. Enforce canonical workflows at .github/workflows/
    workflows_dir = base_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    
    with open(workflows_dir / "build_apk.yml", "w", encoding="utf-8") as f:
        f.write(WORKFLOW_PARALLEL_MATRIX_BUILD)
    print("[✓] Finalized canonical matrix workflow: .github/workflows/build_apk.yml")
    
    # 2. Update .gitignore
    update_gitignore_file(base_dir)

    # 3. Setup standard directory structure
    mobile_lib = base_dir / "mobile" / "lib"
    mobile_assets_img = base_dir / "mobile" / "assets" / "images"
    mobile_assets_mods = base_dir / "mobile" / "assets" / "mods"
    backend_dir = base_dir / "backend"
    scripts_dir = base_dir / "scripts"
    docs_dir = base_dir / "docs"
    
    for d in [mobile_lib, mobile_assets_img, mobile_assets_mods, backend_dir, scripts_dir, docs_dir]:
        d.mkdir(parents=True, exist_ok=True)
        
    # 4. File mappings strictly targeting CANONICAL filenames
    file_mappings = [
        ("kickback_main_app_ui.dart", mobile_lib / "kickback_main_app_ui.dart"),
        ("halo_plaza_experience_ui.dart", mobile_lib / "halo_plaza_experience_ui.dart"),
        ("omni_phaser_studio_ui.dart", mobile_lib / "omni_phaser_studio_ui.dart"),
        ("omni_mobile_mesh_monitor_ui.dart", mobile_lib / "omni_mobile_mesh_monitor_ui.dart"),
        ("plaza_fighting_game_engine.dart", mobile_lib / "plaza_fighting_game_engine.dart"),
        ("continuity_token_service.dart", mobile_lib / "continuity_token_service.dart"),
        ("kickback_seamless_stripe_checkout.dart", mobile_lib / "kickback_seamless_stripe_checkout.dart"),
        ("alpha_tester_digital_flyer.png", mobile_assets_img / "alpha_tester_digital_flyer.png"),
        ("omni_mod_starter_templates.json", mobile_assets_mods / "omni_mod_starter_templates.json"),
        ("localsend_chunk_receiver.py", backend_dir / "localsend_chunk_receiver.py"),
        ("omni_mod_compiler.py", backend_dir / "omni_mod_compiler.py"),
        ("omni_phase1_security_suite.py", backend_dir / "omni_phase1_security_suite.py"),
        ("socioboard_b2b_gateway_adapter.py", backend_dir / "socioboard_b2b_gateway_adapter.py"),
        ("p2p_mesh_health_monitor.py", backend_dir / "p2p_mesh_health_monitor.py"),
        ("omni_flet_desktop_control_panel.py", backend_dir / "omni_flet_desktop_control_panel.py"),
        ("omni_crypto_payment_gateway.py", backend_dir / "omni_crypto_payment_gateway.py"),
        ("build_termux.sh", scripts_dir / "build_termux.sh"),
        ("build_multi_app_suite.py", scripts_dir / "build_multi_app_suite.py"),
        ("build_core_engines_standalone_app.py", scripts_dir / "build_core_engines_standalone_app.py"),
        ("SECURITY.md", docs_dir / "SECURITY.md"),
        ("termux_and_desktop_cheatsheet.md", docs_dir / "termux_and_desktop_cheatsheet.md"),
        ("termux_and_desktop_cheatsheet.pdf", docs_dir / "termux_and_desktop_cheatsheet.pdf"),
        ("alpha_tester_quickstart_guide.md", docs_dir / "alpha_tester_quickstart_guide.md"),
        ("index.md", docs_dir / "index.md"),
    ]
    
    for src_name, dest_path in file_mappings:
        src_path = base_dir / src_name
        if src_path.exists():
            shutil.copy(src_path, dest_path)
            print(f"[✓] File mapped & synced: {src_name} -> {dest_path.relative_to(base_dir)}")
            
    # 5. Execute Automated Pruning Engine
    prune_obsolete_versioned_files(base_dir)
    
    print("==================================================================")
    print(f"OMNIVERSE PROJECT ORGANIZATION & CANONICALIZATION COMPLETE [v{__version__}]")
    print("==================================================================")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Omniverse Project Organizer & Automated Pruning Engine")
    parser.add_argument("--version", "-v", action="version", version=f"organize_project.py version {__version__} ({BUILD_REVISION})")
    args = parser.parse_args()

    target = Path.cwd().resolve()
    organize_and_cleanup_project(target)
