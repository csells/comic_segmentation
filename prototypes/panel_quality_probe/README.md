## Current research prototype: V32 (2026-10-10)

The current entrypoint is [auto_convert.py](auto_convert.py), policy
`automatic-marked-target-completeness-v32`. Acceptance requires a source-bound
completeness proof after the existing quality checks. Every native target check
receives its actual crop plus clean and marked source context; stronger automatic
verification can clear a cheap false alarm. Human reviews assess saved outputs
and control the validation sequence; they do not change runtime flags or geometry.

The frozen candidate passed 281 offline VM checks, all seven injected quality
controls, and actual single-page CLI runs for source pages 1, 56, 6, 57 and 144.
All source/crop bytes and ordered geometry were checked against personal reviews;
the five archives passed 35 browser reading steps. Ten actual-main checks also
verified resume and rejection of changed source, geometry, proof and publication
inputs. These are development results on the supplied PDF, not evidence of
universal comic quality. Sequential prefix, current-policy four-format parity,
remaining historical positives and independent-book validation are still pending.
The prefix subsequently stopped at page5: a correct strong-mapper inventory
correction arrives too late for G's source-audit routing. Its seven proposed crops
passed personal review but the actual outcome is whole-page fallback. Diagnostic
H is being prepared separately; V32 remains frozen and this failure blocks expansion.

Execution stays in the disposable VM, with cache-first bounded inference under
Chris's $100 total cap. Research-source adoption does not promote the candidate:
the stable reader/catalog remain unchanged, and production Rust work has not begun.
Follow the [handoff](../../specs/handoff-comic-panel-cli.md) for current progress
and the [Rust discussion plan](../../specs/plans/0002-quality-gated-rust-cli.md).

[replay_automatic_escalation.py](replay_automatic_escalation.py) is a historical
cache experiment for its archived controller version. It predates mandatory
completeness acceptance and must not run against the current controller. Use the
matching frozen archive to reproduce that historical result; do not add a passing
acceptance callback. Dated checkpoints below preserve earlier results and budgets.

## Historical checkpoint: mask shortlist completed; no qualified repair (2026-10-09)

Chris explicitly approved the second isolated model VM. The
[specialist and semantic-point trials](../../specs/research/specialist-mask-spikes-20261009.md)
and [32-variant seeded-boundary screen](../../specs/research/seeded-boundary-spike-20261009.md)
are complete. ShadowB/Koharu miss scenes on the twelve-page development screen.
SAM box-only and alternate masks merge scenes or omit content. Automatic Astra
ownership points improve several joins, but neither box-plus-points nor the
points-only ablation recovers complete content without regressions. **No tested
configuration was integrated.** Eighteen new coordinate/point/budget checks
passed; those checks do not establish segmentation quality.

Three new point-generation calls cost **$0.577250**. The durable ledger now holds
**$39.009825 of $100 TOTAL**, including unchanged **$4.30 unknown-charge holds**;
**$60.990175 remains**. No completed or unknown paid request was blindly replayed.
The point experiment also enforced its own $2 ceiling. Further paid work needs a
new concrete hypothesis and bounded scope; no permission question remains pending.

V28 stays unchanged: page 57 is a **whole-page fallback**, current qualified
prefix **1–56**, earlier personal review through 150 under prior policies, no
151 request. Do not run acceptance-dependent V25/V26/V28 prefix/matching helpers.
Full 257-page qualification/publication remains unfinished. Reader Build 10 is
active and unchanged; `/healthz` returned HTTP 200. The
[Rust plan](../../specs/plans/0002-quality-gated-rust-cli.md) now separates scene ownership, mask/boundary evidence and
final reading viewports, with concrete advancement gates. It is for discussion;
production implementation and promotion remain unstarted.

The temporary `orca-automation-comic-masks-20261009` VM was gracefully stopped
and deleted after verified export. The unrelated running guest, templates,
VM153, sources, caches and existing books were preserved. No model/API jobs remain.
The specialist report records exact runs, versions, warnings, hashes and limits.

Verified archives under the ignored `validation-artifacts/segmentation-iteration-20261008/`:

- `specialist-masks-20261009/mask-spikes-final-20261009.tgz`: 2,750,795,941 bytes,
  3,453 members; SHA-256 `b6a5789fb8c6a9a4fe7944730cc2062e801c5d6224c29e392bb3a73e246062b5`.
