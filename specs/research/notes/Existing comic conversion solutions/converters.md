# Existing comic conversion solutions

Research date: 2026-10-07. Scope: existing automatic tools taking archives, PDFs, or page images toward a full-page CBZ with ordered panel metadata. This is reuse research, not an implementation plan. The accepted Rust, Gemini, macOS-first, automatic-only direction remains unchanged pending discussion.

## Is there an existing complete converter we should adopt?

### Takeaway

**Pannello is the strongest working near-match found: extend or wrap it, rather than copy its entire pipeline.** It already normalizes inputs, detects ordered panels locally, and produces a full-page CBZ, but stores panels in a KOReader JSON sidecar. An ACBF exporter and preservation fixes remain necessary. No inspected tool demonstrated the complete requested automatic, preservation-aware, embedded-ACBF workflow as shipped.

### Cited Findings

| Tool | Verified input and output | Reuse classification |
|---|---|---|
| **[Pannello](https://github.com/marcopiraccini/pannello)** | CBZ, CBR, CB7, CBT, PDF, image folders; optional repacked full-page CBZ plus ordered normalized JSON sidecar. Kumiko by default, optional local YOLO or Magi. | **Extend/wrap candidate.** Closest existing pipeline; no ACBF export. |
| **[Panelizer](https://github.com/hummat/panelizer)** | CBZ/ZIP, PDF, single image; classic CV and optional YOLO; custom JSON and preview server. Project explicitly archived at early prototype stage. | **Borrow/reference.** Larger human-in-loop/PWA scope, no ACBF export. |
| **[Kindle Comic Converter](https://github.com/ciromattia/kcc)** | Archives, PDF, image directories to CBZ and ebook formats. Runs on macOS, Windows, Linux. Kindle Panel View is emitted in Kindle XHTML, not ACBF. | **Reuse conversion knowledge; not requested panel exporter.** |
| **[AI Comic Panel Extractor](https://github.com/ehsanx/Comic-Panel-Extractor)** | CBZ/PDF to CBZ containing full-page images interleaved with cropped-panel image pages. | **No fit for metadata contract.** An ordinary image-sequence workaround. |
| **[C.A.P.E.](https://github.com/CodeMinion/C.A.P.E)** | OpenCV detector and Electron editor, one `.cpanel` JSON file per page; separate cropped-image extraction. | **Reference.** Custom format, editorial workflow, no evidenced ACBF path. |
| **[Comic Smart Panels](https://github.com/zoran123456/Comic-Smart-Panels)** | CBR/CBZ manual panel creator and WPF reader; `.cpd` JSON, `.cpr` projects, .NET Framework 4.5. | **No fit for automatic macOS v1.** Manual authoring and different metadata. |

- Pannello declares version 0.1.0, Python >=3.9, and base NumPy/OpenCV/Pillow/Requests dependencies. Model support is optional; base installation needs neither Torch nor a cloud API. — [Pinned package definition](https://github.com/marcopiraccini/pannello/blob/d4747266b5e8ac478168050f75c9ea71bba00e85/pyproject.toml)
- Source revisions inspected: Pannello `d4747266b5e8ac478168050f75c9ea71bba00e85`, 2026-08-13; Panelizer `602414714c0c61fa5ae2e8021d3a358d326e29a7`, 2026-07-05; KCC `55342bd4f90dfdeb065fa8d5a6f4935ffd2da69f`, 2026-09-29; Comic Panel Extractor `37dd209098b7cffea7c083d4f97376acd3d42046`, 2026-03-01. These are repository commit dates, not claims of sustained maintenance or latest public releases. — [Pannello revision](https://github.com/marcopiraccini/pannello/commit/d4747266b5e8ac478168050f75c9ea71bba00e85), [Panelizer revision](https://github.com/hummat/panelizer/commit/602414714c0c61fa5ae2e8021d3a358d326e29a7), [KCC revision](https://github.com/ciromattia/kcc/commit/55342bd4f90dfdeb065fa8d5a6f4935ffd2da69f), [Extractor revision](https://github.com/ehsanx/Comic-Panel-Extractor/commit/37dd209098b7cffea7c083d4f97376acd3d42046)
- C.A.P.E.'s documented `.cpanel` schema uses pixel coordinates; its README declares ISC. Comic Smart Panels declares GPL-2.0 and documents manual vector drawing with percentage positions. Neither format is ACBF. — [C.A.P.E. README](https://github.com/CodeMinion/C.A.P.E#metadata-structure), [Comic Smart Panels README](https://github.com/zoran123456/Comic-Smart-Panels)

### Inferences

- The missing ACBF serialization is a bounded adapter problem; archive preservation, page ordering, safe output placement, reader integration, and detector suitability still make this more than a trivial file-extension change.
- Wrapping Pannello would retain Python/OpenCV runtime dependencies. A Rust-only distribution would require a different integration choice or port; this research does not silently replace the user's Rust or Gemini decisions.
- Pannello could be a baseline and regression comparator even if the product stays Rust plus Gemini. Its demonstrated automatic pipeline eliminates any need to invent a first detector merely to establish feasibility.

### Gaps

- Searches cannot prove that no exact-match converter exists. Queries covered ACBF automatic detection/generation, CBZ panel metadata conversion, Kumiko integration, Panelizer, comic2panel, comics2reader, ACV automation, and related GitHub projects.
- Comics2Reader appears to be an older image/ebook converter; no maintained primary repository or automatic panel-metadata exporter was established. It is not a recommended reuse dependency.
- Separate research covers ACBF Editor/Krita/Peruse and detector libraries; this note does not repeat their full evaluations.

## What specifically can Pannello supply, and what must change?

### Takeaway

The detector-to-JSON boundary is usable today and the repack pipeline runs on this Mac. **Do not adopt the CLI unchanged for a real library:** repack drops existing metadata, can lose detected RTL direction, and output creation lacks collision refusal.

### Cited Findings

- Core contracts: naturally sort recognized image paths; skip `__MACOSX` and `._` files; retain image pages including covers; use 1-based page numbers; serialize ordered rectangles as normalized `x,y,w,h` rounded to four decimals. JSON lacks page dimensions. Repack renames images `0001`, `0002`, etc., preserves their bytes, and writes only images. Detection exceptions and unsuitable geometry can collapse to a full-page rectangle. — [Pinned core implementation](https://github.com/marcopiraccini/pannello/blob/d4747266b5e8ac478168050f75c9ea71bba00e85/pannello/core.py)
- Core system dependencies are `file` for format probing, `unrar` for RAR, `7z` for 7z, `tar` for TAR, and Poppler `pdftoppm` for PDFs. PDFs are rendered to JPEG at configurable DPI, default 150. ZIP needs no external extractor. — [Pinned extraction functions](https://github.com/marcopiraccini/pannello/blob/d4747266b5e8ac478168050f75c9ea71bba00e85/pannello/core.py#L45-L99)
- CLI repacks first and then calls `core.generate()` on the new archive; `--rtl` or `--ltr` overrides direction. Its help advertises optional preview/review paths, but these are not required for conversion. — [Pinned CLI](https://github.com/marcopiraccini/pannello/blob/d4747266b5e8ac478168050f75c9ea71bba00e85/pannello/cli.py)
- Default optional YOLO weights come from `mosesb/best-comic-panel-detection`; alternatives include a Manga109 preset, local `.pt`, or Hugging Face model. Its device choice is CUDA when available, otherwise CPU; no Apple MPS branch is present. — [Pinned model adapter](https://github.com/marcopiraccini/pannello/blob/d4747266b5e8ac478168050f75c9ea71bba00e85/pannello/model.py)
- Pannello declares AGPL-3.0-or-later and vendors Kumiko, itself AGPL. Optional Ultralytics is AGPL. Its NOTICE labels default YOLO weights Apache-2.0 and describes Magi as non-commercial; upstream weight-license verification in the detector research takes precedence over this downstream summary. **Do not call the whole stack permissively licensed.** — [Pinned NOTICE](https://github.com/marcopiraccini/pannello/blob/d4747266b5e8ac478168050f75c9ea71bba00e85/NOTICE), [Package license declaration](https://github.com/marcopiraccini/pannello/blob/d4747266b5e8ac478168050f75c9ea71bba00e85/pyproject.toml)
- Maintainer claims about detection quality and CPU timing are not independent benchmarks. The README discusses undetectable subtle boundary errors, so a geometrically plausible grid is not proof of a correct reading experience. — [Pannello limitations and fallback discussion](https://github.com/marcopiraccini/pannello#low-confidence-pages-and-the-automatic-model-fallback)
- Local synthetic testing reproduced `ComicInfo.xml` direction loss: direct detection returned RTL, repack returned LTR, and repacked ZIP entries omitted both metadata and auxiliary notes. Existing source inputs remained byte-identical; generated CBZ/folder page images were also byte-identical to originals. — [Reproducible smoke report](pannello-smoke-report.json), [Fixture and execution script](pannello-smoke.py)

### Inferences

- Candidate adaptation work is explicit: obtain actual page dimensions, map normalized rectangles into ordered ACBF pixel polygons, retain page association/order, embed ACBF alongside the unchanged page images, preserve source metadata/auxiliary assets as required, and validate against the actual Android reader.
- **Rust/Gemini effort boundary:** there is no existing Gemini backend or documented provider plug-in interface in the inspected package. The CLI offers `--repack-only` to skip detection, and Python exposes separate `extract_archive`, `list_pages`, `repack`, `generate`, and normalization functions. `generate()` selects Kumiko/model/Magi through fixed parameters; lower-level `detect_pages_model(..., engine=...)` accepts an engine object, but this is an internal seam rather than a CLI provider contract. Thus the practical existing choices are Python pipeline extension, a Rust subprocess wrapper with Python runtime, or selective reuse/reference while retaining Rust/Gemini. None is a ready-made Rust/Gemini end-to-end implementation. — [CLI choices and skip-detection path](https://github.com/marcopiraccini/pannello/blob/d4747266b5e8ac478168050f75c9ea71bba00e85/pannello/cli.py), [Core callable functions](https://github.com/marcopiraccini/pannello/blob/d4747266b5e8ac478168050f75c9ea71bba00e85/pannello/core.py)
- The direction-loss result follows from repack dropping `ComicInfo.xml` before detection reads metadata. Capturing direction first or carrying metadata would address that class of issue; no product fix was made here.
- Any wrapper should stage output in a fresh work directory and publish a new non-colliding result. This is necessary because Pannello writes output JSON and CBZ in write mode; only the exact input-CBZ filename receives a `.pannello.cbz` alternative. Re-running can replace generated output. — [Core output paths](https://github.com/marcopiraccini/pannello/blob/d4747266b5e8ac478168050f75c9ea71bba00e85/pannello/core.py#L814-L854)
- Preserve original page composition for PDF input by rendering, as Pannello does, rather than assuming every embedded PDF image is a complete page.
- Pannello's tiled, disjoint rectangular zoom regions are a product policy. ACBF can represent more varied panel shapes; adopting Pannello's geometry policy should be a conscious choice, not confused with an ACBF requirement.

### Gaps

- No user comic was processed, no real-art accuracy comparison was performed, no paid API was called, and no YOLO/Magi weights were downloaded. The easy synthetic pages do not establish performance on the user's comic.
- CBR, CB7, CBT, nested path edge cases, damaged files, output collision behavior, and resource exhaustion were source-inspected rather than exercised. No Android UI compatibility claim follows from this test.
- A generic ACBF adapter was not implemented; this remains research only.

## What was actually exercised, and why are the other converters weaker fits?

### Takeaway

Pannello passed four tiny, fully local macOS smoke runs using synthetic content. The other tools show useful existing work but deliver different artifacts: custom JSON, Kindle magnification markup, or additional cropped image pages.

### Cited Findings

- **Observed test environment:** macOS 26.6.2 arm64, Python 3.13.12, Pannello 0.1.0 pinned above, OpenCV 4.14.0.94, NumPy 2.5.3, Pillow 12.3.0; dependencies installed only in a fresh scratch virtual environment. Existing `/opt/homebrew/bin/pdftoppm` was used. Three 800×1160 synthetic pages were made: blank cover, four-panel grid, two-panel grid. — [Smoke report](pannello-smoke-report.json), [Dependency versions](pannello-smoke-requirements.txt), [Script](pannello-smoke.py)

| Synthetic run | Exit | Output panel counts | Output form | Important observation |
|---|---:|---|---|---|
| CBZ direct | 0 | 1, 4, 2 | JSON only | Read RTL from source XML; naturally sorted page1/page2/page10. |
| CBZ `--repack` | 0 | 1, 4, 2 | 3 PNGs in CBZ + JSON | Exact image bytes retained; XML and notes dropped; switched to LTR. |
| PDF `--repack` | 0 | 1, 4, 2 | 3 rendered JPEGs in CBZ + JSON | All rendered pages retained, blank cover uses full-page fallback. |
| Folder `--repack` | 0 | 1, 4, 2 | 3 PNGs in CBZ + JSON | Exact image bytes retained. |

All table observations are recorded in the [smoke report](pannello-smoke-report.json). No output contained embedded ACBF. The blank page yielded `{x:0,y:0,w:1,h:1}` and a logged fallback notice.

- **Reproduction:** copy `pannello-smoke.py` into a fresh temporary directory as `smoke.py`, and copy `pannello-smoke-requirements.txt` alongside it; clone Pannello into its `pannello/` child; check out the pinned revision; create a `venv/`; install that checkout with the recorded dependency versions as constraints; run `venv/bin/python smoke.py`. This retains the observed OpenCV 4.14.0.94 instead of allowing dependency resolution to drift. Poppler must already be available for the PDF run. The script deliberately creates a fresh `fixtures/` and separate output directories, hashes source inputs, and writes `smoke-report.json`. — [Complete test script](pannello-smoke.py), [Recorded dependency versions](pannello-smoke-requirements.txt)

```sh
# Run only in a newly created scratch directory containing smoke.py
# and pannello-smoke-requirements.txt copied from these research notes.
git clone https://github.com/marcopiraccini/pannello.git pannello
git -C pannello checkout d4747266b5e8ac478168050f75c9ea71bba00e85
uv venv venv
uv pip install --python venv/bin/python -c pannello-smoke-requirements.txt ./pannello
venv/bin/python smoke.py
```

- **KCC:** `comic2ebook.py` creates `app-amzn-magnify` XHTML regions with top/bottom/left/right or four quadrant ordering when Kindle panel view is enabled. CBZ export instead ZIPs the processed image folder, optionally retaining ComicInfo. `comic2panel.py` splits long images into shorter image files. This is neither general semantic panel detection nor ACBF serialization. ISC license. — [Pinned Kindle markup](https://github.com/ciromattia/kcc/blob/55342bd4f90dfdeb065fa8d5a6f4935ffd2da69f/kindlecomicconverter/comic2ebook.py#L153-L220), [CBZ output path](https://github.com/ciromattia/kcc/blob/55342bd4f90dfdeb065fa8d5a6f4935ffd2da69f/kindlecomicconverter/comic2ebook.py#L2050-L2062), [Image splitter](https://github.com/ciromattia/kcc/blob/55342bd4f90dfdeb065fa8d5a6f4935ffd2da69f/kindlecomicconverter/comic2panel.py), [License](https://github.com/ciromattia/kcc/blob/55342bd4f90dfdeb065fa8d5a6f4935ffd2da69f/LICENSE.txt)
- **Comic Panel Extractor:** its desktop Python path renders PDFs at 300 DPI, detects panels with thresholding/morphology/contours, re-encodes each complete page as JPEG quality 90, then appends cropped-panel JPEGs as additional CBZ pages. No ACBF or geometry metadata is written. The repository carries GPLv3; precompiled distribution is Windows-focused, source uses Tkinter/OpenCV/PyMuPDF. “AI” in the name does not mean a learned model or paid API is required. — [Pinned processing implementation](https://github.com/ehsanx/Comic-Panel-Extractor/blob/37dd209098b7cffea7c083d4f97376acd3d42046/desktop_app.py#L126-L183), [Detector implementation](https://github.com/ehsanx/Comic-Panel-Extractor/blob/37dd209098b7cffea7c083d4f97376acd3d42046/desktop_app.py#L78-L115), [License](https://github.com/ehsanx/Comic-Panel-Extractor/blob/37dd209098b7cffea7c083d4f97376acd3d42046/LICENSE)
- **Panelizer:** implemented extraction supports CBZ/ZIP, PDF, and single-image inputs; the CLI serializes `BookData` as JSON with page sizes, panel IDs, and explicit order. It uses PyMuPDF and OpenCV, optional Torch/Ultralytics. Its top-level MIT declaration does not establish permissive licensing of every dependency or borrowed detector component. — [Pinned extraction code](https://github.com/hummat/panelizer/blob/602414714c0c61fa5ae2e8021d3a358d326e29a7/src/panelizer/extraction/extractor.py), [JSON export](https://github.com/hummat/panelizer/blob/602414714c0c61fa5ae2e8021d3a358d326e29a7/src/panelizer/__main__.py#L205-L233), [Dependency declaration](https://github.com/hummat/panelizer/blob/602414714c0c61fa5ae2e8021d3a358d326e29a7/pyproject.toml)

### Inferences

- Cropped-panel CBZs can supply sequential mobile reading in many ordinary readers, but they duplicate content and encode panels as pages. They do not meet the current requirement of preserving complete pages plus portable panel metadata.
- KCC is a mature adjacent converter and useful reference, but using its “Panel View” terminology as evidence of ACBF support would be misleading.
- An existing detector baseline should be compared with Gemini on representative pages before choosing whether to replace, augment, or merely benchmark against the accepted Gemini route. That comparison is a future decision, not evidence that one is already superior.

### Gaps

- No KCC, Panelizer, C.A.P.E., or Comic Panel Extractor executable was exercised. Their classification comes from source and project documentation.
- The archived Panelizer README includes comparative claims about other tools (accuracy, licenses, maintenance) that were not adopted as independent evidence. In particular, any model-license conclusion must come from the actual upstream model license.
- Automatic Android readers such as Chika may bypass preprocessing entirely, but that is a different product choice and needs reader-specific investigation; discovering them does not establish ACBF export support.
