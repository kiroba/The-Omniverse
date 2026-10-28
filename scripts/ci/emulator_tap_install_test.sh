#!/usr/bin/env bash
# Runs inside reactivecircus/android-emulator-runner once the emulator has booted.
# For every APK in $APK_DIR (files named <slug>.apk) it tries four install paths and
# records exactly what happened:
#   A  adb install --no-streaming -r
#   B  session install: adb exec-in pm install -S <size> < apk
#   C  tap-to-install: APK pushed to /sdcard/Download, opened from its MediaStore
#      content:// URI with ACTION_VIEW (what Files / a browser download does), the
#      PackageInstaller dialog captured (screencap + uiautomator text) and its Install
#      button tapped
#   D  same as C but with a file:// URI
# Logcat for each path is kept so the exception behind "problem parsing the package"
# (if any) is visible. Always exits 0; verdicts are in $OUT_DIR/results.tsv.
set -u
OUT="${OUT_DIR:-emu-out}"
APK_DIR="${APK_DIR:?APK_DIR not set}"
mkdir -p "$OUT"

adb wait-for-device
adb shell 'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 2; done'
sleep 5
adb shell input keyevent 82 >/dev/null 2>&1 || true   # dismiss keyguard
adb shell wm dismiss-keyguard >/dev/null 2>&1 || true
adb shell settings put global package_verifier_user_consent -1 >/dev/null 2>&1 || true

: > "$OUT/device-props.txt"
for p in ro.build.version.release ro.build.version.sdk ro.build.fingerprint \
         ro.product.cpu.abilist ro.dalvik.vm.native.bridge; do
  echo "$p=$(adb shell getprop "$p" | tr -d '\r')" >> "$OUT/device-props.txt"
done
{
  echo "== installers that handle ACTION_VIEW application/vnd.android.package-archive"
  adb shell cmd package query-activities -a android.intent.action.VIEW \
      -t application/vnd.android.package-archive -d content://x/y.apk 2>&1 | tr -d '\r' | grep -E 'packageName|name=' | head -n 10
  for ip in com.google.android.packageinstaller com.android.packageinstaller; do
    v="$(adb shell dumpsys package "$ip" 2>/dev/null | tr -d '\r' | grep -m1 versionName)"
    [ -n "$v" ] && echo "$ip $v"
  done
} >> "$OUT/device-props.txt" 2>&1
cat "$OUT/device-props.txt"

# Let the shell (the "source" app for am start) install unknown apps, so the dialog
# that appears is the install / parse dialog and not the unknown-sources gate.
adb shell appops set com.android.shell REQUEST_INSTALL_PACKAGES allow 2>&1 | tee "$OUT/appops.txt"
adb shell appops get com.android.shell REQUEST_INSTALL_PACKAGES 2>&1 | tr -d '\r' | tee -a "$OUT/appops.txt"

printf 'apk\tpath\tresult\tdetail\n' > "$OUT/results.tsv"
rec() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$(echo "$4" | tr '\t\n\r' '   ' | cut -c1-300)" >> "$OUT/results.tsv"; }

installed() { adb shell pm list packages | tr -d '\r' | grep -qx "package:$1"; }
uninstall() { adb shell pm uninstall "$1" >/dev/null 2>&1 || true; sleep 1; }

grab_log() { # $1 = output file
  adb logcat -d -v time > "$1.full.txt" 2>&1 || true
  grep -E 'PackageInstaller|InstallStart|InstallStaging|InstallRepository|PackageParser|ParsingPackageUtils|PackageManager|PackageUtil|ApkLite|ApkSignature|InstallInstalling|InstallSuccess|InstallFailed|INSTALL_|problem parsing|Exception|at android\.|at com\.android' \
    "$1.full.txt" > "$1" || true
}

ui_text() { # $1 = prefix; writes $1.png, $1.xml, $1.txt; prints the texts on one line
  adb shell screencap -p /sdcard/s.png >/dev/null 2>&1 && adb pull /sdcard/s.png "$1.png" >/dev/null 2>&1
  adb shell rm -f /sdcard/ui.xml >/dev/null 2>&1
  adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1 || { sleep 2; adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1; }
  adb pull /sdcard/ui.xml "$1.xml" >/dev/null 2>&1 || true
  if [ -s "$1.xml" ]; then
    python3 - "$1.xml" > "$1.txt" <<'PY'
import sys, re, xml.etree.ElementTree as ET
try:
    root = ET.parse(sys.argv[1]).getroot()
except Exception as e:
    print("(uiautomator xml unreadable: %s)" % e); sys.exit()
for n in root.iter("node"):
    t = (n.get("text") or "").strip()
    if t:
        print("%s | %s | %s | %s" % (t, n.get("resource-id", ""), n.get("package", ""), n.get("bounds", "")))
PY
  else
    echo "(no uiautomator dump)" > "$1.txt"
  fi
  cut -d'|' -f1 "$1.txt" | sed 's/ *$//' | paste -sd ';' -
}

tap_button() { # $1 = xml, $2.. = labels; taps the first matching enabled node; returns 1 if none
  local xml="$1"; shift
  local xy
  xy="$(python3 - "$xml" "$@" <<'PY'
import sys, re, xml.etree.ElementTree as ET
xml, labels = sys.argv[1], [l.lower() for l in sys.argv[2:]]
try:
    root = ET.parse(xml).getroot()
except Exception:
    sys.exit()
for want in labels:
    for n in root.iter("node"):
        t = (n.get("text") or "").strip().lower()
        if t == want and n.get("enabled", "true") == "true":
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.get("bounds", ""))
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                print((x1 + x2) // 2, (y1 + y2) // 2); sys.exit()
PY
)"
  [ -z "$xy" ] && return 1
  adb shell input tap $xy
  return 0
}

