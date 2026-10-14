# Cost and quality comparison — 2026-10-08

**Follow-up:** the [eight-page confirmation](sol-confirmation-20261008.md) is now
complete. It selects Sol low as the first-pass research default with explicit
boundary-refinement/escalation limits. The pilot figures below remain historical.

**Sol with low reasoning is the cheapest tested configuration that preserved the
approved pilot's scene inventory, reading order and usable crops.** Chris reported
no errors in the published Astra pilot and requested cheaper OpenAI and specialist
comparisons. This report records that follow-up; the earlier
[detector comparison](detector-comparison-20261008.md) remains historical evidence.
Four difficult pages are a screening set, not proof of whole-book reliability.

**Accounting correction:** subsequent [judge-prototype preparation](escalation-judge-prototype-20261008.md)
found premature fractional-rate rounding. Corrected four-page costs are $0.006279
for GPT-6 Luna and $0.018659 for GPT-5.6 Luna. Original estimates remain in the
historical table below; quality conclusions and Sol/Astra costs are unchanged.

## Matched pilot

All configurations received the same unchanged PDF page renders: pages 5, 25, 254
and 256, 1128 × 1648 JPEGs. Expected scene counts are 7/6/4/1; the last is a
whole-page splash. OpenAI used unchanged prompt v4, original image detail,
structured output, an 8192 output-token cap, standard service and no retries.
Only model or reasoning effort changed. Previous Astra/Sol-high responses were
reused. No evaluation boxes, human coordinates or model answers entered inference.

Costs below are estimates from reported token usage and the runner's conservative
rates, not billing receipts. Times sum generation/inference only; exclude token
preflight, downloads, model loading, rendering and review. Local runtime costs are
not monetized, and local/API hardware and service conditions differ.

| Configuration | Scenes on the four pages | Four-page API estimate | Inference time | Visual result |
| --- | --- | ---: | ---: | --- |
| GPT-6 Astra, high | 7/6/4/1 | $0.405050 | 143.1 s | User-approved baseline; all overlays and 18 crops reviewed. |
| GPT-6 Sol, high | 7/6/4/1 | $0.076630 | 68.9 s | Same scenes/order, usable crops; all overlays and crops reviewed previously. |
| **GPT-6 Sol, low** | **7/6/4/1** | **$0.044230** | **27.6 s** | **Same scenes/order, usable crops; all overlays and ordered crops reviewed.** |
| GPT-6 Luna, high | 8/6/4/1 | $0.004743 | 106.1 s | False split on 5; clipped foreground on 25. Rejected. |
| GPT-5.6 Luna, high | 8/6/4/1 | $0.019308 | 138.4 s | Same false split on 5 and tight/clipped foreground on 25. Rejected. |
| Magi, upstream suppression | 3/5/3/1 | No API charge | ~4.0 s | Merges/misses insets on all three panel pages. Rejected. |
| Magi, adjusted IoU suppression | 7/6/3/1 | No API charge | ~3.9 s | Counts improve but duplicate/composite regions and missing scenes remain. Rejected. |
| Western-comic YOLOv12x, 640 | 4/6/6/1 | No API charge | ~2.0 s | Missed scenes, duplicates and clipped text/art. Rejected. |
| Western-comic YOLOv12x, 1280 | 5/4/2/0 | No API charge | ~6.5 s | More missed scenes; no splash detection. Rejected. |

All 16 new specialist overlays and all eight Luna overlays were inspected. Those
configurations already fail scene/geometry acceptance in overlays; their complete
crop sets were retained but did not receive separate exhaustive crop acceptance.
The apparently reasonable Luna results on 254/256 are not a four-page pass.
Earlier YOLO26n, OpenComic, heuristic and Gemini results were preserved without
repeating their calls. Gemini Pro remains unmeasured because of quota failures.

Sol low is **9.16× cheaper than Astra** and **42.3% cheaper than Sol high** on this
pilot. It is not byte-identical geometry: matched scene boxes have median IoU
0.993 against Astra, minimum 0.870. The largest individual edge difference is
6.9% of a page dimension; a rectangular background crop can include more adjacent
inset material. Sol high has median IoU 0.991, minimum 0.869. These measurements
describe differences after visual scene correspondence was checked; IoU does not
replace visual acceptance, and the approved Astra boxes are not unique ground truth.

