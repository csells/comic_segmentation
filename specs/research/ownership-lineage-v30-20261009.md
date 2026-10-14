# V30: preserve required ownership checks through repairs

2026-10-09. Read-only review during the original source-57 V29 run found a
controller gap: monotonic expansion can reduce overlap *percentage*, allowing a
repaired candidate to leave the ownership path despite unresolved obligations
from its parent. This was demonstrated with synthetic controller inputs, not
claimed as an observed error in source 57. The active V29 run and its immutable
integration snapshot were preserved.

Two parent boxes `[100,100,300,300]` and `[280,100,480,300]` overlap by 10% of the
smaller area. Expanding their outer edges to `[80,100,300,300]` and
`[280,100,500,300]` reduces that ratio to 9.09%. V29 could then accept the native
judge's quiet verdict without the required rich ownership checks. Native checks
still examined the crops; this was a stronger-confirmation bypass, not a total
absence of crop evaluation.

V30 follows the explicit repair lineage and retains required ownership targets
from ancestor overlap/crossing risks, native target warnings and the exact
clipping issues that triggered repair. A quiet later native check cannot erase
those obligations. They are recorded in `ownership_required_targets`, including
when a no-op repair keeps the same content identity and overwrites the ordinary
identity-keyed verdict. Traversal uses object identity for cycle detection so a
legitimate identical descendant can resolve its earlier saved parent. Missing
or cyclic ancestry blocks the run.

The source/inventory/direction/order and immediate-parent monotonic checks remain
binding before inherited source evidence can support verification. Evidence is
also checked against its original frozen proposal and model/prompt/request
hashes. Source evidence alone still cannot accept a crop. Each ownership
candidate must pass a complete-candidate check plus exact marked checks of every
required target. Reading margin remains a one-time expansion; no prompt,
provider request body or detector/refinement algorithm changed. An ordinary
repair with no ownership risk anywhere in its lineage retains its existing
route. A fresh detector proposal does not inherit another proposal's lineage.

## Exact validation scope

All runtime checks ran in a new disposable VM153 directory:
`/home/tester/comic-reader/evidence/ownership-lineage-candidate-20261009`.
No API call, credential read, network attempt or shared-ledger access occurred.

Three new regressions were first run against the untouched V29 modules. All
failed as expected, including a controller example where the old code accepted
the diluted-overlap repair despite the scripted failing marked verdict. The
same tests pass with V30. These use controlled verifier results to test routing;
they are not segmentation-quality measurements.

The corrected candidate passed **92 focused tests**, including nine new
regressions, across these modules: `test_ownership_converter`,
`test_scene_evidence`, `test_geometry_repair`, `test_automatic_escalation`,
`test_component_refine`, `test_candidate_pipeline`, `test_target_detail`,
`test_viewport_refine` and `test_auto_convert`. This is not a rerun of the entire
previous 180-test set. The added cases cover threshold dilution, final marked
failure preserving fallback, multigeneration repairs, fresh proposal separation,
source/inventory/direction/order/shrink rejection, missing/cyclic ancestry,
same-identity no-op repair, retained native/global repair targets and unchanged
ordinary-page routing. An independent read-only review found no remaining blocker.

## Frozen candidate and continuation

The exact passing 179-file app snapshot is
`/home/tester/comic-reader/evidence/candidate-v30-integration-20261009/source`.
`source-manifest.json` SHA-256:
`b64cf3d413840ec012b9c43f7287b3f7389bda91efee71f64abb346fba83311e`.
It differs from frozen V29 in only `ownership_converter.py`, its tests, and the
`auto_convert.py` policy string `automatic-source-ownership-v30`.

Module hashes:

- Ownership converter: `83aeb71714d71df16ff01f9a9013bbe97ccc56fabb979bd9a5f619f1da047d44`.
- Actual converter: `78885f27fcc12daa8fd1bfbdb5218d89bd98e317dbfb592bbdec26790741d485`.
- Ownership tests: `98cc1182e6312def59b99a0ac2a8db13e5b376b7f322cecef1202ca756212195`.

