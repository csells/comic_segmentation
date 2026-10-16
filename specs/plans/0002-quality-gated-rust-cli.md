# Establish quality, then implement the Rust comic CLI

Status (2026-10-16): **Rust CLI implemented in `cli/` on branch `comic-panel-cli`;
production-readiness record in
[cli-production-readiness-20261016](../research/cli-production-readiness-20261016.md),
approved by Chris and merged to `main` on 2026-10-16 (`3779a81`).** The Rust port reproduces the V63
prototype byte for byte (see
[rust-port-parity-20261015](../research/rust-port-parity-20261015.md)). The
milestones below remain the design record; their completion status is in the
readiness record. Original status, updated 2026-10-10: V32 fixes the tested V31 clipped-art failure by giving the
cheap checker marked source context, then letting the existing stronger verifier
decide. All seven integrated quality controls and five actual CLI conversions
passed, along with 35 reader steps and ten actual-main resume/corruption checks.
The sequential prefix then stopped at page5: a late strong-mapper inventory
correction is not routed back to independent source audit, causing an unnecessary
whole-page fallback despite seven correct proposed crops. That generic routing
fix is the immediate gate; broader validation remains open. The H diagnostic adds
at most one independent source audit for that late conflict, retaining the same
prompts, models and strict mapping checks. Its 35 offline regressions pass;
all13 real-response diagnostic cases and root semantic review now pass. Fresh
V33 end-to-end qualification remains pending. The diagnostic used three new
requests/$0.100046 with38 cache reuses; no prompts or model settings changed.

## Current evidence and implementation decision

Retain Sol-low as the provisional first detector, with deterministic refinement,
bounded Sol-high/Astra escalation and independent quality checks. The experiments
support this research direction; they do not establish reliable segmentation of
arbitrary comics. Alternative detectors remain eligible. The tested specialist,
deterministic and mask configurations did not preserve all required content and
were not integrated. Their configuration-specific results are in the
[broad research](<../../reports/Robust comic panel segmentation.md>),
[preprocessing screen](../research/preprocessing-spikes-20261009.md),
[boundary trials](../research/seeded-boundary-spike-20261009.md) and
[specialist trials](../research/specialist-mask-spikes-20261009.md).

The current evidence separates three questions:

| Question | Evidence | Remaining limit |
| --- | --- | --- |
| Are all source scenes represented? | Generic G source inventory and mapping passed 11 personally reviewed diagnostic cases; V31 rejects the tested missing swing, photograph inset and cannon. | Tested development cases do not prove general scene recall. |
| Does each crop retain its own content? | V32 rejects the deliberately clipped swing through automatic escalation and accepts all three intact controls; all seven controls pass. Five actual V32 CLI outputs retain every personally reviewed source/crop byte and ordered region. | Development controls do not establish arbitrary-comic quality. The cheap checker still raises false alarms resolved by stronger checks. |
| Can the result be delivered and read? | V30 prefix six-page conversion passed PDF, CBZ, genuine RAR5 CBR and folder parity, with 80 browser steps. Five actual V32 CBZs passed 35 browser steps; valid resume and four corruption types passed on two outputs. | Four-format parity must pass on the corrected candidate; viewport tests are not physical-phone tests. |

The five V31 CLI source pages are 1, 56, 6, 57 and 144, with 0, 8, 7, 13 and 2
panel steps. They used the actual detector, controller, ownership verifier,
completeness guard and exporter, with zero new requests and 226 cache reuses.
Root reviewed each original and every selected crop without supplying geometry
or runtime decisions. Isolated Chrome at 390×844 verified full-page overview
first, panel order, end boundaries, cleanup and persisted resume. Curved panels
still include neighboring artwork within their rectangular viewports.

All 275 V31 offline tests passed, including saved-proof binding. That establishes
implementation behavior under those tests; it does not clear the quality-control
failure. The seven injected controls produced six correct outcomes and one
harmful acceptance. The two new omission answers identified the actual missing
views; the clipped-art failure is substantive, not a transport error or a malformed
proof. Read the [control protocol and result](../research/v31-injected-quality-controls-protocol-20261010.md)
and [completeness results](../research/source-completeness-guard-results-20261009.md).

The marked-context native screen caught the clipped swing and accepted its intact
pair, but stopped on an intact P6 false alarm. Its three calls cost $0.001853.
[Diagnostic B](../research/crop-extent-b-automatic-route-20261010.md) applied that exact package to every target visited by the actual
judge and passed all three final outcomes: N2 rejected, intact P56 and P6 accepted.
Sol identified the actual missing swing beam, seat and plants; the existing
ownership verifier cleared P6's false alarm. Root checked those explanations and
verified every positive source/crop byte against the prior personal reviews.
This was an injected-proposal quality-boundary diagnostic, not detector-to-CBZ
E2E. It added 21 requests / $0.030952 and reused 37 responses. The native package
also removes automatic ownership hypotheses from native target inputs only;
the strong verifiers retain their existing evidence. Prior unmarked context
failures remain failed evidence. A source-scene inventory alone cannot certify
crop extent, and lowering a threshold cannot fix an observed score of zero.

V32 passed 281 offline tests and all seven integrated controls. Its five actual
CLI conversions of the same source pages produced the same 0/8/7/13/2 panel steps
and every source/crop byte and ordered region matched the earlier personal
reviews. Actual detection, refinement, quality checks, escalation and export ran
without human routing. The five successful invocations added 41 native requests /
$0.028417 and reused 185 responses; the two denied-network preflights reused 21
more responses. Cached stronger-model work makes this an incremental cost, not a
cold page-price estimate. All five actual CBZs passed 35 reader steps; root
personally inspected the 14 retained overview/final/resume screenshots.
Ten actual-main resume/corruption checks passed without requests: intact resumes
retain identical CBZ bytes, while altered source, geometry, proof and publication
bindings reject before publication. The scoped research source now matches V32;
unrelated newer reader and sequential-review work is preserved.

