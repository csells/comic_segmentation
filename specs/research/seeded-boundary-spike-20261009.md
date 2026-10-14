# Automatic seed-based boundary reconstruction: bounded offline spike

**Decision: reject these configurations for automatic panel isolation or clipping
repair.** They are fast enough to be useful proposal generators, but pixel
connectivity and color alone do not establish narrative ownership. No runtime
policy, stored converter output, paid ledger, or reader build changed.

This is a four-page development screen, not a benchmark against pixel annotations
or held-out comics. Counts below refer to saved automatic proposals, not asserted
ground truth. Thirty-two variants completed with **zero API calls** in disposable
VM153 using its existing OpenCV 5.0.0, numpy, and Pillow environment. OpenCV was
restricted to one thread. Source images were 1128 × 1648 pixels.

## Question and bounded experiment

Can source pixels and existing automatic rectangles provide foreground/background
seeds that recover pale curved tips while excluding neighboring scenes?

The probe in
[`experiments/seeded_boundary_v1/probe.py`](../../prototypes/panel_quality_probe/experiments/seeded_boundary_v1/probe.py)
uses no hand coordinates, seeds, scene labels, page identifiers, or personal-review
findings as algorithm input. It:

1. Builds connected components from pixels whose minimum RGB channel is below
   245, with optional morphological opening radii 0, 3, or 7 pixels.
2. Selects significant components contained at least 85% inside an automatic
   proposal. Comparable alternatives and components selected by competing
   proposals cause an explicit abstention.
3. Erodes accepted components to form foreground cores. Near-white areas eroded
   by a 7 × 7 kernel provide background seeds; other selected component cores are
   competing seeds.
4. Runs multi-marker watershed on a lightly blurred source and independently
   runs three-iteration GrabCut within a source-scaled expanded region.
5. Saves masks, source overlays, isolated images, exact input hashes, bounds,
   retained seed pixels, and competing-core intrusion counts.

Initial matching ranks contained pixel support and abstains when the runner-up
has at least 70% as many supported pixels. A second generic variant ranks
component-bound/proposal IoU, requires IoU ≥ 0.5, and abstains when the runner-up
score is at least 90% of the first. The second variant uses radius zero and the
same four pages. All thresholds are experimental heuristics, not calibrated
confidence estimates.

The observable quality condition was complete target art with no merged or
foreign scene, checked against the unchanged full source. A completed algorithm
run, retained seed, or apparently neat outline does not satisfy that condition.

## Measured results

| Source page | Saved proposals | Pixel-support seeds, radii 0 / 3 / 7 | IoU seeds, radius 0 | Main limitation |
| --- | ---: | ---: | ---: | --- |
| 57 | 13 | 6 / 6 / 5 | 10 | Caption bridges join distinct narrative regions; similar colors leak across regions |
| 25 | 6 | 1 / 1 / 1 | 1 | Connected/inset compositions do not yield independent component seeds |
| 40 | 7 | 5 / 5 / 5 | 5 | The lower component includes multiple narrative views |
| 150 | 3 | 1 / 1 / 1 | 1 | Lower regions share connected artwork; bouquet ownership remains unresolved |

Across completed variants, watershed itself took about **0.053–0.091 seconds**
per page, excluding seed extraction and image export. GrabCut took about
**0.371–3.497 seconds** for all seeded targets on a page. These timings omit
unseeded targets and are not end-to-end conversion or production throughput
measurements. Seed extraction took roughly 0.059–0.126 seconds.

Opening did not resolve the caption connections and lost an additional usable
seed at radius seven. Better component-box matching increased page 57 coverage,
but did not fix semantic errors in the components themselves.

## Personally inspected counterexamples

The original source pages, component-label visualization, page overlays, and
selected individual masks were inspected. These counterexamples are sufficient
to reject this screen; they do not imply every generated mask received a full
pixel-level acceptance review.

- **Page 57, target 7:** both watershed and GrabCut preserve the pink upper-left
  strip *and* the yellow lower-left strip in one mask. A caption connects those
  colored regions, so the automatic hard-foreground seed already spans two
  narrative views. Morphological opening through radius seven does not solve it.
- **Page 57, target 4:** IoU-initialized GrabCut admits a large disconnected piece
  of the unrelated brown upper scene. Its mask bounds extend left to x=698,
  beyond the x=742 proposal, adding 7,511 pixels outside the proposal. The
  unrelated scene has a similar color and no accepted competing seed.
- **Page 57, target 10:** both methods' mask bounds start at x=736, *inside* the
  saved proposal's x=733 left edge. They do not repair the disputed pale tip.
  Visually attractive isolation is therefore insufficient evidence of a correct
  boundary. This spike does not settle whether every pale exterior pixel is art
  or a scan halo.
- **Page 57, target 8:** watershed and GrabCut reach x=753 versus the proposal's
  x=754. That one-pixel extension is not proof that the full cyan taper is present.
  The method also drops some component-boundary pixels.
- **Page 40:** the seed assigned to the large lower composition also contains
  adjoining strip views. A connected object is not equivalent to one narrative
  panel.
- **Page 150:** both lower proposals are skipped. No conclusion about the
  bouquet's scene membership follows from the successful upper-panel mask.

For the page-57 IoU variant, both algorithms retain 100% of every accepted eroded
foreground core and include zero competing-core pixels. **Those apparently good
invariants coexist with the target-7 merge and target-4 foreign-art leak.** Hard
seed retention measures compliance with initialization, not correctness.

