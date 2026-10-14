"""Validation-only Pannello JSON -> full-page CBZ + ACBF 1.1 adapter.

Uses existing XML, ZIP and image libraries. No detector implementation lives here.
Owned adapter logic is disposable evidence for an eventual Rust implementation.
"""
import argparse
from datetime import date
import hashlib
import json
import json
import math
from pathlib import Path
import uuid
from xml.etree import ElementTree as ET
import zipfile

from PIL import Image

NS = "http://www.acbf.info/xml/acbf/1.1"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
READER_PROFILE = "panel-reader.json"
ET.register_namespace("", NS)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _tag(parent, name, text=None, **attributes):
    node = ET.SubElement(parent, f"{{{NS}}}{name}", attributes)
    if text is not None:
        node.text = text
    return node


def _rectangle(p, width, height):
    vals = [p[k] for k in ("x", "y", "w", "h")]
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in vals):
        raise ValueError("non-finite or non-numeric rectangle")
    x, y, w, h = vals
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1.0002 or y + h > 1.0002:
        raise ValueError("rectangle outside normalized page bounds or non-positive")
    left, top = math.floor(x * width), math.floor(y * height)
    right = min(width - 1, math.ceil((x + w) * width))
    bottom = min(height - 1, math.ceil((y + h) * height))
    if right <= left or bottom <= top:
        raise ValueError("rectangle collapses at image resolution")
    return f"{left},{top} {right},{top} {right},{bottom} {left},{bottom}"