Extrapolating four-page averages to 257 pages gives roughly **$2.84 for Sol low**,
$4.92 for Sol high and $26.02 for Astra. These are illustrations, not quotes or
full-book measurements. Page complexity, retries and escalation alter cost.
Luna's lower invoice does not make its failed output an acceptable result.
OpenAI documents discounted asynchronous processing, but Batch/Flex was not
tested and no discount is included here. [Official pricing](https://developers.openai.com/api/docs/pricing).

## Specialist trial details

A fresh disposable macOS VM on Orca supplied 4 vCPUs and 8 GiB RAM. Candidate
execution stayed inside it; the host only orchestrated provisioning and evidence
transfer. CPU inference used two Torch threads, one interop thread and no GPU.
Python 3.9, Torch 2.6.0, torchvision 0.21.0, transformers 4.39.3 and the full
dependency freeze are retained. The reader continued in separate Bumble VM153.

- [Magi](https://huggingface.co/ragavsachdeva/magi), pinned revision
  `15ad498ad45093ad3b833d625728220c6309ad99`: grayscale RGB preprocessing per
  upstream guidance, safetensors checkpoint, OCR disabled because it is unrelated
  to panels. Loading assertions confirmed no missing/mismatched detector weights;
  only deliberately unused OCR weights were unexpected. The checkpoint supplies
  the backbone, so redundant pretrained-backbone downloads were disabled.
- Its [upstream panel suppression](https://huggingface.co/ragavsachdeva/magi/blob/15ad498ad45093ad3b833d625728220c6309ad99/processing_magi.py)
  drops boxes when more than half their area is covered by already kept boxes.
  This motivated one bounded experiment: replace that rule with IoU NMS 0.7 at
  confidence 0.2. It recovered additional boxes but did not recover correct scenes.
  Pre-suppression proposals, raw output and both variants are retained.
- [Western-comic YOLOv12x](https://huggingface.co/mosesb/best-comic-panel-detection),
  revision `bbab11504194d0b341ac3f6099f3592aa0604ae3`: original RGB, confidence
  0.25, IoU 0.7, 640 and 1280 image-size trials. The larger resolution did not
  rescue the failed first pass. This checkpoint is distinct from prior YOLO26n.
- Magi's geometric ordering is RTL. The adapter runs its sorter on horizontally
  mirrored box coordinates to obtain LTR indices, preserving actual images and
  detected bounds. Raw native order is retained. Geometry still fails before
  these candidates can qualify as correct guided reading.

Magi's card restricts use to personal/research/noncommercial/not-for-profit uses;
commercial use needs separate permission. The Western model card's Apache terms
do not replace Ultralytics' separate runtime terms. No production dependency was
selected. One dependency emitted an urllib3/LibreSSL compatibility warning;
inference was entirely local with complete model files. It was not suppressed,
and a reproducible supported TLS/Python stack remains necessary for future use.
The intentionally unused OCR-weight warning is explained by the loading record.

These are actual tested configurations, not exhaustive tuning or a claim that
all possible Magi/YOLO fine-tuning would fail. More tuning would need a concrete
hypothesis and broader held-out data; the current results favor Sol for this book.

## Review, evidence and budget

[Panel Lab](https://csells-mac-mini--51996.getbb.app/) build 7 preserves the approved
**OpenAI · reviewed pilot** and adds **OpenAI Sol · low reasoning** and
**OpenAI Sol · high reasoning**. Each uses the original cover plus the same four
pages, unchanged automatic boxes and unchanged source image bytes. Previous
Gemini/full-local experiments remain available. The reader application bytes are
unchanged; only the catalog and two additional CBZs differ from build 6.

The two new books each passed 25 phone-sized Chromium navigation checks with zero
uncaught exceptions on both prepared and published staging. Retained evidence
is recorded in the machine-readable summary. Whole-page overview comes
before the 17 panel steps; cover and splash occur once. Phone-sized gallery and
page-25 panel screenshots were inspected. Physical-phone review of these new
books belongs to Chris; Astra's earlier approval does not imply Sol approval.
Thirteen offline budget/API-contract tests passed. Temporary browser and preview
ports were confirmed closed; the recurring registry HTTP health probe passed
after the build 7 registry update. Anonymous access to the public share returned
401 as expected; published UI checks used the actual VM review endpoint.

[Machine-readable comparison](evidence/segmentation-iteration-20261008/cost-quality-summary.json)
records request/source fingerprints, costs, timings, review scope and artifact
hashes. Private images, responses, overlays, crops and models remain outside Git:

- `validation-artifacts/segmentation-iteration-20261008/openai-{luna,56luna,sol-low}-v4-pilot-20261008/`
- `validation-artifacts/cost-quality-20261008/`: four specialist runs, source-page
  copies, dependency freeze, model-download manifest, budget snapshot and UI evidence.
- `specialist-retained.tgz`, 2,043,559,834 bytes, SHA-256
  `f3ad94be31c7d64b2a7f40a6f1c126f7903ae864683f6302c1a5143c6fe6f9db`, retains
  complete upstream source, downloaded weights, run outputs and dependencies.
  Its exported hash matched the guest before graceful shutdown and deletion of
  only `orca-automation-comic-cost-20261008`. Templates/unrelated guests were preserved.

Twelve new paid calls all completed with recorded usage and no retries, adding
**$0.068281**. The shared ledger now holds **$4.423241 of $20**: $0.823241 estimated
reported usage plus unchanged $3.60 reservations for twelve earlier unknown Gemini
outcomes. Remaining conservative allowance is $15.576759. This iteration totals
29 OpenAI calls and 14 Gemini attempts; no new Gemini calls occurred. Reuse the
same VM153 ledger, `evidence/gemini-10usd-20261008.jsonl`; never reset its allowance.

## Next decision

Use Sol low as the next cost candidate, keeping Sol high and Astra available for
targeted comparisons of actual failures. Its four-page result merits broader
validation, not immediate full-book acceptance. Reuse the existing eight-page
Sol-high sample as a comparison: insets, diagonals, grids, front matter and the
known slightly tight page-100 bounds. No low-reasoning results exist for those
eight pages yet. Then expand in bounded batches and visually inspect every final
page, crop and order, as requested. No production Rust rewrite or automatic
confidence-based escalation policy is validated by this experiment.
