#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE CORE ENGINES STANDALONE APP BUILDER (V7 ALIAS)
==============================================================================
"""
from pathlib import Path
import sys
import os, shutil, json

def resolve_base_dir() -> Path:
    env_dir = os.environ.get("OMNIVERSE_BUILD_DIR")
    if env_dir: return Path(env_dir).resolve()
    if os.environ.get("OMNIVERSE_CLOUD_BUILD") == "1" or os.environ.get("CI") == "true":
        wp = Path("/workspace")
        if wp.exists(): return wp
    return Path.cwd().resolve()

def build_v7_standalone_app(base_dir: Path = None):
    if base_dir is None: base_dir = resolve_base_dir()
    target_dir = base_dir / "omni_core_engines_standalone"
    target_dir.mkdir(parents=True, exist_ok=True)
    mobile_lib = target_dir / "mobile" / "lib"
    mobile_assets = target_dir / "mobile" / "assets" / "mods"
    backend_dir = target_dir / "backend"
    mobile_lib.mkdir(parents=True, exist_ok=True)
    mobile_assets.mkdir(parents=True, exist_ok=True)
    backend_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Main UI fallback
    main_dart = mobile_lib / "main.dart"
    with open(main_dart, "w", encoding="utf-8") as f:
        f.write("import 'package:flutter/material.dart'; void main() => runApp(const MaterialApp(home: Scaffold(body: Center(child: Text('The Omniverse Standalone App')))));")
        
    # 2. Android Scaffolding with gradle.properties
    android_dir = target_dir / "mobile" / "android"
    app_dir = android_dir / "app"
    kotlin_dir = app_dir / "src" / "main" / "kotlin" / "com" / "omniverse" / "core_engines"
    res_val = app_dir / "src" / "main" / "res" / "values"
    res_draw = app_dir / "src" / "main" / "res" / "drawable"
    kotlin_dir.mkdir(parents=True, exist_ok=True)
    res_val.mkdir(parents=True, exist_ok=True)
    res_draw.mkdir(parents=True, exist_ok=True)
    
    with open(android_dir / "gradle.properties", "w", encoding="utf-8") as f:
        f.write("org.gradle.jvmargs=-Xmx4096m -XX:+UseG1GC\nandroid.useAndroidX=true\nandroid.enableJetifier=true\nandroid.nonTransitiveRClass=true\nandroid.newDsl=false\nandroid.defaults.buildfeatures.buildconfig=true\n")
        
    with open(android_dir / "settings.gradle", "w", encoding="utf-8") as f:
        f.write("pluginManagement {\n    def flutterSdkPath = {\n        def properties = new Properties()\n        def file = new File(rootProject.projectDir, \"local.properties\")\n        if (file.exists()) { properties.load(file.newDataInputStream()) }\n        def sdkPath = properties.getProperty(\"flutter.sdk\")\n        assert sdkPath != null : \"flutter.sdk not set in local.properties\"\n        return sdkPath\n    }()\n    includeBuild(\"$flutterSdkPath/packages/flutter_tools/gradle\")\n    repositories { google(); mavenCentral(); gradlePluginPortal() }\n}\nplugins {\n    id \"dev.flutter.flutter-plugin-loader\" version \"1.0.0\"\n    id \"com.android.application\" version \"8.2.1\" apply false\n    id \"org.jetbrains.kotlin.android\" version \"1.9.24\" apply false\n}\ninclude \":app\"\n")

    with open(android_dir / "build.gradle", "w", encoding="utf-8") as f:
        f.write("allprojects { repositories { google(); mavenCentral() } }\nrootProject.buildDir = \"../build\"\nsubprojects { project.buildDir = \"${rootProject.buildDir}/${project.name}\" }\nsubprojects { project.evaluationDependsOn(\":app\") }\ntasks.register(\"clean\", Delete) { delete rootProject.buildDir }\n")

    with open(app_dir / "build.gradle", "w", encoding="utf-8") as f:
        f.write("plugins {\n    id \"com.android.application\"\n    id \"kotlin-android\"\n    id \"dev.flutter.flutter-gradle-plugin\"\n}\nandroid {\n    namespace \"com.omniverse.core_engines\"\n    compileSdk 34\n    ndkVersion \"25.1.8937393\"\n    compileOptions { sourceCompatibility JavaVersion.VERSION_17; targetCompatibility JavaVersion.VERSION_17 }\n    kotlinOptions { jvmTarget = \"17\" }\n    defaultConfig { applicationId \"com.omniverse.core_engines\"; minSdk 24; targetSdk 34; versionCode 1; versionName \"1.0.0\" }\n    buildTypes { release { signingConfig signingConfigs.debug } }\n}\nflutter { source \"../..\" }\n")

    with open(kotlin_dir / "MainActivity.kt", "w", encoding="utf-8") as f:
        f.write("package com.omniverse.core_engines\nimport io.flutter.embedding.android.FlutterActivity\nclass MainActivity: FlutterActivity()\n")

    with open(app_dir / "src" / "main" / "AndroidManifest.xml", "w", encoding="utf-8") as f:
        f.write("<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\" package=\"com.omniverse.core_engines\"><application android:label=\"The Omniverse\" android:name=\"${applicationName}\" android:icon=\"@mipmap/ic_launcher\"><activity android:name=\".MainActivity\" android:exported=\"true\" android:launchMode=\"singleTop\" android:theme=\"@style/LaunchTheme\" android:configChanges=\"orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode\" android:hardwareAccelerated=\"true\" android:windowSoftInputMode=\"adjustResize\"><meta-data android:name=\"io.flutter.embedding.android.NormalTheme\" android:resource=\"@style/NormalTheme\" /><intent-filter><action android:name=\"android.intent.action.MAIN\"/><category android:name=\"android.intent.category.LAUNCHER\"/></intent-filter></activity><meta-data android:name=\"flutterEmbedding\" android:value=\"2\" /></application></manifest>")

    with open(res_val / "styles.xml", "w", encoding="utf-8") as f:
        f.write("<?xml version=\"1.0\" encoding=\"utf-8\"?><resources><style name=\"LaunchTheme\" parent=\"@android:style/Theme.Light.NoTitleBar\"><item name=\"android:windowBackground\">@drawable/launch_background</item></style><style name=\"NormalTheme\" parent=\"@android:style/Theme.Light.NoTitleBar\"><item name=\"android:windowBackground\">?android:attr/colorBackground</item></style></resources>")

    with open(res_draw / "launch_background.xml", "w", encoding="utf-8") as f:
        f.write("<?xml version=\"1.0\" encoding=\"utf-8\"?><layer-list xmlns:android=\"http://schemas.android.com/apk/res/android\"><item android:drawable=\"@android:color/black\" /></layer-list>")

    wrapper_dir = android_dir / "gradle" / "wrapper"
    wrapper_dir.mkdir(parents=True, exist_ok=True)
    with open(wrapper_dir / "gradle-wrapper.properties", "w", encoding="utf-8") as f:
        f.write("distributionBase=GRADLE_USER_HOME\ndistributionPath=wrapper/dists\nzipStoreBase=GRADLE_USER_HOME\nzipStorePath=wrapper/dists\ndistributionUrl=https\\://services.gradle.org/distributions/gradle-8.7-bin.zip\n")

    # 3. Windows CMake
    win_dir = target_dir / "mobile" / "windows"
    (win_dir / "runner").mkdir(parents=True, exist_ok=True)
    with open(win_dir / "CMakeLists.txt", "w", encoding="utf-8") as f:
        f.write("cmake_minimum_required(VERSION 3.14)\nproject(omni_core_engines_standalone LANGUAGES CXX)\nset(BINARY_NAME \"omni_core_engines_standalone\")\nset(FLUTTER_MANAGED_DIR \"${CMAKE_CURRENT_SOURCE_DIR}/flutter\")\ninclude(\"${FLUTTER_MANAGED_DIR}/generated_plugins.cmake\" OPTIONAL)\nadd_subdirectory(runner)\n")

    # 4. pubspec.yaml
    with open(target_dir / "mobile" / "pubspec.yaml", "w", encoding="utf-8") as f:
        f.write("name: omni_core_engines_standalone\ndescription: \"The KickBack & Omniverse Core Engines Mobile & Desktop Application\"\npublish_to: 'none'\nversion: 7.0.0+1\nenvironment:\n  sdk: '>=3.0.0 <4.0.0'\ndependencies:\n  flutter:\n    sdk: flutter\n  flutter_inappwebview: ^6.0.0\n  cupertino_icons: ^1.0.6\n  cryptography: ^2.7.0\n  crypto: ^3.0.3\n  sqflite: ^2.3.0\n  path: ^1.9.0\ndev_dependencies:\n  flutter_test:\n    sdk: flutter\n  flutter_lints: ^3.0.0\nflutter:\n  uses-material-design: true\n  assets:\n    - assets/mods/\n")
        
    print("[✓] Standalone app V7 generated successfully!")
    return True

if __name__ == "__main__":
    base = resolve_base_dir()
    build_v7_standalone_app(base)
