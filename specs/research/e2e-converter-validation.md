# Converter-to-ACBF validation, 2026-10-07

The complete 257-page PDF now converts into a CBZ with full-page images and
embedded, ordered ACBF 1.1 frame metadata. Every output page image matches its
Poppler-rendered source bytes, the original PDF hash is unchanged, and both the
authoritative XSD and unmodified upstream Android metadata parser accept every
page/frame in order. **This establishes the format and conversion plumbing;
Pannello's local detector fails visual quality checks on real pages.** Android
installation, archive discovery, zoom/navigation and Gemini evaluation are
separate validation tracks, not implied by this parser result.

The user's direction is to validate with whichever existing tools work, then
implement application-owned code in Rust while retaining useful libraries as
dependencies. The [Python prototype](../../prototypes/comic_panel_e2e/README.md)
is intentionally separate from the Flutter application and is not a production
migration. It implements no optional review/correction feature. Development
artifact inspection below is verification, not part of the proposed user flow.

## Reused components and narrow adapter

- **Pannello 0.1.0**, pinned at
  [`d4747266b5e8ac478168050f75c9ea71bba00e85`](https://github.com/marcopiraccini/pannello/tree/d4747266b5e8ac478168050f75c9ea71bba00e85),
  supplies input/archive helpers, natural page ordering, existing Kumiko
  detection, normalized ordered JSON, and detector failure classifications.
  No detector code was reimplemented. Model fallback is explicitly `none`; this
  branch performs no cloud requests or model downloads. Pannello and its
  vendored Kumiko are AGPL; using the dependency remains a licensing choice.
- **Poppler** renders composed PDF pages. This preserves each complete page's
  visual composition; extracting individual embedded PDF images would not.
  Each page is rendered to JPEG at 150 DPI, then packaged byte-for-byte. This
  does not preserve the PDF's original vectors, embedded images or compression.
- **Python ZIP/XML plus Pillow** supply packaging, metadata serialization and
  dimensions. The owned adapter maps ordered normalized rectangles to bounded
  integer ACBF polygons, emits one cover followed by the remaining body pages,
  and places `metadata.acbf` at the ZIP root.
- **Authoritative ACBF 1.1 XSD**, revision
  [`e033e004e2897fe20ad09cbd649a8ba1d6b38d09`](https://github.com/ACBF-Advanced-Comic-Book-Format/ACBF/blob/e033e004e2897fe20ad09cbd649a8ba1d6b38d09/XML%20Schema/acbf-1.1.xsd),
  plus `lxml` provide schema validation. Geometry checks are separate because
  the XSD alone accepts malformed frame-point strings.
- **Android ACBFDocument**, revision
  [`1be5e700e793dd864828bbc48927bf28d2f43970`](https://github.com/ACBF-Advanced-Comic-Book-Format/ACBF-Viewer-for-Android/blob/1be5e700e793dd864828bbc48927bf28d2f43970/acbf/acbfdocument.py),
  runs unchanged on the extracted artifact. Only its unrelated `constants`
  module is stubbed (`default_font=''`, `PLATFORM='linux'`), as in the earlier
  research. All returned image names and frame polygons are compared in order.

The adapter refuses existing output paths, empty/inconsistent page manifests,
ambiguous or duplicate image mapping, unmapped images and source-tree symlinks.
Malformed geometry becomes a whole-page frame with a reason; Pannello's explicit
whole-page reasons also reach the manifest. It never silently drops a page or
guesses a structural page association.

The wrapper stages extraction independently instead of calling Pannello repack,
which had dropped metadata in earlier research. It retains ComicInfo and
auxiliary bytes, captures RTL before detection, and stores pre-existing ACBF as
`source-metadata/*.acbf.original` to avoid a second active ACBF. **Catalog fields
are preserved as source bytes, not merged into the generated ACBF**; the latter
currently labels the book author Unknown and uses the supplied title. Catalog
precedence and metadata merge policy remain product work.

## Executed results

| Case | Pages | Frames per page / total | Result |
|---|---:|---|---|
| Known asymmetric ordered fixture | 3 | 1, 4, 1 | XSD/parser pass; cover once, visibly numbered 1→2→3→4, empty-panel whole-page fallback. Geometry is supplied ground truth, so this isolates metadata/navigation from detection. |
| Same synthetic images through Pannello | 3 | 1, 4, 1 | XSD/parser pass; detector finds four intended asymmetric panels. |
| Existing synthetic CBZ with RTL + catalog + notes | 3 | 1, 4, 2 | XSD/parser pass; RTL retained; ComicInfo.xml and notes.txt byte hashes retained. |
| User PDF sample: source pages 1, 3, 5, 25 | 4 | 1, 1, 7, 5 | XSD/parser pass; 1.84 seconds; cover and contents whole-page fallbacks; visual segmentation failures below. |
| User PDF, all pages | 257 | 1,094 total | XSD/parser pass; 103.35 seconds total, 43.05 seconds detector; 48 reported whole-page fallbacks, zero detector exceptions. |

The full-run fallback count includes legitimate covers/splashes and is not a
measured error rate. Full-book accuracy was not manually annotated. Detector
confidence and absence of exceptions do not establish panel correctness.

The output CBZ is 75,361,608 bytes. The 257 pages correspond to one cover and 256
body pages. The reader returned every expected image and ordered polygon. Every
ZIP page image SHA-256 matches the staged rendered image. The full conversion
ran with two detector workers and per-page rendering/detection progress;
recorded launch PID was 23312, host session 92994, exit code 0. Its log remains
at `/tmp/comic-full-e2e-log.MKpd8P`.

| Integrity item | SHA-256 |
|---|---|
| Source PDF before and after sample/full conversion | `30d075d2bf54cdcd2401ccf905ab50a859779296e7afdbff404efd291f42cd32` |
| Full 257-page CBZ | `7fc2547e38a0a1c86c5d338378adabfb0ba5a551f7926da519f9057fa4fc66e7` |
| Four-page sample CBZ | `cdea8a4329408fd89246d445a6be78d953b42fa6d36e8dd3a160315f7017d667` |
| Corrected known-order synthetic CBZ | `78b79194060f980092d2f3fcdc2d0c7026a2b4c212a1b381c2595c0052a637bd` |

All source files and previously generated artifacts remain unchanged. Only new
scratch outputs and prototype/research files were written. The existing Flutter
source and `.vscode/settings.json` were not changed by this validation branch.

## Real-art findings

The sample selection covers the cover, contents, an irregular inset-heavy page,
and a more conventional comic page. Original rendered images and a temporary
detector-overlay contact sheet were visually inspected.

- **Source page 25:** six visually distinct panels, but Pannello emits five
  regions. The first spans both top panels; two middle-left regions split one
  natural panel vertically; the last spans both bottom panels. This is a clear
  qualitative failure. No low-confidence/fallback flag marks this page.
- **Source page 5:** the seven detected regions happen to equal the visually
  apparent panel count, but regions differ from the artwork: the lower-left
  panel is split vertically and the central inset is not separately isolated
  as its own matching region. Overlap between a large background panel's
  rectangular bound and an inset is not, by itself, classified as a failure;
  rectangles can naturally overlap on this composition. The problem is the
  actual panel mapping. This is visual diagnosis, not an annotated benchmark.
- Covers/contents correctly remain available as complete pages. This validates
  the requested whole-page reading behavior when no useful panel sequence is
  produced, without establishing when the detector will notice a failure.

**Conclusion for reuse:** keep Pannello as a useful conversion baseline and
existing detector comparator, but do not select its default detector for this
book based on synthetic success or the 1,094-frame batch count. Evaluate the
accepted Gemini path against the same rendered images before choosing the
production detection layer.

## Failures found and corrected

1. **Schema-valid XML rejected by the Android parser.** The first synthetic
   artifact omitted the XSD-optional `publish-info`; the unmodified parser
   failed with `'NoneType' object has no attribute 'find'`. Emitting an empty
   `publish-info` fixed the compatibility defect. A fresh fixture was created;
   the earlier failed artifact was preserved and was not counted as a pass.
2. **Single-page ACBF edge case.** The 1.1 schema requires at least one body
   page in addition to its cover. A single-image book would either be invalid
   or repeat its cover. The prototype now explicitly rejects it. The unit test
   first failed (`ValueError not raised`) and then passed with the guard.
3. **Geometry and mapping contracts.** Seven adapter tests pass after the
   initial red phase, covering ordered page/cover geometry, invalid geometry
   fallback, duplicate mapping, unmapped images, output collision preservation,
   original metadata retention and the single-image boundary. The tests use
   only newly created temporary fixtures. No failure was suppressed.

Tests and scripts: [adapter](../../prototypes/comic_panel_e2e/adapter.py),
[tests](../../prototypes/comic_panel_e2e/test_adapter.py),
[integration runner](../../prototypes/comic_panel_e2e/run_validation.py),
[reader checker](../../prototypes/comic_panel_e2e/verify_reader.py).

## Reproduction and retained evidence

The actual run used the previously isolated environment
`/tmp/comic-converters-research.PNH3Wl/venv` with Python 3.13.12,
Pannello 0.1.0, Pillow 12.3.0, NumPy 2.5.3 and OpenCV 4.14.0.94.
Parser verification used the existing Python 3.14.8 and lxml 6.1.1 interpreter.
No global packages were installed. See the prototype README for portable command
forms and source revisions; the current synthetic font path is macOS-specific.

Actual full-run command, launched from the repository root:

```sh
/tmp/comic-converters-research.PNH3Wl/venv/bin/python -u \
  prototypes/comic_panel_e2e/run_validation.py convert \
  '/Users/csells/Downloads/Parallel Truths Graphic Novel Anthology - Reader Nation.pdf' \
  --jobs 2
```

The runner always allocates a new directory. The sample command adds
`--pages 1,3,5,25`; source-to-output page correspondence is explicit in the
manifest. There is no provider/API use in these runs.

Durable text-only evidence is in
[prototype evidence](../../prototypes/comic_panel_e2e/evidence/):
[full manifest](../../prototypes/comic_panel_e2e/evidence/pdf-full.manifest.json),
[full reader result](../../prototypes/comic_panel_e2e/evidence/pdf-full.reader-check.json),
[sample manifest](../../prototypes/comic_panel_e2e/evidence/pdf-sample.manifest.json),
[known-order result](../../prototypes/comic_panel_e2e/evidence/known-order.reader-check.json),
and [metadata-preservation manifest](../../prototypes/comic_panel_e2e/evidence/metadata-preservation.manifest.json).

Machine-local deliverables, which can disappear when temporary storage is cleared:

- [Full CBZ](/private/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/comic-panel-e2e-convert-d3c3sbds/comic.cbz).
- [Four-page CBZ](/private/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/comic-panel-e2e-convert-w3e9cnd5/comic.cbz).
- [Synthetic known-order CBZ](/private/var/folders/6k/xzgngnms6jg4_z2l40y0_9vh0000gn/T/comic-panel-e2e-fixture-37q30lnw/known-order.cbz).

Selected CBZ copies were subsequently retained under the repository's ignored
`validation-artifacts/20261007-162937/` directory, with a local hash manifest.
No full comic, source page image or PDF is tracked in Git. Tracked manifests
contain paths, page mappings, frame geometry and hashes only. See the
[handoff](../handoff-comic-panel-cli.md) for the durable local artifact inventory.

## What this leaves open

Native Android UI acceptance, reader installability and reading usability are
tracked separately. These checks did not exercise Android FilePrepare, installed
application archive discovery, zoom, swipes or rendered frames. No blanket
"Android works" claim should be derived from the Python metadata parser.

CBR/RAR and damaged archive paths were not executed. The trusted-fixture wrapper
does not harden external extractors, limit decompression/resource use, implement
resume/retries, merge catalog metadata, or recover unrenderable PDF pages. It
does not implement arbitrary polygons, text recognition, production packaging
or provider abstraction. The prototype's direct output writes refuse collisions
but do not yet implement production atomic publication after all validations.
These are explicit prototype limits, not hidden product decisions.

The small owned XML/ZIP adapter and orchestration are candidates for Rust.
Existing Poppler/image/archive/XML libraries and any chosen detector should be
reused behind that boundary. Existing-library integration and the AGPL license
need deliberate selection; the experiment does not silently commit the eventual
product to Python, Pannello, or its default detector.