view_install() { # $1 slug, $2 pkg, $3 path label, $4 uri
  local slug="$1" pkg="$2" label="$3" uri="$4" p="$OUT/$1-$3"
  uninstall "$pkg"
  adb shell input keyevent 3 >/dev/null 2>&1   # home, clear any previous dialog
  adb logcat -c || true
  echo "== [$slug] $label: am start VIEW $uri"
  adb shell am start -W -a android.intent.action.VIEW -t application/vnd.android.package-archive \
      -d "$uri" --grant-read-uri-permission > "$p-am-start.txt" 2>&1
  cat "$p-am-start.txt"
  sleep 10
  local d1; d1="$(ui_text "$p-dialog1")"
  echo "dialog1: $d1"
  local result detail="dialog1: $d1"
  if echo "$d1" | grep -qi 'problem parsing'; then
    result="PARSE_ERROR"
  elif tap_button "$p-dialog1.xml" "Install" "Update" "Reinstall"; then
    # wait for install to finish
    for i in $(seq 1 30); do sleep 2; installed "$pkg" && break; done
    sleep 3
    local d2; d2="$(ui_text "$p-dialog2")"
    echo "dialog2: $d2"
    detail="$detail || after tapping Install: $d2"
    if installed "$pkg"; then result="INSTALLED"
    elif echo "$d2" | grep -qi 'problem parsing'; then result="PARSE_ERROR_AFTER_TAP"
    else result="NOT_INSTALLED"; fi
  else
    if installed "$pkg"; then result="INSTALLED_NO_TAP"; else result="NO_INSTALL_BUTTON"; fi
  fi
  grab_log "$p-logcat.txt"
  local exc; exc="$(grep -m3 -E 'Exception|INSTALL_|Failed to parse|problem parsing' "$p-logcat.txt" | sed 's/^.\{0,30\}//' | paste -sd ' ' -)"
  [ -n "$exc" ] && detail="$detail || logcat: $exc"
  echo "[$slug] $label => $result"
  rec "$slug" "$label" "$result" "$detail"
}

for APK in "$APK_DIR"/*.apk; do
  slug="$(basename "$APK" .apk)"
  pkg="$(cat "$APK_DIR/$slug.pkg" 2>/dev/null)"
  size="$(stat -c %s "$APK")"
  echo "################ $slug ($pkg, $size bytes)"
  [ -z "$pkg" ] && { rec "$slug" "-" "SKIPPED" "package name unknown"; continue; }

  # A: adb install --no-streaming
  uninstall "$pkg"; adb logcat -c || true
  adb install --no-streaming -r "$APK" > "$OUT/$slug-A-adb-nostream.txt" 2>&1
  line="$(grep -E 'Success|Failure|failed' "$OUT/$slug-A-adb-nostream.txt" | head -n1)"
  installed "$pkg" && r=INSTALLED || r=FAILED
  grab_log "$OUT/$slug-A-logcat.txt"
  rec "$slug" "A adb install --no-streaming" "$r" "$line"

  # B: session install from stdin
  uninstall "$pkg"; adb logcat -c || true
  adb exec-in pm install -r -S "$size" < "$APK" > "$OUT/$slug-B-pm-session.txt" 2>&1
  line="$(grep -E 'Success|Failure|failed|Error' "$OUT/$slug-B-pm-session.txt" | head -n1)"
  installed "$pkg" && r=INSTALLED || r=FAILED
  grab_log "$OUT/$slug-B-logcat.txt"
  rec "$slug" "B pm install -S (session, stdin)" "$r" "$line"

  # C: tap path via MediaStore content:// URI
  name="$slug-android-arm64.apk"
  adb shell rm -f "/sdcard/Download/$name" >/dev/null 2>&1
  adb push "$APK" "/sdcard/Download/$name" > "$OUT/$slug-push.txt" 2>&1
  adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file:///sdcard/Download/$name" >/dev/null 2>&1 || true
  id=""
  for i in $(seq 1 15); do
    adb shell content query --uri content://media/external/downloads --projection _id:_display_name:mime_type:_size:owner_package_name \
        2>/dev/null | tr -d '\r' > "$OUT/$slug-mediastore.txt"
    id="$(grep -F "_display_name=$name," "$OUT/$slug-mediastore.txt" | sed -n 's/.*_id=\([0-9]*\),.*/\1/p' | tail -n1)"
    [ -n "$id" ] && break
    sleep 2
  done
  if [ -n "$id" ]; then
    grep -F "_display_name=$name," "$OUT/$slug-mediastore.txt"
    view_install "$slug" "$pkg" "C-content-uri" "content://media/external/downloads/$id"
  else
    rec "$slug" "C-content-uri" "NO_MEDIASTORE_ROW" "$(head -c 300 "$OUT/$slug-mediastore.txt")"
  fi

  # D: tap path via file:// URI
  view_install "$slug" "$pkg" "D-file-uri" "file:///sdcard/Download/$name"

  adb shell input keyevent 3 >/dev/null 2>&1
done

echo; echo "======== results"; column -t -s $'\t' "$OUT/results.tsv" || cat "$OUT/results.tsv"
exit 0
