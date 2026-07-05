# exynos9611_gcam_patcher


problem statement

the pink tint issues on Exynos9611 when using gcam is HELLA annoying, and i find it easier to work with the gcam itself rather than patching the .so xd
due to the issues that were brought up from this repo issues https://github.com/TBM13/Samsung-Camera-Experiments/issues/23 and the goated guidance from TBM13 himself of ways to fix the pink tint. also thanks to betelqeyza for opening the thread! ofc patching the gcam itself is a MASSIVE workaround but ey better than nothing xd. elegantly one day having the .so be patched would be nice.. not my end goal tho

ofc compatibility is moreso directed towards samsung galaxy a51 since its what im working with but since its gcam and not .so, should be okay for all exynos9611 variant.
the module patch the AsShotNeutral to 1 1 1 on the raw itself so the gcam can process it properly. previously to "fix" the pink tint you can.. use the AWB on the gcam setting buttt that itself is ANOTHER MASSIVE WORKAROUND XD. the color is hella unbalanced, blue looks purple, dead purple. and ofc the color is hella washed out. with this module the pink tint fix worked flawlessly wihout awb. tbh that AsShotNetural 1 1 1 is the only thing thats needed to fix the god awful pink tint so thank you goated TBM13. the black level can be set in the gcam itself through Black Level settings in the camera lens setting. black level 193 from the mentioned issues/23 is okay for me. adjust yours if needed.

this module is SPECIFICALLY FOR SGCAM_8.5.300.XX.10_STABLE_V24_SCAN3D_PACKAGE.apk, do take a look at it on the download section for links, using w other gcam IS NOT GUARANTEED, most likely failed cuz.. its patching the dex directly anyway. and yes! i use ai for lots of the patching and the disecting of the gcam xd or else itd take never xd. also yeah the preview lagged. seems to be related to buffer stuff, something something about full resolution 4000x3000 raw stream filling up the 5 frame buffer. dunno whats up with that, aint takin a look at that for now. i'll post the detail if people want to take a look at it.. if im not lazy later xd , if you want to take a look and have a go on how to patch the gcam, do look in patches/smali/README.md



heres the offical doc not written by me but theyr cool xd

A KernelSU / Magisk module that hot-patches **SGCAM** (`com.samsung.android.scan3d`) — a Google Camera port repackaged to piggyback on Samsung's auxiliary-camera HAL — by bind-mounting an APK with patched `classes*.dex` files over the installed one.

Built for **Exynos 9611** devices (Samsung Galaxy A51 / A41 / M31 / M21 / F41 etc.) running Android 13+.

## What it does

- **No permanent modification** — bind-mounts a patched APK over the live `/data/app/.../base.apk`. The original APK stays untouched; uninstall is just an `umount` + dalvik-cache wipe.
- **Survives reboot** — `boot-completed.sh` re-establishes the mount every boot, with md5 verification to skip when already active.
- **Self-contained** — ships its own aarch64 `bspatch` (statically linked with libbz2) and `zip` so the device doesn't need busybox extras.
- **Hash-verified** — checks the installed SGCAM's DEX MD5s against `hashes.txt` before patching.

The patches themselves fix:

- Auto white balance (AWB)
- Black levels
- Some preview lag fixes

The patches themselves do not fix:

- CameraBuffer issue ( laggy preview )

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
   
   Download here https://www.celsoazevedo.com/files/android/google-camera/dev-shamim/f/dl79/
   'SGCAM_8.5.300.XX.10_STABLE_V24_SCAN3D_PACKAGE.apk'( credit to goated shamim )

3. Push `output/SGCAM_DEX_Patcher.zip` to your phone
4. Flash it via KernelSU Manager → Modules → Install from storage (or Magisk)
5. Reboot or force-stop SGCAM — the patches take effect on next launch

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
## Credits & References

This module stands on the shoulders of several community projects:

- **[TBM13/Samsung-Camera-Experiments](https://github.com/TBM13/Samsung-Camera-Experiments)** — Tool that patches Exynos camera libraries to enable features like RAW capture (required by GCam). The SGCAM mod this module patches is built on top of TBM13's camera library patches. Without TBM13's work, GCam/SGCam wouldn't run on Exynos 9611 at all.
- **[Issue #23 — Pink tint on Exynos 9611 (Galaxy M21)](https://github.com/TBM13/Samsung-Camera-Experiments/issues/23)** — Documents the infamous pink-tint problem on Exynos 9610/9611 devices, where the camera HAL outputs pre-processed DNGs with wrong `BlackLevel` and `AsShotNeutral` metadata. The discussion includes a manual ExifTool-based workaround (`BlackLevel = 3096 3096 3096 3096`, `AsShotNeutral = 1 1 1`) and a lib-side workaround (`Module_M21_NoPureBayerReprocessing.zip`). The patches shipped by this module address the related AWB / black-level symptoms at the SGCAM DEX layer.
- **[bsdiff 4.3](https://www.daemonology.net/bsdiff/)** — Colin Percival's binary diff/patch tool. The `bspatch.c` shipped in `tools/` is the unmodified upstream source.
- **[MMT Extended](https://github.com/Zackptg5/MMT-Extended)** — Zackptg5's Magisk Module Template Extended, the install framework used by `ModuleBase/customize.sh`.
- **[Shamim's SGCAM_8.5.300.XX.10_STABLE_V24](https://www.celsoazevedo.com/files/android/google-camera/dev-shamim/f/dl79/)** — The SGCAM port this module patches, by Shamim. SGCAM is a Google Camera repackaging that piggybacks on Samsung's `scan3d` package name to access the auxiliary-camera HAL. Hosted on [celsoazevedo.com](https://www.celsoazevedo.com/files/android/google-camera/), the canonical GCam port directory.

## License

- `tools/bspatch.c` — BSD-2-clause, Copyright Colin Percival (2003-2005), from [bsdiff 4.3](https://www.daemonology.net/bsdiff/)
- `ModuleBase/common/functions.sh` — MMT Extended framework by Zackptg5 @ XDA
- Everything else — GPL-2.0 (see `ModuleBase/LICENSE`)
