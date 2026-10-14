# Independent review of all 13 page-57 V28 crops — 2026-10-09

All 13 exact crops from the final V28 candidate were freshly compared with the source page. Their scene inventory and alternating left/right reading sequence are coherent. Every identified actor, object, caption, and other drawn narrative detail is present at normal reading scale. **That is not a finding that all 13 viewports preserve the complete region boundary.** Target 8 still appears to lose a small pale cyan taper; target 10 has a less decisive pale pink boundary concern. These concerns should be tested through a generic viewport margin, not dismissed because the central figures are intact.

This is an evaluation-only audit. No model verdict was used as ground truth. No production prompt, runtime geometry, API call, source image, saved crop, or old label was changed. Source-coordinate observations below are inspection notes, not coordinates to feed into an automatic repair. The existing current-policy qualification of page 57 is unchanged by this report.

## Evidence and method

The source is the 1128×1648 saved JPEG with SHA-256:

`910bbb7a131122ea3a7b102ec40fbea4193758ecc2abfa16e793c48626cd34b1`

Local source: `validation-artifacts/segmentation-iteration-20261008/seeded-boundary-spike-20261009/final/inputs/0057.jpg`.

The candidate is the saved VM bundle:

`/home/tester/comic-reader/evidence/component-repair-page57-v28-exact-20261009/candidates/b5cd08f0b5768683c1a6cd351598b4da2801bbe4504fa5914672fb3060f60a8d/bundle.json`.

Its local saved copy is `seeded-boundary-spike-20261009/final/inputs/0057-bundle.json` under the artifact base above, SHA-256 `b3aa2deb8ccf851a82e0caf10b40b128abfed3cbd351fa96f306050878031590`. Every crop below was located by its exact bundle image hash, so older directory names do not imply that an older geometry was reviewed.

The full source and every exact crop were viewed at original image detail. For the hub, VM153 produced unmarked nearest-neighbor and bicubic 4× magnifications with recorded source bounds. The audit inspected the nearest-neighbor hub, upper hub, and wide hub, then cross-checked the hub and wide hub in bicubic. The source already contains soft color transitions; nearest-neighbor enlarges the existing samples without inventing additional source detail.

The magnification evidence is under `source57-fresh-audit-20261009/` in the artifact base, with `manifest.json` recording the source hash, scale, and these bounds:

| Detail | Source rectangle `(left, top, right, bottom)` |
| --- | --- |
| `hub` | `(650, 900, 850, 1150)` |
| `upper-hub` | `(650, 850, 850, 1020)` |
| `wide-hub` | `(600, 880, 900, 1220)` |

These are visual inspection windows, not proposed reading viewports.

## Fresh identities and crop findings

“No omission identified” is a visual finding, not a claim of exact pixel-mask ground truth. A rectangle can preserve its target while cutting through a neighboring scene contained incidentally in the rectangle.

