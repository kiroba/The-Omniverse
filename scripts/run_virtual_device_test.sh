#!/usr/bin/env bash
# ============================================================================
# AUTOMATED VIRTUAL DEVICE SETUP & INTEGRATION TEST RUNNER
# ============================================================================

set -e

echo "=============================================================================="
echo "🚀 OMNIVERSE VIRTUAL DEVICE TEST SUITE LAUNCHER"
echo "=============================================================================="

# 1. Check for Connected Virtual Devices
echo "[1/4] Detecting active Android Emulators / Virtual Devices..."
DEVICE_ID=$(flutter devices | grep -E "emulator|virtual" | head -n 1 | awk '{print $2}' || true)

if [ -z "$DEVICE_ID" ]; then
    echo "[!] No active emulator detected. Booting default Flutter emulator..."
    EMULATOR_NAME=$(flutter emulators | grep -v "Available" | head -n 1 | awk '{print $1}' || echo "Pixel_6_API_34")
    flutter emulators --launch "$EMULATOR_NAME"
    echo "[+] Waiting for virtual device to finish booting..."
    adb wait-for-device
    DEVICE_ID="emulator-5554"
fi

echo "[✓] Target Virtual Device Ready: $DEVICE_ID"

# 2. Fetch Dependencies
echo "[2/4] Resolving Flutter packages & integration_test dependencies..."
cd omni_core_engines_standalone/mobile || cd mobile || true
flutter pub get

# 3. Execute Integration Test
echo "[3/4] Running Automated E2E Test Suite on $DEVICE_ID..."
flutter test integration_test/app_test.dart -d "$DEVICE_ID"

echo "=============================================================================="
echo "🎉 VIRTUAL DEVICE TEST RUN COMPLETED SUCCESSFULLY!"
echo "=============================================================================="
