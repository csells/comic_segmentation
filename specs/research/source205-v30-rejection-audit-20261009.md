# Source205: independent review of the Sol-high target8 rejection

2026-10-09. **The crop really excludes visible ground, but this is not a clean binary ownership control.** The excluded strip is continuous with the crouching cat's unframed foreground and also borders the later leap scene's fissure. The rejection is defensible as conservative background preservation; the evidence does not establish an unambiguous target8-only omission or a confirmed verifier false positive.

The initial evaluation-only review covered a rejected intermediate candidate while the automatic Astra detector was still running. The later acceptance and accounting audit are recorded separately below; they do not change the ownership ambiguity in that rejected crop. No model calls, routing changes, manual geometry corrections or application execution were performed for this review.

## What the images establish

I viewed the full original source, the exact rejected crop8, both its unannotated and marked source details, and the adjacent walking-inset crop9 and leap crop10.

- Crop8 preserves the entire crouching cat, including its high tail and white tip, the muzzle/forepaws, and the collar it is manipulating. The visible bottom-left red book, nearby debris and foreground remain. No missing subject, collar component or target8 text was identified.
- Its right boundary is source x=714 exclusive. Below the walking inset, tan ground and dark edge strokes continue to the right of that boundary before reaching the jagged blue fissure. The unannotated detail confirms this is actual excluded artwork, not a red-line artifact, a JPEG border, or an imagined continuation beyond the original page.
- The lower montage provides no frame or gutter assigning that complete strip exclusively to the crouching-cat moment. The ground flows beneath the inset into the fissure bank, while the two animals' leap is a separate later action. Thus spatial continuity supports preserving more foreground, but it does not by itself settle which moment owns every part of the shared transition.
- The disputed strip is also inside the later crop10 rectangle. That is a page-coverage observation, not permission to omit content that genuinely belongs to crop8. Conversely, the fact that crop8 contains the separate inset and its discarded collar does not make those objects part of the crouching-cat moment.

This differs from the [source36 rejection](source36-v30-rejection-audit-20261009.md), where the omitted courtyard strip belongs to a clearly framed source view. Source205 should not become a high-confidence clipped-subject or exclusive-background negative in verifier calibration without a separately settled ownership standard. It also should not be counted as another confirmed false alarm like source57 target10.

## Saved audit and verifier context

The Astra source audit identifies ten scenes. For scene8 it assigns the crouching cat, engaged collar, curled tail, ground beneath the cat, debris and red book. It describes that cat and its immediate ground as an unframed view. For scene9 it assigns the detached collar crossing the walking inset's bottom border. For scene10 it assigns the airborne animals, luminous fissure, motion field, jagged rock banks and tapered opening toward the bottom.

Those assignments correctly distinguish the main actors and two collar depictions. They leave the disputed foreground/bank transition less precise: “immediate ground” and “jagged rock banks” do not define an exclusive dividing contour. The automatic inventory reports no uncertainty, but its confidence is not an independent ownership annotation.

The exact Sol-high marked-target response `113f1dc5dc40e6def82665a3b80a4173c2ed67baeb0c605bc171d2a34fd6f3c0` returns scene inventory/order pass, coverage fail, and one clipped-art issue for target8. Its explanation identifies the excluded tapering tan ground below the walking inset and before the fissure. That physical observation matches the images; the exclusive attribution to the crouching-cat scene remains an interpretation. Retain the actual rejection and subsequent automatic escalation unchanged.

## Provenance and review limits

| Artifact | Identity / SHA-256 |
| --- | --- |
| Source JPEG, 1128×1648 | `897d3ae22ebe4ae6a667810d190a13e973eabd1b1dfa91f959b106e6434fcab3` |
| Rejected Sol-high candidate | `f2d6a3be35bed2ce9999fcf117ab911968cb513aca4edd81d8fa4ebeca7749eb` |
| Candidate bundle file | `aca784fa51f79144660e0bb8761d719ee0f270063cbac326bdf8ba88ef34a7cd` |
| Exact crop8 | `3c757494fbfe06170f25262fa440458d25ab72d89bc8d53d0e76c5eb0fbb6974` |
| Unannotated target8 detail | `5e1e59553e466d89b97e547bde8a0f96087280ea35de2ca07f7b7cd7c54fe72e` |
| Marked target8 detail | `89e8abeb3fc23e7632c3c367509a476cdd287e9b325615057f211cfd83363bc0` |
| Scene-evidence file | `51e0d24328abd49c3d3399f4c9445bb3988c1fda8e83bee46fad5e2df70da0fe` |
| Saved verifier request file | `98958988e79bb5048afe68bc57f0a6e26addbf0a52f03f7d40c1fcdb7831acaf` |
| Saved verifier response file | `54bdac42781dfd376df941dbaefb31036ad9bd9cf134aa99db58582a85b2e4bf` |

The request's image hashes match the inspected source, crop and two details. The source and crops8/9/10 match the saved bundle hashes. Crop8's normalized box is `[575,0,1000,632]`; its actual pixel extent is **`[0,947,714,1648)`**, with right and bottom exclusive. The bundle stores inclusive opposite corners `(0,947)` and `(713,1647)`. The source-detail extent is `[0,848,781,1648)`; the full source was also inspected, so the assessment is not limited to that detail window.

