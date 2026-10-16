# comic-panel

`comic-panel` converts a comic you own into a CBZ that a compatible reader can
navigate panel by panel. Each original page is kept unchanged. Root
`metadata.acbf` (ACBF 1.1) lists each page's panel frames in reading order.
`panel-reader.json` records the reading direction, bound to that metadata.
Sources are never modified, and outputs are never overwritten.

Inputs: a PDF, a CBZ/ZIP, a CBR/RAR, or a folder of page images
(JPEG, PNG, BMP, GIF, WEBP).

## Install

Requirements:

- Rust 1.88 or newer.
- A C compiler and `cmake`. On x86-64 Linux, also `nasm`. libjpeg-turbo and
  zlib-ng are built from source and linked statically.
- Poppler (`pdfinfo`, `pdftoppm`) for PDF input.
- `bsdtar` (libarchive) for CBR/RAR input. macOS includes it; on Debian/Ubuntu
  it is in `libarchive-tools`.

```sh
# macOS
brew install cmake poppler
# Debian/Ubuntu
sudo apt-get install cmake nasm poppler-utils libarchive-tools

cargo install --locked --path cli
```

## Use

```sh
export OPENAI_API_KEY=sk-...
comic-panel "My Comic.pdf"                    # writes "My Comic.panels.cbz" beside it
comic-panel book.cbr book-guided.cbz --reading-direction rtl
```

The key can also be piped on stdin, for example
`dcli read 'dl://OpenAI Project API Key/content' | comic-panel book.pdf`.
It is never written to disk or logs.

Common options:

| Option | Default | Meaning |
| --- | --- | --- |
| `OUTPUT` | `<source>.panels.cbz` | CBZ to create. An existing file is never replaced. |
| `--max-spend-usd` | `20` | New API spending allowed for this run. Reaching it stops the run resumably. |
| `--page-cap-usd` | `0.50` | First-pass spending limit per page. A page reaching it is published whole and reported. `--no-page-cap` disables it. |
| `--reading-direction` | `auto` | `ltr`, `rtl`, or inferred from the pages. |
| `--title` | source name | Book title in the ACBF metadata. |
| `--work-dir` | `<output>.work` | Resumable run state. |
| `--ledger` | platform data dir | Shared spending ledger and cache of paid answers. |
| `--pages 3,7,9` | all | Convert only these source pages (for trials). |
| `--max-new-pages N` | none | Stop after N new pages; rerun to continue. |
| `--offline` | off | Replay cached answers only: no key, no network, no spending. |
| `--json` | off | Print the machine-readable summary. |

The default ledger is `~/Library/Application Support/comic-panel/ledger.jsonl`
on macOS and `$XDG_DATA_HOME/comic-panel/ledger.jsonl` (or `~/.local/share/...`)
on Linux. A new ledger records a lifetime cap of $100. `--ledger-cap-usd`
asserts the cap of an existing ledger; raising it needs an explicit
`approved_cap_change` entry.

### Resuming and caching

Every paid request is reserved in the ledger before it is sent and settled from
reported usage. Each request is identified by a SHA-256 of its exact body, so
any identical request, from this run or an earlier one, reuses the recorded
answer at no cost. To continue an interrupted, stopped or checkpointed run,
rerun the same command. Unknown request outcomes, such as a crash mid-request,
are never replayed automatically. The hidden `--retry-*` options name one
explicit recovery for a recorded failure.

### Exit status and report

| Status | Meaning |
| --- | --- |
| `0` | Published. Every page has panel guidance or is a legitimate whole-page splash or cover. |
| `2` | Published, with whole-page fallbacks. Each is listed with its reason. |
| `1` | Stopped without publishing: spending limit, API or account problem, unreadable input, or checkpoint. The work directory is kept; rerun to resume. |

The book also contains `comic-panel-report.json`, which records each page's
status, panel count and fallback reason. The work directory keeps every
attempt (`page-NNNN.json`), request/response records, candidate crops and
completeness proofs.

## How it works

Per page:

1. Detection escalates through three tiers: Sol-low, Sol-high, then Astra.
2. Deterministic source-pixel refinement expands boxes to dark gutters,
   lettered balloons, framed ink and black-page fringes, then adds a small
   reading margin.
3. Quality judgement:
   - layout risks escalate to a stronger tier;
   - inventory and continuity checks run on source regions;
   - native decisions run globally and per marked target;
   - crossing-art and occlusion screens run;
   - risky layouts also get source-ownership evidence.
4. Verifiers confirm or reject; each can clear only its own alarm.
5. A final source-completeness gate maps an independent inventory onto the
   proposed panels and writes a replayable proof.
6. Repairs are bounded:
   - up to two verifier-directed geometry repairs;
   - one deterministic component repair;
   - one completeness-driven redetection, plus one repair of it;
   - one deterministic merge.

   Otherwise the page is a reported whole-page fallback.

Models: `gpt-6-sol`, `gpt-6-astra` and `gpt-6-luna` (OpenAI Responses and
Decisions APIs). Prices were verified through 2026-12-31. After that date the
CLI warns that ledger costs are estimates.

## Limits

- Panel detection quality is that of the pipeline above. With the default
  $0.50 page cap, complex pages can stop escalating and are published whole.
  On the 257-page validation book, 25 of 70 replayed pages did so.
- Input limits: 10,000 archive entries, 2 GB expanded, and about 179 megapixels
  per page. Encrypted archives, multi-frame images and RAR archives that
  bsdtar cannot read are refused before any request.
- An embedded ICC profile is not copied into a PNG publication page converted
  from another format. JPEG/PNG page bytes are kept as is.

## Verification

```sh
cargo test --release                       # unit + end-to-end tests (fake OpenAI server)
tests/fetch-acbf-xsd.sh /tmp/acbf-1.1.xsd   # pinned ACBF 1.1 schema
COMIC_PANEL_ACBF_XSD=/tmp/acbf-1.1.xsd cargo test --release   # also validate against the schema
```

The end-to-end tests run the real binary against a fake OpenAI server. They
cover:

- conversion of CBZ, image-folder and single-page books;
- resume, offline replay, and refusing to overwrite an existing output;
- the per-run spending limit, and recovery from a transient 503;
- corrupt pages and path-traversal archives refused before any request.

CI runs formatting, clippy and the tests on Linux and macOS
(`.github/workflows/cli.yml`).

The port's parity with the Python prototype is recorded in
`specs/research/rust-port-parity-20261015.md`. Requests are byte-identical, so
the 257-page offline replay and a live 12-page sample produce the prototype's
decisions exactly.

`tests/differential/` holds the prototype-comparison harnesses:

- `refine_cases.py` with `cargo run --release --example refineprobe`, for the refiners;
- `formats.py`, for page-image preparation and EXIF orientation;
- `v63_replay_oracle.py`, `v63_replay_run.py`, `replay_all.sh` and
  `compare_replay.py`, for whole-page records.

These need the prototype, its Python dependencies and the private validation book.
