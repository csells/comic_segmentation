"""Scratch-only integration runner, not a supported product CLI."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from PIL import Image, ImageDraw, ImageFont
from adapter import build_cbz, digest


def write_json(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write("\n")


def make_fixture(scratch):
    pages = scratch / "pages"
    pages.mkdir()
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 100)
    small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
    cover = Image.new("RGB", (800, 1200), "#203440")
    d = ImageDraw.Draw(cover)
    d.text((70, 390), "PANEL PROBE", fill="white", font=small)
    d.text((70, 460), "COVER ONCE", fill="white", font=small)
    cover.save(pages / "page1.png")
    im = Image.new("RGB", (800, 1200), "white")
    d = ImageDraw.Draw(im)
    rects = [(30, 30, 770, 250), (30, 285, 295, 750), (330, 285, 770, 750), (30, 785, 770, 1170)]
    colors = ["#f5dc7b", "#86c8bb", "#e2ab9b", "#a7bce6"]
    panels = []
    for i, ((x0, y0, x1, y1), color) in enumerate(zip(rects, colors), 1):
        d.rectangle((x0, y0, x1, y1), fill=color, outline="black", width=8)
        d.text((x0 + 40, y0 + 35), str(i), fill="black", font=font)
        panels.append({"x": x0 / 800, "y": y0 / 1200, "w": (x1 - x0) / 800, "h": (y1 - y0) / 1200})
    im.save(pages / "page2.png")
    fallback = Image.new("RGB", (800, 1200), "#f6f0e5")
    d = ImageDraw.Draw(fallback)
    d.text((65, 510), "WHOLE PAGE", fill="black", font=small)
    d.text((65, 565), "FALLBACK", fill="black", font=small)
    fallback.save(pages / "page10.png")
    data = {"reading_direction": "ltr", "total_pages": 3, "pages": [
        {"page": 1, "image": "page1.png", "panels": [{"x": 0, "y": 0, "w": 1, "h": 1}]},
        {"page": 2, "image": "page2.png", "panels": panels},
        {"page": 3, "image": "page10.png", "panels": []}]}
    write_json(scratch / "known-panels.json", data)
    manifest = build_cbz(pages, data, scratch / "known-order.cbz", title="Panel order and fallback probe")
    write_json(scratch / "known-order.manifest.json", manifest)
    print(json.dumps({"scratch": str(scratch), "output": manifest["output"], "sha256": manifest["output_sha256"]}), flush=True)


def convert(source, scratch, selected, dpi, jobs):
    from pannello import core
    started = time.monotonic()
    pages = scratch / "pages"
    pages.mkdir()
    source = source.resolve()
    before = digest(source) if source.is_file() else None
    source_map = None
    if source.suffix.lower() == ".pdf":
        info = subprocess.run(["pdfinfo", str(source)], check=True, capture_output=True, text=True).stdout
        count = int(re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE).group(1))
        selected = selected or list(range(1, count + 1))
        if selected != sorted(set(selected)) or not all(1 <= n <= count for n in selected):
            raise ValueError("selected PDF pages must be unique, increasing and in range")
        source_map = {i: n for i, n in enumerate(selected, 1)}
        for i, n in source_map.items():
            print(f"[{i}/{len(selected)}] rendering source PDF page {n}", flush=True)
            subprocess.run(["pdftoppm", "-f", str(n), "-l", str(n), "-singlefile", "-jpeg", "-r", str(dpi), str(source), str(pages / f"{i:04d}")], check=True, timeout=180)
    elif source.is_dir():
        if selected:
            raise ValueError("--pages currently supported only for PDF")
        for path in source.rglob("*"):
            if path.is_symlink():
                raise ValueError("source symlinks unsupported")
            if path.is_file():
                target = pages / path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    else:
        if selected:
            raise ValueError("--pages currently supported only for PDF")
        # Existing library extraction is allowed only into this new scratch root.
        # This research prototype is for trusted local comics, not hostile input.
        core.extract_archive(source, pages, dpi=dpi)
    detector_out = scratch / "detector"
    detector_out.mkdir()
    print(f"detecting {len(core.list_pages(pages))} pages, jobs={jobs}, no cloud calls", flush=True)
    stats = core.generate(pages, jobs=jobs, fallback="none", out_dir=detector_out, preview=False, review=False, log=lambda msg: print(msg, flush=True))
    data = json.loads(Path(stats["out"]).read_text())
    fallbacks = {row["page"]: f"pannello:{row['reason']}" for row in stats["low_confidence"] if row["fullpage"]}
    manifest = build_cbz(pages, data, scratch / "comic.cbz", title=source.stem, source_map=source_map, fallback_reasons=fallbacks)
    after = digest(source) if source.is_file() else None
    if before != after:
        raise RuntimeError("source hash changed during conversion")
    manifest.update(source=str(source), source_sha256_before=before, source_sha256_after=after,
                    pdf_dpi=dpi if source.suffix.lower() == ".pdf" else None,
                    detector="Pannello 0.1.0 / Kumiko, no model fallback", detector_stats=stats,
                    elapsed_seconds=round(time.monotonic() - started, 2), process_pid=os.getpid())
    write_json(scratch / "comic.manifest.json", manifest)
    print(json.dumps({"output": manifest["output"], "manifest": str(scratch / "comic.manifest.json"),
                      "pages": manifest["page_count"], "frames": sum(p["frame_count"] for p in manifest["pages"]),
                      "fallback_pages": [p["source_page"] for p in manifest["pages"] if p["fallback_reason"]]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["fixture", "convert"])
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("--pages", help="1-based PDF page numbers, comma-separated")
    parser.add_argument("--dpi", default=150, type=int)
    parser.add_argument("--jobs", default=2, type=int)
    args = parser.parse_args()
    scratch = Path(tempfile.mkdtemp(prefix=f"comic-panel-e2e-{args.mode}-"))
    print(f"SCRATCH={scratch} PID={os.getpid()}", flush=True)
    if args.mode == "fixture":
        make_fixture(scratch)
    else:
        if not args.source:
            parser.error("source is required for conversion")
        selected = [int(n) for n in args.pages.split(",")] if args.pages else None
        convert(args.source, scratch, selected, args.dpi, args.jobs)


if __name__ == "__main__":
    main()
