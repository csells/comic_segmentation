# Independent comic fixtures frozen before inference

2026-10-09. Twelve input units from three artist/book groups are acquired and frozen for the next independent screen. No model calls, segmentation outputs, prompt tuning, or product changes occurred during acquisition. The existing anthology remains development material. Every new artist/book group is reserved for independent evaluation until the automatic policy is frozen.

| Group | Fixed primary inputs | Coverage observed in source-only contact sheets | Direction and terms |
| --- | --- | --- | --- |
| Randall Munroe, **xkcd** | 303, 327, 1052 | Sparse line art; one illustrated scene with a large caption; ordinary horizontal frames; dense, tall multirow strip | LTR visual convention. Author's [license](https://xkcd.com/license.html) is CC BY-NC 2.5. Exact image URLs come from each official `/info.0.json` endpoint. |
| Hiroshi Seo, **Ubunchu!**, episode 1, Japanese | Original numbered PNGs 01–06 | Color cover as a whole-page control; monochrome manga; portrait panels spanning rows; art, text, and balloons crossing rectangular frame boundaries | Genuine RTL: the [author's episode page](https://seotch.wordpress.com/2009/04/04/ubunchu01/) explicitly describes the original Japanese reading direction. Accompanying Japanese license names CC BY-NC 2.1 JP; English license names CC BY-NC 3.0. Both files are retained. |
| Cadu Simões / Fred Hildebrand, **Homem-Grilo**, *O Gnomo Azul — Parte 01* | Published filename groups `hq013pg01`, `pg02`, `pg03`, five chunks each | Modern color vertical comic; large interscene whitespace; detached and frame-crossing balloons; lettering outside panel rectangles | Top-to-bottom website sequence, Portuguese LTR lettering. The [official episode](https://homemgrilo.com/comic/o-gnomo-azul-parte-01/) supplies attribution; the [official site](https://homemgrilo.com/chapters/) declares CC BY-SA 4.0. |

This is **nine original pages/strips plus three webtoon sections**, not twelve print pages. The three webtoon sections belong to one episode and artist group. Each section contains its complete published five-chunk filename group in verified DOM order; a group is not claimed to be an original print-page boundary or complete episode. No source image was resized, cropped, mirrored, or edited. The WebPs were decoded to RGB, concatenated without gaps, and saved as lossless PNGs. Each constituent pixel region was compared with its decoded original and matched exactly. The manifest records each source byte hash and exact vertical offset.

The archived Ubunchu originals come from the [translation project's pinned archive](https://gitlab.com/ubunchu-translators/ubunchu/-/tree/9f065a3fde464be893dfba9fb5fc6abc93722cf9/chapters/01/ubunchu01_ja_release). The author-hosted ZIP and its linked mirror returned HTTP 404. The preserved edition identifies itself as version 1.03; the current author page lists 1.04. These are original Japanese pages preserved by that project, but byte equality with the unavailable current author ZIP is unverified. They are not a mirrored Western comic or an English translation.

Three additional Ubunchu pages, 07–09, were frozen and downloaded during acquisition to cover a possible strict conventional-page-count requirement. They are retained as supplemental unused material and are **excluded from the twelve-unit primary screen**. They do not create another independent artist/book group. Source selection and availability substitutions preceded every model output. The initial selection and explicit amendment are retained; missing downloads were not silently replaced after evaluation.

## Artifacts and verification

- VM source: `/home/tester/comic-reader/evidence/independent-fixtures-20261009`.
- Exported originals, full manifest, exact transformations, acquisition log, and source-only contact sheets: `validation-artifacts/segmentation-iteration-20261008/independent-fixtures-20261009/`.
- Reviewable compact manifest: [independent-fixtures-20261009.json](independent-fixtures-20261009.json).
- Full `manifest.json` SHA-256: `c6682e11e3126f65604105449673a3da03a9c71c37159a745a6bd142c7d7e898`.
- Standalone export: `validation-artifacts/segmentation-iteration-20261008/independent-fixtures-20261009.tgz`, 15,508,220 bytes, SHA-256 `314404c192afa30d884f91cd65e102d6d095202a190fd0dea3954ea11e2c36c8`. All 61 regular archive members were fully read and compared with the exported files. The adjacent directory contains `archive-verification.json`.
- Original downloads plus accompanying JSON/license records: 5,144,575 bytes. All image decodes succeeded. All twelve exported input hashes and every contributing original hash matched the VM manifest.
- Source sizes: xkcd 413×360, 666×205, and 605×1629; Ubunchu 1246×1635; webtoon sections 745×5435, 745×5240, and 745×5140. Source previews are evaluation conveniences and must not become runtime inputs.
- After acquisition, the existing staging reader still returned HTTP 200 and the VM retained 4,700,397,568 free disk bytes. No service configuration or application code was changed.

Inputs are grouped into `inputs/xkcd`, `inputs/ubunchu01-ja`, and `inputs/homem-grilo`. Keep attribution and applicable license information with any review copies. The manifest's evaluation fields and human review notes are not runtime prompt content; an explicitly supported user/book reading-direction option may use provenance-backed direction metadata.

## Remaining limits and next gate

Freeze the automatic policy before requesting inference. Review full source, actual emitted crops, reading order, and full-page-first playback; do not judge segmentation from an overlay alone. Count fallback as lost automatic segmentation coverage and record harmful accepted omissions separately. Retire any affected artist/book group into development if its results lead to prompt or policy changes; another page from that same book is not a fresh independent-book test.

The small screen supplies real RTL, ordinary frames, sparse scenes, cover handling, dense multirow layouts, tall color material, and crossing balloons. It does not establish general performance on double spreads, damaged scans, every borderless style, or entire unfamiliar books. No absence from model pretraining is claimed. Long webtoon sections particularly test whether preprocessing preserves readable detail; do not silently reduce them to tiny text and call a failure a model-only result.

Mimi & Eunice direct pages and the official Creative Commons *Sharing Creative Works* asset ZIP returned HTTP 403; they were not bypassed or acquired. One alternative Homem-Grilo episode's published first image and CDN URL returned HTTP 404. These sources are excluded. The accessible *O Gnomo Azul* original URLs all returned HTTP 200. No account, dataset agreement, external contact, paid request, or stable-service change was needed.
