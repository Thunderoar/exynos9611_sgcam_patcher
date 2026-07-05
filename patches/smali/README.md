# SGCAM Smali Source Patches

Source-level smali patches that produce the modified DEX files used by the SGCAM DEX Patcher KernelSU module.

These patches are `git format-patch` files containing only **diffs** — they do not include any decompiled SGCAM source code. To use them, you decompile your own copy of the SGCAM APK, apply the patches with `git am`, and recompile. The binary `*.patch.bsdf` files in the parent directory are derived from these via: `apktool d → git am → apktool b → bsdiff`.

## Why patches only?

The SGCAM APK is a derivative of Google Camera, repackaged to piggyback on Samsung's `scan3d` package. Distributing the decompiled smali source would be legally murky, so this repo ships only the diffs — you bring your own APK, apply the patches, and rebuild. This is the same model Linux distros use for patented codecs and other grey-area code.

## Patch inventory

| # | File | Summary |
|---|------|---------|
| 1 | `0001-docs-add-AGENTS.md-...patch` | Docs: AGENTS.md modification analysis |
| 2 | `0002-perf-replace-acquireNextImage-...patch` | Image reader: acquireLatestImage + null guard |
| 3 | `0003-chore-reduce-photosphere-...patch` | Photosphere: Medium resolution output |
| 4 | `0004-fix-move-RAW-DNG-processing-...patch` | RAW/DNG moved off UI thread (fixes ANR) |
| 5 | `0005-docs-add-comment-noting-dead-FPS-...patch` | Docs: dead FPS fix removed from TEMPLATE_PREVIEW |
| 6 | `0006-fix-add-Exynos-specific-guard-...patch` | Exynos: bypass AWB gain fill, null ColorSpaceTransform |
| 7 | `0007-perf-cache-SharedPreferences-...patch` | Cache SharedPreferences in static field |
| 8 | `0008-fix-Exynos-AWB-override-...patch` | Exynos: unity AWB gains, configurable black levels, preview lag fix v2 |

## Prerequisites

To use these patches, you'll need:

- **The original SGCAM APK** — download [Shamim's SGCAM_8.5.300.XX.10_STABLE_V24](https://www.celsoazevedo.com/files/android/google-camera/dev-shamim/f/dl79/) from celsoazevedo.com
- **apktool** 2.11.0+ — for decompiling and recompiling the APK
- **bsdiff** — for generating the binary patches (`apt install bsdiff` / `pacman -S bsdiff`)
- **git** — for applying the smali patches via `git am`
- **zip / unzip / md5sum** — for extracting DEX files and computing hashes

## Workflow

### Option A: Use the automated regen script

```bash
# From the repo root:
./patches/regenerate_bsdf_patches.sh /path/to/SGCAM_8.5.300.XX.10_STABLE_V24_SCAN3D_PACKAGE.apk
```

The script will:
1. Decompile your SGCAM APK with apktool
2. Initialize a git repo in the decompiled tree
3. Apply each smali patch in order via `git am`
4. Recompile with apktool
5. Extract DEX files from both original and patched APKs
6. Run `bsdiff` to produce `patches/*.patch.bsdf`
7. Update `patches/hashes.txt` with the MD5 of your original DEX files

### Option B: Manual workflow

If you want to understand what's happening or need to debug a failed patch:

```bash
# 1. Decompile your SGCAM APK
apktool d -o sgcam_orig SGCAM_8.5.300.XX.10_STABLE_V24_SCAN3D_PACKAGE.apk
cp -r sgcam_orig sgcam_patched

# 2. Init git and apply patches
cd sgcam_patched
git init
git add -A
git -c user.email=you@local -c user.name=you commit -m "initial decompile"

# Apply patches in order
for p in /path/to/sgcam_ksu_module/patches/smali/*.patch; do
  git am --3way "$p"
done

# 3. Recompile
apktool b -o sgcam_patched.apk .

# 4. Generate bsdiff patches from the DEX files
mkdir -p dex_orig dex_patched
(cd dex_orig   && unzip -qjo ../sgcam_orig/SGCAM_*.apk         "classes.dex" "classes2.dex" "classes3.dex")
(cd dex_patched && unzip -qjo ../sgcam_patched/sgcam_patched.apk "classes.dex" "classes2.dex" "classes3.dex")

for dex in classes classes2 classes3; do
  bsdiff dex_orig/${dex}.dex dex_patched/${dex}.dex ${dex}.patch.bsdf
done

# 5. Update hashes
(cd dex_orig && md5sum classes.dex classes2.dex classes3.dex) > hashes.txt
```

## Inspecting a patch without applying it

To see what a patch changes without committing it:

```bash
# Just read the patch
less /path/to/sgcam_ksu_module/patches/smali/0006-fix-add-Exynos-specific-guard-for-AWB-gains-and-Colo.patch

# Or apply it as a working-tree change (no commit) to inspect the result
cd /path/to/your/decompiled/sgcam
git apply --check /path/to/sgcam_ksu_module/patches/smali/0006-*.patch   # dry-run
git apply         /path/to/sgcam_ksu_module/patches/smali/0006-*.patch   # actually apply
git diff                                                               # see the changes
```

## What if a patch doesn't apply cleanly?

If `git am` fails with a conflict, it usually means one of:

1. **Wrong SGCAM version** — these patches target `SGCAM_8.5.300.XX.10_STABLE_V24`. If you're on a different version, the line numbers and surrounding context may differ. Check `patches/hashes.txt` for the expected MD5 of the original DEX files.
2. **apktool version mismatch** — different apktool versions produce slightly different smali formatting. We use apktool 2.11.0. If you're on an older version, upgrade: `pip install apktool` or download from [ibotpeaches.github.io/Apktool](https://ibotpeaches.github.io/Apktool/).
3. **Patches applied out of order** — `git am` applies them in filename order (0001 → 0008). Don't reorder them.

To recover from a failed `git am`:

```bash
git am --abort                    # Cancel the failed apply
git am --3way --interactive <patch>   # Try with 3-way merge
# Or, if you want to manually resolve:
git am --abort
git apply --reject <patch>        # Creates .rej files for failed hunks
# Edit the files to apply the rejected hunks manually, then:
git add -A
git am --continue
```

## See also

- `../README.md` — top-level repo README
- `../PATCH_NOTES.md` — release changelog
- [Shamim's SGCAM_8.5.300.XX.10_STABLE_V24](https://www.celsoazevedo.com/files/android/google-camera/dev-shamim/f/dl79/) — download the SGCAM APK here
- [TBM13/Samsung-Camera-Experiments](https://github.com/TBM13/Samsung-Camera-Experiments) — Exynos camera library patches (required for GCam to function on Exynos 9611)