| Target | Evaluation-only scene identity | Fresh finding |
| --- | --- | --- |
| 1 | Upper-left tan rooftop/portal scene: walking man and seated/fallen man; first narration box. | No target omission identified. The tan taper toward the hub ends above the saved bottom y=978. An initial suspicion that its tip continued below the crop was resolved by coordinate-grounded magnification. The cut purple, green, and cyan neighbors are incidental. |
| 2 | Upper-right purple scene: distressed man with another man's head in the foreground and the associated narration. | No target omission identified. Its lower purple tip ends inside the saved bottom y=981. The clipped tan scene and its earlier caption at the left are incidental. |
| 3 | Left green scene: man leaning over another person on the ground amid equipment and walls; narration near the tapered end. | No target omission identified. Main scene, caption, and visible tapered region are present; the large cyan scene underneath is incidental. |
| 4 | Narrow right tan/brown close-up of a man's face. | No target omission identified in the final expanded crop. The face, surrounding lines, and curved tan taper are present. Purple clothing above and cyan figures below are neighbors. |
| 5 | Large left cyan scene: two men, skyline/flying craft, and spiked circular shapes. | No target omission identified. The green caption above and pink scene below are incidental; those partial neighboring scenes should not redefine target identity. |
| 6 | Narrow right cyan band with small floating/falling figures and debris. | No target omission identified in the final expanded crop. The brown face above is target 4, not the intended target. See the separate control audit for why the old original-negative/repaired-positive pair is quarantined from completeness scoring. |
| 7 | Left pink scene: man in foreground reaching toward a bearded man, flying craft, beam/action, and narration. | No target omission identified. The large tan scene occupies much of the rectangle but belongs to target 9. The center of this rectangular crop is therefore not a reliable identity anchor. |
| 8 | Right cyan scene below target 6: man with a large cannon/telescope-like device and short action lines near its muzzle. | All identified line art, device, man, and action lines are present. Magnification shows a pale, continuous cyan sweep approaching the hub slightly left of saved x=754, approximately around x=750–753. This is distinct from the darker cyan target-6 taper above it. There is a small target-region boundary loss, despite the absence of an identified missing object or text. |
| 9 | Large lower-left tan scene: two men, including a long-haired man with an eyepatch, gloved hands, and palms. | No target omission identified. The palm/region tip near the hub is inside the saved rectangle. The pink scene and its narration above are incidental. |
| 10 | Right pink scene: large goggle-wearing head on the left and smaller man swinging a loop/whip on the right. | All identified figures, goggles, loop, and other line art are present. A faint continuous pink taper approaches or slightly crosses the saved left x=733. Exact ownership of the lowest-contrast edge samples is less decisive than the target-8 cyan sweep. Preserve this as an unresolved small boundary concern, not a certified pass or a missing-figure failure. The cut cyan cannon scene above is target 8. |
| 11 | Lower cyan scene: man firing upward, large creature, distant figure, and beam. | No target omission identified after the saved top expansion to y=992. The pale cyan region leading into the hub and drawn scene are visible. Purple architecture/body parts to the right belong to target 13. |
| 12 | Lower-right green scene: crouching/kneeling man, small raised-arm figure, and sparse landscape. | No target omission identified in the final crop expanded to x=720. The older x=726 crop also retains the actors and line art but can cut pale green boundary fill; this is not a robust missing-actor/text control. The pink and purple neighboring scenes are incidental. |
| 13 | Final purple scene: large foreground body/leg, man with a rectangular object, and concluding narration. | No target omission identified. The curved purple scene and final caption are present. Most of the upper rectangle belongs to other scenes; its center falls in the green neighbor rather than establishing the purple target. |

No new reading-order discrepancy was identified relative to the declared left-to-right sequence. This single page does not validate reading order for other layouts or right-to-left books.

## Meaningful boundary versus incidental artwork

The audit separates three cases:

1. **Missing target content:** actors, body parts, props, text, line art, or a visible continuous colored region belonging to the intended scene. A small scene-colored taper can still count even if it contains no figure.
2. **Cut neighboring content:** expected in rectangular viewports around curved or overlapping scenes. It should not trigger a target-completeness failure merely because a face, caption, or colored region touches the viewport edge.
3. **Uncertain low-contrast edge samples:** the source fades softly near the hub, and a visual inspection cannot certify which final near-white sample is intentional paint, antialiasing, or JPEG residue. This uncertainty should remain explicit; it is not a reason to assert that every pale fringe is meaningless.

Target 8's pale cyan region is connected visibly to its own cannon scene. The more leftward darker cyan taper belongs to target 6, so there are two nearby ownership questions rather than a single cyan component. For target 10, the material outside or very near the crop is faint pink background, not a missing part of the goggles or whip scene. These distinctions support a conservative boundary-preservation experiment without declaring the current crops perfect.

Historical verifier decisions are preserved. This review does not infer that a particular old model verdict was right or wrong without inspecting that response and its exact supplied evidence.

## Generic viewport margin hypothesis

A deterministic, page-scale safety margin is a reasonable next experiment. For example, expanding every automatically chosen viewport on every side by `ceil(0.01 × min(page_width, page_height))`, then clamping to the page, produces a 12-pixel margin on this source. It would plausibly include the small target-8 and target-10 tapers without any page-specific coordinates or manual target corrections. This remains a hypothesis until the resulting artifacts and automatic checks are evaluated.

The margin should preserve existing pixels and original artwork. It is an expansion of the reading viewport, not a rewrite of panel identity, ordering, masks, or scene boundaries. The prototype must still reject missing inventory, a wrong target, or omissions larger than the margin. In particular, 12 pixels cannot repair page 150's historical 197-pixel bouquet omission.

