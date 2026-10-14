# Marked crop context: automatic escalation result

Diagnostic B passed three fixed-proposal controls on 2026-10-10. It corrected the
tested V31 missed escalation without changing geometry, forcing flags or replacing
the stronger verifier. This is development evidence; fresh V32 integration and
detector-to-CBZ validation are still required.

| Proposal | Automatic path | Final result | Personal review |
| --- | --- | --- | --- |
| N2: clipped swing artwork | Luna flags targets 7 and 8; Sol checks 7 and names missing beam, seat and foreground plants | Whole-page fallback after the single permitted tier | Rejection matches the actual additional left-edge cut |
| P56: intact eight-view page | Native checks keep; completeness guard confirms eight views | Accepted | Geometry and all source/crop bytes match the personally reviewed CLI output |
| P6: intact seven-view page with insets | Native flags target 1; existing ownership verification clears the complete candidate and marked targets 1, 2, 4 and 5; completeness confirms seven views | Accepted | Geometry and all source/crop bytes match the personally reviewed CLI output |

The package sends every native target check four images: the complete source,
actual crop, clean enlarged source context, and the same context marked with the
exact crop boundary. A generic predicate clarification distinguishes an artist's
original cut from additional clipping introduced by the proposed crop. Native
target inputs contain order and geometry but omit automatic ownership hypotheses;
the global checks and stronger verifiers retain their existing evidence. This
experiment tests that combined package, not the isolated effect of one image or
sentence. The code contains no source-page, object or expected-result hints.

All routing used the actual judge, controller, stronger verifier and final
completeness guard. Frozen proposals retained their original tiers and exact
crops; detector expansion and repairs were disabled. The runner stopped on the
first blocked or incorrect final outcome. Root inspected results afterward and
supplied no runtime decision. This did not test new detection or export.

The previous strict native screen remains failed: it stopped after correctly
flagging N2 and keeping P56, then falsely flagging intact P6 target 1. B shows why
that false alarm can be acceptable as an escalation trigger: the actual stronger
route resolved it correctly. No claim is made that the native classifier is
perfect. N2 target 8 was not independently verified because target 7 already
established failure.

B made 21 new requests and reused 37 exact responses. Twenty native calls cost
$0.012054; one Sol verification cost $0.018898, totaling **$0.030952**. Every new
reservation settled once. All 58 request fingerprints were independently rebuilt,
and the earlier ledger prefix, frozen inputs and failed results were unchanged.
Global spending plus retained holds reached **$54.756524 of $100**. This incremental
cost is not a cold per-page price.

Evidence is under the ignored local directory
`validation-artifacts/segmentation-iteration-20261008/`:

- Terminal: `68662ce453ab3d7cc7a41eff97b205da484365a76fda4108018c75dc1e45f606`.
- Root review: `f0f01b9ea228829e6ef7b2510278e9565094c866b2d0f41e70cf52db30885ba5`.
- Independent audit: `7625fb1ab34cfd505000d645e3e4582576b7a5f05392f2bb7cb213eab40a484c`.
- `crop-extent-B-passed-boundary-20261010/evidence.tgz`: 27,113,730 bytes,
  262 regular files fully read; SHA256
  `ed660a93d8afeb563fbe183708fb252a518d6dcfc462c150ccded2a447bb6753`.
- Its semantic addendum: 231,587 bytes, five regular files fully read; SHA256
  `d9c2746d6bc3bd8d9a455e6e0bc1cc81ed3ec18189f1b526b66b337f0e01c440`.

Next, integrate the exact package in a separate candidate and rerun all seven
omission/clipping controls, then actual CLI regressions. Preserve the failed V31
and native-screen evidence. Independent comics and the full PDF remain separate
quality gates; this result alone does not establish general segmentation quality.
