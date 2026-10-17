#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE PROJECT ORGANIZER & WORKFLOW CONSOLIDATOR (V11)
==============================================================================
- Scans and organizes Flutter UIs, Python daemons, assets, and documentation.
- Consolidates GitHub Actions workflows into `.github/workflows/` using
  `subosito/flutter-action@v2` and `flutter clean`.
- Automatically removes stray or duplicate `.yml`/`.yaml` files from subdirectories
  to prevent GitHub Actions workflow resolution issues.
==============================================================================
"""

import os
import sys
import shutil
from pathlib import Path

BUILD_APK_YML = """name: Build Omniverse Standalone APK

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch: # Allows manual trigger from GitHub UI

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: 📥 Checkout Repository
        uses: actions/checkout@v4

      - name: 🐍 Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: ⚙️ Organize Repository & Generate Standalone App
        run: |
          python3 organize_project.py || true
          python3 build_core_engines_standalone_app-v4.py || python3 build_core_engines_standalone_app.py || python3 scripts/build_core_engines_standalone_app-v4.py || python3 core/engines/build_core_engines_standalone_app-v4.py

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
          cd omni_core_engines_standalone/mobile
          flutter clean

      - name: 📦 Install Flutter Dependencies
        run: |
          cd omni_core_engines_standalone/mobile
          flutter pub get

      - name: 🔨 Build Release APK
        run: |
          cd omni_core_engines_standalone/mobile
          flutter build apk --release --target-platform android-arm64

      - name: 📤 Upload APK Artifact
        uses: actions/upload-artifact@v4
        with:
          name: omniverse-core-engines-release-apk
          path: omni_core_engines_standalone/mobile/build/app/outputs/flutter-apk/app-release.apk
          if-no-files-found: error
"""

BUILD_MONITOR_APK_YML = """name: Build Omni Mobile Mesh Monitor APK

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build-monitor:
    runs-on: ubuntu-latest

    steps:
      - name: 📥 Checkout Repository
        uses: actions/checkout@v4

      - name: 🐍 Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: ⚙️ Generate Standalone Mobile Mesh Monitor App
        run: |
          python3 build_mobile_mesh_monitor_app.py || python3 build_mobile_mesh_monitor_app_v2.py || python3 scripts/build_mobile_mesh_monitor_app-v2.py

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
          cd omni_mobile_mesh_monitor_app/mobile
          flutter clean

      - name: 📦 Install Flutter Dependencies
        run: |
          cd omni_mobile_mesh_monitor_app/mobile
          flutter pub get

      - name: 🔨 Build Release APK
        run: |
          cd omni_mobile_mesh_monitor_app/mobile
          flutter build apk --release --target-platform android-arm64

      - name: 📤 Upload Monitor APK Artifact
        uses: actions/upload-artifact@v4
        with:
          name: omni-mobile-mesh-monitor-release-apk
          path: omni_mobile_mesh_monitor_app/mobile/build/app/outputs/flutter-apk/app-release.apk
          if-no-files-found: error
