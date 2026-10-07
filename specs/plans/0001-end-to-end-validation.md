# Validate conversion and Android panel reading

Status: paused at the user's request on 2026-10-07. Authorized validation is substantially executed; the consolidated synthesis and next-phase discussion are unfinished. This is a validation prototype, not the production Rust migration. Resume from the [handoff](../handoff-comic-panel-cli.md).

## Question and scope

Can an automatic converter produce a CBZ that preserves complete comic pages and makes an existing Android reader follow embedded panel geometry in the intended order?

Use existing tools first. The initial integration is Pannello/Poppler plus a small ACBF adapter, with Gemini evaluated on representative pages when credentials are available. This distinguishes reader interoperability from detector accuracy. The [vision](../vision/comic-panel-cli.md) remains authoritative for product behavior; the [reuse research](../research/existing-comic-conversion-solutions.md) explains the dependency choices.

Preserve the Flutter project and all source books. All generated books, model responses, temporary environments, and emulator state belong in fresh isolated directories. Publish new paths exclusively; never overwrite earlier results. No user-facing review or correction tool is part of this prototype.

## Work and completion evidence

1. **Build the format adapter.** Reuse Pannello's full-page CBZ and ordered normalized rectangles. Use existing XML and ZIP libraries to produce root-level ACBF 1.1 with pixel-coordinate frames and the cover listed once. Validate actual dimensions, frame bounds, image references, page order, schema, and collision refusal. Preserve image bytes and relevant existing metadata. Record a passing and failing fixture before relying on the adapter.
2. **Exercise the real reader.** Install the official ACBF Viewer for Android APK on a fresh isolated emulator. Import the generated CBZ through its actual interface. Observe next/previous panel navigation, a page transition, and a page without panel guidance. Use an asymmetric synthetic fixture whose metadata order is unmistakable, including a deliberately non-geometric sequence to distinguish metadata consumption from automatic sorting. Preserve screenshots, the APK version/hash, Android version, and commands. A parser-only test does not complete this step.
3. **Exercise representative real pages.** Read the Downloads PDF without changing it. Include its cover, composed contents page, ordinary panels, and inset/overlapping layouts. Run automatic detection and packaging with a recorded source-page mapping, then open the resulting artifact in the same reader. Describe missed regions or wrong order explicitly; schema validity does not establish segmentation quality. This development assessment is not a manual correction workflow.
4. **Check Gemini integration.** Retrieve the user's key through the established secret mechanism without printing or committing it. Verify a currently accessible model and structured-output request on a small sample before expanding calls. Record model, request count, usage, geometry validation, and failures. Keep successful page outcomes for reuse. Credential or model-access failures are reported separately from the local converter result.
5. **Check book-scale packaging.** When the small path works, run the 257-page input through the validated pipeline with per-page progress. Preserve the source hash and all rendered pages, report page/fallback counts, and confirm the archive's full reference coverage. A full local-detector run and a small Gemini sample are separate observations; neither may be described as a whole-book Gemini result.
6. **Record the result and the Rust boundary.** Save a concise validation report under `specs/research/`, linking the generated artifacts and evidence. Update this plan with observed results and any unresolved acceptance checks. Propose the next implementation phase only from those findings.

## Dependency versus owned-code boundary

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
