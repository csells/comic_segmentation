# Detector comparison — 2026-10-08

**Historical checkpoint:** the subsequent [cost/quality comparison](cost-quality-comparison-20261008.md) records Chris’s Astra approval, cheaper OpenAI trials, actual Magi/Western-YOLO trials, build7 and updated budget. Statements below about untested candidates and build6 describe this earlier checkpoint.

OpenAI currently produces the best usable results we have actually inspected on
this book. This is a sample result, not acceptance of all 257 pages or proof that
OpenAI beats every specialist model. Chris explicitly reopened detector selection:
existing software, deterministic methods, local models and OpenAI are all in scope.
The former Gemini-only decision is superseded; the shared $20 cap still applies.

[Nonprivate machine-readable summary](evidence/segmentation-iteration-20261008/detector-comparison-summary.json)
records per-page findings, request fingerprints, source hashes, timing and costs.

## Measured comparison

The difficult pilot uses original PDF pages 5, 25, 254 and 256, rendered as the
same unchanged 1128 × 1648 JPEGs. Expected narrative regions are 7, 6, 4 and one
whole-page splash. Counts alone are insufficient: review considered missing or
merged scenes, false splits, foreground/text coverage and reading order.

| Detector | Actual result | Assessment |
| --- | --- | --- |
| Pannello/Kumiko default heuristic | Previous full-book run; 164 clear failures in 257-page initial overlay triage | Not acceptable. Its seven regions on page 5 did not represent the seven actual scenes. This did not test its optional learned backends. |
| Gemini Flash | Page 25 merges two bottom scenes; page 256 appropriate. Other difficult-page attempts repeatedly failed at the service | Not acceptable as tested. No usable Pro comparison exists; quota/availability failures are not evidence of Pro's quality. |
| Local Qwen3-VL 4B | Semantic prompts and per-scene zooms retain wrong bounds and false splits | Not acceptable as tested. |
| YOLO26n manga panel ONNX | Pilot counts 10/5/3/1; 0.06–0.08 seconds inference per page | Fast, but false splits on 5, merged bottom scenes on 25, missed portrait on 254, cropped splash on 256. All four overlays inspected. |
| OpenComic 512 | Pilot counts 6/3/2/1 | Merges scenes/misses insets on all three panel pages; splash correct. All overlays inspected. |
| OpenComic 1024 | Pilot counts 10/5/7/3; roughly 67–110 seconds/page on software Vulkan | Still merges top/bottom scenes on 25; invents small components on 5/254/256; splits the splash. All overlays inspected. |
| OpenAI gpt-6-astra, prompt v4 | Pilot counts 7/6/4/1 | All four overlays and all 18 ordered regions inspected. Usable pilot, including the previously merged bottom pair on 25. No manual geometry. |
| OpenAI gpt-6-sol, same prompt | Pilot counts 7/6/4/1 | Same scene recovery and usable order/crops on the four-page pilot at substantially lower measured cost. No manual geometry. |

This is a comparison of observed configurations, not an equally tuned benchmark.
Gemini's service failures prevented a complete same-prompt comparison. The local
tools have not been exhaustively tuned. OpenComic and YOLO raw component/detection
indices are not narrative reading order; geometry already failed before ordering
could establish acceptance.

OpenComic was exercised through its upstream API and native inference binary.
The wrapper has a case-sensitive inverted-model name check and inconsistent
component seed/traversal polarity. A separate offline diagnostic extracted
consistently dark connected components from the saved masks, with no new inference
or comic-specific coordinates. Both sizes retained the same component counts;
the 512 diagnostic overlays retained the failures. The 1024 diagnostic is retained
but has not received a separate visual acceptance. Do not call the wrapper fixed
or attribute all failures to model quality alone.

## Broader OpenAI sample

Sol then processed eight new pages with the unchanged v4 prompt and no reference
boxes. All eight overlays and all 46 emitted regions were inspected. Multi-panel
crops were also reviewed in ordered contact sheets; the two full-page crops are
identical to their inspected source composition.

