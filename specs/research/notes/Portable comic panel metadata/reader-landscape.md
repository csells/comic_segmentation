# Portable panel metadata: reader landscape beyond the ACBF reference readers

Research checked **2026-10-07**. Scope: alternatives to the separately researched ACBF Viewer, ACBF Viewer for Android, and KDE Peruse. Evidence labels distinguish **documented**, **source inspected**, and **runtime tested**. No reader was installed or runtime tested for this note. Read-only source checkouts live in `/tmp/comic-readers-research.cRGSz1/`.

## Can ordinary comic metadata standards encode a portable guided reading experience?

### Takeaway

Opening a CBZ, importing its catalog metadata, and following precomputed panels are three different capabilities. ComicInfo.xml is useful alongside a panel format; its established page fields are not panel geometry. EPUB has a genuine region-navigation standard, but it changes the output container and does not establish universal reader support.

### Cited Findings

- **ComicInfo.xml — schema inspected.** Version 2.0 defines per-page attributes `Image`, `Type`, `DoublePage`, `ImageSize`, `Key`, `Bookmark`, `ImageWidth`, and `ImageHeight`; it does not define nested panels, polygon coordinates, or panel reading order. The current Anansi documentation describes the same page-level fields. `ImageWidth` and `ImageHeight` describe the complete image, not a panel. — [v2.0 schema](https://github.com/anansi-project/comicinfo/blob/main/schema/v2.0/ComicInfo.xsd); [Anansi field documentation](https://anansi-project.github.io/docs/comicinfo/documentation#pages--comicpageinfo)
- **CoMet — specification inspected.** Its published tag list covers bibliographic information, creators, characters, cover image, page count, and reading direction. That published list does not specify panel geometry or a sequence of regions within a page. — [CoMet specification](https://www.denvog.com/wordpress/comet/comet-specification/)
- **ComicBookInfo — documented.** The historical specification mirror describes bibliographic JSON in the ZIP comment, with a 65,535-byte limit. Its overview names title, series, genre, publisher, and authors; it does not document a portable panel contract. A private JSON extension would require matching reader support and should not be presented as existing interoperability. — [Original project's documentation mirror](https://github.com/iComics/comicbookinfo)
- **EPUB Region-Based Navigation — specified.** The 2015 recommended specification defines an ordered list of regions, optional nested subregions, and rectangle coordinates expressed as percentages of the content document. It supports the same broad reading objective but is an EPUB feature, not CBZ metadata. — [IDPF region-navigation specification](https://idpf.org/epub/renditions/region-nav/)
- **EPUB support is limited.** W3C's fixed-layout accessibility techniques explicitly say region-based navigation has support in only a few reading systems and advise testing the actual EPUB. Plain “EPUB supported” therefore does not demonstrate panel navigation. — [W3C fixed-layout techniques, region-based navigation](https://w3c.github.io/epub-specs/epub33/fxl-a11y-tech/#region-based-navigation)

### Inferences

- Preserve or generate ComicInfo.xml for catalog interoperability, while using a separately specified panel format. Treat adding panel-shaped private XML to ComicInfo.xml as inventing a new extension, not unlocking existing support.
- EPUB is a possible future export target if a chosen reader demonstrably consumes its regions. It is not evidence that the requested CBZ can deliver panels everywhere.

### Gaps

- ComicBookInfo's mirror is incomplete; this research did not establish every historical extension or reader-specific addition.
- No current OSS reader consuming EPUB region navigation was proven in this scoped pass. The normative specification alone is insufficient acceptance evidence.

## Which examined readers actually consume externally prepared panel coordinates?

### Takeaway

The strongest additional verified consumer is **Panel by Panel**, an OSS browser reader for unpacked ACBF. **PanelReader for KOReader** genuinely consumes external JSON but requires a sidecar. Several attractive modern readers instead compute their own regions; their guided modes do not establish a route for the proposed CLI's metadata.

### Cited Findings

| Candidate | Platforms and license evidence | What was established | Relevance to portable CBZ panels |
| --- | --- | --- | --- |
| **ragtag/panel-by-panel** | Browser application, GPL-3.0. Author reports testing desktop Chrome/Firefox/Edge/Safari, Android Chrome, and iPhone Safari. [README and license](https://github.com/ragtag/panel-by-panel) | **Documented and source inspected:** reads ACBF `frame` point lists and navigates them. Explicitly requires external images and an unpacked `.acbf`; explicitly excludes `.cbz` ACBF and single-file embedded-image ACBF. | Real imported-panel reader, with an unpacking/hosting step. No direct local CBZ support established. |
| **Kaito0/PanelReader** | KOReader plugin, AGPL-3.0. [Repository](https://github.com/Kaito0/PanelReader); [license](https://github.com/Kaito0/PanelReader/blob/main/LICENSE) | **Documented and source inspected:** looks for `<book>.json` next to the comic, parses ordered per-page normalized `x,y,w,h`, and uses it for panel navigation. [Importer](https://github.com/Kaito0/PanelReader/blob/main/panelzoom_integration.koplugin/main.lua) | Genuine externally generated regions, but a custom sidecar and plugin installation; not a self-contained embedded-metadata CBZ solution. |
| **OpenComic** | Windows, macOS, Linux; GPL-3.0. [Repository](https://github.com/ollm/OpenComic) | **Source inspected:** master has Guided View under undated/unreleased v2.0.0. `_getPanels()` invokes `OpenComicAI.panels.image()` then `panels.path()`. [Changelog](https://github.com/ollm/OpenComic/blob/165826057755d71d1dcf466836c518ef87cc2c6f/CHANGELOG.md); [panel code](https://github.com/ollm/OpenComic/blob/165826057755d71d1dcf466836c518ef87cc2c6f/scripts/reading/panels.mts) | Reader-side detection. No imported ACBF/ACV/panel JSON path found in inspected reading code. Do not claim the advertised stable release, 1.6.5, already ships this master feature. |
| **Komicove, formerly PANEL** | Windows, Linux, Android; MIT. [Repository](https://github.com/lucrazy-fn/PANEL-ComicBookReader) | **Source inspected:** desktop reads manually edited regions from app-data `manual_panels.json`, keyed by content and page; otherwise requests detection. Android persists `customPanels` in its library records. [Desktop persistence](https://github.com/lucrazy-fn/PANEL-ComicBookReader/blob/e9d5c8f390ac89657c8a0a14a861617a100ff449/komicove_app/reader.py); [guided selection](https://github.com/lucrazy-fn/PANEL-ComicBookReader/blob/e9d5c8f390ac89657c8a0a14a861617a100ff449/komicove_app/reader_views.py); [Android store](https://github.com/lucrazy-fn/PANEL-ComicBookReader/blob/e9d5c8f390ac89657c8a0a14a861617a100ff449/android/app/src/main/java/com/lucrazy/komicove/LibraryStore.java) | Automatic detection plus local corrections. No archive-embedded panel importer found. Editing its private app data would not make a portable CBZ. |
| **Panels** | Commercial comparison: iPhone, iPad, Mac. [Official site](https://www.panels.app/) | **Documented:** premium Panels View uses trained machine-learning models to detect and zoom into panels, and is described as experimental. [Panels View guide](https://guides.panels.app/read-content/panels-view) | Strong UX reference, but no verified external-panel import; not evidence for an OSS solution. |

- **Panel by Panel implementation detail:** JavaScript fetches `comics/<name>/<name>.acbf`, parses frame point lists, and derives display bounds relative to the image's natural dimensions. This demonstrates actual consumption rather than just an ACBF checkbox in marketing. Commit inspected: `f916dea4e88c5b3805ee3dbd9fc01163676982ae`, dated 2023-04-26. — [Source at inspected commit](https://github.com/ragtag/panel-by-panel/blob/f916dea4e88c5b3805ee3dbd9fc01163676982ae/pbp/panelbypanel.js)
- **PanelReader's coordinates are an explicit external contract:** its README documents 1-based page numbers and normalized rectangles, `reading_direction`, and a matching JSON filename. The importer actually opens that neighboring JSON rather than looking inside CBZ. — [PanelReader documentation](https://github.com/Kaito0/PanelReader/blob/main/README.md); [Importer](https://github.com/Kaito0/PanelReader/blob/main/panelzoom_integration.koplugin/main.lua)
- **Maintenance snapshots:** OpenComic and Komicove inspected HEAD commits are dated 2026-10-07, while Panel by Panel's inspected HEAD is dated 2023-04-26. This establishes recency, not quality or a maintenance guarantee. The KOReader plugin repository reported a push on 2026-08-09. — [OpenComic commit](https://github.com/ollm/OpenComic/commit/165826057755d71d1dcf466836c518ef87cc2c6f); [Komicove commit](https://github.com/lucrazy-fn/PANEL-ComicBookReader/commit/e9d5c8f390ac89657c8a0a14a861617a100ff449); [Panel by Panel commit](https://github.com/ragtag/panel-by-panel/commit/f916dea4e88c5b3805ee3dbd9fc01163676982ae); [PanelReader repository API](https://api.github.com/repos/Kaito0/PanelReader)
- **Mihon:** its local-source documentation supports folders, CBZ/ZIP, CBR/RAR, and EPUB, with images becoming pages. That establishes archive reading, not panel import. A panel-metadata consumer was not verified in this pass. — [Mihon local-source guide](https://mihon.app/docs/guides/local-source/)
- **Komga:** its documented ComicInfo import maps catalog fields, reading direction, collections, and read lists. This is useful library interoperability; the documentation does not establish consuming panel coordinates. — [Komga metadata import](https://komga.org/docs/guides/scan-analysis-refresh/)
- **Kavita:** a public feature discussion asks for panel reading and discusses accepting ACBF or other precomputed region formats. This is evidence of a request and design discussion, not released support; the discussion alone cannot rule out later implementation. — [Kavita discussion #2826](https://github.com/Kareadita/Kavita/discussions/2826)

### Inferences

- For this project, record compatibility as **“opens generated CBZ”**, **“uses generated panel coordinates”**, and **“navigates the intended order”** separately. A reader that redetects panels discards the central value of preparing and reviewing coordinates once.
- OpenComic and Komicove could be candidates for an upstream metadata-import contribution because they already have region navigation. That is additional reader development, not an existing capability that the Rust converter can rely on.
- The KOReader sidecar format could be an adapter/export option if e-readers matter. It conflicts with a strict single-file-output requirement.

### Gaps

- No actual sample produced by this project was opened in any reader during this research. Source evidence is stronger than feature lists but weaker than an end-to-end compatibility test.
- “No importer found” in OpenComic/Komicove means the relevant source paths and format names were inspected; it is not a formal proof that no obscure extension or future branch exists.
- **PanelPanda:** searches for the exact name and GitHub repository search returned no identifiable project. No platform/license/format claim should be made without a canonical URL.
- **CDisplayEx:** official Windows distribution and proprietary EULA are available, but a precomputed-panel import format was not established. Do not list it as a compatible consumer from its general reader reputation. — [Official desktop page](https://www.cdisplayex.com/desktop/)

## Does this establish an existing OSS panel-reading path on every platform, especially iOS?

### Takeaway

No native iOS/iPadOS OSS consumer of panel metadata embedded in CBZ was verified. A browser path using existing OSS is credible, but the proven ACBF browser reader requires unpacking and serving the comic, and has not been runtime tested here on today's devices. “Any platform” must therefore remain a target to validate, not a promised feature.

### Cited Findings

- **The strongest existing browser bridge has real prerequisites.** Panel by Panel documents PHP, ImageMagick, an unpacked comic directory, and a lowercase `.acbf` filename matching the directory. Its author reports Safari on iPhone testing. This provides a route to iOS browsers without a native app, but not a single CBZ opened from Files or an offline PWA. — [Setup and browser notes](https://github.com/ragtag/panel-by-panel/blob/f916dea4e88c5b3805ee3dbd9fc01163676982ae/README.md)
- **A tempting PWA result needs qualification.** `hummat/panelizer` discusses a future cross-platform PWA in its README, but the README also says the project is archived and unmaintained. GitHub's repository API reported `archived: false`, so describe this as the author's maintenance statement, not GitHub archive state. — [README](https://github.com/hummat/panelizer/blob/main/README.md); [repository API](https://api.github.com/repos/hummat/panelizer)
- **Panelizer has actual browser preview code, but that is a narrower capability.** Its JavaScript navigates panel IDs, fits their bounding boxes, and fetches page JSON from a Python preview server. The server's `page_json` pathway performs detection; this is not proof of the README's envisioned standalone CBZ-opening PWA or an embedded ACBF importer. — [Preview JavaScript](https://github.com/hummat/panelizer/blob/main/src/panelizer/preview/static/app.js); [Preview server](https://github.com/hummat/panelizer/blob/main/src/panelizer/preview/server.py)

### Inferences

- **Best supported direction from this scoped landscape:** standard panel metadata remains worthwhile; use the separately researched native ACBF consumers where available, and consider the existing ACBF browser reader as a bridge for platforms without one. Prove the bridge with a synthetic comic before calling it supported.
- The browser bridge imposes extraction and hosting, and potentially modernization work. Delivering a polished offline, direct-CBZ PWA would be a separate product commitment unless a better existing consumer is proven.
- A native iOS requirement, an OSS-only requirement, and a strict self-contained-CBZ requirement materially narrow the solution. The user should decide which are first-version acceptance criteria before an implementation plan assumes compatibility.

### Gaps

- Native iOS/iPadOS imported-panel support remains **unverified**, not conclusively nonexistent.
- Present-day Safari/iOS behavior, offline operation, storage, image limits, and navigation edge cases were not tested.
- The PBP source converts polygon points into display bounds; irregular panels, overlapping panels, nested panels, RTL ordering, one-frame pages, and cover treatment need fixtures. A successful standard-schema validation is not a substitute for observing the intended reading sequence.
