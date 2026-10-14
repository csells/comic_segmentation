# Automatic semantic ownership points

Bounded research generator for the semantic-point SAM spike. It sends unchanged
source pages and saved automatic scene boxes to Astra high once per page, using
the same generic prompt. It requests up to three exclusively owned interior
points per scene, with explicit abstention. It does not supply evaluation labels,
mask outputs, known defects, hand points, or new geometry.

`generate.py` runs only in VM153, with an API key on stdin. It reuses the existing
durable client/ledger: $100 total cap, at most three new ownership requests, and
a separate $2 experiment ceiling that includes unresolved reservations. Input
token preflight and the existing conservative output allowance apply. Completed
results are reused, unknown requests block, and there is no retry/repair loop.
Do not run it simply to recreate evidence.

The three source pages are 40, 57 and 150. These are development controls, not
held-out evaluation or runtime-specific prompt rules. Original and repaired
SAM proposal sets for the same source use exactly the same generated points.
The [SAM adapter](../sam2_semantic_points_v1/README.md) validates provenance,
maps points to source pixels, and applies frozen positive/negative selection.
Paid usage is recorded separately from local mask inference.