| PDF page | Regions | Visual finding |
| --- | ---: | --- |
| 2 | 1 | Appropriate full-page book description/front matter. |
| 6 | 7 | Main scenes, watch and photograph insets recovered in order. |
| 18 | 6 | Overlapping rescue scenes and reading order recovered; rectangular crops include parts of adjacent insets. |
| 54 | 10 | Nested background, three imagined-life views and bottom sequence recovered. |
| 100 | 5 | All scenes, text and order recovered. Some bounds lie slightly inside the artwork edges, especially the bottom strip. Needs geometry refinement before an excellent-bounds acceptance. |
| 175 | 6 | Regular grid, speech balloons and order recovered. |
| 205 | 10 | Scene inventory recovered, but follow-up inspection found a clipped shared thought balloon. The earlier favorable bounds assessment is superseded by [confirmation and correction](sol-confirmation-20261008.md); high v5 was needed. Rectangular crops necessarily include neighboring inset fragments. |
| 240 | 1 | Appropriate complete credits/introduction composition. |

A targeted Astra comparison on page 100 also recovered all five scenes. Its
bottom edge improved, but some other edges remained slightly inside the artwork.
The overlay and all five crops were inspected. Escalating model size alone does
not establish exact bounds; a general geometry refinement remains open. This
one extra call used the same prompt, no manual boxes, and cost an estimated
$0.076800 in 19.051 seconds. Private run: `openai-astra-v4-page100-20261008`.

Across twelve distinct OpenAI pages, scene inventory/order is promising; do not
turn that into a claim of pixel-perfect bounds or a full-book pass. The remaining
245 pages have no OpenAI result yet. The original 257-page local triage remains
historical evidence, not final acceptance of this new detector.

Rectangles around L-shaped backgrounds or protruding art can legitimately overlap
and show inset fragments. Cropping away a foreground character to avoid overlap
is worse. The four-page manual reference is a provisional evaluation aid, not
unique geometric ground truth: on pages 25 and 254 its visible-only bounds differ
from valid underlying-frame extents. It was never supplied to these models.

## Existing candidates still unproven

