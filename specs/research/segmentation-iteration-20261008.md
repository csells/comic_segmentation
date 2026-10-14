# Segmentation iteration — 2026-10-08

Current continuation: Chris authorized OpenAI and existing specialist comparisons. [Measured detector comparison](detector-comparison-20261008.md) supersedes the pending-approval/provider statements below. OpenAI pilot is live in build 6; seventeen successful calls, shared used/held $4.354960 of $20. Full-book quality remains incomplete.

**Detection is still rejected.** Chris reported missing segmentation, merged or
skipped panels, and incorrect dimensions throughout the supplied PDF. He asked
for agent visual review of every page and an entire-page overview before each
page's ordered panels. The reader change is published; detector work is incomplete.
No new paid API calls, manual panel corrections, or Rust rewrite occurred.

## Reader result

Panel Lab build 5 shows overview → panels in metadata order → next overview.
Covers and full-page fallbacks appear once. Ordinary refresh is required for an
already-open tab. Six parser cases, seventeen synthetic UI checks and sixteen
published real-book UI checks pass. See [reader evidence](web-reader-validation.md).
These checks verify navigation, not the quality of the stored panel regions.

## Every-page baseline review

The agent inspected numbered overlays of **all 257 PDF pages**, four pages per
sheet, generated from the original local detector's 1,094 recorded frames and
the recovered source PDF. The [per-page ledger](evidence/segmentation-iteration-20261008/visual-review.md)
records each observation:

| Initial assessment | Pages |
| --- | ---: |
| Clear detection/classification failure | 164 |
| Appropriate whole-page composition | 21 |
| Needs closer inspection | 72 |

This is initial triage. It is not a full-resolution acceptance pass, a measured
panel precision/recall score, or proof that the remaining 93 pages are correct.
Previously reported fallback counts cannot substitute for quality measurement.

Repeated failures include inset panels merged with their parents, grid cuts
through windows/cage bars, cropped artwork and captions, incorrect order among
overlapping panels, omitted final panels, and false cuts through single splash
images. Pages 254–255 collapse narrative insets into whole pages; page 256 does
the opposite, splitting a single continuous room scene into three arbitrary parts.
Page 233 omits the last wide panel entirely. These are detector failures; changing
the reader alone cannot repair them.

## Bounded local comparison

While the Gemini spending-cap question was pending, six sequential requests
tested the existing shared `qwen3-vl:4b` model through Ollama 0.33.1. No model was
installed or replaced. The model digest observed in the service catalog was
`1343d82ebee38e26a4dd6b0180b915eb91550184e67c505dea97509571c8f683`.
Candidate code, image loading, request construction and evidence stayed in the
disposable VM. The home-lab skill explicitly permits using existing shared model
services through supported interfaces. Gemini remains the proposed v1 provider;
this comparison does not change that decision.

The [probe](../../prototypes/panel_quality_probe/README.md) used existing source
renders, temperature 0, seed 7, 16,384-token context, at most 4,096 output tokens,
and no automatic retries. Prompt v2 emphasizes narrative insets, independent
overlapping bounds, whole-page classification and complete artwork. Prompt v3
replaces the ambiguous coordinate array with named bounds and asks for a scene
description before geometry.

| Request | Prompt | PDF page | Returned regions | Visual result |
| --- | --- | ---: | ---: | --- |
| 1 | v2 | 25 | 6 | Rejected: axes appear transposed; boxes divide two-column art into three columns. |
| 2 | v2 | 254 | 4 | Rejected: same coordinate confusion, wrong bounds. |
| 3 | v2 | 256 | 1 | Whole-page classification and bounds match the single splash. |
| 4 | v3 | 25 | 6 | Rejected: axis issue resolved, but equal grid cuts crop panels 2/4 and omit protruding art. |
| 5 | v3 | 254 | 4 | Rejected: insets recognized, but their boundaries are inaccurate; surrounding/overlapping art is mishandled. |
| 6 | v3 | 5 | 8 | Rejected: large first scene cropped, inset bounds cut artwork/caption, lower scene split falsely. |

The [request summary](evidence/segmentation-iteration-20261008/local-pilot-summary.json)
records prompt hashes, individual visual decisions, 13,848 input tokens and
2,231 output tokens across the six local calls.

Every returned overlay was inspected at source resolution. A correct count did
not pass a page. The local comparison was not expanded to the full book and no
new result replaced the hosted book's metadata.

The installed model returned its complete schema-constrained JSON in the
`thinking` response field despite `think:false`. Request 1 stopped the runner
because final `content` was empty. A separate offline parse recovered that exact
JSON without another request; later requests explicitly enabled that diagnostic
compatibility path. It accepts only complete JSON, never extracts boxes from
reasoning prose. This quirk is recorded, not a production API compatibility claim.

## Budgeted Gemini iteration

Chris first approved $10, then increased the total cap to **$20** and requested
continued iteration until the results are excellent. The durable reservation
ledger now enforces that cap across models, prompts, retries and restarts. Its
historical filename remains `gemini-10usd-20261008.jsonl`; an explicit amendment
preserves the approval history. Never start a second allowance for this work.

[Per-request evidence](evidence/segmentation-iteration-20261008/gemini-pilot-summary.json)
records **14 generation attempts** on 2026-10-08: two usable responses, nine
HTTP 503 failures, one HTTP 429, one HTTP 400 and one timeout with unknown outcome.
A separate 2.5 Pro token-preflight returned 404 (unavailable to new users), so no
2.5 Pro generation was sent. Historical probes from 2026-10-07 are separate.

