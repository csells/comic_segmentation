# Comic panel conversion: validation synthesis

Continuation update: the source PDF is now recovered and hash-verified; new
[offline replays](pdf-saved-result-replay.md) of the saved geometry are available in
Panel Lab. They do not change the historical detector-quality findings or restore
the missing original CBZ bytes. Availability statements below describe the initial
fresh-clone checkpoint.

Completed 2026-10-07 from checkpoint `49bd512` and its retained evidence.
**Complete pages and ordered ACBF frames reach a real Android reader successfully.
Automatic segmentation is not ready for a production-quality claim.** This closes
the [validation experiment](../plans/archive/0001-end-to-end-validation.md);
the [Rust plan](../plans/0002-quality-gated-rust-cli.md) is a proposal for discussion.

After synthesis, Chris changed the immediate review target to a phone browser
hosted in the home lab; native Android is deferred. The Android results below
remain valid historical evidence. A narrow web-reader experiment is now
authorized. The [hosted web experiment](web-reader-validation.md) now passes its
synthetic browser checks; it does not change the segmentation findings or permit
new AI calls.

## Results and their boundaries

| Track | Measured result | What remains unproved |
| --- | --- | --- |
| Format and order | Root `metadata.acbf`, ACBF 1.1, full-page images, integer pixel polygons in XML order. XSD and unchanged Android parser accepted all references/frames. Actual Android UI followed **3 → 1 → 4 → 2**, including previous navigation and whole-page fallback. | Arbitrary readers, isolated panel cropping, RTL controls. |
| Full-book preservation | 257 pages, one cover plus 256 body pages, 1,094 frames, 48 reported whole-page fallbacks, zero detector exceptions. 103.35 seconds total / 43.05 seconds detection. Every archived image matched its rendered input; source PDF hash stayed unchanged. | 48 is not an error rate; covers/splashes contribute. No full-book quality annotation or 257-page UI read-through. |
| Reader installation | Official **v2.0 release asset** started in a fresh Android 14 / API 34 ARM64 AVD and passed the control sequence without a configuration edit. | Physical devices and a supported product installation experience. Both tested assets display version 2.1; identify them by URL and hash. |
| Reader on real books | **v2.1 asset with `use_temp_dir = 0` workaround** imported the full book as `256 + cover` and navigated its first body page. It also navigated the Gemini sample, including fallback and five emitted regions. | These real-book tests were not run on the stock v2.0 asset. Stock v2.1 crashes on first launch. |
| Gemini service | Flash: six calls, three valid responses, three HTTP 503s; source pages 1, 3, 5, 25 emitted `[1,1,1,5]` frames. Page 5 exhausted two attempts. | Full-book service reliability, cost and a successful complex-page-5 result. |
| Gemini quality | Page 25 visibly has six panels; Flash merged the bottom two into one valid box. | Geometry validation cannot detect this omission. No measured representative quality baseline yet. |
| Pro comparison | Four HTTP 429s on pages 5 and 25, explicit zero free-tier quota. No generated output. | No Pro quality comparison or entitlement to use it. |
| Local detector quality | Pannello merged/split panels on page 25 and mis-mapped page 5 despite matching its apparent panel count. | Neither synthetic success nor frame counts justify adopting this detector. |

The three measured reports remain the detailed sources:
[converter/preservation](e2e-converter-validation.md),
[Android installation and UI](android-reader-validation.md), and
[Gemini requests and quality](gemini-e2e-validation.md).
The full-book run used the local detector, not Gemini. The Gemini sample was
four composed PNG pages, 1027 × 1500; the full PDF run rendered JPEG at 150 DPI.
PDF preservation means visible page composition, not original vectors/compression.

## Reader qualification

