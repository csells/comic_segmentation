"""Small local-model research probe. Run in the disposable candidate VM only.

Uses an existing shared Ollama service; does not install models or change it.
Every run is immutable, sequential, bounded, and preserves raw streamed replies.
Structural validation does NOT establish detection quality.
"""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gemini_panel_probe"))
from contract import SCHEMA, validate_page


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def parse_response(events, allow_thinking_json=False, named_bounds=False):
    if not events or not events[-1].get("done") or events[-1].get("done_reason") != "stop":
        raise ValueError("generation incomplete; no implicit retry")
    text = "".join(e.get("message", {}).get("content", "") for e in events)
    channel = "content"
    if not text and allow_thinking_json:
        # Diagnostic compatibility only: this installed model emitted the whole
        # schema-constrained JSON in thinking despite think=False. Accept only an
        # exact complete JSON object, never extract geometry from reasoning prose.
        text = "".join(e.get("message", {}).get("thinking", "") for e in events)
        channel = "thinking_json_diagnostic"
    value = json.loads(text)
    if named_bounds:
        for panel in value["panels"]:
            bounds = panel.pop("bounds")
            panel["box"] = [bounds["top"], bounds["left"], bounds["bottom"], bounds["right"]]
    return validate_page(value), channel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--pages", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=Path(__file__).with_name("prompt-v2.txt"))
    parser.add_argument("--allow-json-in-thinking", action="store_true")
    parser.add_argument("--named-bounds", action="store_true")
    args = parser.parse_args()
    pages = [int(p) for p in args.pages.split(",")]
    if not 1 <= len(pages) <= 8 or len(set(pages)) != len(pages) or min(pages) < 1:
        parser.error("select one to eight distinct positive pages")
    prompt = args.prompt.read_text()
    paths = [args.images / f"{p:04}.jpg" for p in pages]
    for path in paths:
        if not path.is_file():
            parser.error(f"missing source: {path}")
    args.output.mkdir(parents=True, exist_ok=False)
    schema = copy.deepcopy(SCHEMA)
    item = schema["properties"]["panels"]["items"]
    item["properties"]["description"] = {"type": "string"}
    item["required"].append("description")
    if args.named_bounds:
        item["properties"] = {"order": item["properties"]["order"],
            "description": item["properties"]["description"], "bounds": {
                "type": "object", "properties": {
                    name: {"type": "integer", "minimum": 0, "maximum": 1000}
                    for name in ("left", "top", "right", "bottom")},
                "required": ["left", "top", "right", "bottom"]}}
        item["required"] = ["order", "description", "bounds"]
    # Small fixed context/output limits keep this comparison bounded on shared hardware.
    config = {"model": "qwen3-vl:4b", "format": schema, "think": False,
              "stream": True, "keep_alive": "30s",
              "options": {"temperature": 0, "seed": 7, "num_ctx": 16384, "num_predict": 4096}}
    dump(args.output / "run.json", {"config": config, "endpoint": args.endpoint,
         "pages": pages, "prompt": prompt,
         "allow_json_in_thinking": args.allow_json_in_thinking,
         "named_bounds": args.named_bounds,
         "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
         "quality_status": "unreviewed", "started_at": time.time()})
    results = []
    for index, (page, path) in enumerate(zip(pages, paths), 1):
        out = args.output / f"page-{page:04}"
        out.mkdir()
        data = path.read_bytes()
        request = {**config, "messages": [{"role": "user", "content": prompt,
                                          "images": [base64.b64encode(data).decode()]}]}
        dump(out / "request.json", {**config, "prompt": prompt, "source": str(path),
             "source_sha256": hashlib.sha256(data).hexdigest(), "started_at": time.time()})
        print(f"[{index}/{len(pages)}] PDF {page}: request started", flush=True)
        started = last_update = time.monotonic()
        text, final, events = "", None, []
        result = {"source_page": page, "status": "incomplete"}
        try:
            req = urllib.request.Request(args.endpoint.rstrip("/") + "/api/chat",
                    data=json.dumps(request).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as response, (out / "response.ndjson").open("w") as raw:
                for line in response:
                    raw.write(line.decode())
                    raw.flush()
                    event = json.loads(line)
                    events.append(event)
                    if event.get("error"):
                        raise ValueError("provider returned an error; inspect preserved response")
                    text += event.get("message", {}).get("content", "")
                    now = time.monotonic()
                    if now - last_update >= 15:
                        print(f"[{index}/{len(pages)}] PDF {page}: {len(text)} output characters, {now-started:.0f}s", flush=True)
                        last_update = now
                    if now - started > 600:
                        raise TimeoutError("ten-minute page limit")
                    if event.get("done"):
                        final = event
            parsed, channel = parse_response(events, args.allow_json_in_thinking, args.named_bounds)
            dump(out / "panels.json", parsed)
            result.update(status="structurally_valid_unreviewed", panels=len(parsed["panels"]),
                          response_channel=channel,
                          classification=parsed["classification"],
                          prompt_tokens=final.get("prompt_eval_count"), output_tokens=final.get("eval_count"))
        except Exception as exc:
            result.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        result["elapsed_seconds"] = round(time.monotonic()-started, 3)
        dump(out / "result.json", result)
        results.append(result)
        dump(args.output / "results.json", results)
        print(f"[{index}/{len(pages)}] PDF {page}: {result['status']}; {result['elapsed_seconds']}s", flush=True)
        if result["status"] == "failed":
            break  # Investigate before sending another request.


if __name__ == "__main__":
    main()