Next, complete the broader historical positives and six-page four-format parity,
then the frozen 12-unit/three-artist independent
screen, and finally all 257 PDF pages sequentially with personal review and
complete reader traversal. Independent fixtures remain untouched. Earlier
V30/V28 reviews are dated evidence, not completion of these new-candidate gates.
The [development results](../research/v30-development-regressions-20261009.md)
and [request economics](../research/v30-request-economics-20261009.md) preserve
those prior outputs and cold-versus-incremental cost distinctions.

Shared spending plus retained holds is **$55.634680 of $100**, leaving
**$44.365320** after the H diagnostic. Its request-limit continuation
finished with nine new calls/$0.236279; the entire prefix added38/$0.713015. The
shared integration total is$1.925498/140 requests under the prospectively
authorized$6/256 allowance and unchanged global cap. Four prefix pages have
passed personal review. The failed V32 page5 remains unaccepted; the qualified H routing fix still needs
fresh actual CLI validation. All successful calls are retained. The handoff owns later live accounting.
Historical unknown, quota and service-failure holds remain counted; a hold does
not assert billed usage. Do not repeat a successful request to recreate evidence.
No finite benchmark establishes perfection for every comic.

Stable Build10 and the existing phone catalog remain unchanged. Application,
model, test and browser execution stays in disposable VMs. The Rust design below
remains available for discussion while quality gates are open; approval to develop
or passing tests is not approval to promote a staged service.

## Settled scope and proposed sequence

The [vision](../vision/comic-panel-cli.md) remains authoritative: macOS-first
portable Rust, CBR/CBZ/PDF/image-folder input, new CBZ with complete pages and
panel metadata, phone-browser review first (native Android later), a detector selected by measured quality, automatic operation,
reported whole-page fallback after bounded detection failures. Developer quality
assessment never becomes a product review/correction interface. CBC remains outside this plan. Chris explicitly reopened detector selection on 2026-10-08, including OpenAI and existing specialist/deterministic tools. A narrow web-reader adapter is now authorized for reviewing the converter experiments; a general reader product is not the objective.

Proposed sequence: **quality baseline + reader qualification → Rust offline
vertical slice → bounded selected-detector integration → input hardening → release evidence**.
Completing a gate records evidence; it does not grant permission to incur new
spending, start unapproved implementation, or promote a staged candidate.

## Gate 1: establish a representative quality baseline

The [completed Sol confirmation](../research/sol-confirmation-20261008.md) selects
OpenAI Sol low v4 as the first-pass research default. Ten of twelve sampled pages
were usable directly; page 100 needed image-derived dark-gutter expansion and
page 205 needed Sol high v5 to preserve a shared balloon and collar. The original
Sol-high v4 result also clipped that balloon. All final sample crops/order were
inspected, but automatic failure detection/escalation is unvalidated. Chris
approved the earlier Astra pilot. Magi and Western YOLO have failed pilot results.
No whole-book acceptance exists. These12-page findings are historical; the active full-book progress and current prompt versions are in the sequential review report.
The [native OpenAI Decisions diagnostic](../research/openai-decisions-judge-20261008.md)
caught both known defective candidates but escalated ten of twelve usable ones.
Do not select that prompt/input configuration as the automatic quality gate.
Keep judge identity, input representation, rubric and routing threshold versioned
separately from the detector. A judge error/refusal must never certify a page;
judge approval itself needs independent validation. This leaves escalation
selection as an explicit research gap before production orchestration.
The [subsequent optimization and automatic replay](../research/automatic-escalation-optimization-20261008.md)
combines deterministic refinement, target-specific Decisions checks and selective
target-specific Sol verification. Without runtime label lookup or human routing,
the replay selects the accepted geometry on all twelve development pages and
escalates only page 205 to its cached stronger detection. This is a candidate
automatic policy, not a held-out quality result or live detector integration.
Chris explicitly requires automatic quality control; agent inspection of every
converted page is not part of the product or the scaling workflow.
Specialist tools remain eligible; no provider is irrevocably selected. The automatic
corpus review in plan 0003 is active, while the multi-book benchmark below remains
a proposed release gate. The Rust detector boundary should accept ordered regions,
whole-page classifications, provenance and failure reasons independent of provider.


The existing four-page sample is a diagnostic seed, not a benchmark. Page 25 is
a known merge failure; page 5 has no successful Gemini output. Before choosing
a production model/prompt, freeze a developer evaluation corpus and rubric:

1. Use the recovered, hash-verified source PDF and saved private results. Preserve
   their source/render identities, keep them ignored, and reuse successful
   responses rather than replaying them simply to rebuild artifacts.
2. Propose **24 real pages from at least three books**, with 12 development and
   12 held-out pages drawn from untouched books/artists, not adjacent pages of
   a development book. This anthology remains development-only. Include covers/contents/splashes/blanks, ordinary grids,
   irregular/borderless panels, insets/overlap, spreads, small lettering and RTL.
   Assign at least two pages to each difficult layout stratum; strata may overlap.
   Confirm available, authorized source material before freezing the manifest.
   The [independent corpus](../research/independent-fixtures-20261009.md) now
   contains twelve acquired input units from three artist/book groups, including
   native RTL manga and tall webtoon sections. Their source-only inventories and
   reading order are [frozen before inference](../research/independent-source-audit-20261009.md).
   Acquisition and annotation do not establish segmentation quality; no model
   inference or held-out qualification has yet run on those units.
   Pages 1, 3, 5 and 25 belong in the development set, never the held-out set.
