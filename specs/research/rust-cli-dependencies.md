# Rust CLI dependency feasibility

Researched 2026-10-07. Planning evidence only: no Rust implementation, dependency installation, paid API calls, or reader testing. Recommendations below are engineering proposals, not settled product scope. Package versions should be selected and locked during implementation.

## Recommended starting path

Use established Rust crates for ZIP, images, XML, arguments, and HTTP; invoke installed Poppler for PDF rendering. Begin the CBR adapter with macOS `bsdtar`, but make its limited RAR coverage explicit and test it before committing to the input contract. If solid RAR4 is required for initial acceptance, replace that adapter with a vetted UnRAR binding before release. This keeps the first working slice small without claiming universal CBR support or a dependency-free executable.

| Responsibility | Starting choice and evidence |
| --- | --- |
| CBZ input/output | [`zip`](https://docs.rs/zip/latest/zip/) supplies `ZipArchive`/`ZipWriter`. Write Stored or Deflate entries for conventional reader compatibility; broader input compression support is feature-dependent. Call [`finish()`](https://docs.rs/zip/latest/zip/write/struct.ZipWriter.html#method.finish) explicitly and handle its errors. |
| Images | [`image`](https://github.com/image-rs/image#feature-flags) supports the common JPEG, PNG, WebP, TIFF, BMP and GIF families. Enable only the selected codecs. Content-based format guessing is available through [`ImageReader`](https://docs.rs/image/latest/image/struct.ImageReader.html). |
| Orientation | Read [`ImageDecoder::orientation()`](https://docs.rs/image/latest/image/trait.ImageDecoder.html#method.orientation), then explicitly [`apply_orientation()`](https://docs.rs/image/latest/image/enum.DynamicImage.html#method.apply_orientation). Detect panels and write metadata against the same final oriented pixels. |
| ACBF XML | [`quick-xml`](https://docs.rs/quick-xml/latest/quick_xml/) provides reader/writer and optional Serde integration. Use its writer for escaping; validate the ACBF structure separately against the format contract. |
| CLI and JSON | [`clap`](https://docs.rs/clap/latest/clap/) for arguments/help; [`serde`](https://serde.rs/) with `serde_json` for typed Gemini requests, responses, and run manifests. |
| HTTP | [`reqwest::blocking`](https://docs.rs/reqwest/latest/reqwest/blocking/) is sufficient for a sequential first pipeline. Reuse a client, set timeouts, inspect HTTP status, and implement bounded retry policy. An async application framework is unnecessary initially. |
| Page ordering | [`natord`](https://docs.rs/natord/latest/natord/) offers natural comparison. Define deterministic tie-breaking and path rules in the application; a comparator cannot infer a book's intended narrative order. |

## PDF: external Poppler first

`pdftoppm` renders composed pages and supports page ranges, PNG/JPEG output, resolution, CropBox selection, rotation-related scaling, and color profiles. These capabilities are documented in the [maintainer's source mirror](https://github.com/tsdgeos/poppler_mirror/blob/master/utils/pdftoppm.1), linked from the [official Poppler site](https://poppler.freedesktop.org/). Use full-page rendering, not extraction of embedded images: page composition can include multiple images, masks, text, and vector content.

Local read-only observation: `/opt/homebrew/bin/pdftoppm -h` reported 26.09.0 and these options. Preflight `pdfinfo`/`pdftoppm` before contacting Gemini. Invoke argument arrays, preserve stderr and exit status, and write only into a new working directory. Pin the chosen rendering settings in the manifest so retries use identical geometry.

[Homebrew distributes Poppler](https://formulae.brew.sh/formula/poppler) through `brew install poppler`, with GPL-2.0-only OR GPL-3.0-only licensing. Document this prerequisite. Bundling Poppler introduces redistribution obligations and multiple native dependencies; this proposal does not assess the application's legal licensing consequences.

[`pdfium-render`](https://github.com/ajrcarey/pdfium-render/blob/master/README.md) is a credible later alternative, but does **not** include or build PDFium. It needs a separately supplied dynamic library or static build, target-specific packaging, and sometimes additional native linkage. [PDFium's license](https://pdfium.googlesource.com/pdfium/+/refs/heads/main/LICENSE) also identifies third-party components. It simplifies neither initial packaging nor provenance enough to displace an already installed renderer.

## RAR: a material compatibility boundary

[Libarchive documents original RAR and RAR5 reading](https://github.com/libarchive/libarchive/wiki/LibarchiveFormats). However, its [RAR4 reader explicitly rejects solid archives and encryption](https://github.com/libarchive/libarchive/blob/master/libarchive/archive_read_support_format_rar.c); its [RAR5 reader handles solid state but rejects encrypted headers](https://github.com/libarchive/libarchive/blob/master/libarchive/archive_read_support_format_rar5.c). Format names alone overstate compatibility. Local `/usr/bin/bsdtar --version` reported bsdtar 3.5.3 / libarchive 3.7.4; current upstream source is not proof of that binary's behavior.

The [`unrar` crate](https://docs.rs/unrar/latest/unrar/) wraps and statically builds the native UnRAR implementation, supports sequential reads and password handling, and avoids requiring an installed extraction command. It is not pure Rust. Its [published release history](https://docs.rs/crate/unrar/latest) shows 0.5.8 dated 2025-02-19; the repository's [vendored engine version](https://github.com/muja/unrar.rs/blob/master/unrar_sys/vendor/unrar/version.hpp) identifies 7.1 from 2024. Investigate native security updates before adoption; this pass does not establish current maintenance adequacy. The [embedded license](https://github.com/muja/unrar.rs/blob/master/unrar_sys/vendor/unrar/license.txt) permits archive handling and distribution but restricts recreating RAR compression. Preserve required notices; the wrapper's MIT/Apache labels do not cover the engine.

## Acceptance probes before promising support

- **Images:** JPEG/PNG/WebP and selected TIFF/BMP/GIF variants; all EXIF rotations/reflections; transparent and grayscale pages; ICC/CMYK samples. Test animated/multipage inputs explicitly or reject them clearly. Do not assume decoder support guarantees Android reader support; normalized output should use tested JPEG/PNG.
- **Order:** `1, 2, 10`, zero padding, Unicode, mixed case, nested folders, covers, duplicate names, archive order versus filename order, and existing metadata. Record the resolved order.
- **CBR:** RAR4/RAR5, stored/compressed, solid/non-solid, encrypted headers/data, multipart, corrupt CRCs, Unicode names, traversal and links. An unreadable source page is an import failure, not a detection fallback.
- **PDF:** rotated pages, differing MediaBox/CropBox, transparent masks, multiple image layers, vector/text overlays, CMYK/ICC color, spreads, and small lettering at the selected raster resolution. Compare rendered pages visually to the composed PDF.

No fixture-based compatibility probes were run in this research pass. Android ACBF consumption remains a separate end-to-end acceptance requirement.
