# OpenAI Decisions escalation test — 2026-10-08

**This configuration fails the diagnostic gate.** It caught both known bad
segmentations, but escalated ten of twelve usable candidates. Its low cost and
latency are promising; its discrimination is not yet useful for automatic
escalation. Sol low remains the selected first-pass detector, with reviewed
refinements/stronger results as before. Panel Lab build9 is unchanged.

Chris clarified that Laya meant the self-hosted open-source project, not Luna.
[Laya](https://github.com/NandhaKishorM/laya) accepts text/JSON, so it cannot
directly inspect these page images. Chris then asked about OpenAI's new decision
model and explicitly authorized this fourteen-case native Decisions experiment
with “Do that.” This supersedes the unresolved identity/approval state in the
[earlier preparation report](escalation-judge-prototype-20261008.md).

## Experiment and results

Used `POST /v1/decisions`, `gpt-6-luna`, with the fourteen frozen image bundles
and separate pre-existing labels. Every request included the original page,
numbered overlay and ordered crops when panels existed, plus whitelisted
geometry. Labels, detector identity, source run and page identifiers were not
sent as metadata. Printed page content was unchanged. No segmentation call,
retry, manual geometry edit or stronger-model escalation occurred.

Four independent predicates asked about scene inventory/classification, reading
order, clipped text and clipped artwork. The predeclared rule escalates if any
probability is at least 0.5. Refused, missing or invalid answers stop the run.
These are model estimates, not calibrated confidence. All fourteen responses
were valid. The API supplies scores here, not explanations or offending-panel
identifiers; the visual interpretations below are our hypotheses, not model
rationales.

| Page/candidate | Frozen label | Result | Main flag |
| --- | --- | --- | --- |
| 100 raw low | Escalate | Escalate | Art 0.97 |
| 100 gutter v2 | Keep | Keep | Maximum 0.03 |
| 205 raw low | Escalate | Escalate | Text/art 1.00 |
| 18 | Keep | Escalate | Art 0.98 |
| 175 | Keep | Escalate | Text 0.84 |
| 240, title/credits | Keep | Escalate | Scene 1.00 |
| 6 | Keep | Escalate | Art 1.00, text 0.95 |
| 25 | Keep | Escalate | Art 1.00 |
| 205 high v5 | Keep | Escalate | Text/art 1.00 |
| 254 | Keep | Escalate | Art 1.00, text 0.99 |
| 256, whole-page splash | Keep | Keep | Maximum 0.00 |
| 54 | Keep | Escalate | Art 1.00, text 0.99 |
| 5 | Keep | Escalate | Text/art 1.00 |
| 2, introductory page | Keep | Escalate | Scene 1.00 |

- Known defects caught: **2/2**; missed defects: **0/2**.
- Usable candidates retained: **2/12**; unnecessary escalation against frozen
  labels: **10/12 (83.3%)**.
- Agreement with all labels: **4/14**. The sample is deliberately diagnostic,
  not representative of full-book defect prevalence.
- Usage: **85,349 input tokens**, no output tokens. Conservative per-request
  micro-dollar rounding estimates **$0.008542** total, about **$0.000610/case**.
- Median observed request time **0.570 seconds**, range **0.293–1.334 seconds**.
  This includes local request/response processing in the VM, excludes credential
  retrieval and bundle preparation, and is not an SLA or concurrency benchmark.

## Visual recheck and interpretation

Reopened both disputed whole-page originals and all eight disputed panel-page
overlays. Inspected selected actual crops, including all six on page 175,
page 205's repaired balloon and collar, and background/inset crops on pages
5, 18, 54 and 254. No frozen label was changed. This was targeted adjudication,
not a second exhaustive inspection of every crop.

Pages 2 and 240 are introductory/title/credit layouts with illustrative strips;
whole-page presentation is intentional under our settled policy. They are clear
false alarms. Page 175's six crops preserve their associated words; balloons
already meet the source-drawn borders. Page 205's repaired crop 2 contains the
complete shared thought balloon, and crop 9 contains the complete loose collar.
Yet the judge gives its repaired and defective versions identical maximum
text/art scores. In contrast, it distinguishes raw and repaired page 100.

Some rectangles necessarily include fragments of adjacent or inset scenes.
Pages 5 and 54 visibly demonstrate clipped *neighboring* fragments alongside
complete target scenes. Confusing these fragments with defects in the target
scene is a plausible failure mode. Numbered overlays can also obscure pixels.
Neither explanation is proven by the returned predicates, and neither accounts
for every flag. The prompt already permitted overlap and legitimate whole-page
layouts; merely restating that instruction is not an established fix.

Increasing a single threshold cannot separate these cases: several usable
candidates have maximum score 1.00, while one real failure scores only 0.97.
Do not tune a threshold on this sample and present the same pages as independent
validation. Two bad candidates are also insufficient evidence of general recall;
we have not tested planted omissions, merges, wrong order or false splits here.

## Accounting and reproducibility

The [official Decisions guide](https://developers.openai.com/api/docs/guides/decisions)
documents image inputs and $0.10/M input-token billing without output/cache
charges. The [model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna)
documents a doubled input rate above 272k tokens. Actual requests were well below
that boundary. Cost is a gross-input estimate, not a provider invoice.

Each request held a conservative $1 before dispatch; successful usage released
the excess immediately. Fourteen reserves and fourteen settlements were appended
to the existing locked ledger. All earlier bytes and $3.60 unknown Gemini holds
were preserved. Current total is **$4.603790 used/held of $20**: $1.003790 in
reported-usage estimates plus the $3.60 unknown holds. There are now forty OpenAI
segmentation successes and fourteen separate Decisions successes.

Candidate execution and all 29 regression checks ran inside disposable VM153.
The new module's tests failed before implementation and passed afterward.
Checks cover threshold boundaries, refusal/missing/mismatched answers, invalid
probabilities, fractional/native input-only billing and long-context pricing;
existing checks cover label exclusion and unknown-attempt protection. The
credential traveled in memory through SSH stdin and was not saved on the guest.

The [nonprivate evidence summary](evidence/segmentation-iteration-20261008/luna-decisions-v1-summary.json)
contains all scores, costs, timings and hashes. Private artifacts were copied
from the VM to ignored `validation-artifacts/segmentation-iteration-20261008/`:

- `luna-decisions-v1-20261008/`: requests, raw responses, request IDs, verdicts,
  timings, run policy, source snapshot and fetched official documentation.
- Existing `judge-cases-v1-20261008/`: unchanged bundles, crops and frozen labels.
- `decisions-originals-20261008/`: twelve original page images needed to replay
  the requests offline.
- `budget-after-decisions-v1-20261008.jsonl`: updated shared ledger snapshot.

All fourteen wire-payload fingerprints were reconstructed from exported images
and compared with their recorded request IDs. Image hashes matched. The ledger
was checked for an unchanged historical prefix and matching new settlements.

## Consequence for the implementation plan

Do not adopt this configuration as the automatic gate or wire it into published
reader metadata. Keep the Rust quality-gate boundary replaceable and escalation
unvalidated. A useful next experiment would isolate one target scene and compare
its crop against the source without a numbered overlay, explicitly distinguish
title/credit layouts, and require localized evidence in a parallel explanatory
judge. Test any revised representation on these diagnostic cases, then on fresh
pages with different defects. This is a proposed follow-up, not an executed or
validated remedy. Production rewriting and full-book acceptance remain open.
