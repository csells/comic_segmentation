# Page 57, target 10: false clipping warning on a complete viewport

Independent evaluation on 2026-10-09 finds **no visible target-10 omission in the current crop**. The Sol-high marked check's claim that the left edge cuts off the pink inner continuation is a false positive at the frozen reading-viewport standard. The pink taper is visibly inside both the left and top crop boundaries. This conclusion does not certify a pixel-perfect mask or assign ownership to every near-white JPEG sample.

The review inspected the complete source, the actual current and V5 crops, both pairs of unmarked/marked source details, and the previously generated 4× nearest-neighbor hub view. The source and all inspected files remain unchanged. No new image processing, API call, runtime override, manual geometry or routing decision was introduced. The independent finding does not replace the automatic verifier's recorded result.

## Exact crop and verdict comparison

Both runs use the same 1128×1648 source JPEG, SHA-256 `910bbb7a131122ea3a7b102ec40fbea4193758ecc2abfa16e793c48626cd34b1`.

All bounds below are source pixels in **left/top/right-exclusive/bottom-exclusive** form. Earlier four-corner strings use inclusive right/bottom coordinates; their ending `1094,1293` therefore means exclusive `1095,1294`.

| Evidence | Bounds | Actual crop SHA-256 | Recorded Sol-high verdict |
| --- | --- | --- | --- |
| V5 `final57-padded`, check 5, target 10 | `[720,998,1095,1294)` | `882919961fd2a449095139a6cbced5d2c60291b2a253bb9ea3bd73344b7e6c36` | Accept; all predicates pass; no issues |
| Current first-repair crop, checked during V30 | `[719,998,1095,1294)` | `ba9880325a3f07a17d8a2aa93882957b3a88ad2e6723249d8ac586fdd0fe6857` | Escalate; inventory/order pass; coverage fail; target 10 clipped-art issue |

The current source rectangle contains the entire V5 rectangle plus one additional column on the left. The JPEG files are different encodings and are not asserted byte-identical within their common region. The source-coordinate inclusion, inspected geometry and visible artwork establish that this later viewport did not narrow the previously reviewed target.

The negative request is `45ed785f165a9fa8ee9644d64266992e3b3b9f5b6146e7668a9277e943494dcc`; the V5 positive is `c8703893ab1d8be82549d4731e80608ee8a8895d2f17ac9470450bc43c3d9c4f`. The current explanation specifically says that “its left edge cuts off the narrow pink continuation toward the central convergence.” It acknowledges that both figures are present and identifies no other defect.

Tracing the pink field from the hub to the confrontation shows its narrow inner tip to the right of the marked left edge and below the marked top edge. Its pale continuation widens into the goggled foreground figure's scene without leaving the viewport. The head covering and trailing strands, foreground face, nearby raised-hand/pointed detail, looping lash or cord, standing figure and outer pink edge are retained. No target lettering was identified on the source. The viewport also contains incomplete cyan, green and violet neighboring material; those fragments do not establish target-10 clipping. The source contains no identified detached pink target component outside this viewport.

## Why the verdict changed is not established

The two requests have the same non-image/non-input model configuration, including `gpt-6-sol`, high reasoning and the 8192-token allowance. Their target-check prompt and fallible auxiliary instructions match exactly. They nevertheless are not a controlled one-factor comparison:

- The automatically generated scene inventory and ownership descriptions differ. Both describe the same pink confrontation and its inward continuation; neither supplies an expected verdict.
- The complete candidate's normalized geometry differs for orders 4, 6, 8, 10, 11, 12 and 13.
- The current target crop adds one source column; its detail starts at x=651 rather than x=652. Both detail bounds otherwise remain y=899 to1392 and right=1128. This changes both source-detail JPEGs and the generated boundary image.

Description sensitivity, neighboring-scene confusion and model variability remain possible explanations. These artifacts do not identify which caused this false alarm. They also do not reverse the earlier failed description-omission control or prove that source-audit descriptions are sufficient for all layouts.

The [pre-inference source audit](page57-v28-independent-audit-20261009.md) already distinguished ambiguous near-white edge samples from clearly missing target artwork. Its padded positive remains unchanged. The [V5 independent review](ownership-viewport-v5-review-20261009.md) is also preserved. This new automatic false positive is a separate cost/coverage limitation: a complete viewport can trigger extra repair despite valid source ownership. It is not evidence of a harmful accepted omission in this crop.

At this review checkpoint, the bounded automatic run had begun its second model repair; its eventual acceptance or fallback is not claimed here. Any later viewport and the final emitted artifact require their own assessment. This review applies only to the exact current crop above, not all page-57 crops, the whole page, the book or generalization.

## Saved evidence

The current crop and bundle are retained under `validation-artifacts/segmentation-iteration-20261008/actual-v29-live-inspection-20261009/proposal-6a8c21f1f7cc/`. This is the byte-identical crop from the frozen V29 attempt that the V30 exact request used; it is not a selected or published V29 result. Current request, response and both details are in the sibling `repaired-target10-disagreement/` directory:

| File | SHA-256 |
| --- | --- |
| `request.json` | `1169eec69fdaefb28b11e152ed541cf4313e8a514f637067356b0f2f7ae24ab5` |
| `response.json` | `62ea1b2e67d94e1f9b0119a5a0a492122e7c5b1cb28ab4073b60abdc6227e9a8` |
| `target-10-source-detail-v1.jpg` | `564f041028c71ed26e91e974b28bc9882ac7c24b92967f002b47740ddf7b1135` |
| `target-10-crop-boundary-v2.jpg` | `35cf25fe20c7664bc5009f02cfd6f41891cc5372f0df4ccd930d8a294599cc87` |

V5 evidence is under `ownership-viewport-v5-completed-20261009/`: `check-5-bundle.json`, `check-5-result.json`, `final57-padded/crop-10.jpg`, `details/5/` and its saved request. The source is the same verified `seeded-boundary-spike-20261009/final/inputs/0057.jpg`; existing magnification provenance is `source57-fresh-audit-20261009/manifest.json`. All these paths share the artifact base `validation-artifacts/segmentation-iteration-20261008/`.