3. Record expected scene identities, required art/text associations, bounds and
   narrative order independently of candidate output. Distinguish frame boundaries
   from protruding/shared content; freeze treatment of meaningful pale artwork,
   scan halos and ambiguous ownership/order before scoring. Label legitimate
   whole-page compositions separately from failed detection. Developer annotations
   never supply runtime geometry, seeds, routing or approvals.
4. Score panel recall/precision using one-to-one matching at a proposed bounding
   box IoU threshold of 0.80, then separately assess merges, splits, missed insets,
   lettering clipped by the guided region and order. IoU is a diagnostic; it does
   not certify legibility or resolve irregular-panel ambiguity. Define a strict
   page pass as every expected panel present once, no extra/split/merged region,
   complete associated art and lettering, an allowed reading sequence and a useful
   phone viewport. Report thin-structure loss, maximum inward clipping and harmful
   neighboring-scene intrusion separately. Repeating the full page for each panel
   fails usefulness; incidental neighboring art in a necessary rectangular viewport
   does not automatically mean the scenes were semantically merged.
5. Report raw counts and per-stratum outcomes: strict page passes, panel matches,
   order passes, correct whole-page classifications, service fallbacks, invalid
   responses and calls/usage. For strict page pass, a service fallback on a
   panelized page is a failure, not an excluded sample. Show quality conditional
   on a successful response as a separate metric.

**Proposed pilot gate for discussion:** at least 23/24 strict page passes, no
unreported merge/missing panel/clipped lettering/wrong order on any evaluated
page, no failed difficult-layout stratum, and at most one reported service
fallback on a panelized page. Require both halves to be reported separately;
do not tune on the held-out set. These are proposed thresholds, not user decisions
or statistical evidence of production accuracy. A later independent book-scale
sample is required before broader quality claims. Failure means continue bounded
detector research or revisit expectations; porting plumbing does not improve it.

**Historical proposed experiment, superseded by active plan 0003 and the approved $20 comparative pilot:** change one documented
variable (for example, instructions distinguishing adjacent bottom panels), test
only source pages **5 and 25**, one request plus at most one eligible retry per
page: **maximum four generation calls total**, sequentially, with the recorded
8192 output-token cap. Compare page 25 to its saved Flash result and seek the
first valid page-5 result. Name the selected model and concrete hypothesis first.
Stop on hard quota/auth/model/request errors. No automatic Pro substitution,
billing change or full-book inference. Expanding to the 24-page corpus requires
its own finite request/token/spending envelope; this document allocates no money.

Gate completion: a versioned corpus manifest, rubric, unedited outputs, scored
baseline and explicit pass/fail decision. Current evidence **does not pass**.

### Advancement gates for the current hybrid research

| Advance to | Required evidence | Stop condition |
| --- | --- | --- |
| Integrating a boundary/mask adapter into the prototype | Pinned model/code, input and transform hashes; unchanged automatic seeds; source/crop review on known defects 18/21/40/57/150 plus intact controls. Inventory/order, ownership and boundary completeness pass separately. Record coverage, abstentions, memory, latency and local compute. | Any recurring merge, clipped meaningful content, dropped required positive point or foreign-content assignment; component connectivity, seed retention, mask score and box/mask IoU cannot override it. All completed mask configurations fail here. |
| Freezing a hybrid policy | Actual import → automatic detection/refinement/judgment → CBZ → hosted reader on the development regression set, without human intervention. Known defective crops must be rejected and intact controls accepted. Freeze prompts, algorithms, ownership rules and bounded escalation before evaluating untouched books. | Runtime labels/manual seeds, a known harmful false acceptance, or repeated contradictory verdicts on equivalent evidence. Investigate the representation; do not retry until a pass appears. |
| Resuming the full-PDF sequential qualification | The page-57 failure pattern is resolved by the frozen automatic policy; every changed earlier output is revalidated against actual source/crop bytes. Budget and request limits cover the selected policy. | Stop on the next recurring failure class; preserve evidence and repair generically before advancing. A reported fallback remains unsegmented, not a strict page pass. |
| Production implementation readiness | Gate 1's untouched-book results, Gate 2's actual reader artifacts and the full-PDF outcome are recorded separately. Report false acceptances, fallbacks, cost and tail latency; state unsupported/uncertain layouts. This plan is available for discussion now. | The development anthology alone cannot establish generalization. Failed or tuned-on holdouts require a new untouched evaluation set. Passing evidence does not itself authorize the production rewrite or promotion. |

These are research advancement criteria. The numerical release thresholds above
remain proposals for discussion; no finite sample establishes perfection for every
possible comic. Prototype work continues within the authorized total cap.

## Gate 2: browser-based phone review first

**Experiment delivered:** [web-reader validation](../research/web-reader-validation.md)
records the hosted candidate and passing Chromium phone-viewport checks. Physical
device/browser qualification remains open. Chris reported that Panel Lab works,
and the [PDF-backed saved-result replay](../research/pdf-saved-result-replay.md)
now supplies real books. He then rejected their panel-detection quality. This
does not close Gate 1; improving detection is the next product-quality task.

Chris superseded Android-first on 2026-10-07: provide a home-lab-hosted web reader
for CBZ plus panel metadata, with a link that reflects experiments without app
installation. Preserve the completed Android evidence as later compatibility
coverage; physical Android app installation no longer gates this phase.

Evaluate existing web readers first. Panel by Panel consumes ACBF but requires
unpacked books and PHP; PanelView opens CBZ and has a mobile guided view but needs
an ACBF importer. The authorized experiment can adapt an existing reader to consume
our exact archive metadata, with no segmentation, manual editing or new AI calls.
Keep this experimental web code under `prototypes/`, separate from the Rust CLI.

