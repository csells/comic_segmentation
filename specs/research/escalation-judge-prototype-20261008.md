# Decision-model escalation prototype — 2026-10-08

Status: **historical preparation, superseded by the completed
[native OpenAI Decisions test](openai-decisions-judge-20261008.md).** Chris clarified
that Laya is the separate open-source text/JSON model, then explicitly authorized
testing OpenAI Decisions. Fourteen native Decisions calls completed; the old
Responses-based judge below was never executed. The historical ambiguity and
approval block no longer apply to that authorized test. Current used/held total
is $4.603790 of $20. Preserve the preparation evidence and frozen labels.

## Historical preparation checkpoint (before clarification)

Original status: implemented and verified offline; live model test awaited confirmation.
Chris proposed using “laya” to decide when segmentation needs escalation. The
likely interpretation is GPT-6 Luna, but that name has not been confirmed.
Automatic approval review rejected the attempted 14-case upload on that ambiguity.
No judge request or new generation call was sent. The user has been asked whether
to send these existing private page images/crops to GPT-6 Luna via OpenAI, using
the same key and shared $20 cap. Do not bypass the rejection or treat elapsed
time as approval.

## Concrete experiment

The candidate judges saved detections rather than generating boxes. Input is the
original full page, numbered proposed rectangles, each crop in reading order and
normalized candidate geometry. Labels, generating model, source run, source page
identifier and existing review findings are excluded from the API payload.
Images can naturally contain printed page numbers; the claim is about metadata,
not removing source content. The model receives no reference answer or repaired
coordinates for comparison with a different candidate in the same request.

Fourteen frozen cases cover twelve original low-v4 pages and the two selected
repairs. Expected outcomes were recorded before any judge call: twelve usable
candidates and two defective candidates (raw low-v4 pages 100 and 205). This tests
whether the judge detects known edge/balloon failures while accepting both the
repairs and the other good pages. It does not yet test detection of merges,
missing scenes, false splits or wrong order on a separate corpus.

The trial is blinded to labels, not an independent held-out benchmark: the prompt
includes general failure categories learned during earlier research, and two
pages occur in original and repaired versions. Even a perfect result would
justify a larger test, not a production quality guarantee.

`judge-prompt-v1.txt` asks for scene inventory, reading order and crop coverage.
Structured output includes accept/escalate/uncertain and grounded issue evidence.
The prototype keeps a candidate only if all three checks pass, the decision is
accept and no issues are reported. Uncertainty or contradictory issues route to
escalation; malformed/refused/incomplete responses stop the run without accepting
anything. It never changes geometry or automatically invokes the stronger model.
First measure routing quality, then qualify the complete escalation loop.

The existing ACBF adapter supplies pixel endpoints for diagnostic crops, with the
endpoint pixel included. Input images and candidate geometry have hashes. The
raw and repaired page-205 balloon crops were visually checked after preparation:
the former still clips lettering; the latter contains the entire balloon. The
published twelve-page book remains unchanged.

## Execution and accounting

All candidate execution stays in disposable VM153. New helpers:

- `prepare_judge_cases.py`: source-hash verification, frozen images and labels.
- `escalation_probe.py`: explicit model, original-detail images, high reasoning,
  strict schema, 8,192 output-token cap, no retries, unknown-attempt protection.
- `test_escalation_probe.py`: fail-closed routing, refusals/malformed output,
  missing outcomes and payload label exclusion.

Nineteen offline tests passed inside the VM, including the existing API/budget
tests. An observed failing regression test exposed an accounting bug: model
rates were rounded to quarter-dollar increments before token multiplication.
Decimal arithmetic now preserves fractional rates and rounds only final
micro-dollar totals upward. Existing ledger history remains intact; eight
corrective settlement events adjust the earlier Luna and 5.6-Luna estimates by
net **+$0.000887**. Gemini unknown holds are unchanged.

Corrected historical four-page estimates: Luna **$0.006279** (previously
$0.004743), 5.6 Luna **$0.018659** (previously $0.019308). Their quality failures
and Sol selection are unchanged. The current shared total is **$4.595248
used/held of $20**, including $3.60 unknown holds. Forty OpenAI segmentation
successes remain; there are zero judge calls.

The existing conservative Luna rates were rechecked against the
[official model page](https://developers.openai.com/api/docs/models/gpt-6-luna):
$0.125/M input covers cache writes and $0.50/M output includes reasoning. Standard
service only; no tools, regional processing or discounts. With at most 60,000
input tokens and 8,192 output tokens, each call reserves $0.011596; fourteen
reserve at most **$0.162344**. Token preflight refuses larger input before generation.
The runner uses the existing locked, fsynced ledger, never a fresh allowance.
Missing usage keeps its reservation; no implicit retry/model substitution.

An actual offline preparation run built all fourteen requests with zero network
calls and an unchanged ledger hash. It is not evidence of model performance.
Private files were exported to ignored `validation-artifacts/segmentation-iteration-20261008/`:

- `judge-cases-v1-20261008/`: manifest, separate evaluation labels, input bundles.
- `luna-judge-v1-offline-20261008/`: fourteen prepared requests; no responses.
- `judge-offline-validation-20261008.json`: actual preparation/accounting checks.
- `judge-budget-correction-20261008.json`: per-request accounting correction.
- `budget-after-fractional-rate-correction-20261008.jsonl`: fresh ledger snapshot.

After confirmation, run the prepared manifest once into a fresh live output
directory. Report false accepts of defective cases and unnecessary escalations
of usable cases separately, alongside usage/latency and each visible rationale.
Do not mark unknown/missing results correct or let the model grade itself. If a
result disputes the frozen label, inspect the original/crops and record any
correction explicitly. Preserve all versions and failure evidence.
