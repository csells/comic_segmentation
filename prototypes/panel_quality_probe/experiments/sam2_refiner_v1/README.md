# SAM 2.1 tiny refinement — executed development screen

Question: can a generic box-prompted mask recover the full semantic region,
including content outside saved automatic box proposals, without merging a rival
scene? This spike supplies **only automatic saved boxes**, with no manual points,
review labels, text descriptions, or target-specific parameters. It produces
diagnostics and does not alter conversion or the reader.

Run only in the authorized disposable mask-worker VM. The six-case, 45-box single-mask and three-alternative runs completed there.
Six coordinate tests passed. A writable-input repeat removed a NumPy warning
with all 45 binary masks unchanged. See the
[measured report](../../../../specs/research/specialist-mask-spikes-20261009.md).
Box-only configurations remain unqualified; no paid calls were needed for them.

## Pinned runtime and checkpoint

- Official code: Meta [SAM 2](https://github.com/facebookresearch/sam2/tree/2b90b9f5ceec907a1c18123530e92e794ad901a4), commit `2b90b9f5ceec907a1c18123530e92e794ad901a4`.
- Official [tiny checkpoint](https://huggingface.co/facebook/sam2.1-hiera-tiny/tree/de431c4043854a71d8101e17995dfe596bf101a5): `sam2.1_hiera_tiny.pt`, revision `de431c4043854a71d8101e17995dfe596bf101a5`.
- Weight SHA-256 `7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69`, expected size 156,008,466 bytes. Pinned upstream file metadata was inspected; local byte verification happens on download.
- Config `configs/sam2.1/sam2.1_hiera_t.yaml`, CPU float32, four torch threads, no CUDA extension. Code/checkpoints are Apache-2.0 according to the [official repository](https://github.com/facebookresearch/sam2/tree/2b90b9f5ceec907a1c18123530e92e794ad901a4).

Use a separate environment. Install the exact noneditable git revision so its
`direct_url.json` proves the code commit (the runner requires this). Save a full
package freeze and install log. The upstream minimums are torch 2.5.1,
torchvision 0.20.1, Python 3.10; use a supported matching torch/torchvision pair.

```sh
SAM2_BUILD_CUDA=0 python -m pip install 'git+https://github.com/facebookresearch/sam2.git@2b90b9f5ceec907a1c18123530e92e794ad901a4'
python -m pip freeze > resolved-requirements.txt
python probe.py --cases cases.json --output sam2-tiny-box-v1 --weights-dir weights
```

Weights download only if absent; an existing file must match its digest. Partial
downloads are retained on failure and require inspection before recovery.

## Case manifest

`cases.json` supplies immutable evidence files already produced automatically.
Paths are relative to the manifest, or absolute. Populate hashes from actual
files; placeholder values below are deliberately unusable. Case IDs never enter
the model. Keep adjudication labels in a separate evaluation file.

```json
{
  "version": 1,
  "cases": [
    {
      "id": "page57-original",
      "source": "inputs/0057.jpg",
      "source_sha256": "REPLACE_WITH_ACTUAL_SHA256",
      "proposals": "proposals/page57-original-bundle.json",
      "proposals_sha256": "REPLACE_WITH_ACTUAL_SHA256"
    }
  ]
}
```

Use saved `bundle.json` when available: the source `images[0].sha256` must match,
and each panel's `images[order].points` supplies **inclusive corner pixels**.
The converter uses `(left, top, right + 1, bottom + 1)` to create the actual crop.
The runner therefore adds one to the saved maximum x/y before using half-open
XYXY extents for SAM prompts and pixel measurements. A page-edge corner at
`width - 1` becomes a half-open right extent of `width`. The bundle must contain
one crop for every ordered panel.

A saved `result.json` with `panels[].box` and `source_sha256` is also accepted;
its normalized `[y0,x0,y1,x1]` coordinates are mapped once with floor on minima,
ceil on maxima. This fallback is an **estimated analysis prompt**, not verified
equivalence to the converter's `_rectangle` rounding or the actual saved crop.
Every record retains the mapping rule, original box and `crop_extent_exact`
flag. Use bundles for any exact crop-completeness comparison. A changed
source hash, nonrectangular saved points, unexpected ordering, or nontrivial EXIF
orientation fails explicitly.

Run the coordinate-only regression tests inside the VM before inference. They
import only the Python standard library and do not load torch, Pillow or SAM:

```sh
python -m unittest discover -s . -p test_coordinates.py -v
```

Recommended first manifest: all thirteen original automatic page-57 proposals,
their automatically repaired set, and the original/corrected automatic page-150
sets. Do not substitute hand-drawn boundaries or select individual targets based
on visual review. The old/new sets are diagnostic controls; no result is claimed
held out. A single full-page embedding is reused across all prompt sets with the
same source hash. Each box is then decoded separately to bound memory.

## What the runner saves

- Source, proposal, checkpoint, native-output and case-manifest hashes; package
  versions, exact git-install provenance, model configuration and CPU settings.
- Import/model-load time; one embedding time per unique source; separate prompt
  inference time; process-lifetime peak RSS with platform-specific units.
- Full source-resolution floating logits, low-resolution logits and every model
  quality score in an NPZ per target. Native array shapes/dtypes are preserved.
- Binary masks at threshold zero, complete source-coordinate mask bounds,
  overlays with the exact red prompt rectangle, and source-pixel diagnostic
  windows containing the union of the original box and mask bounds.
- Mask pixels inside/outside the original box, outward extension in pixels,
  original-box mask coverage and empty-mask flags. These are geometric residuals,
  **not semantic correctness measurements**.

Baseline uses `multimask_output=False`, appropriate to an explicit box prompt.
SAM's default model stability postprocessing remains enabled and recorded; hole
filling/sprinkle removal are explicitly disabled for a reproducible CPU path.
If ambiguity remains, `--multimask` runs a separately named variant and preserves
all returned candidate masks and scores. No candidate is selected using review
labels, and no repeated run should occur merely to seek a better random outcome.

## Why content can extend beyond the seed box

Pinned SAM [predictor code](https://github.com/facebookresearch/sam2/blob/2b90b9f5ceec907a1c18123530e92e794ad901a4/sam2/sam2_image_predictor.py)
encodes the two box corners as prompt tokens. Its [mask postprocessor](https://github.com/facebookresearch/sam2/blob/2b90b9f5ceec907a1c18123530e92e794ad901a4/sam2/utils/transforms.py)
upsamples logits to full source dimensions; it does **not** clip masks to the box.
This runner also never crops the input page or truncates output masks to a prompt.
The model can therefore expand beyond an imperfect seed, although a learned
object mask may still omit the panel's background or select a character instead.

Inspect full source, each mask and each diagnostic crop, including known-good
controls. Reject full-page leakage, wrong semantic ownership, missing text/art,
scene merges and disconnected-content omissions. A higher quality score or a
nonempty outside-box residual does not prove a useful refinement. Do not erase
artwork with these masks or integrate them before automatic E2E qualification.
