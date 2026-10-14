# Nested budget scheduling and source205 continuation

This records an orchestration fix, its offline qualification, and the subsequent successful source205 continuation. It does not change the frozen V30 segmentation policy, prompts, request payloads, model selection, source pixels, or production installation.

## Observed failure

Source205 stopped at 47 requests and $1.286989, with all 47 requests settled. The original case allowed $4 and 48 requests. The converter computed native concurrency from the global remaining budget and selected three workers. Three simultaneous $1 native reservations exceeded the case's remaining $2.713011, although two would fit. This was a guard-before-dispatch failure, not an unknown provider request or a geometry rejection.

The original terminal, requests, responses, root diagnostic review of the source and ten Astra crops, and ledger were preserved. Diagnostic crop review did not turn the blocked candidate into an accepted page or publication. The root evidence export is `actual-v30-sources144-56-100-and205-stop-20261009.tgz`, SHA256 `3007ab4bffd818f85d0567dc860d53ccd02ac1a6336ab27c0ee4f4fb63539064`.

## Bounded continuation

The root authorized a distinct continuation output under the existing regression suite, with the original and new source205 rows counted together: $4 and 160 requests cumulatively, inside the unchanged $20/480-request suite and $100 global ceiling. Thus 47 old requests remain charged and at most 113 additional requests fit the prospective case allocation. No retry flags are supplied. Successful cached responses remain available through the actual Client.

The wrapper first enters the real Budget, validating the original $100 ledger policy and taking its exclusive session lock. It then exposes `used + min(global remaining, suite remaining, case remaining)` as the effective scheduling cap. Since all subsequent reservations and settlements are restricted to the current case, all three remaining amounts change by the same delta. The unchanged converter sees two workers for the observed case. Explicit dollar, request-count, path, terminal, and unknown-reservation guards remain in force. The effective cap is restored on exit and is never written as a budget amendment.

## Cache proof and tests

The actual full-context source205 CLI ran once with a copied ledger, denied reservations, denied HTTP and socket access, and an offline placeholder credential. It reused 46 original successful responses plus one other historical cached response before two new native requests reached the denial boundary. Parallel cancellation left one later successful target check unvisited. The initial proof correctly failed its overly strict requirement that all 47 original successes must be reached before the first miss; that proof is preserved.

The unvisited check was target6, fingerprint `370676af7218d9dffa87ad0f1ea172a2d204c9f839783f5a6dcb3ced2939196f`. A separate probe reconstructed it with the actual OwnershipConverter's saved source-audit enrichment, unchanged target prompt/questions, and exact replayed bundle. Both the complete fingerprint and sanitized body matched the original before the real Client returned its cached response. An earlier probe using the base Converter omitted ownership hypotheses and failed before cache lookup; its files were also preserved. No whole CLI rerun was needed.

The final qualification therefore reports **46 original CLI cache hits plus one separate exact cache probe**, rather than claiming the CLI reached all 47. It also binds identical candidate geometry, original source bytes, all ten crop bytes and metadata, and unchanged shared/copied ledgers. The two requests actually missing from cache were:

- `ff34876a50447976bfcbdf42cb0c5c037b31b1c47e541c2d64d88773fecb8d27`
- `ff67e1d3cb4d99a383e60892438b8952c4f5aa4a7ae12402fd387bbe5553cfc9`

The source205 wrapper passed 15 initial VM checks, followed by 18 checks of the final V3 preparation. The latter include real Budget/Client behavior on disposable ledgers, inherited counts and costs, two-worker reservation/settlement throughput, original policy validation, scope and terminal denial, no credential lookup after readiness failure, dependency hashes checked before import, and negative cache-proof controls. These are focused wrapper checks, not a rerun of every application test.

## Actual continuation result

