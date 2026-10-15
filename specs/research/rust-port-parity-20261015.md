# Rust CLI port: parity with the V63 prototype (2026-10-15)

Branch `comic-panel-cli-rust` ports the complete V63 converter
(`prototypes/panel_quality_probe`, policy `automatic-marked-target-completeness-v63`)
to the Rust crate in `cli/`. The goal is for the Rust CLI to match or exceed
the prototype on a representative sample of page kinds.

## Method

Every model request is identified by `sha256(prefix + json.dumps(body, sort_keys=True))`,
images included. The port reproduces every byte that reaches a request:

- Python's JSON serialization;
- libjpeg-turbo with Pillow's encoder and decoder defaults;
- Pillow's LANCZOS resampling and rectangle drawing;
- OpenCV 5's connected-component label order, 3×3 closing and CCOMP hole contours;
- NumPy's linear quantiles and Python's rounding.

Given the same recorded model answers, the Rust CLI must therefore reach exactly
the prototype's decisions.

The replay used the real shared ledger, copied read-only on staging VM153. Each
of the 257 pages ran in its own output directory under the exact options of the
V63 first-pass run:
- LTR, `$0.50` page cap, automatic transient recovery;
- the frozen V63 prototype in cache-only mode, then `comic-panel --offline`.

Page records were compared after normalizing run-directory paths. Completeness
proof file names hash implementation-specific configuration, so they were
compared structurally.

## Results

- Refiners: 771/771 cases on all 257 pages are byte-identical
  (`cli/tests/differential/refine_cases.py`).
- Images: crops, LANCZOS details and marked boundaries are byte-identical to Pillow.
  The macOS arm64 build produces the same bytes as Linux x86-64.
- End to end, 257/257 pages are identical:
  - 70 pages replay completely from cache: pages 1–65, 119, 144, 209, 245 and 251.
    That is 1,163 recorded requests reused byte-identically. The page records are
    identical: 45 accepted and 25 whole-page fallbacks under the V63 page cap.
  - 187 pages stop at their first uncached request in both implementations. The
    blocked records are identical too, including the attempts so far and the
    identity of the first new request.
- Unit tests pass on Linux x86-64 (Debian 13) and macOS 26 arm64.

V63 finding, the same in both implementations: once cached answers are charged at
their recorded cost, 25 of the 70 replayable pages reach the $0.50 page cap and
fall back. Page 5 is one of them. The earlier V62 run accepted them only because
its cached calls were free.

## Evidence

`validation-artifacts/rust-port-20261015/` holds:
- the comparison and run logs;
- sample prototype and Rust page records (pages 5, 12, 119);
- the macOS build and test logs.

## Remaining

A paid live sample would exercise the HTTP path end to end on pages the cache
does not cover. The Rust CLI runs live on those pages, then the prototype
replays Rust's recorded answers, which checks both implementations for one
spend. Proposed pages: 67, 73, 74, 83, 85, 100, 101, 109, 145, 183, 195, 215.
It needs OpenAI credits and Chris's approval of the spend.