- [Magi](https://github.com/ragavsachdeva/magi) explicitly detects panels and
  predicts reading order; it remains a relevant candidate, especially for manga.
  We have not run it. Its much larger runtime/model does not fit this 512 MiB
  disposable guest. Neither lab worker has sufficient unreserved configured
  memory for a heavyweight test guest while preserving its required headroom.
- [Western comic YOLOv12x](https://huggingface.co/mosesb/best-comic-panel-detection)
  is more directly relevant to this anthology than a manga nano model. Its
  author-reported validation score is not a comparison on this PDF. The available
  checkpoint is a PyTorch model and has not been executed here.
- [Pannello](https://github.com/marcopiraccini/pannello) offers optional Magi/YOLO
  paths. Rejecting its default heuristic does not reject these untested paths.

No existing tool tested so far establishes an advantage over Gemini on this book
as a complete solution; individual pages differ. More importantly, OpenAI now
provides a materially better observed starting point than either. Recommend Sol
for the next bounded batches, retaining Astra as a targeted comparison for actual
failures. Continue evaluating specialist alternatives when a suitable isolated
runtime is available. Do not start a production rewrite based on this pilot.

## Reproduction and provenance

Owned probes live in `prototypes/panel_quality_probe/`. Prompt v4, unchanged source
hashes, request fingerprints, raw responses, timings, overlays and crops are retained
under Git-ignored `validation-artifacts/segmentation-iteration-20261008/` and VM153.
Run names are `openai-astra-v4-pilot-20261008`, `openai-sol-v4-pilot-20261008`,
`openai-sol-v4-diverse-20261008`, `yolo26-pilot-20261008`,
`opencomic512-pilot-v3-20261008`, and `opencomic1024-pilot-20261008`.

- [OpenComic code](https://github.com/ollm/opencomic-ai-bin) pin
  `f4d2a82fcd08b31c0796cbe4161da6c1765f0114`; [model repository](https://github.com/ollm/opencomic-ai-models)
  pin `e32481d5c272441908b087cf0a3a3ad9375c6475`. Models are
  `opencomic-ai-panels-fast-512-channels-inverted-259780` and
  `opencomic-ai-panels-fast-big-1024-channels-inverted-custom-arch-v2.1-20000`.
  Wrapper MIT, native backend AGPL, model repository CC-BY-4.0; preserve the separate terms.
- [YOLO26n original](https://huggingface.co/leoxs22/manga-panel-detector-yolo26n)
  revision `40a2854663d537563cfb95c370288a84c6505b9a`;
  [ONNX distribution](https://github.com/xulihang/balloon-dataset/releases/tag/models)
  `manga-panel.zip`, actual model SHA retained in `run.json`. Original card says
  Apache-2.0, export metadata says AGPL-3.0: reconcile before production use.
  ONNX Runtime 1.30.0 CPU, 640-pixel letterbox, RGB float/255, class 0, threshold
  0.25, end-to-end output without a second NMS. No narrative sorting or hand fixes.
- `specialist-reproduction-20261008.tar.gz` retains upstream source/model files,
  hashes, licenses, exact npm lock and transpilation helper outside the VM.
  `build6-review-record-20261008.tar.gz` retains the new catalog, rollback/current
  unit files, published browser screenshots/results and dependency-install logs.

All candidate runtime changes are confined to the disposable VM. Node 20.19.2,
npm 9.2.0, TypeScript 6.0.3, Mesa Vulkan 25.0.7 and ONNX Runtime were added there.
OpenComic used software Vulkan, one thread and bounded systemd jobs, protecting
the reader. Both jobs completed; no inference or temporary browser/server remains
running. Credentials were passed in memory only, never written to the guest.

## Cost and review URL

Seventeen OpenAI calls succeeded with no automatic retries: Astra four-page
estimated usage cost **$0.405050**, Sol same-four **$0.076630**, Sol diverse-eight
**$0.188670**, and one targeted Astra page-100 comparison **$0.076800**. OpenAI total **$0.747150**. Sol was about 5.3× cheaper on the matched
pilot; this small-sample ratio is not a full-book quote. Sequential inference times
were 143.117, 68.893 and 194.397 seconds respectively, excluding preflight/review.

The single shared ledger now holds **$4.354960 of $20**: $0.754960 estimated
reported usage across providers plus $3.60 reserved for twelve earlier Gemini
failed/unknown outcomes. These are conservative estimates, not billing receipts.
There were 31 generation attempts in this iteration: 14 Gemini and 17 OpenAI;
the original checkpoint's earlier ten Gemini calls are separate historical work.
Never reset the ledger or blindly repeat successful/unknown requests.

[Panel Lab](https://csells-mac-mini--51996.getbb.app/) build 6 now offers
**OpenAI · reviewed pilot** first: original cover, then pages 5, 25, 254 and 256.
The automatic Astra metadata is unchanged. The 1,699,011-byte CBZ has SHA-256
`fa6044fb55b4631c44d4b70f4615aa44bd0364caeaa39b7ed402528252b0d98a`.
Twenty-five phone-sized UI checks plus zero uncaught exceptions passed against
both temporary and published staging: cover once, overview before all 17 panel
steps, splash once. Phone-sized gallery and page-25 last-two-panel screenshots
were inspected. This is browser emulation, not a new physical-phone claim.
Previous Gemini/full-book experiments remain available and clearly labeled.

## Remaining quality work

1. Refine the tight edge behavior on page 100 with a general automatic rule or
   targeted model refinement; retain the raw result and evaluate regressions.
2. Expand Sol in bounded batches under the existing ledger; visually inspect every
   final page, crop and reading order. Escalate actual failures, not successful
   requests. Preserve honest per-page acceptance status.
3. Package a new full-book experiment only after that review. The current pilot
   must never be mistaken for a corrected 257-page book.
4. Use measured quality to settle detector choice before the proposed Rust plan.
   Keep detector adapters replaceable; import/preservation/ACBF/reader evidence
   does not depend on selecting Gemini or OpenAI.