| Experiment | Result and visual assessment |
| --- | --- |
| Flash 3.8, v3, page 5 plus one retry | Two 503 responses; no geometry to review. |
| Flash 3.7, v3, page 5 | 503; no geometry. |
| Flash 3.8, v3, pages 256/25/254 | 256 is an appropriate whole-page splash; 25 still merges its last two scenes; 254 returned 503. |
| Flash 3.8, v4, high reasoning/resolution, page 25 | Read timeout at 180 seconds; unknown outcome retained, not replayed. |
| Flash 3.8, v4 plus unchanged model proposals, streaming, page 25 and one retry | Two 503 responses; proposed geometry comparison remains untested. |
| Interactions v1, v4/proposals, page 25 | 3.7 first rejected bare content input with 400; corrected `user_input` wrapper reached inference but 3.7 and 3.8 returned 503; 3.6 returned 429. |

Both successful overlays and their ordered crops were personally inspected at
source resolution. On page 25, the fifth crop contains two distinct narrative
views; the final scene has no separate reading step. This is a rejected result,
not a mostly-correct page accepted by its count. The single-scene page 256 passes
that pilot check. No new metadata was published. The four-page pilot and full-book
acceptance remain incomplete.

The two reported usage records imply **$0.007810** at standard list rates.
Twelve requests lack reported usage and retain **$3.60** in reservations:
**$3.607810 used/held of $20**. These are conservative allowances, not confirmed
billing. Rates were checked against [Google's pricing](https://ai.google.dev/gemini-api/docs/pricing).
Thirteen offline budget/replay/stream/Interactions/OpenAI tests pass in the disposable VM.

The project has a real availability/access blocker. Both supported transports
returned repeated overload responses, and alternate model access hit quota/model
availability errors. Dashlane contains only the known working key and the older
invalid key. No signed-in gcloud account was available to inspect billing; no
billing/project settings changed. Chris has been asked for working 3.1 Pro access
on the existing project or the name of another enabled Gemini key in Dashlane.
Do not repeatedly retry zero quota or burn the allowance on blind 503 loops.
The automatic approval review initially questioned upload permission; the
user-adopted handoff's explicit Google page-upload authorization resolved it.

## Continued geometry work and prepared provider comparison

A delayed, explicitly bounded 3.8 Interactions retry on page 25 returned HTTP 503
in 13.862 seconds. Its raw result is retained as
`gemini38-v4-interactions-recovery-20261008`; no new successful Gemini output.

Three additional local calls zoomed into unchanged model proposals for page 25,
orders 2, 5 and 6. Source hashes were checked, each proposal was expanded by 50%
on each side, and returned crop coordinates were mapped back without manual
correction. The assembled full-resolution overlay was inspected and rejected:
the foreground horse is clipped and neighboring content remains in the bounds.
These calls used 3,639 input and 154 output tokens on the existing shared service.
There are now nine local diagnostic calls, not a full-book local rerun.

An offline border-candidate experiment ran in the disposable VM using isolated
NumPy 2.5.3, OpenCV-headless 5.0.0.93 and Pillow 12.3.0. Initial closed-contour
extraction found no boxes on the four pilots. A Hough-line version first failed
on the OpenCV 5 array shape; the repaired run produced excessive false boxes.
Adding edge-coverage filtering left 253/22/6/57 candidates on pages 5/25/254/256.
Inspected page-25 and page-254 overlays still missed scenes and included objects
or lettering. These are diagnostic candidates, never accepted panel metadata.
All run directories, including failed attempts, remain preserved.

A private evaluation reference now records 18 manually annotated rectangles
across pages 5/25/254/256 (7/6/4/1). All four overlays and all crops were visually
checked against source-resolution pages. Overlap is intentional for L-shaped
backgrounds, overlapping portrait insets and the horse breaking a frame. This
reference is an evaluation target only, not an automatic detector result, and
must remain separate from inference inputs. It does not establish generality
or acceptance of the remaining 253 pages.

`openai_probe.py` is prepared for a four-page comparison. An existing project key
passed only a read-only model-list request. No comic page was uploaded to OpenAI
and no generation was sent. Its offline preparation completed in the candidate
VM and three adapter tests passed alongside the ten existing runner tests.
The runner uses source/request hashes, strict structured output, original-detail
images, high reasoning, no storage, input-token preflight, an 8192 output cap,
and the existing shared budget ledger. A gpt-6-astra pilot reserves up to $0.70
per page ($2.80 total); rates conservatively include possible input cache-write
premium. Actual endpoint compatibility and quality remain untested.

Chris was asked specifically whether those four pages may be sent to OpenAI.
This answer remains pending because the settled provider decision authorized
Google uploads and deferred other providers. The $20 cap is already authorized
and is not being requested again. No billing settings were changed.

## Remaining validation

Resume the difficult-page pilot (5,25,254,256) when working access is established.
Reuse all successful saved responses and investigate unknown outcomes before any
retry. Evaluate each new overlay and crop against the original, then expand the
successful approach and review **every resulting page**, including panel bounds
and sequence. No hand-edited geometry may be represented as detector success.
The $20 authorization persists; do not ask for it again. Production Rust work is
still deferred behind the quality gate.

Private source, overlays, panel crops, raw responses, prompt snapshots and source
hashes are retained outside Git under
`validation-artifacts/segmentation-iteration-20261008/` and the disposable VM's
`comic-reader/evidence/` directory. All new Gemini runs, proposal records and the
shared ledger were copied back to the Mac. The original whole-book overlay sheets
remain under `validation-artifacts/local-review-20261008/`. Earlier artifacts and
hosted books are unchanged.