A prepared `replay-source57-cache-only.py` beside that VM snapshot invokes the
actual converter with the original full PDF/render cache, source 57, explicit
LTR and both real predecessors. It requires the V29 terminal plus root's bound
visual-review receipt, uses a disposable ledger copy and dummy credential, and
denies both new reservations and all HTTP, including token preflight. Detection,
decision, ownership, repair and publication are not stubbed. It preserves every
cache miss and stops; it does not retry or fund missing checks. At the first
snapshot export, only syntax/import was checked. That first runner was preserved
when the blocked-diagnostic gate below required a separately versioned runner.

The first prepared output name was
`actual-v29-regressions-v1-20261009/source-57-v30-cache-only`; the later executed
V2 uses `source-57-v30-cache-only-v2` in that same suite. Any future paid V30
runner must retain that same parent suite's $20/240-request accounting and the
global $100 ledger so V29 spending cannot reset. Cached V29 responses are reused
only through the unchanged exact request cache. A new policy name changes
candidate identity but does not authorize repeating a completed provider call.

V29 source 57 subsequently ended blocked at its 96-request case ceiling, before
another dispatch, with no selected page record or CBZ. Root bound its completed
source/all-13-crop inspection to the latest blocked candidate and terminal,
explicitly recording no automatic acceptance, publication or intervention.

The separately prepared V2 diagnostic gate checks the latest blocked record,
candidate/bundle geometry, complete crop inventory and exact source/crop hashes.
Its actual receipt check passed, followed by **31 separate orchestration tests**
(20 spending/dispatch plus 11 adversarial provenance checks) in VM153. These used
disposable ledgers without API/network/credential access or opening the shared
ledger; they do not expand the 92-test application qualification claim.

Root then ran the actual cache-only V2 replay: it stopped at the first missing
target-9 request after 4.079 seconds, with zero API calls, unchanged shared/copied
ledgers, and source/all-13-crop hashes matching the reviewed diagnostic. Its
terminal hash is `65f28609518f7919ee4d2c5582f19ed8cd76ede926368c310bf5ac4778f1fd42`.
Root separately authorized the concrete incremental check and started the bounded
V30 source-57 run; its final automatic outcome remains a separate qualification.
No stable service, reader build, Rust implementation or deployment changed.

Prepared V2 launcher, receipt schema, stable title/resume rules and exact shared
limits are documented in
`validation-artifacts/segmentation-iteration-20261008/candidate-v30-regression-prepared/README-v30-v2.md`.
The orchestration export there is `v30-orchestration-v2.tgz`, 39,403 bytes,
SHA-256 `36dd739e31a56590c10f80d0ab32cdc201c845ad8c9509b9e987333e19907e79`;
all 55 regular members were fully read and hash/size verified after transfer.
It preserves prepared scripts, guard fixtures/receipts and the actual diagnostic
gate proof, and excludes subsequent live cache/paid outputs. The passing first
orchestration version remains separately archived as `v30-orchestration-v1.tgz`,
25,964 bytes, SHA-256
`8324e6fcbfd973950db917a243b57d2ffd57d8e80e1df7d3a3dbe621e02cae93`.

The off-VM restore artifact is
`validation-artifacts/segmentation-iteration-20261008/candidate-v30-integration-20261009.tgz`,
390,475 bytes, SHA-256
`8516589af379855126dccb1525c5132664baf3a2e90de8b707dfc3a39e8850f6`.
All 193 regular members were fully read after transfer; 192 entries match the
included export manifest, with the manifest itself the remaining member. It
contains the frozen source, both positive/negative test receipts and logs,
validation harness, prepared replay runner, source/provenance manifests and
continuation instructions. The adjacent `.verification.json` records the check.
