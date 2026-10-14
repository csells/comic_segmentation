# Actual source 57: V30 automatic conversion and review

2026-10-09. **The V30 converter automatically accepted all 13 scenes on source page 57, emitted a one-page CBZ, and passed browser playback of its overview followed by all 13 panels.** Personal review found no missing target content in the selected viewports. This is one difficult development-page result, not qualification of the full anthology or unseen comics.

## Actual pipeline and selected artifact

The input was the original full 257-page PDF, SHA-256 `30d075d2bf54cdcd2401ccf905ab50a859779296e7afdbff404efd291f42cd32`, with its verified render cache, explicit LTR and `--pages 57`. The converter retained real predecessor context from pages 55 and 56. It used the frozen `automatic-source-ownership-v30` runtime: actual detector responses, automatic routing, source ownership, crop checks, bounded repairs and publication. Saved provider responses were reused by exact request identity; selected geometry, expected labels and human routing were not imported. Human inspection was evaluation only.

The attempt sequence was Sol-low, Sol-high, Astra-high, then two Astra geometry repairs. The final candidate retained the 13-scene inventory and order. Its source-evidence link resolved, its complete-candidate ownership confirmation passed, and all 13 required marked target checks passed before automatic acceptance. The [V30 lineage correction](ownership-lineage-v30-20261009.md) keeps those checks binding through repairs; source evidence alone cannot accept a crop.

Selected candidate: `9452859ab41cc6d150cd18821b308ea1d211e7d92284f4ebcd892754c0460a98`.

Published CBZ SHA-256: `a050b65de50363e090d59a65753910a2831dbe23ac703b9b8eaf9fbeeb58def8`. Output ordinal 1 is original source page 57. The archive contains the complete original page image, 13 ordered ACBF frames on its cover page, and an LTR reader profile bound to the actual metadata hash. A cover-only single-page book must retain all 13 frames; the intended reading sequence is one overview followed by 13 panels.

## Visual evidence and remaining presentation limits

The root reviewer inspected the full source and all 13 first-repair crops. The final repair changed only targets 4 and 10; those two exact crops were viewed freshly, while the other 11 retained the previously inspected byte hashes. The final review export's 13 crop hashes match that recorded review. This report's author additionally inspected the changed 4/10 crops and the accepted controller trace. No target omission or inventory/order discrepancy was identified in this selected artifact.

The prior [target-10 warning is an independently documented false positive](page57-target10-verifier-disagreement-20261009.md): its pink taper was already inside the first-repair viewport, which contained the V5 positive plus one extra source column. The automatic second repair expanded target 10 leftward by another nine source pixels. A separate marked target-4 clipping warning also contributed to that repair; its necessity has not been independently adjudicated. Therefore the target-10 expansion is unnecessary, but the entire second repair and its whole cost are not classified as unnecessary. The first-repair complete-candidate check passed; the target-4 warning was local, despite the provisional human note calling it global. The original note is preserved unchanged.

Rectangles around these curved scenes retain substantial partial neighboring artwork, especially in views 1, 7 and 13; target 10 includes neighboring cannon art while preserving its own long taper. These are usable complete viewports, not isolated scene masks. Near-white boundary samples remain visually ambiguous. This result does not establish pixel-perfect segmentation or exact generated object annotations.

## Costs and preserved predecessor evidence

| Run/checkpoint | New requests | Incremental reported usage | Result |
| --- | ---: | ---: | --- |
| Original V29 source 57 | 96 | $2.766642 | Stopped at its request ceiling; no accepted page or publication |
| V30 source 57 | 34 | $1.155186 | Accepted after two geometry repairs; 129 cache hits; 633.483 seconds |
| Shared V29/V30 regression suite at this terminal | 130 | $3.921828 | Counts and spending retain the V29 work |

Global spending at this terminal is **$46.773160 used/held of $100**, leaving **$53.226840**. The conservative earlier holds remain included. These are checkpoint values; the handoff and ledger own subsequent spending. The V30 duration and $1.155186 are incremental measurements with substantial cache reuse, not a cold conversion cost or a normal per-page estimate. The original V29 terminal and its unaccepted diagnostic review were not rewritten as a pass. A guarded, zero-dispatch V30 replay first exposed an actual uncached target check before the additional bounded paid run.

## Actual browser playback and qualification boundary