Gate completion: an isolated home-lab candidate with a remotely accessible HTTPS
review URL; real CBZ loading; cover once; every complete page first, then its
panels in exact metadata order (synthetic control **3 → 1 → 4 → 2**);
previous/page-boundary navigation; readable whole-page fallback and page mode;
phone-sized viewport/rotation tests; and a clearly labeled synthetic demonstration.
The agent verifies the actual hosted reader before offering it. Chris's phone
feedback is optional qualitative assessment, not a substitute for agent tests.

Use existing private outputs only when recovered and hash-verified; a synthetic
fixture can establish the transport/navigation path immediately. Record browser
and device scope accurately: desktop mobile emulation is not a physical-phone
pass. Preserve all experimental source and geometry; never silently redetect
panels when metadata is malformed. Hosting changes must stay in a disposable VM
under the global development rule; expose its URL through a relay if needed.

Later Android work can reuse the stock v2.0 release asset's known control result
and extend real-book/device qualification when Android returns to scope. Keep
its release URL/hash and the separate v2.1 startup-workaround qualification in
[the Android report](../research/android-reader-validation.md).

## Rust ownership and interfaces

After the gates and implementation discussion, begin with one crate containing
a library plus a thin CLI. A proposed `convert(request) -> RunOutcome` owns the
workflow; `resume(run_directory) -> RunOutcome` continues recorded work. Keep
module seams at external effects or independent invariants, not a framework of
speculative providers.

| Module / narrow operation | Owned contract | Reused dependency |
| --- | --- | --- |
| `import.prepare(source, policy) -> PreparedBook` | Inventory every page/auxiliary file, validate extraction, canonical identity/order, orientation and source-to-output mapping; fail before inference on unreadable content. | ZIP/RAR readers, image codecs, installed Poppler. |
| `geometry.validate(response, page) -> PageOutcome` | Types, completion, classification, ordered positive boxes, image coordinate transform; explicit failure reasons. Pure and offline-testable. | Serde JSON and image dimension primitives. |
| `detector.analyze(page, contract) -> AttemptOutcome` | Exact selected-provider protocol, timeouts, error/usage normalization, no hidden retry or model switch. Start with the measured OpenAI contract; recorded fixtures exercise the HTTP boundary. | Selected inference service; established HTTP/TLS client. |
| `geometry.refine(page, outcome, policy) -> RefinedOutcome` | Optional mask/source-boundary proposals and conservative viewports with raw geometry retained, exact transforms, seed provenance and before/after evidence. Preserve scene identities/count/order; ambiguous ownership remains unresolved. No semantic certification from connectivity or mask overlap. | Qualified image-processing or specialist-mask adapter; research configurations are not shipping dependency choices. |
| `quality.assess(page, candidate, policy) -> QualityOutcome` | Separate inventory/order, semantic ownership, source-boundary completeness and viewport-usefulness outcomes; flagged scene identities and immutable scoped evidence. A mask pass cannot clear a semantic/crop failure. No human-routing dependency; invalid/unknown responses cannot certify quality. | Qualified decision/verification providers; saved fixtures and independent annotated evaluation set. |
| `run.advance(book, policy) -> RunOutcome` | Retry/quota/circuit-breaker policy, immutable attempts, budgets, resume identity and progress/reporting. | Filesystem/hash/clock primitives; injectable clock for deterministic retry tests. |
| `publish.commit(book, outcomes, destination) -> PublishedBook` | One cover, ACBF profile, source metadata retention, archive integrity, all-page coverage and atomic no-replace publication. | ZIP writer and XML writer, pinned XSD/parser in validation tooling. |

`PreparedBook` contains ordered `PageId`s, original locators and hashes, final
publication-image hashes/dimensions, analysis-image hashes/dimensions, transforms,
cover role, direction and retained metadata. `PageId` includes the book identity
and original locator/ordinal: identical page bytes at different positions remain
distinct pages. Basenames alone never identify a page.

`PageOutcome` distinguishes `Panels`, `WholePage` (legitimate cover/splash/blank)
and `Fallback { reason, attempts }`. Import failure and account-wide failure are
run outcomes, not successful page outcomes. Store ordered panels; never sort
the detector's returned sequence by coordinates. Overlapping rectangles are allowed.

Within a panel candidate, retain four distinct records rather than replacing a
semantic rectangle with an unqualified foreground mask:

| Record | Meaning and invariant |
| --- | --- |
| `Scene` | Stable candidate-local identity, order constraints and required art/text associations. Shared balloons or protruding objects may belong to more than one scene; unresolved membership is explicit. |
| `MaskEvidence` | Proposed frame/balloon/text regions, including disconnected components, source-pixel transform, algorithm/model, exact automatic prompts and observed seed compliance. It is evidence about appearance, not ownership truth. |
| `BoundaryEvidence` | Native-source neighborhoods, uncertain boundary bands and measured content outside the proposed viewport. Keep clean source, optional marked boundary and actual crop; thresholded/cleaned images never become authoritative publication art. |
| `Viewport` | The final integer source-image rectangle shown by the reader, derived from the scene's required content. Record actual crop extents and mapping to publication pixels; preserve original art and allow necessary overlap. |

Initially publish rectangular viewports through the tested ACBF profile; masks
remain internal and do not erase surrounding artwork. Map coordinates once with
the crop API's explicit inclusive/exclusive convention. Judge cache identities
include every image and contextual field actually sent, not just crop bytes.
An ownership dispute routes a semantic question with full-page context; a confirmed
localized boundary defect routes source-detail/refinement. Missing/merged/split
scenes require inventory repair, never merely an enlarged mask or viewport.
Exclusive target/rival point hints must come from automatic semantic evidence,
with shared or uncertain ownership kept explicit. A mask missing a required
positive point is invalid for that candidate; satisfying all point hints still
does not establish complete content between or beyond those points.

