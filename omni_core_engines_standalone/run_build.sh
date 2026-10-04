#!/usr/bin/env bash
set -euo pipefail
echo "🚀 Building Standalone Core Engines App APK..."
cd mobile
flutter clean
flutter pub get
flutter build apk --release
echo "✅ Build Complete: mobile/build/app/outputs/flutter-apk/app-release.apk"