There are real tradeoffs to measure. For target 8's stored corner span of 327×163 pixels, adding 12 on every side gives 351×187 before any page clamp: roughly 23% more rectangular area, although only about 7% more width. Dense small panels can incur greater relative enlargement and show more neighboring material. Tests should inspect complete target coverage, unwanted neighbor intrusion, reading scale on a phone, page-edge clamping, and behavior on uncomplicated panels. A margin should be chosen from cross-page evidence, not optimized to the two disputed tips.

Useful validation order: generate the same margin mechanically for all 13 saved page-57 viewports and several ordinary control pages; compare target coverage and viewport usefulness; then test the resulting generic candidate through the automatic converter and reader. Evaluation labels remain outside the runtime, and a successful local boundary experiment does not by itself qualify the complete end-to-end policy.

## Exact crop index

Paths are relative to `validation-artifacts/segmentation-iteration-20261008/`. Rectangles are the saved pixel corner coordinates `(left, top, right, bottom)`; they are not the normalized `panels[].box` arrays.

| Target | Rectangle | Exact saved path | SHA-256 |
| --- | --- | --- | --- |
| 1 | `(63, 57, 861, 978)` | `full-sequential-v16/page-0057/crop-01.jpg` | `d75005e5b10009a8ab163c162d6ece9923909f36109e0aee3327a716feca0e12` |
| 2 | `(457, 57, 1081, 981)` | `full-sequential-v16/page-0057/crop-02.jpg` | `bd14efe52842fa8c6916eca2c143640aae069e373b82b3cc0d09a2267bddc1a3` |
| 3 | `(63, 448, 757, 971)` | `full-sequential-v16/page-0057/crop-03.jpg` | `b65f51094cf15c00ac23a6379e1c52cfd1fda9ecaaff86af89f645d67d81f67b` |
| 4 | `(742, 641, 1081, 1017)` | `page57-repair-inflight/crop-04.jpg` | `84e2a16a6e079a6ee5581c2a41c9370961d64923c156cde5d104a0a9bc58bb12` |
| 5 | `(63, 721, 743, 1075)` | `full-sequential-v16/page-0057/crop-05.jpg` | `6610211947b63ba6364516029f034ca2a293bd8d1df6f7398d3e2896ebc9a33a` |
| 6 | `(742, 858, 1081, 1078)` | `page57-repair-inflight/crop-06.jpg` | `e7fb8ef139f97fccc24ac545546ed1c90caa3cd529ddeae3f0adb5ad03b416d2` |
| 7 | `(63, 931, 736, 1599)` | `full-sequential-v16/page-0057/crop-07.jpg` | `79e9dfc1ae65c470a76c8416ce437207a873ba325f22452ade5bef403b63e17a` |
| 8 | `(754, 1008, 1081, 1171)` | `full-sequential-v16/page-0057/crop-08.jpg` | `c2ae645184045b53348e379b38eb1fab3fa37ddff9d9aa7769cf71b210dad997` |
| 9 | `(166, 985, 731, 1599)` | `full-sequential-v16/page-0057/crop-09.jpg` | `20e73bfe97b90b245dc71ed94082a2d9ee5b928ec5c9197d9dacbfda7aeaaae7` |
| 10 | `(733, 1011, 1081, 1279)` | `page57-second-repair/crop-10.jpg` | `a8855143787d4c215073afc7f6788dd063bea14de8fb6d4d0519bd0fb34de014` |
| 11 | `(516, 992, 821, 1599)` | `page57-repair-inflight/crop-11.jpg` | `a31f840c0e97ecccae8f165868f191a3d04e6b4d73182b007184c49efa392090` |
| 12 | `(720, 1020, 1081, 1447)` | `page57-component-repair/crop-12.jpg` | `a8fe114275bd038881b96144646805ed52ae300ef6554d0379829c8d4b03e78b` |
| 13 | `(674, 992, 1081, 1599)` | `page57-repair-inflight/crop-13.jpg` | `32f49672f388759ba14e8c0aa612a78c821df9a2479690784ff88bf1e31b3cb3` |

The prior original target-12 crop, inspected only as an additional possible control, is `full-sequential-v16/page-0057/crop-12.jpg`, with saved rectangle `(726, 1020, 1081, 1447)`. It is not the final candidate indexed above and is not added as a binary completeness control by this audit.

