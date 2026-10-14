# Candidate V29 reader browser validation

2026-10-09. Final reader build **`e5a769ca768d395e`** passes nine rendered
parser/archive/profile tests, 29 navigation checks, 12 rendered-frame containment
and centering checks, four thumbnail scheduling checks, eight prefetch lifecycle
checks, and playback of eight actual converter outputs. The original 257-page
CBZ opens and navigates to its first, middle and last pages with their complete
page overviews centered. No uncaught browser exception occurred in these final
checks. No paid API request was made for this browser work.

These results qualify reader behavior and transport. The eight new outputs
contain whole-page compositions, and the original 257-page archive has known bad
segmentation. Neither establishes narrative panel-detection quality, physical-phone
memory behavior, Safari support, or a production release.

## Final candidate and isolation

The final immutable product workspace is
`/home/tester/comic-reader/candidate-v29/browser-final-v2-20261009` on VM153.
Its `site/` remains served by Python HTTP **8084**, PID **59030**. It was built
from the pinned, unmodified PanelView upstream with a fresh source snapshot and
fresh fixtures. `build.py` SHA-256 is
`b0b2e9f644d11a390a7463f3bf69f20c4051d85790ca72f0de0d42f396f62b3e`.
The frozen converter V5/runtime was not changed for these reader fixes.

The existing Build 10 service on port 8080 remains active. All eleven JavaScript,
HTML and JSON asset hashes match the pre-work baseline, and its health endpoint
still returns 200. Earlier candidate servers 8081, 8082 and 8083 were stopped only
after their source, built sites and evidence had been exported. Their workspaces
remain intact. No stable installation or existing user archive was modified.

Browser execution used disposable Orca guest
`orca-automation-comic-browser-20261009`, 4 vCPU / 8 GiB / 50 GiB. Signed Google
Chrome 155.0.8059.40 passed strict deep signature verification (Google team
`EQHXZ8M8AV`). Python 3.14.7 used websockets 17.2, lxml 6.1.3 and Pillow 12.3.0.
No host mounts, private SSH keys, API credentials or coding-agent runtime were
copied into the guest. The host performed SSH relaying, file transfer and evidence
analysis; application and browser execution remained in the disposable VMs.

Bumble and Badger could not admit a browser guest within their configured-memory
headroom. Authoritative, unsandboxed Tart inspection verified the unrelated Rooms
guest and the owned browser guest. Sandboxed Tart can incorrectly report running
guests as stopped. Rooms and all templates were preserved.

The guest browser saw the unchanged site through an SSH relay at loopback,
which is a secure browser context. Initial direct LAN HTTP failed profile hashing
because `crypto.subtle` was unavailable; that trace remains retained. No browser
security bypass was used. A user review route must use HTTPS.

## Final acceptance coverage

The real browser used actual file-input, pointer and touch events. Portrait was
390 × 844 and landscape 844 × 390.

- The complete cover/page overview precedes panels in metadata order, including
  the deliberately nongeometric synthetic sequence 3 → 1 → 4 → 2.
- Previous/next traversal, page boundaries, swipe suppression, landscape,
  whole-page fallback, page mode, local-file resume and single-page books pass.
- RTL reverses tap navigation while retaining metadata order; its label and hint
  match. A single page retains all four frames and cannot invent a second page.
- Stored/deflated archives load. Invalid XML, geometry, image references, duplicate
  entries, decoded-image bounds and mismatched profile hashes are rejected.
- The selected overview or panel remains centered and contained after both
  showing and hiding thumbnails.

The final checked harness is `browser_check.py`, SHA-256
`d3269ec3660824b08158f534d84e54b35853dee69dc9fea6d34b6b3de0493fe6`.
It requires a connected image/viewport, positive intrinsic and rendered sizes,
image URL and rectangle-cache binding to the current page, then waits for the
850 ms camera transition before measuring/capturing. The final archive's
`final-reader-suite.py` executes that exact file; `final-reader-check/checked-harness-sha256.txt`
records its hash. The build snapshot and historical `browser_check-final.py`
contain an earlier harness. This is a test-only difference; the final product
assets are the immutable build identified above.

Fourteen of the final fifteen synthetic screenshots are byte-identical to already
inspected screenshots. The remaining thumbnail-overview screenshot was inspected
again. First/middle/last full-book screenshots and actual thumbnail-strip
screenshots were also inspected. The standalone thumbnail checks pass all four
cases with zero live temporary URLs, including global two-load concurrency,
leaving the visible region, hide/book replacement, failed preview and stale decode.

