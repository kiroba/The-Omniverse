#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE CORE ENGINES STANDALONE APP BUILDER (RESILIENT ALIAS)
==============================================================================
Acts as a resilient fallback wrapper invoking the V4 build pipeline.
Auto-resolves write permissions across GitHub Actions, Termux, and local dev.
==============================================================================
"""

import os
import sys
import shutil
from pathlib import Path

# Try importing from local v4 script or inline execution
try:
    from build_core_engines_standalone_app_v4 import build_v4_standalone_app, resolve_base_dir
except ImportError:
    def resolve_base_dir() -> Path:
        env_dir = os.environ.get("OMNIVERSE_BUILD_DIR")
        if env_dir:
            return Path(env_dir).resolve()
        
        workspace_path = Path("/workspace")
        if workspace_path.exists():
            try:
                test_file = workspace_path / ".write_test"
                test_file.touch()
                test_file.unlink()
                return workspace_path
            except Exception:
                pass
                
        return Path.cwd().resolve()

    def build_v4_standalone_app(base_dir: Path = None):
        if base_dir is None:
            base_dir = resolve_base_dir()
            
        print("==================================================================")
        print("BUILDING OMNIVERSE CORE ENGINES STANDALONE APP (FALLBACK ALIAS)")
        print("==================================================================")
        print(f"[INFO] Target Base Directory: {base_dir}")
        
        target_dir = base_dir / "omni_core_engines_standalone"
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        target_dir.mkdir(parents=True, exist_ok=True)
        mobile_lib = target_dir / "mobile" / "lib"
        mobile_lib.mkdir(parents=True, exist_ok=True)
        
        fallback_ui = """import 'package:flutter/material.dart';

void main() {
  runApp(const KickBackApp());
}

class KickBackApp extends StatelessWidget {
  const KickBackApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'The KickBack & Omniverse',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        primaryColor: const Color(0xFF00FFCC),
      ),
      home: const Scaffold(
        body: Center(
          child: Text(
            'The KickBack & Omniverse Core Engines Active',
            style: TextStyle(color: Color(0xFF00FFCC), fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ),
      ),
    );
  }
}
"""
        with open(mobile_lib / "main.dart", "w", encoding="utf-8") as f:
            f.write(fallback_ui)

        pubspec_content = """name: omni_core_engines_standalone
description: "The KickBack & Omniverse Core Engines Mobile & Desktop Application"
publish_to: 'none'
version: 4.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.6

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0

flutter:
  uses-material-design: true
"""
        with open(target_dir / "mobile" / "pubspec.yaml", "w", encoding="utf-8") as f:
            f.write(pubspec_content)

        # Android Scaffolding
        android_dir = target_dir / "mobile" / "android"
        app_dir = android_dir / "app"
        kotlin_dir = app_dir / "src" / "main" / "kotlin" / "com" / "omniverse" / "core_engines"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        
        with open(android_dir / "settings.gradle", "w", encoding="utf-8") as f:
            f.write("""pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
plugins {
    id "dev.flutter.flutter-plugin-loader" version "1.0.0"
    id "com.android.application" version "8.7.3" apply false
    id "org.jetbrains.kotlin.android" version "2.0.20" apply false
}
include ":app"
""")
            
        with open(android_dir / "build.gradle", "w", encoding="utf-8") as f:
            f.write("""allprojects {
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
""")

        with open(app_dir / "build.gradle", "w", encoding="utf-8") as f:
            f.write("""plugins {
    id "com.android.application"
    id "kotlin-android"
    id "dev.flutter.flutter-gradle-plugin"
}
android {
    namespace "com.omniverse.core_engines"
    compileSdk 34
    defaultConfig {
        applicationId "com.omniverse.core_engines"
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName "4.0.0"
    }
}
flutter {
    source "../.."
}
""")

        with open(kotlin_dir / "MainActivity.kt", "w", encoding="utf-8") as f:
            f.write("""package com.omniverse.core_engines
import io.flutter.embedding.android.FlutterActivity
class MainActivity: FlutterActivity()
""")

        print("==================================================================")
        print("STANDALONE BUILD COMPLETE at:", target_dir)
        print("==================================================================")
        return True

if __name__ == "__main__":
    base = resolve_base_dir()
    build_v4_standalone_app(base)
