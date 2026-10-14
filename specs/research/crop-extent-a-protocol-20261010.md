# Crop extent A: marked-context native diagnostic

Status: **completed and failed** on the third case. Root launched the frozen revision 2 screen after both independent preparation reviews passed. Preparation used no inference; the diagnostic then made three native requests and stopped at its first false rejection. No application integration or production geometry changes occurred. V31 remains unqualified.

## Question and fixed change

Does the existing native Luna target text/art judge distinguish additional crop damage from an original artist cut when it receives exact marked local source context and an explicit original-cut clarification?

Historical unmarked context failed. This experiment uses the existing frozen `target_detail.with_source_detail(..., mark_boundary=True)` without editing it: full source, exact actual crop, clean source detail, then that detail with a generated red rectangle at the actual inclusive crop coordinates (converted to exclusive right/bottom for drawing). The detail adds 6% of source width/height, with a minimum 64 source pixels, clamped to the page, and displays at up to 2×. The original source and actual crop bytes remain unchanged.

The native model remains `gpt-6-luna`, with two independent `predicate` questions named `text_clipping` and `art_clipping`. The current target-v3 text predicate is unchanged. The current art predicate is preserved and followed by:

> An artist's original cut excuses only that original cut. A candidate boundary further inside the same scene that removes additional visible artwork or background is a defect, even if a subject was already partly outside the original frame. Compare the top, right, bottom and left actual crop edges separately against the original scene; do not stop after finding that one edge matches an original cut.

The unchanged native base prompt and target-selection instruction receive an explicit override: “There is exactly one target output crop: image 2. Image 1 is the complete source; images 3 and 4 are source-only context, never additional candidate crops. Evaluate only the supplied two predicates for that one target.” They also receive uniform guidance to compare all four actual crop edges, explaining the clean/marked source pair and that the red line is generated. No case name, source page number, expected answer, object hint, detector description, old answer, or evaluation label enters any request. Panel metadata is reduced to `order` and `box` before the existing `judge_payload` builder runs. Target ordinal and candidate geometry remain legitimate runtime inputs.

## Fixed order and labels

These labels are evaluation-only. Root personally reviewed current CLI images and reopened the exact historical unpadded P150 controls. The known quarantined P57/6 is excluded.

| Order | Case | Expected |
|---|---|---|
| 1 | N2, clipped source56 target7 | Art defect |
| 2 | Current CLI source56 target7 | Intact |
| 3 | Current CLI source6 target1 | Intact |
| 4 | Current CLI source6 target2 | Intact |
| 5 | Current CLI source6 target4 | Intact |
| 6 | Current CLI source6 target5 | Intact |
| 7 | Current CLI source57 target8 | Intact |
| 8 | Current CLI source57 target10 | Intact |
| 9 | Current CLI source144 target1 | Intact |
| 10 | Historical original source150 target3 | Art defect |
| 11 | Historical corrected source150 target3 | Intact |
| 12 | Historical corrected source150 target2 | Intact |

The P150 triplet is the exact control-audit, unpadded crop bytes retained in the v5 original/corrected bundles: original3 `6c2311dcb0812b319cccb84634019c617c722d775a48334b9459f7198124b83d`, corrected3 `de439d0e649b9a0023edeb077091487a8e0c3c3432966a579466ab16d0fcee92`, corrected2 `af023e46688b619d390ba33f2997f67618ab3b655fdf13ec87295c32d50796dd`.

An intact case matches only when **both probabilities are below 0.5**. A negative matches only when **art probability is at least 0.5**; text alone cannot rescue an art miss. Stop immediately at the first mismatch, including false rejection, malformed/refused answer, transport/usage failure, unknown prior request, or budget block. There is no Sol fallback, prompt change, repair, automatic retry, or continued inference after a failure. Root must review any result before proposing another experiment. Even all twelve matching would be a limited diagnostic result, not production qualification.

## Bounds and evidence

All execution stays in VM153. Root alone may launch paid inference. The existing `auto_convert.Client`, native parser, actual ledger `Budget`, and unchanged qualified `integration_budget.py` are reused. The global cap remains $100; the **same existing integration envelope remains $3 and 64 requests in total**, with all previous settlements/holds counted. Preparation observed 12 integration requests and $1.014537 used/held; global $54.723719. No new allowance is allocated. At most one new native call per fixed case is possible, with cached saved responses reused by exact request identity. No recovery flags are supplied.

VM paths, relative to `/home/tester/comic-reader/evidence/v31-integration-20261010`:

- `crop-extent-A-prepared-v2/`: materializer, runner, minimal checks, exact native prompt/questions and qualified helper.
- `crop-extent-A-materialized-v2/manifest.json`: all twelve exact sources/crops/geometry/context and evaluation-only evidence bindings.
- `crop-extent-A-cache-only-v2/`: actual Client preflight with a copied ledger, denied reservations and denied network.
- `crop-extent-A-v1/`: prospective immutable paid output; absent during preparation.