## Follow-up: frozen evaluation of the generic bounded-margin candidate

The next offline candidate was generated in VM153 and copied to `ownership-viewport-v2-20261009/` under the same artifact base. It expands each axis by the smaller of `ceil(1% × shorter page dimension)` and `ceil(5% × that crop dimension)`, then rounds the normalized bounds outward. Thus this candidate adds a crop-relative cap to the earlier margin hypothesis. Actual rendered rectangles, rather than the nominal margin alone, are recorded below because normalization can add an extra pixel at an edge.

All 13 `final57-padded` crops, all three `corrected150-padded` crops, and `original150-padded/crop-03.jpg` were freshly viewed against their source and earlier crops. **Expected answers were frozen and sent to the experiment owner before the new inference answers were inspected: 16 target-completeness positives and one negative.** These labels stay in evaluation material and do not supply scene descriptions or coordinates to the runtime.

| Candidate | Frozen expected target completeness | Visual finding |
| --- | --- | --- |
| `final57-padded`, targets 1–13 | **Complete for these reviewed controls.** | All previously identified actors, objects, captions, line art, and visible scene regions are preserved. Target 8 now includes the pale cyan taper toward the hub; target 10 includes its pale pink taper. The expanded targets 1–7, 9, and 11–13 introduce no identified target loss. |
| `corrected150-padded`, target 1 | **Complete.** | The upper handshake/wedding scene and both speech balloons remain intact. |
| `corrected150-padded`, target 2 | **Complete.** | The middle doorway, crowd, carriage, couple, and speech balloon remain intact. The large bouquet is still a partial intruding neighbor from target 3; its clipping here is not a target-2 omission. |
| `corrected150-padded`, target 3 | **Complete.** | The whole bouquet, stems, ribbon, lower wedding scene, foreground hands, and dialogue are present. The padding also gives visible space above the uppermost flower. |
| `original150-padded`, target 3 | **Incomplete.** | Starting at y=843 still omits a substantial upper portion of the bouquet, stems, and ribbon. The small deterministic margin does not repair the original semantic ownership error. This remains the strong negative control. |

The positive page-57 labels mean that the reviewed visible target regions are covered. They do not certify a pixel-perfect segmentation mask or prove that every near-white source sample has an unambiguous semantic owner. The expanded viewport contains the previously disputed taper areas, so it avoids relying on a decision that those pale regions may be discarded.

### Reading usefulness and neighboring content

The padded page-57 crops remain useful rectangular views of their intended scenes. Actors, props, and text remain recognizable, and the added border is modest relative to the existing scene view. Targets 8 and 10 retain a readable presentation of their intended action while gaining the missing or uncertain pale boundary. Their neighbors remain visible and sometimes cut off; the margin does not introduce a new ambiguity about which previously audited scene is intended.

Several original page-57 rectangles already include a large amount of neighboring artwork because their intended scenes curve around other scenes. Targets 1, 7, and 13 are particularly conspicuous examples. Padding preserves that limitation and adds some more neighboring material; it does not solve scene isolation. The audit found no material new loss of usefulness from this bounded expansion, but it does not characterize these rectangles as an ideal isolated-panel presentation.

Page 150 remains straightforward to read, and the important bouquet overhang is retained in corrected target 3. There are minor presentation costs: expansion can reveal a very thin strip of the adjacent panel, and the lower crop reaches a sliver of the page footer/watermark below the comic artwork. These are polish issues to track separately from target completeness. A future viewport refinement must not trade away the bouquet or another overhang merely to remove such strips.

This was an image audit, not a phone-browser interaction test. It did not exercise page-first navigation, panel stepping, packaged metadata, CBZ creation, API escalation, or a fresh conversion. Those end-to-end checks remain required before presenting the candidate as a qualified automatic reader result.

### Inventory and order remain separate

The independent source review still identifies the same 13 page-57 scenes and three page-150 scenes; no additional inventory or order discrepancy was identified in this follow-up. The margin operation changes only viewports and does not repair inventory or reading order. Passing the crop-completeness controls therefore does not validate those stages for other inputs or replace the converter's separate checks.

### Exact padded artifacts for the frozen labels

