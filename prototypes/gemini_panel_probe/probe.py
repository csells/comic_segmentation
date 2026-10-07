"""Bounded small-sample empirical probe. Requires google-genai and Pillow.

Writes only into a new output directory. Credentials stay in process memory.
The probe is evidence scaffolding, not the production converter.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from contract import PROMPT, SCHEMA, extract_generation, pannello_page, source_pages, api_retryable


def write_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default="gemini-3.8-flash")
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--pages", type=source_pages, default=[1, 3, 5, 25],
                        help="one to four explicit source page numbers, comma-separated")
    parser.add_argument("--credential-note", default="Gemini API key dartantic")
    args = parser.parse_args()
    from google import genai
    from google.genai import types, errors
    import httpx
    from PIL import Image, ImageDraw, ImageFont

    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "pages").mkdir()
    (args.output / "overlays").mkdir()
    write_json(args.output / "contract.json", {"prompt": PROMPT, "schema": SCHEMA})
    # Capture both pipes; never expose vault stderr or note content in diagnostics.
    credential = subprocess.run(["dcli", "read", f"dl://{args.credential_note}/content"],
                                capture_output=True, text=True)
    if credential.returncode:
        raise SystemExit("Dashlane credential read failed; no requests made")
    matches = re.findall(r"AIza[\w-]{30,}", credential.stdout)
    if len(set(matches)) != 1:
        raise SystemExit("Dashlane note did not contain one recognizable API key; no requests made")
    key = matches[0]
    del credential, matches
    report = {"requested_model": args.model, "sdk": f"google-genai {genai.__version__}",
              "api": "v1beta generateContent", "max_output_tokens": args.max_output_tokens,
              "max_pages": len(args.pages), "selected_source_pages": args.pages,
              "max_attempts_per_page": 2, "requests": [], "pages": []}
    # attempts=1 disables implicit SDK retries; the only retry budget is below.
    client = genai.Client(api_key=key, http_options=types.HttpOptions(
        api_version="v1beta", timeout=180000, retry_options=types.HttpRetryOptions(attempts=1)))
    mapped = []
    try:
        for target_page, source_page in enumerate(args.pages, 1):
            source = args.source / f"page-{source_page}.png"
            image_name = f"{target_page:04d}.png"
            data = source.read_bytes()
            if len(data) * 4 / 3 + len(PROMPT) + len(json.dumps(SCHEMA)) >= 19_000_000:
                raise ValueError("image exceeds this probe's conservative inline request limit")
            target = args.output / "pages" / image_name
            with target.open("xb") as stream:
                stream.write(data)
            with Image.open(source) as image:
                width, height = image.size
            value = None
            failure = None
            for attempt in (1, 2):
                started = time.monotonic()
                request = {"source_pdf_page": source_page, "output_page": target_page,
                           "attempt": attempt, "model": args.model}
                report["requests"].append(request)
                try:
                    response = client.models.generate_content(
                        model=args.model,
                        contents=[PROMPT, types.Part.from_bytes(data=data, mime_type="image/png")],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json", response_json_schema=SCHEMA,
                            max_output_tokens=args.max_output_tokens, temperature=0.0,
                            candidate_count=1))
                    raw = response.model_dump(mode="json", by_alias=True, exclude_none=True)
                    # These are response fields only; SDK HTTP response headers are omitted.
                    raw.pop("sdkHttpResponse", None)
                    write_json(args.output / f"page-{source_page}-attempt-{attempt}-response.json", raw)
                    request.update({"status": "received", "usage": raw.get("usageMetadata", {}),
                                    "model_version": raw.get("modelVersion"),
                                    "finish_reasons": [c.get("finishReason") for c in raw.get("candidates", [])]})
                    value = extract_generation(raw)
                    request["status"] = "valid"
                    break
                except (ValueError, errors.APIError, httpx.TransportError) as error:
                    code = getattr(error, "code", None)
                    failure = f"{type(error).__name__}: {str(error).replace(key, '[REDACTED]')}"
                    request.update({"status": "failed", "error": failure, "http_status": code})
                    # Authentication/schema/model issues stop the bounded run immediately.
                    if isinstance(error, errors.APIError) and not api_retryable(code, error.details):
                        raise RuntimeError(f"Gemini request failed with HTTP {code}; see sanitized report") from None
                    if attempt == 1:
                        time.sleep(2)
                finally:
                    request["elapsed_seconds"] = round(time.monotonic() - started, 3)
                    write_json(args.output / f"page-{source_page}-attempt-{attempt}-status.json", request)
                    print(json.dumps({k: request.get(k) for k in
                        ("source_pdf_page", "attempt", "status", "elapsed_seconds", "usage")}), flush=True)
            fallback = value is None
            if fallback:
                value = {"classification": "whole_page", "orientation": "upright", "reading_direction": "ltr",
                         "panels": [{"order": 1, "box": [0, 0, 1000, 1000]}]}
            write_json(args.output / f"page-{source_page}-panels.json", value)
            mapped.append(pannello_page(value, target_page, image_name))
            report["pages"].append({"source_pdf_page": source_page, "output_page": target_page,
                "image": image_name, "sha256": hashlib.sha256(data).hexdigest(),
                "dimensions": [width, height], "classification": value["classification"],
                "panel_count": len(value["panels"]), "fallback": fallback,
                "fallback_reason": failure if fallback else None})
            with Image.open(source) as original:
                overlay = original.convert("RGB")
            draw = ImageDraw.Draw(overlay)
            font = ImageFont.load_default(size=32)
            for panel in value["panels"]:
                ymin, xmin, ymax, xmax = panel["box"]
                box = (round(xmin*width/1000), round(ymin*height/1000),
                       round(xmax*width/1000)-1, round(ymax*height/1000)-1)
                draw.rectangle(box, outline="red", width=4)
                draw.text((box[0]+5, box[1]+5), str(panel["order"]), font=font,
                          fill="red", stroke_width=2, stroke_fill="white")
            overlay.save(args.output / "overlays" / image_name)
        write_json(args.output / "panels.json", {"reading_direction": "ltr", "total_pages": len(mapped), "pages": mapped})
    finally:
        client.close()
        write_json(args.output / "report.json", report)


if __name__ == "__main__":
    main()
