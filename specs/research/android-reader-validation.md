# Android reader validation

Executed 2026-10-07 on an isolated Android 14 / API 34 ARM64 emulator on macOS. This is an installed reader UI test, beyond the earlier schema/parser probes.

## Result

Embedded ACBF panel metadata in CBZ **does drive real Android panel navigation**. The official **v2.0 release asset**, installed into a second fresh Android 14 AVD with untouched app configuration, imported the control archive and followed the deliberately non-geometric sequence **3 → 1 → 4 → 2**. Previous navigation returned from 1 to 3, the cover appeared once, and the final frame advanced to a readable full-page fallback. This stock release provides an end-to-end proof without a configuration workaround.

**Release qualification matters:** the untouched 2.1 APK crashed on first launch in a fresh installation. Its source reads the `general.use_temp_dir` option but no longer supplies that default. Adding only `use_temp_dir = 0` to the isolated app's generated configuration allowed the unmodified APK to run. All 2.1 UI successes below therefore require this configuration workaround; they are not evidence of an out-of-box 2.1 installation working.

The v2.0 release asset itself reports versionName **2.1** and versionCode **1021201**, as does the actual v2.1 release asset. Pin the release URL and SHA-256 below; the displayed version alone cannot distinguish these APKs.

No reader source, image rendering, archive loading, frame parser, or navigation algorithm was modified. No real Android device or existing AVD was used.

## Reader and test environment

