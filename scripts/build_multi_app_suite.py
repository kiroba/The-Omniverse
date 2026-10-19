#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE MULTI-APP WORKSPACE SUITE GENERATOR (V5.2 - KOTLIN 2.2.20 & SKIP VALIDATION)
==============================================================================
System Design Architecture:
Generates individual, isolated Flutter projects for each core subsystem:
1. `apps/idle_plaza_standalone`    -> Halo Plaza & Fighting Game Brawler APK
2. `apps/phaser_studio_standalone` -> OmniPhaser 2D Creator Studio APK (Desktop target)
3. `apps/kickback_main_standalone`  -> KickBack Main Social Network APK
4. `apps/mesh_monitor_standalone`  -> Mobile Mesh Monitor Utility APK
5. `apps/omniverse_superapp_master` -> Full Unified Superapp APK
==============================================================================
"""

import os
import sys
import shutil
import stat
import re
from pathlib import Path

__version__ = "5.2.0"
BUILD_REVISION = "2026-10-18.v5.2-canonical"

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
    """Safely removes a directory tree, handling Windows read-only locks & process holds."""
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
    """Fixes invalid Dart constants like Colors.black80 -> Colors.black87."""
    if not file_path.exists():
        return
    try:
        content = file_path.read_text(encoding="utf-8")
        if "Colors.black80" in content:
            content = content.replace("Colors.black80", "Colors.black87")
            file_path.write_text(content, encoding="utf-8")
            print(f"  [✓] Sanitized Dart code in {file_path.name} (Colors.black80 -> Colors.black87)")
    except Exception as e:
        print(f"  [!] Notice during Dart sanitization of {file_path.name}: {e}")

def generate_android_scaffolding(app_dir: Path, package_name: str, app_label: str):
    android_dir = app_dir / "mobile" / "android"
    app_android_dir = android_dir / "app"
    package_path = package_name.replace(".", "/")
    kotlin_dir = app_android_dir / "src" / "main" / "kotlin" / Path(package_path)
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
    
    # 1. settings.gradle with AGP 8.11.1 & Kotlin 2.2.20 (satisfies Flutter SDK requirements)
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
        
    # 3. app/build.gradle with compileSdk 36
    app_build_gradle = f"""plugins {{
    id "com.android.application"
    id "kotlin-android"
    id "dev.flutter.flutter-gradle-plugin"
}}

android {{
    namespace "{package_name}"
    compileSdk 36
    ndkVersion "25.1.8937393"

    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}

    kotlinOptions {{
        jvmTarget = "17"
    }}

    defaultConfig {{
        applicationId "{package_name}"
        minSdk 24
        targetSdk 36
        versionCode 1
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
        
    # 6. styles.xml, launch_background.xml & launcher icons
    styles_xml = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="LaunchTheme" parent="@android:style/Theme.Light.NoTitleBar">
        <item name="android:windowBackground">@drawable/launch_background</item>
    </style>
    <style name="NormalTheme" parent="@android:style/Theme.Light.NoTitleBar">
        <item name="android:windowBackground">?android:attr/colorBackground</item>
    </style>
</resources>
"""
    with open(res_val / "styles.xml", "w", encoding="utf-8") as f:
        f.write(styles_xml)
        
    bg_xml = """<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:drawable="@android:color/black" />
</layer-list>
"""
    with open(res_draw / "launch_background.xml", "w", encoding="utf-8") as f:
        f.write(bg_xml)

    # AAPT launcher icon XML resources
    icon_xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@android:color/black" />
    <foreground android:drawable="@drawable/launch_background" />
</adaptive-icon>
"""
    with open(res_mipmap / "ic_launcher.xml", "w", encoding="utf-8") as f:
        f.write(icon_xml)
    with open(res_mipmap_anydpi / "ic_launcher.xml", "w", encoding="utf-8") as f:
        f.write(icon_xml)
        
    # 7. gradle.properties (disabled newDsl validation issue)
    gradle_props = """org.gradle.jvmargs=-Xmx4096m -XX:+UseG1GC
android.useAndroidX=true
android.enableJetifier=true
android.nonTransitiveRClass=true
android.newDsl=false
android.defaults.buildfeatures.buildconfig=true
"""
    with open(android_dir / "gradle.properties", "w", encoding="utf-8") as f:
        f.write(gradle_props)
        
    # 8. Gradle Wrapper (GRADLE 8.14)
    wrapper_dir = android_dir / "gradle" / "wrapper"
    wrapper_dir.mkdir(parents=True, exist_ok=True)
    wrapper_props = """distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-8.14-bin.zip
"""
    with open(wrapper_dir / "gradle-wrapper.properties", "w", encoding="utf-8") as f:
        f.write(wrapper_props)

def create_standalone_project(base_dir: Path, app_folder_name: str, package_name: str, app_label: str, main_dart_src: str, auxiliary_files: list, search_paths: list):
    app_dir = base_dir / "apps" / app_folder_name
    safe_rmtree(app_dir)
        
    mobile_lib = app_dir / "mobile" / "lib"
    mobile_assets = app_dir / "mobile" / "assets" / "mods"
    mobile_lib.mkdir(parents=True, exist_ok=True)
    mobile_assets.mkdir(parents=True, exist_ok=True)
    
    # Copy or create main.dart
    main_file = find_file(main_dart_src, search_paths)
    if main_file:
        shutil.copy(main_file, mobile_lib / "main.dart")
        sanitize_dart_code(mobile_lib / "main.dart")
        print(f"  [✓] Linked main.dart from {main_file.name}")
    else:
        with open(mobile_lib / "main.dart", "w", encoding="utf-8") as f:
            f.write(f"import 'package:flutter/material.dart'; void main() => runApp(MaterialApp(home: Scaffold(body: Center(child: Text('{app_label} Standalone App')))));")
        print(f"  [!] Fallback main.dart created for {app_label}")
        
    # Copy auxiliary dart files
    for aux_name in auxiliary_files:
        aux_file = find_file(aux_name, search_paths)
        if aux_file:
            dst_aux = mobile_lib / aux_file.name
            shutil.copy(aux_file, dst_aux)
            sanitize_dart_code(dst_aux)
            print(f"  [✓] Linked dependency: {aux_file.name}")
            
    # pubspec.yaml
    pubspec = f"""name: {app_folder_name}
description: "{app_label} Standalone Subsystem APK"
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
    with open(app_dir / "mobile" / "pubspec.yaml", "w", encoding="utf-8") as f:
        f.write(pubspec)
        
    generate_android_scaffolding(app_dir, package_name, app_label)
    print(f"[✓] Project generated: apps/{app_folder_name}/mobile (AGP 8.11.1, CompileSDK 36, Kotlin 2.2.20, Gradle 8.14 Ready)")

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
    if (Path("/workspace") / "artifacts").exists():
        search_paths.append(Path("/workspace") / "artifacts")
        
    # 1. Idle Plaza & Combat Brawler App
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

    # 2. OmniPhaser 2D Creator Studio App
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

    # 3. KickBack Main Social Network App
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

    # 4. Mobile Mesh Monitor App
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

    # 5. Omniverse Unified Superapp Master
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
    print(f"MULTI-APP SUITE GENERATION COMPLETE [v{__version__}] (AGP 8.11.1, CompileSDK 36, Kotlin 2.2.20, Gradle 8.14)")
    print("==================================================================")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        print(f"build_multi_app_suite.py version {__version__} ({BUILD_REVISION})")
        sys.exit(0)
    build_all_apps()
