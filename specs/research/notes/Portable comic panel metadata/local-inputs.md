# Local project and comic input constraints

## What does the current project establish?

### Takeaway

The project is a single-image Gemini segmentation experiment. Whole-book import, panel reading order, and export are new requirements, not capabilities to assume already exist.

### Cited Findings

- The screen picks one image from gallery or camera, reads its bytes, calls `segmentPage`, and displays a bounding-box overlay and raw response. It contains no archive-import or book-export flow. Observed 2026-10-07. [Local Flutter screen](../../../../lib/comic_scanner_screen.dart)
- `AIService` uses Google's provider through `dartantic_ai`, selecting `gemini-3-pro-preview`. Its prompt requests all panel bounding boxes as integers on a 0-1000 scale, ordered within a box as `ymin, xmin, ymax, xmax`; it does not tell the model to emit panels in reading order. [Local service](../../../../lib/ai_service.dart)
- `Panel` has only four rectangle coordinates. `ComicPageSegmentation` has a list of panels; there are no explicit order, polygon, confidence, page identity, or source-dimension fields. Array position exists but has no documented reading-order semantics. [Local model](../../../../lib/segmentation_models.dart)
- The README describes panel detection and visual overlays and says the Flutter app was tested on macOS and Web. That statement is about this prototype, not prospective readers or a Rust CLI. [Local README](../../../../README.md)

### Inferences

- The prototype's normalized rectangles can inform a future segmentation contract, but simply copying them into an archive would leave reading sequence unspecified.
- Reading order must be explicit in the future model or established by a documented ordering contract. Layouts with insets and overlapping regions make a universal top-to-bottom sorting shortcut questionable.
- Provider choice, retries, cost limits, restart behavior, coordinate validation, and correction workflows remain design questions; the inspected code does not settle them.

### Gaps

- No Gemini calls were made and no segmentation accuracy assessment was conducted. Model quality on the sample remains unmeasured.
- No existing whole-book outputs or reader compatibility tests were found in the inspected `lib` files and README. This was a targeted source review, not a claim about every file or historical branch.

## What does the Downloads PDF imply for import?

### Takeaway

The sample is a composed PDF, not a reliable one-image-per-page container. A general importer must preserve the rendered page; extracting every embedded image and calling each one a comic page would omit or fragment content.

### Cited Findings

- Local `pdfinfo` reports 257 pages, 119,103,854 bytes, PDF 1.6, no encryption, tagged content, an AcroForm, and an XMP metadata stream. The default page size shown is 541.417 by 790.866 points. Inspection date: 2026-10-07. [Local sample PDF](</Users/csells/Downloads/Parallel Truths Graphic Novel Anthology - Reader Nation.pdf>)
- `pdfimages -list` shows CMYK JPEG2000 images, grayscale images, and transparency masks. Page 2 has multiple image objects and associated masks; page 3's listed raster content is only a small 365 by 32 image and mask. [Local sample PDF](</Users/csells/Downloads/Parallel Truths Graphic Novel Anthology - Reader Nation.pdf>)
- Rendering and visually inspecting pages 1, 3, 5, and 25 showed a cover, a complete contents/credits page, and comic pages with irregular, inset, or overlapping panels. Page 3's visible text and design are therefore not represented by its small embedded raster image. The four images were rendered locally into a fresh temporary directory outside the repository; no source file was changed. [Local sample PDF](</Users/csells/Downloads/Parallel Truths Graphic Novel Anthology - Reader Nation.pdf>)
- `pdfinfo -meta` shows Adobe/InDesign provenance, document identifiers, dates, and PDF production metadata. No panel descriptions were identified in that XMP output. This does not prove that no other PDF object could contain additional information. [Local sample PDF](</Users/csells/Downloads/Parallel Truths Graphic Novel Anthology - Reader Nation.pdf>)
- Poppler's image-extraction documentation distinguishes embedded images and native JPEG/JPEG2000 extraction. Image extraction produces image objects rather than complete page renderings. [Poppler source manual](https://skia.googlesource.com/third_party/poppler/+/master/utils/pdfimages.1)
- MuPDF's rendering example produces a page pixmap using a transform and a target color space. Its `PDFPage.toPixmap` documentation additionally exposes page-box, usage, and annotation/widget rendering choices. These illustrate the controls a page-rendering import contract may need; they are not a library selection. [MuPDF rendering example](https://mupdf.readthedocs.io/en/1.28.5/cookbook/c/example.html), [MuPDF PDFPage API](https://mupdf.readthedocs.io/en/1.28.0/reference/javascript/types/PDFPage.html)

