# Comic panel CLI vision

Status: v1 scope captured through research and interview on 2026-10-07; implementation and reuse approach under discussion. This is not an implementation plan.

## Purpose

Turn a comic the user already owns into a portable comic archive that a compatible reader can navigate panel by panel. Reimagine the current Flutter page-segmentation experiment as a general-purpose Rust command-line tool that processes an entire book.

The desired workflow is to supply an existing comic archive, a comic PDF, or a folder of page images and receive a new CBZ containing the complete pages plus metadata describing their panels and reading sequence. The reading experience happens in an existing comic reader; the CLI prepares the book.

## Intended experience

The user opens the generated CBZ in a compatible reader, advances through panels in a sensible story sequence, and reads the artwork and lettering comfortably without repeatedly positioning and zooming the page by hand.

Panel metadata must identify both the region to display and its place in the sequence. Finding rectangles alone does not establish reading order. The result should preserve access to complete pages, including covers, title pages, credits, and pages without separable panels. Whole-page reading is the desired fallback when panel guidance is absent or unsupported; exact behavior depends on the reader and remains to be verified.

Android is the required reading platform for the first version. The Rust CLI initially runs on macOS, matching the user's current machine, while its code should remain portable for later Linux and Windows support. Broader reading-platform coverage remains a longer-term ambition. The research must connect a concrete archive layout to readers that actually consume it, without promising that every CBZ reader understands panel metadata.

The validation demonstrated CBZ with ACBF 1.1 driving ordered panel navigation in ACBF Viewer for Android. The tested v2.1 release required a startup configuration workaround, and automatic detection quality remains unresolved. See the [reader research](../research/portable-comic-panel-metadata.md), [actual Android validation](../research/android-reader-validation.md), and [paused-work handoff](../handoff-comic-panel-cli.md). These results do not yet establish production readiness.

The first version performs automatic conversion only. Panel detection and reading-order determination happen automatically, with no human review or correction step. Review tools, visual editors, and manual panel-editing workflows are outside v1 scope. This supersedes the earlier proposal for optional review and correction.

If panel detection fails on a page after retries, conversion continues and includes that complete page without panel guidance. The CLI clearly reports the affected pages and the failures; it must not silently imply that every page received panel guidance. This fallback concerns panel detection on a successfully imported page, not permission to omit unreadable source content. Retry limits and command exit-status details belong to the implementation plan.

V1 uses Gemini with the user's API key, sending page images to Google's service for analysis. Fully local inference and additional AI providers are deferred. The specific model, request limits, and cost controls belong to the implementation design.

## Scope from the request

- A Rust CLI that operates on a complete comic book.
- Initial CLI platform: macOS; keep the code portable for later Linux and Windows support.
- Inputs: CBR and CBZ archives, PDF comics, and folders containing page images.
- Output: a new CBZ with page images and interoperable panel metadata.
- V1 interaction: automatic conversion through the CLI, without a review or correction interface.
- V1 AI provider: Gemini using the user's API key; local inference and additional providers are deferred.
- Research existing open-source readers before choosing the compatibility target or implementation approach.
- Research existing converters and segmentation tools before implementing the pipeline; prefer reusing an adequate existing solution or component over rebuilding it.
- Capture the vision in `specs/vision`, evidence in `specs/research`, and a later implementation plan in `specs/plans` after discussion.

CBR and CBZ normalize the spoken archive names in the request. CBC is a separate collection format and is not silently included in the core input contract; whether the user intended collection handling remains open.

## Preservation

Source archives, PDFs, image folders, existing metadata, and the Flutter project remain intact. Conversion produces a separate artifact and must not overwrite user data. Complete page content remains available in the generated book; panel guidance describes views into those pages rather than authorizing deletion of material outside detected panels.

PDFs require particular care: their visible pages can combine multiple images, text, masks, and other graphics. Import must preserve the visible composition. The choice between page rendering and a proven equivalent image-extraction path belongs to the later design.

## Starting point

The current Flutter app selects one image, sends it to Gemini, displays the returned JSON, and overlays detected panel rectangles. Its model records `ymin`, `xmin`, `ymax`, and `xmax` on a 0-1000 scale. It has no explicit reading-order field or instruction in the prompt, no whole-book importer, and no comic-archive exporter. See [the service](../../lib/ai_service.dart), [the data model](../../lib/segmentation_models.dart), and [the screen](../../lib/comic_scanner_screen.dart).

This establishes a useful segmentation experiment. The interview confirmed retaining Gemini as the Rust CLI's v1 provider; the specific model, geometry representation, and metadata standard are not settled by the prototype.

## Representative input

The Downloads sample is `Parallel Truths Graphic Novel Anthology - Reader Nation.pdf`: 257 pages, approximately 119 MB, and an unencrypted PDF. A read-only inspection of representative pages found a cover, a composed contents page, and comic pages with inset or overlapping panels. It cannot safely be treated as a sequence of independent embedded images. Inspection did not identify panel guidance in its XMP metadata; this was not an exhaustive search of every PDF object. Detailed evidence and limitations are in [the local-input research](../research/notes/Portable%20comic%20panel%20metadata/local-inputs.md).

## Interview decisions and open questions

The first interview question is answered: Android is the first-version reading target. No additional reading platforms have been made first-version requirements.

The workflow decision is automatic conversion only. The user's clarification supersedes the earlier agreement to optional review and correction. The third question about choosing a correction interface is therefore withdrawn; no such interface is in v1 scope.

The fourth interview question is answered: after retries, panel-detection failures use whole-page fallback while the rest of the book completes. Affected pages must be clearly reported.

The fifth interview question is answered: retain Gemini with the user's API key, including sending page images to Google. Local processing and additional providers are deferred beyond v1.

The sixth interview question is answered: macOS is the initial CLI platform, with portable Rust code for possible later Linux and Windows support. Android remains the reading target.

The implementation plan should make the reader compatibility test and initial archive scope explicit. Actual CBC collection support remains unconfirmed; the core requested archive inputs are CBR and CBZ.

The requested [existing-solutions research](../research/existing-comic-conversion-solutions.md) identifies Pannello as the strongest existing pipeline to evaluate, with source and synthetic runtime evidence. It does not yet supply ACBF export or Gemini integration, and its preservation behavior needs changes.

The user authorized end-to-end validation using whichever existing tools work. The validation prototype may use Python and local detectors while proving the artifact and reader workflow. Keep the boundary between third-party dependencies and project-owned code explicit: existing libraries can remain dependencies, while code incorporated into this project must be ready for a Rust implementation. Prototype technology choices do not replace the intended Rust product or the agreed Gemini provider. Follow the [validation plan](../plans/0001-end-to-end-validation.md).

## What would demonstrate success

A representative book can be converted without changing its source, opened in a named compatible reader, and followed in a verified panel sequence while retaining complete-page access. The project's eventual compatibility claims should name the reader, platform, metadata format, and evidence tested. Specific acceptance criteria and milestones belong to the implementation discussion.
