#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE MASTER MULTI-PROJECT MANAGER [v1.0.0]
==============================================================================
System Architecture:
- Manages decoupled standalone repositories across the Omniverse workspace:
  1. `The-Omniverse`       -> Master Umbrella & Unified Superapp Repo
  2. `KickBack-Social`     -> Standalone KickBack Social Network Repo
  3. `Halo-Plaza-Idle`     -> Standalone Spatial Hub & Combat Brawler Repo
  4. `Omni-Mesh-Monitor`   -> Standalone 1-Node Telemetry Observer Repo
  5. `OmniPhaser-Studio`   -> Standalone 2D Desktop/Mobile Creator Engine Repo
  6. `OmniCast`            -> Standalone P2P WebRTC Video & Chat Testing App
- Embedded App Scaffolder Engine (`--create <app_name>`):
  * Generates production Flutter layout (lib/main.dart, pubspec.yaml).
  * Android AGP 8.11.1, CompileSDK 36, MinSDK 26, NDK 27.0.12077973, useAndroidX=true.
  * AAPT-safe adaptive icons (mipmap vs mipmap-anydpi-v26).
  * Dedicated GitHub Actions parallel matrix workflow (.github/workflows/build_apk.yml).
- Browser Download Ingestion:
  * Automatically detects `filename (1).ext` duplicates from Firefox/Chrome.
  * Overwrites target canonical files and purges lingering `(1)` copies.
==============================================================================
"""

import os
import sys
import shutil
import glob
import re
from pathlib import Path

__version__ = "1.0.0"
BUILD_REVISION = "2026-10-20.v1.0-polyrepo"

REPO_REGISTRY = {
    "The-Omniverse": "Master Umbrella & Unified Superapp Shell",
    "KickBack-Social": "Standalone KickBack Social Network",
    "Halo-Plaza-Idle": "Spatial Hub & Arcade Combat Brawler",
    "Omni-Mesh-Monitor": "1-Node Telemetry & Network Observer",
    "OmniPhaser-Studio": "2D Desktop/Mobile Creator Studio Engine",
    "OmniCast": "P2P WebRTC Video & Real-Time Mesh Chat"
}

def resolve_base_dir() -> Path:
    env_dir = os.environ.get("OMNIVERSE_BUILD_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    if os.environ.get("OMNIVERSE_CLOUD_BUILD") == "1" or os.environ.get("CI") == "true":
        workspace_path = Path("/workspace")
        if workspace_path.exists():
            return workspace_path
    return Path.cwd().resolve()

def ingest_browser_downloads(base_dir: Path):
    print("------------------------------------------------------------------")
    print("🧹 BROWSER DOWNLOAD AUTO-INGEST: SCANNING FOR (1) DUPLICATE FILES...")
    print("------------------------------------------------------------------")
    pattern = re.compile(r"^(.*?)\s*\(\d+\)\.(.*)$")
    search_dirs = [base_dir, base_dir / "scripts", base_dir / "mobile" / "lib"]
    
    ingested = 0
    for sdir in search_dirs:
        if not sdir.exists():
            continue
        for file_path in sdir.glob("* (*).*"):
            match = pattern.match(file_path.name)
            if match:
                clean_name = f"{match.group(1)}.{match.group(2)}"
                canonical_path = sdir / clean_name
                try:
                    shutil.move(str(file_path), str(canonical_path))
                    ingested += 1
                    print(f"[✓] Auto-ingested browser download: {file_path.name} -> {clean_name}")
                except Exception as e:
                    print(f"[!] Warning ingesting {file_path.name}: {e}")
    if ingested == 0:
        print("[✓] No browser duplicate (1) files found.")

def scaffold_standalone_repo(base_dir: Path, app_name: str, app_label: str, package_name: str):
    print("==================================================================")
    print(f"🚀 SCAFFOLDING STANDALONE REPOSITORY: {app_name}")
    print("==================================================================")
    repo_dir = base_dir / "apps" / app_name if (base_dir / "apps").exists() else base_dir / app_name
    mobile_lib = repo_dir / "mobile" / "lib"
    mobile_android = repo_dir / "mobile" / "android"
    app_android = mobile_android / "app"
    workflows_dir = repo_dir / ".github" / "workflows"

    mobile_lib.mkdir(parents=True, exist_ok=True)
    app_android.mkdir(parents=True, exist_ok=True)
    workflows_dir.mkdir(parents=True, exist_ok=True)

    # 1. main.dart
    main_dart = f"""import 'package:flutter/material.dart';

void main() {{
  runApp(const {app_name.replace('-', '').replace('_', '').capitalize()}App());
}}

class {app_name.replace('-', '').replace('_', '').capitalize()}App extends StatelessWidget {{
  const {app_name.replace('-', '').replace('_', '').capitalize()}App({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: '{app_label}',
      theme: ThemeData.dark(),
      home: Scaffold(
        appBar: AppBar(title: const Text('{app_label}')),
        body: const Center(
          child: Text(
            '{app_label} Standalone Subsystem Ready\nConnected to Local Engine (127.0.0.1)',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16),
          ),
        ),
      ),
    );
  }}
}}
"""
    (mobile_lib / "main.dart").write_text(main_dart, encoding="utf-8")

    # 2. pubspec.yaml
    pubspec = f"""name: {app_name.lower().replace('-', '_')}
