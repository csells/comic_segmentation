# Full-artifact traversal harness validation — 2026-10-09

The hardened traversal harness passed inside the disposable Orca browser VM on two
existing, unchanged actual converter outputs and a focused synthetic RTL control.
A deliberately interrupted run also proved cleanup. This qualifies the harness for the
eventual accepted 257-page artifact; that full traversal has **not** run yet.
No model calls, reader changes, catalog changes or promotion occurred.

| Input | Actual steps checked | Selected screenshots | Outcome |
| --- | ---: | ---: | --- |
| Original source page 56 as output page 1 | overview + 8 panels = 9 | 3, including resumed last frame | Pass |
| Actual three-page CBZ format output | 3 whole-page compositions | 4, including resumed last page | Pass |
| Synthetic equal-camera/different-mask RTL control | overview + 2 nested frames = 3 | 3, including resumed last frame | Pass |

All runs used frozen reader build `e5a769ca768d395e` on VM153 port 8084 through
the existing secure-context relay, Chrome 155.0.8059.40 in the isolated Orca guest,
and a 390 × 844 emulated mobile viewport. The reader product bytes were unchanged.
This is desktop Chrome emulation, not physical-phone or Safari qualification.

For every metadata step, the harness verifies the expected page and step index,
source-image intrinsic dimensions, connected visible image, current page URL and
panel-cache binding, exact ordered metadata geometry, overview-first behavior,
and centered/contained framing after the normal camera and child dim-mask
animations settle. It
checks the displayed blob's SHA-256 against the original archived image once per
page. Animations are observed, never disabled or accelerated. The source's expected
LTR/RTL direction must match both the independently validated `panel-reader.json`
profile and runtime reading direction. The profile is bound to the metadata SHA;
standard ACBF itself supplies geometry/order, not a reading-direction field.

The harness also checks the final advance remains on the last frame, closes the
book through the visible button, and confirms every previously cached page URL
is revoked, the URL array is empty and thumbnail nodes are removed. Reopening the
same file restores the final page/frame; a second close passes cleanup again.
The three completed inputs retained their original archive hashes and raised zero
uncaught browser exceptions. All ten selected final screenshots were inspected.
Some resume images appeared blank in tool previews; their saved central page/frame
pixels exactly match the visibly rendered pre-close captures in all three cases.
The additive pixel comparison preserves that distinction; there is no demonstrated
blank-page bug.

Independent review identified that a camera-only animation wait could miss a
moving child mask when two rectangles share the same camera transform. The final
regression has exactly that geometry: its second panel observed only an 850 ms
`guided-dim` clip-path transition, waited 0.902 seconds, and then reported zero
subtree animations. The RTL source profile and left-side advance were verified.
The first fixture mistakenly included an empty ACBF body; the reader correctly
rejected it. Its unchanged failure screenshot/logs and V2 tool files remain in
the export. Omitting the body fixed only the synthetic fixture; reader code was
never changed.

The runner samples all owned Chrome processes each second, writes per-process RSS,
and stops at 4 GiB aggregate RSS or its explicit time bound. Per-page evidence
records JS heap, retained full-page URLs, pending URLs and panel-cache counts.
RSS sums can double-count shared mappings and JS heap excludes native image
memory. Neither is a physical-phone memory measurement. The runner records a
bounded final process check after the parent exits, handles verified task-owned
leftovers, and fails if any remain. A forced ten-second run on the existing
13-panel source-57 archive intentionally stopped after 11 steps; the time guard
fired and all Chrome processes exited. This is a successful interruption/cleanup
test, not a segmentation or archive failure. No whole-book stress test was repeated.

## Evidence and reproducibility

Evidence root (ignored/private):
`validation-artifacts/segmentation-iteration-20261008/reader-traversal-validation-v3-20261009/`.

- `traversal-validation-v3.tgz`: 3,732,354 bytes, 77 regular members,
  SHA-256 `e0b0d894c34b7b76383f614718e3d5d812af90744d7c1bcfd61e76c21e633e6d`.
  Every member was fully read; all manifest hashes and the local harness source
  hashes match. `archive-verification.json` records that verification.
- `extracted/traversal-validation-v3/{mask-v3,source56-v3,threepages-v3}/results/` contains
  `expected.json`, streamed `steps.jsonl`, `results.json` and screenshots.
  Sibling `runtime/` directories hold invocation, browser version, timing,
  per-process RSS and all-process close receipts. The archive includes all inputs,
  the malformed V2 fixture/failure, and the expected forced-stop evidence.
- `resume-pixel-comparison.json` is additive evidence, separate from the immutable
  archive. `visual-review.json` binds the ten inspected final PNGs.
- `traversal_check.py` SHA-256:
  `ba17b4640895d1304c474a78783d782eb27be8037fd94c68f4fe87770b2ab510`.
- `traversal_run.py` SHA-256:
  `0a3053b194f971d8cf7c77b64039394d18076b09b637c4ecc8771c9684d0eb35`.
- Imported `panelized_check.py` SHA-256:
  `d48a2adbea66f5b958f0c32a282deef9ad962066ba4a2bc77a562d90ee4dde93`.
- `make_traversal_fixture.py` SHA-256:
  `f17931b92a485905d816970a9f0cb57bb373b2a5a8884be9e6929e39ae87a3d1`.

The earlier V1 archive remains unchanged under
`reader-traversal-validation-v1-20261009/`, SHA-256
`1a3e6eaff6117178c9faf105515427829b93de004346fcf755619b35a12c7061`.
Its initial small-book passes preceded the independent harness review. Use the
final V3 tools and receipts for future full-artifact work.
An independent agent reviewed the final source and reread all V3 result/run/close
receipts, including the mask-only transition and forced-stop proof; no remaining
blocker was identified within this scope.

## Remaining full-book check

The [existing same-build reader report](reader-v29-browser-20261009.md) already
measures the original 257-page archive at pages 1, 129 and 257 and independently
checks visible-thumbnail scheduling. Reuse those results; they do not claim
sequential traversal of all pages. Reader `pageURL` retains visited encoded
full-page blob URLs until close. It does not prove that all decoded images remain
resident, but complete traversal can increase retention beyond the prior sample.

When the actual accepted 257-page CBZ exists, run this harness on that unchanged
artifact. Assert every overview and metadata frame, record page source hashes,
geometry/order, settled framing, URL/heap/RSS progression and close/reopen cleanup.
Capture first/middle/last page overview and final panel, plus failures; streamed
assertions cover every other step. The runtime bound must accommodate normal
850 ms camera transitions. Stop and preserve evidence if memory or time bounds
are reached. Segmentation quality still depends on the separately recorded
source/crop review; a browser transport pass does not establish universal quality.
