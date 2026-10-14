# Phone-browser reader validation

2026-10-08 build 6: [OpenAI reviewed pilot and comparison](detector-comparison-20261008.md) is now first in the same Panel Lab catalog. Twenty-five UI checks plus zero exceptions passed against temporary and published staging. Reader JavaScript is unchanged from build 5; original experiments remain. Only four detector pages plus the cover are in this new sample.

## Page-first update — 2026-10-08

Build 5 is running at the same review URL. In Panels mode each page starts with
the entire page, then visits each supplied panel in metadata order. A single
full-page frame is deduplicated. Switching into Panels resets the current page
to its overview; previous from an overview returns to the preceding page's final
panel. Existing metadata and all earlier builds remain intact.

The original build 3 failed the new overview assertion. Build 5 passes six parser
cases, seventeen synthetic UI checks, and sixteen published real-book checks
against both replay CBZs, with zero uncaught browser exceptions. Real PDF page 25
shows its overview before its five saved regions; that known merged panel is still
wrong. The 257-page archive still contains exactly 1,094 raw frames. Navigation
checks do not measure detection accuracy.

An open tab needs a normal refresh. Build-time module URLs use asset revision
`d9b4a6c82fd6adc8`; verification used ordinary reload with cache enabled. The
resume key has a page-first version suffix, preserving earlier local records
without interpreting their old panel indices as new overview indices. Failed
intermediate cache/navigation-race runs and final passing evidence are retained
privately in `validation-artifacts/page-first-20261008/vm-evidence/`:
`build5-green/results.json` and `build5-refresh-check/results.json` are the final
synthetic and published real-book runs respectively. The task VM hosts the
candidate and browser; the Mac only relays the review endpoint.

Chris rejected the original detections throughout the book and requested visual
iteration on every page. See [the active quality work](../plans/0003-segmentation-quality-iteration.md)
and [initial 257-page audit](evidence/segmentation-iteration-20261008/visual-review.md).

## Historical build-2 and build-3 evidence

Update: the [PDF replay report](pdf-saved-result-replay.md) records the recovered
source PDF and build 3's two real-comic review books. The original CBZs were not
recovered; saved geometry was reused without inference. Historical build-2 scope
and limitations below are retained as measured at that checkpoint.

2026-10-07, continuation of `49bd512`. Chris requested a home-lab web reader so
phone review does not require reinstalling an Android app. Native Android is now
later work. **The synthetic CBZ/metadata reading path passes in Chromium at phone
dimensions; physical-phone feedback and real-book replay remain open.**

Chris subsequently tried Panel Lab and reported that it “works great,” then
authorized recovering the saved real-comic CBZs for hosted review. The exact
device/browser was not reported, so this is positive user feedback rather than
an additional named-device compatibility result. Recovery requires access to
the original machine; no private artifact has yet been recovered on this host.

