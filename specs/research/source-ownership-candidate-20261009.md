# Source ownership and reading viewports — candidate V29

The candidate separates two questions: which scene owns visible content, and whether its actual reading crop preserves that content. Neither a detector caption nor an attractive mask answers both. V29 is implemented for testing, **not qualified for the full PDF or promoted to the reader**.

## Frozen experiments

The controls use the original clipped lower crop on source150, corrected150, and the final V28 source57 inventory. Gold labels and visual review stay outside model requests. The plausible-wrong-caption control uses an actual saved Sol detector description; the omission control removes only its phrase “flower-decorated,” without adding a human-corrected story.

| Experiment | Measured result | Calls and usage estimate | Decision |
| --- | --- | --- | --- |
| V2, Sol source audit | Four audits returned structurally complete evidence. On original150 and phrase-erased150, Sol repeated the wrong attribution of the bouquet to the carriage. The first crop check accepted the defective lower crop; six later checks were skipped. | 5 new calls, $0.174907 | Failed ownership/completeness control; terminal. |
| V3, Astra source audit, same prompt | All three150 audits correctly identified the airborne bouquet as lower-scene content despite misleading or incomplete detector hints. The13scene57 audit returned incomplete after8192 output tokens,7682 of them reasoning. No crop controls ran. | 4 new calls, $0.958502 | Useful source evidence; crop gate still untested. Capacity failure preserved. |
| V4, generic scene-count allowance | Reused the three completed audits exactly. The13scene request now allows17408 output tokens; provider rejected it with HTTP429 `credit_balance_exhausted`. No crop controls ran. | 3 cache hits; 1 rejected dispatch; $1.620400 reservation retained conservatively | Blocked by provider credits, not the project cap. Terminal run must not be blindly relaunched. |
| V5, explicit funded recovery | After Chris restored credits, reused the three completed audits and recovered only the named quota rejection. The13scene audit completed, and all seven fixed crop controls returned the expected outcome: three clipped controls rejected and four intact controls accepted. Independent image/reason review supports these narrow results. | 8 new calls, 3 cache hits; $0.724016 | Controls passed; actual automatic V29 regressions are the next gate. |

After V5, shared used/held is **$42.851332 of $100**. This includes unchanged **$4.30 old unknown holds** and the separate **$1.620400 reservation for the original explicit quota rejection**. These are conservative accounting records, not a claim that OpenAI charged for that rejected request. Provider credits are restored. V5 is terminal and must not be replayed; actual automatic regression runs may reuse its completed responses through the normal cache. The handoff and live ledger own later spending.

Output capacity is now generic: up to4 scenes retains8192 tokens and unchanged cache fingerprints; larger inventories use `max(8192, min(24576, 4096 + 1024 × scene_count))`. The verifier reserves the full configured output limit, including reasoning, before dispatch. An incomplete response cannot become source evidence or crop approval. The source prompt and page pixels did not change.

## Candidate behavior

`OwnershipConverter` extends the existing bounded controller. Ordinary layouts retain its prior checks. Risky overlap/crossing layouts require a source-only Astra audit bound to source bytes, ordered proposal, descriptions, model, prompt and exact request. Valid evidence identifies scenes and supporting visual ownership cues. Missing, uncertain, stale, malformed or inventory-changing evidence escalates.

A structurally valid source audit is only a prerequisite. Risky candidates also require a complete-candidate Sol-high confirmation and marked source-detail checks for every overlapping, crossing or otherwise flagged crop. Native-model approval cannot bypass these checks. Independent layout, split, inventory and global failures remain binding. Descriptions enter only the source audit and explicitly fallible auxiliary evidence; ordinary geometry fields contain no hidden gold labels.

A geometry repair can inherit an audit only through explicit saved ancestry, the same source/inventory/order/direction, and monotonic expansion relative to both its immediate parent and original audited proposal. A new detector inventory requires a fresh audit. There is no per-page winner table or runtime human review.

The reading margin expands each crop edge by at most1% of the shorter page dimension and5% of that crop axis, with outward integer rounding and page-edge clamping. It applies once per repair lineage and preserves scene order. It is a reading viewport, not a segmentation mask. The [fresh source audit](page57-v28-independent-audit-20261009.md) reviewed all13 padded57 crops and all3 corrected150 crops before inference. The padded original150 lower crop still omits substantial bouquet content and remains a required negative control.

## Supporting integration fixes

The current candidate also canonicalizes unsupported still-image formats and EXIF orientation while retaining original bytes; keeps transparent publication pixels and uses a recorded white matte for JPEG analysis; binds preceding-page context to actual analysis paths; validates analysis-cache hashes on resume; carries explicit/automatic LTR/RTL through parsing, refinement and repair; and supports one-page output without duplicated art. Reader direction uses an optional hash-bound companion profile because ACBF1.1 has no standard direction field. These changes require separate transport and browser qualification; they do not imply correct segmentation.

A narrowly explicit quota-recovery path passed its offline safety tests and the live V5 recovery: only a named request with a recorded HTTP429 credit-balance rejection received one separately reserved retry after funding. Completed results remained cached, unknown/time-out requests do not qualify through this path, and the original reservation was retained. V5 used the same seven crop controls and unchanged V4 request bodies. All180 offline tests pass; source and test logs are archived. The complete13scene response used9108 output tokens, including6589 reasoning, and took253.4s. The larger allowance resolved that capacity failure; it is not a latency guarantee.

## Remaining qualification

1. The seven frozen crop controls passed with exact cache reuse and independent visual/reason review. Preserve the [evaluation report](ownership-viewport-v5-review-20261009.md), including its noun-level uncertainty in one source description; no human labels enter runtime requests.
2. Run actual V29 conversion of the difficult source pages and intact regression pages without supplying saved winning geometry. Inspect every final crop and the emitted CBZ in the reader.
3. Freeze the passing policy before the [independent12-unit source screen](independent-fixtures-20261009.md); expected inventory is [separately frozen](independent-source-audit-20261009.md). Any book used for tuning ceases to be independent evaluation.
4. Requalify affected earlier outputs and continue the entire257page PDF sequentially. Current historical qualification remains1–56, page57 fallback underV28, older review through150; no151 inference.

See the [handoff](../handoff-comic-panel-cli.md) for immutable run paths, archive hashes and lifecycle state. The completed broader [spike inventory](spike-closure-20261009.md) distinguishes failed tested configurations from conditional literature leads. Preserve failed results and existing Build10; Rust production work and promotion remain unstarted.
