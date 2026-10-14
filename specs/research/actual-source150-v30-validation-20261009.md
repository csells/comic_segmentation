# Actual source 150: V30 bouquet-ownership regression

2026-10-09. **V30 automatically accepted three scenes on source page 150 and passed actual catalog-to-reader playback. Independent inspection of the original source and all three selected crops found the complete thrown bouquet in the lower scene.** The actual path escalated Sol-low → Sol-high → Astra without a model geometry-repair round. This is a known development regression, not unseen-book accuracy.

## Automatic path and selected artifact

The run used `automatic-source-ownership-v30`, the original full 257-page PDF, explicit LTR and original source selection `[150]`. Its PDF hash is `30d075d2bf54cdcd2401ccf905ab50a859779296e7afdbff404efd291f42cd32`; output ordinal 1 maps to original page 150. Exact cached provider responses were reused through the converter's ordinary routing. No expected labels, manually selected final geometry or human verdicts entered the runtime.

Sol-low escalated because of overlapping scenes. Sol-high's candidate still described the bouquet as carriage decoration and started the lower view partway through it. Its native lower-target art risk was only 0.18, but the required source-evidence-aware complete-candidate check rejected that crop: the flowers and looping ribbon belong to the lower scene, and their presence in the middle crop cannot complete it. The controller escalated to Astra instead of accepting the native result.

Both new Astra source audits were inspected independently against the full source. The audit of Sol-high's misleading proposal explicitly corrected the carriage-decoration claim, associated the uninterrupted flowers/stems/ribbon and reaching hands with scene 3, and kept the distant entrance/carriage view as scene 2. The audit of Astra's corrected proposal retained those same ownership distinctions. Their relevant identities and owned-content lists agree with the source. The saved Sol-high-proposal audit request contains the generic source-audit prompt, automatic proposal descriptions/boxes and one full-source image; it contains no output crops or human expected ownership label.

Astra's automatically returned three-scene proposal retained the bouquet in the lower view. The selected source-evidence gate resolved to Astra evidence `f5e18a15fc2a53c25b05afc55ca8aec1628c1cc72c74f688bfe5084cf4ba2aad`, bound to proposal `361cc7631b9af29c6796537d3ccfeda2262037ab8a181b330b545551817286cd`. Despite quiet native target flags, crossing-art risk kept targets 2 and 3 mandatory. Complete-candidate ownership confirmation and both marked target checks passed. The final source inventory, order and crop checks stayed independent; source evidence alone did not accept the page.

Selected identity: `282930df729dbe0e30a0ab8eb37282cf8056d39cb12bfa91e387a8874a539819`.

Published CBZ: `665bce6d0c5044d14ce361b3813ec52fa78da248596aa5aad75d1d918d604b5a`. It contains the original page JPEG, three ordered cover-page ACBF frames, and an LTR profile bound to metadata SHA-256 `5047d385c3b710b08274da00a82d6826413a1e20c79920a787762e4d004192bf`. Reading is intended to show one full-page overview, then the three frames. The selected candidate received the generic once-only reading margin; “zero repairs” means zero model geometry-repair rounds, not unmodified detector coordinates.

## Independent visual assessment

Root and this report's author separately viewed the full source and all three actual selected crops. The first view retains the church greeting and both balloons; the second retains the entrance/carriage scene and its balloon; the third retains the couple, all three balloons, reaching foreground hands and complete thrown bouquet, including its upper flowers, ribbon loops, stems and small detached colored flecks. No inventory, order or target-content omission was identified.

The lower crop's exact pixel bounds are `[46,646,1074,1633)` with right/bottom exclusive. Its normalized box is `[392,41,990,951]` in top/left/bottom/right order. The rejected Sol lower crop starts at normalized top 512 even after padding, compared with Astra's raw top 400 before padding. The change therefore addresses ownership across the frame boundary; a small reading margin alone did not repair the wrong Sol proposal.

The middle view contains an incomplete portion of the lower scene's bouquet. That incidental fragment is not a missing component of the middle scene. Conversely, the lower rectangle includes a substantial strip of carriage art above the gutter to preserve its own bouquet. These are complete reading viewports, not isolated masks. Original page-edge truncations and the printed composition remain unchanged.

The [historical failure](full-pdf-sequential-review-20261008.md) first records harmful acceptance on page 150 under V21, followed by an earlier V23 correction. V30 independently requalifies this case under the current ownership-aware policy; it neither rewrites the old failures nor establishes that descriptions or judges are always reliable. V5's deliberately defective controls and failed description-omission ablation remain part of the evidence.

