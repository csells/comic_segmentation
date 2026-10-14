# Foundation models, semantic geometry, and evaluation for comic panels

Research date: 2026-10-09. Scope: primary-source research only; no paid inference, downloads of model weights, runtime experiments, or external contacts. Recommendations below are hypotheses to test, not newly established segmentation results.

## Which foundation-model methods deserve a serious comparison?

### Takeaway

The best-supported architectural direction is to separate semantic panel discovery from pixel boundary reconstruction and reading-order inference. Generic segmentation models are useful proposal/refinement tools, but none of the sources reviewed establishes perfect autonomous comic panel discovery or exact crop completeness.

### Cited Findings

- **SAM 2.1:** official implementation supports point/box prompted image masks and automatic mask generation. Tiny is 38.9M parameters; large is 224.4M. Published throughput is measured on an A100, so it cannot predict home-lab CPU latency. Code and model checkpoints are Apache 2.0; custom training is supported. This makes the tiny checkpoint a relatively accessible first learned-mask comparator. [Official repository and checkpoints](https://github.com/facebookresearch/sam2), [model sizes, benchmark hardware and licensing](https://raw.githubusercontent.com/facebookresearch/sam2/main/README.md).
- **SAM 3 / 3.1 actually exist:** SAM 3 accepts text and visual prompts and returns masks, boxes and scores; it has 848M parameters. The repository lists Python 3.12+, PyTorch 2.7+, CUDA 12.6+ and gated checkpoint access. SAM 3.1 was announced March 27, 2026, emphasizing multi-object video tracking. The image benchmarks are LVIS, COCO and SA-Co, not exact comic-panel crops. [Official SAM 3 repository](https://github.com/facebookresearch/sam3). It uses a custom SAM license, distinct from SAM 2's Apache 2.0; retain the actual license in any selection decision. [SAM license](https://raw.githubusercontent.com/facebookresearch/sam3/main/LICENSE).
- **A comic-specific SAM adaptation already exists:** Vrroom's project modifies SAM to predict comic-frame polygon corners. Repository declares Apache 2.0 and reports testing on an A10. [Repository](https://github.com/Vrroom/segment-anything-comic). The installer downloads original SAM ViT-H plus a 2.6GB trained checkpoint from Drive; availability is declared in code, not download-verified here. [Installer](https://raw.githubusercontent.com/Vrroom/segment-anything-comic/main/install_and_run.sh).
- The SAM-comic author's report uses procedural synthetic comic layouts and freezes the heavy image encoder while training the decoder to predict canonicalized corners. On Pepper & Carrot, reported IoU is original SAM 0.42, the adaptation 0.88, and classical Halford 0.93. Its prompted evaluation gives the model ground-truth frame centers; the author explicitly acknowledges this advantage and failure on complex cluttered pages. Automatic operation samples points and filters predictions with NMS. These are class-project results, not proof that SAM wins or that automatic discovery is solved. [Author's technical report/blog](https://vrroom.github.io/blog/2024/02/23/comic-frame-segmentation.html).
- **Grounding DINO:** released open-set text-conditioned box detector, with downloadable Swin-T/B weights and CPU-only support. The README's example zero-shot COCO evaluation reports 48.5 AP, not comic performance. [Official implementation](https://github.com/IDEA-Research/GroundingDINO). The repository license is Apache 2.0. [License](https://raw.githubusercontent.com/IDEA-Research/GroundingDINO/main/LICENSE). Its natural role here is an independent box proposal feeding a mask model, not a replacement for source-aware completeness checks.
- **Florence-2:** Microsoft's model card lists MIT licensing, 0.23B base and 0.77B large variants, object detection, phrase grounding, region proposals and OCR-region outputs; example inference has CPU and CUDA branches. The current large model card warns the continued-pretraining variant may not be well trained, so pin revision and checkpoint identity rather than assuming every Florence-2 download is the same model. No comic-specific benchmark is supplied there. [Official model card](https://huggingface.co/microsoft/Florence-2-large).
- **DocLayout-YOLO:** YOLOv10 document-layout detector with synthetic document pretraining and global-to-local perception; provided DocStructBench weights, sample input size 1024, CPU/CUDA inference. Its document benchmarks do not establish comic panel semantics. [Official README](https://raw.githubusercontent.com/opendatalab/DocLayout-YOLO/main/README.md). Repository is AGPL-3.0. [License](https://raw.githubusercontent.com/opendatalab/DocLayout-YOLO/main/LICENSE). Lower-priority generic comparator than a comic-trained detector.
- **A detector-to-mask hybrid is already used on comics:** CoMix v0.1 pages uses Faster R-CNN detections to prompt SAMv2 segmentation; page classes distinguish story, cover, ads and text stories. The dataset card warns that masks may be empty, flags optimistic, detections noisy; splits are at book level. Its declared license is CC-BY-SA-4.0. Consequently these machine annotations can seed experiments but must not become independent gold labels for the same mask method. [Dataset card and pipeline](https://huggingface.co/datasets/emanuelevivoli/comix-v0_1-pages/blob/main/README.md).
- **Magi supplies a stronger domain model:** its authors frame panels, characters and text as scene-graph nodes with speaker/identity links. Magi v1/v2 use DETR-style node generation; v3 uses next-token prediction. Manga panel order is a directed graph followed by topological sorting, with intra-panel text order handled separately. [Oxford project description](https://www.robots.ox.ac.uk/~vgg/research/magi/). A failed pilot of one Magi version/configuration does not evaluate all of these components or current versions.

### Inferences

- Rank **SAM2.1 tiny as a box-conditioned refiner**, a domain-trained detector as alternate inventory, and **SAM3 text/box masks as a challenger**. Grounding DINO and Florence-2 are useful independent proposals, but an unbounded model zoo is unlikely to be the best use of this budget. DocLayout-YOLO is a lower-priority baseline.
- A panel is not necessarily a single physical object, connected foreground component, rectangle or closed contour. A character can cross a frame; a balloon can belong to two scenes; a borderless scene can share paper background with the gutter. Generic “segment anything” masks may isolate a character instead of the narrative region. Check inventory separately from masks.
- Store three distinct representations: **semantic panel identity**, **frame/content footprint** (polygon/mask, potentially multiple components), and **reading viewport** (safe rectangular crop). A tight frame mask should not erase crossing artwork. The viewport can include neighboring incidental pixels while still being the correct readable crop.
- Reuse one page image embedding for multiple panel prompts where the API permits. Preserve original bytes and coordinates. Pixel geometry can operate on a native-resolution local crop, while semantic inventory sees the complete page.
- New local models need a suitably provisioned disposable VM. Do not infer that 512MiB VM153 can host PyTorch models because a README supports CPU execution. SAM3's documented CUDA path additionally requires GPU discovery/provisioning.

### Gaps

- No source found proves SAM3, SAM2, Florence or Grounding DINO beats the current Sol-based prototype on this book, much less arbitrary books. We have not run them.
- No verified RAM/VRAM peak or CPU latency for our actual page sizes/hardware; A100 FPS and parameter counts are not deployment measurements.
- SAM-comic's trained weight URL was inspected but not downloaded or integrity-verified. Its corner representation may not express curved ribbon boundaries; inspect output dimensionality before integration.
- Code license, weight license and training-data rights are distinct. This note reports upstream labels, not a legal approval for redistribution.

## What input representation and automatic quality policy should improve robustness?

### Takeaway

The strongest directly relevant evidence favors **global page context plus enlarged local evidence**, not asking a single whole-page model to locate every thin boundary exactly. Independent geometric measurements and calibrated, localized semantic checks should replace repeated expensive full-candidate judgment as the first response to uncertainty.

### Cited Findings

- **Zooming into Comics / AI4VA-FG** evaluates 16,264 VQA examples derived from two Franco-Belgian comic series with faded colors, halftones and hand lettering. For Qwen2.5-VL-7B, zoomed panel input improved panel-understanding accuracy from 41.33 to 58.67 and action recognition from 43.54 to 55.78; GPT-4o also improved. These are VQA tasks, not exact segmentation. The authors note Gemini-generated panel-understanding labels confound Gemini comparison. Their RARL training used eight H800 80GB GPUs, far beyond this experiment budget. Take the input-representation lesson first, not the training recipe. [Paper, especially Tables 3–5](https://arxiv.org/html/2511.06490v1).
- **CHROMIC (EACL 2026)** uses a YOLOv12 detector and DAG/topological ordering; Western inputs receive indexed panel boxes, Japanese panels are cropped into the predicted order. It reports that page overlays alone did not resolve dense Japanese layout relationships. Dataset construction includes human refinement and deliberately prioritizes clear segmentation and reading orders. Thus it supports separate structure/preprocessing stages, but its curated benchmark is not evidence for autonomous hard-page perfection. [Paper, Sections 3.2–3.3 and Appendix A](https://aclanthology.org/2026.eacl-long.205.pdf).
- **GroundingME** explicitly tests similar-object discrimination, spatial relationships, tiny/occluded objects and rejection of nonexistent targets. The live leaderboard uses Accuracy@0.5, not pixel completeness. Its updated top entry is 49.8 overall and 5.5 rejection, while the page's abstract still quotes an older 45.1 best result. This discrepancy is within the source; avoid treating its headline as a current universal model ranking. It supplies evidence that grounding and abstention require dedicated evaluation. [Primary project and results](https://groundingme.github.io/).
- **Ensemble agreement is not independence:** a 2026 preprint tested nine LLM judges from seven families on three natural-language-inference datasets and estimated about two independent votes' information. This is language evaluation, not a direct comic-VLM result, so its numbers should not be transferred. It nevertheless provides a concrete reason to measure correlated failures instead of assuming majority vote creates correctness. [Nine Judges, Two Effective Votes](https://arxiv.org/abs/2605.29800).
- **Conformal Risk Control** provides calibration of an expected monotone loss under its statistical assumptions, with computer-vision false-negative examples. It is a framework for measured error control, not an unconditional every-image guarantee. [Paper](https://arxiv.org/abs/2208.02814), [author's implementation and segmentation example](https://github.com/aangelopoulos/conformal-risk).

### Inferences

- **Proposed representation:** full-page overview for scene count/order; clean native-resolution target neighborhood; clean rendered candidate crop; optional correctly marked integer crop boundary. Keep source and overlay separate. Present all coordinates with explicit origin, units, resize, padding and rounding transforms. The existing marked-detail experiment already heads in this direction.
- **Do not upscale and assume extra evidence.** Selectively rerender original PDF regions at higher resolution when source content supports it; an enlarged existing JPEG reveals existing pixels but cannot recover discarded detail. Compare native PDF/raster source against cached 150DPI representation on thin boundary controls before spending inference money.
- **Geometry-first correction:** use the semantic candidate to seed a source mask, compare its actual support with the viewport, then expand to a safe support envelope. Keep ambiguity explicit when touching regions, white-on-white art or multiple components make ownership uncertain. Deterministic threshold sweeps should agree on stable boundaries; disagreement itself is a routing feature.
- **Two cheaper model tasks:** inventory/order judgment and ownership of a localized disputed region. Ask the model which candidate region belongs to which panel, rather than requesting another set of approximate absolute coordinates whenever one narrow taper is disputed.
- **Cache quality evidence by actual dependencies:** source hash, target crop bytes, local source neighborhood, target identity/context actually included, model/prompt/version. Unchanged target evidence can be reused if dependencies are unchanged; whole-page inventory judgments still depend on the full candidate. Do not silently reuse a decision if the earlier request included changed boxes or full-candidate metadata.
- **Adopt bounded repair with monotone progress:** each correction should address a localized measured defect and either reduce it or abstain. A crop rejected then accepted on identical evidence should trigger a judge-stability finding, not repeated calls until an accept appears. Preserve all conflicting verdicts.
- **Calibrate the decision model on unseen books:** confidence is a score until empirically validated. Measure harmful false acceptance versus automatic coverage and cost at several thresholds. Use family/style strata, then book-held-out tests. A clean 12-page development replay cannot calibrate a risk guarantee.
- **Abstention is an output contract:** unresolved geometry should retain the whole source page and carry a reason. Report its rate separately from correct panel segmentation. Zero clipped art through universal whole-page fallback is not a successful panel detector.

### Gaps

- No reviewed paper quantifies how much our current marked-detail prompt improves crop-completeness accuracy across independent books.
- No universally valid background/halftone/noise threshold exists in these sources. Threshold-specific pale-art failure must be measured on held-out scans.
- Statistical risk control cannot justify “perfect for every comic” from a finite development sample, especially after layout/style distribution shift.

## How should we measure success and spend the remaining research budget?

### Takeaway

Measure **readable, complete, correctly ordered panels on held-out books**, with whole-page exact success as the main product metric. Spend first on representations and cheap geometry, then small falsifiable model comparisons; reserve most remaining money for an independent validation run rather than repeated retries on page57.

### Cited Findings

- **Boundary IoU** was introduced because ordinary mask IoU can hide boundary errors, especially for large objects. The authors propose boundary-sensitive AP/PQ and show responsiveness to improvements overlooked by standard mask IoU. [Boundary IoU paper](https://arxiv.org/abs/2103.16562).
- Boundary metrics also have limitations: the tolerance-band width changes the interpretation and should reflect annotation variability; boundary-only predictions can score misleadingly without interior checks. [Metrics Reloaded: Boundary IoU](https://metrics-reloaded.dkfz.de/metric-library/boundary_intersection_over_union_local).
- **clDice** measures skeleton/mask overlap to emphasize connectivity in tubular structures. Its validation domains are vessels, roads and neurons, not comics. It is an idea for detecting loss of thin tips/links, not a ready-made comic quality metric. [Original paper](https://arxiv.org/abs/2003.07311).
- CoMix v0.1's own dataset card distinguishes noisy model annotations from reliable independent truth and uses book-level splits; borrowing its automatically generated masks to certify the same SAM pipeline would be circular. [Dataset card](https://huggingface.co/datasets/emanuelevivoli/comix-v0_1-pages/blob/main/README.md).

### Inferences

**Evaluation contract (proposed):**

1. Annotate panel inventory, allowed reading-order relations, frame footprint, readable-content ownership, shared balloons, and source-drawn truncation separately. Permit multiple defensible orders where art deliberately leaves ambiguity; report those cases separately. Evaluation labels must stay outside runtime prompts/routing.
2. Match predicted and true panels one-to-one, then count missed, merged, split, extra and misordered panels. Report exact-page success: every required panel complete, no harmful crop, correct ordering. Also retain detection AP for comparison with academic work.
3. For each viewport, calculate required-content recall, amount of clipped required content and maximum inward boundary distance. Use actual integer-pixel crop extents, not merely serialized normalized boxes. Any omitted lettering, face part, limb, motion line or narratively relevant artwork can be a severe failure even when its area is tiny.
4. Penalize excessive viewport expansion too: unrelated-scene area, duplicate exposure, zoom/readability. Otherwise outputting the entire page for each panel wins recall. Shared content can legitimately belong to multiple panels; incidental neighbor fragments are not automatically defects.
5. Add maskIoU plus BoundaryIoU, per-edge and thin-structure diagnostics; do not substitute them for content ownership. A 1px scan halo should not equal a missing balloon word. Freeze an annotation tolerance and adjudication policy before comparing systems.
6. Report source-type ingestion success (PDF/CBZ/realCBR/folder), reading direction (LTR/RTL/vertical), plain grids, borderless/overlap/montage/splash/spread/curves, color/B&W/halftone, resolution and scan quality. Hold out entire books/artists, not adjacent pages from the same story. Existing 257-page anthology remains development material.
7. Report acceptance precision, fallback/abstention rate, exact-page success, model calls, cold-cache and warm-cache costs, median/tail latency and resource peak. Separately report unknown paid-request holds and unavailable-account failures.
8. Apply metamorphic tests where semantics should be stable: slight uniform resize, padding, lossless format change and benign JPEG variation, with inverse coordinate transforms. Do not assume every rotation/mirror preserves reading order. Reuse saved candidate results for geometric checks; new inference only when testing actual model stability.

**Project economics supplied by the coordinator (observed local evidence, not literature):** total ledger $38.313667 used/held, including $4.30 unknown holds; authorized total $60, remaining $21.686333. The V28 two-page56/57 dependency graph uses181distinct cached+new requests totaling$10.437855 reported usage:67Astra requests account$10.230645,110cheapjudge requests$.030753,4Sol requests$.176457. This is cold dependency accounting for a pathological case, not incrementalV28spend($2.473042) or a general per-page forecast. Preserve the holds.

**Ranked experiment allocation — proposed spending ceilings, not price quotations:**

| Rank | Experiment and falsifiable outcome | Incremental paid cap |
|---|---|---:|
|1|Freeze a small mixed-style boundary/ownership suite from existing reviewed evidence; inspect nativePDF/high-resolution source versus cached150DPI; compare exactedge mapping, local contrast views, component support and conservative envelopes. Fail any method that restores tips by swallowing unrelated scenes or damages known-good controls.|$0 API|
|2|Run SAM2.1tiny with automatic box/point prompts on the same frozen candidates, plus one comic-trained detector chosen by the adjacent survey. Measure boundaries, inventory, RAM and latency. No manual point placement in the scored automatic track. Keep an oracle-point track only as an explicitly labeled upper bound.|$0 API; localcompute measured|
|3|Evaluate global+local source representation and localized ownership questions on held-out examples with current low-cost models. Include identical-crop/context-variation stability controls and deliberately flawed negatives. Stop on a repeated failure class.|$3|
|4|Compare SAM3 only if existing disposableGPU capacity/weightaccess make it practical; otherwise postpone. Do not rent hardware solely to fit a model before cheapgeometry and SAM2 establish opportunity. GroundingDINO/Florence are second-line challengers when their error diversity is demonstrably useful.|$0 API by default|
|5|Select one hybrid candidate, freeze prompt/policy, run bounded live held-out book samples and score actual final output. Keep at least$15for this and continuation; don't spend it on page57judgefan-out. Expand sample only while projected reservedcost fits.|$15|
|6|Keep unallocated allowance for one specific failure-driven ablation or unexpectedly expensive unresolved request, while retaining the existing$4.30hold.|$3.686333|

Total new paid allocations are at most$21.686333. No paid work was performed for this note. Broad perfection remains an aspiration; the concrete milestone is increased exact-page success across independently chosen books with a measured low harmful-accept rate, bounded cost, and explicit whole-page fallback.

### Gaps

- A sufficiently diverse, independently adjudicated crop-completeness benchmark does not yet exist in this project. Published detectorAP and text/VQA benchmarks cannot substitute for it.
- No guaranteed number of remaining PDF pages can be processed for$21.686333 until the pathological verifier fan-out is reduced and ordinary-page cost is measured.
- Current source availability and licenses for independently held-out books must be checked before assembling the scored corpus. No new corpus was downloaded here.
