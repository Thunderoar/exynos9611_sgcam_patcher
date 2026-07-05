#!/usr/bin/env python3
"""
Build script for SGCAM DEX Patcher KernelSU module.

Auto-downloads/compiles dependencies if missing:
  - bspatch: cross-compiled from bspatch.c (needs aarch64-linux-gnu-gcc)
  - zip: downloaded from Termux aarch64 package repo

Usage:
  python3 build_module.py
"""

import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MODULE_BASE = os.path.join(ROOT, 'ModuleBase')
TOOLS_DIR = os.path.join(ROOT, 'tools')
PATCHES_DIR = os.path.join(ROOT, 'patches')
OUTPUT_DIR = os.path.join(ROOT, 'output')

# Expected hashes for downloaded binaries (safety check)
ZIP_URL = "https://packages.termux.dev/apt/termux-main/pool/main/z/zip/zip_3.0-7_aarch64.deb"
ZIP_EXPECTED_SHA = "a0e32027146d73bf2ac385eacc8a98ce49481b5c481b3e1cce5d5cd33cc0be05"  # optional


def ensure_bspatch():
    """Compile bspatch from source if binary doesn't exist."""
    bspatch_bin = os.path.join(TOOLS_DIR, 'bspatch')
    if os.path.exists(bspatch_bin) and os.path.getsize(bspatch_bin) > 10000:
        print(f"    [*] bspatch binary already exists, skipping compilation")
        return
    
    print(f"    [*] Compiling bspatch for aarch64...")
    bspatch_src = os.path.join(TOOLS_DIR, 'bspatch.c')
    
    # Check for cross-compiler
    cc = shutil.which('aarch64-linux-gnu-gcc')
    if not cc:
        print(f"    [!] ERROR: aarch64-linux-gnu-gcc not found. Cannot compile bspatch.")
        print(f"    [!] Install it or place a pre-built bspatch binary at {bspatch_bin}")
        sys.exit(1)
    
    # Check if bzlib is available - we ship it pre-compiled as libbz2.a + bzlib.h
    bzlib_path = os.path.join(TOOLS_DIR, 'libbz2.a')
    bzlib_header = os.path.join(TOOLS_DIR, 'bzlib.h')
    if not os.path.exists(bzlib_path) or not os.path.exists(bzlib_header):
        print(f"    [!] ERROR: libbz2.a or bzlib.h not found in tools/")
    
    # Compile bspatch
    cmd = [
        'aarch64-linux-gnu-gcc', '-static', '-o', bspatch_bin,
        bspatch_src,
        '-I', os.path.join(TOOLS_DIR),
        bzlib_path
    ]
    subprocess.run(cmd, check=True)
    
    # Strip
    strip_cmd = shutil.which('aarch64-linux-gnu-strip')
    if strip_cmd:
        subprocess.run([strip_cmd, bspatch_bin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    size = os.path.getsize(bspatch_bin)
    print(f"    [*] bspatch compiled: {size:,} bytes")


def ensure_zip():
    """Download zip binary from Termux if not present."""
    zip_bin = os.path.join(TOOLS_DIR, 'zip')
    if os.path.exists(zip_bin) and os.path.getsize(zip_bin) > 10000:
        print(f"    [*] zip binary already exists, skipping download")
        return
    
    print(f"    [*] Downloading zip binary from Termux...")
    deb_path = os.path.join(TOOLS_DIR, 'zip_aarch64.deb')
    
    try:
        urllib.request.urlretrieve(ZIP_URL, deb_path)
    except Exception as e:
        print(f"    [!] Failed to download zip: {e}")
        print(f"    [!] Place a pre-built Android aarch64 zip binary at {zip_bin}")
        sys.exit(1)
    
    # Extract the zip binary from the .deb
    extract_dir = os.path.join(TOOLS_DIR, 'zip_extract')
    os.makedirs(extract_dir, exist_ok=True)
    
    # .deb is ar archive containing tar.xz
    subprocess.run(['ar', 'x', deb_path], cwd=extract_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    data_tar = os.path.join(extract_dir, 'data.tar.xz')
    if os.path.exists(data_tar):
        subprocess.run(['tar', 'xJf', data_tar], cwd=extract_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Find the zip binary
    zip_extracted = None
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f == 'zip':
                zip_extracted = os.path.join(root, f)
                break
    
    if not zip_extracted:
        print(f"    [!] Could not find zip binary in extracted Termux package")
        sys.exit(1)
    
    shutil.copy(zip_extracted, zip_bin)
    os.chmod(zip_bin, 0o755)
    shutil.rmtree(extract_dir)
    os.remove(deb_path)
    
    size = os.path.getsize(zip_bin)
    print(f"    [*] zip downloaded: {size:,} bytes")


def main():
    print("[*] Building SGCAM DEX Patcher module...")
    print()
    
    # Step 1: Ensure tool binaries exist
    print("  [*] Checking dependencies...")
    ensure_bspatch()
    ensure_zip()
    print()
    
    # Step 2: Verify all required files exist
    required = [
        (TOOLS_DIR, 'bspatch'),
        (TOOLS_DIR, 'zip'),
        (PATCHES_DIR, 'hashes.txt'),
        (PATCHES_DIR, 'classes.patch.bsdf'),
        (PATCHES_DIR, 'classes2.patch.bsdf'),
        (PATCHES_DIR, 'classes3.patch.bsdf'),
    ]
    
    all_ok = True
    for dirpath, filename in required:
        path = os.path.join(dirpath, filename)
        if not os.path.exists(path):
            print(f"    [!] ERROR: Required file not found: {path}")
            all_ok = False
        else:
            size = os.path.getsize(path)
            print(f"    [*] {filename} ({size:,} bytes)")
    
    if not all_ok:
        sys.exit(1)
    
    print()
    
    # Step 3: Create temp build directory
    tmp_dir = MODULE_BASE + 'Temp'
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir)
    shutil.copytree(MODULE_BASE, tmp_dir)
    
    # Create required directories in build
    os.makedirs(os.path.join(tmp_dir, 'system/bin'), exist_ok=True)
    os.makedirs(os.path.join(tmp_dir, 'system/etc/sgcam-patches'), exist_ok=True)
    
    # Copy binaries
    shutil.copy(os.path.join(TOOLS_DIR, 'bspatch'), os.path.join(tmp_dir, 'system/bin/bspatch'))
    shutil.copy(os.path.join(TOOLS_DIR, 'zip'), os.path.join(tmp_dir, 'system/bin/zip'))
    
    # Copy patches
    shutil.copy(os.path.join(PATCHES_DIR, 'hashes.txt'), os.path.join(tmp_dir, 'system/etc/sgcam-patches/hashes.txt'))
    shutil.copy(os.path.join(PATCHES_DIR, 'classes.patch.bsdf'), os.path.join(tmp_dir, 'system/etc/sgcam-patches/classes.patch.bsdf'))
    shutil.copy(os.path.join(PATCHES_DIR, 'classes2.patch.bsdf'), os.path.join(tmp_dir, 'system/etc/sgcam-patches/classes2.patch.bsdf'))
    shutil.copy(os.path.join(PATCHES_DIR, 'classes3.patch.bsdf'), os.path.join(tmp_dir, 'system/etc/sgcam-patches/classes3.patch.bsdf'))
    
    # Set permissions
    os.chmod(os.path.join(tmp_dir, 'system/bin/bspatch'), 0o755)
    os.chmod(os.path.join(tmp_dir, 'system/bin/zip'), 0o755)
    
    # Step 4: Create module zip
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    zip_path = os.path.join(OUTPUT_DIR, 'SGCAM_DEX_Patcher.zip')
    
    print("  [*] Packaging module...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(tmp_dir):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                arcname = os.path.relpath(file_path, tmp_dir)
                zf.write(file_path, arcname)
    
    # Clean up
    shutil.rmtree(tmp_dir)
    
    print()
    print(f"  [*] Module built: {zip_path}")
    print(f"      Size: {os.path.getsize(zip_path):,} bytes")
    print()
    print("=" * 60)
    print("Install via KernelSU Manager or Magisk:")
    print("  1. Push the zip to your device")
    print("  2. Install in KernelSU Manager / Magisk")
    print("  3. Ensure SGCAM is installed BEFORE module")
    print("  4. Reboot or force-stop SGCAM after install")
    print("=" * 60)


if __name__ == '__main__':
    main()
