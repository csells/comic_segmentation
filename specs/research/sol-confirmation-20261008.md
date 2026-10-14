# Sol low confirmation — 2026-10-08

**Select Sol low, prompt v4, as the first-pass research default.** The extended
sample supports moving on from model shopping to full-book validation. It does
not establish that low reasoning alone delivers excellent bounds on every page.
Of twelve sampled pages, ten were usable directly, one needed automatic
pixel-based expansion, and one needed a stronger inference pass. Developer visual
inspection found those failures; automatic escalation remains unvalidated.

This follows the [four-page cost comparison](cost-quality-comparison-20261008.md).
Chris authorized the eight-page confirmation and general boundary refinement.
All requests reused the original page renders and shared $20 ledger. No manual
coordinates entered inference or replacement metadata. No Rust rewrite began.

## Confirmation and failures

Sol low v4 ran once on PDF pages 2, 6, 18, 54, 100, 175, 205 and 240. All eight
overlays and all 44 panel crops were inspected; the two whole-page compositions
were inspected in full. Scene counts matched saved Sol high: 1/7/6/10/5/6/10/1.
Matching counts did not establish correct boundaries.

| PDF page | Scenes | Visual assessment of low v4 |
| --- | ---: | --- |
| 2 | 1 | Appropriate whole-page front matter. |
| 6 | 7 | Separate scenes and insets, usable crops and order. |
| 18 | 6 | Separate scenes, complete associated content and usable order. |
| 54 | 10 | Dense layout recovered with usable crops and order. |
| 100 | 5 | Correct scenes/order; tight edges trim artwork. Failed bounds gate. |
| 175 | 6 | Separate scenes and border-breaking content retained in usable sequence. |
| 205 | 10 | Shared thought balloon clipped in the second crop; collar clipped in the ninth. Failed bounds gate. |
| 240 | 1 | Appropriate whole-page composition. |

**Correction to the earlier Sol-high review:** its saved v4 page 205 also clips
the shared thought balloon. The balloon has thought-dot chains into two scenes
and must remain complete in both guided crops. The earlier broadly favorable
page-205 assessment missed this defect and is superseded here. Higher reasoning
with the old prompt was not a complete fix.

Prompt v5 adds a general crop audit: complete shared balloons in each associated
scene, complete border-breaking subjects/accessories, and outer artwork borders.
Low v5 on pages 100/205 still trimmed page 100 and the shared balloon on 205,
although it recovered the collar. Both overlays were inspected; this rejected
experiment received no exhaustive crop acceptance and was not adopted globally.

Sol high v5 on page 205 recovered the shared balloon, complete collar and all ten
scenes. Its overlay and all ten ordered crops were inspected. The reaction inset
precedes the collar-removal background, then departure and the jump. Borderless
speed lines and overlapping insets mean enclosing rectangles include neighboring
fragments; those fragments are not additional detected scenes. This result is
usable for the reviewed sample. One targeted success does not prove an automatic
escalation policy or universal reliability.

## General dark-gutter refinement

`gutter_refine.py` v2 expands a near-correct model rectangle to image-derived
foreground bounds when all four corners establish a uniformly dark background.
A unique connected component must have at least 90% reciprocal rectangle
coverage, edges within 2% of page dimensions, at least 75% fill and at least 1%
of page area. The result is the union of the original rectangle and the component
plus two pixels. It never shrinks bounds, changes scene count/order or invents
missing scenes. Ambiguous and non-dark cases retain the original geometry.

The first version fixed four of five page-100 boxes. A regression fixture for an
offset thin panel failed before the reciprocal-coverage adjustment and passed
after it. All six synthetic tests pass inside the disposable VM. Running v2 on
all twelve saved low-v4 pages changed only the five boxes on page 100. A separate
JSON comparison confirms the other eleven pages are unchanged. All five refined
crops and the page overlay were inspected; the complete artwork is now present.
The first version, failed prompt experiments and original results remain saved.

This is a narrow geometry refinement, not a new detector. It cannot fix merged or
missing scenes, reading order, white gutters or shared balloons. Its favorable
result on one real page needs broader validation; six synthetic tests do not
establish corpus-level quality. Refinement records retain source-panel hashes,
pixel bounds before/after and `inference_calls: 0`. Copied generation usage is
historical and must not be counted as another paid request.

## Cost and decision