- `seeded-boundary-spike-20261009/final-evidence.tgz`: 42,616,341 bytes,
  309 members; SHA-256 `b765ef0b3ea64dc6b30b8d685e2462bf36e60c4187245f65c8fb69f04070cc65`.
- `semantic-points-cap100-20261009.tgz`: 360,779 bytes, 122 members;
  SHA-256 `c3cd4e369e9fe98b34dde60089267dd3705b7833249c0ddf4270825a28584efa`.

Keep the previous archive chain, especially `preprocessing-controls-cap100-20261009.tgz`.
[Independent-fixture planning](../../specs/research/mask-evaluation-review-20261009.md)
identifies untouched sources and unresolved RTL/book coverage; those fixtures
were not acquired or qualified. Any next candidate needs semantic ownership,
boundary completeness and actual E2E checks separately, before held-out books
or restarting sequential qualification. The completed shortlist is stopped;
more confidence/threshold sweeps alone do not address its observed failure modes.

The dated entries below are history and do not override this checkpoint.

# Historical research-launch checkpoint — 2026-10-09

V28's actual `component-repair-regression-v28-20261009` completed with page 56
accepted and page 57 a **whole-page fallback**. Final marked-detail checks reject
8/10 and accept 9/12; do not claim complete segmentation. The run made 32 new
calls with 190 cache hits. Current qualified prefix is 1–56; prior personal review
reached original page 150, and page 151 has not been dispatched.

Chris approved **$100 TOTAL** after the earlier $40 → $60 increases and explicitly
authorized spikes and tests. Used or held remains **$38.313667**, including $4.30
retained unknown-charge holds, leaving **$61.686333**. The $100 runtime/ledger
amendment is complete in VM153; 25 budget/converter checks passed for this cap-only
change. Converter SHA-256:
`eeb01f352f379bb2be615dd386f0250ad76a4d8213d757d9644374fa32974132`.
The prior V28 suite passed 117 checks. No new paid calls were made during research.

Follow the [current handoff](../../specs/handoff-comic-panel-cli.md) and
[broad research/experiment plan](<../../reports/Robust comic panel segmentation.md>).
The native-PDF audit has started in VM153; no result is claimed yet and new mask
spikes have not run. Continue the authorized spikes and tests, selecting bounded
experiments before new paid work. Older acceptance-dependent
prefix/matching helpers remain unrun and must not be used; the prepared
`/tmp/comic-target-detail-sol-code.txt` also retains the old $40 cap.

Prior verified source/ledger/run checkpoint ($60 state; a $100 checkpoint is
pending after the first native-PDF audit):
`research-cap60-checkpoint-20261009.tgz` (28,442,673 bytes, 421 members), SHA-256
`6896a289ed023bc048af461f5e68018f44495fefb3a41dd073010a2fec038601`.
Retain the previous V28 archive and earlier evidence chain. Reader Build 10 is
unchanged and active; no production rewrite or promotion has begun.

The dated entries below are historical. Their running-job, cap, and continuation
statements are superseded by this checkpoint.

### Historical V28 component-edge launch snapshot (2026-10-09)

117 tests pass inVM153. After at most two model repairs, the candidate permits
one source-pixel expansion for unresolved machine-confirmed clipping only. Every
flagged target must have one qualifying mostly enclosed color component; only
those boxes and missing edges change. All quality checks run again. The broad
refinement changed56/150pages offline and was therefore not enabled by default.
V28 also avoids redundant verifier calls after an intermediate candidate is
already rejected. Final-tier quality checks remain complete. Actual56/57 E2E is
running; full-book acceptance remains unestablished. Shared cap$40 total.

### V26 bounded repair and source-boundary context (2026-10-09)

111 tests pass in VM153. The current candidate allows at most two machine-directed
clipping repairs after three detector tiers, preserving inventory/order and all
unflagged boxes. No-change repairs stop. Only unresolved findings can feed the
next repair; all quality checks run again. A final repaired target's localized
clipping warning receives source-detail context with the exact crop boundary,
while global/structural failures stay binding. The marked-detail diagnostic passed
four development controls; its unmarked predecessor failed and was rejected.
Actual56/57 regression is running. Full-book qualification remains unfinished.
The shared cap is $40 total, with unknown charge reservations retained.

### V24 bounded clipping repair (2026-10-09)

