# Proposed ordinary-layout omission controls

**Stopped after N1 was falsely accepted, 2026-10-09.** Root completed the pre-inference labels and authorized the first negative after cache/format qualification. The actual unchanged quality route accepted the missing-scene candidate; N2 remains unrun. See the [independent result audit](disjoint-defect-control-results-20261009.md). The frozen V30 policy, prompts, transport snapshot and existing evidence remain unchanged. The original protocol below is followed by the completed preparation evidence.

The question is narrow: can an otherwise valid, ordinary first proposal omit a complete scene or meaningful content inside one scene and still be accepted by the actual V30 quality route when ownership auditing is not triggered? This tests quality checking at the saved-candidate boundary. It does not estimate detector error frequency, establish converter E2E performance or qualify unseen books.

## Existing evidence and the gap

- [V5](ownership-viewport-v5-review-20261009.md) tests an incomplete bouquet crop and intact ownership controls on overlapping layouts. It does not test a whole missing scene in an ordinary proposal that never reaches the source-ownership stage.
- The earlier [inventory experiments](full-pdf-sequential-review-20261008.md) tested regions where a later, lower-count proposal absorbs multiple earlier boxes. `inventory_guard.merged_groups` needs an earlier proposal and at least two earlier views covered by one current region. It does not independently enumerate all scenes in a first proposal, or recognize every deleted region. Historical labels and subsequent source reinterpretations must remain separate from this new screen.
- Existing false-split/continuity controls address a different defect. A missing scene need not create a false split or an overlapping pair. The failed [description-omission ablation](scene-identity-verification-20261009.md) also remains failed; deleting a description is not deleting a proposed scene.
- Static inspection shows `OwnershipConverter._risk_orders` and `Converter.check_crossing_art` depend on overlap/crossing risk and valid repair lineage. An ordinary first proposal with neither has only the existing native/global/target and continuity checks. Those checks may correctly reject the proposed negatives; no false acceptance is claimed before observing them.

An independent reviewer of the existing experiments found no duplicate saved V30 first-proposal whole-scene deletion control.

## Saved positive and proposed mutations

Use original source56, an eight-scene page already accepted automatically at Sol-low, personally reviewed by root and played through the unchanged reader. Its scene order is a wide family-yard opening, two rows of three scenes, then a wide eyes strip. The source was independently reopened for this proposal. Gold descriptions below stay in the evaluation manifest and never enter runtime prompts, hypotheses, repair input or routing decisions.

| Case | Evaluation-only construction | Expected quality outcome |
| --- | --- | --- |
| P0: intact | Copy the exact selected candidate, source and all eight crop bytes. Preserve geometry, direction, descriptions and already-applied margin. | Accept through the same cached first-tier route. |
| N1: missing scene | Starting independently from P0, remove order7, the empty-swing scene. Keep orders1–6 unchanged and relabel old order8 as order7. Remove the omitted crop entry; copy every retained crop byte exactly, renaming the last file and its label to match the new order. | Reject the defective candidate. The source still contains the separate swing scene and its caption; no proposed view represents it. |
| N2: missing owned artwork | Starting independently from P0, move only order7's left boundary inward by one quarter of its width: normalized `[527,656,816,928]` becomes `[527,724,816,928]`. Preserve all other ordered boxes and crop bytes. Generate only the changed crop with the frozen producer's exact coordinate/encoding convention. | Reject the defective candidate. The proposed cut removes meaningful left-hand swing artwork from a separate framed scene while leaving the other seven scenes unchanged. |

N2 is a proposed geometry, not yet a scored crop: generate it only in the disposable VM, view its exact bytes against the unchanged source, and freeze the independent label before any model dispatch. Do not substitute a faint boundary or empty-margin disagreement for meaningful missing art. If this crop is ambiguous, stop preparation rather than selecting successive harder examples after seeing model answers.

The accepted crops include small reading-margin intersections. “Ordinary” here means below the implementation's ownership-risk threshold, not mathematically zero intersection. Before dispatch, use the actual frozen `overlap_risk_pairs` and `partial_overlap_pairs` functions to assert empty risk-pair lists for all three cases; also require empty `_risk_orders` before judging. Do not suppress a discovered risk or fake a crossing result to maintain the premise.

Freeze these positive inputs before materializing the negatives:

