# Gemini to ACBF sample validation

Date: 2026-10-07. **The live API and CBZ metadata path work, but the four-page
sample does not pass a panel-detection quality gate.** Source page 25 merges two
visibly separate bottom panels; page 5 required whole-page fallback after service
errors. No detected box was manually corrected.

## Exact experiment

Used read-only, composed PNG renders of PDF pages **1, 3, 5, 25**, already present
in `/tmp/comic-panel-pdf-review.4MZwB2/`. All are 1027 × 1500 pixels. The sample
CBZ maps them, in that order, to `0001.png` through `0004.png`. SHA-256 checks in
the adapter verify that each archived PNG exactly matches its source image.
The original PDF, its images and the Flutter application were untouched. No
other PDF pages were processed.

Used official **google-genai 2.29.0**, Python 3.14, and Pillow 12.3.0 in a fresh
scratch environment. Requested and returned model: **`gemini-3.8-flash`**. The
working contract was `v1beta models.generateContent`, with JSON Schema, one
candidate, temperature 0, and a maximum of 8192 output tokens. No thinking override
or implicit SDK retry was used. This directly tests the supported generateContent
path; it does **not** validate Interactions. [Google API reference](https://ai.google.dev/api/generate-content),
[structured-output documentation](https://ai.google.dev/gemini-api/docs/structured-output).

The prompt requests ordered panels, including insets and overlapping regions,
upright orientation, and integer `[ymin,xmin,ymax,xmax]` bounds in 0–1000. Array
order is authoritative. Content in the image is explicitly treated as content,
not instructions. Covers/title pages return a complete-page box. Application
validation rejects out-of-range/zero-area geometry, wrong types, order mismatch,
non-upright coordinates and incomplete generation. Boxes are converted to ordered
normalized `x,y,w,h` for the existing adapter. [Coordinate convention](https://ai.google.dev/gemini-api/docs/image-understanding#object-detection).

## Observed requests and usage

| Source PDF page | Attempts | Result | Prompt tokens | Output tokens | Thought tokens | Total tokens |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 2 | HTTP 503, then whole-page detection | 1365 | 78 | 489 | 1932 |
| 3 | 1 | Whole-page detection | 1365 | 78 | 173 | 1616 |
| 5 | 2 | HTTP 503 twice; explicit whole-page fallback | Not reported | Not reported | Not reported | Not reported |
| 25 | 1 | Five ordered detected panels | 1365 | 228 | 1059 | 2652 |
| Reported total | **6** | **3 valid responses, 3 HTTP 503 errors** | **4095** | **384** | **1721** | **6200** |

Every successful response finished with `STOP`; no safety block or malformed
geometry occurred. The three 503 errors reported temporary high demand and no
token usage. Recorded attempt wall time totaled 58.855 seconds, including two
2-second retry waits. Actual billed currency and any usage on failed requests
were not provided and are not inferred from the reported tokens.

## What this proves and what fails

The live output passes the geometry/sequence contract and automatically produces
a full-page CBZ with embedded ACBF, including an explicit fallback reason in the
adjacent manifest. The cover and title-page classifications match visual
inspection. On source page 25, boxes 1–4 correspond to the first four panels in
plausible reading order. **Box 5 encloses both bottom panels instead of making two
frames.** Its upper boundary also crosses the neighboring panel area because the
lower row begins at unequal heights. This is valid rectangular metadata but an
incomplete guided-reading result. Source page 5's complex insets remain untested
by a successful Gemini response because both attempts returned 503.

The numbered overlays exist only as developer assessment evidence. They were not
used to change the output. The ACBF 1.1 schema and unchanged upstream Android
metadata parser both accepted the artifact, preserving all four images, their
order and exact frame lists `[1,1,1,5]`; see the
[parser evidence](evidence/gemini-e2e/flash-reader-check.json). Reader UI results
are owned by the separate Android validation; producing and parsing an archive
alone does not prove reader behavior.
This small sample establishes neither a production quality threshold nor full-book
cost, reliability, resume behavior or sustained service availability.

## Bounded Pro comparison: unavailable quota

One follow-up used exactly the same prompt/schema, source images for pages **5
and 25**, and 8192-token cap with **`gemini-3.1-pro-preview`**, in a separate
`pro-run/` directory. All four calls (one initial attempt and one retry per page)
returned HTTP 429 with **free-tier request and input-token quota limits of zero**
for `gemini-3.1-pro`. No model output, returned model version or usage was reported.
No quality comparison is possible: a model appearing in the model list does not
prove this project's entitlement to generate with it. No further model or live
requests were attempted. The Flash archive remains the reading artifact; the Pro
fallback-only result was not promoted over it. No API project or billing setting
was changed. Across both experiments, exactly **10 calls** were made: six Flash
and four Pro, with **6200 total reported tokens** from Flash's three successes;
usage for all seven failed calls was absent.

This exposed a prototype error: it treated every 429 as transient. A failing
offline test was added, then the classifier was fixed to stop on explicit zero
quota, daily quota exhaustion and retry delays beyond this small probe's wait
budget. Existing evidence preserves the four calls as they actually occurred;
the fix was verified offline, without spending another request. Production code
must retain this distinction so it does not turn account-wide failures into a
book full of fallbacks. [Captured quota evidence](evidence/gemini-e2e/pro-quota-report.json).

## Reproducible code and artifacts

- Code: [probe and contract](../../prototypes/gemini_panel_probe/README.md).
- Eight standard-library contract tests were first observed failing because the
  implementations did not exist, then passed after implementation. They cover
  y/x mapping, preservation of array order, invalid bounds/types/area, inconsistent
  order, whole-page extent, orientation/direction, generation completion, bounded
  source-page selection and nonretryable quota responses.
- Scratch environment: `/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/comic-gemini-e2e-fer6gndl/`.
- Run evidence beneath `run/`: `contract.json`, `report.json`, per-attempt response
  and status JSON, per-page validated JSON, `panels.json`, `pages/`, `overlays/`.
- Archive: `run/gemini-sample.cbz` and source-aware
  `run/gemini-sample.manifest.json`.
- Archive SHA-256: `4f6ef5f6856141a6f8d38b6f9f5e77ae624dadd15417bddd1df7f7db00848869`.
- Text-only measured reports, geometry, manifests and parser results are preserved
  in [evidence/gemini-e2e/](evidence/gemini-e2e/); private image bytes and full SDK
  responses remain in scratch.

Credentials were captured from Dashlane directly into the process and were never
written into these files. A copy of the sample CBZ is retained in the ignored
`validation-artifacts/20261007-162937/` directory; full SDK responses remain in
scratch and private images are not tracked in Git. The owned prompt, contract and mapping logic are small
enough to port to Rust; Google's SDK and established image/archive libraries were
used as dependencies, not reimplemented.
