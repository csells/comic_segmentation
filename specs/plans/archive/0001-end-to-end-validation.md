# Validate conversion and Android panel reading

Status: **completed and archived, 2026-10-07**. The executed experiment and its
reporting are complete. Format/preservation/Android navigation passed within the
recorded scope; detector quality did not establish production readiness. See the
[consolidated result](../../research/end-to-end-validation.md) and proposed
[next plan](../0002-quality-gated-rust-cli.md). Completion authorizes neither a
production migration nor additional inference.

## Question and scope

Can an automatic converter produce a CBZ that preserves complete comic pages and makes an existing Android reader follow embedded panel geometry in the intended order?

Use existing tools first. The initial integration is Pannello/Poppler plus a small ACBF adapter, with Gemini evaluated on representative pages when credentials are available. This distinguishes reader interoperability from detector accuracy. The [vision](../../vision/comic-panel-cli.md) remains authoritative for product behavior; the [reuse research](../../research/existing-comic-conversion-solutions.md) explains the dependency choices.

Preserve the Flutter project and all source books. All generated books, model responses, temporary environments, and emulator state belong in fresh isolated directories. Publish new paths exclusively; never overwrite earlier results. No user-facing review or correction tool is part of this prototype.

## Work and completion evidence

1. **Build the format adapter.** Reuse Pannello's full-page CBZ and ordered normalized rectangles. Use existing XML and ZIP libraries to produce root-level ACBF 1.1 with pixel-coordinate frames and the cover listed once. Validate actual dimensions, frame bounds, image references, page order, schema, and collision refusal. Preserve image bytes and relevant existing metadata. Record a passing and failing fixture before relying on the adapter.
2. **Exercise the real reader.** Install the official ACBF Viewer for Android APK on a fresh isolated emulator. Import the generated CBZ through its actual interface. Observe next/previous panel navigation, a page transition, and a page without panel guidance. Use an asymmetric synthetic fixture whose metadata order is unmistakable, including a deliberately non-geometric sequence to distinguish metadata consumption from automatic sorting. Preserve screenshots, the APK version/hash, Android version, and commands. A parser-only test does not complete this step.
3. **Exercise representative real pages.** Read the Downloads PDF without changing it. Include its cover, composed contents page, ordinary panels, and inset/overlapping layouts. Run automatic detection and packaging with a recorded source-page mapping, then open the resulting artifact in the same reader. Describe missed regions or wrong order explicitly; schema validity does not establish segmentation quality. This development assessment is not a manual correction workflow.
4. **Check Gemini integration.** Retrieve the user's key through the established secret mechanism without printing or committing it. Verify a currently accessible model and structured-output request on a small sample before expanding calls. Record model, request count, usage, geometry validation, and failures. Keep successful page outcomes for reuse. Credential or model-access failures are reported separately from the local converter result.
5. **Check book-scale packaging.** When the small path works, run the 257-page input through the validated pipeline with per-page progress. Preserve the source hash and all rendered pages, report page/fallback counts, and confirm the archive's full reference coverage. A full local-detector run and a small Gemini sample are separate observations; neither may be described as a whole-book Gemini result.
6. **Record the result and the Rust boundary.** Save a concise validation report under `specs/research/`, linking the generated artifacts and evidence. Update this plan with observed results and any unresolved acceptance checks. Propose the next implementation phase only from those findings.

## Completion ledger

The numbered work above is retained as the original experiment contract. Its
completion ledger is:

| Work item | Closure evidence and qualification |
| --- | --- |
| 1. Format adapter | [Converter report](../../research/e2e-converter-validation.md): seven tests, cover once, ordered bounded pixels, image/auxiliary preservation, collision refusal, XSD/parser passes. Single-image input explicitly rejected; atomic publication remains later work. |
| 2. Actual reader | [Android report](../../research/android-reader-validation.md): stock v2.0 release asset on API 34 followed 3 → 1 → 4 → 2, previous, cover and fallback. v2.1 passes required a startup-config workaround. |
| 3. Real pages | [Converter sample](../../research/e2e-converter-validation.md#real-art-findings) and [Gemini sample](../../research/gemini-e2e-validation.md): original pages 1, 3, 5, 25 preserved. Actual Gemini navigation tested on workarounded v2.1. Real panel merges/splits recorded rather than accepted as quality passes. |
| 4. Gemini integration | [Request evidence](../../research/gemini-e2e-validation.md): six Flash calls, three successes/three 503s; four Pro hard-quota failures. Retry classifier corrected offline. Exactly ten historical calls; no Pro quality comparison. |
| 5. Book scale | [Full manifest](../../../prototypes/comic_panel_e2e/evidence/pdf-full.manifest.json): 257 pages / 1,094 frames / 48 fallbacks, unchanged PDF hash and rendered-image bytes. XSD/parser complete; Android UI smoke test only. Local detector, not full-book Gemini. |
| 6. Report and boundary | [Synthesis](../../research/end-to-end-validation.md) consolidates exact evidence and artifact availability; [0002](../0002-quality-gated-rust-cli.md) proposes Rust ownership, staged acceptance and unresolved policies for discussion. |

No validation-experiment acceptance check is silently carried as a pass. The
remaining product concerns move to 0002: representative segmentation quality,
physical-device/stock-reader real-book qualification, CBR safety/variants, corrupt
inputs and resource limits, folder ordering, single-image policy, catalog merging,
atomic publication, resume/cost controls, RTL and full-book Gemini reliability.
Private binaries were retained on the original machine but are absent in the new
clone; this is an explicit replay limitation, not a reason to repeat paid calls.

## Recorded implementation boundary

| Piece | Validation implementation | Rust product implication |
| --- | --- | --- |
| PDF composition/rendering | Existing Poppler tools | Retain as a dependency initially; do not write a PDF renderer. |
| Existing detector/converter | Pinned Pannello/Kumiko dependencies | Can remain an external dependency or baseline; do not silently port upstream algorithms or change the agreed Gemini provider. |
| Model inference | Gemini service and supported HTTP/SDK tooling | Keep the service dependency; implement owned request orchestration and response validation in Rust. |
| Archive/image/XML primitives | Established ZIP, image, and XML libraries | Use maintained Rust libraries or established external tools. |
| Page identity/order, coordinate conversion, ACBF profile, safe output, retry/fallback policy | Small project-owned prototype adapters | Rewrite these owned behaviors in Rust after validation; retain shared fixtures and observed reader behavior as acceptance evidence. |
| Reader | Official Android APK | External compatibility target, not a reader to rebuild. |

Pin upstream versions and record license/deployment constraints. Reuse through a dependency does not erase its license, runtime, or maintenance requirements. A successful Python prototype is evidence for the behavior to preserve, not a requirement to ship Python as the final implementation.

## Acceptance and limits

The format/reader path passes only when the actual Android application opens the generated CBZ and visibly follows the encoded sequence while retaining whole-page access. Original-file hashes and page/image mapping checks must pass. Detection accuracy and reliability on the real sample are reported separately, including valid-looking omissions that do not trigger fallback.

Do not call the entire product complete from this experiment. CBR variants, general folder layouts, publication packaging, broad Android-device coverage, full-book Gemini quality/cost, and the Rust rewrite still require explicit evidence or later implementation.
