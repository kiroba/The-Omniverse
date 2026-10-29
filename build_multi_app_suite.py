#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE MULTI-APP WORKSPACE SUITE GENERATOR [v5.4.0]
==============================================================================
System Architecture:
- Generates isolated standalone Flutter projects inside `apps/`:
  1. `apps/idle_plaza_standalone`    -> Halo Plaza & Combat Brawler APK
  2. `apps/phaser_studio_standalone` -> OmniPhaser 2D Creator Studio Desktop/APK
  3. `apps/kickback_main_standalone`  -> KickBack Main Social Network APK
  4. `apps/mesh_monitor_standalone`  -> Mobile Mesh Monitor Utility APK
  5. `apps/omniverse_superapp_master` -> Full Unified Superapp APK
- Android Configuration:
  * AGP 8.11.1, CompileSDK 36, TargetSDK 36, MinSDK 26
  * Android NDK 27.0.12077973 (Required for sqflite_android)
  * Kotlin Target 2.2.20 & Gradle Wrapper 8.14
  * AndroidX Enabled in BOTH root and app gradle.properties (android.useAndroidX=true)
  * AAPT Safe Mipmap Adaptive Icon separation (mipmap vs mipmap-anydpi-v26)
- Automatic Dart code sanitizer for invalid color constants and CrossAlignment typos.
- Embedded versioning: v5.4.0 (Build 2026-10-19.v5.4-canonical).
==============================================================================
"""

import os
import sys
import shutil
import stat
from pathlib import Path

__version__ = "5.4.0"
BUILD_REVISION = "2026-10-19.v5.4-canonical"

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
            code = f.read()
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
            if old in code:
                code = code.replace(old, new)
                modified = True
        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            print(f"  [✓] Sanitized Dart syntax in {file_path.name}")
    except Exception as e:
        print(f"  [!] Warning sanitizing {file_path.name}: {e}")

def generate_android_scaffolding(app_dir: Path, package_name: str, app_label: str,
                                 fragment_activity: bool = False, extra_permissions: list = None,
                                 remote_hub_cleartext: bool = False):
    """fragment_activity: MainActivity extends FlutterFragmentActivity (required by local_auth's
    BiometricPrompt). extra_permissions: additional <uses-permission> names for this app only."""
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
        coreLibraryDesugaringEnabled true
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
        versionCode (1000 + (System.getenv("OMNI_VERSION_CODE") ?: "0").toInteger())
        versionName "5.4.0"
    }}

    // Stable signing: CI points OMNI_KEYSTORE at a PKCS12 keystore so every build has
    // the same signature and installs over the previous one.
    //  - GitHub Releases (release.yml): private key decoded from repo secrets, and
    //    OMNI_REQUIRE_RELEASE_KEY=1 makes a missing keystore a hard build failure.
    //  - CI/test builds: the shared test key signing/omniverse-test.p12.
    //  - Local builds without the env var fall back to the debug key.
    signingConfigs {{
        release {{
            def ks = System.getenv("OMNI_KEYSTORE")
            if (ks != null && new File(ks).exists()) {{
                storeFile file(ks)
                storeType "pkcs12"
                storePassword System.getenv("OMNI_KEYSTORE_PASSWORD")
                keyAlias System.getenv("OMNI_KEY_ALIAS")
                keyPassword System.getenv("OMNI_KEY_PASSWORD")
            }} else if (System.getenv("OMNI_REQUIRE_RELEASE_KEY") == "1") {{
                throw new GradleException("OMNI_REQUIRE_RELEASE_KEY=1 but the release keystore is missing (OMNI_KEYSTORE=" + ks + "). Refusing to fall back to the debug key.")
            }}
        }}
    }}

    buildTypes {{
        release {{
            def ks = System.getenv("OMNI_KEYSTORE")
            signingConfig ((ks != null && new File(ks).exists()) ? signingConfigs.release : signingConfigs.debug)
        }}
    }}
}}

dependencies {{
    // Required by ota_update 7.x
    coreLibraryDesugaring "com.android.tools:desugar_jdk_libs:2.1.4"
}}

flutter {{
    source "../.."
}}
"""
    with open(app_android_dir / "build.gradle", "w", encoding="utf-8") as f:
        f.write(app_build_gradle)
        
    # 4. MainActivity.kt
    activity_class = "FlutterFragmentActivity" if fragment_activity else "FlutterActivity"
    main_activity = f"""package {package_name}

import io.flutter.embedding.android.{activity_class}

class MainActivity: {activity_class}()
"""
    with open(kotlin_dir / "MainActivity.kt", "w", encoding="utf-8") as f:
        f.write(main_activity)
        
    # 5. AndroidManifest.xml
    extra_perm_xml = "".join(
        f'    <uses-permission android:name="{perm}" />\n' for perm in (extra_permissions or [])
    )
    manifest_xml = f"""<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}">
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
{extra_perm_xml}    <application
        android:networkSecurityConfig="@xml/network_security_config"
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
        <!-- In-app OTA updates (ota_update plugin) -->
        <provider
            android:name="sk.fourq.otaupdate.OtaUpdateFileProvider"
            android:authorities="${{applicationId}}.ota_update_provider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/filepaths" />
        </provider>
        <receiver android:name="sk.fourq.otaupdate.InstallResultReceiver" android:exported="false">
            <intent-filter>
                <action android:name="${{applicationId}}.ACTION_INSTALL_COMPLETE"/>
            </intent-filter>
        </receiver>
    </application>
</manifest>
"""
    with open(app_android_dir / "src" / "main" / "AndroidManifest.xml", "w", encoding="utf-8") as f:
        f.write(manifest_xml)

    # 5b. Network security: allow plain HTTP ONLY to the on-device daemon (loopback).
    #     Everything else stays HTTPS-only (Android default since API 28).
    res_xml = main_res / "xml"
    res_xml.mkdir(parents=True, exist_ok=True)
    network_security_xml = """<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="false">127.0.0.1</domain>
        <domain includeSubdomains="false">localhost</domain>
    </domain-config>
</network-security-config>
"""
    if remote_hub_cleartext:
        # KickBack "Remote hub" setting: plain HTTP to another phone's daemon, usually its
        # Tailscale 100.x IP (Tailscale encrypts the link; the daemon also requires a bearer
        # token). IP ranges can't be listed in a domain-config, so cleartext is allowed app-wide
        # for this app only. Its other traffic (OTA updates) uses https URLs.
        network_security_xml = """<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true" />
</network-security-config>
"""
    with open(res_xml / "network_security_config.xml", "w", encoding="utf-8") as f:
        f.write(network_security_xml)
    filepaths_xml = """<?xml version="1.0" encoding="utf-8"?>
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <files-path name="internal_apk_storage" path="ota_update/"/>
</paths>
"""
    with open(res_xml / "filepaths.xml", "w", encoding="utf-8") as f:
        f.write(filepaths_xml)
        
    # 6. Launcher icon.
    # Every layer MUST have an intrinsic size. The old icon was an <adaptive-icon> made of
    # bare @android:color layers (and a <shape> with no <size> as fallback), so the icon
    # drawable reported width/height <= 0. Android's PackageInstaller turns the icon into a
    # Bitmap (PackageUtil.AppSnippet.getBitmapFromDrawable) and crashed with
    # "IllegalArgumentException: width and height must be > 0" when Install was tapped
    # (reproduced on API 35 emulators); on phones this showed up as
    # "There was a problem parsing the package". adb install never draws the icon, which
    # is why it still worked. Sized vector drawables fix it.
    icon_bg_xml = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#FF0B0F1A" android:pathData="M0,0h108v108h-108z" />
