# V32 seven actual quality controls

Prepared against the fresh, strict 191-file V32 source. The source changes only
actual-main selection of the exact B marked native adapter, its four runtime
asset pins, the V32 policy, and relevant tests. The guard, source ownership,
strong verification, controller, detector and repair behavior remain unchanged.
All 281 VM offline tests passed. V32 is not yet qualified by those tests or by B.

Use the exact original `prepared-controls-v1/run_controls.py:run_case` and frozen
materialized-controls-v1 histories, pixels, crops and geometry. Ordered cases:
P56 accepted; N56 whole_page_fallback; P6 accepted; N6 whole_page_fallback;
P57 accepted; N57 whole_page_fallback; N2 whole_page_fallback. This is an injected
post-refinement quality boundary, not detector or CLI E2E. Historical proposal
identities remain intentional fixture identities; actual V32 CLI computes its
own policy-bound identities. No quality flags, model answers or final outcomes
are injected. The real integrated judge visits targets, actual stronger checks
resolve warnings, and positive acceptance must pass the unchanged G callback
with a valid proof. No repairs, extra detector tiers or retries are introduced.

Paid execution stops on its first blocked or incorrect final outcome. Cache-only
execution visits all seven even after a blocked case to expose concrete pending
request identities, with all reservations, HTTP and sockets denied. It uses an
exact copied ledger under the existing integration lock and the actual Budget.
Observed misses are a lower bound; later branches may need additional calls.
No result from a blocked cache-only case is a quality judgment.

The exact V32 native-body inventory was reconstructed without Client/API calls:
61 unique bodies, 23 saved responses, 38 uncached, 0 unresolved. Missing target
bodies are N56=7,N6=6,P57=13,N57=12. P56/P6/N2 reuse B's23 saved targets. This
exceeds the old 28 remaining request slots. Root prospectively authorized a new
128-request shared helper if at least 29 misses were proven; 38 satisfies that
condition. The sole change from the qualified helper is request cap64→128.
The original helper is preserved. The shared integration dollar cap stays $3,
global stays $100, and all prior 36 requests/$1.047342 remain counted. No expense
increase, reset, or per-case allowance is granted. Any future envelope change
requires a separate prospective decision before dispatch, never a silent retry.

The canonical new helper is integration-budget-128-v1/integration_budget.py,
SHA 51e878a55f2dc8b80c0dea510c74f0be4abc4f120d3c2a3c9cf269dfada27631.
Its authorization receipt is a9aa633f31516e3cf3f1cac711d1fc7a786920109ffe31100580b9f133b91648.
Native demand proof is 4332d5676ddc435aaef972226c36bdf2ec6a78118cf1ebfe1c1a21f612824038.

Root owns all paid execution. The paid gate binds the strict V32 source manifest,
preparation manifest, runner/helper, unchanged seven-case order/expectations,
all three caps, cache preflight, passed independent review, diagnostic scope and
first-mismatch/no-recovery rules. Current source manifest is
195c2db619fd73f896be54b5ee09e5d735eb398118b5f6cefb339596f0630f44.
B root review f0f01b9ea228829e6ef7b2510278e9565094c866b2d0f41e70cf52db30885ba5
qualifies only B's three injected outcomes; V31 and A failures remain failures.

A successful execute terminal must say controls_passed, have all seven matching
statuses, harmful_acceptance=false and bound positive proofs. It still requires
a separate root semantic receipt binding that terminal and source manifest with
controls_qualified=true. Only then can independently gated V32 CLI checks use it.
No application promotion, publication or broad validation follows automatically.

## Completed validation

The actual cache-only seven-case run returned 81 cached responses and made no new calls. P56/P6 were accepted with valid proofs; N6/N57 failed their source-ownership gates; N2 failed stronger crop verification. N56/P57 blocked at uncached native targets. The observed four request-frontier misses were not a complete remaining-call estimate: the offline 38-body inventory includes 18 target bodies skipped by N6/N57's early source gates.

Root then executed the frozen runner and all seven final outcomes matched. No proposal geometry, crops, runtime flags or model answers were changed by a person.

| Case | Final outcome | Decisive path |
|---|---|---|
| P56 | Accepted | Native checks and G completeness pass |
| N56 | Whole-page fallback | Strong crop checks clear surviving crops; G still rejects the omitted view |
| P6 | Accepted | Ownership verification clears the native alarm; G passes |
| N6 | Whole-page fallback | Source ownership detects the omitted inset before target calls |
| P57 | Accepted | Strong ownership checks clear the complete candidate and all 13 targets; G passes |
| N57 | Whole-page fallback | Source ownership detects the omitted view before target calls |
| N2 | Whole-page fallback | Stronger crop verification confirms clipping |