After three failed detector tiers, allow at most one verifier-directed expansion
for confirmed clipping only. Preserve inventory/order and unflagged rectangles;
reject shrinking and rerun all quality checks. Actual17/18 E2E passes, with all six
page18 final crops personally inspected and byte-matched.103tests pass inVM153.
Prior-prefix revalidation is running; full257-page qualification remains unfinished.
The cap remains $40 TOTAL, including retained unknown holds.

### V23 crossing-artwork escalation (2026-10-09)

The shared authorized cap is $40 total. V23 adds source-only layout-risk screening
for partial overlaps and mandatory Astra target audits for uncertain crossing
artwork. At the final tier, required full-candidate verification also uses Astra;
all independent gates remain binding. Unchanged generic prompts produce correct
page150 crops through actual E2E;96tests pass. Earlier-prefix revalidation is in
progress. This is anthology development evidence, not held-out qualification.
See `specs/research/full-pdf-sequential-review-20261008.md` for current status.

# Panel quality research probe

Current continuation: [full-PDF sequential review](../../specs/research/full-pdf-sequential-review-20261008.md).
The historical experiments below are not the current whole-book result. The
integrated `auto_convert.py` imports PDF/CBZ/CBR/image folders, uses generic
prompt-v6 with automatic Sol-low → Sol-high → Astra escalation, then produces
CBZ/ACBF. `--max-new-pages 1` checkpoints before the next page; personal inspection
is development validation outside the runtime. The full 257-page task is ongoing.

Current V21 preserves V20's segmentation policy and raises the shared API cap to
$40 at Chris's explicit instruction.90 tests pass. The intact144portrait and both
negative clipping controls now behave correctly. Full1–144 cached revalidation
under the new run identity precedes continued sequential review145–257. Detector
prompt-v6 is unchanged; no manual runtime geometry or page-specific instructions.

Candidate V18 adds a source-only count-conservation guard when stronger detection
reduces the largest earlier inventory. Full-page context disambiguates flagged
regions; existing overlapping insets count separately. It catches the missed
page144 merge in frozen controls; actual E2E regression is pending.82 tests pass.
This is an extra routing signal, not proof of scene identity. See the continuation
for rejected prompt variants, model sensitivity and current budget.

V17 retains the original cheap source-continuity predicate. A positive warning
at the final Astra tier receives independent source-only Sol-high adjudication;
only a valid distinct-view verdict clears that pair warning. Uncertainty retains
it, and every downstream quality check still applies. This replaced v16's second
Luna predicate after correlated false positives caused a fallback on111. The
stronger diagnostic passed13/13 frozen regions (4 continuous,9 distinct), and
actual source111 now passes all checks and personal review. Full prefix
revalidation is ongoing.74 tests pass. Native false negatives can still escape
because stronger adjudication only sees flagged cases; broader validation remains
unfinished. A global prompt replacement (v15) was rejected for a false alarm on5.

V14 adds conservative expansion for disconnected foreground marks near inset
panels on black gutters. Page 101's formerly clipped rain streaks now pass actual
automatic processing and personal inspection; prefix revalidation is ongoing.
V13 framed-ink and V12 enclosed-lettered-balloon expansion remain active. All
corrections only expand boxes and still undergo every automatic quality check.
Prompts remain generic prompt-v6. 69 relevant tests pass in the disposable VM;
full-book and generalization claims remain unproven.

V9 retains v8 quality routing and adds operational timeout recovery. By default,
an unknown paid request stops. `--retry-unknown SHA256` explicitly permits one
separately reserved attempt only for that recorded timeout; the original hold is
never released. Successful requests reuse cached responses, including a successful
recovery. A second unknown attempt stops permanently under this option; quota or
other errors cannot use it. Responses requests now wait up to 600 seconds, with
start/completion logs. The recovery ID records its original fingerprint, and the
same $20 ledger caps both attempts. This changes no geometry, prompt or quality
selection. Use a new output directory after any runtime-source change; run identity
includes all detection, routing and import dependencies. 54 offline tests pass. The rejected hidden-gutter v10/v11 experiment is retained
under `experiments/hidden_gutter_v11/`; it is not integrated. Its initial page61
merge label was withdrawn after closer source inspection showed a continuous
conversation view. See the sequential review for the correction and backups.


