# Actual four-format prefix6 validation — 2026-10-09

PDF, CBZ, genuine compressed RAR5/CBR, and image-folder inputs all completed the unchanged V30 transport candidate using recorded provider responses. Each produced six accepted pages with panel counts `[0,0,0,0,7,7]`, no fallback, and the same source images, selected candidates, crop bytes, geometry, order, ACBF semantics and reader profile semantics. The actual four emitted archives passed all **80 browser steps**: six complete-page overviews and fourteen ordered panels per book, followed by the end boundary. No metadata was corrected for playback.

This closes format transport/publication/playback coverage for these six root-reviewed pages. It does **not** qualify V30 generally: the separate N1 missing-scene control was falsely accepted, so unseen-comic and full257 execution remain blocked on a generic completeness correction. Four formats of the same pages are not four independent quality samples.

## Converter and review binding

The unchanged prepared harness `run.py` has SHA256 `c982e7224cfe0797c31e3f1c623b60c6214370db0928095b20a022e0ca1aff43`. Its source is the frozen 180-file V30 transport candidate, manifest `debd22e84b2457c66a174151ffe67574d1a688a09c8b7d0da922f81f2461d51c`. A prerequisite-only wrapper checked all six existing positive root receipts against source images, selected candidates, page records and all fourteen crops before calling the unchanged harness. It did not supply outcomes or panel geometry.

Each format made **55 exact cache hits and zero new calls**. Copied ledgers plus denied reservation/HTTP/socket access prevented accidental paid work; no misses occurred. The live ledger, copied ledgers, original input data and frozen source remained unchanged. The PDF path used the original PDF and its existing render cache; archive/folder inputs contained the exact same six original image bytes. Cached elapsed times were 3.188s PDF, 1.565s CBZ, 1.579s CBR and 1.578s folder; these exclude provider inference.

The accepted prefix archive used for root review is `f5fc162a43f88b755aa246d91eb24fa7d334c8328a4e87dee4a2ee9b2595a37b`. All six root receipts and their per-output binding are preserved. `root-review-output-binding.json` has SHA256 `b269d80262e0527b02a910485c2236d5dd580dda9a450019474b6d672b1e3da0`; converter `report.json` is `685a505f147aead63f0cec9b7fe332b01a45fba15c5a0a2e4e9667e416290de7`.

| Input | Actual emitted CBZ SHA256 | Browser steps |
|---|---|---:|
| PDF | `2a24f4440b17aa906ee938e57a2cd81870d637743b11cddaf641b904a0600a23` | 20/20 |
| CBZ | `5b6cb8cd3f22c44fa2c10e6e08a0a40e4b03e6cc8b23aa06ef2cea7fd1975444` | 20/20 |
| CBR | `910deff540e019667b53636c8243cd1ff84acfa3dcf1f808ea9da07192ed3f6e` | 20/20 |
| Folder | `2e818d366832bc76deade3eeb54d2756d86c2f2a2327bf354ec83db04c9f90af` | 20/20 |

All four ACBFs passed the retained official 1.1 XSD (`154e997a600143adf205bfcad427ef6e6fa4a6fcfce10cece4d58a0b64c2ac32`) in the browser guest. Each `panel-reader.json` metadata hash and expected LTR direction matched the actual ACBF and observed reader direction. Standard ACBF has no reading-direction field; the hash-bound profile carries this extension.

## Actual browser playback

The isolated Orca guest ran Chrome 155.0.8059.40 at 390×844 with the frozen reader build `e5a769ca768d395e` served by VM153:8084. Reader code SHA256 remains `387161f4b5d7eb9940857a26203efd151c740f387ffee3673b72fad171a9eafd`. The existing all-screenshot harness, SHA256 `d48a2adbea66f5b958f0c32a282deef9ad962066ba4a2bc77a562d90ee4dde93`, loaded each actual archive through the file input and used real pointer navigation.

Every step checked the expected page/frame ordinal, overview flag, exact ordered ACBF rectangle, connected image with positive intrinsic/rendered dimensions, current page URL/cache binding, target containment and centering after the normal 850ms camera transition. Every archive reached its proper final boundary, raised no runtime exception and remained byte-identical. All 80 screenshots are retained. Browser-worker personally inspected all **31 distinct screenshot byte variants**; the remaining **49** exactly match an inspected screenshot. The six overviews, lunar action scenes, watch inset and separate photo inset render correctly. Broad rectangular frames still include neighboring or inset artwork; this is not polygon isolation.

The old bounded runner's PDF process check caught one retained task-owned crashpad helper after Chrome exited. This was a cleanup assertion, not a playback failure. Evidence was preserved; bounded cleanup checked process identity and terminated any remaining task Chrome helper. Each final owned-process list is empty. No product test was repeated. Peak aggregate process RSS was 1.458–1.524 billion bytes across the four runs; shared pages may be counted more than once, so this is not physical phone memory usage or a replacement for the earlier same-build memory study.

VM153:8080/8084/8085 remain HTTP200, Build10 remains active, and the phone catalog still contains only source57 and source150. No reader code, catalog or stable installation changed. This is desktop Chrome mobile emulation, not physical phone or Safari qualification.

## Retained evidence

Artifact root: `validation-artifacts/segmentation-iteration-20261008/format-converter-v30-prefix6-transport-e2e-20261009/`.

- `converter-evidence.tgz`: 172,169,452 bytes; **668 regular members fully read and hashed**; SHA256 `cfebbb79c80d6a9ddae205577b445aafb975070006253bc6c9df7b16cbeac359`. Includes all four actual conversion directories, source/input evidence, copied ledgers, root receipts, executed harness and binding files. Extracted under `converter-evidence/format-converter-v30-prefix6-transport-e2e-20261009/`.
- `browser-evidence.tgz`: 36,334,438 bytes; **142 regular members fully read and hashed**; SHA256 `d4bb927eb10af5a09433b37953be1791132203aef6198f2bb959a755cea356da`. Extracted under `browser-evidence/`; exact results are `actual-formats-prefix6-v30-20261009/{pdf,cbz,cbr,folder}/browser-results/results.json`. Includes all screenshots, schema/profile checks, screenshot comparisons, harnesses, bounded process logs and cleanup receipts.
- Additive `visual-review.json`, `converter-archive-verification.json`, `browser-archive-verification.json`, `reader-health-after-browser.json` and `registry-receipt.json` bind the later human inspection, archive readback and lifecycle observations without rewriting either archive.

No new API calls, production rewrite, promotion or full257 traversal was performed by this validation.