[Open Panel lab](https://csells-mac-mini--51996.getbb.app/) using the owner's BB
session. Choose **Open the order experiment**. Tap right/left or swipe for panels;
choose **Page** for the complete artwork. The sample is synthetic, deliberately
ordered **3 → 1 → 4 → 2**, followed by an explicit whole-page fallback. A local
CBZ with the tested metadata profile can also be selected without uploading it.

## Reuse decision

Two existing projects were inspected before implementing an adapter:

| Candidate | Source observation | Decision |
| --- | --- | --- |
| [Panel by Panel](https://github.com/ragtag/panel-by-panel/tree/f916dea4e88c5b3805ee3dbd9fc01163676982ae) | GPL-3.0; consumes ACBF, but expects unpacked books and PHP/ImageMagick. | Useful precedent; less direct for browser-local CBZ review. |
| [PanelView](https://github.com/wenn-id/panelview/tree/ba86994fd8b8c99b62e960bccbeb51a576772f03) | MIT; opens CBZ in the browser with guided/page/scroll modes and touch controls. Its supplied-panel format is Comic Sol; other books normally use heuristic detection. | Reuse the renderer and ZIP reader; add an ACBF importer and a narrow entry point. |

Pinned PanelView commit: `ba86994fd8b8c99b62e960bccbeb51a576772f03`.
The [prototype README](../../prototypes/web_panel_reader/README.md) records the
tarball hash and reproduction. Copied upstream modules retain their MIT license.
No existing product was found and claimed compatible without testing: the hosted
candidate includes our experimental adapter.

The importer supplies every page's ordered rectangles explicitly, including an
empty array when frames are absent. This bypasses upstream detection. It rejects
missing/duplicate/escaping image references and malformed geometry; decoded image
dimensions bound the coordinates. XML title content is rendered as text. Polygon
bounding boxes fit the viewport while neighboring art remains dimly visible.
This matches the experiment's full-page-plus-guidance model, not isolated crops.

## Measured acceptance

Actual candidate build 2 ran inside the disposable Debian 13 VM. The browser was
Chromium headless shell **154.0.8037.92** inside that same VM, with a fresh isolated
profile. Tests used portrait **390 × 844** and landscape **844 × 390** viewports.
These are desktop browser emulations, not Android Chrome or iPhone Safari passes.

The [retained results](assets/web-reader-validation-2026-10-07/results.json) record:

- Six browser parser/archive cases: cover once and exact frame order; literal
  title and no-frame handling; reference/path failures; XML/namespace/DTD/geometry
  failures; actual deflated CBZ image decode; duplicate archive member rejection;
  bounds rejection. Related assertions are grouped into six cases.
- Fourteen rendered input/navigation checks: guided cover, first panel 3, next 1,
  previous 3, swipe advances once, synthetic click suppression, next 4, next 2,
  whole-page fallback, previous across the page boundary, ordinary page mode,
  local file-input opening/resume, uncompressed adapter CBZ loading, and visible
  malformed-archive error.
- Zero uncaught browser exceptions in the final run.
- Existing converter adapter **7/7** and Gemini contract **8/8** offline tests
  passed again in the disposable VM. No model request was involved.

Screenshots: [phone landing](assets/web-reader-validation-2026-10-07/01-phone-landing.png),
[panel 3](assets/web-reader-validation-2026-10-07/03-panel-3.png),
[panel 4](assets/web-reader-validation-2026-10-07/04-panel-4.png),
[rotated panel 2](assets/web-reader-validation-2026-10-07/05-landscape-panel-2.png),
[fallback](assets/web-reader-validation-2026-10-07/06-whole-page-fallback.png),
[full page](assets/web-reader-validation-2026-10-07/07-page-mode.png), and
[visible error](assets/web-reader-validation-2026-10-07/08-visible-error.png).

The new sample is generated with the existing adapter and new synthetic PNGs,
then repacked with ZIP deflate. It has three images and ordered frames; its
whole-page fallback is `(0,0)…(999,1499)` on a 1000 × 1500 image, the adapter's
inclusive pixel profile. It is a new artifact, not a recreation of the historical
Android control or of a paid conversion. Its hashes and candidate source hashes
are retained in the adjacent artifact manifest.

## Diagnosis and test limits

The first inline test page failed to parse because a literal closing script tag
appeared in a JavaScript assertion. Splitting that literal fixed the test harness;
the next run correctly failed on the absent ACBF module before implementation.
After implementation all six cases passed. The first navigation run expected
1000 × 1500 for fallback but the existing adapter emits inclusive endpoints
999 × 1499; the expectation was corrected after inspecting the archive and reader
state, without changing adapter geometry. A final screenshot run waits for the
250 ms page entrance animation so the full-page evidence is not captured mid-fade.
Adding a stored-CBZ case also exposed a test that could observe an old hidden
page after close; file-opening checks now require a live book, visible reader and
decoded image before continuing.

Mac Chrome for Testing could not render reliably in this remote/headless context.
It was closed by its exact task-owned PID; browser verification moved into the VM.
The 512 MiB VM initially could not reserve Chromium's V8 code range; a task-only
1 GiB swap file allowed startup. DBus/DRM warnings reflect its headless environment;
rendered tests subsequently passed. No user's browser or stable service changed.

Supported input is deliberately narrow: root ACBF 1.1, JPEG/PNG pages, stored or
deflated CBZ, with documented resource limits. No general hostile-ZIP audit or CRC
verification, XSD validation, Safari compatibility, full-book memory performance,
RTL acceptance, pinch-zoom quality or physical-device result is claimed. The
browser needs `DecompressionStream` support for raw deflate. Full-page availability
does not mean lettering is readable at every phone scale.

The private full-book and Gemini CBZs from the original machine are absent here.
They were not regenerated or copied into the web root. Recover and hash-check
those artifacts before a real-comic browser replay. The known Gemini panel merge
remains unresolved; this reader proves metadata transport, not segmentation quality.

## Hosting and continuation

The authoritative home-lab record is `comic-panel-reader-stage`, depending on
`machine-bumble`. The candidate lives in a newly created disposable VM; an enabled
systemd unit serves static files. A dedicated Mac launch agent relays traffic to
it, and BB Connect supplies the HTTPS review address. No credentials or private
books were copied to the VM. Candidate source and synthetic screenshots were
exported to this checkout on a separate physical machine.

Direct VM/relay health returned HTTP 200. An unauthenticated request to the BB
share returned HTTP 401 as expected; authenticated phone access is for Chris to
review. The agent did not claim an authenticated remote-browser test. The registry
has a recurring HTTP health probe, observed healthy with HTTP 200 after registration;
its current observation should be read from
the record rather than treated as a perpetual availability guarantee.

Retain staging for review. Its manual review-expiry date and exact teardown steps
are in the registry; do not delete it automatically or promote it to a stable
installation. Future candidate builds use new directories and the same review
address. Continue with phone feedback and recovered real books, then discuss the
[Rust plan](../plans/0002-quality-gated-rust-cli.md). No Rust rewrite or new inference
was started for this experiment.
