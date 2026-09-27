#!/usr/bin/env bash
# ==============================================================================
# The KickBack — 1-Click Desktop & Repository Bootstrapper
# Creates directory structures and writes all required build files with
# clean YAML syntax and Android v2 Embedding.
# ==============================================================================

set -e

echo "🚀 Bootstrapping The KickBack repository tree..."

# Create directory structures
mkdir -p .github/workflows
mkdir -p mobile/android/app/src/main/kotlin/com/kickback
mkdir -p mobile/android/app/src/main/res/mipmap-hdpi
mkdir -p mobile/lib
mkdir -p mobile/assets/images

# 1. Write GitHub Actions Workflow (.github/workflows/build_apk.yml)
cat << 'EOF' > .github/workflows/build_apk.yml
name: Build Standalone KickBack Alpha APK

on:
  push:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build-apk:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Java JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: 'microsoft'
          java-version: '17'

      - name: Set up Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.x'
          channel: 'stable'

      - name: Install Dependencies
        run: |
          if [ -d "mobile" ]; then cd mobile; fi
          flutter pub get

      - name: Build Release APK
        run: |
          if [ -d "mobile" ]; then cd mobile; fi
          flutter build apk --release --target=lib/omni_hub_gateway_launcher_ui.dart

      - name: Upload APK Artifact
        uses: actions/upload-artifact@v4
        with:
          name: The-KickBack-Alpha-v1.0
          path: |
            mobile/build/app/outputs/flutter-apk/app-release.apk
            build/app/outputs/flutter-apk/app-release.apk
EOF

# 2. Write Flutter Dependencies (mobile/pubspec.yaml)
cat << 'EOF' > mobile/pubspec.yaml
name: kickback
description: "The KickBack — Sovereign, Serverless P2P Social Ecosystem"
publish_to: 'none'

version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'
  flutter: '>=3.16.0'

dependencies:
  flutter:
    sdk: flutter

  cupertino_icons: ^1.0.6
  camera: ^0.10.5+9
  video_player: ^2.8.2
  google_fonts: ^6.1.0
  sqflite: ^2.3.0
  path_provider: ^2.1.2
  crypto: ^3.0.3
  pointycastle: ^3.7.3
  device_info_plus: ^9.1.1
  web_socket_channel: ^2.4.1
  connectivity_plus: ^5.0.2

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0
  flutter_launcher_icons: ^0.13.1

flutter:
  uses-material-design: true
  assets:
    - assets/images/
EOF

# 3. Write Kotlin MainActivity with v2 Embedding (mobile/android/app/src/main/kotlin/com/kickback/MainActivity.kt)
cat << 'EOF' > mobile/android/app/src/main/kotlin/com/kickback/MainActivity.kt
package com.kickback

import io.flutter.embedding.android.FlutterActivity

class MainActivity: FlutterActivity() {
}
EOF

# 4. Write Android Gradle Build Config (mobile/android/app/build.gradle)
cat << 'EOF' > mobile/android/app/build.gradle
plugins {
    id "com.android.application"
    id "kotlin-android"
    id "dev.flutter.flutter-gradle-plugin"
}

def localProperties = new Properties()
def localPropertiesFile = rootProject.file('local.properties')
if (localPropertiesFile.exists()) {
    localPropertiesFile.withReader('UTF-8') { reader ->
        localProperties.load(reader)
    }
}

def flutterVersionCode = localProperties.getProperty('flutter.versionCode') ?: '1'
def flutterVersionName = localProperties.getProperty('flutter.versionName') ?: '1.0'

android {
    namespace "com.kickback"
    compileSdkVersion 34
    ndkVersion flutter.ndkVersion

    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = '17'
    }

    defaultConfig {
        applicationId "com.kickback"
        minSdkVersion 21
        targetSdkVersion 34
        versionCode flutterVersionCode.toInteger()
        versionName flutterVersionName
    }

    buildTypes {
        release {
            signingConfig signingConfigs.debug
            minifyEnabled false
            shrinkResources false
        }
    }
}

flutter {
    source '../../'
}
EOF

# 5. Write AndroidManifest.xml (mobile/android/app/src/main/AndroidManifest.xml)
cat << 'EOF' > mobile/android/app/src/main/AndroidManifest.xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.kickback">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
    <uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />

    <uses-feature android:name="android.hardware.camera" android:required="true" />

    <application
        android:label="The KickBack"
        android:name="${applicationName}"
        android:icon="@mipmap/ic_launcher"
        android:hardwareAccelerated="true"
        android:allowBackup="false">

        <meta-data
            android:name="flutterEmbedding"
            android:value="2" />

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:theme="@style/LaunchTheme"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">

            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>

            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="kickback" android:host="invite" />
            </intent-filter>
        </activity>
    </application>
</manifest>
EOF

echo "✅ Bootstrap complete! All build files created with clean YAML formatting and Android v2 embedding."
