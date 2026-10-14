# Specialist masks: useful proposals, incomplete comic segmentation

2026-10-09. ShadowB and KoharuLayout completed the same twelve-page development
screen in a separate 8-GiB, four-vCPU macOS VM on the M4 host. Chris explicitly
authorized this second VM alongside the unrelated existing guest. No host model
runtime, API credentials, paid calls, reader changes or converter changes were
used. These are comparisons against saved source pages, not automatic conversion
or held-out qualification.

**Neither specialist is a replacement for the current semantic detector.**
Both omit entire scenes on difficult layouts. Koharu produces more useful
proposals on some conventional pages, but returns no panels on the thirteen-scene
spiral page. It also omits the lower scene containing the bouquet on page 150.
Correct-looking masks or counts do not establish complete reading crops.

## Reproducible execution

The [runner](../../prototypes/panel_quality_probe/experiments/specialist_masks_v1/probe.py)
pins repository revisions and checkpoint SHA-256s. ShadowB uses Ultralytics
8.4.43, CPU, 1280-pixel analysis, confidence .25, IoU .7 and native masks.
Koharu uses RF-DETR 1.7.0, the author's 1152-pixel configuration, strict loading
of its complete safetensors checkpoint, and per-class thresholds including .50
for panels. The runner initially requests four torch threads; Ultralytics may
reset that count during device selection, and the effective ShadowB count was
not recorded. The input manifest preserves twelve
original 1128×1648 JPEG hashes.

Every returned mask has the source dimensions; unexpected dimensions fail
explicitly. NPZ files preserve the APIs' native **postprocessed binary masks**,
not pre-threshold model logits. Source-coordinate boxes, masks, overlays, scores,
timing and dependency freezes are retained. Separate saved rendering helpers
create diagnostic box crops using floor on minimum and ceil on maximum coordinates.
Reading order and text/balloon ownership are not inferred by this runner.

Koharu's initial Python 3.14 run warned that TorchScript was unsupported.
The entire twelve-page run was repeated in a fresh Python 3.13.16 environment.
**Every saved binary mask was byte-identical across the two environments.**
Both runs used torch 2.14.1 and torchvision 0.29.1. The unsupported-Python warning
disappeared; upstream TorchScript and `use_return_dict` deprecation warnings
remain. Constructor warnings about missing base pretraining are expected here:
the complete pinned Koharu state is subsequently loaded with `strict=True`.
The model is deliberately unoptimized for this reference-quality comparison;
its latency is not a best achievable deployment measurement.

## Personally inspected twelve-page screen

Full-page box/mask overlays were inspected for every page and both models.
Gross omissions are sufficient to reject a configuration; this was not a
pixel-by-pixel acceptance audit of every apparently good crop. Counts are
returned panel-class instances, not ground-truth counts or accuracy scores.

| PDF page | ShadowB | Koharu | Observed limitation |
| --- | ---: | ---: | --- |
| 5 | 5 | 7 | ShadowB misses the large parent scene. Koharu recovers it; full crop ownership is unqualified. |
| 18 | 6 | 4 | Koharu omits the two borderless head views; ShadowB's protruding content needs crop review. |
| 21 | 6 | 6 | Both find the main layout; exact crossing-art boundaries remain unqualified. |
| 25 | 4 | 5 | ShadowB misses the bottom composition; Koharu merges its approach/departure views. |
| 40 | 6 | 5 | ShadowB misses the upper wide scene; Koharu omits the lower close-up/embrace composition. |
| 57 | 1 | 0 | ShadowB combines many lower ribbons; neither discovers the thirteen individual scenes. |
| 72 | 8 | 9 | ShadowB omits the bottom action scene. Koharu recovers it, but a right speech balloon extends beyond its box. |
| 100 | 7 | 5 | ShadowB adds a strip and duplicate lower proposal. Koharu has the main layout; exact content is unqualified. |
| 144 | 0 | 2 | Koharu merges the multiple montage views; ShadowB finds no panel frames. |
| 150 | 0 | 2 | Koharu omits the lower scene and its crossing bouquet; ShadowB finds no panel frames. |
| 254 | 3 | 2 | Both omit the large parent portrait; Koharu also misses an inset. |
| 256 | 0 | 0 | This splash naturally admits a whole-page reading view; zero detections alone is not a harmful narrative error here. |

Both specialists were trained for manga frame/layout tasks; these are Western
color pages. The screen uses author-recommended thresholds without a threshold
or training ablation. Its conclusions concern these pinned configurations.
This selected hard-page screen cannot estimate ordinary-book accuracy, and it
does not qualify every page without a listed gross defect. There is no measured
end-to-end winner from these counts.

## Timing and representation limits