Keep raw model geometry and refinement separate. A refinement's identity includes
its algorithm/version and parameters, in addition to the source image and raw
response hashes; changing it must not require another paid inference call.
Record developer-selected escalation as research provenance. Production must not
silently depend on a human identifying missed panels or clipped balloons. A
model's self-reported confidence or valid JSON is not an established quality signal.

The V32 research candidate retains V30's Sol-low → Sol-high → Astra-high
detection, V31's mandatory source-completeness guard, and B's marked-context
native crop check. Its integrated quality gates remain pending. Explicit LTR
preserves generic v6 and its response cache;
auto/RTL use the direction-aware v7 prompt. Raw and refined geometry remain
separate. Structural, inventory, continuity, order and crop checks remain binding;
risky layouts additionally require source-bound Astra ownership evidence and
marked Sol crop confirmation. Required target checks persist through valid
geometry-only repair ancestry even if an overlap score falls. This is a versioned
research policy, not a frozen production specification. V28 remains the historical
prefix/fallback baseline; the [V30 lineage evidence](../research/ownership-lineage-v30-20261009.md)
records the controller correction.

Carry these orchestration constraints into the Rust design; the particular model
choices, thresholds and repair counts remain research choices:

- Establish scene coverage before accepting a first proposal. N1 proves that
  empty overlap/continuity flags and a cheap global scene-defect score of0.0 can
  coexist with a completely omitted narrative panel. Prior-proposal inventory
  conservation cannot detect a scene that no proposal ever contained. Qualify a
  source-first omission gate against both ordinary missing panels and missing
  insets inside otherwise covered rectangles. The qualified G diagnostic uses an
  independent source inventory followed by source-to-step mapping. Earlier source
  uncertainty triggers a stronger audit even if a later inventory sounds certain;
  a cheap missing verdict or structural conflict receives one stronger mapping.
  V31 exercised these choices in actual CLI conversions and omission controls;
  unseen-book validation and the corrected V32 integration remain open. A positive finding must remain binding through escalation
  and repair until a specifically qualified check resolves it.
- Apply that final completeness check to every provisional acceptance: native
  judgment or stronger verification, detector or repaired candidate, and legitimate
  whole-page classifications. Record its source, candidate and policy binding
  separately from verifier-clearable flags. Reusing an accepted checkpoint also
  requires a matching positive binding; an older policy's accepted record cannot
  silently skip a newly required check. Explicit fallback is still distinct from
  a quality pass.
- Keep source-scene completeness and crop extent as separate acceptance
  obligations. V31's clipped-art control contained all eight scenes and still
  lost substantive artwork. B's marked-source native check correctly triggered
  the existing stronger verifier, which confirmed the missing content; an intact
  crop's cheap false alarm was correctly cleared. Preserve the source, actual
  crop, clean context and boundary locator in request identity. Evaluate the
  automatic final outcome, while reporting the cheap check's false alarms and
  misses separately from final quality and escalation cost.
- Define the inventoried unit as a visually separate panel/view composition.
  Separate insets and borderless panels need their own steps; a composited
  portrait, silhouette or change of scale inside one continuous composition does
  not automatically create another panel. The E diagnostic shows that stronger
  reasoning alone does not settle this distinction. The definition and uncertainty
  routing need both omitted-panel negatives and intact-montage positives.
- Bind acceptance to the exact analysis image, candidate geometry and ordered
  crop bytes, policy and request/response evidence. At resume and publication,
  verify that the selected candidate is the final accepted attempt and its
  checker trace is possible under the controller. Keep the publication image's
  identity separate from the analysis JPEG. Archive reuse additionally requires
  an unchanged ordered publication-input digest, including proof identities,
  direction, statuses and fallback reasons; a structurally valid old CBZ is not
  evidence that it represents changed inputs.
- Keep the largest earlier panel inventory across escalation; a stronger model
  returning fewer boxes must explain the lost views. Count conservation alone
  does not establish scene identity.
- Check continuity from original source regions. At the final tier, a limited
  window of actual preceding pages can resolve montage ambiguity. Build that
  window from source order before applying any developer page selection.
- Keep whole-page and individual-crop verdicts independent. A global pass cannot
  clear a crop failure, and crop passes cannot clear a global failure. All gates
  must pass, or the page escalates/falls back.
- Treat uncertain crossing-artwork ownership as a reason for stronger inspection,
  even when the cheap crop check passes. V23's source-only risk screen and0.2
  threshold remain development choices requiring independent qualification.
- Reuse content-identical provider requests across policy changes. Re-run local
  policy/refinement and audit changed final artifacts without repeating successful
  paid requests. Include every relevant code/prompt/schema version in run identity.
- Bound detection to three named tiers. V28 prototypes at most two model geometry
  repairs only for machine-confirmed localized clipping after those tiers fail.
  It preserves inventory/order, cannot shrink content or change unflagged boxes,
  and must pass all independent checks again. A no-change model repair stops; no
  third model repair is permitted. One final deterministic correction may expand
  specifically flagged edges to a nearly enclosed source color component, only
  when every unresolved target qualifies. This is not a default page refiner and
  must pass all quality checks again. Exhausted
  quality attempts produce a reported whole-page fallback; budget/account/unknown-
  request failures stop resumably. Preserve every attempt and selection reason.