"""

def organize_and_cleanup_project(base_dir: Path):
    print("==================================================================")
    print("OMNIVERSE PROJECT ORGANIZER & WORKFLOW CONSOLIDATOR (V11)")
    print("==================================================================")

    # 1. Ensure canonical workflow directory
    workflows_dir = base_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    with open(workflows_dir / "build_apk.yml", "w", encoding="utf-8") as f:
        f.write(BUILD_APK_YML)
    print("[✓] Finalized canonical workflow: .github/workflows/build_apk.yml")

    with open(workflows_dir / "build_monitor_apk.yml", "w", encoding="utf-8") as f:
        f.write(BUILD_MONITOR_APK_YML)
    print("[✓] Finalized canonical workflow: .github/workflows/build_monitor_apk.yml")

    # 2. Cleanup stray workflow YAMLs in subdirectories to avoid GitHub confusion
    subdirs_to_check = [
        base_dir / "mobile",
        base_dir / "backend",
        base_dir / "scripts",
        base_dir / "docs",
        base_dir / "tools"
    ]

    for sdir in subdirs_to_check:
        if sdir.exists():
            for stray in sdir.rglob("*.yml"):
                if stray.name in ["build_apk.yml", "build_monitor_apk.yml", "codemagic.yaml"]:
                    try:
                        stray.unlink()
                        print(f"[✓] Purged stray workflow from subdirectory: {stray}")
                    except Exception:
                        pass
            for stray in sdir.rglob("*.yaml"):
                if stray.name in ["build_yaml.yaml", "build_apk.yaml", "build_monitor_apk.yaml"]:
                    try:
                        stray.unlink()
                        print(f"[✓] Purged stray workflow from subdirectory: {stray}")
                    except Exception:
                        pass

    # 3. Standardized mappings
    mobile_lib = base_dir / "mobile" / "lib"
    mobile_assets_img = base_dir / "mobile" / "assets" / "images"
    mobile_assets_mods = base_dir / "mobile" / "assets" / "mods"
    backend_dir = base_dir / "backend"
    scripts_dir = base_dir / "scripts"
    docs_dir = base_dir / "docs"

    for d in [mobile_lib, mobile_assets_img, mobile_assets_mods, backend_dir, scripts_dir, docs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    mappings = [
        ("kickback_main_app_ui-v4.dart", mobile_lib / "kickback_main_app_ui.dart"),
        ("halo_plaza_experience_ui-v4.dart", mobile_lib / "halo_plaza_experience_ui.dart"),
        ("omni_phaser_studio_ui.dart", mobile_lib / "omni_phaser_studio_ui.dart"),
        ("omni_mobile_mesh_monitor_ui.dart", mobile_lib / "omni_mobile_mesh_monitor_ui.dart"),
        ("alpha_tester_digital_flyer.png", mobile_assets_img / "alpha_tester_digital_flyer.png"),
        ("omni_mod_starter_templates.json", mobile_assets_mods / "omni_mod_starter_templates.json"),
        ("localsend_chunk_receiver.py", backend_dir / "localsend_chunk_receiver.py"),
        ("omni_mod_compiler.py", backend_dir / "omni_mod_compiler.py"),
        ("omni_phase1_security_suite.py", backend_dir / "omni_phase1_security_suite.py"),
        ("socioboard_b2b_gateway_adapter.py", backend_dir / "socioboard_b2b_gateway_adapter.py"),
        ("p2p_mesh_health_monitor.py", backend_dir / "p2p_mesh_health_monitor.py"),
        ("omni_flet_desktop_control_panel.py", backend_dir / "omni_flet_desktop_control_panel.py"),
        ("build_termux.sh", scripts_dir / "build_termux.sh"),
        ("build_core_engines_standalone_app-v4.py", scripts_dir / "build_core_engines_standalone_app-v4.py"),
        ("build_mobile_mesh_monitor_app-v2.py", scripts_dir / "build_mobile_mesh_monitor_app-v2.py"),
        ("SECURITY.md", docs_dir / "SECURITY.md"),
        ("termux_and_desktop_cheatsheet.md", docs_dir / "termux_and_desktop_cheatsheet.md"),
        ("termux_and_desktop_cheatsheet.pdf", docs_dir / "termux_and_desktop_cheatsheet.pdf"),
        ("alpha_tester_quickstart_guide.md", docs_dir / "alpha_tester_quickstart_guide.md"),
        ("index.md", docs_dir / "index.md"),
    ]

    for src_name, dest_file in mappings:
        for search_root in [base_dir, Path("/workspace/artifacts"), Path("/workspace/scratch")]:
            src_path = search_root / src_name
            if src_path.exists():
                shutil.copy(src_path, dest_file)
                print(f"[✓] File mapped & synced: {src_name} -> {dest_file.relative_to(base_dir) if dest_file.is_relative_to(base_dir) else dest_file}")
                break

    print("==================================================================")
    print("OMNIVERSE V11 PROJECT ORGANIZATION & CLEANUP COMPLETE!")
    print("==================================================================")
    return True

if __name__ == "__main__":
    target = Path(".").resolve()
    organize_and_cleanup_project(target)
