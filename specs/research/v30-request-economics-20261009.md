# V30 request economics: source 57 and 150

2026-10-09. **The accepted source-57 path depends on 134 distinct successful requests priced at $4.420136 by the research ledger; source 150 depends on 21 priced at $0.584057.** These reconstruct the cost of the exact saved successful responses, including responses first paid for in earlier runs. They are more useful for planning than incremental spend alone, but are not measured cold conversions, provider invoices or ordinary-page averages.

## Reconciled scope

The audit collected every distinct request ID referenced by the two accepted page records, including rejected intermediate candidates, source audits, native checks, model verifiers and repairs. It found all 155 saved requests, response-usage records and timings, with exactly one reservation and settlement per successful dependency. Every current-run new reservation appears in its page trace; none was omitted. Repeated trace references were deduplicated by request identity rather than charged again.

All saved input/output totals agree with the corresponding ledger usage, and recomputing each cost at its recorded rates reproduces every settlement. Native Decisions outputs have zero output tokens as expected. Responses records report completion, valid token totals and the expected model. The pricing calculation uses gross input tokens without provider cache discounts and includes all billed output tokens, including reasoning. One source-57 response records 3,388 provider-cached input tokens; the ledger still prices them at the gross rate. This report verifies the historical pricing calculation, not today's price schedule.

| Measure | Source 57, 13 scenes | Source 150, 3 scenes |
| --- | ---: | ---: |
| Actual new paid requests in V30 invocation | 34 | 17 |
| Actual Client cache hits | 129 | 6 |
| Actual incremental ledger usage | $1.155186 | $0.451539 |
| Recorded elapsed conversion time, with caches | 633.483 s | 201.034 s |
| Distinct successful dependencies | 134 | 21 |
| Gross ledger price of those dependencies | **$4.420136** | **$0.584057** |
| Dependency cost first incurred before this invocation | $3.264950 | $0.132518 |
| Sum of each dependency's historical request duration | 2,273.945 s | 251.029 s |

The last row is **not cold wall-clock latency**. Requests were originally issued at different times, some native work runs concurrently, and these per-request timers omit input-token preflight and local preparation. Future service time, outputs, escalation and transport failures may differ. It would be misleading to call either the cached invocation's elapsed time or the historical duration sum a measured cold conversion.

The Client counts cache hits per access, not per distinct dependency. The source-57 trace describes 163 logical request accesses: five detector/repair calls, two fresh source-inventory audits, 108 native checks and 48 Sol verification calls. The 108 native checks contain only 79 unique identities, accounting for 29 same-invocation reuses. Thus its 129 hits combine 100 distinct prior responses and 29 repeated accesses. Source 150 has 23 accesses but 21 identities: its six hits combine four distinct prior responses with two repeated native checks. Inherited source-evidence references and duplicate selected/raw candidate fields are provenance references, not extra dispatches.

## Where the cost and time went

| Successful dependency category | Source 57: count / price / recorded duration sum | Source 150: count / price / recorded duration sum |
| --- | --- | --- |
| Native Decisions checks | 79 / $0.035999 / 37.0 s | 12 / $0.004474 / 13.7 s |
| Sol-low detector | 1 / $0.016588 / 11.9 s | 1 / $0.012908 / 10.2 s |
| Sol-high detector | 1 / $0.074968 / 90.0 s | 1 / $0.025408 / 26.0 s |
| Astra detector and geometry repairs | 3 / $1.008376 / 420.8 s | 1 / $0.093988 / 20.5 s |
| Astra source-inventory audits | 2 / $1.233288 / 552.7 s | 2 / $0.348901 / 150.3 s |
| Sol-high ownership-aware verification | 48 / $2.050917 / 1,161.5 s | 4 / $0.098378 / 30.4 s |

Source 57's 48 Sol checks comprise four whole-candidate checks and 44 marked targets across the detector and two repair stages; the first Sol-high stage stops after target 5 fails. Subsequent Astra stages retain all required targets. The two repairs' generation alone costs $0.601838 within the Astra row; their downstream checks are additional. The source-57 target-10 warning is a confirmed false positive, but the separate target-4 warning has not been adjudicated, so the entire second repair's cost cannot be classified as waste.

