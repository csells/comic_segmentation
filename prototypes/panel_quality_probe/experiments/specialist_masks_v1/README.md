# Specialist mask comparison — executed development screen

Question: do specialist instance masks recover curved boundaries, insets, and
crossing content that our semantic box proposals miss?

Run only inside a disposable VM. Chris approved the concurrent isolated Orca
clone `orca-automation-comic-masks-20261009`, where both twelve-page runs completed.
See the [measured report](../../../../specs/research/specialist-mask-spikes-20261009.md).
Do not use the host Python/model runtime.

Use separate virtual environments for the two comparators. Install
`ultralytics==8.4.43` for ShadowB, or `rfdetr==1.7.0` and `safetensors>=0.5` for
Koharu, plus Pillow. Save the full resolved dependency versions. The model cards
and loader were inspected; repository revisions and weight SHA256s are pinned in
`probe.py`. The script reproduces recommended thresholds/resolution, forces CPU,
and retains native postprocessed binary masks for every class. It does not infer reading order.

```sh
python probe.py shadowb --input inputs --output shadowb-first --weights-dir weights
python probe.py koharu --input inputs --output koharu-first --weights-dir weights
```

Prepare identical saved original JPEGs for pages 5, 18, 21, 25, 40, 57, 72, 100,
144, 150, 254, and 256. This is a development screen, not held-out qualification.
Output directories must be new. Existing weight files must match their pinned
hash; partial downloads require inspection before recovery. Save errors rather
than silently changing a model, resolution, or threshold.

Inspect full sources, all panel masks, and proposed bounds. Record missing/merged/
split panels, inward clipping, unrelated scene intrusion, and balloon ownership.
Correct count is insufficient. Compare cold model-load time, per-page inference,
and peak RSS separately; local inference has no additional API charge but consumes
compute. Do not integrate a winner or alter the reader on the strength of this
screen alone. Frozen held-out books and actual automatic E2E validation follow.

Model loading and all twelve predictions passed for both configurations, with
source-sized masks. Neither configuration passes the quality screen. Koharu
was repeated on Python 3.13 after a Python 3.14 compatibility warning; all 195
returned binary masks were byte-identical. Saved freezes, logs, checkpoints,
rendering helpers and outputs support the report. ShadowB may override the
requested torch thread count during CPU selection; effective threads were not
recorded. This limits the timing comparison, not the observed structural failures.