ShadowB's measured model-load stage took 1.02 seconds, first prediction .63
seconds and warm predictions .25–.35 seconds. Process-lifetime peak RSS was
1,413,332,992 bytes. Supported-Python Koharu loaded in 5.58 seconds, first
prediction took 6.94 seconds and warm predictions 3.65–3.96 seconds; peak RSS was
3,785,916,416 bytes. These prediction times include each API's pre/postprocessing
but exclude result encoding, environment setup and source acquisition. Guest
swap usage and cumulative swapouts were zero after these runs. Shared-host
contention and initialization make this a bounded feasibility check, not a
throughput benchmark.

Static [API review](mask-evaluation-review-20261009.md) found that ShadowB's
Ultralytics path clips masks to its predicted boxes. Mask agreement therefore
cannot independently prove its own box complete. Koharu upsamples full-page
mask logits without box clipping, but its learned instance inventory still
misses the relevant scenes. Neither confidence score measures semantic
ownership or exact reading-crop completeness.

The [automatic component-seeded experiment](seeded-boundary-spike-20261009.md)
also failed: 32 watershed/GrabCut variants preserve caption-connected scenes
together and sometimes absorb similarly colored foreign art. Good seed-retention
metrics coexist with these failures. This strengthens the need for independent
semantic ownership evidence; it does not prove that every mask method will fail.

## SAM follows curves but box prompts do not establish ownership

Official SAM 2.1 tiny, pinned in the
[refiner](../../prototypes/panel_quality_probe/experiments/sam2_refiner_v1/README.md),
ran on four sources: 25, 40, 57 and 150. Saved automatic proposals supply all
prompts. Original and automatically repaired proposal sets for 57/150 bring the
total to six cases and 45 box prompts; there are four source embeddings.
No manual points, source crops, evaluation labels or reviewed mask selections
enter inference. Exact saved inclusive ACBF corners are converted to half-open
crop extents by adding one to maxima. Six VM-executed coordinate tests passed.

Both single-mask mode and three-alternative mode completed. The alternative-mode
screen selects the highest model score automatically and preserves every other
candidate. **Neither mode provides a qualified automatic repair.**

- On 57, target 1 joins the brown and green scenes; target 7 joins pink and yellow;
  target 10 retains foreign cyan content. Targets 8/10 do not extend the disputed
  left boundaries. Some masks follow individual curved ribbons attractively,
  which does not resolve these failures.
- One lower-scored alternative separates target 7's pink scene more cleanly,
  but the highest-scored result is merged. Inspection of all three alternatives
  for targets 1/7/10 and original 150/3 did not reveal a complete automatic answer.
- Original 150/3 expands upward by 62 pixels but still omits much of the bouquet.
  The already repaired proposal retains more bouquet content; that is not a
  successful recovery from the original input.
- Masks on 25/40/150 often remove characters or other interior content while
  preserving backgrounds. They cannot serve as complete ownership labels or
  destructive display masks. A union of their bounds with the original box would
  preserve original pixels, but does not prove recovery of omitted content.

All 29 single-mask outputs for the four saved source sets, the original 150
control, and the above alternate-mode counterexamples were personally viewed.
This is sufficient to reject those configurations; it is not a complete
acceptance audit of all 180 returned single/alternate masks.

Python 3.13.16, CPU float32, four threads: model-load stage .24 seconds;
page embedding .45–.49 seconds; single prompt decode .017–.024 seconds;
process-lifetime peak RSS 1,528,102,912 bytes. Output encoding and installation
are excluded. Full-resolution and low-resolution logits, scores, exact prompt
coordinates and source hashes are retained. The initial run warned about a
read-only NumPy input; using an explicit writable copy removed that warning,
and all 45 binary outputs were byte-identical in the repeat. The upstream
TorchScript deprecation remains a version-maintenance issue.

## Automatic semantic points separate scenes but do not qualify boundaries

The [ownership generator](../../prototypes/panel_quality_probe/experiments/semantic_points_v1/README.md)
made exactly three Astra-high requests: one each for pages 40, 57 and 150.
It received unchanged source images and saved automatic proposals, with the same
generic prompt. It received no masks, known defects, page-specific instructions
or human coordinates. Each scene gets at most three exclusively owned interior
points; uncertainty must abstain. All three responses completed with no abstentions.
The $2 local spending limit includes unknown holds and shares the $100 ledger;
two VM-executed budget tests passed. The calls cost **$0.577250** from usage.

The [point-guided runner](../../prototypes/panel_quality_probe/experiments/sam2_semantic_points_v1/README.md)
used the target's points as positives and exclusive rival points inside its
baseline mask as negatives. Original and repaired sets reuse the same point
manifest per source. Hash and coordinate checks bind every source, proposal,
point set and baseline mask. Ten point-validation tests passed. The fixed
single-mask run covered 39 targets across five cases and three page embeddings.

The major brown/green, pink/yellow and cyan/pink/green merges on page 57 separate
much better. However, target 8's mask starts at x=759 versus the existing x=754
crop edge, and target 10 starts at x=745 versus x=733. **Neither repairs the
disputed left tip.** Captions and interior artwork are sometimes missing from
the masks. On original 150/3 the mask expands upward from y=856 to y=676, but
does not retain the supplied bouquet point and still misses bouquet content.
The already repaired proposal retains more of it; that does not qualify recovery
from the flawed proposal. Source and isolated masks for the saved sets and the
original 150 control were personally inspected.

