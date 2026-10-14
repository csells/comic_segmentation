# Automatic conversion through the reader — 2026-10-08

The research prototype now converts an actual input through detection, automatic
quality checks/escalation, portable CBZ/ACBF output and the staged phone reader.
The previous 12-page controller replay did not establish that integration.

## Executed sample

Original PDF source pages **1,2,5,6,18,25,26,27,54,100,101,175,205,206,240,254,256**.
The cover and pages26,27,101,206 required fresh first-pass detection. The converter
made52 new paid requests:6 detector,43 native Decisions and3 scoped verifier calls.
It reused101 exact cached requests. No runtime evaluation labels, case catalog,
manual box changes or human routing decisions were used.

All17 pages reached the policy's accepted state. Source pages26 and205 escalated
from Sol-low-v4 to Sol-high-v5;26 exercised a fresh live escalation,205 reused exact
prior high/quality requests. Dark-gutter refinement changed100 and101. The output
contains the cover,16 body pages and92 guided panel steps. Whole pages precede
panels in the reader; whole-page compositions are not duplicated. No page required
the terminal whole-page fallback. These are automated outcomes, not independent
proof that every panel is correct. Fresh pages were not manually certified.

The live analysis took122.39 seconds after input preparation. Added usage estimate
**$0.172592**; shared used/held total **$4.953583 of $20**, including unchanged$3.60
unknown Gemini reservations. Input rendering used the previously verified150dpi
cache, checking original PDF and all rendered page hashes. Only the17 selected
pages were sent for inference or published.

## Reproduction and safety

`prototypes/panel_quality_probe/auto_convert.py` owns the integrated adapter.
Run in disposable staging with key on stdin, existing shared ledger, source PDF,
new output directory, `--render-cache`, the selected `--pages`, and
`--execute-approved`. Never put a key in arguments, environment or saved files.
Use the existing Dashlane launcher rather than creating another credential copy.
Do not change the shared ledger or repeat requests with unknown outcomes.

Each completed page is checkpointed. Request identities include the exact payload;
completed responses are reused, unknown dispatched attempts stop. Reservations
precede paid requests; budget/account/schema failures stop resumably. The finite
quality policy can escalate through high Sol and Astra, then retain an explicit
whole-page fallback. Incomplete input preparation without a completed manifest
refuses to overwrite existing evidence; use a new output directory. This remains
research code, not the production Rust implementation.

CBZ-to-CBZ and image-folder-to-CBZ runs each completed all17 pages with153 cache
hits and zero new calls; the folder test disabled HTTP dispatch entirely. All17
source image bytes were preserved. A final safety change was tested with42 passing
unit checks and a second PDF conversion with HTTP disabled. Archive contents match
the live run except the intentionally new ACBF document UUID. CBR extraction is
implemented using libarchive-c5.3/libarchive3.7.4, but a real RAR fixture has not yet
qualified that path. Do not advertise CBR as validated.

## Reader and retained evidence

Build10 adds **Automatic panels · end-to-end sample** to the existing gallery;
all six previous books and application assets are preserved. Prepared and served
reader checks use390x844 and traverse every page/panel:112 assertions and zero
browser exceptions passed in each run. The relay delivered the exact generated
CBZ, verified by SHA-256. Results and private
screenshots live under `automatic-e2e-reader-*` in the retained archive. The first
attempt used a stale remote four-page test; syncing the already generalized test
fixed the harness, with no application or book changes.

Private evidence is retained under ignored
`validation-artifacts/segmentation-iteration-20261008/automatic-e2e-20261008.tgz`:
live requests/responses, page routing traces, four conversion runs, CBZs, source
snapshots, reader checks, rollback unit and the latest budget ledger. Source PDF
and earlier request caches remain in their existing retained locations. Public
review: https://csells-mac-mini--51996.getbb.app/ (owner authentication required).
The retained archive SHA-256 is
`fac7766c49838932aa699e9f68099acecf8e05146058a0370cd2a8b9a35cd126`,
verified equal on the VM and separate Mac. Temporary browser9222 and preview8081
are stopped; only the existing review service8080 remains.

## Remaining qualification and authorization

This establishes bounded input-to-reader integration, not full-book quality.
Optimize/calibrate the policy against independently annotated defect cases,
especially missed panels, merges, reading order, subtle edge cuts and shared text.
Known raw100 edge misses remain a judge limitation addressed by the refiner, not
proof of a reliable learned crop detector. No production rewrite/promotion.

Automatic approval review rejected the proposed entire257-page private-PDF upload
before execution: it interpreted prior permission as bounded validation and
required explicit authorization for newly expanded full-book egress. The approved
17-page run above completed instead. Obtain explicit permission before processing
the whole book, retaining the existing$20 total cap and request cache. Do not infer
that elapsed time, the existing budget, or this sample's success grants approval.
