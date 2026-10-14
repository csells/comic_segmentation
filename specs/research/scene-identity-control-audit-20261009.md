# Scene identity control audit — 2026-10-09

The current paired completeness experiment uses three saved crops from page 150: original target 3 as a negative, corrected target 3 as a positive, and corrected target 2 as an ownership positive. These expected answers were established by fresh visual inspection of the source and exact saved crops before inspecting the new paid experiment's answers.

The identities and labels in this document are **evaluation annotations only**. They must not be copied into production prompts, automatic scene descriptions, or runtime repairs. The audit made no API calls, changed no image or bundle, and did not alter the reader or conversion policy. It assesses target-scene completeness, not reading order, detector accuracy across a book, or exact pixel-mask accuracy.

## Frozen scored controls

| Saved crop | Evaluation-only intended scene | Expected answer and evidence |
| --- | --- | --- |
| Page 150, original target 3 | The lower wedding scene: blond woman in yellow beside the man in a dark coat, raised foreground hands, dialogue about being picked up and placed in the carriage, and the large airborne bouquet. | **Incomplete.** The crop begins at source y=856 and visibly removes the upper flowers, stems, and ribbon of the bouquet. The source shows these parts extending upward across the horizontal gutter. |
| Page 150, corrected target 3 | The same lower wedding scene and its bouquet. | **Complete for this visual control.** The crop begins at y=659 and includes the full visible bouquet and lower scene. It necessarily includes some of the middle panel because this is a rectangular reading viewport. That neighboring material alone is not a completeness defect. |
| Page 150, corrected target 2 | The middle wide view of the couple at the doorway behind the carriage, with the speech balloon beginning “Time to convince…”. | **Complete for this visual control.** The doorway, couple, speech balloon, crowd, and carriage view are present. The bouquet intrudes from target 3 and is cut by the bottom of this viewport; its missing lower portion is not missing artwork from target 2. |

The last two controls deliberately distinguish ownership from simple edge contact. Cropping the bouquet is a defect when the intended target is the lower scene, but does not by itself make the middle scene incomplete. Positive labels mean the reviewed target scene is preserved; they do not assert a formally certified contour or absence of every neighboring pixel.

The source-space rectangles below are the saved bundle's inclusive pixel corner coordinates `(left, top, right, bottom)`, not the normalized `panels[].box` arrays. Image extraction uses right+1 and bottom+1 as exclusive bounds.

| Crop | Saved rectangle | SHA-256 |
| --- | --- | --- |
| Original 150/3 | `(58, 856, 1061, 1619)` | `6c2311dcb0812b319cccb84634019c617c722d775a48334b9459f7198124b83d` |
| Corrected 150/3 | `(58, 659, 1061, 1619)` | `de439d0e649b9a0023edeb077091487a8e0c3c3432966a579466ab16d0fcee92` |
| Corrected 150/2 | `(58, 362, 1061, 846)` | `af023e46688b619d390ba33f2997f67618ab3b655fdf13ec87295c32d50796dd` |

## Page 57 target 6: historical labels quarantined

Fresh source review identifies target 6 as the **narrow cyan band on the right containing small floating or falling figures and debris**, between the brown face band above and the cyan telescope band below. The brown face belongs to target 4. Both saved target-6 rectangles also contain a substantial, truncated portion of that neighboring brown face.

The original target-6 crop is `(754, 858, 1081, 1078)`; the repaired version is `(742, 858, 1081, 1078)`. Their only geometric difference is a 12-pixel expansion to the left near the spiral hub. Both show the cyan figures and debris. Whether the original loses a small target-colored taper at that hub remains ambiguous in this audit. Neither a missing main brown face nor its truncation is sufficient evidence that target 6 is incomplete.

Therefore the previous original-negative/repaired-positive labels are **quarantined from completeness scoring**. They remain preserved as historical records and are superseded for the current scored experiment; no old artifact or verdict is overwritten. The pair could still test scene identification, including whether a verifier mistakes the incidental brown face for the cyan target, but it does not currently provide a reliable binary completeness pair.

This audit did **not** re-open or adjudicate the historical Astra verdict. It does not claim that verdict was wrong. It establishes independently that a brown-face-based rejection, if used as the justification for target-6 incompleteness, would not be supported by the reviewed target identity.

## Additional unscored observation

Saved page 57 target 5 appears to preserve its large left cyan band, showing two men, a skyline, flying craft, and spiked circular shapes. Its rectangle includes clipped green and pink neighbors. This is a possible future ownership positive, but it is **not part of the frozen three-control experiment**, and no synthetic negative was created during this audit.

Rectangle centers are not reliable scene identifiers on this page. For example, the center of target 7's rectangle lies in the neighboring brown scene, while its intended pink scene curves around the left and top. Target 13's rectangle similarly contains a center in the neighboring green scene. An automatic identity stage must establish intended scene membership rather than equating the box center or largest visible component with the target.

## Exact evidence paths and hashes

All paths in this section are relative to the repository's ignored artifact directory:

`validation-artifacts/segmentation-iteration-20261008/`

They were read from the local checkout and hashed directly. Crop hashes agree with the corresponding saved bundle image entries. The local `page-0002` directory is the second input of an earlier regression run; its source is PDF page 150, as confirmed by the source hash and bundle.

| Artifact path | SHA-256 |
| --- | --- |
| `seeded-boundary-spike-20261009/final/inputs/0150.jpg` | `ce13e97dcf81deb016a7b3201c59d2ff1e07c0e1638cd8690fe8a1341d397e92` |
| `specialist-masks-20261009/control-proposals/0150-original-bundle.json` | `75f9b1f1d0c349ed17bf14e40c291b9f2191676003a7bbb90f16054607fb994e` |
| `seeded-boundary-spike-20261009/final/inputs/0150-bundle.json` | `59c19d2f12a27b36c997e701949e486b1341c082365da294a09d20ca483cd822` |
| `full-sequential-v21/page-0150/crop-03.jpg` | `6c2311dcb0812b319cccb84634019c617c722d775a48334b9459f7198124b83d` |
| `crossing-art-regression-v23-20261009/page-0002/crop-03.jpg` | `de439d0e649b9a0023edeb077091487a8e0c3c3432966a579466ab16d0fcee92` |
| `crossing-art-regression-v23-20261009/page-0002/crop-02.jpg` | `af023e46688b619d390ba33f2997f67618ab3b655fdf13ec87295c32d50796dd` |
| `seeded-boundary-spike-20261009/final/inputs/0057.jpg` | `910bbb7a131122ea3a7b102ec40fbea4193758ecc2abfa16e793c48626cd34b1` |
| `specialist-masks-20261009/control-proposals/0057-original-bundle.json` | `68bc35ec18484b576b973c8d493c77d184baa8bbe73e0a2c4b4094de54b88f90` |
| `seeded-boundary-spike-20261009/final/inputs/0057-bundle.json` | `b3aa2deb8ccf851a82e0caf10b40b128abfed3cbd351fa96f306050878031590` |
| `full-sequential-v16/page-0057/crop-06.jpg` | `7f719fa959e999afac6fbbe5ef320f6cabedd92c0732cf2e1b90c6fe5448732e` |
| `page57-repair-inflight/crop-06.jpg` | `e7fb8ef139f97fccc24ac545546ed1c90caa3cd529ddeae3f0adb5ad03b416d2` |
| `full-sequential-v16/page-0057/crop-05.jpg` | `6610211947b63ba6364516029f034ca2a293bd8d1df6f7398d3e2896ebc9a33a` |

Ignored artifacts need the existing evidence backup chain or a local artifact checkout; tracking this document alone does not distribute the private comic images.
