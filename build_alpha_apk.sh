#!/usr/bin/env bash
# ==============================================================================
# THE KICKBACK (com.kickback) — STANDALONE CLOSED ALPHA APK BUILD SCRIPT
# Direct 1-Click Build for October 1st Alpha Launch (0% Termux / End-User Direct)
# ==============================================================================

set -e

echo "=============================================================================="
echo "🚀 THE KICKBACK — STANDALONE RELEASE APK BUILD PIPELINE (v1.0.0-alpha.1)"
echo "Target Package: com.kickback"
echo "Target Entrypoint: mobile/lib/omni_hub_gateway_launcher_ui.dart"
echo "Output Target: app-release.apk"
echo "=============================================================================="

# ------------------------------------------------------------------------------
# STEP 1: Verify Build Environment Requirements
# ------------------------------------------------------------------------------
echo "🔍 [1/5] Verifying local build toolchain (Flutter, Java JDK, Android SDK)..."

if ! command -v flutter >/dev/null 2>&1; then
    echo "❌ ERROR: 'flutter' CLI is not installed or not in PATH."
    echo "   Please install Flutter SDK (>=3.16.0) or run this build via GitHub Actions."
    exit 1
fi

if ! command -v java >/dev/null 2>&1; then
    echo "❌ ERROR: Java JDK (JDK 17 recommended) is not found in PATH."
    exit 1
fi

echo "    ✓ Flutter CLI detected: $(flutter --version | head -n 1)"
echo "    ✓ Java environment verified."

# ------------------------------------------------------------------------------
# STEP 2: Navigate to Mobile Project Directory
# ------------------------------------------------------------------------------
echo "📁 [2/5] Locating mobile project root..."

if [ -d "mobile" ]; then
    cd mobile
elif [ -f "pubspec.yaml" ]; then
    echo "    ✓ Already in mobile root directory."
else
    echo "❌ ERROR: Could not locate 'mobile/' directory or 'pubspec.yaml'."
    exit 1
fi

# ------------------------------------------------------------------------------
# STEP 3: Clean & Fetch Dependencies
# ------------------------------------------------------------------------------
echo "📦 [3/5] Cleaning build cache and fetching Flutter pub dependencies..."
flutter clean
flutter pub get
echo "    ✓ Dependencies resolved successfully."

# ------------------------------------------------------------------------------
# STEP 4: Generate Branded App Icons (If Configured)
# ------------------------------------------------------------------------------
echo "🎨 [4/5] Checking launcher icon generation..."
if grep -q "flutter_launcher_icons" pubspec.yaml; then
    echo "    ├─ Generating branded launcher icons for com.kickback..."
    flutter pub run flutter_launcher_icons || true
    echo "    ✓ Launcher icons compiled."
else
    echo "    ├─ Skipping icon generation (flutter_launcher_icons not in pubspec.yaml)."
fi

# ------------------------------------------------------------------------------
# STEP 5: Compile Standalone Release APK
# ------------------------------------------------------------------------------
echo "⚡ [5/5] Compiling standalone release APK for Android..."

TARGET_FILE="lib/omni_hub_gateway_launcher_ui.dart"
if [ ! -f "$TARGET_FILE" ]; then
    if [ -f "lib/main.dart" ]; then
        TARGET_FILE="lib/main.dart"
    fi
fi

echo "    ├─ Target entrypoint: $TARGET_FILE"
flutter build apk --release --target="$TARGET_FILE"

APK_PATH="build/app/outputs/flutter-apk/app-release.apk"

if [ -f "$APK_PATH" ]; then
    echo "=============================================================================="
    echo "🎉 STANDALONE RELEASE BUILD SUCCESSFUL!"
    echo "=============================================================================="
    echo "📦 Output APK Location: $(pwd)/$APK_PATH"
    echo "📱 Package Identifier:  com.kickback"
    echo "🚀 App Name:            The KickBack"
    echo "------------------------------------------------------------------------------"
    echo "💡 Distribution Instructions for October 1st Alpha Testers:"
    echo "   1. Upload 'app-release.apk' to Google Drive, Firebase, or your website."
    echo "   2. Share the download link with your 50 alpha testers."
    echo "   3. Testers tap the link, install, and launch directly from their home screen!"
    echo "=============================================================================="
else
    echo "❌ Build finished, but output APK was not found at expected path: $APK_PATH"
    exit 1
fi
