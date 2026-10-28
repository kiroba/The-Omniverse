#!/usr/bin/env bash
# Runs inside reactivecircus/android-emulator-runner once the emulator has booted.
# Installs $APK_PATH, launches $PKG and records what happened in $OUT_DIR.
# Always exits 0 so the workflow can upload artifacts; the verdict is in $OUT_DIR/result.env.
set -u
OUT="${OUT_DIR:-emu-out}"
APK="${APK_PATH:?APK_PATH not set}"
PKG="${PKG:?PKG not set}"
mkdir -p "$OUT"

adb wait-for-device
adb shell 'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 2; done'

# Device facts, the ABI list and native bridge show whether ARM translation exists.
: > "$OUT/device-props.txt"
for p in ro.build.version.release ro.build.version.sdk ro.build.fingerprint \
         ro.product.cpu.abi ro.product.cpu.abilist ro.product.cpu.abilist64 \
         ro.dalvik.vm.native.bridge ro.enable.native.bridge.exec ro.dalvik.vm.isa.arm64; do
  echo "$p=$(adb shell getprop "$p" | tr -d '\r')" >> "$OUT/device-props.txt"
done
cat "$OUT/device-props.txt"
ABILIST="$(adb shell getprop ro.product.cpu.abilist | tr -d '\r')"
if echo "$ABILIST" | grep -q 'arm64-v8a'; then ARM64_TRANSLATION=yes; else ARM64_TRANSLATION=no; fi

adb logcat -c || true

echo "== adb install -r $APK"
adb install -r "$APK" > "$OUT/adb-install.txt" 2>&1
INSTALL_RC=$?
cat "$OUT/adb-install.txt"
echo "exit code: $INSTALL_RC" >> "$OUT/adb-install.txt"
INSTALL_LINE="$(grep -E '^(Success|Failure|adb: failed|Performing)' "$OUT/adb-install.txt" | grep -v '^Performing' | head -n1)"
[ -z "$INSTALL_LINE" ] && INSTALL_LINE="$(grep -v '^exit code' "$OUT/adb-install.txt" | tail -n1)"
if grep -q '^Success' "$OUT/adb-install.txt"; then INSTALL_OK=yes; else INSTALL_OK=no; fi

adb shell pm list packages | tr -d '\r' | grep -F "$PKG" > "$OUT/pm-list.txt" || true
if grep -qx "package:$PKG" "$OUT/pm-list.txt"; then LISTED=yes; else LISTED=no; fi

LAUNCHED=no; ALIVE=no; PID=""
if [ "$INSTALL_OK" = yes ]; then
  adb shell dumpsys package "$PKG" | tr -d '\r' | grep -E 'versionCode|versionName|primaryCpuAbi|secondaryCpuAbi|targetSdk|minSdk' > "$OUT/dumpsys-package.txt" || true
  echo "== monkey -p $PKG 1"
  adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 > "$OUT/monkey.txt" 2>&1
  cat "$OUT/monkey.txt"
  if grep -q 'Events injected: 1' "$OUT/monkey.txt"; then LAUNCHED=yes; fi
  sleep 12
  PID="$(adb shell pidof "$PKG" | tr -d '\r')"
  [ -n "$PID" ] && ALIVE=yes
  adb shell dumpsys activity activities | tr -d '\r' | grep -E 'mResumedActivity|topResumedActivity|ResumedActivity' > "$OUT/resumed-activity.txt" || true
fi

adb shell screencap -p /sdcard/emu-screen.png && adb pull /sdcard/emu-screen.png "$OUT/screen.png" >/dev/null || true

adb logcat -d -v time > "$OUT/logcat-full.txt" 2>&1 || true
grep -E 'PackageManager|PackageInstaller|AndroidRuntime|flutter|FATAL|DEBUG +:|native.?bridge|ndk_translation|houdini|mesh_monitor|UnsatisfiedLinkError|INSTALL_' \
  "$OUT/logcat-full.txt" > "$OUT/logcat-filtered.txt" || true
grep -E 'FATAL EXCEPTION|UnsatisfiedLinkError|Fatal signal|ABI|native bridge|libflutter|libapp' "$OUT/logcat-filtered.txt" | head -n 40 > "$OUT/logcat-notable.txt" || true

{
  echo "API_LEVEL=$(adb shell getprop ro.build.version.sdk | tr -d '\r')"
  echo "ABILIST=$ABILIST"
  echo "ARM64_TRANSLATION=$ARM64_TRANSLATION"
  echo "INSTALL_OK=$INSTALL_OK"
  echo "INSTALL_RC=$INSTALL_RC"
  printf 'INSTALL_LINE=%q\n' "$INSTALL_LINE"
  echo "LISTED=$LISTED"
  echo "LAUNCHED=$LAUNCHED"
  echo "ALIVE=$ALIVE"
  echo "PID=$PID"
} > "$OUT/result.env"
cat "$OUT/result.env"
exit 0
