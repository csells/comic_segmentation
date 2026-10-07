# Continue comic-panel CLI validation

The user paused work on 2026-10-07 and requested a branch check-in plus this handoff. Resume only when the user gives this prompt to a new agent or otherwise asks to continue. This is a session-continuation prompt, not authorization to start a production rewrite.

## Mission and checkout

Finish documenting the executed end-to-end validation and discuss a concrete Rust implementation plan grounded in the results. Do not claim automatic segmentation is production-ready.

- Repository: `/Users/csells/Code/csells/comic_segmentation`.
- Checkpoint branch: `research/comic-panel-cli-validation`, based on `main` at `3cd8046`.
- Work belongs in `specs/vision`, `specs/research`, `specs/plans`, and isolated `prototypes/` scaffolding.
- The Flutter application remains unchanged. `.vscode/settings.json` was already modified before this task; it is deliberately excluded from the checkpoint commit. Preserve that unrelated change.
- The user requested research, a vision, later plan discussion, and end-to-end validation using whatever existing technology works. The intended owned product code remains Rust; useful third-party libraries may remain dependencies.

## Read first, in order

1. [Vision](vision/comic-panel-cli.md): accepted scope and interview answers.
2. [Paused validation plan](plans/0001-end-to-end-validation.md): authorized work and acceptance boundaries.
3. [Android UI results](research/android-reader-validation.md): real installed-app evidence, startup defect and reader limitations.
4. [Converter results](research/e2e-converter-validation.md) and [Gemini results](research/gemini-e2e-validation.md): measured success, quality failures, request counts and retained evidence.
5. [Existing solutions](research/existing-comic-conversion-solutions.md) and [portable metadata](research/portable-comic-panel-metadata.md): primary-source research, licenses and interoperability.
6. [Rust dependencies](research/rust-cli-dependencies.md) and [Gemini contract](research/gemini-segmentation-contract.md): implementation candidates, not final dependency commitments.
7. [Converter prototype](../prototypes/comic_panel_e2e/README.md) and [Gemini prototype](../prototypes/gemini_panel_probe/README.md): exact reproduction commands and code limits.

## Decisions already answered by the user

- Android is the first reading target. The CLI starts on macOS and should remain portable Rust.
- Inputs: CBR/CBZ, PDF, or an image folder. Output: a new CBZ with complete page images and panel metadata.
- Automatic conversion only: no optional review, correction interface, or manual panel-editing workflow.
- After bounded page-detection retries fail, retain the entire page and clearly report the affected page and reason. Do not drop source content.
- Gemini with the user's API key is the v1 provider, including uploading page images to Google. Local inference and other providers are deferred.
- Validate the whole conversion/reader path with existing tools first. Rewrite project-owned behavior in Rust later; do not rewrite capable third-party libraries merely because they are not Rust.
- No interview question is currently pending. CBC collection support was never confirmed; do not add it to the core scope or block this validation on it. If a genuine decision is needed, use the invoked grill-me approach and ask one question at a time.

## Verified results at the pause

### Format, preservation and scale

The converter prototype reuses pinned Pannello/Kumiko, Poppler, Pillow, and standard ZIP/XML tooling. Its small owned adapter emits root `metadata.acbf` using the ACBF 1.1 namespace, integer pixel polygons and XML frame order. It preserves complete page images and the cover exactly once.

