# Learned comic panel detection, segmentation, and evaluation

Research checked 2026-10-09. No candidate executed, paid inference requested, dataset access agreement accepted, or author contacted in this research. Scores below are author-reported and belong to different datasets/tasks; they are not a common leaderboard.

## Which learned approaches are worth testing next?

### Takeaway

The most promising untested direction is **specialized instance masks**, particularly KoharuLayout RF-DETR and MangaSeg-trained YOLO segmentation. Magi v3 is a newer available model than the Magi v1 checkpoint already tested, but its output remains autoregressive localization, not a source-pixel mask. None establishes universally correct guided reading.

### Cited Findings

| Candidate | Verified capability and evidence | Reproducibility and limitations |
| --- | --- | --- |
| **KoharuLayout RF-DETR Seg 2XL, 1152 px** | Panel, bubble, dialogue text, and sound-effect boxes plus instance masks; 40.3M parameters, SafeTensors, strict loader, inference config and metrics files. Trained predominantly on Japanese manga. No reading order or OCR. | First candidate for detailed mask evaluation. Card describes a qualitative 291-page color/monochrome out-of-domain review, explicitly without ground truth. Custom/other model terms; card reports RF-DETR software Apache-2.0 and Manga109 academic-use source data. [Model card](https://huggingface.co/mayocream/koharu-layout-rfdetr-seg-2xl-1152) |
| **ShadowB YOLO26s segmentation** | Panel/frame, text, balloon masks; 11.44M parameters; 23.4 MB checkpoint; recommended 1280 px, `retina_masks=True`. 1,468 validation pages from 12 books; overall mask mAP50 .97013, mask mAP50–95 .84573. | No numeric per-panel-class AP table. These are overall validation metrics, not unseen Western-comic or clipped-art recall. Uses separate instance masks (`overlap_mask=False`); frame need not equal semantic scene. MIT model-repository label does not override dataset/runtime terms. Upstream explicitly warns about Western/color/webtoon transfer, borderless scenes, thin boundaries and imperfect masks. [Card](https://huggingface.co/ShadowB/Manga109-panel-balloon-text-yolov26-segmentation) |
| **Koharu YOLO26s** | Fine-tunes ShadowB with four classes, adding sound effects. SafeTensors with strict loading and reported exact export parity. A 1,539-page book-disjoint test gives four-class box AP50–95 .795, mask AP50–95 .422; shared three-class mask AP .492 versus upstream .380 on that same evaluation. | Largest claimed improvement is dialogue text, not demonstrated panel superiority. The numbers cannot be compared directly with ShadowB's different validation setup. Custom/other derived-research terms. [Card](https://huggingface.co/mayocream/koharu-yolo26s) |
| **Magi v2** | CNN/transformer detection includes panels and speech-bubble tails, with character associations; chapter transcription uses geometric panel/text ordering. Paper reports Manga109 panel AP .9405 versus Magi v1 .9357, and zero-shot GroundingDINO .5131 in the same table. | Marginal in-domain panel improvement; main innovations concern transcription and identities. Grayscale-RGB preprocessing and CUDA examples supplied. Model card permits personal/research/noncommercial/not-for-profit uses, other use requires arrangements; repository language is narrower academic-only, so preserve both terms rather than treating this as permissive OSS. [Paper](https://arxiv.org/html/2408.00298v1), [model card](https://huggingface.co/ragavsachdeva/magiv2), [repository](https://github.com/ragavsachdeva/magi) |
| **Magi v3** | Released Florence2-family vision-language model; roughly .8B parameters, F16 SafeTensors. Task prompts autoregressively produce panel/character/text/tail locations, OCR, and character grounding. ICCV2025 *From Panels to Prose*. | A meaningful new model to screen, not a rerun of rejected v1. Model-card noncommercial restrictions parallel v2. Example uses GPU; .8B F16 weights alone imply roughly 1.6 GB before runtime/activations (our arithmetic). Not suitable for current 512 MiB reader guest. [Card](https://huggingface.co/ragavsachdeva/magiv3), [paper](https://arxiv.org/html/2503.23344v1) |
| **PanelForge by DATGMAC** | 3.4M U-Net predicts panel foreground, eroded instance markers, and boundaries; nearest-marker assignment creates instances. Polygon refinement intends to preserve protruding figures/balloons. Recursive XY-cut order supports LTR/RTL; author reports F1@IoU .5 of .863 raw/.898 filtered on held-out books, 1024 px. | MIT code; training uses Manga109-derived pages. Default confidence filter .9 can hide misses. Author documents interleaving errors on aligned 4-koma spreads. No checkpoint file found in public repository tree and README does not link one; therefore presently a technique/code lead, not a verified ready-to-run model. [README](https://raw.githubusercontent.com/DATGMAC/panelforge/main/README.md), [repository tree](https://api.github.com/repos/DATGMAC/panelforge/git/trees/main?recursive=1) |
| **Manga page element YOLO11m segmentation** | Released character/frame/balloon masks, recommended synthetic+MangaSeg checkpoint. On 784 held-out pages, frame mask AP50 .8427 and AP50–95 .5164, versus all-class .8689/.6620. | Useful independent mask architecture/character ownership signal; actual frame results clearly weaker than aggregate marketing can suggest. Model terms `other`; underlying Manga109-s/MangaSeg and Ultralytics terms remain. [Card](https://huggingface.co/anonimkaq4/manga-page-element-segmentation) |
| **DeepPanel** | Mobile-oriented TensorFlow U-Net; background/border/content labels, Android/iOS sibling implementations. Intentionally groups related panels rather than being strictly a frame-contour detector. Apache-2.0 code. | Author-reported subsecond inference lacks hardware-matched comparison here. Training set (550 pages) and test set (83) are private; public source requires creating a training dataset. Old Python3.7 stack; lower priority for exact independent scene inventory. [README](https://raw.githubusercontent.com/pedrovgs/DeepPanel/master/README.md) |

- **Important metric correction:** KoharuLayout's .9573686 panel score is explicitly in `box_ap_by_class`, not a panel-mask score. Its 1,001-page, 1152 px validation artifact reports overall box AP50–95 .7968885 and overall mask AP50–95 .5712966. There is no panel-specific mask metric in that file. The JSON training-checkpoint hash differs from the published SafeTensors hash in the card; record and verify the exact exported checkpoint during reproduction rather than assuming byte identity. [Metrics JSON](https://huggingface.co/mayocream/koharu-layout-rfdetr-seg-2xl-1152/raw/main/validation_metrics.json)
- An ONNX Koharu derivative drops the entire segmentation branch and resizes positional embeddings from 1152 to 768. Author claims lower CPU latency, but it emits **boxes only**. Its result cannot establish whether original high-resolution masks improve boundary completeness. [Derivative card](https://huggingface.co/DevilishDaoSaint/koharu-layout-rfdetr)
- Already measured here: Magi v1 with original suppression and an IoU-NMS variant, Western YOLOv12x at640/1280, manga YOLO26n, OpenComic512/1024 and heuristic tools all failed the inspected difficult four-page pilot. Magi was about4 seconds for four pages on a disposable4CPU/8GiB guest. These are tests of particular configurations, not proof that all learned specialists fail. [Local cost/quality evidence](/Users/csells/code/csells/comic_segmentation/specs/research/cost-quality-comparison-20261008.md), [local detector evidence](/Users/csells/code/csells/comic_segmentation/specs/research/detector-comparison-20261008.md)

Model repository revisions retrieved from the official Hugging Face API on2026-10-09 (pin these for a reproducible initial screening; these are repository revisions, not model-file SHA256s):

| Repository | Revision | Last modified |
| --- | --- | --- |
| [KoharuLayout API](https://huggingface.co/api/models/mayocream/koharu-layout-rfdetr-seg-2xl-1152) | `aed55fdb8ca953c6bec33cf6ed6dd52a9b72bfa2` |2026-07-25 |
| [ShadowB API](https://huggingface.co/api/models/ShadowB/Manga109-panel-balloon-text-yolov26-segmentation) | `3a860269ee0beb43ce9f31d82c7851441eb178ae` |2026-06-10 |
| [Koharu YOLO API](https://huggingface.co/api/models/mayocream/koharu-yolo26s) | `aa7b56752bc91337e0af1e44ad08b4022c9a975b` |2026-07-19 |
| [Magi v3 API](https://huggingface.co/api/models/ragavsachdeva/magiv3) | `49c73a225122d53adbaa26d53868be81a57706e2` |2026-07-21 |
| [Magi v2 API](https://huggingface.co/api/models/ragavsachdeva/magiv2) | `fbc890fec52977142e8ee00bfe26e9458b65517c` |2025-03-07 |
| [YOLO11 element API](https://huggingface.co/api/models/anonimkaq4/manga-page-element-segmentation) | `1f30cd14d255569d431d787d7eea7c1874892241` |2026-08-09 |

### Inferences

1. Test **full-resolution KoharuLayout masks** and **ShadowB segmentation** first, on identical preserved inputs and predefined failure strata. Their representations directly address our current thin/curved boundary problem and provide balloons/text as additional completeness signals. This priority is a hypothesis based on their outputs, not a demonstrated quality ranking.
2. Screen Magi v3 after mask candidates as a distinct specialist semantic proposer; do not spend effort exhaustively tuning the already-failed v1 without a specific hypothesis. V2 is a useful inexpensive control only if convenient; its published panel delta alone does not justify expecting a dramatic Western-comic improvement.
3. Keep learned masks separate from semantic panel ownership. A pixel can belong to a protruding figure or shared balloon associated with another frame. Save `frame_mask`, `content_mask`, and final conservative viewing rectangle separately; unions or associations must be explicitly validated.
4. Test source RGB and model-documented grayscale as named variants where appropriate. Do not silently remove color for all detectors: some candidate training pipelines expect grayscale, but our page57 colored ribbons contain useful color boundaries.
5. Current staging512MiB/1CPU is not a reasonable blanket host for Torch models. Use an isolated disposable larger VM for screening; measure peak RSS, warm/cold latency, model load, and batch1 CPU inference. ONNX/NCNN export should follow quality qualification, with crop/mask parity checks; it should not introduce silent resolution/geometry changes.

### Gaps

- No matched ground-truth test on this PDF or independent Western books exists for the new candidates. Author benchmarks do not establish zero clipping, exact narrative regions or good reader navigation.
- No independently reproduced CPU memory/latency figures found for the two highest-priority mask models. Model weights are not peak runtime memory.
- PanelForge released weights were not located. Full MangaSeg benchmark model training/inference release was not verified; the paper primarily delivers annotations.
- Scope of some custom weight licenses requires clarification before distribution. No legal conclusion is asserted from a model-card badge alone.

## What annotation geometry and algorithms actually fit guided reading?

### Takeaway

Frame detection and complete reading crops are different objectives. The literature explicitly studies **content-aware extended panels**, and modern mask datasets make a better hybrid possible; curved boundaries and out-of-frame artwork cannot be guaranteed by high bounding-box AP alone.

### Cited Findings

- *Towards Content-Aware Pixel-Wise Comic Panel Segmentation* (MANPU2022 proceedings published2023) is listed by its author; related2022 research defines extended boxes for comic editing and creates artificial datasets for instance segmentation. This is directly relevant to including art outside nominal frames. Verified primary abstract supports the approach, but not a numerical production-quality claim. [Author publication listing](https://yusukematsui.me/), [IEICE abstract](https://ken.ieice.org/ken/paper/20220311UC8r/eng/)
- SReN's author describes regressing quadrilateral storyboard vertices instead of relying exclusively on handcrafted edge/line/component rules. This is precedent for polygon geometry; it is not evidence that quadrilaterals solve arbitrary curves or shared foreground. [Author project](https://philokey.github.io/sren.html)
- CVPR2025 **MangaSeg** expands Manga109 from boxes to over700,000 segmentation annotations on10,130 double-page images, covering frames, balloons, text, onomatopoeia, faces and bodies. The paper explicitly identifies screentone and B/W distribution gaps from natural-image segmentation. [Paper](https://openaccess.thecvf.com/content/CVPR2025/papers/Xie_Advancing_Manga_Analysis_Comprehensive_Segmentation_Annotations_for_the_Manga109_Dataset_CVPR_2025_paper.pdf), [project](https://msxie92.github.io/MangaSeg/)
- MangaSeg distributes COCO-style per-volume annotation files, not source Manga109 images. Its supplement distinguishes pixel masks and original coarse boxes and describes six categories. [Supplement](https://openaccess.thecvf.com/content/CVPR2025/supplemental/Xie_Advancing_Manga_Analysis_CVPR_2025_supplemental.pdf)
- Magi's ordering explanation represents panels as nodes in a directed graph, uses geometric before/after relations and topological sorting. Its pipeline is useful evidence that ordering must be explicit rather than inherited from detector output indices. [Oxford project](https://www.robots.ox.ac.uk/~vgg/research/magi/)
- EACL2026 **CHROMIC** evaluates chronological reasoning across Western/Japanese comics with panel reordering, description reordering and question answering. Authors report that even leading VLMs struggle with fine-grained actions and hallucinations. It is a reasoning benchmark, not a pixel-boundary test. [Paper and abstract](https://aclanthology.org/2026.eacl-long.205/)

### Inferences

- Our desired ontology should be: narrative region identity; visible frame shape; owned/associated artwork and text; safe viewing window; order constraints. Store evidence/provenance for each. A frame-box-trained detector optimizes the wrong target when foreground exits the border; expanding every box blindly is also wrong.
- For straight/skewed pages use polygons or masks internally, while exporting a conservative rectangle for the existing reader. For curved ribbons preserve mask edges. Do not automatically suppress overlap: inset and background panels can legitimately overlap, as already seen locally.
- Bounding-box AP@.5 can remain excellent despite a narrow missing boot, bouquet stem or ribbon. Compare instance identity/count, per-edge content omission, mask boundary quality, text/balloon/art completeness and reader order separately. Add hard-negative checks for splitting one continuous scene and merging adjacent scenes.
- A promising architecture is semantic region proposal plus independently learned mask/balloon/character signals, source-resolution boundary reconstruction and conservative acceptance. This is a research proposal, not a validated pipeline.
- Semantic and geometric reading order should be separate: use declared book direction and hierarchical geometry for clear cases; escalate conflicting insets/spirals. Retain partial order/ambiguity rather than pretending sorting coordinates always identifies authorial intent.

### Gaps

- Exact frame-mask annotation conventions may exclude protruding content. Inspect annotation rules and samples before interpreting a benchmark mask as the complete guided-reading region.
- The full content-aware paper and release of its code/weights were not verified. Do not claim it is a ready-to-integrate solution.
- Curved pale scan halos versus intended artwork have no universally defined pixel-perfect truth in these sources. Evaluation needs a documented practical viewing criterion and tolerance, not a claim that every anti-aliased pixel has unambiguous ownership.

## Which datasets and benchmarks can establish generalization?

### Takeaway

Use book-disjoint **cross-style** evaluation, not more development pages from one anthology. CoMix is the strongest directly relevant public evaluation framework found; combine its domains with dedicated mask and out-of-frame-content cases, and keep data permissions independent of software/weight permissions.

### Cited Findings

| Dataset or benchmark | Verified relevance | Access/interpretation |
| --- | --- | --- |
| **CoMix, NeurIPS2024** | Combines existing datasets with expanded tasks and American comic books to counter manga-heavy evaluation; detection, reading order, character association and narrative tasks; zero-shot and limited fine-tuning settings, validation data and held-out evaluation server described. | Paper reports a substantial human/model gap. It provides a multi-domain qualification design, not proof any model solves segmentation. [Paper](https://arxiv.org/abs/2407.03550) |
| **CoMix implementation / Comics Datasets Framework** | Repository has completed detection evaluation machinery exporting COCO predictions, with DCM, COMICS, eBDtheque and PopManga adapters; README marks Manga109 and some multitask work unfinished. | Useful adapter/evaluator reference. Obtain each image collection from original owners; the framework's existence does not waive source licenses. [Repository](https://github.com/emanuelevivoli/CoMix), [dataset procedures](https://raw.githubusercontent.com/emanuelevivoli/CoMix/main/docs/datasets/README.md) |
| **Manga109 / Manga109-s** | Official current site:109 Japanese volumes,21,142 single pages; original frame/face/body/text boxes.109-volume set academic/noncommercial;87-volume Manga109-s permits commercial use per official summary. | Exact release/access agreements still govern use. Distinguish single pages from the10,602 double-page image records to avoid incorrect sample counts. [Official site](https://manga109.github.io/manga109-project-website/en/), [annotation format](https://manga109.github.io/manga109-project-website/en/annotations.html) |
| **Manga109-v2026** | Revises roughly29,000 dialogue annotations; official current statistics retain103,850 frame annotations. | Not a new all-style panel-mask benchmark. One book's images were resized with rescaled annotations; pin image release alongside masks to avoid coordinate drift. [Paper](https://arxiv.org/abs/2605.21182), [official release card](https://huggingface.co/datasets/hal-utokyo/Manga109/blob/main/README.md) |
| **MangaSeg** | Pixel mask supervision complementary to boxes. | Gated contact-sharing access. Public card grants academic/commercial use of its annotation images with attribution, but this does not automatically grant Manga109 source-image rights. Do not accept access agreement or share user details as a side effect of research. [Official card](https://huggingface.co/datasets/MS92/MangaSegmentation) |
| **mayocream Manga109 Segmentation v2** | Annotation-only COCO RLE for text/SFX/bubbles/panels;10,098 retained pages,103,640 panels, containment relations, provenance and excluded-page diagnostics. | Uses revised supervision including teacher-refined text masks; not independent manually adjudicated truth for every pixel. Source images separately required; custom/other terms. [Dataset card](https://huggingface.co/datasets/mayocream/manga109-segmentation/blob/main/README.md) |
| **eBDtheque** |100 pages spanning America/Japan/Europe; manual horizontal boxes for panels, balloons and text; reading-order rank and other metadata in SVG. | Scientific/noncommercial computer-science use; registration. Small but valuable style-diverse held-out set. [Official description](https://ebdtheque.univ-lr.fr/database/), [terms](https://ebdtheque.univ-lr.fr/registration/) |
| **DCM772** |772 comic images with panel/character/face boxes, introduced for deep-learning indexing. Authors explicitly illustrate that cross-domain detected boxes may fail to fit panel edges. | Distinct from the much larger COMICS corpus and raw Digital Comic Museum library. CoMix documents the original university GitLab download. [Original paper](https://staging.core.mdpi.com/2313-433X/4/7/89), [download reference](https://raw.githubusercontent.com/emanuelevivoli/CoMix/main/docs/datasets/README.md) |
| **COMICS** | Authors release raw page/panel data, OCR, annotations and original narrative-learning code. | Legacy Python2.7/Theano baseline should not become our runtime. Separate human annotated evaluation from automatically extracted large-scale panels; automatically produced crops cannot prove detector correctness. [Official repository](https://github.com/miyyer/comics), [original paper](https://home.cs.colorado.edu/~jbg/docs/2017_cvpr_comics.pdf) |
| **AI4VA** | Franco-Belgian1950s comics, two consistent styles, segmentation/depth/saliency/characters. | Useful Western-domain supplementation, not broad by itself. Official code/data terms personal research/noncommercial/not-for-profit. [Paper](https://arxiv.org/abs/2410.20459), [repository terms](https://github.com/IVRL/AI4VA) |

### Inferences

1. Freeze a small screening set before trials: our current failure patterns plus independent regular Western pages, irregular Western layouts, B/W manga RTL, 4-koma double spreads, webtoons, aged scans, borderless scenes, shared balloons, insets and page-edge foreground. Compare every candidate on the same set; retain correct examples to detect regressions.
2. Then evaluate on disjoint books/artists with fixed prompts/thresholds and no per-book edits. Split by book before augmentation and deduplicate spread/single-page versions; avoid training on one half and testing on its other half.
3. Measure exact-page success and dangerous false acceptance, not only panel AP. A final pipeline should disclose unresolved whole-page fallback and make fallback frequency a quality metric. Human inspection qualifies a frozen version; it must never silently supply boxes or choose branches during automatic evaluation.
4. Prioritize complementary error reduction over blindly ensembling votes. Two manga models trained on overlapping labels are not independent evidence; their agreements can share the same annotation blind spots.
5. File-container diversity (PDF/CBZ/CBR/folder) should be tested independently from visual-domain diversity using equivalent page pixels. Rendering/scaling differences must be recorded so decoder drift is not falsely credited to the detector.

### Gaps

- No public benchmark located establishes perfect content-preserving crops across arbitrary Western/manga/webtoon/art-comic layouts. There is no defensible evidence for a universal perfection guarantee.
- Gated images were not obtained; benchmark reproduction remains future authorized work. Public-dataset terms and permitted trained-weight uses differ, especially for commercial distribution.
- Independent mask-boundary gold labels for our difficult Western examples remain necessary; Manga109-derived metrics alone would systematically under-test the intended product.
