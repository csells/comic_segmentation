# Scene-assisted crop verification — 2026-10-09

**Result: useful development improvement, failed robustness gate; not integrated.**
Automatically generated scene descriptions corrected both observed ownership
errors in the three-control screen. Removing the descriptions made the checker
accept the same known defective crop again. The fixed runner stopped immediately,
preserving the failure and skipping the last request. No prompt was tuned or
request repeated after this result.

Nine new calls cost **$0.363682**; one exact baseline was reused from cache.
The experiment's ceiling was $5 within the shared $100 total authorization.
Total used/held is **$39.373507**, including unchanged **$4.30 unresolved holds**;
**$60.626493 remains**. All nine new calls settled with reported usage. No new
unknown hold, automatic recovery, or blind replay occurred.

## Fixed comparison

The [fresh control audit](scene-identity-control-audit-20261009.md) established
expected answers before new inference. It quarantined the old page57/6 pair:
the saved Sol rejection names the neighboring brown face, whereas the intended
target is a narrow cyan scene. That unsupported explanation must not count as
successful defect detection. The small taper difference itself remains ambiguous;
this does not adjudicate the old Astra response or qualify page57.

The scored controls are all from page150, with unchanged saved image bytes:
original lower scene/target3 (missing upper bouquet and ribbon), corrected lower
scene/target3 (intact), and corrected middle scene/target2 (intact even though
incidental bouquet artwork from the lower scene is clipped). These are one
negative and two positives from one development source, not three independent
pages. No synthetic defect was created.

Astra-high received only the complete source and the **original** automatic
proposal inventory. It generated scene identities, owned content, ownership cues,
neighbor distinctions and uncertainty. It did not receive crops, corrected
proposal geometry, reviewer labels, expected findings or earlier verifier answers.
Its saved descriptions correctly associate the airborne bouquet with the lower
scene's throwing action. That is a post-run visual assessment, not supplied text.

All verification used Sol-high, the existing marked source-detail v2 prompt and
unchanged verdict schema. The treatment appended fallible automatic hypotheses
and instructions to verify them against the source. Full source, actual crop,
clean source detail, marked crop extent, geometry, image order/detail and model
settings stayed fixed per case. The same generated descriptions were reused for
both original/corrected crops. The package changes both instructions and evidence;
its effect cannot be attributed to descriptions alone without the ablation.

Two robustness conditions were fixed before inference: rotate description
payloads across orders (1 receives2, 2 receives3, 3 receives1), and omit every
description while retaining identical auxiliary instructions. No reviewer-authored
scene descriptions entered any request. The generator and verifier builders
whitelist runtime fields; filenames, case labels and evaluation findings are absent.

## Observed answers

| Condition | Defective lower scene | Intact lower scene | Intact middle scene |
| --- | --- | --- | --- |
| Existing checker | **Wrong acceptance**, exact cached response | Correct acceptance | **Wrong rejection**: assigns bouquet to middle scene |
| Automatic scene assistance | Correct rejection, naming missing upper bouquet/stems/ribbon | Correct acceptance | Correct acceptance |
| Rotated descriptions | Correct rejection with source-grounded bouquet evidence | Correct acceptance | Not scheduled |
| Omitted descriptions | **Wrong acceptance — stop** | Skipped after stop | Not scheduled |

The assistance condition passed 3/3 controls; rotation passed 2/2 scheduled
controls. The full acceptance gate failed at omitted-description/negative. Do not
aggregate these correlated controls into a general accuracy percentage. The
omission failure was a predeclared stop even though the baseline already exhibited
that mistake. No uncertainty verdict occurred; uncertainty would not count as a pass.

Both correct negative findings were personally checked against the source and
actual crop. The intact crop decisions also match the frozen visual review.
The runner stopped with a nonzero exit because its explicit harmful-acceptance
condition fired; this was not a transport error or reason to retry.