- Full input: `/Users/csells/Downloads/Parallel Truths Graphic Novel Anthology - Reader Nation.pdf`, 257 pages, 119,103,854 bytes. Composed pages require full-page rendering; embedded-image extraction is insufficient.
- Source SHA-256 before and after: `30d075d2bf54cdcd2401ccf905ab50a859779296e7afdbff404efd291f42cd32`.
- Full conversion: 257 page images, 1,094 frames, 48 reported whole-page fallbacks, zero detector exceptions; 103.35 seconds total, 43.05 seconds detection. The fallback count includes legitimate covers/splashes and is not an error rate.
- PDF rendered at 150 DPI into JPEGs. Every archived image matches its rendered input bytes. This preserves visual composition, not original PDF vector data or compression.
- Authoritative XSD and unchanged upstream Android metadata parser verified every image/frame in order. The actual Android app imported `256 + cover`, opened the full book, and navigated regions on its first body page. This was a UI smoke test, not a read-through of 257 pages.
- Seven meaningful adapter tests passed. Source mapping ambiguity, duplicate/unmapped pages, symlinks and output collisions are rejected. Invalid geometry gets an explicit whole-page fallback reason.
- Source auxiliary metadata bytes are retained. Existing `.acbf` is stored as `source-metadata/*.acbf.original` in the derived archive to avoid competing active documents; catalog fields are not yet merged into the new ACBF.
- ACBF 1.1 requires a body page in addition to its cover; single-image books are currently rejected. Do not silently duplicate their cover.
- The Android parser requires a `publish-info` element despite it being optional in the schema. The adapter includes it. The initial failure was `'NoneType' object has no attribute 'find'`.

Pinned sources: Pannello `d4747266b5e8ac478168050f75c9ea71bba00e85`; ACBF XSD `e033e004e2897fe20ad09cbd649a8ba1d6b38d09`; Android parser `1be5e700e793dd864828bbc48927bf28d2f43970`. Pannello/Kumiko are AGPL dependencies, not an implicit final licensing decision. OpenCV 4.14.0.94 works for this baseline; OpenCV 5 broke the synthetic detector probe.

### Actual Android navigation

Official ACBF Viewer for Android v2.1 release APK, API 34 ARM64 isolated emulator, followed a deliberately non-geometric sequence **3 → 1 → 4 → 2**. Previous from 1 returned to 3; cover appeared once; the next page showed the whole-page fallback. This proves metadata order controls navigation. Screenshots of our synthetic fixture are tracked under `specs/research/assets/android-validation-2026-10-07/`.

Stock v2.1 first launch failed with:

```text
configparser.NoOptionError: No option 'use_temp_dir' in section: 'general'
```

Adding only `use_temp_dir = 0` to the fresh test app's config, after preserving its original config, allowed the unchanged APK to run. All v2.1 navigation passes must retain this qualification. No user AVD or existing installed app was changed. A fresh second AVD was then used to test the official **v2.0 release asset**: stock startup and the actual sequence **cover → 3 → 1 → previous 3 → next 1 → 4 → 2 → whole-page fallback** passed without a config injection. That APK misleadingly advertises versionName/UI 2.1, so identify it by release URL and SHA, not its displayed version. The Android report records its exact asset and screenshots. The real-comic/full-book smoke tests used the v2.1 asset with its stated workaround, not the v2.0 release asset.

The reader fits/centers frame bounds but can show neighboring artwork; it does not clip each panel into an isolated full-screen crop. Importing another folder can invalidate the currently open book's extracted images; reopening the book from the library recovers it.

### Gemini and detection quality

Used official `google-genai==2.29.0`, supported `v1beta models.generateContent`, a JSON schema, explicit ordered boxes, temperature 0, an 8192 output-token cap, no implicit SDK retries, at most two attempts per page. Sample source PDF pages were 1, 3, 5, 25, rendered to 1027 × 1500 PNGs. No panel was manually corrected.

