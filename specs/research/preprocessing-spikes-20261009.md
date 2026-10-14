# Source and verifier spikes narrow the next experiment

Follow-up: Chris authorized the second isolated VM. The [specialist-mask and
semantic-point experiments](specialist-mask-spikes-20261009.md) and
[seeded-boundary screen](seeded-boundary-spike-20261009.md) have now run. None
qualifies an automatic repair. The later ledger is $39.009825 used or held of
$100, leaving $60.990175. The preparation state below is historical.

2026-10-09. Three research-driven experiments have now run in disposable VM153: a native-PDF/source-threshold audit, the new `paneldet` baseline, and a cheaper source-detail verifier control. **None supplies a quality improvement ready to integrate.** Lossless/higher-resolution rendering did not separate page 57's thirteen scenes through simple components; `paneldet` failed all twelve deliberately difficult screening pages; Sol high falsely accepted a known clipped bouquet. The V28 production-candidate policy is unchanged: page 57 remains a whole-page fallback, the current qualified prefix is 1–56, and no page 151 has been dispatched. Earlier personal review through page 150 belongs to prior policies.

The [broad research report](<../../reports/Robust comic panel segmentation.md>) remains the architecture proposal. These results favor testing semantic-seeded masks and competing-region ownership, rather than repeating threshold sweeps or weakening the verifier. They do not reject preprocessing, deterministic methods, or cheaper verifiers as whole classes.

## Native pixels contain no hidden high-resolution boundary answer here

`pdfimages` inspection covered all 257 PDF pages and found 264 large artwork images with each dimension at least 1000 pixels. Their reported resolution is 150 ppi. On page 57 the RGB raster is 1133×1653. Its accompanying 2953×4308 soft mask is listed at 391 ppi, but extraction and inspection found a constant opaque range of `(255, 255)`. **That larger mask contributes no extra artwork-edge information.** This is a finding about the inspected source, not an assertion that arbitrary PDFs lack vector detail or that native-image extraction always reproduces a composed page.

The experiment compared the existing cached 150-DPI JPEG with lossless PNG page renders at 150 and 300 DPI. The offline [probe](../../prototypes/panel_quality_probe/experiments/preprocessing_v1/probe.py) uses the same thirteen saved automatic panel proposals, converts their bounds to each source's integer pixel coordinates, then builds 8-connected foreground masks where the minimum RGB channel is below 220, 235, 245, 250, 253 or 254. It counts significant components and records candidate associations to proposals; these associations are diagnostics, not semantic truth or accepted corrections.

At thresholds 220–245, all three input variants produce twelve significant components and at most ten distinct selected components for thirteen proposed panels. At 250 and above, regions merge. The threshold-245 overlay was personally inspected. **Neither lossless rendering nor doubling render DPI made this component method resolve the page.** No claim of better crops follows from these measurements, and no source image or converter output was replaced. The experiment has not yet evaluated automatically seeded watershed, GrabCut, learned masks, adaptive thresholds, denoising or local-contrast variants.

Evidence: VM153 `/home/tester/comic-reader/evidence/preprocessing-native-audit-20261009`. The source PDF and saved model responses remain unchanged. A 300-DPI rasterization is an analysis derivative; it is not evidence of additional source detail.

## A fast new classical baseline fails this difficult screen