## Defects found and fixed

The original reader eagerly extracted/decoded all 257 thumbnails and retained
full-page URLs for them. The candidate loads only previews within the strip's
visible area plus 240 px overscan, allows at most two extraction/decode jobs,
stores 120 × 160 previews and revokes temporary full-size URLs. Stale work cannot
draw into a replacement book. A separate real IntersectionObserver probe of the
257-page archive verifies the behavior independently of the controlled scheduler
tests:

| Position | Ready previews, cumulative | Full-page URL cache entries |
| --- | ---: | ---: |
| First page | 5 | 2 |
| Middle page | 12 | 3 |
| Last page | 17 | 4 |

All ready preview indices belong to regions actually visited. All 257 page-jump
controls remain available. The second initial full-page URL is the existing
next-page prefetch, not a retained thumbnail.

Closing thumbnails previously left the camera centered against the smaller,
thumbnail-open viewport. The candidate reframes after either toggle. Measurements
verify centering as well as containment; containment alone missed this problem.
Thumbnail-only reframing does not launch speculative next-page work.

A controlled browser reproduction also exposed a real upstream prefetch race.
Book A's pending next-page extraction resolved after opening book B. Its revoked
image decoded unsuccessfully, yet the old prefetch populated B's panel cache with
a zero-width/zero-height overview. The saved screenshot shows the replacement
page unscaled in a corner without an error. The fix binds speculative work to both
the book object and its open-lifecycle cache, coalesces duplicate work, ignores
stale work, and does not cache failed decodes. Speculative extraction failure
leaves the current view usable; explicit navigation retries and reports failure.

The reusable `prototypes/web_panel_reader/prefetch_check.py` passed eight focused
checks: different-book replacement, reopening the same book object, stale
extraction rejection, failed decode, one next-page decode for repeated framing,
valid resulting geometry, current speculative extraction failure, and explicit
next-navigation retry with the normal visible error. Original reproduction,
intermediate traces and final checks are retained.

## Actual converter-output playback

The converter agent produced one-page and three-page CBZ outputs from each of
PDF, CBZ, CBR and folder input, using completed provider-response caches with
network requests and budget reservation denied. The eight exact output archives
were opened in both the baseline and final readers. All sixteen source-page
views, LTR profile, one overview per source page, final-page boundary and unchanged
archive hashes passed. ACBF uses one full-page frame sentinel per page; the reader
collapses it into a single overview, with no duplicate guided step.

These pages are a cover, promotional composition and table of contents. They do
not test narrative-panel discovery. The converter's longer prefix stopped at an
uncached page-5 source audit before any new request; it produced no panelized
archive for this browser run.

The image-view tool misleadingly displayed some contents-page PNG previews as
black. Direct saved-pixel analysis proved these were not blank browser captures:
all sixteen final central page regions are RGB-byte-identical to the personally
reviewed baseline. The three affected intermediate/final regions also match the
baseline exactly. The comparison uses the interior rectangle
`(25,230)–(365,720)`, excluding toolbar/hint, and records hashes and zero mean/max
pixel differences in `final/final-page-pixel-comparison.json`. Root independently
viewed a final affected image and confirmed the full table of contents. This
preview anomaly is separate from the independently reproduced prefetch defect.

## Full-book transport and measured performance

Input is the unchanged existing `replay-local/local-saved.cbz`, SHA-256
`7f684110be76a478f8d79ce6c249b0d70f6ebd2ae142858942587a84365be073`:
75,362,700 archive bytes, 257 pages, 258 ZIP entries, 75,338,932 declared expanded
bytes, maximum entry 481,840 bytes and maximum image 1,858,944 pixels. These fit
the current reader caps: 128 MiB archive, 512 MiB expanded, 2,000 entries,
32 MiB per entry, 600 pages and 40 MP per image. All 257 JPEG entries were compared
byte-for-byte with the existing source render cache; decoded RGB hashes were also
recorded. Neither source nor archive changed.

Each revision used a fresh Chrome profile and the same archive, navigating through
real thumbnail controls to pages 1, 129 and 257. Cold timing begins **before**
`DOM.setFileInputFiles`; settled timing includes the camera wait and screenshot.
The shorter state-ready value is not presented as visible-ready latency.

| Measurement | Baseline eager reader | Thumbnail-only revision | Final reader |
| --- | ---: | ---: | ---: |
| Cold state ready | 0.056 s | 0.056 s | 0.053 s |
| Cold settled overview | 1.148 s | 1.149 s | 1.117 s |
| Middle settled overview | 2.559 s | 1.637 s | 1.662 s |
| Last settled overview | 1.574 s | 1.588 s | 1.581 s |
| Peak sum of Chrome process RSS | 1,708.8 MiB | 1,321.3 MiB | 1,324.4 MiB |
| Processes in peak sample | 10 | 11 | 11 |