- `gemini-3.8-flash`: six calls, three valid responses and three HTTP 503 responses. Output frame counts `[1,1,1,5]`; page 5 exhausted two attempts and remained a whole-page fallback.
- Reported usage: 4,095 input + 384 output + 1,721 thought = **6,200 total tokens**. Failed requests supplied no usage. No billed currency was inferred.
- Source page 25 visibly has six panels but Flash merged its bottom two. The contract accepts the valid geometry, so structural validation does not catch this quality defect.
- A bounded same-prompt comparison used `gemini-3.1-pro-preview` on pages 5 and 25: four calls, all HTTP 429 with zero free-tier request/input-token quota. No Pro output or quality comparison exists. No billing/project settings were changed.
- Exactly **ten generation calls** occurred across both experiments. Stop further live calls until there is a concrete reason and bounded test scope; do not rerun successful probes merely to recreate evidence.
- The probe initially retried the hard 429s. A failing offline test exposed this; the classifier now stops on explicit zero/daily quota and excessive retry delays. Eight offline tests passed after the fix. The stored reports intentionally preserve the original four failed Pro calls.
- The Flash CBZ passed XSD/parser checks and actual Android UI navigation, including preserved fallback and the five emitted regions. A reader can honor incorrect segmentation perfectly.
- Pannello also failed on real pages: on page 25 it merged top/bottom pairs and split a middle panel; on page 5 its count of seven masked incorrect region mapping. Neither detector is accepted for production quality.

The environment did not have a Gemini key. The Dashlane secure note named `GEMINI_API_KEY` was invalid; `Gemini API key dartantic` worked. The probe retrieves the latter using `dcli`, captures it into memory, and never prints or persists it. Read the dashlane skill before credential access. Do not output credential values or change account settings.

## Artifacts available to the next agent

Durable local copies exist in the **Git-ignored** directory `validation-artifacts/20261007-162937/`. They will not arrive in a fresh clone; on this machine they were checked present at handoff. Preserve all of them.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `parallel-truths-local-detector.cbz` | 75,361,608 | `7fc2547e38a0a1c86c5d338378adabfb0ba5a551f7926da519f9057fa4fc66e7` |
| `gemini-sample.cbz` | 7,539,350 | `4f6ef5f6856141a6f8d38b6f9f5e77ae624dadd15417bddd1df7f7db00848869` |
| `metadata-order-control.cbz` | 38,231 | `4ea5e750ccdf3d4df23f251d6b8171b7a46f63d7fdafd274b9db52200ce35220` |
| `known-order.cbz` | 38,214 | `78b79194060f980092d2f3fcdc2d0c7026a2b4c212a1b381c2595c0052a637bd` |

Their adjacent `manifest.json` records source paths and hashes. Tracked text evidence is in `prototypes/comic_panel_e2e/evidence/` and `specs/research/evidence/gemini-e2e/`; tracked Android screenshots contain our synthetic artwork, not the user's comic pages.

Machine-local scratch paths, all retained rather than reset:

- Converter environment: `/tmp/comic-converters-research.PNH3Wl/venv/`.
- Initial sample PNGs: `/tmp/comic-panel-pdf-review.4MZwB2/page-{1,3,5,25}.png`.
- Gemini run, raw responses, overlays and environment: `/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/comic-gemini-e2e-fer6gndl/`; Flash under `run/`, quota-only comparison under `pro-run/`.
- Full conversion: `/private/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/comic-panel-e2e-convert-d3c3sbds/`; full run log `/tmp/comic-full-e2e-log.MKpd8P`; completed process PID 23312, exit 0.
- Android APKs, logs, real-comic screenshots and isolated AVDs: `/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/acbf-android-e2e.q335cv4f/`.
- Android tools: `/opt/homebrew/share/android-commandlinetools/{emulator/emulator,platform-tools/adb}`. Both owned emulator PIDs 15987 (`emulator-5562`) and 31088 (`emulator-5564`) were stopped and confirmed absent at pause. No task emulator remains running. PID values are historical, not permission to kill a reused PID later.

## Complete remaining work list