Exact read-only export: `validation-artifacts/segmentation-iteration-20261008/source205-sol-high-rejection-audit-20261009/exact-rejection-evidence.tgz`, **2,154,583 bytes**, **11 regular files fully read**, SHA-256 `c4e97c7ef4645aa6df7c10ad565360aaa9676bdb839e5c347e7a3d11e28b624f`. `export-proof.json` records every member hash. The export preserves the provider request metadata and full response, candidate bundle, original source, three crops, marked/unmarked detail and source audit. It is a targeted intermediate-rejection export, not a complete run backup or a review of all ten crops.

## Automatic acceptance and settled continuation

The unchanged V30 quality policy subsequently accepted ten panels from Astra candidate `6b0bd0fc4076a35853c9421f892c608397f038bd6a25f7a1a08e23895d0ee9ab`. The first invocation stopped at a reservation scheduling guard after 47 settled requests; it had neither accepted nor published the candidate. A separately qualified continuation exposed the remaining nested budget to the existing worker scheduler, preserving the original requests, prompts, source and geometry. Sol-low and Sol-high still escalated. Astra's native judge still requested escalation; its source-ownership global check and nine required marked-target checks all accepted, producing the ordinary automatic `keep` route.

I independently read the accepted record, terminal, completion summary, root review and ledger. All 47 original request IDs appear as cached requests in the accepted page trace; their bound original files remain unchanged. The 16 continuation requests have distinct IDs, no retry ancestry, saved responses and timing records, and exactly one settlement each. All 63 original-plus-continuation requests are settled. The completion summary reports **49 cache-hit events**; this is an event count, not 49 additional distinct original requests. No original successful request was paid for again.

| Accounting scope | New requests | Used or held |
| --- | ---: | ---: |
| Original source205 invocation | 47 | $1.286989 |
| Continuation | 16 | $0.304194 |
| Source205 combined | 63 | $1.591183 |
| Development suite at this terminal | 306 | $8.502016 |
| All research at this terminal | — | $51.353348 |

The continuation's six Luna native checks and ten Sol verifier checks took **136.647 seconds** in total. These are incremental, cache-assisted measurements, not cold-page cost or latency. The old and new source205 runs share the same $4 cumulative case ceiling; the prospective 160-request limit, $20/480-request development suite and $100 global ceiling remained enforced. The independently read ledger snapshot had 7,090 rows and SHA-256 `0f72ba783cb0c9b325dc5c88c75dbe22befee02acf04f1b5d18a1ea0da35acc4`.

The accepted bundle's source and all ten crops are byte-identical to the earlier Astra diagnostic that root personally reviewed. Root's subsequent acceptance receipt binds those exact bytes and the actual publication, with no human routing or geometry correction. Accepted crop8 extends farther right than the rejected Sol-high crop; it retains more ground without settling exclusive ownership of that continuous background. Rectangular views still include neighboring inset and scene content.

Acceptance evidence is under `validation-artifacts/segmentation-iteration-20261008/actual-v30-source205-accepted-20261009/`. The VM run is `evidence/actual-v29-regressions-v1-20261009/source-205-v30-continuation-v1`. Root's complete quiescent export `actual-v30-source205-continuation-accepted-20261009.tgz` contains 256 fully read regular files, 20,392,927 bytes, SHA-256 `88a3affe61a2989a8fee72575ac2fcaac34953e3e263c47249a496e28a8c89e9`.

| Artifact | SHA-256 |
| --- | --- |
| Accepted continuation terminal | `2e6e6fd64c5db693e14d4037e56f3934690d91ab1627c38c4f60fb36efb4f3d1` |
| Root's exact-source/all-crop acceptance receipt | `9d4f93ed3af736e84602aff4837a50246295499923d2e80f6d5e6189887b6989` |
| Actual one-page, ten-panel CBZ | `ed018c263910d975c0092addd25875a57ee5c8bbdbe5d16c16458194613d5664` |

The browser worker subsequently passed actual CBZ playback on unchanged reader `e5a769ca768d395e` at port8084: overview, all ten frames in order and the end boundary, exact source/metadata binding, centered containment and zero exceptions. The worker personally inspected all eleven screenshots, including the lower cat/collar, separate walking inset and final fissure. This is desktop Chrome155 in the isolated macOS VM at a 390×844 mobile viewport, not a physical-phone/Safari test. No browser metadata correction or catalog addition was made.

Browser evidence is under `validation-artifacts/segmentation-iteration-20261008/reader-v30-source205-20261009/`; the archive has 26 fully read regular members and SHA-256 `5dce017249b536873797363e0f9c90c56801422bdad762fd661909578d485de1`. The worker's visual receipt SHA-256 is `da1abe8d50a5f2c6034261e0a8b93665d9263da31a53cd5c6eda97c035289d66`.

This closes automatic conversion, root crop review and actual reader playback for source205. It does not resolve the earlier ownership ambiguity or qualify the remaining PDF.