Latest integration: [actual automatic input-to-reader conversion](../../specs/research/automatic-conversion-e2e-20261008.md). `auto_convert.py` handles PDF, CBZ and image folders through live/cached providers, bounded escalation and CBZ/ACBF publication. CBR extraction is implemented but not fixture-qualified. The17-page run completed with52 new calls;42 tests pass. Build10 serves its generated output. Chris subsequently explicitly authorized the entire PDF, sequentially with personal review, under the shared $20 cap. Older totals and replay-only statements below are historical.

Latest work: [automatic escalation optimization](../../specs/research/automatic-escalation-optimization-20261008.md).
The target-specific Decisions experiment reduces false escalations from10/12 to2/12;
it still misses the raw page100 edge defect. Combine real gutter refinement with
cheap checks and scoped stronger verification. The research controller replay
selects the accepted output for12/12 development pages without runtime labels or
human routing. This is cached development evidence, not live/held-out qualification.

`automatic_escalation.py` owns bounded routing; `replay_automatic_escalation.py`
exercises real refinement plus exact cached providers. `decisions_probe.py` keeps
all variants separately identifiable; target v3 uses original+one crop. The generic
Responses judge is now exercised for global and target verifier comparisons; its
global crop-coverage verdict failed both bad controls and must not override target
warnings. Target-only Sol-high verification is more useful but also misses raw100.

Run candidate checks only inside the disposable VM, using the geometry venv:
`python3 -m unittest test_automatic_escalation test_decisions_probe test_escalation_probe test_budget test_stream test_interactions test_openai_probe test_gutter_refine -v`
All37 passed. Optimization added$0.177201; shared used/held$4.780991 of$20, including
$3.60 old unknown holds. Preserve results and reuse the single existing ledger.
The reader is unchanged. Figures below are historical snapshots.

These are research probes for local models, Gemini, OpenAI and specialist panel
detectors, not production implementations. Chris explicitly authorized comparison
and reopened detector selection on 2026-10-08.
[Current confirmation](../../specs/research/sol-confirmation-20261008.md) records
actual results, private evidence and outstanding bounds/full-book work. OpenAI is
the strongest tested candidate so far; no whole-book acceptance exists.

Run candidate code only inside a disposable VM. Discover the supported shared
Ollama endpoint and capacity from the home-lab registry first. The local probe never
downloads models, changes services, sends paid API requests or edits source images.
It processes one to eight selected pages sequentially with no automatic retries,
and refuses an existing output directory. Failure stops the run. Preserve unknown
outcomes instead of silently repeating them. Prompt, options, source hash, raw
NDJSON and timings are saved before/after each request. Keep private images and
responses out of Git.

Copy this directory and sibling `gemini_panel_probe/` to the VM; the latter supplies
only the existing structural contract. Python standard library handles inference;
Pillow is used only for diagnostic rendering. The local probe needs no API credentials.

```sh
python3 source/panel_quality_probe/ollama_probe.py \
  --endpoint "$REGISTERED_OLLAMA_ENDPOINT" \
  --images replay-local/pages --pages 25,254,5 \
  --prompt source/panel_quality_probe/prompt-v3.txt \
  --named-bounds --allow-json-in-thinking --output evidence/unique-run
python3 source/panel_quality_probe/render_probe.py \
  evidence/unique-run replay-local/pages
```

Review every emitted `review/page-NNNN.jpg` overlay and relevant ordered panel
crops. Structural validation is not a quality pass. Named bounds are converted
deterministically to the existing `[ymin,xmin,ymax,xmax]` contract; no per-page
coordinates or human corrections enter inference. `--allow-json-in-thinking` is
an explicit diagnostic workaround for the observed installed-model response
field quirk; default behavior rejects missing final content. It accepts only a
complete JSON object, not geometry extracted from reasoning text.