The paid terminal is `c87ed9262d56ab7c297d3277c4f8a8adbeb6e1091ab5bdd722bd3918361453ef`. Root's semantic receipt `0f1d8de26e9de7fe155795d13228a592e52796c8179972996742fe29989e3475` qualifies these controls and explicitly leaves application E2E qualification false. Root confirmed all 31 positive source/crop image bytes and geometry match the personally reviewed correct outputs, and reviewed the negative causes.

The run used 22 new calls and 103 cache returns, costing $0.036678. At control completion, shared usage was 58 requests and $1.084020 of $3, and global usage was $54.793202 of $100. The prospective shared request ceiling is 128; the dollar caps and all historical entries were retained. There were no retries or unresolved new holds.

The post-run audit reconstructed all 125 request fingerprints from their exact image bytes and saved request bodies, verified request/response/result hashes, recomputed all 22 costs from saved usage, confirmed each new request settled once, and revalidated the three positive G proofs without Client/API calls. Audit receipt: `6502c7bbe19bf658100f2e7dfc409da40337d8b6f9e01bb22662f035ce9403a3`. Root owns the separate visual review.

This validates the integrated quality boundary on the seven frozen proposals. Detector behavior, actual CLI publication/resume, the five-positive reader checks, four-format regression, independent books and the full PDF remain separate qualifications. V31's harmful acceptance and A's native false rejection remain preserved failures.


## V32 actual-main resume and corruption checks

After the seven controls passed, the existing real CLI resume fixture was adapted only for the V32 source, policy, output paths and a second actual output (source pages 1 and 56). Ten calls to the real `auto_convert.main()` ran in VM153 against disposable copies. Both pristine resumes preserved the exact published CBZ and produced one completion. Each of the four corruptions failed before a new completion: changed prepared source bytes; changed selected and attempt geometry; a forged completeness decision with its reference hash updated; and changed publication inputs with their digest updated. The failures came from the expected source, bundle geometry, completeness replay and publication binding checks.

The fixture denied model requests, budget reservations and network access; none were attempted. Both original output trees, referenced original proofs, strict 191-file source inventory, shared ledger and each copied ledger remained unchanged. The fixture did not change application code or make a model call.

- Runner SHA-256: `5472c1aba5ee7b5a6cc8d038b4b1d983ce360a675a517075d4c4099de283fd36`.
- VM terminal: `v31-integration-20261010/cli-rejection-v32-v1/receipt.json`, SHA-256 `a63a3377f043a172fd737f27eede136a0cedd772c52c1f00961264d64fb6dff8`.
- Page 1 receipt: `c3c51ca5caab4495a66f88e0cf233c51a1e8dc8e0c681f844a05670b268a428c`; page 56 receipt: `b2195bdd0549bfc7d40adf2c33c5bfd3978f54b3c153171b6306cdfbdf4241d1`.

These checks cover resume and publication integrity for those two completed V32 outputs. The independent comic screen, four-format prefix validation and full-book run remain separate requirements.


## Retained artifacts

All archive members were fully read and verified on VM153 and again after copying to the host artifact directory `validation-artifacts/segmentation-iteration-20261008`.

- Controls preparation/cache: `v32-controls-preparation-20261010.tgz`, SHA-256 `b1598fb0b47a9b31c582d4befcb588e7b054319155ac42f6aa0f7d65a6305d59`, 45,348,947 bytes / 591 regular files.
- Completed controls/audit/root review: `v32-controls-completed-20261010.tgz`, SHA-256 `79b3820442d20a152d9d800facb3fd2ffbae8786dc80e0f38a44192ffe7536fb`, 53,190,618 bytes / 444 regular files.
- Actual-main resume/corruption fixture and all copied trial evidence: `v32-cli-resume-corruption-20261010.tgz`, SHA-256 `812923ab8c81473a0fd0c28ee4bb6a9e45ba4ce687132eb19b605569bfb980a7`, 82,143,327 bytes. This content-addressed archive retains all 2,882 regular files through 343 unique byte blobs and a path/hash index; duplicate bytes are stored once.

Independent peer review of the complete V32 resume fixture, ten execution logs, exact mutations and unchanged copied CBZ/ledger bytes passed without rerun or API use. Additive receipt: `v32-cli-rejection-prepared/independent-review.json`, SHA-256 `e8b322a5cb8e197a1dfa3aa27b013da254e881cdd63f54db1b5a7604ad5bb001`; retained separately from the frozen resume archive.