description: "{app_label} Standalone Subsystem Package"
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.6
  cryptography: ^2.7.0
  crypto: ^3.0.3
  sqflite: ^2.3.0
  path: ^1.9.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0

flutter:
  uses-material-design: true
"""
    (repo_dir / "mobile" / "pubspec.yaml").write_text(pubspec, encoding="utf-8")

    # 3. Android Scaffolding
    package_path = package_name.replace(".", "/")
    kotlin_dir = app_android / "src" / "main" / "kotlin" / Path(package_path)
    res_mipmap = app_android / "src" / "main" / "res" / "mipmap"
    res_mipmap_v26 = app_android / "src" / "main" / "res" / "mipmap-anydpi-v26"
    
    kotlin_dir.mkdir(parents=True, exist_ok=True)
    res_mipmap.mkdir(parents=True, exist_ok=True)
    res_mipmap_v26.mkdir(parents=True, exist_ok=True)

    # gradle.properties (AndroidX Enabled)
    gradle_props = """org.gradle.jvmargs=-Xmx4096m -XX:+UseG1GC
android.useAndroidX=true
android.enableJetifier=true
android.nonTransitiveRClass=true
android.newDsl=false
android.defaults.buildfeatures.buildconfig=true
"""
    (mobile_android / "gradle.properties").write_text(gradle_props, encoding="utf-8")
    (app_android / "gradle.properties").write_text(gradle_props, encoding="utf-8")

    # app/build.gradle
    app_gradle = f"""plugins {{
    id "com.android.application"
    id "kotlin-android"
    id "dev.flutter.flutter-gradle-plugin"
}}

android {{
    namespace "{package_name}"
    compileSdk 36
    ndkVersion "27.0.12077973"

    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}

    kotlinOptions {{
        jvmTarget = "17"
    }}

    defaultConfig {{
        applicationId "{package_name}"
        minSdk 26
        targetSdk 36
        versionCode 100
        versionName "1.0.0"
    }}

    buildTypes {{
        release {{
            signingConfig signingConfigs.debug
        }}
    }}
}}

flutter {{
    source "../.."
}}
"""
    (app_android / "build.gradle").write_text(app_gradle, encoding="utf-8")

    # Icons
    shape_xml = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="@android:color/black" />
</shape>
"""
    adaptive_xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@android:color/black" />
    <foreground android:drawable="@android:color/white" />
</adaptive-icon>
"""
    (res_mipmap / "ic_launcher.xml").write_text(shape_xml, encoding="utf-8")
    (res_mipmap_v26 / "ic_launcher.xml").write_text(adaptive_xml, encoding="utf-8")

    # CI Workflow
    workflow_yml = f"""name: 🚀 {app_label} Standalone Build Matrix

on:
  push:
    branches: [ main, desktop ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-apk:
    name: 📦 Build {app_label} APK
    runs-on: ubuntu-latest
    steps:
      - name: 📁 Checkout Repository
        uses: actions/checkout@v4

      - name: ☕ Setup Java 17
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'

      - name: ⚡ Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          channel: 'stable'
          cache: true

      - name: 🔨 Build Release Universal FAT APK
        run: |
          cd mobile
          flutter build apk --release --android-skip-build-dependency-validation

      - name: 📤 Upload Build Artifact
        uses: actions/upload-artifact@v4
        with:
          name: {app_name.lower().replace('-', '_')}-release-apk
          path: mobile/build/app/outputs/flutter-apk/app-release.apk
"""
    (workflows_dir / "build_apk.yml").write_text(workflow_yml, encoding="utf-8")
    print(f"[✓] Scaffolding complete for {app_name} ({package_name})")

def main():
    base_dir = resolve_base_dir()
    print("==================================================================")
    print(f"OMNIVERSE MASTER MULTI-PROJECT MANAGER [v{__version__}]")
    print(f"Revision: {BUILD_REVISION}")
    print("==================================================================")
    print(f"[INFO] Workspace Root: {base_dir}")

    ingest_browser_downloads(base_dir)

    # Check for --create flag
    if len(sys.argv) > 2 and sys.argv[1] == "--create":
        new_app = sys.argv[2]
        label = sys.argv[3] if len(sys.argv) > 3 else new_app.replace("-", " ").title()
        pkg = f"com.omniverse.{new_app.lower().replace('-', '_')}"
        scaffold_standalone_repo(base_dir, new_app, label, pkg)
        return

    # Scaffold OmniCast automatically as part of the initial polyrepo setup
    scaffold_standalone_repo(
        base_dir,
        "OmniCast",
        "OmniCast P2P WebRTC Video & Chat",
        "com.omniverse.omnicast"
    )

    print("------------------------------------------------------------------")
    print("📋 REGISTERED STANDALONE REPOSITORIES MATRIX:")
    print("------------------------------------------------------------------")
    for repo, desc in REPO_REGISTRY.items():
        exists = (base_dir / "apps" / repo).exists() or (base_dir / repo).exists()
        status = "[✓] Active" if exists else "[+] Ready to Scaffold"
        print(f"  * {repo:<20} {status:<20} -> {desc}")
    print("==================================================================")
    print("OMNIVERSE MULTI-PROJECT MANAGER RUN COMPLETE")
    print("==================================================================")

if __name__ == "__main__":
    main()