Rotation leaves the true visual facts somewhere in the supplied inventory. Its
success therefore does **not** prove that the checker independently reconstructs
ownership or tolerates plausible false ownership claims. Omission directly shows
that the current package cannot provide the required robustness without evidence.
No scene-repair geometry, E2E conversion or reader publication was attempted.

## Cost and runtime evidence

| Work | New cost | Recorded request time |
| --- | ---: | --- |
| Two missing baselines | $0.058705 | 15.9s and11.2s |
| One Astra source-only inventory | $0.114913 | 53.0s |
| Three assisted checks | $0.092976 | 6.9s,23.8s,5.2s |
| Two rotated checks | $0.066433 | 9.7s,15.5s |
| One omitted check | $0.030655 | 12.5s |

Times are individual generation HTTP durations, excluding token preflight,
preparation and orchestration; this is not a throughput benchmark. The cached
baseline added zero new cost. There is no demonstrated production cost saving:
one source-inventory call was shared among repeated development checks.

Seven offline tests passed in VM153 for request-label exclusion, unchanged image
and model settings, deterministic rotation/omission, source tampering, unresolved
hold accounting, invalid identity responses and uncertainty handling. These test
harness correctness, not comic quality. Independent code review caught and fixed
missing shared-code hash freezing and a mixed uncertain/fail scoring edge before
paid dispatch. Initial preparation was retained with a pre-dispatch amendment.
An independent post-run artifact audit confirmed the outcomes, exact cost sum,
matching per-case image/geometry/settings across conditions, and exclusion of
reviewer labels, crops and corrected geometry from the generator request.

## Disposition and next hypothesis

Keep the scene-assistance result as research evidence. V28 remains unchanged,
page57 remains a whole-page fallback, and the currently qualified prefix remains
1–56. Earlier review through150 used older policies; no page151 was dispatched.
Reader Build10 remains active with `/healthz` HTTP200. No production Rust work or
promotion occurred. The frozen experiment is terminal; do not rerun its launcher.

A concrete follow-up would make a complete, source-linked scene inventory a
required input and escalate before judging if that input is missing or uncertain.
That would address missing-input handling only. It still needs fresh controls with
plausible wrong ownership or omitted owned content inside an otherwise populated
inventory, plus difficult intact/defective crops outside this page. Freeze those
controls and a finite request envelope before further calls. Do not relabel this
failed robustness test as a pass or treat a presence check as semantic validation.
Automatic repair and actual E2E qualification remain downstream of that evidence;
untouched-book and full-PDF work remain outstanding.

## Reproduction and preservation

Code: `prototypes/panel_quality_probe/experiments/scene_identity_v1/`.
VM evidence: `/home/tester/comic-reader/evidence/scene-identity-controls-v1-20261009/`.
The immutable run manifest includes source/proposal, input, prompt and shared-code
hashes. It preserves evaluation labels separately; sanitized request bodies,
full responses, timings, all generated/transformed descriptions, terminal stop,
spend and post-run review are retained. No credentials are stored in the artifacts.

Exact cached baseline ID:
`4efdac1289b76037e683147f7ac131fa2c68ac028d5b150afd388f862ca4e043`.
Generator ID:
`c197759293aac6d436858e7830411773cb03878b0800798643c97d95ac40fc7e`.
Terminal false-accept ID:
`a85da7b19bb5dada4d86eaf9417e22f2a95341f047aee419c2310a396ed21217`.

Off-VM archive under the ignored `validation-artifacts/segmentation-iteration-20261008/`:
`scene-identity-controls-cap100-20261009.tgz`, **2,694,721 bytes,177 members**,
SHA-256 `b36a630bde306a80f51fc8144be15e615855babc1666cc503e6c166aa5c35462`.
All156 regular files were read successfully during verification. The adjacent
verification JSON records the check; an extracted copy of the run is available.
This archive includes current source, new run and shared ledger; retain earlier
source/crop archives because referenced historical images are not duplicated here.
Service registry `comic-panel-reader-stage` revision38 and `machine-bumble`
revision47 were updated and read back with this terminal state and budget. The
service's stale pending-mask summary was replaced; dated earlier evidence remains.