def build_cbz(page_root, panel_data, output, *, title, source_map=None, fallback_reasons=None):
    """Refuse collisions/mapping mistakes; retain every page and auxiliary byte.

    Malformed per-page geometry uses an explicit whole-page fallback. Structural
    mismatches fail before output creation because guessing could reorder a book.
    JSON images may be relative paths or unambiguous basenames (Pannello's form).
    """
    root, output = Path(page_root).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    if output.is_relative_to(root):
        raise ValueError("output must be outside the source page tree")
    if any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("symlinks in source tree are unsupported")
    files = [p for p in root.rglob("*") if p.is_file()]
    page_files = [p for p in files if p.suffix.lower() in IMAGE_EXTS and "__MACOSX" not in p.parts and not p.name.startswith("._")]
    entries = panel_data.get("pages", [])
    if not entries or panel_data.get("total_pages") != len(entries):
        raise ValueError("empty pages or inconsistent total_pages")
    if panel_data.get("reading_direction") not in ("ltr", "rtl"):
        raise ValueError("reading_direction must be ltr or rtl")
    mapped, records, seen = [], [], set()
    for index, entry in enumerate(entries, 1):
        if entry.get("page") != index:
            raise ValueError("page numbers must be consecutive and in reading order")
        image = entry.get("image", "")
        candidates = [p for p in page_files if p.relative_to(root).as_posix() == image]
        if not candidates and "/" not in image:
            candidates = [p for p in page_files if p.name == image]
        if len(candidates) != 1:
            raise ValueError(f"missing or ambiguous page image: {image}")
        path = candidates[0]
        if path in seen:
            raise ValueError(f"duplicate page mapping: {image}")
        seen.add(path)
        with Image.open(path) as im:
            width, height = im.size
        if width < 2 or height < 2:
            raise ValueError(f"page image too small: {image}")
        fallback = (fallback_reasons or {}).get(index)
        try:
            if not isinstance(entry.get("panels"), list) or not entry["panels"]:
                raise ValueError("empty_panels")
            frames = [_rectangle(p, width, height) for p in entry["panels"]]
        except (KeyError, TypeError, ValueError) as exc:
            fallback = f"{fallback}; invalid_geometry: {exc}" if fallback else str(exc)
            frames = [_rectangle({"x": 0, "y": 0, "w": 1, "h": 1}, width, height)]
        archive_name = f"{index:04d}{path.suffix.lower()}"
        mapped.append((path, archive_name, frames))
        records.append({"page": index, "source_image": path.relative_to(root).as_posix(),
                        "source_page": (source_map or {}).get(index, index), "archive_image": archive_name,
                        "width": width, "height": height, "sha256": digest(path),
                        "frame_count": len(frames), "frames": frames, "fallback_reason": fallback})
    if seen != set(page_files):
        raise ValueError("unmapped source images would be lost")

    acbf = ET.Element(f"{{{NS}}}ACBF")
    meta = _tag(acbf, "meta-data")
    book = _tag(meta, "book-info")
    _tag(_tag(book, "author"), "nickname", "Unknown")
    _tag(book, "book-title", title)
    cover = _tag(book, "coverpage")
    # Optional in XSD, required in practice by the Android v2.1 parser.
    _tag(meta, "publish-info")
    doc = _tag(meta, "document-info")
    _tag(_tag(doc, "author"), "nickname", "comic-panel-e2e validation prototype")
    today = date.today().isoformat()
    _tag(doc, "creation-date", today, value=today)
    _tag(doc, "id", str(uuid.uuid4()))
    # The pinned ACBF 1.1 XSD accepts a cover-only document. An empty body is
    # invalid, and duplicating the source page to invent a body page loses the
    # one-source-page/one-reader-page invariant. The older Android parser still
    # assumes a body element; single-page books target our web profile for now.
    body = _tag(acbf, "body") if len(mapped) > 1 else None
    for index, (_, name, frames) in enumerate(mapped):
        page = cover if index == 0 else _tag(body, "page")
        _tag(page, "image", href=name)
        for points in frames:
            _tag(page, "frame", points=points)
    xml = ET.tostring(acbf, encoding="utf-8", xml_declaration=True)
    # ACBF 1.1 has no standard reading-direction field. Keep schema-valid ACBF
    # and carry this reader's control direction in a hash-bound companion file.
    reader_profile = {"format": "comic-panel-reader-profile", "version": 1,
                      "reading_direction": panel_data["reading_direction"],
                      "metadata_sha256": hashlib.sha256(xml).hexdigest()}
    occupied = {name.casefold() for _, name, _ in mapped} | {"metadata.acbf", READER_PROFILE}
    auxiliary = []
    for path in sorted(set(files) - seen):
        name = path.relative_to(root).as_posix()
        if path.suffix.lower() == ".acbf" or name.casefold() in occupied:
            name = "source-metadata/" + name + ".original"
        if name.casefold() in occupied:
            raise ValueError(f"preserved auxiliary path collision: {name}")
        occupied.add(name.casefold())
        auxiliary.append((path, name))
    with output.open("xb") as stream:
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
            for path, name, _ in mapped:
                archive.write(path, name)
            archive.writestr("metadata.acbf", xml)
            archive.writestr(READER_PROFILE, json.dumps(reader_profile, sort_keys=True) + "\n")
            for path, name in auxiliary:
                archive.write(path, name)
    with zipfile.ZipFile(output) as archive:
        for record in records:
            if hashlib.sha256(archive.read(record["archive_image"])).hexdigest() != record["sha256"]:
                raise RuntimeError("archive image preservation check failed")
    return {"prototype": True, "output": str(output), "output_sha256": digest(output),
            "page_count": len(records), "body_page_count": len(records) - 1,
            "reading_direction": panel_data["reading_direction"], "pages": records,
            "reader_profile": reader_profile,
            "preserved_auxiliary": [{"source": p.relative_to(root).as_posix(), "archive": n, "sha256": digest(p)} for p, n in auxiliary]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("page_root", type=Path)
    parser.add_argument("panel_json", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()
    manifest_path = args.output.with_suffix(".manifest.json")
    if manifest_path.exists():
        raise FileExistsError(manifest_path)
    result = build_cbz(args.page_root, json.loads(args.panel_json.read_text()), args.output, title=args.title)
    with manifest_path.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "manifest": str(manifest_path), "pages": result["page_count"]}))


if __name__ == "__main__":
    main()