A final **points-only ablation**, using identical points and rival selection but
omitting the box prompt, completed the same 39 targets without further API calls.
It recovers more bouquet content but drops another supplied positive point on
the lower scene's hand. On 57 it remerges pink/yellow and drops much of the pale
pink taper; target 10's mask starts at x=813. The page-40 control loses substantial
content too. These configurations fail the predeclared improvement-without-damage
condition, so the SAM shortlist stops here. No mask or union-window correction
was integrated. Retaining all seed points would not itself have established
complete ownership; failure to retain them is an additional diagnostic.

This result supports separating semantic identity from geometric evidence in
the Rust discussion plan. It does not establish a winning hybrid. A future
experiment needs a specific hypothesis about missing content or boundary
uncertainty, with intact controls and independent ownership/completeness checks.
Do not tune new thresholds to these masks and call them held-out evidence.

## Current product and spending state

V28 remains unchanged: page 57 falls back to the whole page, current qualified
prefix is 1–56, prior-policy personal review extends through 150, and page 151
has not been dispatched. The web reader remains Build 10. Full 257-page
qualification and publication are unfinished; Rust implementation remains a
discussion plan.

Local model comparisons added **$0 API spend**; the three automatic semantic
point requests added **$0.577250**. The durable ledger is now
**$39.009825 used or held of $100**, including unchanged $4.30 unknown-charge
holds; **$60.990175 remains**. Local inference also consumes compute.

Paid request/source/ledger backup: `semantic-points-cap100-20261009.tgz`,
360,779 bytes, 122 members, SHA-256
`c3cd4e369e9fe98b34dde60089267dd3705b7833249c0ddf4270825a28584efa`.
The earlier source and cached-proposal archive chain remains necessary.

## Preserved evidence and worker teardown

The complete worker archive is
[`mask-spikes-final-20261009.tgz`](../../validation-artifacts/segmentation-iteration-20261008/specialist-masks-20261009/mask-spikes-final-20261009.tgz):
**2,750,795,941 bytes, 3,453 tar members**, SHA-256
`b6a5789fb8c6a9a4fe7944730cc2062e801c5d6224c29e392bb3a73e246062b5`.
Its transferred hash matched the VM's hash and every regular tar member was
read back. Adjacent `archive-verification.json` records that verification.
The task VM was then gracefully shut down and deleted; authoritative Tart
inventory confirms the unrelated running guest and templates remain intact.
No API credential was copied into the model worker. VM153's reader remains
active and its actual `/healthz` returned HTTP 200.
Registry updates were read back: Orca revision 13, Bumble revision 46, reader
service revision 37. Re-fetch current records before any later operations.

Archive paths correspond to the former `/Users/admin/comic-masks/` workspace:

- `shadowb-first/`, `koharu-first/`, `koharu-py313/`: all twelve-page outputs.
- `sam2-single/`, `sam2-single-copy/`, `sam2-multi/`: six cases each;
  `sam2-semantic/`, `sam2-semantic-point-only/`: five cases each.
- `inputs/`, `seeded-inputs/`, `control-proposals/`, `ownership-points/`, and case
  manifests: immutable inputs and automatic proposal/point provenance.
- `weights/`, `installed-source/`, dependency freezes, `logs/`, `executed-source/`
  and `render_*.py`: pinned checkpoints, installed model code, tests, warnings,
  actual runners and diagnostic-image generation. Python environments themselves
  are excluded. The older standalone `sam_probe.py` was preparation-only; use
  the executed-source/run hashes rather than assuming it ran.
- `mask-repeat-equivalence.json`: per-mask hash comparisons for 195 Koharu
  masks and 45 SAM writable-copy repeat masks, all equal. This does not assert
  general cross-version equivalence of logits, boxes or scores.

Specialist runner SHA-256:
`136ecff6de7f913dc3e0eae286ff9783b7424bd45499decf9569f899c8c2993d`.
SAM writable-copy box runner:
`bf0a8facce7089eddec99671be85f6da1088ae17f94d69f859b9123f2c7fcae3`.
The exact earlier semantic-with-box source is preserved and verified against its
run-recorded SHA-256
`0cd0d02dddecd4e8f8d83e169a185a86aa727cd960acdffcfa9b7d0d11347228`;
the final point-only run records the later runner hash separately.

The separate seeded-boundary archive remains
`seeded-boundary-spike-20261009/final-evidence.tgz`, 42,616,341 bytes, 309 members,
SHA-256 `b765ef0b3ea64dc6b30b8d685e2462bf36e60c4187245f65c8fb69f04070cc65`.
Keep all earlier archives; this worker export does not replace the historical
PDF/converter/cached-request evidence.