Page 25's saved bundle contains exactly six panel entries and no extra whole-page
entry. On fresh inspection, the bottom-left entry shows a foreground rider
approaching the viewer; the bottom-right inset shows a rider from behind moving
toward the abbey. This report treats them as the six supplied proposals and does
not convert that observation into a general ground-truth panel-count metric.

## Implication for the hybrid architecture

Keep these algorithms as possible inexpensive *boundary proposal* tools only
when a stronger semantic source supplies reliable instance seeds. Neither raw
components nor bounding-box containment safely provides those seeds on overlapping
comics. Every mask-based candidate still needs inventory, semantic ownership,
source-boundary completeness, and reading-order validation.

A learned instance-mask trial should specifically test the two caption bridges,
the repeated brown colors, the cyan/pink pale tips, and the crossing bouquet.
Do not integrate this spike into the converter, treat seed metrics as confidence,
or use its masks to replace existing accepted geometry.

## Exact provenance and portable evidence

VM run root:
`/home/tester/comic-reader/evidence/seeded-boundary-spike-20261009`.

The saved inputs are byte copies under that root's `inputs/`. `cases.json`, each
variant's `result.json`, both executed code versions, progress logs, source
images, masks, and assessment are retained. The current repository probe matches
the second executed version, SHA256
`4986b7dde99e13932a7f79cbe5ebebb3392a77bafc13a86231940fa1f8462922`.

All source files are `/home/tester/comic-reader/replay-local/pages/NNNN.jpg`:

| Page | Exact source SHA256 | Exact saved-bundle SHA256 |
| --- | --- | --- |
| 25 | `891cb81430ce12281c848f8025b8fb75aec4eeecc005312d04cb9c998938b14b` | `f6dc78ccad1364266efa9f7e3691fbf0931b31486b903f0e574dca877bf474b8` |
| 40 | `74388fa031f95c367c3d293458b1d6c50ce712e74674563ec5cf8f97f19aae25` | `1f8d40cef90dc88ff6b2605cefa735882e0fb65ad9f59200975d6db182b8d8fa` |
| 57 | `910bbb7a131122ea3a7b102ec40fbea4193758ecc2abfa16e793c48626cd34b1` | `b3aa2deb8ccf851a82e0caf10b40b128abfed3cbd351fa96f306050878031590` |
| 150 | `ce13e97dcf81deb016a7b3201c59d2ff1e07c0e1638cd8690fe8a1341d397e92` | `59c19d2f12a27b36c997e701949e486b1341c082365da294a09d20ca483cd822` |

The original bundle paths, relative to `/home/tester/comic-reader/evidence/`:

- 25: `full-sequential-v24-20261008/candidates/2bd96bc55c7d521d2542646067a77c71b8437092bec5130463165a205fe2585e/bundle.json`
- 40: `full-sequential-v24-20261008/candidates/c61591c9a41df0ab6ce4275fe2a85108a37f59f00497b7a5d65796f1bc6fdd19/bundle.json`
- 57: `component-repair-page57-v28-exact-20261009/candidates/b5cd08f0b5768683c1a6cd351598b4da2801bbe4504fa5914672fb3060f60a8d/bundle.json`
- 150: `crossing-art-regression-v23-20261009/candidates/336c8c32736fda4e69aaa3f5db415680ef9360cdada05395aa288b6d0b838871/bundle.json`

Portable off-VM archive:
[`final-evidence.tgz`](../../validation-artifacts/segmentation-iteration-20261008/seeded-boundary-spike-20261009/final-evidence.tgz),
42,616,341 bytes, 309 tar members, SHA256
`b765ef0b3ea64dc6b30b8d685e2462bf36e60c4187245f65c8fb69f04070cc65`.
The archive was fully read back and extracted successfully.

Useful exported review images under
`validation-artifacts/segmentation-iteration-20261008/seeded-boundary-spike-20261009/final/`:

- [`component-labels-57.jpg`](../../validation-artifacts/segmentation-iteration-20261008/seeded-boundary-spike-20261009/final/component-labels-57.jpg)
- [`bbox-page-0057/opening-0/grabcut-04-isolated.jpg`](../../validation-artifacts/segmentation-iteration-20261008/seeded-boundary-spike-20261009/final/bbox-page-0057/opening-0/grabcut-04-isolated.jpg): foreign brown scene
- [`bbox-page-0057/opening-0/grabcut-07-isolated.jpg`](../../validation-artifacts/segmentation-iteration-20261008/seeded-boundary-spike-20261009/final/bbox-page-0057/opening-0/grabcut-07-isolated.jpg): two narrative regions retained as one
- [`bbox-page-0057/opening-0/grabcut-10-isolated.jpg`](../../validation-artifacts/segmentation-iteration-20261008/seeded-boundary-spike-20261009/final/bbox-page-0057/opening-0/grabcut-10-isolated.jpg): attractive mask does not repair disputed left extent
- [`page-0040/opening-0/grabcut-overlay.jpg`](../../validation-artifacts/segmentation-iteration-20261008/seeded-boundary-spike-20261009/final/page-0040/opening-0/grabcut-overlay.jpg)
- [`page-0150/opening-0/grabcut-overlay.jpg`](../../validation-artifacts/segmentation-iteration-20261008/seeded-boundary-spike-20261009/final/page-0150/opening-0/grabcut-overlay.jpg)

No spike jobs remain running. The existing reader service remains active; the
last measured guest free disk space was 4,737,077,248 bytes. No credentials were
needed or copied, and no dependencies were installed.