</vector>
"""
    icon_fg_xml = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:strokeColor="#FFFFFFFF" android:strokeWidth="7" android:fillColor="#00000000"
        android:pathData="M54,32a22,22 0,1 1,0 44a22,22 0,1 1,0 -44z" />
</vector>
"""
    # Fallback for the plain mipmap/ qualifier (only used below API 26), also sized.
    mipmap_icon_xml = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="48dp" android:height="48dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#FF0B0F1A" android:pathData="M0,0h108v108h-108z" />
    <path android:strokeColor="#FFFFFFFF" android:strokeWidth="7" android:fillColor="#00000000"
        android:pathData="M54,32a22,22 0,1 1,0 44a22,22 0,1 1,0 -44z" />
</vector>
"""
    anydpi_icon_xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
"""
    with open(res_draw / "ic_launcher_background.xml", "w", encoding="utf-8") as f:
        f.write(icon_bg_xml)
    with open(res_draw / "ic_launcher_foreground.xml", "w", encoding="utf-8") as f:
        f.write(icon_fg_xml)
    with open(res_mipmap / "ic_launcher.xml", "w", encoding="utf-8") as f:
        f.write(mipmap_icon_xml)
    with open(res_mipmap_anydpi / "ic_launcher.xml", "w", encoding="utf-8") as f:
        f.write(anydpi_icon_xml)

    # 7. styles.xml & launch_background.xml
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
        
    # 8. gradle.properties (Write to BOTH root android_dir AND app_android_dir)
    gradle_props = """org.gradle.jvmargs=-Xmx4096m -XX:+UseG1GC
android.useAndroidX=true
android.enableJetifier=true
android.nonTransitiveRClass=true
android.newDsl=false
android.defaults.buildfeatures.buildconfig=true
"""
    with open(android_dir / "gradle.properties", "w", encoding="utf-8") as f:
        f.write(gradle_props)
    with open(app_android_dir / "gradle.properties", "w", encoding="utf-8") as f:
        f.write(gradle_props)
        
    # 9. Gradle Wrapper
    wrapper_dir = android_dir / "gradle" / "wrapper"
    wrapper_dir.mkdir(parents=True, exist_ok=True)
    wrapper_props = """distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.14-bin.zip
"""
    with open(wrapper_dir / "gradle-wrapper.properties", "w", encoding="utf-8") as f:
        f.write(wrapper_props)

