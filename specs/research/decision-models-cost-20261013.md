# Decision models for cutting per-page segmentation cost (2026-10-13)

## Question

Can a "System One" decision model (typed answers, no generated text) replace the expensive
`gpt-6-astra` / `gpt-6-sol` Responses calls that dominate the prototype's cost?

## Where the money goes (measured, batch sources 125–257, $124.27 across 133 pages)

| Pages resolved by | Pages | Share | Spend | Per page |
|---|---|---|---|---|
| First Sol tier | 57 | 43% | $2.63 | $0.05 |
| Second Sol tier | 32 | 24% | $17.41 | $0.54 |
| Astra tier | 17 | 13% | $28.68 | $1.69 |
| Astra plus repair | 14 | 11% | $48.70 | $3.48 |
| Whole-page fallback | 13 | 10% | $26.85 | $2.07 |

By request type: Astra crop verifiers $54.05 (340 calls, $0.16 each), Astra ownership audits
$36.71 (117 calls, $0.31 each), Astra detectors $16.02 (65 calls). The prototype's existing
decision-model calls (`gpt-6-luna` via OpenAI's Decisions endpoint) cost $0.80 for 1,886 calls,
about $0.0004 each.

## Options

| Model | Images | Input price per M tokens | Notes |
|---|---|---|---|
| TypeSafe Jev (jev-1.13) | **No.** State is "a simple string or structured object" | $0.042, output free | Fast (70–500 ms vendor figure). Documented weaknesses: counting, large or noisy state, numeric/RGB closeness, first-option bias in choices, prompt injection. |
| OpenAI Decisions API (`gpt-6-luna`) | Yes, inline base64 data URLs only | $0.10, output free | Public beta since 2026-10-06. Already used by the prototype for predicates. |
| Cloudflare Clef / Clef-flash | Yes, up to 4 images per request | $0.09 (flash) / $0.24 | Vendor-reported latency 39 ms / 209 ms. Not yet evaluated here. |

## Conclusions

1. **Jev cannot replace the image checks.** Every expensive call judges source pixels and crops
   (clipping, ownership, scene inventory). Jev is text-only, so it could only take text-only
   routing decisions, which already cost almost nothing here.
2. **The real lever is turning more Astra verdicts into image-capable decision predicates**
   (OpenAI Decisions/Luna, or Clef). A predicate costs about $0.0004 against $0.16–0.31 for an
   Astra call. If accuracy holds, per-page cost on hard pages could drop by one to two orders of
   magnitude.
3. **Accuracy must be measured, not assumed.** The prototype has a natural evaluation set: pages
   1–138 personally reviewed, plus hundreds of recorded Astra verdicts with known outcomes
   (confirmed clipping, false alarms, ownership resolutions). The next experiment is to replay
   those cases as decision predicates (for example "does crop N contain all artwork of its scene
   at every edge?") and compare them with the Astra verdicts and the root reviews.
4. **Independent of model choice,** a per-page spend limit with a whole-page fallback bounds cost:
   at about $0.15 per page this book would cost about $15–25, with the hardest roughly 30% of pages
   shown whole-page.

## Experiments (2026-10-13)

Labels are recorded Astra target-crop verdicts (clipped_art/clipped_text = clipped, keep = good). Astra is a
proxy for truth, not ground truth; root reviews found occasional Astra false alarms (for example source128).

1. **Existing generic Luna predicates (free, recorded data):** 1,021 crops (63 Astra-clipped). The pipeline's
   own `art_clipping`/`text_clipping` probabilities reached AUC **0.61**. At threshold 0.3: 70% of Astra's
   clippings caught, 53% false alarms on good crops.
2. **New edge predicates (`decision-edge-experiment-20261013`, $0.053 for 198 calls):** 99 Astra-clipped and
   99 sampled Astra-keep crops. One Luna Decisions call per crop: original page with the target outlined plus
   four zoomed edge strips with the crop edge marked, four yes/no "does the target scene continue past this
   edge?" predicates, score = max. AUC **0.733**. Threshold 0.2: 84% caught, 48% false alarms. Threshold 0.3:
   68% caught, 26% false alarms. Threshold 0.5: 34% caught, 14% false alarms.

**Result:** sharper questions on zoomed inputs help (0.61 → 0.73), but nowhere near Astra agreement. Used as a
replacement, the decision model would either let a third of real clipping through or reject a quarter to half of
good crops. Not a safe Astra substitute for this task with today's model. Cost per call (about $0.0003) makes
it attractive only as a pre-filter whose errors the rest of the pipeline can absorb.

Artifacts on VM153: `evidence/decision-edge-experiment-20261013/{experiment.py,cases.json,results.json,summary.json,calls/}`.
Script copy: `validation-artifacts/segmentation-iteration-20261008/helpers-20261013/decision-edge-experiment.py`.

## Sources

Primary:
- [TypeSafe quickstart](https://docs.typesafe.ai/introduction/quickstart): input is "a simple string or structured object".
- [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13): documented weaknesses.

Secondary (verify against vendor rate cards before relying on prices):
- [InfoQ: TypeSafe AI releases Jev](https://www.infoq.com/news/2026/10/typesafe-ai-jev-released/)
- [Developers Digest: OpenAI Decisions API vs Jev vs Clef](https://www.developersdigest.tech/blog/openai-decisions-api-vs-jev-vs-clef-2026)
- [OpenAI opens Decisions API, adds image input](https://app.dealroom.co/news/note/openai-opens-decisions-api-to-all-developers-adding-image-input-in-challenge-to-typesafe-s-jev)
- [Check Point: prompt injection against Jev](https://blog.checkpoint.com/ai-security/jev-is-not-a-language-model-but-it-breaks-like-one-prompt-injection-against-a-typed-decision-model/)