| Item | SHA-256 / identity |
| --- | --- |
| Source JPEG | `81f2d6e5b7803e2939e5acd0eb406ec43e5a3c4bd424d1fa41097a4fcfe5c526` |
| Selected candidate | `56887bb78ee067c73f76ae3b57f8247d81a3ff7768e988b31db4323054ad8cd2` |
| Accepted page record | `c1d043730d8f8a7ea1581e405847651d6af6fb2068a89a29ef3974e864097627` |
| Diagnostic result | `b84e7da7f1694bda44a9903db1340aa620734c9b4b9d39a000df185e59a22a6d` |
| Root source/all-eight-crop receipt | `d19224becac91c4f988e62fdc2bef18c3486786d618019b08975706518a0431d` |

Local positive evidence: `validation-artifacts/segmentation-iteration-20261008/actual-v30-source56-accepted-20261009/`. The root receipt lists every positive crop hash. Preserve that directory and its original CBZ; all control artifacts belong in a new evaluation directory.

## Freeze and cache-only preparation

1. Bind the already-qualified 180-file transport snapshot and its manifest, policy `automatic-source-ownership-v30`, generic prompts, source, positive record/bundle and every image hash. No credentials or live ledger mutation are needed for preparation.
2. Materialize the controls in the VM. Recompute each changed candidate identity with the frozen identity formula; validate classification, orientation, direction, contiguous orders, normalized geometry, source/crop labels, actual pixel points and hashes. Mutants are explicitly injected evaluation proposals, never attributed to a detector response that did not produce them. Strip selected-run verdicts, source evidence, hypotheses, repair flags and repair ancestry. Keep the actual full-PDF predecessor mapping available, without labels.
3. Use a fresh converter instance and fresh candidate history for each case, containing only that case as its first proposal. Do not seed P0 as an earlier candidate for N1/N2: doing so changes the question and can activate conservation or inherited ownership checks. Record exact runtime history and pair lists.
4. Preserve P0 bytes. Separately, run the ordinary deterministic refiner on each injected mutant offline and record whether it repairs the defect. That result is preprocessing evidence, not a judge pass. The primary quality-boundary screen below uses the frozen post-refinement control bytes; it must not be reported as proof that a raw detector error survives the complete converter. Do not silently substitute refiner-produced crops, add another margin or regenerate P0 to obtain cache matches.
5. Invoke the frozen controller and real `OwnershipConverter.judge`/`verify` methods, with only fixed-candidate loading in place of new detection/refinement. Use the actual single-tier `run_page` path (`sol-low`), with detector generation, geometry repair and component repair unavailable. Judge acceptance ends normally; otherwise the actual controller calls the unchanged verifier and decides whether that candidate can be accepted. An exhausted single-candidate control is a rejection for this experiment, not a completed full-converter fallback result.
6. First execute P0 with network disabled and all new reservations denied. It must reproduce acceptance using exact cached provider responses. An unexpected miss or changed request stops preparation. No model verdict may be replaced with a scripted success. Enumerate both negatives' actual cache hits and first misses with the same disabled transport, recording request bodies/fingerprints and expected dispatch kinds; do not use a fake passing model to infer downstream routes.

Recompute and freeze the mutation/source/crop manifest, visual labels, request builder hashes, and the finite dispatch policy before root dispatch. A separate evaluation runner now implements these guards; it has not made a paid call.

## Optional bounded dispatch and scoring

If root chooses to run it, use fixed order P0, N1, N2. P0 remains cache-only. Reuse every exact success already recorded; never repeat a successful request for another draw. Preserve all unknown/failed reservations and use no explicit or automatic transport retries in this screen.

Propose a maximum **$4 used or held and 40 new requests** for both negatives together, inside the existing shared **$100 total** and a separately named evaluation envelope that never resets between cases or resumptions. This is a ceiling, not an expected charge or pre-approved spend. Three concurrent native $1 holds fit initially; a tighter remaining nested envelope may stop the unchanged scheduler. Such a capacity stop is inconclusive, not a quality failure or permission to relax reservations. Check current global availability immediately before any proposed dispatch.