The control test used the official
[v2.0 APK asset](https://github.com/ACBF-Advanced-Comic-Book-Format/ACBF-Viewer-for-Android/releases/download/v2.0/ACBFViewerforAndroid-2.0.apk),
SHA-256 `87c2891541d0ae54812e46b2defbd603a97ce9762054e0829ba21089b178e03f`.
Its stock settings/library-folder workflow and exact UI sequence are recorded in
the [Android report](android-reader-validation.md#stock-v20-release-validation).
The v2.1 asset SHA-256 is
`eef447647211aeb27f4a5e454e881f70a97a11372dae3d932e0ebe46ffc6ef24`.

Tracked synthetic screenshots show [cover](assets/android-validation-2026-10-07/v20-11-control-cover.png),
[3](assets/android-validation-2026-10-07/v20-12-control3.png),
[1](assets/android-validation-2026-10-07/v20-13-control1.png),
[previous 3](assets/android-validation-2026-10-07/v20-14-control-prev3.png),
[next 1](assets/android-validation-2026-10-07/v20-15-control-next1.png),
[4](assets/android-validation-2026-10-07/v20-16-control4.png),
[2](assets/android-validation-2026-10-07/v20-17-control2.png), and
[fallback](assets/android-validation-2026-10-07/v20-18-control-fallback.png).
The reader centers/fits frame bounds and can expose neighboring artwork. Changing
library folders can invalidate extracted images until the book is reopened.
The stock v2.0 test answers the experiment's installation question; it is not
physical-device certification or a commitment to ship that reader version.

## Service failures are separate from reading quality

Exactly **ten generation calls** were recorded: six Flash and four Pro. Flash's
three successful responses reported **4,095 input + 384 output + 1,721 thought =
6,200 total tokens**. Usage for seven failed calls was absent, not zero. No billed
currency or whole-book extrapolation is established. The Pro probe originally
retried hard quota failures; a subsequent offline fix stops explicit zero/daily
quota and excessive retry delays. Captured reports preserve the original calls.

Whole-page fallback keeps an imported page readable after a detected failure.
It does not rescue an unnoticed merge or establish good guided reading. A valid
whole-page classification for a cover is also different from fallback after an
API failure. Production reports must preserve that distinction. Unreadable source
pages are import failures, not permission to drop content or invent a replacement.

## Retained evidence and artifact availability

Recomputed from tracked JSON in this fresh clone: 257 page records, 1,094 frames,
48 fallback reasons, six Flash requests, four Pro requests and 6,200 reported
tokens. The [full manifest](../../prototypes/comic_panel_e2e/evidence/pdf-full.manifest.json)
and [parser result](../../prototypes/comic_panel_e2e/evidence/pdf-full.reader-check.json)
retain the page map and polygons. The
[Flash manifest](evidence/gemini-e2e/flash-manifest.json),
[Flash report](evidence/gemini-e2e/flash-report.json), and
[Pro quota report](evidence/gemini-e2e/pro-quota-report.json) retain the sample evidence.
The source PDF's recorded before/after SHA-256 is
`30d075d2bf54cdcd2401ccf905ab50a859779296e7afdbff404efd291f42cd32`.

The original handoff records these durable copies beneath
`validation-artifacts/20261007-162937/` in the **original checkout**:

| Artifact filename | Bytes | Recorded SHA-256 |
| --- | ---: | --- |
| `parallel-truths-local-detector.cbz` | 75,361,608 | `7fc2547e38a0a1c86c5d338378adabfb0ba5a551f7926da519f9057fa4fc66e7` |
| `gemini-sample.cbz` | 7,539,350 | `4f6ef5f6856141a6f8d38b6f9f5e77ae624dadd15417bddd1df7f7db00848869` |
| `metadata-order-control.cbz` | 38,231 | `4ea5e750ccdf3d4df23f251d6b8171b7a46f63d7fdafd274b9db52200ce35220` |
| `known-order.cbz` | 38,214 | `78b79194060f980092d2f3fcdc2d0c7026a2b4c212a1b381c2595c0052a637bd` |

**Availability on the continuation host:** only `validation-artifacts/.gitignore`
arrived in this clone. Those CBZs, their local manifest, the source PDF and the
named scratch environments are absent at their recorded paths. No claim is made
that their bytes were rehashed here. The [handoff inventory](../handoff-comic-panel-cli.md#artifacts-available-to-the-next-agent)
provides original-machine locations; recover copies and verify these hashes
before a future replay. Missing private binaries do not invalidate the retained
experimental record, but prevent independent replay here. Do not regenerate
successful paid responses to replace missing files.

Continuation checks: all 25 checkpoint JSON files parse; the two Android
manifests verify 22 screenshot/config files byte-for-byte. Selected stock-reader
screenshots were visually reinspected. Documentation links and the Git diff are
checked separately from the original application's acceptance tests. All seven
adapter and eight Gemini contract tests also passed again offline in the disposable
web-reader VM. No historical private-book conversion, Android UI run or inference
was repeated.

## Consequences for implementation

Use the measured ACBF profile and preservation fixtures as acceptance contracts.
Keep PDF rendering, archive/image/XML primitives and inference as dependencies;
own identity/order, geometry validation, Gemini orchestration, manifests, safe
publication and reporting in Rust. The experiment does not select Pannello's AGPL
detector as a shipping dependency or prove an untested transport API.

Plan 0002 first establishes a representative quality baseline and a hosted
phone-browser review path, carrying the original Android work forward for later. It carries forward CBR/RAR compatibility and extraction
safety, damaged inputs, resource limits, folder ordering, single-image books,
catalog precedence, atomic publication, resume and spending controls, RTL,
physical devices and full-book Gemini reliability/quality. Those requirements
remain open even though this validation experiment is complete. No production
rewrite, new generation calls or billing changes were made during synthesis.
