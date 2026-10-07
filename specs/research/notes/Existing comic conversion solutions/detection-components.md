# Reusable panel detection and reading-order components

Research date: 2026-10-07. Scope: four component choices, not complete converters. Evidence labels: **advertised** means maintainer documentation; **source** means inspected implementation; **runtime** means executed locally. No user pages were uploaded, no Gemini requests were made, and no pretrained weights were downloaded. Existing Gemini approval remains settled; alternatives below are recommendations for evaluation, not an agreed provider change.

## Which components actually provide geometry and reading order?

### Takeaway

Kumiko directly produces ordered rectangles. OpenComic AI provides masks and rectangles, with ordering implemented separately in its reader. Magi combines detection with geometric ordering, but its licensing requires clarification. Existing Gemini integration is small and reusable conceptually, but does not yet request reading order.

### Cited Findings

- **Kumiko — source.** Pin [`9d587ae`](https://github.com/njean42/kumiko/commit/9d587ae9498bc84dfda06fc19c6ad89f421bec14), last commit 2024-12-22. Its CLI accepts an image or directory and emits JSON containing page dimensions and ordered `[x,y,width,height]` rectangles; `--rtl` changes direction. Shapes are reduced to bounding rectangles even when contours are irregular. This is a direct subprocess boundary for Rust, without a model download. — [Usage](https://github.com/njean42/kumiko/blob/9d587ae9498bc84dfda06fc19c6ad89f421bec14/doc/Usage.md).
- Its Python pipeline uses Sobel edges, external contours, line segments, splitting, merging and panel expansion; `fix_panels_numbering()` reorders by neighboring panels. It inserts a whole-page rectangle if no panels survive. `merge_panels()` combines containment, a relevant limitation for inset panels. Python imports include OpenCV, NumPy and Requests; documentation's “only OpenCV” statement is incomplete for the inspected code. — [Page implementation](https://github.com/njean42/kumiko/blob/9d587ae9498bc84dfda06fc19c6ad89f421bec14/lib/page.py), [imports](https://github.com/njean42/kumiko/blob/9d587ae9498bc84dfda06fc19c6ad89f421bec14/kumikolib.py).
- **OpenComic AI — source.** [`opencomic-ai-bin` 1.4.7, pin `f4d2a82`](https://github.com/ollm/opencomic-ai-bin/blob/f4d2a82fcd08b31c0796cbe4161da6c1765f0114/package.json), committed 2026-10-04, exports `OpenComicAI.panels.image(source, options)`. Options select a named 512/1024 model, minimum component pixels, aspect handling and optional mask upscaling. It resizes/grayscales the page, transforms channels, runs the model, thresholds connected regions and returns `boxes` with `[x1,y1,x2,y2]`, masks, working dimensions and original dimensions. The returned `probability` is hardcoded to `1`, **not calibrated confidence**. — [Panel implementation](https://github.com/ollm/opencomic-ai-bin/blob/f4d2a82fcd08b31c0796cbe4161da6c1765f0114/src/panels.mts).
- `.panels.path()` converts masks into SVG paths; it does not mean reading path/order. The test entrypoint demonstrates the API and logs a JavaScript object, not a stable JSON CLI protocol. A small Node adapter could emit JSON; Rust must map working coordinates to the preserved output page. — [Test entrypoint](https://github.com/ollm/opencomic-ai-bin/blob/f4d2a82fcd08b31c0796cbe4161da6c1765f0114/src/test-panels.mts), [path implementation](https://github.com/ollm/opencomic-ai-bin/blob/f4d2a82fcd08b31c0796cbe4161da6c1765f0114/src/yolo.mts).
- Reading order is separately implemented in OpenComic's `sortBoxes()`: corner-based row comparisons, aggregate pairwise scores, and X inversion for manga. It is not part of the inference package. — [Reader source, pin `1658260`, 2026-10-07](https://github.com/ollm/OpenComic/blob/165826057755d71d1dcf466836c518ef87cc2c6f/scripts/reading/panels.mts#L221).
- **Magi — source.** The project provides v1/v2/v3 detectors. Inspected v1 Hugging Face pin [`15ad498`](https://huggingface.co/ragavsachdeva/magi/tree/15ad498ad45093ad3b833d625728220c6309ad99) includes a separate `sort_panels(rects)`: pairwise geometry, rectangle erosion for overlap, cycle removal and topological sorting. This is a heuristic algorithm, not a learned reading-order model. Its assumptions favor manga's right-to-left order. — [Ordering code](https://huggingface.co/ragavsachdeva/magi/blob/15ad498ad45093ad3b833d625728220c6309ad99/utils.py#L174), [research paper](https://arxiv.org/html/2401.10224v2#S4).
- **Gemini — source/advertised.** This project's [AI service](/Users/csells/Code/csells/comic_segmentation/lib/ai_service.dart:33) asks for normalized rectangles and supplies a JSON schema, but contains no instruction or field establishing reading order. Google's API documents normalized `[ymin,xmin,ymax,xmax]` detection and structured segmentation output. That supports reusing the existing approach through HTTP, not a claim of comic-specific accuracy. — [Google documentation](https://ai.google.dev/gemini-api/docs/image-understanding#object-detection).

### Inferences

- A common page-plus-ordered-regions result type can accommodate all four approaches. None requires cropping away the full page before packaging ACBF.
- Reusing OpenComic AI through Node preserves its preprocessing/postprocessing. Calling only its native executable from Rust would still require equivalent image normalization, component extraction, coordinate scaling and order handling.

### Gaps

- No inspected component provides a verified combination of arbitrary Western comic geometry, narrative order and Android ACBF compatibility out of the box.
- Semantic ordering of ambiguous layouts remains unproven for all candidates. A successful detector response can still omit an inset or select the wrong sequence.

## What are the deployment, licensing and quality limits?

### Takeaway

Local detection is feasible on macOS, but “open source” does not imply a uniformly permissive stack or demonstrated accuracy. Kumiko passed simple local probes after pinning OpenCV; trained alternatives have stronger representation options but remain untested here.

### Cited Findings

- **Kumiko:** code is AGPL-3.0-or-later; there are no pretrained weights. Its README acknowledges imperfect detection and lists intertwined/borderless layouts as ongoing work. — [License](https://github.com/njean42/kumiko/blob/9d587ae9498bc84dfda06fc19c6ad89f421bec14/LICENSE), [limitations](https://github.com/njean42/kumiko/blob/9d587ae9498bc84dfda06fc19c6ad89f421bec14/README.md#short--and-longer-term-features-roadmap).
- **OpenComic AI:** wrapper code is MIT and its own panel weights are CC-BY-4.0, requiring attribution. Inspected weights repository pin is [`f1ac651`](https://github.com/ollm/opencomic-ai-models/tree/f1ac6511e41783b23d7872e4d0cc337806b92b33), dated 2026-10-04. These terms must not be generalized to every third-party model included in the catalog. — [Wrapper license](https://github.com/ollm/opencomic-ai-bin/blob/f4d2a82fcd08b31c0796cbe4161da6c1765f0114/LICENSE), [weight license](https://github.com/ollm/opencomic-ai-models/blob/f1ac6511e41783b23d7872e4d0cc337806b92b33/LICENSE_MODELS).
- Its registry includes macOS arm64/x64 native Upscayl binaries. The wrapper invokes image-to-image inference with `-i`, `-o`, `-m` model directory, `-n` model name, `-z 1`, and model-sized tiles; it does not request panel JSON. Both panel entries still contain `TODO: Test model` and zero latency placeholders. — [Registry and argument builder](https://github.com/ollm/opencomic-ai-bin/blob/f4d2a82fcd08b31c0796cbe4161da6c1765f0114/src/index.mts).
- The author's Upscayl backend fork has an **AGPLv3** license; the OpenComic reader carrying ordering code is **GPLv3**. macOS backend build instructions use Vulkan/MoltenVK, CMake and OpenMP, not PyTorch MPS. Node/Sharp plus bundled binaries is the nearer integration route. — [Backend license, pin `68813ff`](https://github.com/ollm/upscayl-ncnn/blob/68813ffc803f01efa9cb6653ca9bc8726572f9c4/LICENSE), [macOS build](https://github.com/ollm/upscayl-ncnn#macos), [reader license](https://github.com/ollm/OpenComic/blob/165826057755d71d1dcf466836c518ef87cc2c6f/LICENSE).
- OpenComic's training source describes procedural Krita datasets. Its panel preset requests 25,000 generated images; generation supports BSP and Voronoi polygons. That establishes training machinery for irregular geometry, not measured success on this book. — [Training configuration](https://github.com/ollm/opencomic-ai-training/blob/7b63179d4611cbe88e0546a5b8a92ce1b8026270/options/opencomic-ai-panels.yml), [generator](https://github.com/ollm/opencomic-ai-training/blob/7b63179d4611cbe88e0546a5b8a92ce1b8026270/src/panels.mts).
- **Magi:** licensing sources conflict. GitHub pin [`2a45bf0`](https://github.com/ragavsachdeva/magi/blob/2a45bf09b43adc80778270a366372aaa148e2291/readme.md#license-and-citation), dated 2025-06-27, says academic research only; [HF v1](https://huggingface.co/ragavsachdeva/magi/blob/15ad498ad45093ad3b833d625728220c6309ad99/README.md#license-and-citation) and [v2](https://huggingface.co/ragavsachdeva/magiv2#license-and-citation) permit personal/research/noncommercial/not-for-profit use. No clear independent permissive grant for copying the ordering code was found. Standard examples use Transformers, PyTorch, remote custom code and CUDA; v1's documented CPU demo is described as slow. MPS was not verified. — [Usage](https://github.com/ragavsachdeva/magi/blob/2a45bf09b43adc80778270a366372aaa148e2291/readme.md).
- Magi's paper evaluates panel detection on Manga109 and demonstrates ordering with overlapping panels. It does not establish Western-color-comic performance or parity with Gemini. — [Evaluation and ordering](https://arxiv.org/html/2401.10224v2).

**Runtime evidence:** unmodified pinned Kumiko CLI, macOS arm64, Python 3.13.12, synthetic 800×1000 images, fresh isolated venv. OpenCV 5.0.0.93 failed all probes with `IndexError` in line-segment handling. OpenCV 4.14.0.94 completed:

| Fixture | Observed result |
| --- | --- |
| Four framed panels, LTR | Four rectangles; correct row-major order. |
| Same grid, RTL | Four rectangles; each row reversed correctly. |
| Black bridge across upper gutter | Four rectangles, but two bounds expanded into gutters; count alone would hide geometry changes. |
| Large panel containing one framed inset | One outer rectangle; inset omitted. |

Raw results are preserved in [OpenCV 4 evidence](kumiko-opencv4-synthetic-results.json) and [OpenCV 5 evidence](kumiko-opencv5-synthetic-results.json). The [probe generator](kumiko-synthetic-probe.py) includes the exact source pin and isolated dependency setup. Scratch originals remain intact. These probes establish compatibility and concrete failure modes, not a quality benchmark.

### Inferences

- Whole-page fallback after errors does not address confidently wrong geometry. The missing inset returned valid JSON with no error.
- Recent commits establish activity, not quality. OpenComic is promising for local evaluation, but its placeholders and absent reviewed benchmark prevent recommending it as already proven.

### Gaps

- OpenComic binary-to-source build provenance, actual macOS runtime/CPU fallback, memory use and benchmark quality were not established. Wrapper licensing alone cannot settle binary redistribution.
- No trained model or Gemini comparison was run. No comic-specific Gemini benchmark or stronger reusable Gemini panel pipeline was verified in the focused search.

## What should this project reuse first?

### Takeaway

Keep the approved Gemini path as the initial candidate, reuse its existing normalized-box contract and Google's structured-output facilities, and evaluate existing local components before writing a new detector. Do not port an entire heuristic or model stack merely to make it Rust.

### Cited Findings

- Kumiko already supplies the ordered JSON boundary a Rust subprocess adapter needs; OpenComic's test program demonstrates reusable mask inference; Magi publishes a useful ordering algorithm but ambiguous reuse terms. — [Kumiko contract](https://github.com/njean42/kumiko/blob/9d587ae9498bc84dfda06fc19c6ad89f421bec14/doc/Usage.md), [OpenComic example](https://github.com/ollm/opencomic-ai-bin/blob/f4d2a82fcd08b31c0796cbe4161da6c1765f0114/src/test-panels.mts), [Magi licensing](https://github.com/ragavsachdeva/magi/blob/2a45bf09b43adc80778270a366372aaa148e2291/readme.md#license-and-citation).

### Inferences

- Recommended comparison: pinned Kumiko as a cheap baseline, OpenComic AI as the leading local mask candidate, and Gemini as the already approved general-vision candidate. Use the same representative pages and score missed/inset panels, geometry, order, processing time and cost separately. This is development evaluation, not a user-facing review feature.
- Prefer subprocess/library reuse over fresh OpenCV detector code. Add only input/output adaptation, geometry validation, explicit order and ACBF packaging around the selected component. A small Node helper is less reinvention than recreating OpenComic postprocessing in Rust.
- Avoid an automatic multi-engine cascade initially: no examined local score reliably identifies when to invoke Gemini. Select one production path after evidence; retain whole-page error fallback and the original page.

### Gaps

- Final detector choice depends on representative-page results and distribution scope. Gemini remains the agreed provider until the user explicitly changes that decision; this note authorizes neither uploads nor a silent switch.
