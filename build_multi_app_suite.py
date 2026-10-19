#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE MULTI-APP WORKSPACE SUITE GENERATOR [v5.3.0]
==============================================================================
- Generates 5 isolated standalone Flutter projects inside `apps/`
- Android Build Specs: AGP 8.11.1 | CompileSDK 36 | minSdk 26 | NDK 27.0.12077973 | Kotlin 2.2.20 | Gradle 8.14
- AAPT Fix: Separates shape fallback in res/mipmap/ from <adaptive-icon> in res/mipmap-anydpi-v26/
- Includes automatic Dart sanitizer for CrossAlignment -> CrossAxisAlignment typos
==============================================================================
"""

import os
import sys
import shutil
import stat
from pathlib import Path

__version__ = "5.3.0"
BUILD_REVISION = "2026-10-19.v5.3-canonical"

def resolve_base_dir() -> Path:
    env_dir = os.environ.get("OMNIVERSE_BUILD_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    if os.environ.get("OMNIVERSE_CLOUD_BUILD") == "1" or os.environ.get("CI") == "true":
        workspace_path = Path("/workspace")
        if workspace_path.exists():
            return workspace_path
    return Path.cwd().resolve()

def find_file(filename: str, search_paths: list) -> Path:
    for p in search_paths:
        if p.exists():
            target = p / filename
            if target.exists():
                return target
            matches = list(p.glob(f"*{filename}*"))
            if matches:
                return matches[0]
    return None

def safe_rmtree(path: Path):
    if not path.exists():
        return
    def _remove_readonly(func, path_str, exc_info):
        try:
            os.chmod(path_str, stat.S_IWRITE)
            func(path_str)
        except Exception:
            pass
    try:
        shutil.rmtree(path, onerror=_remove_readonly)
    except Exception:
        for item in path.glob("*"):
            try:
                if item.is_dir():
                    shutil.rmtree(item, onerror=_remove_readonly)
                else:
                    os.chmod(item, stat.S_IWRITE)
                    item.unlink()
            except Exception:
                pass

def sanitize_dart_code(file_path: Path):
    if not file_path.exists():
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            c = f.read()
        replacements = {
            "Colors.black80": "Colors.black87",
            "Colors.black90": "Colors.black87",
            "Colors.white80": "Colors.white70",
            "CrossAlignment.start": "CrossAxisAlignment.start",
            "CrossAlignment.center": "CrossAxisAlignment.center",
            "CrossAlignment.end": "CrossAxisAlignment.end",
            "CrossAlignment.baseline": "CrossAxisAlignment.baseline",
            "CrossAlignment.stretch": "CrossAxisAlignment.stretch",
        }
        modified = False
        for old, new in replacements.items():
            if old in c:
                c = c.replace(old, new)
                modified = True
        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(c)
            print(f"  [✓] Sanitized Dart syntax in {file_path.name}")
    except Exception as e:
        print(f"  [!] Warning sanitizing {file_path.name}: {e}")

def generate_android_scaffolding(app_dir: Path, package_name: str, app_label: str):
    android_dir = app_dir / "mobile" / "android"
    app_android_dir = android_dir / "app"
    
    pkg_parts = package_name.split(".")
    kotlin_dir = app_android_dir / "src" / "main" / "kotlin" / Path(*pkg_parts)
    main_res = app_android_dir / "src" / "main" / "res"
    res_val = main_res / "values"
    res_draw = main_res / "drawable"
    res_mipmap = main_res / "mipmap"
    res_mipmap_anydpi = main_res / "mipmap-anydpi-v26"
    
    kotlin_dir.mkdir(parents=True, exist_ok=True)
    res_val.mkdir(parents=True, exist_ok=True)
    res_draw.mkdir(parents=True, exist_ok=True)
    res_mipmap.mkdir(parents=True, exist_ok=True)
    res_mipmap_anydpi.mkdir(parents=True, exist_ok=True)
    
    # 1. settings.gradle
    settings_gradle = f"""pluginManagement {{
    def flutterSdkPath = {{
        def properties = new Properties()
        def file = new File(rootProject.projectDir, "local.properties")
        if (file.exists()) {{
            properties.load(file.newDataInputStream())
        }}
        def sdkPath = properties.getProperty("flutter.sdk")
        assert sdkPath != null : "flutter.sdk not set in local.properties"
        return sdkPath
    }}()

    includeBuild("$flutterSdkPath/packages/flutter_tools/gradle")

    repositories {{
        google()
        mavenCentral()
        gradlePluginPortal()
    }}
}}

