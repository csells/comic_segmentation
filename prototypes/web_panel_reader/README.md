# Phone-browser panel experiment

Current staging is build 7: approved Astra pilot, Sol low/high comparison pilots, Gemini sample and full local-detector book. [Measured comparison](../../specs/research/cost-quality-comparison-20261008.md). Each new Sol book passed 25 navigation checks and zero exceptions in prepared and published staging; reader application bytes remain unchanged from build 5.

The review site now also includes two real-comic books rebuilt from the verified
source PDF and saved geometry. See the [PDF replay report](../../specs/research/pdf-saved-result-replay.md).
PDF, CBZ, CBR and image folders remain converter inputs; the reader consumes the
derived CBZ. No new detector/model call is required to reproduce these saved runs.

This is a narrow ACBF adapter for the existing MIT-licensed
[PanelView](https://github.com/wenn-id/panelview/tree/ba86994fd8b8c99b62e960bccbeb51a576772f03)
reader, pinned at `ba86994fd8b8c99b62e960bccbeb51a576772f03`. It is experimental
review tooling, separate from the proposed Rust converter and the Flutter app.
See the [measured report](../../specs/research/web-reader-validation.md).

[Open the staged reader](https://csells-mac-mini--51996.getbb.app/), using the
owner's BB session. Choose the order experiment, tap right/left or swipe, and
switch between Page and Panels. The sample deliberately follows 3 → 1 → 4 → 2.
Panels mode now starts each page with its complete overview, then follows that
metadata sequence. Covers and whole-page fallbacks appear once. Refresh an open
tab to load build 5; module URLs are versioned and old resume positions remain
in their original namespace. Switching from Page to Panels shows the overview.
A local CBZ selection stays in the browser; there is no book-upload endpoint.

## Boundary and limitations

`acbf.js` parses root `metadata.acbf` in ACBF 1.1, keeps cover/body/XML frame order,
checks image references, and supplies rectangles to PanelView. Empty frame arrays
force whole-page viewing instead of detection. Nonrectangular polygons use their
bounding boxes; surrounding artwork is dimmed, not clipped away. The hosted
sample uses the existing converter adapter's explicit whole-page fallback frame.

`main.js` provides local-file/demo opening and touch/keyboard controls with visible
errors. The renderer, navigation, full-page image URL lifecycle, resume and ZIP
inflation remain upstream. No model, detector, credentials or paid API is used.
`guided_sequence.js` and checked build-time renderer patches supply page-first
navigation without changing the saved ACBF geometry or its panel order.

`visible_thumbnails.js` supplies previews near the horizontal strip's viewport,
with 240 pixels of overscan and at most two extraction/decode jobs at once. Each
preview uses its own temporary object URL, fits the complete page into a 120×160
canvas, then clears its image and revokes the URL. Small canvases survive strip
hide/show for the current book; closing or replacing the book releases them.
The pinned renderer patch preserves thumbnail buttons and scroll position on a
page jump. `test-thumbnails.html` exercises cancellation, stale work, concurrency,
whole-image fitting, and failed-preview navigation in a browser; actual full-book
memory measurements remain separate from those controlled checks.
Thumbnail toggles reframe the guided view without starting another prefetch.
The renderer patch also coalesces pending guided prefetches for each page and
binds them to the current book and its open-session panel cache. A canceled or
failed decode cannot seed geometry for a different book or a reopened session.
Speculative page-load failure leaves the current page open; explicit navigation
retries the load and uses the normal visible error path if it still fails.

This supports our tested profile, not every ACBF document or ZIP variant. Limits:
128 MiB archive, 2 MiB XML, 2,000 entries, 32 MiB per entry, 512 MiB declared
expanded size, 600 pages, 200 frames/page and 40 MP decoded images. PNG/JPEG and
stored/deflated non-ZIP64 archives only. Frame bounds are checked against decoded
image dimensions. The image pixel limit is checked **after** decoding; it is not
a hard peak-memory guarantee. Upstream ZIP code does not verify CRCs or thoroughly
validate every header. This is not a hostile-archive certification. No XSD schema
validation, encrypted/RAR/PDF support, text-layer rendering, physical-phone/Safari
qualification or full-book memory measurement is claimed. `DecompressionStream`
with `deflate-raw` is required for compressed CBZs.

Only browser-local reading position is retained. Keep private comics out of the
static site's directory. A reload obtains an updated candidate without installing
an app; no service worker is registered by this entry point.

## Reproduce inside a disposable VM

Follow the home-lab skill/global isolation rule. Use a new workspace and output
directory per build; never execute the candidate on the stable host. The tested
Debian 13 VM has `python3-pil`, `fonts-dejavu-core`, `curl`,
`chromium-headless-shell`, and `python3-websockets`. It needs no Node build step.

Fetch the pinned GitHub tarball into the candidate workspace:

```sh
curl --fail --location --output panelview.tar.gz \
  https://api.github.com/repos/wenn-id/panelview/tarball/ba86994fd8b8c99b62e960bccbeb51a576772f03
sha256sum panelview.tar.gz
mkdir upstream
tar -xzf panelview.tar.gz -C upstream --strip-components=1
```

The observed tarball SHA-256 is
`fcc1065133658434416f5a9f3fd14780a25c09c61cd2d256878874e3f0d3ef00`.
Verify it before extraction/use; a changed archive needs inspection. Copy this
prototype and `prototypes/comic_panel_e2e` to the VM, then run there:

```sh
python3 source/web_panel_reader/make_fixtures.py fixtures \
  --adapter-directory source/comic_panel_e2e
python3 source/web_panel_reader/build.py upstream fixtures build-1
python3 -m http.server 8080 --bind 0.0.0.0 --directory build-1
```

The builder copies pinned renderer modules and their original MIT `LICENSE`,
then overlays this experiment's entry point, parser and template changes. It
refuses existing output directories. Fixture generation creates new synthetic
art and CBZs; timestamps/IDs mean it does not reproduce the historical Android
fixture hash. The duplicate ZIP fixture intentionally contains a repeated member.

Use an isolated headless browser/profile inside that VM. Once its CDP endpoint
is available, the rendered acceptance runner uses real pointer/touch/file-input
events and preserves screenshots/results in a new directory:

```sh
python3 source/web_panel_reader/browser_check.py \
  http://127.0.0.1:9222 evidence/acceptance-new
```

The runner currently assumes fixtures are under `/home/tester/comic-reader/fixtures`
and the candidate is served on VM loopback port 8080. Adjust those test-only paths
for another disposable deployment. The separate `test-acbf.html` reports six
parser/archive checks in a rendered browser. This is not a phone-device test.

For an actual book, `traversal_check.py CDP_URL NEW_EVIDENCE_DIR SITE_URL CBZ
EXPECTED_BUILD EXPECTED_DIRECTION`
traverses every page overview and every ACBF frame through normal pointer events.
It independently reads the archive, hashes the displayed source image per page,
checks metadata order/geometry and settled framing, and streams step evidence.
It captures selected pages and failures, checks the end boundary, verifies cached
page URL revocation on close, and verifies reopening at the saved final step.
It preserves normal camera transitions and does not change reader code or metadata.

`traversal_run.py LABEL NEW_EVIDENCE_DIR SITE_URL CBZ --max-seconds 3600
--expected-direction ltr`
runs that harness only in the disposable Orca browser guest. It starts an isolated
Chrome profile, records process RSS every second, enforces a 4 GiB aggregate RSS
bound and a wall-clock bound, and verifies all owned Chrome processes exit. Keep
both traversal files and `panelized_check.py` together. Direction is independently
checked against the hash-bound publication profile and the supplied source
expectation. The current default expected reader build
is `e5a769ca768d395e`; deliberate build changes require a new qualification.
See the [traversal validation report](../../specs/research/reader-traversal-validation-20261009.md)
for the small-book checks and the remaining full-artifact test.

## Review deployment and teardown

For an offline replay, run `replay_saved.py SOURCE_PDF HISTORICAL_MANIFEST NEW_DIR
--mode gemini` (or `--mode local`) inside staging. It refuses an existing directory
or a mismatched source PDF and retains every recorded frame unchanged. Prepare
`replay-gemini/` and `replay-local/`, then pass their parent via `build.py
--saved-books DIRECTORY`. The builder verifies each CBZ against its replay hash
before including it. `check_saved_books.py NEW_PRIVATE_EVIDENCE_DIRECTORY [BASE_URL]`
drives the gallery and actual reading flow; keep its real-comic screenshots out of
Git. The general `browser_check.py` also accepts an optional site base URL after
its evidence-directory argument.

The authoritative inventory is the home-lab registry record
`comic-panel-reader-stage`, linked to `machine-bumble`. It records VM identity,
source/build paths, service, relay, health probe and cleanup procedure. Read it
fresh before operating on the lab. The review VM is retained for Chris; the
recorded review expiry is manual, not an automated deletion timer.

The stable Mac only runs the SSH relay and BB Connect share. The enabled static
HTTP service executes in the VM. No production installation was promoted. Before
teardown, export any new source/evidence; then stop only the recorded relay/share
and verified disposable VM, and update both registry records. Do not touch other
VMs, services, browsers or stored books.