### Inferences

- A full-page rendering path is necessary for broad PDF coverage. A future extraction optimization should only be used when it is demonstrably equivalent to the visible page, including orientation, clipping, masks, overlaid text, and other content.
- The output page dimensions and orientation must be finalized before panel coordinates are attached, or coordinates must be transformed consistently. Metadata describes the images stored in the CBZ, not an unrelated PDF coordinate system.
- The presence of both CMYK imagery and composed pages makes visual comparison necessary when later selecting color conversion and rasterization settings. Rendering DPI, output image format, and quality are unapproved implementation choices.
- Covers and contents pages need a defined whole-page treatment. They should not disappear just because they lack ordinary comic panels.
- Inspection supports retaining complete pages and treating panel regions as reading guidance. It does not justify cropping away anything outside detected regions.

### Gaps

- Only four pages were visually inspected. No claim is made that all 257 pages share the same geometry, image structure, or panel style.
- The PDF's form fields, structure tree, and every object dictionary were not exhaustively inspected for panel metadata. The limited XMP inspection found none.
- No output conversion, archive generation, cloud upload, or AI analysis of the user's PDF was performed.
- There is no measured quality, speed, memory, or output-size comparison yet. Selecting Rust crates or render engines belongs to the later implementation plan.

## Which input terms and preservation rules need to remain distinct?

### Takeaway

CBR and CBZ are the intended ordinary comic-archive inputs; CBC is a separate collection wrapper and should not be silently treated as a spelling variant. Import ordering and safe conversion need a clear contract, independent of panel-detection technology.

### Cited Findings

- CDisplayEx's official input settings map CBR, CBZ, CB7, and CBT to RAR, ZIP, 7z, and TAR archives respectively. The same documentation treats opening a folder of images and opening PDFs as separate capabilities. This source is used only for archive terminology, not as an OSS-reader recommendation. [CDisplayEx settings](https://www.cdisplayex.com/mobile/settings/)
- Calibre defines CBC as a ZIP containing CBZ/CBR files plus UTF-8 `comics.txt`; each manifest entry uses `filename:title`. Calibre uses these entries for the resulting book's table of contents. CBC therefore represents a collection of books or chapters rather than an ordinary CBZ page-image archive. [Calibre comic book collections](https://manual.calibre-ebook.com/conversion.html#comic-book-collections)
- The user's request names PDFs, page-image folders, existing comic archives, and CBZ output, while also speaking variants including CBC/CVR/CVZ. The requested task is research and vision first, followed by discussion of an implementation plan. Source: user request in this conversation, 2026-10-07.
- The user-scoped instructions in this conversation require preserving user-created and program-produced data; fresh test state belongs in a throwaway location. Source: supplied `AGENTS.md` instructions in this conversation.

### Inferences

- Normalize the ordinary archive terms to CBR/CBZ in the vision. Keep actual CBC collection support open until clarified; do not silently promise it.
- The future import contract should distinguish ordered book pages, container entries, and embedded image objects. They are different entities.
- Filename ordering, nested folders, duplicate names, spreads, animation, and already-present page/panel metadata will need deliberate behavior. The existence of a ZIP or image folder alone does not settle those choices.
- Conversion should produce a separate output, preserve the original source, and avoid treating unknown metadata or auxiliary files as disposable. How much existing metadata is copied into the derivative is a design question, not permission to alter the source.
- A prospective importer can inspect the underlying container rather than trusting filename spelling. That is a recommendation for later design, not an implementation decision.

### Gaps

- Whether CBC collections are actually required is unconfirmed.
- Required first-version reading devices are pending the user's first interview answer; no iOS, Android, or desktop priority has been selected.
- Exact accepted image formats, folder recursion rules, archive limits, unsupported-file policy, and input/output naming rules remain open.