| New experiment | Calls | Reported-usage estimate | Generation time |
| --- | ---: | ---: | ---: |
| Low v4 confirmation | 8 | $0.095530 | 54.037 s |
| Low v5 boundary experiment | 2 | $0.026770 | 17.138 s |
| High v5 page 205 | 1 | $0.048820 | 52.170 s |
| Total | 11 | $0.171120 | 123.345 s |

These are conservative token-price estimates from the existing runner policy,
not billing receipts; timings exclude preflight, rendering and visual review.
The twelve-page low-v4 first pass totals $0.139760. The selected sample additionally
uses the high-v5 page-205 response and zero-cost pixel refinement, while rejected
experiments remain part of the actual research spend.

The durable ledger now has **$4.594361 used/held of $20**: $0.994361 estimated
reported usage plus unchanged $3.60 reservations for twelve unknown Gemini
outcomes. Remaining conservative allowance: $15.405639. Iteration totals are
40 successful OpenAI calls and 14 Gemini attempts (two responses). No new Gemini
calls or blind retries occurred. Keep the same ledger despite its legacy
`gemini-10usd-20261008.jsonl` filename.

Continue with low v4, preserving raw outputs, then the conservative refinement.
Visually inspect every page and ordered crop. Escalate only concrete failures;
retain which prompt/model resolved each. The user wants automatic conversion,
so developer review is evaluation work, never a proposed customer correction
workflow. Until a reliable automatic signal exists, do not claim that this
research selection is an automatic quality guarantee.

## Review artifact and evidence

The extended reader sample contains the original cover followed by PDF pages
2, 5, 6, 18, 25, 54, 100, 175, 205, 240, 254 and 256: 61 panel steps and three
whole-page compositions. Every final scene/crop/order was visually inspected.
Page 100 uses refined low v4; page 205 uses high v5; the other ten use low v4.
The cover is preserved from source and is not a thirteenth detector test.
Build 9 is live in [Panel Lab](https://csells-mac-mini--51996.getbb.app/) as
**Sol · 12 reviewed pages**. Prepared and published versions each passed 77
phone-sized navigation assertions and zero uncaught exceptions, including all
page overviews and 61 panel steps. Gallery and shared-balloon screenshots were
inspected. ZIP integrity, all 13 source-image byte matches, one cover and every
body-page frame count passed. This is desktop mobile emulation, not a new
physical-phone test. The initial build 8 filename contained digits and the
existing catalog validator rejected it; build 8 remains retained, while build 9
uses a valid filename without changing reader code. A first browser check also
hit a startup race; after confirming CDP readiness, checks ran normally.
All prior application/book files are byte-identical; only the catalog and added
book differ from build 7. Full-book quality is still open: 245 pages have no
OpenAI result. Twelve selected pages from one book are not a held-out multi-book
benchmark, and Chris's Astra approval is not approval of this new sample.

[Machine-readable evidence](evidence/segmentation-iteration-20261008/sol-confirmation-summary.json)
records individual request/source/output hashes, usage, timings and review scope.
Private evidence remains under ignored
`validation-artifacts/segmentation-iteration-20261008/` and VM153 `evidence/`:

- `openai-sol-low-v4-confirmation-20261008/`
- `openai-sol-low-v5-boundaries-20261008/`
- `openai-sol-high-v5-boundaries-20261008/`
- `openai-sol-low-v4-gutter-v2-{pilot,confirmation}-20261008/`
- `openai-sol-reviewed-12-20261008/` (per-page selection and provenance)
- `openai-sol-reviewed-12-book-20261008/` (new CBZ and publication manifest)
- `budget-after-sol-confirmation-20261008.jsonl` (exported ledger snapshot)
- `sol12-review-build9-20261008.tgz` (59,906,656 bytes; SHA-256
  `a4f0c7ead49eb5267a9f0f5541869986c682f6398efa81983d110f2c909e8365`)

The archive was hash-verified after export from VM153 to the separate Mac. It
retains the book, catalog, per-page selection, source probes, prepared/published
UI evidence and rollback unit. Task browser/preview services were stopped and
ports 9222/8081 confirmed closed; the review service remains on 8080. Headless
Chromium's absent desktop-DBus/DRM and sandbox startup diagnostics are retained;
desktop integration and hardware video are not used, and actual rendering and
navigation passed. No inference job or persisted credential remains.

Earlier v1 gutter runs are retained as `openai-sol-low-v4-gutter-{pilot,confirmation}-20261008`.
No source image, earlier response, old book or unrelated change was replaced.
