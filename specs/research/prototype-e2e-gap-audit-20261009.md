# Remaining prototype acceptance work — 2026-10-09

Static audit after the scene-identity v1 stop, before the next experiment. This
audit made no API calls, executed no prototype, acquired no comics and changed
no VM or reader. The current handoff is authoritative: V28 qualifies pages 1–56,
page 57 falls back, older-policy review reached 150, and page 151 has not run.
Build 10 remains the earlier 17-page automatic sample. The shared ledger's latest
documented used/held amount is $39.373507 of $100, including $4.30 unresolved
holds; the broad research report's $39.009825 allocation is historical.

## What is already established

The actual automatic entry point is
[`auto_convert.py`](../../prototypes/panel_quality_probe/auto_convert.py), not the
older Pannello runner. It prepares input, invokes the bounded
[`automatic_escalation.py`](../../prototypes/panel_quality_probe/automatic_escalation.py)
controller, builds full-page CBZ/ACBF through
[`adapter.py`](../../prototypes/comic_panel_e2e/adapter.py), and records routing,
hashes, output and usage. It has no human-routing callback.

The [17-page integration run](automatic-conversion-e2e-20261008.md) exercised
actual PDF input, cached and fresh detection, automatic escalation and refinement,
CBZ/ACBF output and every emitted reader step. Prepared and served builds each
passed 112 assertions at 390×844 with no browser exception. CBZ-to-CBZ and
folder-to-CBZ versions each used 153 exact cache hits, no new call, and retained
all 17 source image bytes. The folder run and a final PDF replay disabled HTTP.
This establishes transport and integration for that older policy; it does not
qualify V28 or a future ownership policy.

Page-first navigation is implemented separately from metadata in
[`guided_sequence.js`](../../prototypes/web_panel_reader/guided_sequence.js):
overview, then XML panel order; empty or whole-page geometry appears once.
Existing browser tests cover the deliberately non-geometric 3→1→4→2 order,
previous navigation, page boundaries, rotation, page mode, local-file loading,
resume and visible malformed-input errors. Reuse this evidence unless affected
code changes; exercise the actual new artifact through the hosted reader.

## Critical path and concrete completion evidence

| Step | Required result | Evidence that does not suffice |
| --- | --- | --- |
| Required scene evidence | Missing/uncertain inventory routes safely; populated but wrong ownership or incomplete descriptions cannot conceal a real defect. Include intact crops whose incidental neighboring artwork is cut. Freeze labels separately before requests. | A presence guard, rotated descriptions that still contain the correct facts elsewhere, or another pass on the same three correlated page-150 controls. |
| Automatic correction | The integrated controller derives corrections from source and machine evidence, then independently checks scene inventory, order, ownership, meaningful content and useful viewport. Source-57/150 failures and intact regressions pass without supplied labels, manual coordinates or human branch selection. | Isolated verifier accuracy, attractive masks, correct panel count or source-connected pixels alone. |
| Actual candidate E2E | Run the changed converter from a real source through automatic routes to its own new CBZ, with frozen code/prompt hashes, shared budget and exact cache provenance. Review source and every changed final crop. Run the emitted artifact through schema/parser and the phone reader. | Packaging hand-selected known-good geometries, changing metadata after conversion, or publishing an isolated crop experiment. |
| Independent books | Freeze book/artist groups, original hashes, transformations, expected scenes/ownership/order and a finite request budget before inference. Run the frozen policy without tuning; report strict page pass, false acceptance, fallback, cost and latency by book. | Adjacent pages of this anthology, multiple strips counted as multiple artists, or test examples reused for tuning and still called held out. |
| Full source PDF | Resolve the page-57 pattern, revalidate affected earlier outputs, then continue sequentially to 257 with personal source/crop review and no runtime interference. Stop and repair generically on recurring defects. Publish only the resulting actual automatic artifact. | Historical review through 150, current prefix 1–56, or the old 257-page Pannello artifact with known failures. |
| Phone review candidate | New disposable build and review endpoint preserving Build 10; exact output hash matches the served CBZ. Traverse all page/panel steps, confirm full-page first, then inspect portrait/landscape crop readability and fallback behavior. | A gallery entry, HTTP 200, parser success, screenshot of an overlay, or desktop emulation described as a physical-phone pass. |

Prototype development and staging are authorized. Production Rust implementation
and promotion remain separate decisions; completing the rows above is not an
implicit promotion approval. Reader refresh can expose an improved staging
candidate without app installation.

## Input and metadata gaps that affect the next candidate

