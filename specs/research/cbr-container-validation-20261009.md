# Real CBR container fixture — 2026-10-09

Three owned synthetic comic PNG pages were packed into a genuine compressed RAR5
archive in disposable VM153. Official RAR's archive test and independent
libarchive extraction both passed. Every original image byte and decoded RGB
pixel hash matched. The actual candidate importer also passed RAR5, equivalent
CBZ and folder parity: ordered page hashes/dimensions, auxiliary bytes, identical
resume and unchanged originals. The real RAR4 symlink input was rejected without
creating a symlink or marking preparation complete. Provider HTTP was explicitly
blocked and had zero dispatches. **Automatic inference and reader qualification
remain subsequent gates.**

The [official download page](https://www.rarlab.com/download.htm) supplied stable
Linux x64 RAR 7.23. Its [trial terms](https://www.rarlab.com/license.htm) permit
testing at no charge for up to 40 days. The portable package was downloaded and
used only inside this task's evidence directory; no host/system installation,
license purchase, registration, API request or reader service change occurred.
No separately published vendor checksum was found; the recorded SHA-256 pins
the package fetched over the vendor's HTTPS endpoint, not an independently
authenticated release signature. Do not bundle this proprietary utility into
the product or treat trial use as a permanent runtime dependency.

Evidence: `/home/tester/comic-reader/evidence/cbr-validation-20261009/`.
The directory measured 5,423,243 bytes after initial fixture creation. The portable
package, notices, version output, exact command arrays, logs, source pages,
archives, extraction and hashes are retained. Source PNGs use valid uncompressed
DEFLATE blocks so RAR's own compression is measurable; these are container
fixtures, not evidence of segmentation quality.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Official `rarlinux-x64-723.tar.gz` | 746,868 | `759b4b6aa0d9f77131882162951193f3a0e54bf60e1d8dc4255aa308accab588` |
| `synthetic-rar5-compressed.cbr` | 12,098 | `66402b767e4fafdce66cf5a021e4bdc9e443f9b7aba24322df7c106fe3185fad` |
| `synthetic-equivalent.cbz` | Recorded in fixture manifest | `d52ccfa64ed9b92e5fa070cee7643ba7dce766a059870793511fb4c78ece5e78` |
| Upstream RAR4 symlink fixture | Recorded in retained source | `d421b86f6290aefad61b2a36737253b2b30fe27c156bd95abfc230f24fe0307e` |

The positive archive has RAR5 signature `526172211a070100`, normal compression
`-m3`, a requested 1 MiB dictionary (actual entries report 512 KiB), one thread,
non-solid storage, no encryption and one
volume. Three 320×480 PNGs total 1,384,491 bytes before compression, plus an
81-byte auxiliary note. `rar t` returned success. The inspected archiver reports
`RAR 7.23`, dated June 27, 2026. Its executable hash and complete `rar lt` output
are preserved in `fixture-manifest.json` and `rar-list.txt`.

The negative archive comes from
[libarchive v3.7.4's test fixture](https://github.com/libarchive/libarchive/blob/v3.7.4/libarchive/test/test_read_format_rar.rar.uu)
and its [test/source notice](https://github.com/libarchive/libarchive/blob/v3.7.4/libarchive/test/test_read_format_rar.c).
It contains text, a symlink and directories. Entries were inspected through
libarchive without creating the symlink. This establishes a real nonregular
member input for rejection, not general malicious-RAR coverage. Successful RAR4,
solid archives, encrypted/multipart archives and damaged-archive recovery remain
unqualified.

Reproduction code lives under
`prototypes/panel_quality_probe/experiments/cbr_validation_v1/`. The producer
refuses to replace completed evidence. `validate_import.py` ran against
`/home/tester/comic-reader/candidate-v29/source`; its `import-validation.json`
records exact candidate hashes. `auto_convert.py` was
`263858ca5ec737679b57c3043ad0342e20068ecd173a831267a2333d82085741`.
The validator exercises actual `prepare_input()` with HTTP explicitly disabled;
it does not mock extraction or page preparation. A source-equivalent automatic
conversion and emitted-reader test is a subsequent integration gate.