- Official [2.1 release](https://github.com/ACBF-Advanced-Comic-Book-Format/ACBF-Viewer-for-Android/releases/tag/v2.1), asset `ACBFViewerforAndroid-2.1.apk`; SHA-256 `eef447647211aeb27f4a5e454e881f70a97a11372dae3d932e0ebe46ffc6ef24`.
- Official [v2.0 APK asset](https://github.com/ACBF-Advanced-Comic-Book-Format/ACBF-Viewer-for-Android/releases/download/v2.0/ACBFViewerforAndroid-2.0.apk); SHA-256 `87c2891541d0ae54812e46b2defbd603a97ce9762054e0829ba21089b178e03f`. Tested in separate fresh app state, never downgraded over the workarounded installation.
- APK package `org.acbf.acbfa`, versionName `2.1`, versionCode `1021201`, min SDK 21, target SDK 31, ARM64 and ARMv7 native code. Launch activity `org.kivy.android.PythonActivity`.
- Fresh Pixel 5 AVD, installed system image `system-images;android-34;google_apis;arm64-v8a`, 1080×2340 portrait screen, headless emulator using `swiftshader_indirect` GPU rendering.
- First AVD serial `emulator-5562`, recorded emulator PID `15987`; stopped by this exact PID after collecting evidence. Its files are preserved.
- Second AVD serial `emulator-5564`, recorded emulator PID `31088`, AVD home `v20-avd-home` and AVD path `v20-avd` within the same scratch root. Stopped by this exact PID after collecting evidence. Both isolated AVDs and all evidence are preserved; no emulator from this validation remains running.
- Scratch root: `/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/acbf-android-e2e.q335cv4f`. The entire screenshots, APKs, logcats, config snapshots, isolated AVD, and recorded command arguments remain there. Scratch files are machine-local and may eventually expire.

## First-run failure and exact workaround

The first launch generated `files/.acbfa.ini`, requested storage access, then exited with:

```text
configparser.NoOptionError: No option 'use_temp_dir' in section: 'general'
```

The traceback reaches `load_settings` in `main.py` line 1288. The same read exists in [2.1 source](https://github.com/ACBF-Advanced-Comic-Book-Format/ACBF-Viewer-for-Android/blob/v2.1/main.py); [2.0 source](https://github.com/ACBF-Advanced-Comic-Book-Format/ACBF-Viewer-for-Android/blob/v2.0/main.py) supplies a `use_temp_dir: 0` default in `build_config` that 2.1 removed. This is source evidence of the regression, independent of the metadata fixtures.

The APK is debuggable. The generated configuration was copied aside both on the isolated device and on the host, then the following single line was added under `[general]`:

```ini
use_temp_dir = 0
```

The app was launched again normally. It opened its bundled tutorial. The UI reports version 2.1 and its default **Zoom to frame** setting is ON. Durable evidence: [crash excerpt](assets/android-validation-2026-10-07/v21-first-start-crash.txt), [original config](assets/android-validation-2026-10-07/acbfa-before-workaround.ini), [config with the one-line workaround](assets/android-validation-2026-10-07/acbfa-workaround.ini), [settings screenshot](assets/android-validation-2026-10-07/09-settings.png).

## Stock v2.0 release validation

The official v2.0 release asset was installed into a newly created second AVD using the same Android 14 system image. It launched its tutorial successfully on the first attempt. Its [first generated configuration](assets/android-validation-2026-10-07/v20-clean-first.ini) already contains `use_temp_dir = 0`. No configuration injection, source change, or direct app-state mutation was used in this test.

In this release, enable **Change Library Folder** in Settings to open the Android document-tree picker. Select the folder containing the control CBZ, then **Use this folder** and **Allow**. The ordinary library UI imports the archive and displays its frame definitions. With the default **Zoom to frame** enabled, the visible sequence was cover → 3 → 1 → previous 3 → next 1 → 4 → 2 → whole-page fallback.

Durable evidence: [settings](assets/android-validation-2026-10-07/v20-04-settings.png), [book metadata](assets/android-validation-2026-10-07/v20-10-control-dialog.png), [cover](assets/android-validation-2026-10-07/v20-11-control-cover.png), [3](assets/android-validation-2026-10-07/v20-12-control3.png), [1](assets/android-validation-2026-10-07/v20-13-control1.png), [previous 3](assets/android-validation-2026-10-07/v20-14-control-prev3.png), [next 1](assets/android-validation-2026-10-07/v20-15-control-next1.png), [4](assets/android-validation-2026-10-07/v20-16-control4.png), [2](assets/android-validation-2026-10-07/v20-17-control2.png), [fallback](assets/android-validation-2026-10-07/v20-18-control-fallback.png), and [artifact hashes](assets/android-validation-2026-10-07/v20-artifact-manifest.json). This completes the fresh-stock-release control test. Real comic sample and full-book smoke tests below were performed in the first AVD with the v2.1 workaround; they were not repeated in v2.0.

## Import and navigation method

For the v2.1 tests below, files were transferred into new folders on the isolated emulator's shared storage using `adb -s emulator-5562 push`. Within the actual app:

1. Tap the center to show the toolbar; open Settings.
2. Select **Comics Path**, which opens Android's standard document-tree picker.
3. Select the test folder, choose **Use this folder**, then **Allow**. The app reads the CBZ files through the granted content URIs.
4. Close settings, show the toolbar, open the comic library, select the book, then press its folder/open icon.
5. With the toolbar hidden, tap the right third to advance one frame and the left third to go back. On this screen the test used `(950,1200)` and `(100,1200)`.
6. Wait for the animation to settle, capture the actual framebuffer with `adb exec-out screencap -p`, and inspect it.

All app interaction was through ADB touch events and the genuine release UI; the panel decisions came from the archive's embedded ACBF. The only direct app-state edit was the explicitly recorded startup configuration workaround.

## Synthetic tests

| Test | Observed result | Evidence |
| --- | --- | --- |
| Regular numbered fixture | Opened cover, then focused 1 → 2; previous returned to 1; next returned to 2, then 3 → 4 → full-page fallback. | Scratch screenshots `13`–`22`. |
| Non-geometric order control | Same page images, XML frame order changed to 3 → 1 → 4 → 2. UI followed that order. Previous from 1 returned to 3. | Durable screenshots linked below. |
| Cover and page transition | Library shows `2 + cover`, cover opens once, final body frame advances to the fallback page. | Book dialog and cover/fallback screenshots. |
| Fallback | One full-page polygon displays the whole source page in frame mode. | Final screenshot reads `WHOLE PAGE FALLBACK`. |

The control CBZ SHA-256 is `4ea5e750ccdf3d4df23f251d6b8171b7a46f63d7fdafd274b9db52200ce35220`; its source path is `/private/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/comic-acbf-order-control-einofv1r/non-geometric-order.cbz`. Its manifest records the intentional order `[3,1,4,2]`.

Durable sequence: [book metadata](assets/android-validation-2026-10-07/27-control-dialog.png), [cover](assets/android-validation-2026-10-07/28-control-cover.png), [3](assets/android-validation-2026-10-07/29-control3.png), [1](assets/android-validation-2026-10-07/30-control1.png), [previous back to 3](assets/android-validation-2026-10-07/31-control-prev3.png), [4](assets/android-validation-2026-10-07/33-control4.png), [2](assets/android-validation-2026-10-07/34-control2.png), [fallback](assets/android-validation-2026-10-07/35-control-fallback.png). Screenshot hashes are in the [artifact manifest](assets/android-validation-2026-10-07/artifact-manifest.json).

**Presentation detail:** the reader fits the rectangular bounds of each frame and centers it, but does not clip away neighboring artwork. A very wide panel in portrait can therefore show neighboring panels above or below. The selected panel's center and scale, and the effect of ordered navigation, are unambiguous in the control screenshots. Metadata enables guided focusing; it does not guarantee an isolated crop filling the screen.

## Real comic tests

The source was the user's *Parallel Truths Graphic Novel Anthology* PDF. Source files were preserved. These tests validate transport and navigation, not the correctness of automatic segmentation.

| Artifact | Observed reader behavior | Scope |
| --- | --- | --- |
| Four-page Gemini sample, source PDF pages 1, 3, 5, 25 | Library imported the archive. Cover and title page displayed normally. Source page 5, whose Gemini request failed, remained readable as a whole page. Source page 25 advanced through the five emitted frame regions; previous from region 2 returned to region 1. | Screenshots `40`–`50` in scratch. The fifth region visibly merges two bottom panels, a model quality failure carried faithfully into the reader. |
| Full Pannello conversion, 257 pages, 75,361,608 bytes | Library reported `256 + cover` and frame definitions True. Book opened its cover; next moved to source page 2 and subsequent taps advanced its detected regions. Previous at the first region returned to the cover. | Screenshots `52`–`58` in scratch. Smoke test of archive import, count, rendering and navigation; all 257 pages were not read through. |
| Four-page Pannello sample | Imported into the same library and metadata dialog reports `3 + cover`. | Import/metadata check only; real panel navigation was exercised with the Gemini sample and full conversion. |

Gemini sample SHA-256: `4f6ef5f6856141a6f8d38b6f9f5e77ae624dadd15417bddd1df7f7db00848869`. Artifact: `/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/comic-gemini-e2e-fer6gndl/run/gemini-sample.cbz`.

Full conversion artifact: `/private/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/comic-panel-e2e-convert-d3c3sbds/comic.cbz`. Its sibling manifest and reader-check file capture source-to-output details. Real comic screenshots remain in local scratch; repository evidence uses the synthetic fixture.

## Additional limitations found

- Importing a different folder while a book was open invalidated that book's extracted temporary images. Returning directly to that book could produce a blank image and `Image Not found .../tmp/0002.png` in logcat. Reopening the book from the library extracted it again. This is a reader usability issue, not an archive-order failure.
- These results cover one Android 14 ARM64 emulator and portrait orientation. They do not certify a physical phone/tablet, Android 15/16, other ABIs, rotation, RTL controls, extreme page dimensions, or arbitrary reader applications.
- API failures and detected panel boundaries/order remain converter-quality concerns. A reader can honor incorrect metadata perfectly.

## Reproduction outline

Create a new scratch AVD home/path; use an already installed system image. Never reuse, wipe or reset an existing user AVD for this test. The commands used were equivalent to:

```sh
ANDROID_AVD_HOME="$scratch/avd-home" ANDROID_SDK_ROOT="$sdk" \
  "$sdk/cmdline-tools/latest/bin/avdmanager" create avd \
  --name acbf_e2e_api34 --device pixel_5 \
  --package 'system-images;android-34;google_apis;arm64-v8a' \
  --path "$scratch/avd"

ANDROID_AVD_HOME="$scratch/avd-home" ANDROID_SDK_ROOT="$sdk" \
  "$sdk/emulator/emulator" -avd acbf_e2e_api34 -port 5562 \
  -no-window -no-audio -no-snapshot -gpu swiftshader_indirect -no-boot-anim

"$sdk/platform-tools/adb" -s emulator-5562 install ACBFViewerforAndroid-2.1.apk
"$sdk/platform-tools/adb" -s emulator-5562 shell am start \
  -n org.acbf.acbfa/org.kivy.android.PythonActivity
```

Wait until `getprop sys.boot_completed` returns `1` before installing. Record the emulator PID at launch and stop only that PID after evidence collection. Always specify the exact device serial. The missing-setting workaround must be applied only to the throwaway 2.1 installation, after preserving the first-run config and crash evidence. Production reader onboarding needs a supported release or upstream fix; the workaround is an experimental qualification, not a desirable product requirement.
