# Format and reader-direction candidate — 2026-10-09

The candidate has now executed in isolated staging. The original preparation
notes below are updated with measured boundaries; existing Build10 and its saved
books remain untouched. New source changes after these frozen runs require their
own checks and do not inherit an E2E pass from a matching version label.

| Boundary | Current evidence |
| --- | --- |
| Import and packaging | Genuine compressed RAR5, CBZ and folder import byte/pixel parity passed; real RAR symlink rejection passed. Original bytes remained unchanged. [CBR evidence](cbr-container-validation-20261009.md). |
| Single-page schema | Cover-only ACBF passes the pinned1.1 XSD; an empty body fails. All frames remain on the sole image, with no duplicated page. |
| Rendered synthetic reader | Final build passes nine parser/archive/profile tests,29 navigation checks,12 actual-frame containment/centering checks, four thumbnail scheduler checks and eight prefetch lifecycle/error checks, with zero uncaught exceptions. Covers page-first, specified3→1→4→2 order, RTL, swipe/resume, portrait/landscape, whole-page fallback, single-page termination and corrupt-profile/bounds rejection. [Browser report](reader-v29-browser-20261009.md). |
| Actual converter across PDF/CBZ/CBR/folder | Eight real `auto_convert.main()` runs passed: one-page and three-page inputs for all four formats, with2 or6 exact provider-cache hits per run and zero new calls. Image bytes, actual outcomes and normalized ACBF/profile semantics match. These first three source pages all classify as whole-page compositions; this is transport/publication evidence, not panel-segmentation coverage. |
| Panelized current-policy format E2E | Prefix1–6 attempt completed four whole pages, then stopped on page5's uncached Astra ownership audit before HTTP/preflight dispatch or reservation. No prefix CBZ was emitted. Complete segmentation/escalation format parity remains unqualified. |
| Actual generated-archive playback | All eight actual outputs passed rendered playback across16 page views on the baseline and final readers: correct LTR, each whole page once, no invented next page, zero exceptions and unchanged archive hashes. Final source-page screenshot interiors match the reviewed baseline exactly. This covers whole-page transport, not segmentation quality. The browser report retains the artifact-specific evidence. |

Actual converter evidence is in VM153
`evidence/format-converter-e2e-20261009` and
`evidence/format-converter-prefix6-e2e-20261009`. Both retain frozen source hashes,
commands, actual traces, semantic comparisons and ledger checks. The first also
retains `frozen-source/` before later candidate recopy. Shared ledger, original
PDF and input bytes remained unchanged. Runtime cache lookup, escalation and
packaging were real; only new reservations and network dispatch were disabled.
See the [closure protocol](spike-closure-20261009.md) for the remaining gates.

The off-VM export is
`validation-artifacts/segmentation-iteration-20261008/format-converter-e2e-20261009.tgz`,
25,861,990 bytes, SHA-256
`34d763f049103993d905414242586bac7d1343490cf8632aa1d99b5d3df46ba8`.
All386 archive members were fully read;385 manifest entries matched byte counts
and SHA-256. It includes exact frozen source, harnesses, both runs, generated
CBZs, genuine CBR inputs and copied ledgers. Redundant prepared page copies are
excluded; original PDF and verified render-cache bytes remain in the retained
prior backup chain. The six-page attempt reused nine complete provider responses
before the denied source-audit preflight; it created no new ledger reservation.

Follow-up single-page schema check did execute in VM153: a cover-only document
passes the pinned ACBF 1.1 XSD; an empty `<body/>` fails because it lacks a page.
Evidence is `evidence/single-page-validation-20261009/single-page-schema-check.json`.
Candidate adapter now omits the body for one source page and preserves all frames
on that page, without duplicating its artwork. The web parser accepts this form.
The pinned older Android parser assumes a body exists, so single-page output is
qualified only for our web profile until Android compatibility is revisited.
The rendered single-page control passed; Android compatibility remains deferred.

The converter permits a single imported page or a single `--pages` selection.
`all-page-counts.json` and summary `panel_counts` include every source page;
`panel_steps` sums all panels, including any on the first image. Historical
`counts.json` remains body-only for the existing test harness, and
`body_panel_steps` labels that narrower count. No existing Build 10 artifact is
rewritten. The single-page browser control shows its full overview followed
by four metadata frames and remains on that sole page at the end.

