# exynos9611_gcam_patcher

A KernelSU / Magisk module that hot-patches **SGCAM** (`com.samsung.android.scan3d`) — a Google Camera port repackaged to piggyback on Samsung's auxiliary-camera HAL — by bind-mounting an APK with patched `classes*.dex` files over the installed one.

Built for **Exynos 9611** devices (Samsung Galaxy A51 / A41 / M31 / M21 / F41 etc.) running Android 13+.

## What it does

- **No permanent modification** — bind-mounts a patched APK over the live `/data/app/.../base.apk`. The original APK stays untouched; uninstall is just an `umount` + dalvik-cache wipe.
- **Survives reboot** — `boot-completed.sh` re-establishes the mount every boot, with md5 verification to skip when already active.
- **Self-contained** — ships its own aarch64 `bspatch` (statically linked with libbz2) and `zip` so the device doesn't need busybox extras.
- **Hash-verified** — checks the installed SGCAM's DEX MD5s against `hashes.txt` before patching.

The patches themselves fix:

- Preview lag
- Auto white balance (AWB)
- Black levels
- General camera performance

## Repository layout

```
sgcam_ksu_module/
├── build_module.py                # packager (Python 3)
├── ModuleBase/                    # what gets zipped into the flashable module
│   ├── module.prop                # id, version, min API 33
│   ├── customize.sh               # install-time patcher
│   ├── boot-completed.sh          # re-establishes bind mount every boot
│   ├── uninstall.sh               # umount + dalvik-cache wipe
│   ├── common/functions.sh        # MMT Extended framework (Zackptg5 @ XDA)
│   └── META-INF/com/google/android/{update-binary, updater-script}
├── patches/
│   ├── hashes.txt                 # MD5 of expected original classes*.dex
│   ├── classes.patch.bsdf         # BSDIFF40 — applied to classes.dex
│   ├── classes2.patch.bsdf        # BSDIFF40 — applied to classes2.dex
│   ├── classes3.patch.bsdf        # BSDIFF40 — applied to classes3.dex
│   └── original/patched_classes*.dex (gitignored, for local verification)
├── tools/
│   ├── bspatch                    # aarch64 binary (compiled by build_module.py)
│   ├── bspatch.c                  # canonical bsdiff-4.3 source
│   ├── bzlib.h + libbz2.a         # bzip2 1.0.8 (statically linked in)
│   ├── smali.jar                  # smali/baksmali for DEX surgery
│   └── zip                        # aarch64 zip, pulled from Termux deb
└── output/
    └── SGCAM_DEX_Patcher.zip      # final flashable module (gitignored)
```

## Build

Requires Python 3 and the Android NDK (r25+) with `aarch64-linux-android33-clang` on PATH, or `aarch64-linux-gnu-gcc` as a fallback.

```bash
python3 build_module.py
```

The script will:

1. Cross-compile `bspatch` from `tools/bspatch.c` against the bundled `libbz2.a` (static, stripped)
2. Download `zip` from the Termux aarch64 package repo if not already present
3. Package `ModuleBase/` + binaries + patches into `output/SGCAM_DEX_Patcher.zip`

## Install

1. Ensure SGCAM (`com.samsung.android.scan3d`) is already installed on the device
2. Push `output/SGCAM_DEX_Patcher.zip` to your phone
3. Flash it via KernelSU Manager → Modules → Install from storage (or Magisk)
4. Reboot or force-stop SGCAM — the patches take effect on next launch

To verify the bind mount is active:

```bash
adb shell logcat -d -s SGCAM_Patcher
# Should see: "Bind mount established: ... -> /data/app/.../base.apk"
```

## Uninstall

Disable or remove the module in KernelSU Manager. The `uninstall.sh` will `umount` the bind mount and wipe dalvik-cache; on next launch the camera reverts to the original APK.

## How the patches were generated

The `patches/*.bsdf` files are BSDIFF40-format patches produced by `bsdiff` from `original_classes*.dex` → `patched_classes*.dex`. They are applied at install time (and re-applied at every boot if the bind mount is lost) by the shipped `bspatch` binary.

To regenerate patches after a DEX change:

```bash
bsdiff original_classes.dex patched_classes.dex classes.patch.bsdf
md5sum original_classes.dex >> hashes.txt   # only the original's hash matters
```

## License

- `tools/bspatch.c` — BSD-2-clause, Copyright Colin Percival (2003-2005), from [bsdiff 4.3](https://www.daemonology.net/bsdiff/)
- `ModuleBase/common/functions.sh` — MMT Extended framework by Zackptg5 @ XDA
- Everything else — GPL-2.0 (see `ModuleBase/LICENSE`)
