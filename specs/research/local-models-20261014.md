# Local models for comic segmentation (2026-10-14)

Question from Chris: can local models replace the paid OpenAI calls? Two zero-API-cost experiments, both on
home-lab hardware. Evidence is under `validation-artifacts/local-judge-experiment-20261014/` and
`validation-artifacts/dragon-finetune-20261014/`.

## 1. Local vision model as the crop judge (Orca, M4 32GB)

- Model: `qwen3-vl:30b` on Orca's shared Ollama, `think: false`, temperature 0, schema
  `{reason, edges[], clipped_probability}`.
- Cases: the same 198 crops as the decision-model test (99 that Astra judged clipped, 99 that Astra kept).
  Each case sends the full page with the target outlined plus the crop itself.
- Result: **AUC 0.525 (chance)**. It answered 0 or 100 only, and said "complete" for 181 of 198 crops.
  It flagged 11% of Astra-clipped crops, with a 6% false-alarm rate. Mean time was 32 s per crop.
- For comparison, the paid Luna edge-strip predicates scored AUC 0.733, and neither approach is safe as an
  Astra replacement.
- **Rejected.**

## 2. Fine-tuned panel detector (Dragon, RTX 3080 10GB, disposable LXC 201)

The earlier zero-shot detectors were all rejected for quality, not speed: Magi, YOLOv12x at 640 and 1280,
YOLO26n and Pannello. So the GPU was used to fine-tune instead.

- Base model: `mosesb/best-comic-panel-detection` (YOLOv12x).
- Training data: the accepted automatic output for source pages 139–257 (97 train pages and 13 val pages,
  where every 8th page is val; whole-page fallbacks excluded).
- Test data: the personally reviewed segmentations for source pages 1–138 (675 boxes; 21 whole-page
  splashes scored as one full-page box). None of these pages were trained on.
- Training settings: imgsz 1024, batch 4, 150-epoch budget with patience 30. Each epoch took about 13 s and
  used 7.3 GiB of VRAM.
- Metric: a page counts as exact when the predicted box count matches the reviewed count and every reviewed
  box is matched at IoU ≥ 0.85.

| Model on reviewed pages 1–138 | Conf | Exact pages | Count correct | Recall@0.85 | Precision@0.85 |
|---|---|---|---|---|---|
| Zero-shot YOLOv12x comic | 0.05 (val) | 5 / 138 | 28 | 0.401 | 0.404 |
| Fine-tuned | 0.15 (val-chosen) | **26 / 138 (19%)** | 44 | 0.782 | 0.629 |
| Fine-tuned, threshold tuned on test (diagnostic only) | 0.5 | 48 / 138 (35%) | 81 | 0.754 | 0.760 |

Findings:

- Fine-tuning roughly doubles panel recall at the strict IoU and multiplies exact pages by 5×.
- The dominant remaining error is **over-prediction**: 86 of 138 pages have extra boxes, with 169 overlapping
  pairs among the predictions.
- The 13-page val set chose too low a threshold. Even a perfect threshold caps out near 35% exact pages,
  because about 22% of reviewed panels are never localized at IoU ≥ 0.85.
- Weights SHA256: `4399ba541858f321e57298293a264692af52c3cace64928a39f59dc1a3111915`.

## Conclusion

- Neither local model can replace the paid pipeline's quality.
- A fine-tuned detector could serve as a free first proposal, with the existing cheap verification accepting it
  and Astra reserved for rejections. On this evidence it would only help on roughly a fifth to a third of pages,
  mostly the easy pages that are already cheap.
- Next levers, if pursued:
  - more training pages from other comics;
  - containment/duplicate suppression tuned on a larger val set;
  - a hybrid run that measures actual API dollars saved per page.