The probe uses the documented [Ollama chat API](https://docs.ollama.com/api/chat)
and [base64 image input](https://docs.ollama.com/capabilities/vision). Actual model
and version observations, including the response-field defect, take precedence
over assuming documentation establishes behavior. The Gemini research runner below has a separate cost and credential contract.


## Bounded Gemini probe

`gemini_probe.py` accepts a key only on stdin, checks input tokens before
inference, and reserves cost in one locked, fsynced JSONL ledger shared by all
runs and model/prompt changes. Copy this directory and sibling
`gemini_panel_probe/` into the disposable VM; run the candidate there. The key
must be piped from the authorized vault in memory, never passed on the command
line or written to the guest. Preserve all private outputs outside Git.

Chris approved a **$20 total cap** on 2026-10-08. The existing ledger's name
still contains `10usd`; its explicit cap-amendment event records the increase.
**Reuse that ledger; do not create a fresh allowance.** The runner refuses a
mismatched cap, duplicate request, existing output directory or expired pricing
policy. Successful fingerprints reuse saved panels. Failed/unknown outcomes
stop the batch. `--retry-transient` allows one explicitly requested retry after
a received HTTP 500/502/503/504; never a timeout, quota failure, or success.

Current checkpoint: **14 generation attempts, 2 responses, 12 failed/unknown**;
one separate 2.5 Pro token-preflight 404 sent no generation. Estimated cost from
reported usage is $0.007810; $3.60 remains reserved for missing usage. Total
used/held: **$3.607810**. This is conservative accounting, not a billing receipt.
Do not treat failed HTTP responses as free without evidence.
[Nonprivate request summary](../../specs/research/evidence/segmentation-iteration-20261008/gemini-pilot-summary.json).

The page-25 response still merges two bottom panels; page 256 is an appropriate
whole-page splash. Both overlays and ordered crops were inspected. No new output
replaced reader metadata. Flash 3.8/3.7 repeatedly returned 503 through both
GenerateContent and Interactions; 3.6 returned 429. Earlier 3.1 Pro had zero
quota and was not retried. Working Gemini access is needed before scaling.

Prompt v4 asks for a semantic inventory of camera views before geometry, including
border-breaking foreground and inset scenes. `--proposals` accepts unchanged
prior model outputs only when their source-image hash matches, and labels them
fallible evidence. It is not a hand-annotation path. The comparison has no usable
response yet. `--high-detail` is a separate experiment with high reasoning/image
resolution; its single timed-out attempt has an unknown outcome and must not be
silently replayed.

`--stream` preserves SSE events for GenerateContent. `--interactions` tests stable
v1 with `store:false`, no tools, medium thinking and an 8192 output cap. The live
v1 API rejected a bare image/text content array despite the documented union;
wrapping it in a `user_input` step reached inference (then 503). Keep that failure
as contract evidence. Interactions ignores the legacy config in `run.json`:
its actual configuration is the explicit stateless body constructed in the
runner. Future records include `interaction_config`; historical runs are retained
unchanged. All transport/model changes have distinct fingerprints and share cost
reservations. Interactions is an availability experiment, not a validated adapter.

Run the ten offline tests inside the candidate VM:

```sh
cd source/panel_quality_probe
python3 -m unittest test_budget test_stream test_interactions -v
```

Prices and API contracts verified 2026-10-08:
[pricing](https://ai.google.dev/gemini-api/docs/pricing),
[GenerateContent](https://ai.google.dev/api/generate-content),
[Interactions v1](https://ai.google.dev/api/interactions-api-v1).
Flash 3.6/3.7/3.8 standard rates are $0.75/M input and $3.75/M output including
thinking through 2026-12-31. The $0.30 reservation covers 20,000 input tokens plus
the full 65,536 model output limit. Different model rates are stored with each
reservation. The runner fails closed after the price-policy expiry.

## OpenAI comparison and geometry diagnostics

`openai_probe.py` is offline by default. Live execution uses `--execute-approved-comparison`; Chris explicitly approved
OpenAI uploads/comparison on 2026-10-08. Forty requests have now succeeded. It shares the
existing budget ledger with Gemini, preflights input tokens and caps output at
8192 tokens. A gpt-6-astra page reserves $0.70; no automatic retries. Keys arrive
on stdin only. Preserve raw responses before parsing and stop on refusals,
incomplete responses or unknown outcomes. Actual request compatibility is verified; visual quality is recorded separately
from structural success. The shared ledger now holds $4.594361 of $20; the Gemini
amount above is its historical subtotal, not current remaining allowance.

Official contracts checked 2026-10-08:
[model](https://developers.openai.com/api/docs/models/gpt-6-astra),
[vision](https://developers.openai.com/api/docs/guides/images-vision),
[structured output](https://developers.openai.com/api/docs/guides/structured-outputs),
[token counting](https://developers.openai.com/api/docs/guides/token-counting).

Run all thirteen offline tests in the VM with
`python3 -m unittest test_budget test_stream test_interactions test_openai_probe -v`.

`refine_local.py` explores per-scene zooms from unchanged local-model proposals.
`border_candidates.py` explores image edges and parallel lines. Neither produced
an acceptable pilot detector; see the measured report. Candidate-only dependencies
are installed in `geometry-venv` in VM153. Private hand-annotated reference boxes
are evaluation targets, never inference inputs or replacement detector output.


## Specialist probes and reviewed reader sample

`opencomic_probe.mjs` runs the pinned upstream OpenComic API with software Vulkan
inside the disposable VM. `render_opencomic.py` scales its raw component boxes;
component indices do not imply reading order. `opencomic_mask_components.py`
examines saved masks offline without another inference call. Both 512 and 1024
original outputs failed visual acceptance; retained diagnostic output is not a
production fix.

`yolo_onnx_probe.py` runs the pinned YOLO26n panel export using ONNX Runtime CPU,
640-pixel letterboxing, class 0 and confidence 0.25. Raw model arrays, metadata,
source/model hashes and overlays are retained. Its pilot also failed geometry.
Model archives, licenses and installation locks live in ignored evidence; do not
execute arbitrary downloaded PyTorch checkpoints to reproduce this ONNX probe.

`package_pilot.py` packages saved OpenAI results and the original cover via
the existing ACBF adapter. It verifies source hashes, preserves image bytes and
never changes boxes or calls inference. The default title/output name refer
to Astra; `--title` and `--filename` label each separate Sol experiment. The reader's `check_openai_pilot.py` verifies actual
page-first navigation through those unchanged results in phone-sized Chromium.


## Cheaper models and larger specialists

`openai_probe.py` supports gpt-6-luna and gpt-5.6-luna prices plus explicit
`--reasoning low` (default high). Reasoning is part of the saved configuration and
request fingerprint. Four-page trials found Sol low usable, while both Luna
configurations failed visual acceptance. Pricing reservations remain conservative;
all variants share the same ledger. Do not repeat a saved run to obtain examples.

`specialist_torch_probe.py` runs pinned Magi or Western YOLO checkpoints in a
separate adequately sized disposable guest. It saves source/model hashes, raw
outputs, LTR ordered indices, overlays, crops and timings. Magi uses recommended
grayscale preprocessing; OCR is disabled, detector checkpoint loading is asserted.
`--magi-iou-nms` records an explicit postprocessing experiment; `--image-size 1280`
records a separate YOLO resolution trial. All four configurations failed the
pilot. The downloaded source, weights, license records and dependency freeze were
exported before the research guest was deleted. Consult the report and fresh lab
registry before reproducing; the existing reader guest is too small for Torch.

Official price references checked 2026-10-08:
[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
The conservative runner rates include cache-write input rates ($0.125/M and
$0.25/M) and output including reasoning ($0.50/M and $1.20/M respectively).
No Batch/Flex discount was tested. GPT-5 nano is deprecated and was not selected.

## Sol confirmation and conservative refinement

Low v4 is the first-pass research default after twelve reviewed pages. Prompt v5
adds a general boundary audit; low v5 failed to fix the two selected pages, so
v5 is not a global replacement. High v5 recovered a shared balloon and collar on
page 205. That escalation was selected through developer review; no automatic
quality detector is validated. See the current confirmation report for limits.

`gutter_refine.py` consumes saved results, verifies source hashes and writes a
fresh output directory. Version 2 expands only a unique, near-matching foreground
component on a uniformly dark background. It never shrinks boxes or changes
scene count/order. Its `refinement.json` records original panel hashes and pixel
changes. Reused generation usage in output records is not another API charge.
Of twelve tested pages, only page 100 changed; all five expanded crops were
visually inspected. Candidate-only dependencies: Pillow, NumPy and OpenCV.

```sh
geometry-venv/bin/python source/panel_quality_probe/gutter_refine.py \
  evidence/saved-run replay-local/pages evidence/new-refined-run
geometry-venv/bin/python source/panel_quality_probe/render_probe.py \
  evidence/new-refined-run replay-local/pages
geometry-venv/bin/python source/panel_quality_probe/contact_sheets.py \
  evidence/new-refined-run/review
cd source/panel_quality_probe
../../geometry-venv/bin/python -m unittest test_gutter_refine -v
```

All six refinement tests passed in VM153, including an observed failing test
before the thin-panel correction. `contact_sheets.py` creates ordered diagnostic
crops without changing detection or source images. Review originals/overlays too;
a contact sheet alone can hide a missed scene or insufficient source boundary.