The two dense source audits took 275.4 and 277.3 seconds and each consumed 11,460 output tokens within the 17,408-token allowance. Source 150's audits took 68.8 and 81.5 seconds. Source 57's 48 Sol verifiers had a 21.5-second median and 56.0-second maximum; source 150's four ranged from 5.3 to 11.8 seconds. These observed tails support durable progress/checkpoints and timeouts that allow qualified long responses. They do not justify arbitrary increases in token capacity or model attempts.

## Unresolved failure cost and interpretation

Source 57's Astra detector is an explicitly recovered response, ID `c8e86b8de517f60c7e09525359c7dec7e1943d126a8509630e6bb473ea1196da`, for original request `eaba5225368880b59d2536d1b10fb0275f3c256a1e54b6918a6ecb49f7407ca4`. The successful recovery costs $0.406538 and is counted once in the dependency total. The original request retains a separate **$0.700000 unsettled hold** in the global ledger. It is not another successful dependency and is not assumed free, billed in full, or automatically retried. Actual provider cost of that failed attempt is not identifiable from a reservation.

The separately preserved parent metadata confirms a recorded read timeout, one reservation, no settlement, and no saved response or timing file. Its elapsed time and actual token usage therefore cannot be added to a measured cold-latency or settled-cost total.

Consequently, $4.420136 is a conditional successful-path reconstruction: what the saved responses cost at the ledger's gross rates if obtained once each. A fresh page can fail, generate different geometry or take a different route. The unresolved parent hold and unrelated research experiments remain accounted globally rather than being hidden inside this estimate. Neither page provides a representative cost distribution for a full comic.

## Implications for the Rust plan

- Persist one immutable request identity, payload/model policy, response, usage and timing per dispatch; link every candidate/repair verdict to that record. Report cache accesses separately from unique responses and new reservations.
- Budget the complete page dependency graph: source audits, native checks, whole-candidate and marked targets, bounded geometry repair and all required rechecks. A two-request estimate is untenable for these paths. A $4/64-request bound would stop the reconstructed source-57 path; that can be an honest product limit, but not a promise of completing it.
- Reserve under the shared lock before dispatch and account for simultaneous outstanding holds as well as final token usage. Three native requests can temporarily reserve $3 even though their eventual charges are much smaller. A page limit equal to its final reconstructed cost does not guarantee sufficient reservation headroom.
- Preserve exact cache reuse and immutable ancestry. Optimizations must prove that the complete input and evidence obligations are unchanged; an unchanged crop alone does not make a check equivalent after global context changes. Any reduced verification policy needs fresh defect-control qualification.
- Measure cold wall time and success/fallback cost across independent pages when needed; do not repeat these paid paths solely to obtain a cold benchmark. The saved evidence already identifies source-audit and repeated Sol-verification work as the major costs on the dense example.

## Evidence

The page/CBZ identities are bound by the [source-57 report](actual-source57-v30-validation-20261009.md) and [source-150 report](actual-source150-v30-validation-20261009.md). Read-only metadata export:
`validation-artifacts/segmentation-iteration-20261008/source57-150-cached-request-audit-20261009/source57-150-cached-request-audit-20261009.tgz`, SHA-256 `a2fb876b0278477d9e658cddf7c54ecee62b23b14aea15729092c2689fd274f6` (466 regular members, fully read by the exporter).

Its manifest records the exact source hashes, reserve/settle rows, request/response/timing file hashes and missing-file checks. The compact response export excludes model output and encrypted reasoning. The independent join, recomputed costs and per-request timing table are in sibling `independent-cost-analysis.json`, SHA-256 `33203f33736b5b8fcc5fe2151777ff31b08922a5cbec5162c07933fd6c1a536f`. No API calls, converter replay or ledger mutation were used for this audit.

The failed-parent export is sibling `source57-failed-parent-metadata-20261009/source57-failed-parent-metadata-20261009.tgz`, SHA-256 `613098e107b3a451d7b333ec9e7a08b199d54043b86360389322a5a032f7d29b` (three regular members, fully read by the exporter). Its manifest explicitly records the missing response/timing rather than imputing zeros.