- A final repaired crop's clipping warning can receive one further scoped check
  with enlarged source context and its exact generated crop boundary. The clean
  source detail remains alongside the marked copy. Preserve both verdicts; a
  contextual pass clears only that target warning, never an independent global
  or structural failure. Feed only unresolved findings into a subsequent repair.
- Stop expensive checks on an intermediate candidate once a binding verdict
  already requires stronger detection. Preserve complete checks at the final
  tier for acceptance and repair feedback. Page57 exposed13 redundant stronger
  crop requests after its intermediate whole-page rejection; those calls do not
  improve the eventual selection.

All three detector tiers are exercised in the prototype. Page150 demonstrates
why broad verification alone is insufficient: even Astra's full-page check missed
a clipping defect that its scoped crop check caught. Personal inspection has
qualified the corrected bounded result, and page18 passes automatic escalation
plus repair. Page57 exposed both real tapered-edge clipping and false alarms
about neighboring scenes. An unmarked source-detail verifier was rejected for
missing a then-labeled clipped tip. Historical marked-detail checks were recorded
as four paired development controls. The later source-identity audit quarantines
the old57/6 negative/positive pair: a rejection identified the neighboring scene,
so those labels do not establish correct target verification. Preserve the old
records but do not count that pair as successful evidence. Other source/detail
reviews found a further real omission in crop10.
The two-model-repair regression fixed10 but exposed another narrow omission in12.
The final source-component correction restored that edge offline, but V28's actual
regression finished with page 57 a whole-page fallback. Final marked-detail checks
rejected targets 8/10 and accepted 9/12; this is not complete-page success. A broad
application changed 56/150 pages, so the heuristic remains limited to final
machine-flagged targets and unqualified on other books. Completed preprocessing
did not recover additional useful source detail. The seeded-mask screen shows
why source-connected components cannot establish scene membership: it retained
100% of accepted eroded cores and zero competing-core pixels while still merging
two scenes and admitting unrelated art. Preserve those failures as regression
controls for specialist adapters. The subsequent Koharu/ShadowB frame screens
omit whole scenes. SAM's automatic semantic-point screen improves separation
without preserving all thin/disconnected content; removing the boxes shifts the
errors instead of eliminating them. Preserve the box, box-plus-point and point-only
counterexamples and exact automatic hints. No tested mask correction has replaced
V28; another experiment requires a concrete ownership/completeness hypothesis.
Full-book revalidation is unfinished. This is development evidence, not proof of
quality on arbitrary books.

## Policies to settle before implementing each boundary

The following are engineering proposals, not additions to the accepted scope.

| Concern | Proposed behavior and acceptance evidence |
| --- | --- |
| Transport/model | Begin from the saved OpenAI Responses contract in `openai_probe.py`: original-detail image, strict structured output, direction-aware generic prompt (v6 for explicit LTR cache compatibility; candidate v7 otherwise), Sol-low first pass, recorded output cap and explicit reasoning effort. Preserve requested/returned model and usage. Sol-high and Astra-high are explicit bounded tiers selected by versioned quality policy. Verify exact API/model availability and rates when implementing; Gemini is a historical comparator. |
| Input order | PDF intrinsic page order. For folders/archives, explicit page-list override if supplied; otherwise one unambiguous, complete existing ACBF page map; otherwise deterministic natural relative-path ordering with bytewise tie-break. Report provenance and resolved order; reject ambiguous or incomplete supplied maps. ComicInfo catalog data alone is not a complete page-order authority. Arbitrary names cannot reveal intended narrative order. |
| Direction | Explicit CLI choice first, recognized source direction next, documented LTR default last, with provenance. Feed the selected direction into the model contract. ACBF1.1 has no standard direction field. The tested candidate writes optional `panel-reader.json`, bound to the exact ACBF hash; RTL controls passed synthetic browser tests, while native RTL segmentation remains unqualified. |
| Images/PDF | Compose whole PDF pages through Poppler. Keep publication and analysis copies separate; use tested JPEG/PNG publication images, preserve existing compatible upright image bytes when no transform is required. Normalize orientation once and record transformations. Qualify render resolution/color/lettering; 150 DPI is an experimental setting, not a quality guarantee. Reject unsupported multipage/animated variants rather than silently discarding frames. |
| Geometry/profile | Reject bad types, out-of-range coordinates, zero area, inconsistent order/orientation and incomplete generation. Convert validated 0–1000 boxes to final pixels with floor left/top, ceil right/bottom capped at width−1/height−1; reject collapsed boxes. Emit one lowercase root `metadata.acbf`, ACBF 1.1, `publish-info`, ordered integer polygons and exactly one cover. Fallback uses the tested whole-page frame. |
| Single image | The prototype now supports one-page books with cover-only ACBF1.1, omitting the body and retaining cover frames. Official XSD and web reader checks pass; never duplicate art. Pinned Android body assumptions remain deferred. Port this demonstrated web-profile behavior and preserve the original image. |
| Catalog metadata | Preserve auxiliary bytes and original ACBF as inactive `.acbf.original`; propose catalog precedence explicit CLI fields → one valid source ACBF → ComicInfo → documented unknown/default. Record conflicts and provenance; do not merge incompatible page maps or silently overwrite originals. Qualify Android catalog display. |
| CBR/RAR | Qualify RAR4/RAR5, solid/non-solid and stored/compressed fixtures before selecting the extractor. Explicitly reject encrypted/multipart/unsupported variants in preflight unless support is demonstrated and included in the stated matrix. CBR remains required; the tested subset must be named and discussed before release. |
| Extraction/resources | Inspect entry paths and types before extraction; reject absolute/traversal paths, symlinks/hardlinks, duplicate or case/Unicode-colliding destinations, CRC failures and escaping references. Stream into a new private directory. Enforce both declared and actual limits on entries, expanded bytes, per-page pixels, XML depth/size, request bytes, disk and subprocess time. Fixture-test lying sizes and decompression bombs. Choose numeric defaults from measured fixtures before enabling general inputs. |
| Import failure | A missing/corrupt/unrenderable page stops publication with source locator and reason, preserving the checkpoint. Detection fallback applies only to a successfully imported complete page. All source content must be accounted for before upload. |

