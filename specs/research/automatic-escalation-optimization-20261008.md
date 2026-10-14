# Automatic escalation and judge optimization — 2026-10-08

Chris clarified that the finished tool must obtain the best results automatically,
without an agent inspecting each page. Manual inspection is development evidence,
not a runtime dependency. This replaces the earlier operational suggestion to
have the agent inspect all remaining 245 pages. Rust production work is still
unstarted; this work prototypes the quality policy in the disposable VM.

**The automatic replay now selects the previously accepted output for all twelve
development pages.** It runs the actual geometry refiner, uses model decisions
to route requests and rechecks the stronger candidate. It reads no evaluation
labels and has no human-routing callback. Detector/model responses are cached:
this establishes routing on these examples, not fresh-book quality or live
production integration.

## What was optimized

The original native Decisions experiment used one prompt/input representation.
It was premature to treat that first failure as the model's capability limit.
This continuation tests three changed configurations at the same 0.5 threshold:

| Native Decisions configuration | Missed bad candidates / 2 | Unnecessary escalations / 12 good |
| --- | --- | --- |
| Original page, overlay, all crops (v1) | 0 | 10 |
| Clearer target-scene and whole-page rubric (prompt v2) | 1 | 5 |
| Same v2 rubric, overlay removed | 1 | 6 |
| One target crop per call; page-level scene/order checks retained | 1 | 2 |

The rubric distinguishes the target scene from incidental fragments of adjacent
or inset scenes, source-drawn clipping from crop damage, and intentional title/
credits pages from narrative pages. The target experiment compared 76 crops
individually with their unchanged source pages. It flags raw page 205 crop 2's
clipped shared balloon, while retaining its repaired crop 2. It still falsely
flags repaired page 205 crop 10 and page 5 crop 1. The combined rule also retains
the page-level order warning on repaired 205.

All three changed configurations miss raw page 100's small trimmed artwork
edges. Its deterministic dark-gutter repair runs *before* judging in the proposed
pipeline and fixes all five boxes. This is why the combined pipeline succeeds
here; it does not establish that the decision model detects subtle clipping on
other backgrounds. The same labels were used to measure every variant. No
threshold was tuned afterward and no labels were silently changed.

## Stronger verification also needed optimization

A global Sol-low explanatory verifier was tested on both bad candidates and
the two remaining false alarms. It accepted all four. Its crop-coverage verdict
is unsuitable as a veto on a localized warning. Higher model capability alone
did not solve an overly broad judging task.

A target-only Sol-high verifier received the original page and exactly one crop,
with explicit instructions to identify missing *target* content. Five controls:

| Target | Result |
| --- | --- |
| Raw 100 crop 1, trimmed artwork | Incorrectly accepted |
| Raw 205 crop 2, clipped shared balloon | Correctly escalated with specific evidence |
| Repaired 205 crop 2 | Correctly accepted |
| Repaired 205 crop 10, incidental neighbor fragments | Correctly accepted |
| Page 5 crop 1, background with overlapping insets | Correctly accepted |

The targeted verifier explains that the raw dog-scene crop removes the left
part of a shared thought balloon. It separates this from the irrelevant scene
fragments in the two false alarms. The page-100 miss remains an explicit gap.
This changes both representation and reasoning effort relative to the global
verifier; the improvement cannot be attributed solely to prompt wording.

## Automatic loop

The research controller implements this sequence, with provider operations
injected behind a durable cache/budget boundary:

1. Detect with Sol low. Validate the structure and preserve the raw result.
2. Apply the conservative gutter expansion to qualifying boxes automatically.
3. Use cheap Decisions checks for page scene inventory/order and individual
   target-crop coverage. Keep candidates that pass the configured checks.
4. Send flagged targets to a stronger, target-specific verifier. For semantic
   flags, use the corresponding semantic check. A whole-page coverage answer
   cannot override a target-crop defect. If all flags are dismissed, keep the
   candidate; a confirmed or uncertain defect advances to stronger detection.
5. Detect with Sol high and repeat refinement and judging. The general controller
   permits a third distinct detector tier, but this replay only exercises low
   and high; an Astra tier is a proposal, not a validated fallback.
6. If qualified detector tiers are exhausted, preserve the source as an explicit
   whole-page fallback with the unresolved reason and retained attempts. Budget,
   account, invalid verdict or unknown-request failures stop resumably. They
   cannot become an accepted page or an unbounded retry loop.