def create_standalone_project(base_dir: Path, app_folder_name: str, package_name: str, app_label: str, main_dart_src: str, auxiliary_files: list, search_paths: list,
                              extra_dependencies: dict = None, fragment_activity: bool = False, extra_permissions: list = None,
                              remote_hub_cleartext: bool = False):
    """extra_dependencies: {pub_package: version_constraint} added to this app's pubspec only."""
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
            shutil.copy(aux_file, mobile_lib / aux_file.name)
            sanitize_dart_code(mobile_lib / aux_file.name)
            print(f"  [✓] Linked dependency: {aux_file.name}")
            
    # pubspec.yaml
    extra_deps_yaml = "".join(f"  {name}: {ver}\n" for name, ver in (extra_dependencies or {}).items())
    pubspec = f"""name: {app_folder_name}
description: "{app_label} Standalone Subsystem APK"
publish_to: 'none'
version: 5.4.0+540

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.6
  http: ^1.2.0
  ota_update: ^7.1.0
  omni_core_ui:
    path: ../../../packages/omni_core_ui
  cryptography: ^2.7.0
  crypto: ^3.0.3
  sqflite: ^2.3.0
  path: ^1.9.0
{extra_deps_yaml}
dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0

flutter:
  uses-material-design: true
"""
    with open(app_dir / "mobile" / "pubspec.yaml", "w", encoding="utf-8") as f:
        f.write(pubspec)
        
    generate_android_scaffolding(app_dir, package_name, app_label,
                                 fragment_activity=fragment_activity, extra_permissions=extra_permissions,
                                 remote_hub_cleartext=remote_hub_cleartext)
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
        ["kickback_seamless_stripe_checkout.dart", "continuity_token_service.dart",
         "kickback_app_lock.dart", "kickback_secure_identity.dart", "kickback_hub_settings.dart",
         "kickback_platform.dart"],
        search_paths,
        # Biometric / device-credential app lock + Keystore-encrypted identity seed.
        # local_auth 2.x needs FlutterFragmentActivity and minSdk >= 23 (we use 26).
        # sqflite_common_ffi: sqflite has no Windows plugin, so the Windows desktop build
        # (release.yml) uses SQLite via FFI; package:sqlite3's build hook bundles the library.
        extra_dependencies={"local_auth": "^2.3.0", "flutter_secure_storage": "^9.2.4",
                            "sqflite_common_ffi": "^2.4.0"},
        fragment_activity=True,
        extra_permissions=["android.permission.USE_BIOMETRIC"],
        remote_hub_cleartext=True,  # Settings > Hub > Remote hub (http://100.x.y.z:5000)
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
    print(f"MULTI-APP SUITE GENERATION COMPLETE [v{__version__}] (AGP 8.11.1, CompileSDK 36, NDK 27.0.12077973, Kotlin 2.2.20, Gradle 8.14)")
    print("==================================================================")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        print(f"build_multi_app_suite.py version {__version__} ({BUILD_REVISION})")
        sys.exit(0)
    build_all_apps()