plugins {{
    id "dev.flutter.flutter-plugin-loader" version "1.0.0"
    id "com.android.application" version "8.11.1" apply false
    id "org.jetbrains.kotlin.android" version "2.2.20" apply false
}}

include ":app"
"""
    with open(android_dir / "settings.gradle", "w", encoding="utf-8") as f:
        f.write(settings_gradle)
        
    # 2. build.gradle (root)
    build_gradle = """allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.buildDir = "../build"
subprojects {
    project.buildDir = "${rootProject.buildDir}/${project.name}"
}
subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register("clean", Delete) {
    delete rootProject.buildDir
}
"""
    with open(android_dir / "build.gradle", "w", encoding="utf-8") as f:
        f.write(build_gradle)
        
    # 3. app/build.gradle
    app_build_gradle = f"""plugins {{
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
        versionCode 520
        versionName "5.2.0"
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
    with open(app_android_dir / "build.gradle", "w", encoding="utf-8") as f:
        f.write(app_build_gradle)
        
    # 4. MainActivity.kt
    main_activity = f"""package {package_name}

import io.flutter.embedding.android.FlutterActivity

class MainActivity: FlutterActivity()
"""
    with open(kotlin_dir / "MainActivity.kt", "w", encoding="utf-8") as f:
        f.write(main_activity)
        
    # 5. AndroidManifest.xml
    manifest_xml = f"""<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}">
    <application
        android:label="{app_label}"
        android:name="${{applicationName}}"
        android:icon="@mipmap/ic_launcher">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:theme="@style/LaunchTheme"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">
            <meta-data
                android:name="io.flutter.embedding.android.NormalTheme"
                android:resource="@style/NormalTheme" />
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
        <meta-data
            android:name="flutterEmbedding"
            android:value="2" />
    </application>
</manifest>
"""
    with open(app_android_dir / "src" / "main" / "AndroidManifest.xml", "w", encoding="utf-8") as f:
        f.write(manifest_xml)
        
    # 6. Mipmap Icon XML Fallback vs Adaptive
    shape_icon_xml = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="@android:color/black" />
</shape>
"""
    adaptive_icon_xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@android:color/black" />
    <foreground android:drawable="@android:color/white" />
</adaptive-icon>
"""
    with open(res_mipmap / "ic_launcher.xml", "w", encoding="utf-8") as f:
        f.write(shape_icon_xml)
    with open(res_mipmap_anydpi / "ic_launcher.xml", "w", encoding="utf-8") as f:
        f.write(adaptive_icon_xml)

def create_standalone_project(base_dir: Path, app_folder_name: str, package_name: str, app_label: str, main_dart_src: str, dependency_darts: list, search_paths: list):
    app_dir = base_dir / "apps" / app_folder_name
    mobile_dir = app_dir / "mobile"
    lib_dir = mobile_dir / "lib"
    
    safe_rmtree(app_dir)
    lib_dir.mkdir(parents=True, exist_ok=True)
    
    src_main = find_file(main_dart_src, search_paths)
    if src_main and src_main.exists():
        shutil.copyfile(src_main, lib_dir / "main.dart")
        print(f"  [✓] Linked main.dart from {src_main.name}")
        sanitize_dart_code(lib_dir / "main.dart")
    else:
        fallback_main = f"""import 'package:flutter/material.dart';

void main() => runApp(const MaterialApp(
  home: Scaffold(
    body: Center(child: Text('{app_label} Standalone')),
  ),
));
"""
        with open(lib_dir / "main.dart", "w", encoding="utf-8") as f:
            f.write(fallback_main)
        print(f"  [!] Fallback main.dart created for {app_label}")

    for dep_name in dependency_darts:
        dep_path = find_file(dep_name, search_paths)
        if dep_path and dep_path.exists():
            shutil.copyfile(dep_path, lib_dir / dep_name)
            print(f"  [✓] Linked dependency: {dep_name}")
            sanitize_dart_code(lib_dir / dep_name)

    pubspec = f"""name: {app_folder_name}
description: {app_label} Standalone Mobile Application
publish_to: 'none'
version: 5.2.0+520

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.8
  sqflite: ^2.3.3+1
  path: ^1.9.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0

flutter:
  uses-material-design: true
"""
    with open(app_dir / "mobile" / "pubspec.yaml", "w", encoding="utf-8") as f:
        f.write(pubspec)
        
    generate_android_scaffolding(app_dir, package_name, app_label)
    print(f"[✓] Project generated: apps/{app_folder_name}/mobile (AGP 8.11.1, CompileSDK 36, NDK 27.0.12077973, Kotlin 2.2.20, Gradle 8.14 Ready)")

def build_all_apps():
    base_dir = resolve_base_dir()
    print("==================================================================")
    print(f"OMNIVERSE MULTI-APP SUITE GENERATOR [v{__version__}]")
    print(f"Revision: {BUILD_REVISION}")
    print("==================================================================")
    print(f"[INFO] Root Directory: {base_dir}")
    
    search_paths = [
        base_dir,
        base_dir / "mobile" / "lib",
        base_dir / "backend",
        base_dir / "scripts",
        Path.cwd()
    ]
    if (Path("/workspace") / "scratch").exists():
        search_paths.append(Path("/workspace") / "scratch")
    if (Path("/workspace") / "artifacts").exists():
        search_paths.append(Path("/workspace") / "artifacts")
        
    print("\n[1/5] Building Idle Plaza & Combat Brawler Standalone...")
    create_standalone_project(
        base_dir,
        "idle_plaza_standalone",
        "com.omniverse.idle_plaza",
        "Omniverse Idle Plaza",
        "halo_plaza_experience_ui.dart",
        ["plaza_fighting_game_engine.dart", "continuity_token_service.dart"],
        search_paths
    )

    print("\n[2/5] Building OmniPhaser 2D Creator Studio Standalone...")
    create_standalone_project(
        base_dir,
        "phaser_studio_standalone",
        "com.omniverse.phaser_studio",
        "OmniPhaser 2D Studio",
        "omni_phaser_studio_ui.dart",
        [],
        search_paths
    )

    print("\n[3/5] Building The KickBack Main App Standalone...")
    create_standalone_project(
        base_dir,
        "kickback_main_standalone",
        "com.omniverse.kickback",
        "The KickBack Social Network",
        "kickback_main_app_ui.dart",
        ["kickback_seamless_stripe_checkout.dart", "continuity_token_service.dart"],
        search_paths
    )

    print("\n[4/5] Building Mobile Mesh Monitor Standalone...")
    create_standalone_project(
        base_dir,
        "mesh_monitor_standalone",
        "com.omniverse.mesh_monitor",
        "Omniverse Mesh Monitor",
        "omni_mobile_mesh_monitor_ui.dart",
        [],
        search_paths
    )

    print("\n[5/5] Building Omniverse Unified Superapp Master...")
    create_standalone_project(
        base_dir,
        "omniverse_superapp_master",
        "com.omniverse.superapp",
        "The Omniverse Superapp",
        "omniverse_superapp_master_ui.dart",
        [
            "kickback_main_app_ui.dart",
            "halo_plaza_experience_ui.dart",
            "plaza_fighting_game_engine.dart",
            "continuity_token_service.dart",
            "kickback_seamless_stripe_checkout.dart"
        ],
        search_paths
    )

    print("\n==================================================================")
    print(f"MULTI-APP SUITE GENERATION COMPLETE [v{__version__}] (AGP 8.11.1, CompileSDK 36, NDK 27.0.12077973, Kotlin 2.2.20, Gradle 8.14)")
    print("==================================================================")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        print(f"build_multi_app_suite.py version {__version__} ({BUILD_REVISION})")
        sys.exit(0)
    build_all_apps()
