# comic-panel

`comic-panel` converts a comic you own into a CBZ that a compatible reader can
navigate panel by panel. It is the Rust implementation of the V63 prototype in
`prototypes/panel_quality_probe` (policy `automatic-marked-target-completeness-v63`).

Inputs: a PDF, a CBZ/ZIP, a CBR/RAR, or a folder of page images.
Output: a new CBZ containing every complete page unchanged, root `metadata.acbf`
(ACBF 1.1 frames in reading order) and `panel-reader.json` (reading direction).
Sources are never modified.

## Build

Requirements: Rust 1.85+, a C compiler, `cmake` and `nasm` (libjpeg-turbo and
zlib-ng are built from source and linked statically).

```sh
cargo build --release
```

Runtime tools: Poppler's `pdfinfo`/`pdftoppm` for PDFs and `bsdtar` (libarchive) for CBR/RAR.

## Run

```sh
dcli read 'dl://OpenAI Project API Key/content' | \
  comic-panel book.pdf runs/book --ledger ledger.jsonl --budget-cap-usd 100 \
    --page-cap-usd 0.50 --auto-transient-recovery --reading-direction ltr \
    --title "Book title" --execute-approved
```

- The API key is read from the first line of stdin and is never written anywhere.
- `--ledger` is a durable JSONL spending ledger. Every paid request is reserved
  before dispatch and settled from reported usage. `--budget-cap-usd` must equal
  the ledger's effective cap, so raising a cap needs an explicit ledger amendment.
- `--page-cap-usd` limits first-pass spending per page. A page that reaches it
  stops escalating and is published as a reported whole-page fallback.
  Cached answers count at their recorded cost, so cached and cold runs make the
  same decisions.
- The run directory is resumable: rerun the same command to continue. Use
  `--max-new-pages N` to checkpoint, and `--pages 3,7,9` to process a subset.
- Unknown request outcomes never replay automatically. The `--retry-*` flags
  name one explicit, separately reserved recovery for a recorded failure.

### Offline replay

`--offline` denies every reservation and network call, and needs no key. Each
request is a SHA-256 of its exact body, so replay reuses any byte-identical
request recorded in the ledger, including the prototype's. A miss blocks the
page with `CACHE_ONLY_MISS` and changes nothing.

## Pipeline per page

1. Detection: Sol-low, then Sol-high, then Astra (`gpt-6-sol`/`gpt-6-astra`).
2. Deterministic source-pixel refinement: dark gutters, lettered balloons,
   framed ink, black-page fringes, plus a small reading margin.
3. Quality judgement. Layout risks escalate. Inventory and continuity checks run
   on source regions. Native decisions are made globally and per marked target.
   Crossing-art and occlusion screens and source-ownership evidence run on risky
   layouts.
4. Verification: Sol/Astra verifiers can clear only their own alarms.
5. Final source-completeness gate H: an independent inventory mapped onto the
   proposed steps, with a replayable proof.
6. At most two verifier-directed geometry repairs, one deterministic component
   repair, one completeness-driven redetection (plus one repair of it) and one
   deterministic merge of unreferenced steps. Otherwise: whole-page fallback.

## Outputs

`automatic-panels.cbz` and `book.manifest.json` are published together.
`page-NNNN.json` records every attempt and the selected candidate. Request and
response records, candidate crops and completeness proofs are also kept.
`completed-*.json` summarizes accepted, fallback, escalated and refined pages.

Exit status: `0` means the book was published (fallback pages are listed in the
summary). `2` means the run is blocked: a budget, account or unknown request
state that is resumable after inspection. `1` is any other error.

## Parity with the prototype

The port reproduces the prototype byte for byte wherever bytes reach a request:

- Python `json.dumps` serialization;
- libjpeg-turbo with Pillow's defaults;
- Pillow's LANCZOS resampling and rectangle drawing;
- OpenCV's labeling order, closing and CCOMP contours;
- NumPy's quantiles.

`tests/differential/` holds the checks:

- `refine_cases.py` runs the prototype refiners on every page; `cargo run --release --example refineprobe`
  must match them exactly.
- `v63_replay_oracle.py` replays the frozen prototype from the recorded cache;
  `replay_all.sh` replays the same pages with this binary;
  `compare_replay.py` compares the page records.