`import_format.prepare_publication_image(source, destination_stem, originals_root,
source_locator=...)` returns a prepared page record. Upright JPEG/PNG keep exact
source bytes; BMP/GIF/WebP stills and EXIF-oriented images become upright PNG.
Transformed originals are retained beneath `source-auxiliary/original-images`
with `.original` suffixes so the packaging adapter cannot count them as pages.
The record retains original SHA-256, format, dimensions, EXIF orientation,
publication transforms, preserved-original path and publication hash/dimensions.
Animation/multipage images explicitly fail before an output is written. Existing
output collisions and source symlinks are rejected. No image or source is edited
in place. This handles publication compatibility, not general color-management or
hostile-image qualification.

The candidate converter replaces each folder/archive image-copy step with this
helper, using `pages / f'{ordinal:04d}'` as destination stem, and includes it in
immutable run source hashes. Detection sees upright publication geometry with a
recorded JPEG analysis copy when needed. Existing LTR JPEG inputs retain their
bytes and legacy prompt-v6 path when direction is explicit. Analysis-image
resume/provenance and predecessor-context changes are separately tested; the
four-format replay above exercised the preserved JPEG path.

The official [pinned ACBF 1.1 schema](https://github.com/ACBF-Advanced-Comic-Book-Format/ACBF/blob/e033e004e2897fe20ad09cbd649a8ba1d6b38d09/XML%20Schema/acbf-1.1.xsd)
and [current schema](https://github.com/ACBF-Advanced-Comic-Book-Format/ACBF/blob/main/XML%20Schema/acbf-1.1.xsd)
have no reading-direction element. Candidate packaging therefore keeps valid
ACBF and writes optional `panel-reader.json` containing format/version,
`reading_direction` and SHA-256 of the exact `metadata.acbf` bytes. This is our
reader profile, **not standard ACBF direction support**. Existing source profiles
are preserved as auxiliary bytes. The reader validates exact fields, version,
size, direction and metadata hash before using it; absence retains the historical
LTR default. A separate profile resume identity prevents an older direction
preference overriding a newly published profile. XML frame sequence is never
sorted or reversed.

Pinned [PanelView `openBook`](https://github.com/wenn-id/panelview/blob/ba86994fd8b8c99b62e960bccbeb51a576772f03/reader.js)
already propagates `book.readingDirection` into state and uses it for navigation;
no renderer patch is needed for that behavior. Candidate browser tests add exact
profile binding, legacy compatibility, RTL state, left-tap advancement, right-tap
previous and unchanged panel order. These are direction-transport controls, not
evidence that an LTR detector prompt segments native RTL comics correctly.

Run only in the disposable candidate VM, adjusting source prefixes:

```sh
geometry-venv/bin/python -m unittest discover -s candidate-source/panel_quality_probe -p test_import_format.py -v
geometry-venv/bin/python -m unittest discover -s candidate-source/comic_panel_e2e -p test_adapter.py -v
geometry-venv/bin/python candidate-source/web_panel_reader/make_fixtures.py candidate-fixtures --adapter-directory candidate-source/comic_panel_e2e
geometry-venv/bin/python candidate-source/web_panel_reader/build.py upstream candidate-fixtures candidate-build
```

Validate both stored controls against the pinned ACBF XSD/parser. Serve only the
fresh build on a separate preview port, then run `browser_check.py CDP_URL
NEW_EVIDENCE_DIR PREVIEW_URL ABSOLUTE_CANDIDATE_FIXTURES_DIR`. The parser suite now
expects all newly generated fixtures. The bounds fixture updates its companion
hash after intentional XML corruption so the bounds test still reaches image
validation. The mismatched-profile fixture tests the independent binding failure.
No model key or paid call is needed for these checks.

Libarchive's pinned [RAR test source](https://github.com/libarchive/libarchive/blob/v3.7.4/libarchive/test/test_read_format_rar.c)
and [small real RAR fixture](https://github.com/libarchive/libarchive/blob/v3.7.4/libarchive/test/test_read_format_rar.rar.uu)
are accessible with their source notice, but the fixture contains text and a
symlink, not comic images. It validated intentional rejection of nonregular
members. A separate genuine image-bearing compressed RAR5 fixture has now passed
import parity, and real RAR5 containers holding the exact original rendered PDF
pages passed actual cached conversion as described above. No fixture was
extracted or executed on the host for this work.