1. **Real CBR remains untested.** `prepare_input()` contains a libarchive path and
   rejects traversal, duplicates and nonregular entries, but no real `.cbr`/`.rar`
   fixture was found in the ignored local artifacts. Qualify at least one genuine
   compressed RAR through extraction → equivalent pixels → cached automatic
   analysis → output → reader. Name the exact supported RAR4/RAR5, solid and
   encryption scope; archive hardening beyond that is later product work.
2. **Accepted image formats exceed reader formats.** Import accepts BMP, GIF and
   WebP as well as PNG/JPEG, and publication preserves the original extension.
   `acbf.js` rejects all page extensions except PNG/JPEG. This directly affects
   the proposed Homem-Grilo WebP source. Add a documented canonical publication
   transform, preserving original bytes and source hashes, or fail preflight
   before paid inference. Animated/multipage input and EXIF orientation need
   explicit handling; inspecting the first frame without qualification cannot
   establish complete-page preservation.
3. **RTL is not generic yet.** `prompt-v6.txt` explicitly describes a left-to-right
   comic and forces `reading_direction ltr`; publication also hard-codes `ltr`.
   `build_cbz()` validates direction and records it only in the manifest. The
   original reader looked for `book-info/reading-direction`, but a later check
   of the official pinned and current ACBF 1.1 schema found no such standard
   field. Candidate code now carries an optional hash-bound companion profile;
   VM validation and converter direction integration are still pending at this
   audit. Do not mirror a Western page as native RTL qualification.
4. **Input order is currently filename-based.** Folder/archive import uses natural
   relative-path sorting and retains existing metadata as auxiliary data; it
   does not consume an existing ACBF page map. Equal natural-sort keys have no
   explicit bytewise tie-break. For the prototype, freeze unambiguous fixtures
   and report this limitation; the planned explicit order/metadata precedence
   policy is not implemented.
5. **Single-image books are explicitly rejected.** The adapter requires a cover
   plus a body page. Do not silently duplicate an independent one-page comic to
   pass it. Use an explicitly documented multi-page fixture group, or resolve the
   publication contract before advertising one-page source support.
6. **Full-book reader size remains a gate.** The web reader limits archives to
   128 MiB, 600 pages, 2,000 entries, 32 MiB/entry and 512 MiB declared expanded
   size. It checks 40 MP after decode. Inspect the generated full-book archive
   against these limits and measure actual staged memory/readability before
   changing limits. A larger reader cap alone is not a memory fix.

Container parity tests should reuse identical page pixels and cached or recorded
analysis, blocking HTTP. They test import/publication behavior independently of
detector quality and should not spend again on equivalent images. Compare page
hashes/order, auxiliary preservation and frame sequences, allowing intentional
document UUID/time differences. Existing collision, resume, unknown-charge and
budget checks remain useful; rerun the affected subset when integration changes.

## Research scope: completed screens versus conditional leads

The committed bounded shortlist is complete: native-PDF resolution/source audit,
paneldet, marked cheaper verifier controls, 32 seeded watershed/GrabCut variants,
ShadowB, KoharuLayout, SAM 2.1 box prompts/alternate masks, automatic semantic
points with box-plus-points and points-only ablation, and scene-identity v1.
Their failures remain controls. No threshold sweep or identical paid replay is
owed merely because the user asked to finish the spikes.

Magi v3, SAM 3, random walker, PanelForge, additional preprocessing and alternate
YOLO/Florence/document models are literature leads with specific limitations,
not unfinished committed experiments. Trial one only if a concrete unresolved
capability justifies its pinned version, inputs, finite runtime/cost and stop
condition. The directly supported next hypothesis is source-linked ownership
evidence plus boundary completeness, because scene v1 changed the observed
page-150 outcome while omission exposed unsafe behavior.

## Independent source availability

No xkcd, Homem-Grilo, Mimi & Eunice, Little Nemo or native RTL fixtures were found
in the local ignored artifact filenames. The prior
[fixture review](mask-evaluation-review-20261009.md) verified accessible headers
for xkcd and Homem-Grilo but did not acquire image bodies. Those represent two
artist groups, not the proposed three-book baseline. Homem-Grilo WebP needs the
format fix above. LOC/Nina Paley access was unresolved; Pepper & Carrot needs its
current terms considered. Genuine native RTL, independent borderless book and
four-panel/spread coverage remain unfilled. Do not describe planned or accessible
sources as acquired, annotated or qualified.

Execution belongs inside the isolated candidate VM. The current paths recorded
in the handoff are `/home/tester/comic-reader/source/panel_quality_probe`,
`/home/tester/comic-reader/source.pdf`, verified rendered pages under
`replay-local/pages`, and shared ledger
`evidence/gemini-10usd-20261008.jsonl`. Refresh the authoritative home-lab registry
before operational changes. Preserve Build 10, prior candidates, raw responses,
unknown holds and the verified off-VM archive chain.
