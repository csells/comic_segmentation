# Comic panel end-to-end validation prototype

Disposable Python glue for validating full-page images + ordered ACBF metadata in
CBZ. This is not the product CLI, a production migration, or a detector. The
eventual application-owned pipeline/adapter is intended to be Rust; existing
libraries may remain dependencies.

The user requested automatic conversion only. No review or correction UI is
implemented. Visual inspection performed by the development team is validation,
not a product feature.

## Dependencies and scope

- Pannello `d4747266b5e8ac478168050f75c9ea71bba00e85` (AGPL-3.0-or-later), including its
  vendored Kumiko; this prototype calls the existing library, without copying its
  detector implementation. No model downloads or cloud calls occur here.
- Pillow for dimensions/known synthetic fixture; Python standard ZIP/XML libraries
  for packaging; Poppler `pdfinfo`/`pdftoppm` for composed PDF page rendering.
- `lxml` and the unmodified upstream Android `ACBFDocument` class for validation.
  Only unrelated constants for font discovery/platform are stubbed.

Current adapter contract is Pannello JSON: `total_pages`, `reading_direction`
(`ltr`/`rtl`), and ordered `pages` containing consecutive 1-based `page`, `image`,
and normalized ordered `panels` (`x,y,w,h`, each relative to page dimensions).
All image pages in the source tree must map exactly once; ambiguous basenames
are rejected. The first image is the cover and is not repeated in the body.

Existing output names are refused. New integration runs always allocate a fresh
scratch directory. Source PDF/archive SHA-256 is checked before and after;
every output image is compared against its staged input bytes. PDF conversion
renders complete pages at 150 DPI by default; it is not lossless PDF conversion.
The JSON manifest records source PDF page mappings, image hashes/dimensions,
exact output frame polygons, fallback reasons, and preserved auxiliary hashes.

Malformed geometry becomes a reported whole-page frame. Invalid page mappings
are fatal. Pannello's upstream low-confidence reasons are retained. Existing
ComicInfo and auxiliary bytes are preserved; original `.acbf` files are stored
under `source-metadata/*.acbf.original` so they cannot become a second active
metadata document. Existing catalog fields are **not** merged into the new ACBF;
the author is marked Unknown. Reader metadata precedence still needs a product
policy.

## Run

The commands below assume an isolated Python environment with Pannello/Pillow,
and a validation interpreter with lxml/Pillow. The integration runner prints its
fresh scratch directory and PID before work and reports page progress.

```sh
python -m unittest discover -s prototypes/comic_panel_e2e -p test_adapter.py -v
python -u prototypes/comic_panel_e2e/run_validation.py fixture
python -u prototypes/comic_panel_e2e/run_validation.py convert /path/to/book.pdf --pages 1,3,5,25 --jobs 2
python -u prototypes/comic_panel_e2e/run_validation.py convert /path/to/book.pdf --jobs 2
python -u prototypes/comic_panel_e2e/run_validation.py convert /path/to/book.cbz --jobs 2
python -u prototypes/comic_panel_e2e/run_validation.py convert /path/to/image-folder --jobs 2
```

To package detector JSON from any provider independently:

```sh
python prototypes/comic_panel_e2e/adapter.py PAGE_ROOT PANELS.json NEW_OUTPUT.cbz --title "Book title"
```

To check the authoritative ACBF 1.1 XSD and upstream Android parser:

```sh
python prototypes/comic_panel_e2e/verify_reader.py NEW_OUTPUT.cbz \
  --xsd '/path/to/ACBF/XML Schema/acbf-1.1.xsd' \
  --reader /path/to/ACBF-Viewer-for-Android/acbf/acbfdocument.py
```

Pinned validation sources: ACBF schema `e033e004e2897fe20ad09cbd649a8ba1d6b38d09`;
Android reader `1be5e700e793dd864828bbc48927bf28d2f43970`. Reader verification
creates a fresh unpacking directory and refuses an existing result JSON.
Neither schema validation nor this parser check exercises the Android UI.

## Limits discovered by executing the prototype

- ACBF's schema allows omitting `publish-info`, but the Android parser crashes
  without it. The adapter emits the node even when no publisher is known.
- Single-image books are explicitly rejected: ACBF 1.1 requires a body page in
  addition to its cover; silently duplicating the cover would break preservation
  of logical page count. This boundary needs a product decision later.
- Pannello gets the asymmetric synthetic four-panel page right. On the user's
  PDF page 25, it merges and splits real panels and does not flag the failure.
  All 257 pages convert structurally, but the local detector is not accepted for
  production accuracy by these results.
- The renderer emits JPEGs, and detector geometry is rectangular. Polygon
  segmentation, graceful corrupt-page recovery, retries/resume, packaging,
  resource limits, catalog merging, extraction security, and reader UI behavior
  are not implemented here. Archive extraction is for trusted local fixtures.
- RAR/CBR, CB7, CBT and damaged archives are inherited source paths, not exercised
  validation claims. This fixture generator currently uses a macOS system font.
- Scratch artifact links are machine-local and may disappear. `evidence/` retains
  text-only manifests and parser results. Selected CBZ copies are retained under
  the ignored `validation-artifacts/20261007-162937/` directory; no comic pages
  are tracked in Git. See the [handoff](../../specs/handoff-comic-panel-cli.md).

See [the measured research result](../../specs/research/e2e-converter-validation.md)
for commands, artifacts, timings, failures and remaining acceptance work.
