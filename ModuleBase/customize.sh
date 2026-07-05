##########################################################################################
#
# SGCAM DEX Patcher - MMT Extended Config Script
#
##########################################################################################

SKIPUNZIP=1

##########################################################################################
# Config Flags  (MUST be set before sourcing functions.sh)
##########################################################################################

REPLACE="
"

# Minimum Android 13 (API 33)
MINAPI=33

##########################################################################################
# Permissions  (MUST be defined before sourcing functions.sh — MMT calls it inline)
##########################################################################################

set_permissions() {
  set_perm_recursive $MODPATH/system/bin 0 0 0755 0755
  set_perm_recursive $MODPATH/system/etc/sgcam-patches 0 0 0644 0644
}

##########################################################################################
# Source MMT framework (runs install logic, including set_permissions at the end)
##########################################################################################

unzip -qjo "$ZIPFILE" 'common/functions.sh' -d $TMPDIR >&2
. $TMPDIR/functions.sh

##########################################################################################
# Installation
##########################################################################################

ui_print ""
ui_print "  SGCAM DEX Patcher v1"
ui_print "  ===================="
ui_print ""

# Find installed SGCAM
SGCAM_PKG="com.samsung.android.scan3d"
APK=$(pm path $SGCAM_PKG 2>/dev/null | grep base | head -1 | cut -d: -f2)

if [ -z "$APK" ]; then
  ui_print "  [WARN] SGCAM ($SGCAM_PKG) is not installed!"
  ui_print "  Module installed but will patch at boot when SGCAM is detected."
  touch $MODPATH/skip_mount
  exit 0
fi

ui_print "  Found SGCAM at: $APK"
ui_print ""

# Extract DEX
ui_print "  [*] Extracting DEX files from installed APK..."
cd /data/local/tmp
rm -f classes.dex classes2.dex classes3.dex 2>/dev/null
unzip -o "$APK" classes.dex classes2.dex classes3.dex 2>/dev/null
if [ ! -f classes.dex ]; then
  abort "  [!] Failed to extract DEX files from APK!"
fi

# Verify DEX hashes
ui_print "  [*] Verifying DEX integrity..."
HASHES_FILE="$MODPATH/system/etc/sgcam-patches/hashes.txt"
EXPECTED_HASHES=$(cat "$HASHES_FILE")
ACTUAL_HASHES=$(md5sum classes.dex classes2.dex classes3.dex 2>/dev/null)

if [ "$EXPECTED_HASHES" != "$ACTUAL_HASHES" ]; then
  ui_print "  [WARN] DEX hashes do not match the expected version!"
  ui_print "  Expected:"
  echo "$EXPECTED_HASHES" | while read line; do ui_print "    $line"; done
  ui_print "  Actual:"
  echo "$ACTUAL_HASHES" | while read line; do ui_print "    $line"; done
  ui_print ""
  ui_print "  Patches may not apply correctly. Attempting anyway..."
fi

# Apply bspatch for each DEX
BSPATCH="$MODPATH/system/bin/bspatch"
PATCH_DIR="$MODPATH/system/etc/sgcam-patches"
chmod 0755 "$BSPATCH"

for dex in classes classes2 classes3; do
  ui_print "  [*] Patching ${dex}.dex..."
  "$BSPATCH" "${dex}.dex" "${dex}_patched.dex" "$PATCH_DIR/${dex}.patch.bsdf" 2>&1
  if [ $? -ne 0 ]; then
    abort "  [!] bspatch failed for ${dex}.dex!"
  fi
  # Verify DEX header (should start with "dex\n" magic bytes)
  HEADER=$(head -c 4 "${dex}_patched.dex" 2>/dev/null)
  if [ "$HEADER" != "$(printf 'dex\n')" ]; then
    abort "  [!] Patched ${dex}.dex has invalid header! Corrupted patch?"
  fi
  mv "${dex}_patched.dex" "${dex}.dex"
done

# Create modified APK with patched DEX files
ui_print "  [*] Creating patched APK..."
cp "$APK" "$MODPATH/base_patched.apk"
ZIP="$MODPATH/system/bin/zip"
chmod 0755 "$ZIP"
cd /data/local/tmp
"$ZIP" -f -0 "$MODPATH/base_patched.apk" classes.dex classes2.dex classes3.dex 2>&1
if [ $? -ne 0 ]; then
  abort "  [!] Failed to update DEX files in patched APK!"
fi

# Verify the patched APK is valid
# Use the exit code of `unzip -t` directly — Toybox unzip (Android 16/SDK 36)
# does NOT emit InfoZIP's "No errors detected in ..." footer, so grepping for
# "No errors" produces false failures. The exit code is reliable across
# Toybox, BusyBox, and InfoZIP.
ui_print "  [*] Verifying patched APK integrity..."
UNZIP_TEST_OUTPUT=$(unzip -t "$MODPATH/base_patched.apk" 2>&1)
UNZIP_TEST_EXIT=$?
if [ $UNZIP_TEST_EXIT -ne 0 ]; then
  ui_print "  [!] unzip -t failed (exit $UNZIP_TEST_EXIT). Last 10 lines:"
  echo "$UNZIP_TEST_OUTPUT" | tail -10 | while read line; do ui_print "    $line"; done
  abort "  [!] Patched APK is corrupted!"
fi
ui_print "  [*] APK integrity OK"

# Set SELinux context
chcon u:object_r:apk_data_file:s0 "$MODPATH/base_patched.apk" 2>/dev/null || true

# Clear compiled cache
ui_print "  [*] Clearing dalvik-cache for SGCAM..."
rm -rf /data/app/*/com.samsung.android.scan3d*/oat/ 2>/dev/null
rm -f /data/dalvik-cache/arm64/*scan3d* 2>/dev/null
rm -f /data/dalvik-cache/arm64/*camera2* 2>/dev/null

# Bind mount the patched APK
ui_print "  [*] Bind mounting patched APK over original..."
NS=""
command -v nsenter >/dev/null 2>&1 && NS="nsenter -t 1 -m --"
$NS mount -o bind "$MODPATH/base_patched.apk" "$APK" 2>&1
if [ $? -ne 0 ]; then
  ui_print "  [!] Bind mount failed! Will retry at boot."
else
  ui_print "  [*] Bind mount successful"
fi

# Force-stop camera
ui_print "  [*] Restarting camera app..."
am force-stop $SGCAM_PKG 2>/dev/null

ui_print ""
ui_print "  [*] SGCAM DEX Patcher installed successfully!"
ui_print "  Open SGCAM to verify patches are applied."
ui_print ""