1. Read the final Android report. Its stock v2.0-release-asset startup and control-navigation results answer the installation-path follow-up; do not repeat them without a changed condition. Preserve the release URL/hash qualification and distinguish those tests from the v2.1 real-book tests.
2. Write `specs/research/end-to-end-validation.md` as the concise synthesis, linking the three measured reports, stable local artifacts and synthetic screenshots. Separate format/reader success, full-book preservation, model service failures, detector quality failures and reader installability. No aggregate report has been written yet.
3. Reconcile the paused validation plan with executed evidence. Finish and archive `0001` only when its remaining reporting/acceptance work is actually complete; preserve unresolved product requirements and update links when moving it. A useful experiment can be complete even when it disproves quality readiness.
4. Discuss/propose the next numbered plan under `specs/plans/` (`0002` is unused). First establish an explicit representative segmentation-quality baseline and a supported reader installation path. Keep developer evaluation separate from the forbidden product review UI. Do not silently choose a paid/quota-enabled model, change billing, add providers, or launch full-book Gemini inference.
5. Prepare the Rust boundary: own importer orchestration, canonical page identity/order, geometry validation, ACBF profile, safe publication, retry/quota classification, manifest/resume behavior and reporting. Reuse PDF rendering, archive/image/XML primitives and external inference as dependencies. Preserve fixtures as acceptance tests. Do not start the production Rust migration merely because this prototype works.
6. Carry forward unvalidated product concerns: CBR/RAR variants and extraction safety, damaged/unreadable inputs, decompression/resource limits, arbitrary folder order, single-image books, existing catalog precedence, atomic final publication, resumable calls, cost limits, RTL controls, physical Android devices and full-book Gemini reliability/quality. Prioritize these in the plan; do not imply the current scaffold implements them.
7. Validate relevant changed code, local links, JSON evidence and Git diff before the next checkpoint. Do not rerun expensive successful tests without a changed condition or unresolved concern.

Offline commands, from the repository root (already passed before this pause):

```sh
/tmp/comic-converters-research.PNH3Wl/venv/bin/python -m unittest discover -s prototypes/comic_panel_e2e -p test_adapter.py -v
python3 -m unittest discover -s prototypes/gemini_panel_probe -v
git diff --check
```

Expected test counts: seven converter tests and eight Gemini contract tests, with no API calls. The README contains integration/reader commands; do not blindly execute its live Gemini example. The check-in audit found no secret candidates or broken local Markdown links; all 21 JSON evidence files parsed. `git diff --cached --check` reports whitespace in the three verbatim captured Android `.ini` files (empty values and a final blank line). Their bytes intentionally remain unchanged; the check passes with those three evidence snapshots excluded.

## Standing rules and acceptance

- Never delete, overwrite, truncate, reset or reseed user/app data, including prior generated artifacts. Tests use new scratch scaffolding and exclusively new output paths. No `git clean`, blanket cleanup or user AVD reset.
- Stop only provably task-owned processes, by exact recorded PID. Never use `pkill`, `killall`, name-pattern termination, or quit a user app. Preserve AVDs/logs after stopping task-owned emulators; leave the existing ADB server alone.
- No real credentials or private comic images in Git. Never print Dashlane values. Keep the existing `.vscode/settings.json` change untouched and outside this task's commits.
- Never answer a question on the user's behalf. Ask only genuine unresolved decisions, one at a time, then wait; independent work may continue.
- Subagents are authorized when useful, with disjoint ownership. No agents need to be kept running during the pause.
- Read applicable project/user instructions and skills. Relevant skills already used were grill-me, research/deep-research, watch-background-work, pdf, codebase-design, writing-for-agents, computer-use, dashlane and agent-handoff-prompt. Shared skill tree: `/Users/csells/Code/csells/agent-skills/skills/`; shared methodology: `/Users/csells/Code/csells/agent-skills/house-rules.md`.
- Use red-green tests for meaningful owned behavior changes; never suppress root causes. The explicitly authorized whole-page fallback must remain reported, not hide failed detection.
- Internal artifacts belong in `specs/`; numbered plans move to `specs/plans/archive/` only on completion. No AI attribution in commits/PRs. No merge, PR, push or deployment is required to resume this research checkpoint.

Completion of this phase means a truthful consolidated validation result and a reviewable Rust plan based on it, with exact evidence and limitations. It does not mean declaring a good-reading-quality product from structurally valid metadata.
