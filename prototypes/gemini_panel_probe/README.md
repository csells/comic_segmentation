# Gemini four-page probe

Evidence scaffolding for the proposed Rust converter. It uses Google's Python SDK
as a dependency and owns only a small prompt/validation/mapping contract. It is not
the production CLI and provides no panel editing or review interface.

`probe.py` defaults to `page-1.png`, `page-3.png`, `page-5.png`, and
`page-25.png` from a supplied read-only source directory. `--pages 5,25` selects
an explicit smaller sample; at most four unique pages are allowed. It makes one request per
page, with at most one additional attempt for a transient/invalid response. No
implicit SDK retry occurs. Persistent per-page failure is reported and represented
by a complete-page frame; authentication, model, request and hard quota errors stop the run.

Install `requirements.txt` in a fresh scratch virtual environment. The live command
reads its credential directly from the named Dashlane secure note into memory:

```sh
python prototypes/gemini_panel_probe/probe.py SOURCE_IMAGE_DIR NEW_OUTPUT_DIR \
  --model gemini-3.8-flash --max-output-tokens 8192
```

Running this command sends the selected private page images to Gemini and may incur API
charges. The output directory must not already exist. It contains response JSON,
attempt status/usage, validated panel JSON, exact input-image copies, source page
mapping and numbered overlays for development assessment. It never modifies the
source images. It does not silently switch models, reorder panels, clamp geometry,
or correct detections.

`panels.json` feeds `../comic_panel_e2e/adapter.py`. For a source-aware manifest,
call its `build_cbz` function with the source map and fallback reasons from
`report.json` (default map `{1:1,2:3,3:5,4:25}`). The adapter preserves PNG bytes in the CBZ.

Offline contract tests make no API requests:

```sh
python3 -m unittest discover -s prototypes/gemini_panel_probe -v
```

See [the measured run](../../specs/research/gemini-e2e-validation.md), including
the undersegmentation finding. These results do not establish detection quality
or full-book reliability.
