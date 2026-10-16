# comic-panel CLI production readiness (2026-10-16)

**Approved by Chris and merged to `main` on 2026-10-16 (`3779a81`).** CI
passed on Linux and macOS for both the branch and `main`. The disposable
staging environments have been removed.

This is the state of the Rust CLI (`cli/`) that was reviewed for that decision.

Parity with the V63 prototype is recorded in
[rust-port-parity-20261015](rust-port-parity-20261015.md). The milestones refer
to [plan 0002](../plans/0002-quality-gated-rust-cli.md).

## What production-ready covers here

| Area | State | Evidence |
| --- | --- | --- |
| Pipeline fidelity | Byte-identical requests to V63. A 257-page offline replay of the hardened binary matches exactly: 70 cached pages identical, 187 uncached pages blocked identically. Live 12-page sample matches. | parity record; `validation-artifacts/rust-port-20261015/` |
| CLI shape | `comic-panel SOURCE [OUTPUT]`. Key from `OPENAI_API_KEY` or piped stdin. Shared default ledger in the platform data directory. `--max-spend-usd` (run limit, default $20) and `--page-cap-usd` (default $0.50). Resumable work directory. `--offline` replay. `--json`. | `cli/README.md` |
| Exit status | `0` published; `2` published with listed whole-page fallbacks; `1` stopped without publishing, resumable. | e2e tests |
| Publication safety | Built CBZ re-opened and checked: entry CRCs, page bytes, ACBF page order and frame counts, reader-profile hash binding. Copied to the destination through a synced temporary file and a hard link, so an existing file is never replaced and no partial file is left. Non-active `comic-panel-report.json` inside the book. | `publish::tests`, e2e `refuses_to_overwrite_existing_output` |
| ACBF validity | Published metadata validates against the pinned ACBF 1.1 XSD (upstream commit `e033e004`, sha256 `154e997a…`). Covers multi-page, folder and single-page (cover-only) books. | e2e with `COMIC_PANEL_ACBF_XSD`; `tests/fetch-acbf-xsd.sh` |
| Inputs | PDF via Poppler, with the 257-page book. CBZ/ZIP via e2e tests and the unseen comic. Genuine RAR4 CBR prepared via bsdtar. Image folders in natural order. Single-image books. JPEG/PNG/BMP/GIF/WEBP and all 8 EXIF orientations identical to the prototype. RGBA preserved. | e2e; `tests/differential/formats.py` (13/13) |
| Input safety | Path traversal, absolute paths, symlinks, duplicate and case-colliding members, encrypted members, more than 10,000 entries, more than 2 GB actually expanded (lying sizes caught while copying), and pages over ~179 MP are refused. Multi-frame images are refused. Every page is fully decoded before any paid request. | e2e `rejects_corrupt_or_unsafe_input_before_any_request`; animated-GIF check |
| Spending and recovery | Durable reservations before dispatch, settlement from reported usage, global ledger cap, per-run limit, per-page cap with cold-run accounting. One automatic recovery of a recorded transient 503/connection failure; unknown outcomes are never replayed. | `budget::tests`; e2e `run_spending_limit_stops_resumably`, `recovers_one_transient_server_error`, `converts_resumes_and_replays` |
| Platforms | Linux x86-64 (Debian 13) and macOS 26 arm64: fmt, clippy `-D warnings` and all 22 tests pass. Image bytes are identical across platforms. | `validation-artifacts/cli-production-20261016/macos-*.log` |
| CI | `.github/workflows/cli.yml` runs fmt, clippy and the tests (with schema validation) on Ubuntu and macOS. | green on `comic-panel-cli` and `main` (`validation-artifacts/cli-production-20261016/ci-*.log`) |
| Reproducible build | `Cargo.lock` committed; `rust-version = 1.88`. | `cli/Cargo.lock` |

## Unseen-book validation

**Modern comic: Pepper&Carrot episodes 37–39** (David Revoy, 2022–2024, CC BY 4.0).
The input was 30 English pages, 1200×1660 digital paintings, packed as a CBZ
with a credits file. It ran live with the default settings.

- Result: 22 pages with panel guidance (134 panels), 4 title/splash pages kept
  whole, and 4 whole-page fallbacks (pages 6, 17, 18 and 24, all at the $0.50
  page cap). Exit status 2, with the fallbacks listed.
- Cost: $7.36 in total (about $0.25 per page), 546 requests, about 40 minutes.
- Review: every page was inspected visually in contact sheets
  (`validation-artifacts/cli-production-20261016/pc-sheet-*.jpg`). All 22
  multi-panel pages show every panel in reading order, with no missed or merged
  panels. Overlapping boxes on pages 2, 5, 9 and 21 follow figures or balloons
  that break their frames.
- The published CBZ preserves every page byte, carries `source-auxiliary/CREDITS.txt`
  and `comic-panel-report.json`, and was shared with Chris for reading.

**1941 scan: *Exciting Comics #10*** (public domain). This run was stopped on
Chris's direction after 18 of 64 pages, because a 1941 newsprint scan
represents current comics poorly. Of those 18: 15 had panels, 2 were whole-page
covers and 1 fell back. It cost $5.21. The run was stopped between pages, so no
reservation was left held. The yellowed paper triggers V63's uncovered-content
ownership checks on every panel, which makes old scans slower and more
expensive (about 8 minutes and $0.30 per page).

**Genuine RAR4 CBR:** 28 pages were extracted and prepared offline through
bsdtar, with no API use. The file was deleted afterwards because its
public-domain label was doubtful.

## Known limits (not blockers to merging, but true of the product)

- Segmentation quality and cost are V63's. With the $0.50 page cap, pages with
  complex layouts can stop escalating and are published whole: 4 of 30 modern
  pages, 25 of 70 replayed pages of the validation book and 2 of its 12 live
  pages. Raising `--page-cap-usd` trades cost for coverage. Better quality per
  dollar is pipeline research, not port work.
- No single-version run of the whole 257-page book. Chris kept the $370 ledger
  cap, so that run was not attempted.
- Not exercised: RAR5, multipart RAR, ZIP CRC corruption (the zip reader checks
  it on read), Windows.
- Model prices are compiled in, verified through 2026-12-31; after that the CLI
  warns that ledger costs are estimates.
- ICC profiles of non-JPEG/PNG pages are not copied into converted PNG pages.