`automatic_escalation.py` has no human approval/review callback. The runtime
providers must enforce budgets, source identity, structural validation and durable
request records; the controller is not itself a complete provider integration.
The verifier mechanism still needs independent qualification, particularly for
cases where a false “keep” would overrule a real defect.

## What the replay actually proved

`replay_automatic_escalation.py` builds its detector catalog from original saved
Sol runs and matches candidates by source hash and geometry, not by expected
answer. It runs the real refiner and looks up only exact matching judge evidence.
Missing cache evidence blocks explicitly. The separate scoring step reads frozen
labels *after* the run and compares selected geometry byte-equivalent structures.

- All twelve source pages ended with the previously accepted geometry.
- Page 100's five boxes were repaired by the real pixel algorithm.
- Page 205's balloon warning was confirmed, triggering selection of its cached
  Sol-high candidate. That candidate was judged again, and targeted verification
  dismissed the remaining crop false alarm. Its order flag used only the global
  verifier's reading-order field, not its unreliable crop-coverage verdict.
- Page 5's false alarm was dismissed without another detector pass.
- The other nine pages needed no stronger verifier. There were thirteen detector
  selections total, three verifier invocations, and no human routing decisions.
- No network requests occurred during replay. The higher detector output already
  existed, so this does not test generating a new stronger result under live failure
  conditions, or validate an unseen-page routing policy.

The input/geometry catalog and provider run paths are research configuration.
There are no per-page policy branches or hand-edited production coordinates.
The twelve development pages include the previously studied failures, and this
policy was developed around those observations. A 12/12 replay is a regression
milestone, not an independent quality estimate.

## Cost, verification and retained evidence

Additional research estimated cost **$0.177201**:

| Run | New paid calls | Reused | Estimated cost |
| --- | --- | --- | --- |
| Prompt v2 | 14 | 0 | $0.008717 |
| No-overlay v2 | 11 | 3 | $0.005689 |
| Target Decisions v3 | 76 | 0 | $0.024260 |
| Global Sol-low verifier | 4 | 0 | $0.060957 |
| Target Sol-high verifier | 5 | 0 | $0.077578 |

Target Decisions calls had median request time **0.337 seconds**; target Sol-high
verification **8.971 seconds**. These are individual observed requests, not total
book conversion latency. The replay referenced 88 judging requests whose saved
usage estimates sum to **$0.098577**, about **$0.00821 per source page**, if all
were uncached. That excludes detection and preparation and is an accounting
projection from these cases, not a fresh live conversion bill. Selective
verification concentrates the slower calls on flagged cases.

The [official API](https://developers.openai.com/api/docs/guides/decisions)
supports these image predicates. Native pricing differs from Responses pricing;
both were charged to the existing single ledger. Current used/held balance is
**$4.780991 of $20**, including unchanged **$3.60** unknown Gemini holds. No
successful baseline was rerun; three identical whole-page requests were reused.
The 110 new calls have 110 durable settlements; historical ledger bytes remain
unchanged. The request bodies were reconstructed from exported inputs and all
110 fingerprints and image hashes matched.

Thirty-seven regression tests passed inside VM153, including observed failing
tests before the new controller/variant implementations. They cover bounded
escalation, rechecking, dismissing a false alarm, budget stops, invalid verdicts,
target selection, label exclusion, accounting and existing geometry behavior.
All changed experiments, raw responses, prompts, source snapshot, replay trace
and the updated ledger were exported under ignored
`validation-artifacts/segmentation-iteration-20261008/`. The
[machine-readable summary](evidence/segmentation-iteration-20261008/decision-optimization-summary.json)
contains per-variant metrics, selections, hashes and accounting.

The live reader, its metadata, original inputs and unrelated work are unchanged.
No agent visually re-inspected these pages during this optimization; scoring used
the existing frozen development labels.

## Remaining qualification

Freeze this candidate policy before testing on independent annotated pages.
Measure final output quality and harmful false acceptance, not just judge accuracy
or fewer escalations. Include deliberately omitted panels, merged scenes, false
splits, wrong order, shared lettering and small artwork trimming on backgrounds
that do not qualify for the gutter refiner. Also measure unnecessary redetection,
fallback frequency, total latency and total cost. Separate budget/account failures
from segmentation failures. Use the frozen evaluation harness to compare changes;
do not make per-book agent inspection part of the product.

Then exercise the same controller with live, cached/resumable detector adapters
on a bounded fresh-page batch. Whole-book automated conversion and production
implementation remain future work. The proposed Rust plan now includes an
explicit quality-assessment boundary and automatic escalation policy.