The root then dispatched the qualified continuation. Source205 was automatically accepted with ten panels after 16 new calls costing $0.304194, 49 cache hits, and 136.647 seconds. All ten selected crop hashes match the source/crops personally inspected in the earlier diagnostic review. The diagnostic did not supply geometry or a runtime verdict; the actual automatic checks completed independently before the root recorded acceptance. The new accepted review is VM `evidence/root-source205-accepted-review-v30-20261009.json`, SHA256 `9d4f93ed3af736e84602aff4837a50246295499923d2e80f6d5e6189887b6989`.

Old and new source205 requests total 63, all settled, costing $1.591183. No original successful request was paid again. At this checkpoint the global held/settled total was $51.353348 and the regression suite was 306 requests/$8.502016. These are checkpoint totals before subsequent prefix work. The actual source205 browser gate also passed all eleven overview/panel steps; its evidence is maintained in the development/browser reports.

## Restore and continuation

All paths below are under local `validation-artifacts/segmentation-iteration-20261008/` or VM `/home/tester/comic-reader/evidence/` unless noted.

- Frozen application: `candidate-v30-transport503-20261009/source`; manifest SHA256 `debd22e84b2457c66a174151ffe67574d1a688a09c8b7d0da922f81f2461d51c`.
- Final source205 runner: `source205-continuation-prepared/runner-v3.py`, SHA256 `098aea36b74c9ebe61930ab66ce8b67e58f46b37080e786ffa2476aa0fe803b0`.
- Root-only host launcher: `source205-continuation-prepared/launch-staging-v3.py`, SHA256 `3228c44ab03c5ea9d9442a3f269223f132ed83d39f10d20a25ac6c09c083dad7`. With `--gate ABSOLUTE_VM_PATH`, it checks readiness without reading credentials; the root alone supplies `--execute-approved` after review.
- Final cache qualification: VM `actual-v29-regressions-v1-20261009/source-205-v30-continuation-cache-supplement-v3/qualification-terminal.json`, SHA256 `b1bc0d4b9542203397072969b5528a10daf18b0d0ca2b4b2e845339eb1ed0d21`.
- Preparation export: local `source205-continuation-prepared/source205-continuation-preparation-20261009.tgz`, SHA256 `a35d6eb70f114e0e5927125d6e9d0a55f9d9a95d01345b56dd1072b36a55c0fc`, 86,821,958 bytes, all 393 regular members read after transfer. Includes failed and passing proofs, scripts, manifests, disposable ledgers and test receipts. Original root-reviewed evidence remains in the separate root export above.

The prefix runner is separately versioned as `candidate-v30-regression-prepared/vm-runner-v30-v5.py`, SHA256 `2f7c30670f47aee20ce57e72054096adb36dbb7224c6597ef5c11d9a513cb02e`. It exposed only the then-unstarted prefix1–6 case, retained its $4/60 cumulative limits and the same suite, and applies the same nested-headroom correction across page checkpoints. Eight focused VM checks passed, using the exact extracted guard class and real Budget on disposable ledgers; independent source review found no blocker. The export `candidate-v30-regression-prepared/prefix-v5-headroom-preparation-20261009.tgz` has SHA256 `d97c75275180038629b6dd09df7657e466c09049b0bc27afdc92c210a20512fc`, 14,586 bytes, all 16 regular files read. The root subsequently adopted it for the actual prefix, reviewing one page before advancing; live progress belongs in the rolling development report.

The separate `independent-v30-transport-headroom-prepared` and `full257-v30-transport-headroom-prepared` versions carry the same correction using their existing immutable per-page baselines. Each passed eleven narrow VM checks, including accumulated-page headroom, settlement, prior suite/global costs, restart, count/scope/exception guards and exact wrapper binding in root gates. Plans, helpers, output scopes and all prior spending are preserved; full257 prospective allocation remains unresolved. These are additional focused checks, not reruns of the old 19/24-test suites. See [the sequential preparation report](sequential-execution-preparation-20261009.md) for exact runner hashes and pending qualification gates.