`paneldet` v0.2.1, pinned to commit `f0ef27986969fce6ca2dd75e2be2962b56db376c`, ran on twelve cached pages in VM153. The trial used RGB inputs, the default automatic engine and enabled deskew; every reported angle was zero. SciPy 1.17.1 was installed into an isolated `--target` dependency directory. On the 1-CPU, 512-MiB guest, recorded per-page execution was 0.252–0.373 seconds. This timing is specific to this setup and does not include a deployment-wide cold-start or acquisition comparison. ([Upstream pinned source](https://github.com/jsneij/paneldet/tree/f0ef27986969fce6ca2dd75e2be2962b56db376c))

| Original PDF page | Returned regions | Personally inspected structural defect |
| --- | ---: | --- |
| 5 | 3 | Combines upper scenes and insets. |
| 18 | 1 | Returns the whole page instead of its distinct scenes. |
| 21 | 3 | Combines the upper montage. |
| 25 | 4 | Merges the two upper scenes. |
| 40 | 5 | Merges lower scenes and clips a head. |
| 57 | 1 | Returns the whole page instead of thirteen curved regions. |
| 72 | 9 | Splits a balloon strip. |
| 100 | 6 | Invents a vertical strip. |
| 144 | 2 | Combines four montage regions into two. |
| 150 | 2 | Merges the middle and lower scenes. |
| 254 | 1 | Returns a whole-page region, losing distinct scenes. |
| 256 | 5 | Invents regions from floor fragments in the splash. |

All twelve overlays were personally viewed. Each exposes sufficient structural failure to reject the configuration; a complete pixel-level crop acceptance audit was therefore unnecessary and was not claimed. **Twelve failures on selected difficult development pages is not a general accuracy estimate.** The result establishes that this configuration is not a drop-in replacement for the current semantic detector on our hardest examples. Further tuning needs a specific hypothesis, rather than indiscriminate parameter search.

Evidence: VM153 `/home/tester/comic-reader/evidence/paneldet-spike-20261009`.

## Sol high misses a known clipping defect in the marked-detail control

The cheaper-verifier spike held the source-detail v2 prompt and control inputs fixed while substituting Sol high for the stronger verifier. Four development controls were planned, with an explicit stop at the first wrong decision. They are known positive/negative controls, not a held-out estimate of general accuracy.

| Control | Required result | Actual result |
| --- | --- | --- |
| Original page 57, target 6, clipped taper | Reject | Reject: correct. |
| Repaired page 57, target 6 | Accept | Accept: correct. |
| Original page 150, target 3, missing bouquet content | Reject | **Accept: wrong.** |
| Corrected page 150, target 3 | Accept | Not dispatched because the preceding control failed. |

Three new requests cost an estimated **$0.118908** from reported usage. The weaker verifier was **not integrated**, and the failed negative remains preserved. This experiment does not justify replacing scoped Astra checks with Sol high; two successful controls did not compensate for a harmful false acceptance. Evidence: VM153 `/home/tester/comic-reader/evidence/target-detail-controls-sol-v2-20261009`.

The shared ledger now totals **$38.432575 used or held against the $100 total authorization**, with **$4.30 of unknown-charge holds retained** and **$61.567425 remaining**. These are recorded/conservative accounting estimates, not provider billing receipts. No completed request or unknown held request was blindly replayed.

## Historical mask-runtime preparation (superseded by completed trials)

The next comparisons remain KoharuLayout/ShadowB instance masks and SAM 2.1 refinement of automatic proposals. A fresh disposable Tart clone, `orca-automation-comic-masks-20261009`, is configured with 8 GiB RAM, 4 CPUs and a 50-GB disk but remains **stopped**. Authoritative unsandboxed Tart inventory shows `bbrooms` running; the home-lab runbook requires serialized VM jobs. A sandboxed inventory had incorrectly appeared to show all guests stopped, and that finding was corrected. Orca's host registry revision 11 records the stopped clone.

At that earlier checkpoint, the question requesting permission for a second isolated VM after verifying headroom was unanswered. Chris subsequently approved it, and the linked specialist report supersedes the following pending-work statements. **No dependent VM start or mask-model inference is authorized by elapsed time.** No weights have been downloaded and no new specialist mask inference has run. The reader's VM153 remains separate and Build 10 is unchanged. Rust production implementation remains unstarted.

The [pinned mask runner](../../prototypes/panel_quality_probe/experiments/specialist_masks_v1/README.md)
is prepared and passed a syntax check inside VM153; loading/inference remain unverified.
It pins both model revisions and weight checksums, uses author-recommended settings,
and saves raw masks, source-coordinate boxes, timing, and peak RSS. The identical
twelve original JPEG inputs are staged locally in
`validation-artifacts/segmentation-iteration-20261008/mask-model-preparation-20261009/inputs.tgz`:
3,630,847 bytes, twelve members, SHA-256
`5e65099ca8968aa1b43332bc0fb493b4d19f34b727f55d62ae7ed74817ef7624`.
The final reader health check returned HTTP 200; VM153 has 4,781,858,816 free bytes
and no inference process remains. Registry readbacks: reader service revision 36,
Bumble revision 45, Orca revision 11. Re-fetch revisions before updates.

Verified off-VM backup: `preprocessing-controls-cap100-20261009.tgz`,
**95,629,135 bytes, 1,775 members**, SHA-256
`8bf8b933ef1e3ecda634958fcd0c44ccf84a06d3efc0f7789f866aabf14a4bd0`.
It preserves all three spike runs, pinned paneldet source and SciPy dependencies,
the $100-cap prototype code and shared ledger. The archive is retained under
`validation-artifacts/segmentation-iteration-20261008/`. Keep the older archive
chain because cached-request provenance still depends on earlier evidence.