Paths below are relative to `validation-artifacts/segmentation-iteration-20261008/ownership-viewport-v2-20261009/`. Each rendered crop was hashed directly and matched to its bundle image entry.

| Bundle | SHA-256 |
| --- | --- |
| `final57-padded/bundle.json` | `8cce3a1e212953985330a8f2e9f14d08be64d035c18a5621ec758375bb0783ce` |
| `corrected150-padded/bundle.json` | `7e8fc595b702caa571b28f6dd92e3d8a63b08ae4e01a6ec51be27fc77031bc5e` |
| `original150-padded/bundle.json` | `24a8546bbef8ac5a2828d285fb3eef2aca1a946c3521469965a18b24e141075a` |

| Crop path | Actual pixel rectangle | SHA-256 |
| --- | --- | --- |
| `final57-padded/crop-01.jpg` | `(50, 44, 874, 991)` | `5a200c8f0d42cb3b617cdf135e752253881aeb4a5d4dee3d1f93388726e7b390` |
| `final57-padded/crop-02.jpg` | `(445, 44, 1094, 994)` | `cc4e7c57ec4fa30be423ae3dae3bca0f098a72d537d46b4a508598148eb77f9b` |
| `final57-padded/crop-03.jpg` | `(50, 435, 770, 984)` | `e62e99fdff48ce40c7f2e015c71194016d82e840802959e3fabdb32fbb69682c` |
| `final57-padded/crop-04.jpg` | `(729, 627, 1094, 1030)` | `46b5ebe53456910391c989afb6c746cb3c0d203190c2c2bdf2e10b43f9940834` |
| `final57-padded/crop-05.jpg` | `(50, 708, 755, 1088)` | `0df308b5cf9b48e30d63d22117f59c2cddaff713aa6e378a4f60e6cf0f0b1b26` |
| `final57-padded/crop-06.jpg` | `(729, 847, 1094, 1090)` | `16501d9392119f637c814358b2e6c882b7f211050254bd19c820bfd44674fa01` |
| `final57-padded/crop-07.jpg` | `(50, 917, 748, 1612)` | `a2846c87686c06c4a9eefd1d8b9f758297e5d5765a0058f7adcadbc6ca080881` |
| `final57-padded/crop-08.jpg` | `(742, 998, 1094, 1180)` | `54b7fa31a81341aa34a107d4d1d2fdde4070dba7cf04e2e5bee0da43ecf51eea` |
| `final57-padded/crop-09.jpg` | `(154, 972, 744, 1612)` | `bc6aa768caf4e00ca0df2b21b86af71698657a03b6e26135991061f144f2ae22` |
| `final57-padded/crop-10.jpg` | `(720, 998, 1094, 1293)` | `882919961fd2a449095139a6cbced5d2c60291b2a253bb9ea3bd73344b7e6c36` |
| `final57-padded/crop-11.jpg` | `(504, 978, 833, 1612)` | `ac6495edb1ca80f365c61d5995c5c7b94fb61fb02be5166df6568f0b06ee2fbd` |
| `final57-padded/crop-12.jpg` | `(708, 1006, 1094, 1461)` | `5565595ca70d80756febeb241898fd7b3d967b86e8358ce0bd40cafee8c1a72c` |
| `final57-padded/crop-13.jpg` | `(662, 978, 1094, 1612)` | `98e0188404dcc4789f15874323d6039b57ef30e815838c9614d886fd54cfe9aa` |
| `corrected150-padded/crop-01.jpg` | `(46, 19, 1073, 365)` | `58c8c0d27a0eee16eb9e41eeeae6bc97216614040faa7e360f398905d7b4cac2` |
| `corrected150-padded/crop-02.jpg` | `(46, 349, 1073, 859)` | `dcd21ac9987056dea22d2692ecb42ca815833e73405b217338cdc15dcf364fab` |
| `corrected150-padded/crop-03.jpg` | `(46, 646, 1073, 1632)` | `de32d78a86e7f766802ae2b4adeb3317db478e5b52355f1a6db6d87e738311ae` |
| `original150-padded/crop-03.jpg` | `(46, 843, 1073, 1632)` | `8b80291af4661217a49dc85c307743592f873d525144de097f631e3f2ba210cc` |

The audit appended only these evaluation findings. It made no runtime edits or paid calls and preserved every original artifact.