Frozen material manifest: `89b4e9a44a2a68c7c2b005e9ea91e59616e35d94e45dc69fd92f4e5fbf0835fd`.
Frozen runner: `c54ae580bc5906072fc1bd1f0da3ab1814e13bdd8b2a48aa5d4376a5104ed132`.
Frozen source manifest: `3dda1a1996ebd7a96a040a5f848501f4929eb494a6ac142720dfaeaacbaaa3d5` (strict 186 files, no symlinks/extras).
Shared helper: `2ab955cd8beef57c69ab7efc5037b7a38df2b015f020bfa71b7129faf487b576`.
Failed V31 controls terminal: `c4c0aba9c468c5a6acb3aa48a5825715401af5c4165c3f165583dbf9315c409b`.
First N2 native fingerprint: `0fc0256f358639ef3f69a2952c0582b82a5e9eeb4148004c71bb72ee34fb745c`.
Cache-only terminal: `1a879e13b051be0484f1a514f21e0f1308a0ade4958f970499ee9bbe2033d863`.

Seventeen VM checks passed: all twelve native bodies with exact four-image hashes and geometry-only fields, unchanged text predicate, fixed thresholds, actual image tamper refusal, first negative mismatch stop, positive false-rejection stop, and malformed-answer stop. The real Client cache preflight stopped at the first new N2 native reservation, before HTTP: zero model calls, zero reservations, unchanged shared/copied ledger and frozen source. This verifies dispatch readiness, not model correctness.

The paid root gate must bind runner/source/material/helper hashes, the exact order/output, all unchanged budget caps, diagnostic-only/first-mismatch/no-recovery flags, this cache preflight, and a passed independent review receipt. The runner rechecks all evidence before and after execution and records actual response provenance and accounting. Existing source, old answers, old controls, unrelated data and prior prepared-but-unqualified sequential work remain intact.

Preparation revision 1 is retained unchanged in its original directories. Before any paid request, independent content review identified the inherited base prompt’s stale four-predicate/crops wording. Revision 2 adds only the explicit one-crop/two-predicate override above and regenerates hashes and offline receipts. No observed model answer informed this preparation clarification.

## Completed result — first mismatch stop

Root execution produced terminal `b8c5542ee1809a3850a9582da4c1f4bb920971f25f93bcd3154e8b761db000fd` at `v31-integration-20261010/crop-extent-A-v1/terminal.json`. The exact frozen runner and body identities were used; there was no retry, fallback, prompt adjustment or later-case inference.

| Case | Text probability | Art probability | Result |
|---|---:|---:|---|
| N2, deliberately clipped source56 target7 | 0.00 | 0.67 | Correctly flagged |
| P56-7, intact current CLI crop | 0.00 | 0.30 | Correctly kept |
| P6-1, intact current CLI crop | 0.04 | 0.83 | **False rejection; stopped** |

Root reopened source6 and actual crop1 and confirmed the upper room scene is complete. The partly visible watch inset belongs to another scene and is incidental; its incomplete appearance does not make target1 defective. The native response contains probabilities, not a rationale, so attributing its false alarm specifically to that inset remains an inference. The remaining nine cases were not evaluated.

The marked-context/original-cut change provided useful evidence that the N2 miss can be detected, but **A failed its fixed diagnostic criterion** and does not qualify as a final acceptance/rejection rule. No candidate is adopted or repaired from this experiment. The next bounded question is whether the actual existing stronger escalation rejects the clipped target while clearing this intact target; that requires separate frozen evidence and root authorization to dispatch, and is not a result of A.

Three new native calls cost $0.001853, with zero cache hits. The same integration envelope now records 15 requests and $1.016390 used/held; global usage is $54.725572 of $100. Prior ledger rows were preserved. The gate was `b807440d64c873d2367a5ba4b6fede3e15c20539e7636baffd4fe7fcf0a129cf`; ledger after the diagnostic was `527230a5a519378c75b2710902628410ea46c82a301a093ffaf87de476bb9a7e`. Raw failure results and all three responses remain unchanged.

Root's completed semantic review is `4ba74375869ce247ec8677cfb1b24f6e420deeca47c85ca1437382f78c3511a9` and explicitly leaves the screen unqualified. Preparation was exported as `crop-extent-A-preparation-v2-20261010.tgz` (36,434,401 bytes, 410 regular files, SHA `8b84bff382cd1300127f6c311f7645b89b6434ad63dea6d31657680423c3f6d1`). Completed evidence was exported as `crop-extent-A-completed-v1-20261010.tgz` (12,509 bytes, 18 regular files, SHA `83ab19375ea42cef2f2f384ccc4f7ab86223d6c4bb3b8d2f3ab0aa98634624fd`). Both archives were copied off VM153 and every regular member was read and verified against its hash index. The completed archive contains the paid gate, three raw requests/responses/results, terminal, root semantic review, and the failure protocol update. Archiving made no API calls or candidate changes.
