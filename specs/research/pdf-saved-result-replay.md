# PDF source recovered; saved experiments replayed

2026-10-08 update: Chris clarified that problems occur throughout the book and
requested every-page visual iteration. [The new audit and experiments](segmentation-iteration-20261008.md)
supersede the request for an example page below. Build 5 adds page-first reading;
the two original replay books retain their rejected detector output. The replay
preservation measurements below remain historical evidence, not quality acceptance.

User review: Chris reports that panel detection is not correct. The browser
transport/navigation passes below are not detection-quality acceptance. A fresh
offline comparison confirmed that the Gemini archive's page 4 (source PDF page
25) retains exactly the five historical frame strings; a six-panel count check
fails. The error therefore predates replay for this known case. The precise book,
page and symptom Chris observed are still being clarified; do not assume this
known merge explains every reported problem. No correction or new inference has
been performed in response to this report yet.

2026-10-07 (2026-10-08 UTC). Chris reaffirmed **PDF, CBZ, CBR and image folders**
as converter inputs and supplied the source PDF through Google Drive. CBZ is the
derived reader artifact, not a restriction on source input. No production Rust
implementation or new detection run was needed for this replay.

The downloaded *Parallel Truths Graphic Novel Anthology – Reader Nation.pdf*
is 119,103,854 bytes and matches the historical source SHA-256 exactly:
`30d075d2bf54cdcd2401ccf905ab50a859779296e7afdbff404efd291f42cd32`.
The Drive file ID is `14bfWbyIf-SFrRlXvtdEDPjEVJL6wxHcZ`.
Drive metadata succeeded; the connector's temporary binary link returned HTTP
403. The user-provided sharing link's ordinary download form succeeded instead.
Sharing permissions and the source file were not changed.

## New review artifacts

The original CBZs are still absent. The new
[offline replay helper](../../prototypes/web_panel_reader/replay_saved.py) rendered
this verified PDF in the existing disposable VM with Poppler 25.03.0, then copied
the historical manifests' pixel-frame strings in their original order. It did not
call Gemini or Pannello, sort/correct panels, or alter fallback records.

| Artifact | Pages / frames / recorded fallbacks | Bytes | New SHA-256 |
| --- | --- | ---: | --- |
| `gemini-saved.cbz` | 4 / 8 / 1; source pages 1, 3, 5, 25 | 7,539,352 | `8b5e080530f1532cfa0d710a3001490b6825220c15d8c8c764ce7386358d2848` |
| `local-saved.cbz` | 257 / 1,094 / 48 | 75,362,700 | `7f684110be76a478f8d79ce6c249b0d70f6ebd2ae142858942587a84365be073` |

Gemini pages were rendered as PNG at a 1500-pixel maximum dimension, resulting
in the recorded 1027 × 1500 size. Full-book pages were JPEG at 150 DPI and matched
every recorded dimension. Only 1/4 Gemini image hashes and 9/257 local image hashes
match the historical renders. These are **new renderings with saved geometry**,
not restored original CBZ bytes or a fresh model-quality experiment.

All 261 rendered images decoded successfully. Both archives passed CRC checks,
exact page/reference counts, byte hashes against their new render inputs, and
exact ordered frame-string comparison against the historical manifests. The PDF
hash remained unchanged. No page was omitted. The 48 fallbacks remain a recorded
count that includes legitimate whole-page compositions, not an error-rate measure.

## Reader verification and delivery

[Panel Lab](https://csells-mac-mini--51996.getbb.app/) now offers **Gemini sample**
and **Full book · local detector**, with download progress and descriptions of
their limitations. Refresh an already-open landing page to see the books. The
synthetic order experiment and browser-local CBZ selection remain available.

Candidate build 3 was checked on a separate VM loopback port before the existing
review service switched to that build. The prior build and service unit remain
available for rollback. The same saved-book acceptance ran against the published
service afterward; this is still disposable staging, not a stable installation.

Chromium 154 at 390 × 844 passed 14 real-book checks: gallery entries, Gemini
page/frame counts, source-page navigation/fallback, all five page-25 regions,
the unchanged merged bottom region, full-page viewing, full-book page/frame counts,
and its first body page/page mode. No uncaught browser exceptions occurred.
The six parser/archive cases and fourteen synthetic navigation/input checks also
passed on the changed candidate. These checks establish browser transport and
navigation; they are not a 257-page quality review or new physical-phone result.

Visual inspection confirms source page 25 still has the known merged bottom
region and that Page mode retains its complete artwork. The original detection
quality concern therefore remains. The Gemini sample's source page 5 retains
its recorded whole-page fallback after the historical HTTP 503 failures.

## Preservation and remaining scope

Source PDF: `validation-artifacts/drive-source-20261007/source.pdf`.
New CBZ copies, full replay manifests and private screenshots/results:
`validation-artifacts/pdf-replay-20261007/`. Both directories are Git-ignored.
Tracked text-only [replay evidence](evidence/pdf-replay-20261007/summary.json)
records hashes, counts, rendered checks and artifact provenance. Private comic
images and the PDF are not committed. The home-lab registry's
`comic-panel-reader-stage` record owns current deployment paths and cleanup.

The source and derived books are now intentionally present in the disposable VM
for the authorized phone review. Access through BB Connect requires the owner's
session. No credentials were copied. Copies outside the VM preserve the artifacts
before eventual teardown; original manifests and earlier synthetic evidence remain
unchanged.

This exercises **PDF → complete page renders + saved coordinates → ACBF CBZ →
web reader**. It is not a general automatic converter release. CBR compatibility,
general archive/folder import, model-quality acceptance and the Rust implementation
remain in [plan 0002](../plans/0002-quality-gated-rust-cli.md). Panel Lab itself reads
the generated CBZs; its file picker is not yet a PDF/CBR conversion interface.