The native path has at most fourteen checks for the seven-scene N1 and sixteen for the eight-scene N2 before any verifier confirmation: adjacent continuity checks, one complete-candidate check and each target check. Many continuity inputs match saved P0 exactly. Full-candidate geometry changes affect the native target request bodies even where crop bytes are unchanged, so they must not be counted as cache hits without exact fingerprints. Responses confirmation is conditional and may stop earlier. The finite request ceiling can terminate an unexpectedly long path; it never licenses additional detectors, repairs, source audits or prompt experiments beyond the unchanged route.

- **Harmful false acceptance:** the actual controller accepts either frozen defective candidate, whether directly or after a verifier dismisses the native warning. Stop immediately, preserve the entire route, and do not run N2 after N1 fails.
- **Correct rejection:** the candidate does not reach acceptance because an actual quality guard remains binding. Report whether the guard identified the intended omission/clipping, an unrelated continuity issue, or uncertainty. Only defect-aligned evidence supports that defect-specific capability; safe abstention is reported separately.
- **Positive regression:** P0 no longer accepts with exact cached requests, or its input/route differs. Stop before paid negatives and investigate the harness or version binding.
- **Inconclusive:** missing/invalid evidence, malformed output, transport failure, budget stop, unexpected ownership-risk route or an ambiguous crop label. Preserve the stop; do not call it a successful rejection.

Report both native warnings and the final controller outcome. A native scene warning that the ordinary verifier wrongly clears is a failure, even though the first predicate found the defect. A pass is two bounded development controls on one known source, not an accuracy percentage or a reason to remove independent ownership checks. Any policy change suggested by a failure requires a separate proposal and intact controls before integration.

## Completed VM-only preparation

The exact proposed mutations were materialized in VM153 with no source/prompt edits or ledger access. P0 retains all original source/crop bytes; N1 retains all seven remaining crop bytes while relabeling the eyes strip; N2 changes only crop7 using the frozen producer's coordinate and JPEG conventions. The fresh-history actual risk checks are empty for all three cases. Separately running the ordinary deterministic refiner changed none of their geometries. This does not turn the injected-candidate screen into detector E2E evidence.

The actual unchanged single-tier controller and `OwnershipConverter` accepted P0 with **16 exact cached requests and zero new requests**. Cache-only N1 used six saved responses and stopped before reserving native request `23508c6d684646ba03812f9343b81b7461df09babb1b0343a14d6dc389a726da`; N2 used seven and stopped before reserving `2d649f397b8eb89f551258746f543e509c7b67d80ae22d11bfaf08d6260ff502`. These are unscored cache misses, not successful negative rejections. Qualification used a read-only snapshot and a separate ledger copy; no HTTP requests, credentials or live-ledger writes occurred.

I viewed the exact full source, intact crop7 and N2 crop7: the new left edge visibly severs the swing seat/owned artwork while retaining the caption. Root subsequently completed independently bound pre-inference labels, SHA `25b1a5ca9eca8b16ad130c249b67a2fb19e83e67fb70a3933b746a6ab513a856`. No negative model verdict was generated or used to select these mutations.

Ten VM guard tests passed on disposable ledgers: cumulative $4/40 accounting across both negatives, concurrent holds, settlement headroom, global-policy/scope enforcement, exact cache success at an exhausted envelope, bound review/dispatch receipts, and stop-before-key/next-case behavior. Three additional VM launcher tests checked readiness before credential access and stdin-only transfer using fake subprocesses and a fake key. Runtime supports only the actual ordinary native/Sol confirmation path; unexpected ownership/detector routes stop inconclusively. Independent source/proof review passed before dispatch, receipt SHA `3d0f6a8460a557ace33d45f4ab415a86e897776ac747df13c293b80950449b31`; it verified all 31 cached-preparation request fingerprints and all 30 control files. These checks establish experiment integrity, not segmentation quality.

Prepared code and exact gate schema: `validation-artifacts/segmentation-iteration-20261008/disjoint-defect-v1-prepared/README.md`. Controls SHA `d7c06d41cda9c4d6debd8119c118eff880f8222b05254399caef5e5b0b088dea`; cache terminal SHA `51328308887f5d84bb1250bbb898bba6566d93a48d024370ac6eab7145e6a978`. Fully read off-VM export `disjoint-defect-v1-materialized-20261009/evidence.tgz`: **8,847,708 bytes, 143 regular files**, SHA `90bf564258e776e237eb065af6e5089ee88605d819546adcaa306f08a2204cff`. This initial export contains no subsequent root labels, paid gate or inference outcome.
