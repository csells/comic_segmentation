# V31 injected quality-boundary controls

**Completed: FAILED.** The actual seven-case run accepted all three intact
proposals and rejected all three omissions, but falsely accepted N2's clipped
swing crop. Root's semantic review rejects application qualification. No
independent-page or full-PDF continuation is authorized by these results. The
frozen protocol and failed evidence are preserved; see the
[audited execution results](source-completeness-guard-results-20261009.md#actual-v31-control-execution-clipping-false-acceptance).

This tests the actual V31 quality controller, `OwnershipConverter` judgment and
verification, and mandatory source-completeness acceptance callback against seven
fixed post-refinement proposals. It is a deliberately injected boundary test.
The separate CLI experiment must establish detector-to-export behavior.

The source is frozen in VM153 at
`evidence/candidate-v31-source-completeness-G-20261010/source`, with adjacent
186-file source-manifest SHA256
`3dda1a1996ebd7a96a040a5f848501f4929eb494a6ac142720dfaeaacbaaa3d5`.
The runner verifies every source file before importing the application. Execution
and tests stay in that disposable VM. Stable Build10 is untouched.

## Frozen cases and hypotheses

| Order | Case | Proposal | Required result |
| --- | --- | --- | --- |
| 1 | P56 | Original accepted eight-view automatic geometry | Accepted with a valid completeness proof |
| 2 | N56 | Delete view 7, the swing scene; renumber the retained final view | Whole-page fallback; never accept |
| 3 | P6 | Original accepted seven-view automatic geometry | Accepted with a valid completeness proof |
| 4 | N6 | Delete the dedicated photograph inset, original view 5 | Whole-page fallback; never accept |
| 5 | P57 | Original accepted thirteen-view automatic geometry and repair ancestry | Accepted with a valid completeness proof |
| 6 | N57 | Delete original view 8, the cannon scene; retain and renumber the other twelve | Whole-page fallback; never accept |
| 7 | N2 | Exact previously labeled clipped-art challenge on source 56 view 7 | Whole-page fallback; never accept |

Materialization preserves every supplied source/crop byte, full automatic panel
description, classification, orientation, direction, and geometry. The positives
retain only their actual repair ancestors. The deletions are standalone proposals
at the original tier; a deleted panel cannot honestly be represented as a
monotonic geometry repair. Identities and positive ancestry references are rebased
using the actual V31 policy identity formula. No human description or expected
label is passed to a model.

The immutable materialization manifest is
`evidence/v31-integration-20261010/materialized-controls-v1/manifest.json`, SHA256
`6b61b85ad4019bbe5bd5fb7c13d27ab93bc4935f937c4278122dcd1994ee1da0`.
It binds 114 material files, original automatic records, preceding-page context,
pre-existing root labels, G terminal/root semantic receipt, and the old N1
terminal and stop. It is additive: the stopped historical N2 dispatcher is never
resumed or modified.

## Actual application boundary

Each case gets a fresh `OwnershipConverter`, genuine saved bundle, original
source pixels and actual preceding two pages, when present. Ancestor bundles and
candidate lineage are loaded; no judgment, source audit, scene links, passing
decision or verifier answer is injected. The controller receives the fixed
post-refinement candidate at its original tier with no detector or repair calls.
It invokes actual `judge`, `verify` when needed, and application
`final_acceptance` with actual `SourceCompleteness`. An accepted positive must
also pass the actual bound-proof validator. Per-case result files preserve the
entire actual controller trace.

A negative may be rejected by existing quality checks before completeness. The
terminal explicitly records `completeness_exercised`; such a result cannot be
described as a successful test of the final callback. A transport/cache/budget
block is inconclusive. It never counts as the required whole-page fallback.
Root must examine final semantic behavior before qualification.

## Cache preflight and budget

The root-owned common integration envelope is **$3 and 64 new requests total**
across every attempt beneath `evidence/v31-integration-20261010`, including these
controls and separate actual CLI runs. The global cap remains **$100**. The old
G diagnostic envelope remains separately recorded at 45 requests / $1.434407.
Every prior integration reservation, including unknown/unsettled attempts,
counts. The wrapper uses the tighter global/integration remaining balance and
holds `integration.lock` plus the durable ledger lock. No automatic recovery or
cap amendment is allowed. Root owns any prospective adjustment and paid launch.

Cache-only execution copies the complete global ledger, denies `Budget.reserve`,
denies HTTP including non-generative preflight, and denies socket connections.
It visits all seven cases solely to discover exact missing requests. It proves
both the copied and real ledger stayed byte-identical. Paid execution uses the
real ledger, checks an explicit root gate, and stops at the first mismatch,
uncertainty, or blocked case. Expected labels only evaluate returned statuses.

The frozen runner is `prepared-controls-v1/run_controls.py`, SHA256
`9376597382a73752e006ecc8f6a3e64bb78f81c1a49b5578a0af1ff492b00b7e`;
shared helper `integration_budget.py`, SHA256
`2ab955cd8beef57c69ab7efc5037b7a38df2b015f020bfa71b7129faf487b576`.
These are retained locally under
`validation-artifacts/segmentation-iteration-20261008/v31-injected-controls-prepared`.

The final actual cache-only run completed with **111 exact response reuses,
zero new calls and zero paid reservations**. P56, P6 and P57 were accepted with
validated final completeness proofs; N56 was rejected by final completeness.
The remaining negatives reached exact uncached requests:

| Case | Uncached next request | Fingerprint |
| --- | --- | --- |
| N6 | Astra source-ownership audit | `bc6f3b7c38fa6232697496eae4ac36e2dc23cdbdf5af5df040f2926f1c0340ec` |
| N57 | Astra source-ownership audit | `7fb44c68438982cb959ef5e7156e81409757f668c001cd63f09cd540c33154ac` |
| N2 | Native Luna quality decision | `2d649f397b8eb89f551258746f543e509c7b67d80ae22d11bfaf08d6260ff502` |

This is a blocked preflight, not a passing seven-case result. The terminal at
`controls-cache-only-v2/terminal.json` is SHA256
`64c0b0037ed6d8b6a68eba1b22a70e2c559d14437d3ea7bd4343897dafcc9103`.
The initial cache-only run has identical outcomes and remains preserved. The
final runner suppresses bytecode and checks exact source inventory/no symlinks;
task-generated bytecode from the initial run was removed only after matching
each parent source to the frozen manifest, with a cleanup receipt retained.

Global held/used remained $53.709182; integration spend/request count remained
zero. The three missing requests may reveal further required checks; no answer
is substituted to predict them.

The independent preparation review passed with no findings and revalidated all
111 reused request/response identities plus the four decisive completeness
proofs using a client that cannot make a request. Its receipt
`prepared-controls-v1/independent-controls-review.json` is SHA256
`bfe8c654310e036f9c78ad5a3ab0d92d04c92cda12ef8b01e035fccd6ba973d5`.

Eight additional shared-budget checks use the real `Budget` implementation on
fresh copies of the captured ledger. They verify prior holds/attempts, 64-request
counting, tighter global headroom, settlement cost release, exact path scope,
denied offline reservations, and no policy amendments. All passed; the receipt
`prepared-controls-v1/budget-proof-v1/receipt.json` is SHA256
`e5b7130f76699e7f39a51d3a3b31a3368c27cdc13d826301e3edd1774445a991`.
Synthetic reservations exist only in those copied test ledgers.

## Launch and qualification gates

Paid output is fresh `evidence/v31-integration-20261010/controls-v1`.
The root gate must bind exact runner/helper, source and materialization manifest
hashes; cache-preflight and independent review files; ordered cases; output;
global/integration caps; and the no-recovery policy. The key arrives only on
stdin for root's launch. The runner has no credential acquisition code.

Terminal `cases` is an ordered list keyed by `case_id`. Each row records status,
expected status, match, source/candidate identity, result path/hash, actual
judge/verifier/completeness routes, whether completeness ran, and call/cache
counts. Top-level fields bind all inputs, original labels/stops, complete call
log, before/after accounting and ledger hashes. `outcome=controls_passed` requires
all seven expected results and no harmful acceptance; otherwise `blocked` or
`failed`. Paid execution stops immediately on an unexpected case. A separate
root semantic review must bind the complete terminal SHA and explicitly pass
before independent continuation or application qualification.

Even a complete passing control run does not establish full-PDF, independent
holdout, other-format, or general comic segmentation accuracy. The actual CLI
and export checks, followed by independent sequential qualification, remain
separate requirements.
