# Scene-assistance verification experiment

Research only, fixed before inference on 2026-10-09. Runtime and tests execute
inside VM153; existing converter policy and reader stay unchanged.

Question: does a fallible automatic scene inventory improve Sol-high's marked
source-detail crop verification, while resisting omitted/wrong scene evidence?
Astra-high generates descriptions once from the full source plus the ORIGINAL
automatic proposal inventory. It receives no crops, corrected proposals, reviewer
findings, expected labels or defect descriptions. All variants reuse that output.

Three freshly reviewed controls use page150: original target3 (missing upper
bouquet/ribbon), corrected target3 (complete), corrected target2 (complete middle
scene despite incidental clipped bouquet from target3). These expected answers
are evaluation-only. The older page57 target6 negative is quarantined: the saved
rejection discusses the neighboring brown face, not the intended cyan scene;
the small taper difference has no sufficiently confident completeness label.
No page57 pair is scored in this experiment.

Fixed sequence: three Sol-high v2 baselines; the same three with auxiliary scene
hypotheses; then original/corrected target3 with rotated descriptions; then the
same pair with descriptions omitted. Rotation preserves order IDs but maps
1<-2, 2<-3, 3<-1. Omission keeps the identical handling instructions. This tests
the combined instructions-plus-description package; omission also checks the
instruction-wrapper contribution. No prompt tuning or retries on these controls.

The original target3 baseline must match its saved request fingerprint and cache.
The two missing baselines may each be measured once. At most ten new requests
including one generator; $5 local ceiling within the shared $100 ledger. Durable
unknown holds count against both caps. Stop all remaining calls on the first
nonbaseline harmful acceptance, invalid output, unknown request or budget block.
A baseline failure is evidence, not a stop. Positive rejections remain failures.

Pass requires correct explicit defect evidence on the negative and acceptance
of the positives in every treatment/robustness condition. Uncertainty is safe
escalation, not a quality pass. Routing gates run automatically; a separate
post-run visual review checks evidence correctness without editing requests or
answers. Even a complete pass is one-source development evidence, not held-out
accuracy, E2E qualification, or permission to integrate.

`run.py prepare` saves immutable hashes and input bundles before any paid work.
`run.py execute` reads the credential from stdin, preserves requests/responses,
and writes terminal state and spend. Never execute it on the host or rerun a
terminal experiment. Tests: VM Python `-m unittest -v test_protocol`.