Dependency candidates remain those in the [feasibility research](../research/rust-cli-dependencies.md):
`zip`, `image`, `quick-xml`, `clap`, `serde`/`serde_json`, hashing and tempfile
primitives, plus installed Poppler. A sequential
[`reqwest::blocking` client](https://docs.rs/reqwest/latest/reqwest/blocking/)
is sufficient initially. Handle
[`ZipWriter::finish`](https://docs.rs/zip/latest/zip/write/struct.ZipWriter.html#method.finish)
errors explicitly. The saved `openai_probe.py` requests/responses and its linked
official API references establish the observed inference contract. Exact crate versions, features, licenses and
native-tool distribution must be checked and locked during implementation.
Pannello/Kumiko remain AGPL research comparators; do not copy their algorithms or
silently make them shipping dependencies. RAR extraction choice remains open.

## Retry, spending and resumability

Separate quality attempts from transport attempts. A page may use three detector
tiers, multiple scoped quality checks, and at most two qualified geometry repairs.
One optional source-component correction can require another full quality pass
without a generation call; include that fan-out in the same run envelope.
Those are distinct requests with independent identities and reservations; they do
not fit an old two-requests-per-page limit. Put an explicit whole-run request and
spending envelope around this bounded fan-out, with a validated maximum panel
count and output-token cap.

Report conversion economics separately from the shared research ledger. The
ledger includes rejected experiments, policy revalidation and unknown charges;
dividing its total by book length would misstate normal conversion cost. For the
final policy, attribute each distinct required request to the selected run,
including requests reused from earlier experiments. Report estimated cold-cache
cost, actual incremental cost, cache reuse, escalation/repair frequency and
per-page latency separately. Dense irregular pages can require many scoped
checks, so include the slowest pages rather than only the average. Optimize that
cost after quality is established, retaining the same independent defect cases.

The [V30 request audit](../research/v30-request-economics-20261009.md) now prices
the exact saved successful dependency graphs: source 57 needs 134 distinct
requests totaling $4.420136 at the ledger's gross rates, while source 150 needs
21 totaling $0.584057. Their incremental runs cost $1.155186 and $0.451539;
neither is a measured cold conversion. The dense page's two source audits each
took about 4.6 minutes, and 48 Sol ownership checks account for $2.050917.
Retain the separate $0.70 unknown hold on its earlier timed-out detector request.
Per-page request/dollar limits must include repair rechecks and outstanding
concurrent reservations, with explicit stopped/fallback outcomes when exhausted.
These two development pages establish a real expensive tail, not a normal-page
average or shipping service-level promise.

The prototype's native target-check worker count uses only global ledger
headroom (`auto_convert.py`, `Converter.judge`); it can start three workers while
the enclosing page or research suite has room for fewer conservative holds.
The nested reservation guards still enforce every cap, but this mismatch can
stop useful work before earlier requests settle. For example, a retained $1
failure hold inside a $4 page envelope leaves less than $3 after any settled
usage, so three additional simultaneous $1 native holds cannot all fit. This is
a scheduling limitation, not evidence that the guards overspend. Rust should
start with one in-flight request, then admit parallel requests only against the
minimum available headroom of all applicable page, run and global envelopes.
Reserve durably under the shared lock; wait for active requests to settle when
that can free capacity, and stop explicitly when no progress can fit. Never
reduce a hold or renew an envelope to obtain concurrency. Offline acceptance
cases must cover a retained failure hold, a tighter nested cap than the global
cap, concurrent admissions, cached requests at the ceiling, settlement waking a
queued request, and an exhausted envelope with no in-flight work.

The [actual source61 transport recovery](../research/explicit-transient-recovery-20261009.md)
exercises the failure policy separately from segmentation: a structured HTTP503
stopped the original run, one explicitly named recovery received its own durable
reservation, cached successes were reused, and the original $1 hold remained.
After normal quality checks, the same reviewed five-panel candidate was accepted
and played correctly. Preserve this separation of transport identity and quality
policy in Rust; a service retry must not clear a crop warning or reset case limits.

The current prototype stops resumably on transport/account/budget failures. For
Rust, propose one in-flight request initially and at most one transport retry only
for an explicitly classified retryable outcome, within both request and run
budgets. Unknown potentially billed requests retain their holds and stop by
default; recovery requires an explicit bounded policy. Preserve the observed
600-second reasoning-request timeout as research evidence, then qualify the
shipping timeout against the chosen model. Earlier60-second proposals are too
short for several observed valid high-reasoning calls. Honor Retry-After within a
bounded wait policy; never hide retries in the HTTP adapter.

| Outcome | Run behavior |
| --- | --- |
| Valid response | Persist raw response and validated outcome durably, then advance. |
| Known retryable service failure | A proposed transport retry must fit both request and run budgets. Distinguish it from an unknown potentially billed request; the latter stops with its reservation retained. |
| Safety-blocked image | Preserve safety controls; report page fallback without retrying to evade the block. |
| Invalid output/geometry | Preserve it as a failed quality attempt and follow the configured next detector tier. No hidden same-request retry. Confirmed localized clipping may qualify for at most two bounded repairs after tier exhaustion, each independently rechecked. |
| Invalid key/permission/model/request, explicit zero or daily quota | Stop resumably on the first classified hard failure. Make no requests for remaining pages. |
| Long rate-limit delay or repeated outage | Stop resumably rather than classify an entire book as successful fallbacks. Proposed circuit breaker: three consecutive pages exhausted by service errors. |
| Call/token/spending envelope exhausted | Stop before dispatching another request; record pending pages, publish no final book. |

Preflight import/tools/limits/output collisions before the first paid request.
Model listing is not entitlement; the first necessary page request supplies the
access check and its result is retained. A hard failure stops immediately.
Require an explicit finite run call limit and output-token cap. Record every
attempt, including failed calls and missing usage. Token/currency estimates
cannot promise an invoice cap; a hard money limit requires a conservative bound
covering all billed categories and ambiguous failures, or provider enforcement.
If that cannot be established, stop for a concrete budget decision before calls.

A versioned run manifest records source/page hashes, tool versions, render and
analysis settings, endpoint, requested/returned model, prompt/schema version,
direction, attempt IDs, usage/errors, accepted geometry and fallback reasons.
Secrets and auth headers never enter logs or manifests. Persist an attempt intent
before dispatch and its response before deriving an outcome. Verify hashes on
resume; reuse completed matching outcomes and revalidate saved responses locally.
Changed source/model/prompt/render parameters create a new run/cache identity.

An interrupted in-flight request may have been billed without a durable response.
Represent it as **unknown**, retain it in the budget ledger and do not resend it
automatically. There is no exactly-once API-call guarantee. Retrying unknown
attempts requires an explicit bounded policy; completed fallback pages also remain
final unless specifically selected for a new attempt. Fault tests must cover
crashes before dispatch, after response and before checkpoint publication.

## Safe publication and command results

Build in a new private run directory, using a uniquely created temporary CBZ on
the destination filesystem. Finish and sync it; reopen to validate CRCs, every
page hash/reference, frame geometry/order, cover count and retained metadata.
Include a non-active conversion report inside the CBZ so the book and its report
publish as one unit; the resumable run manifest remains outside. Verify that
readers tolerate this extra report in the offline slice.

Only then atomically publish using a **no-replace** operation; an existence check
followed by ordinary overwriting rename is insufficient. A competing creator must
win without either file being overwritten. Test crashes and concurrent collision
on macOS; qualify equivalent semantics before claiming another OS. Keep failed
staging and prior artifacts for diagnosis. No blanket cleanup or overwrite flag.

Proposed command status contract: `0` = all pages published with valid panel or
legitimate whole-page outcomes; `2` = all pages published with reported detection
fallbacks; `1` = no new final book, run failed/stopped and checkpoint retained.
Print artifact/run paths and source-page-specific reasons plus machine-readable
counts. Exit 0 means contract completion, not independently verified model accuracy.
Check final source fingerprints against import snapshots before publication.

## Implementation milestones and acceptance

| Milestone | Deliverable / completion evidence |
| --- | --- |
| A — quality and reader gates | Gates 1/2 recorded, thresholds and remaining product policies discussed. No production migration merely to compensate for a failed detector. |
| B — offline Rust vertical slice | Synthetic folder/CBZ → canonical pages → recorded responses → ACBF CBZ → actual reader. Port seven adapter/eight contract behaviors as meaningful Rust tests, adding non-geometric order, malformed HTTP fixtures, collision/crash publication and source immutability checks. Use red-green tests for new behavior. Validate the actual emitted artifact against pinned XSD/parser and reader; no live calls. |
| C — selected-detector orchestration | Saved OpenAI success/usage records plus recorded or synthetic 503, hard 429, malformed/safety/auth, truncation and unknown-attempt fixtures prove retry, accounting and resume. Preserve model/reasoning/prompt identity and raw/refined geometry. A changed, authorized live probe uses named pages and a finite budget; successful calls become cached evidence. |
| D — input coverage | PDF composition/color/orientation/lettering fixtures; archive attack/CRC/resource fixtures; RAR compatibility matrix; folder order/catalog/single-image cases. Demonstrate clear errors before paid calls for unsupported/unreadable inputs and complete-page preservation for every supported path. |
| E — release candidate | macOS installation from documented prerequisites, real CLI conversion/resume, hosted browser import/navigation at phone dimensions; record actual-phone coverage separately. Native Android is deferred. Test scale offline with saved results first. Live inference follows the selected detector's quality and budget gates; full-book research is authorized under plan 0003 and the subsequently approved shared $100 total cap. Report sustained failures, quality by sampled strata, actual reported usage, unknown charges and limits. |

Preserve pinned XSD/parser sources and synthetic fixtures as acceptance assets.
The existing fixture generator depends on a macOS font; make future fixture input
portable without changing the historical evidence. Keep private books out of Git.
Neither schema tests nor a parser-only test replaces actual reader acceptance.

For implementation covered by the global development rule, use the home-lab skill
and a disposable VM with its own runtime/workspaces; stable installations/data
remain untouched. Select an environment capable of the macOS acceptance checks or
obtain an explicit exception before using a stable Mac as execution backend.
Present the actual staged candidate after end-to-end verification; merge/promotion
requires Chris's explicit approval of that candidate. The separately authorized
web experiment already runs in a disposable VM; this Rust proposal authorizes
neither production implementation nor credential copying.

## Discussion order

Start with the quality rubric/corpus and acceptable failure threshold, then the
web-reader behavior and target phone browsers. Resolve spending/model entitlement only when a live
experiment has a concrete purpose. Settle single-image behavior, ordering/catalog
precedence, CBR coverage and command statuses before their implementation slices.
Ask genuine product decisions one at a time; keep proposed defaults visibly
proposed. Continue the authorized web-reader experiment and discuss this Rust plan; production converter coding remains deferred.