Final peak aggregate RSS was 1,388,740,608 bytes, **22.5% below** the baseline's
1,791,770,624 bytes. This is the sum of RSS across owned Chrome application
processes sampled once per second, including detached crash helpers when present.
Shared mappings may be counted more than once; it is not physical footprint,
peak-native-memory accounting or a phone-memory measurement. Per-process
PID/PPID/RSS samples and a comparison are retained. Final JS heap samples were
1.46–1.94 MB and omit native image memory. The 4 GiB aggregate-RSS and 120 s
bounds were never reached. One trace per product revision establishes this
observed comparison, not a statistical latency guarantee.

An initial middle-page test clicked before scrolling settled. Its trace remains;
the helper now uses instant scrolling and verifies the intended button is the hit
target before dispatching pointer events. A first focused regression assertion
also sampled before settling; its subsequent diagnostic showed correct geometry.
These harness timing corrections are not recorded as product defects.

## Evidence and lifecycle

All paths below are relative to
`validation-artifacts/segmentation-iteration-20261008/reader-v29-browser-20261009/`.
Every regular archive member was fully read after export; archives remain immutable.

| Artifact | Bytes | SHA-256 | Regular files read |
| --- | ---: | --- | ---: |
| `browser-evidence-settled.tgz` | 1,044,480 | `9416a8568fe384b335a678da13ac80cf02e044d8133ef5747979a90dd770608c` | 61 |
| `candidate-vm153-evidence.tgz` | 893,386 | `b5ff3dcfe613beceb9c593248f5c47b6463d68cb0ea26cf89c1447229fd32f98` | 69 |
| `full257/baseline-browser-evidence.tgz` | 1,198,080 | `87fe9da81d1f978396ca309c00e20c679be5da79d5bd584ac88755855fb9ffe4` | 23 |
| `actual-formats/browser-evidence.tgz` | 15,073,280 | `f9bd35215750d28456ee4db409381e0bfd4600e09716bfd995e9ef5a29c447c2` | 57 |
| `thumbnails/thumbnail-transport-evidence.tgz` | 10,858,677 | `4e4045f7b552b43fd5e44c77201299269834fe19caf66f60720378298384fbc0` | 49 |
| `final/reader-final-vm153-evidence.tgz` | 1,741,316 | `f61d0e6da4ad162b6040033b3681bf29e25a1911224575d5bfd976050edfad17` | 179 |
| `final/reader-final-browser-evidence.tgz` | 13,035,343 | `7541b08d46c2ffdd859a986994fee3d98c8d26bfce8e03176c907bcee10b14fc` | 168 |

Additional thumbnail source/module/final-check archives, failed traces, exact
harnesses and standalone JSON comparisons remain alongside those primary bundles.
Browser profiles are excluded. The final browser bundle includes all prefetch
failure/pass evidence, final acceptance, actual outputs, performance and structural
checks. The final VM bundle includes both final-stage source/build snapshots and
Build 10 preservation verification.

Chrome sessions were closed through CDP and zero owned Chrome processes remained.
Four owned SSH relays were closed. The owned Orca browser VM was gracefully stopped
in 0.358 s, with its disk retained for resumption and no guest deleted. Rooms
remained running, all other guests retained their previous state, and 8 GiB of
configured running-guest RAM was released. The manual expiry remains
2026-10-11T19:37:02Z; it is not automatically enforced. Provisioning, pinned-host
provenance and cleanup receipts are retained in thread storage under
`comic-browser-provision/`, registered as `comic-browser-worker-stage` and in
`machine-orca`. Final compare-and-swap updates were read back at revisions 5 and
22 respectively, preserving the Rooms record. The worker health observation is
explicitly unknown because it is intentionally stopped, not a running service.
Additive cleanup, pixel-comparison and RSS records have their own hashes in
`final/additive-evidence-manifest.json`; the existing archives were not rewritten.

Chrome logs include unused password-store encryption and push/updater warnings,
and headless virtual-display messages. No credentials were supplied; rendered
reader checks passed. The official Chrome-for-Testing archive initially failed
strict signature verification and was replaced with signed stable Chrome without
a bypass. These retained runtime limitations do not qualify unrelated browser
features or physical-device behavior. Final staging remains for review; there
has been no promotion.