## Cost, actual browser playback and limits

The runner reports 17 new calls, six cache hits, $0.451539 additional usage and 201.0335 seconds. All three detector responses were cached. The shared V29/V30 regression suite now records 147 new requests and $4.373367; global spending at this terminal is **$47.224699 used/held of $100**, leaving **$52.775301** with prior conservative holds retained. These are incremental/checkpoint costs, not cold-run or typical per-page estimates. The handoff and shared ledger own subsequent spending.

The exact CBZ passed actual pointer-click catalog playback through **Page 150 · 3 panels** on disposable VM153 port 8085, using unchanged reader `e5a769ca768d395e` and Chrome 155 at a 390×844 mobile viewport. The full-page overview, all three ACBF frames and the final boundary passed. Every step matched the emitted source/geometry, used a connected image, and was contained and centered; zero exceptions occurred and the CBZ hash stayed unchanged. The browser worker personally inspected all five screenshots, including the catalog and the complete bouquet in panel 3. This reviewer read the saved results and provenance. No browser-side geometry correction occurred. The existing source-57 book and reader code were preserved byte-for-byte; only the catalog changed and `bouquet-page.cbz` was added.

The remaining development cases, contiguous-prefix requalification, panelized PDF/CBZ/CBR/folder parity, independent books/RTL, physical-phone/Safari behavior and full 257-page review remain open. Source 57 and 150 are separate passing development cases, not a qualified contiguous V30 prefix or universal accuracy claim. Stable services and Rust production implementation remain unchanged.

## Evidence

VM run: `/home/tester/comic-reader/evidence/actual-v29-regressions-v1-20261009/source-150-v30/`. Verified local copy: `validation-artifacts/segmentation-iteration-20261008/actual-v30-source150-accepted-20261009/`. The review helper explicitly identifies selected geometry and source-page provenance; the archive's JPEG and metadata hashes were also checked directly for this report.

The sibling complete export `actual-v30-source150-qualified-20261009.tgz` hashes to `fbbea20b3d338f8d1a33757ca9c9fc19a9d4c9895a19336531a7086d0fb3e39b`. Its 203 regular files preserve runtime source, request/response records, both full source-evidence artifacts, candidates and accounting. The root exporter verified every member; this reviewer checked the archive hash and read the two source inventories and relevant request directly from it. The quiescent ledger audit settled all 17 new source-150 reservations to 451,539 micro-USD.

Sibling `reader-v30-source150-20261009/` retains browser results at `browser-evidence/actual-v30-source150/browser-results/results.json` and site provenance at `site-evidence/phone-review-source150-20261009/provenance.json`. Browser export `actual-v30-source150-browser-evidence.tgz` hashes to `92837cccc718f9871a99a63c0c02f13412aec2e37052acd3f22efc81e7ecc1fc` (19 regular members), and `phone-review-source150-site-evidence.tgz` hashes to `a027ab3e06f156db7ff5f4c4262ff74c5f29f87b9f794e2302f8af9ce6edc328` (30 regular members). The browser worker fully read both exports.

The browser worker's `visual-review.json`, SHA-256 `3a6a5a8f104507eefffceeae835af922d2967e82249c71e05b4d1eea796eae31`, binds all five personally viewed screenshots and records the complete lower bouquet and rectangular-overlap limitation.

| File | SHA-256 |
| --- | --- |
| `run.json` | `61ed9d507143c0e99c01ffc1d07e0813151a44af0bcd205d8e0a921fe5881574` |
| `page-0001.json` | `fbc139a277d25a681d27af297185e85cb665312378ebeb8b8b6453fb4758a0d2` |
| `regression-terminal.json` | `fe084d6d80efe9c7bbee8e4f651de1159131ac1fb07718e9bec1edf1e6b58070` |
| `visual-review/source.jpg` and archive `0001.jpg` | `ce13e97dcf81deb016a7b3201c59d2ff1e07c0e1638cd8690fe8a1341d397e92` |
| `visual-review/crop-01.jpg` | `58c8c0d27a0eee16eb9e41eeeae6bc97216614040faa7e360f398905d7b4cac2` |
| `visual-review/crop-02.jpg` | `dcd21ac9987056dea22d2692ecb42ca815833e73405b217338cdc15dcf364fab` |
| `visual-review/crop-03.jpg` | `de32d78a86e7f766802ae2b4adeb3317db478e5b52355f1a6db6d87e738311ae` |

No API calls or application runtime were executed for this independent report.
