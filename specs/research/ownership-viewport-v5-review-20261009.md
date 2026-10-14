# V5 ownership and viewport controls: independent review

Reviewed 2026-10-09, completed at 20:50 UTC. **The saved evidence supports advancing to actual V29 automatic regressions.** All seven crop outcomes agree with the previously frozen visual labels, and the three negative explanations identify the actual omitted content. This qualifies the bounded control experiment, not fresh conversion, all page-57 crops, the full PDF, or general comic segmentation.

This document is evaluation only. The reviewer read all four source-audit results and all seven crop verdicts, compared them with the full source pages and exact saved controls, and re-opened the four positive crops and the padded negative. No runtime input, prompt, geometry, label, frozen run, or API request was changed. The [pre-inference source/crop audit](page57-v28-independent-audit-20261009.md) and [original control audit](scene-identity-control-audit-20261009.md) remain authoritative labels.

## Source identities and ownership

The original, phrase-erased, and corrected page-150 audits each retain the same three source scenes: interior greeting; distant entrance/crowd/carriage; and the tilted bouquet-toss view with foreground reaching hands. All three correctly assign the large bouquet, stems, ribbon and upward overhang to scene 3. They distinguish it from the small flowers depicted in scene 1 and the carriage in scene 2. Thus the original misleading carriage description and removal of its flower adjective do not determine the audited ownership. The corrected proposal's clearer detector description is a separate positive control, not independent proof of resistance to misleading hints.

The page-57 audit returns 13 mapped scenes, `inventory_status: complete`, no issues, and no uncertain scene. Each identity and its principal owned content were checked against the source:

| Order | Source scene and assessment |
| --- | --- |
| 1 | Golden rooftop/portal, two men, caption and long rooftop taper: correspondence correct. |
| 2 | Violet encounter, foreground head/clothing, curved backdrop and caption: correspondence correct. |
| 3 | Green ground struggle, pole, prone man, doors/rubble and caption: correspondence correct. |
| 4 | Narrow golden face/planking close-up: correctly separate from the rooftop and cyan band. |
| 5 | Large cyan city view with two men and surrounding structures: correspondence correct. |
| 6 | Narrow cyan suspended-figure/debris band: correctly separate from the brown face and cannon view. |
| 7 | Pink ray-gun confrontation, airships and caption: correctly retained despite neighboring golden artwork occupying much of its rectangle. |
| 8 | Cyan cylindrical-weapon view: correctly separate from the cyan band above and pink scene below. |
| 9 | Golden eyepatched-man struggle and surrounding birds: correspondence correct. |
| 10 | Pink goggles/looping-lash encounter and inward taper: correspondence correct. |
| 11 | Cyan creature/weapon encounter and its narrow continuation: correspondence correct. |
| 12 | Green kneeling/open-ground view: ownership correct, with the noun-level disagreement below. |
| 13 | Violet indoor/briefcase view, large foreground figure and final caption: correctly retained despite neighboring green artwork near the rectangle's center. |

The generated order-12 description calls the small upright background form a planted, ring-hilted swordlike object; the frozen human audit called it a small raised-arm figure. This review preserves that disagreement rather than rewriting the label after inference. Both identify the same visible form within the green scene, and the crop contains it. It does not alter any of the seven tested outcomes. It does mean the generated descriptions should not be promoted to exact object annotations or treated as an exhaustive completeness checklist.

## Seven crop controls

| Index | Fixed control | Verdict | Independent assessment |
| --- | --- | --- | --- |
| 0 | Original150, target 3 | Reject, clipped art | Correct: the top edge removes upper bouquet flowers, stems and ribbon belonging to the lower scene. |
| 1 | Same crop with phrase-erased source hints | Reject, clipped art | Correct for the same visible omission; the altered hint does not erase ownership. |
| 2 | Corrected150 with margin, target 3 | Accept | Correct: complete bouquet, ribbon, stems, couple, reaching hands and dialogue are retained. |
| 3 | Corrected150 with margin, target 2 | Accept | Correct: carriage/entrance scene is complete. Its partial view of the neighboring bouquet is not a target-2 defect. |
| 4 | Final57 with margin, target 8 | Accept | Correct: cannon/operator and visible cyan continuation are retained; partial neighboring scenes are incidental. |
| 5 | Final57 with margin, target 10 | Accept | Correct: goggles, standing figure, looping lash and pink taper are retained; the cut cannon view is incidental. |
| 6 | Original150 with margin, target 3 | Reject, clipped art | Correct: the small margin still leaves substantial upper bouquet content outside the crop. |

Every negative has scene inventory and reading order marked pass, coverage marked fail, and a concrete target-3 clipping issue. None succeeds merely by expressing uncertainty or rejecting the wrong neighboring scene. Positive responses contain pass fields and no issues; they provide no separate prose rationale, so the explanations above are the reviewer's visual findings. Target-only reading-order pass is prescribed by that prompt and does not validate page reading order.

The five padded crop hashes exactly match the pre-inference audit. Checks 0 and 1 use the same original crop SHA-256 `6c2311dcb0812b319cccb84634019c617c722d775a48334b9459f7198124b83d`. The two full source hashes match the frozen page-57 and page-150 sources. The inspected request builder and saved new request records exclude evaluation labels and case names; raw detector hints enter the source audit, and its generated evidence enters the explicitly fallible auxiliary wrapper.

## Provenance and limits

Local evidence: `validation-artifacts/segmentation-iteration-20261008/ownership-viewport-v5-completed-20261009/`. Frozen `run.json` SHA-256 is `222065599d278bf35b3e04dc3d608ceb60c4ea6e6786ab2ae67719b52b3f66d2`; `terminal.json` is `15c059f1e7f97b5166b8ec697ed4c4f130f333c438d9be47988ccdecfcf6c4b8`.

The three page-150 source audits are recorded cache hits. The completed page-57 source audit is linked by `retry_of` to the named quota rejection, uses Astra in the verifier namespace, and retains the 17,408-token allowance. It completed with 9,108 output tokens, including 6,589 reasoning tokens. The terminal record reports eight new calls, three cache hits, $0.724016 new usage and $42.851332 shared used/held. No remaining control was skipped. Earlier holds and failed experiments remain separate preserved evidence.

Advance first to automatic source-57/149/150 conversion with no imported winning geometry or human routing; inspect every resulting crop, repair lineage and emitted book. Risky accepted candidates must have their own linked source audit, complete-candidate confirmation and all required marked target checks. Then exercise the earlier inset, continuity and lost-inventory regressions before the independently frozen book screen.

The source-ownership stage is conditional on the implementation's overlap/crossing risk route; these controls do not establish that every possible wrong detector proposal reaches it. V5 does not reverse the earlier failed description-omission ablation, validate every scene noun, certify pixel-perfect masks, or replace actual converter and reader qualification.
