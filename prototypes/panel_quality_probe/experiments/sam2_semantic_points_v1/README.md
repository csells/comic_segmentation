# Automatic semantic-point SAM experiment — executed, unqualified

Hypothesis: exclusive scene-owned points resolve the ambiguity that makes a
box-only SAM mask join neighboring narrative scenes. This runner makes **no API
requests**. The parent workflow generates and accounts for ownership manifests
separately; model-generated points must never be replaced with human corrections.
This is a diagnostic, with no reader/converter integration.

Run only in the authorized disposable CPU VM. Keep this directory beside
`sam2_refiner_v1`: the runner imports that spike's checkpoint pins, integrity
helpers and corrected inclusive-corner-to-half-open coordinate mapping. It also
records the exact helper-file hash. Use the same pinned, noneditable Meta SAM
installation described in [the box-only README](../sam2_refiner_v1/README.md).
Ten point-validation tests passed inside the VM. Box-plus-point and point-only
variants each completed 39 targets across five cases. Automatic points improve
some scene separation, but neither configuration passes content-completeness
checks. Three separately accounted Astra point requests cost $0.577250; neither
SAM run made paid calls. See the
[measured report](../../../../specs/research/specialist-mask-spikes-20261009.md)
for exact failures and verified exported evidence. The temporary worker has
been deleted after export; recreate an authorized isolated environment to run
a genuinely new experiment.

```sh
python -m unittest discover -s /path/to/sam2_semantic_points_v1 -p test_points.py -v
python /path/to/sam2_semantic_points_v1/probe.py --cases semantic-cases.json --output semantic-points-first --weights-dir weights
```

The separately named `--omit-box` ablation keeps saved boxes for provenance and
diagnostics while sending only the frozen positive/negative points to SAM.
It recovers more of the bouquet but drops other required content and remerges
neighboring scenes. Do not select between configurations using review labels
or treat a retained seed as proof of complete content.

## Immutable input contract

Every case extends the existing box-only case manifest with a point manifest and
its exact baseline single-mask result file. Paths resolve against the case
manifest. Populate actual hashes; the placeholders below cannot run.

```json
{
  "version": 1,
  "cases": [{
    "id": "page57-original",
    "source": "inputs/0057.jpg",
    "source_sha256": "ACTUAL_SOURCE_HASH",
    "proposals": "proposals/0057-original-bundle.json",
    "proposals_sha256": "ACTUAL_BUNDLE_HASH",
    "points": "points/0057.json",
    "points_sha256": "ACTUAL_POINT_MANIFEST_HASH",
    "baseline_result": "baseline/page57-original/result.json",
    "baseline_result_sha256": "ACTUAL_BASELINE_RESULT_HASH"
  }]
}
```

The baseline result binds each native NPZ by SHA256. The runner verifies the
baseline source hash, proposal hash, source dimensions, panel order and exact
half-open prompt box, plus the native NPZ's prompt box. It accepts only one
finite source-resolution baseline mask per target. All cases for one source
must reuse exactly the same point-manifest hash; original and repaired boxes
therefore receive the same page-level semantic information. Approximate
normalized-box fallback is not allowed in this spike: use saved bundles with
inclusive corner points and a matching original source hash.

Point-manifest schema:

```json
{
  "version": 1,
  "source_sha256": "ACTUAL_SOURCE_HASH",
  "scenes": [
    {"order": 1, "exclusive_points": [[250, 350]], "uncertain": false},
    {"order": 2, "exclusive_points": [], "uncertain": true}
  ]
}
```

These coordinates are schema examples, never fixture coordinates. The scene
inventory must exactly match the cached automatic proposals. Each scene can have
up to three points. Unambiguous scenes need at least one. Coordinates must be
finite numeric values strictly inside 0–1000, with no booleans. Source floats are
`[x * width / 1000, y * height / 1000]`, without integer rounding. Mask membership
uses the containing source pixel via floor. Exact duplicates and points mapping
to the same source pixel, including contradictory ownership across scenes, fail
explicitly. The generator should assign exclusively owned content only: shared
or uncertain art does not justify a point with exclusive ownership.

## Frozen prompting and selection

For each target:

1. If its scene has `uncertain: true`, record an abstention and make no SAM
   prediction. Never infer certainty from its baseline mask.
2. Use its one to three exclusive points as positives, including points outside
   the original box/mask where the semantic generator places them.
3. Examine points belonging to other unambiguous scenes. Include a point as a
   negative **only when the target's cached baseline mask contains its pixel**.
   Points from uncertain scenes are never negative prompts.
4. Pass the unchanged saved box, positive/negative points, full-page embedding
   and `multimask_output=False` to SAM. No manual selection, iterative point
   repair, threshold tuning or outcome-dependent retries occur.

Each unique source is embedded once and reused across proposal sets. The model
can extend beyond the box; masks are not clipped to it. Full-resolution logits,
low-resolution logits, quality score, actual float32 prompt arrays and labels are
preserved per target. JSON preserves normalized/source coordinates, owner IDs,
baseline binding and every positive/negative choice. Outputs include binary
masks, mask overlays (green positives, magenta negatives, red box), source bounds,
diagnostic union-window crops and added/removed pixels versus the baseline.

Point retention/exclusion checks are initialization-compliance diagnostics;
they do not certify semantic correctness. Model quality scores are not scene
ownership probabilities. Record ownership-generation mistakes separately from
SAM failures despite correct ownership points. Count uncertain targets as
abstentions, never successful segmentation. Planned source set: 40, 57 and 150,
with saved original/repaired controls for 57 and 150; all are development cases.

The runner records effective torch threads, dependency versions, import/load and
embedding/prompt timing, source hashes and process-lifetime RSS. It does not
account for the separately authorized ownership API requests or claim $0 total
experiment cost.