The exact emitted CBZ passed the unchanged candidate reader `e5a769ca768d395e` in isolated staging: Chrome 155.0.8059.40 on macOS 26.6.2 arm64, with a 390×844 mobile viewport. The browser worker inspected all 14 settled screenshots: one complete-page overview, then all 13 panels in the emitted ACBF order. Every frame matched the metadata dimensions, used a connected current-page image bound to the expected source/cache entry, and was contained and centered in the reading viewport. The final navigation boundary passed, no uncaught exception occurred, and the archive hash remained unchanged. There were no browser-side metadata corrections or model calls.

The screenshots retain the same substantial neighboring artwork visible in the rectangular crops; playback does not make them isolated scene masks. This was a mobile-sized Chrome test in a disposable VM, not physical-phone or Safari validation. This report's author checked the saved result and provenance; the browser worker performed the full screenshot inspection.

A separate catalog-route run also passed: an actual pointer click on **Page 57 · 13 panels** downloaded the exact archive and traversed the same 14 steps and final boundary with zero exceptions. Its 15 screenshots include the catalog; five were freshly inspected and ten were byte-identical to the already inspected playback screenshots. The disposable VM153 review site at port 8085 uses the identical tested reader code, with only `catalog.json` changed and `radial-page.cbz` added. Stable Build10 and the prior candidate site remain unchanged; this is staged review, not promotion.

The remaining development regressions, contiguous-prefix requalification, panelized PDF/CBZ/CBR/folder parity, independent books/RTL material and the requested full 257-page review remain open. Source 57 does not extend the historical V28 prefix 1–56 into a common-policy V30 prefix. The older description-omission failure and disjoint-proposal routing limitation also remain. No stable-service promotion or Rust production rewrite follows from this single result.

## Evidence locations

VM runtime: `/home/tester/comic-reader/evidence/actual-v29-regressions-v1-20261009/source-57-v30/`. Verified local review material is under `validation-artifacts/segmentation-iteration-20261008/actual-v30-source57-accepted-20261009/`, including the actual run, terminal, accepted page record, selected-candidate review export and CBZ. Root's earlier visual receipts remain in sibling `actual-v29-live-inspection-20261009/proposal-6a8c21f1f7cc/` and `proposal-9452859ab41c/`; their provisional timestamps/roles are not altered by the later acceptance.

Browser evidence is in sibling `reader-v30-source57-20261009/`: `actual-v30-source57-browser-evidence.tgz` contains the results, source/candidate provenance and all 14 screenshots. Its 4,980,060 bytes hash to `21ac036f087acd1bb68f84d3c5033084d465a038c7b34bf461bf0992291c45ad`; the browser worker fully read all 29 regular archive members. Extracted `browser-evidence/actual-v30-source57/browser-results/results.json` hashes to `0767a2ba21f24686cf43aa75892dec561acbcfb0b1c180b6f355957fa0259f6b`, and sibling `provenance.json` hashes to `6114fb97a0bbc91d497e5180eebc89dd8fb70dc34d7d5ba2fb0cd97597a3eebc`. Those records bind original source 57, output ordinal 1 and the selected candidate/CBZ above.

The catalog-route receipt is `phone-review-visual-review.json` in the same artifact root. Its browser export `phone-review-source57-browser-evidence.tgz` hashes to `aa0dbdb35077204dc32c64ab5d51b2ea3c3a5ee72ae9af09f3b21bf10c83c981`; the immutable site/provenance export `phone-review-source57-site-evidence.tgz` hashes to `269d967f79dd3af7bc2794624b32f3d3e2cfe9f5e3c8d0b8019edcc2cd495346`. The site provenance records the exact two catalog/archive changes and identical reader assets.

| Saved file | SHA-256 |
| --- | --- |
| `run.json` | `300cbb63c0fe863d9fee0be4dbf8c190e5767e165dfc44081772e61746203d3b` |
| `page-0001.json` | `6da8d270b235f578fe7c1cb147193ca1c421597f73532183877c7de909f5d260` |
| `regression-terminal.json` | `152c39c12d2201624cb132c428833adbaf4999b2e86637d7d39de30aedd3deae` |

The source-page JPEG hash is `910bbb7a131122ea3a7b102ec40fbea4193758ecc2abfa16e793c48626cd34b1`. No API calls or application runtime were executed to write this report.
