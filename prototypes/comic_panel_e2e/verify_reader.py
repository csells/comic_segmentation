"""Run authoritative XSD and unmodified upstream Android metadata parser.

This deliberately does not claim Android archive discovery, rendering, or UI.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import zipfile

from lxml import etree as ET


def verify(archive_path, xsd_path, reader_path):
    target = Path(tempfile.mkdtemp(prefix="comic-acbf-parser-"))
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("archive CRC validation failed")
        archive.extractall(target)
    xml_path = target / "metadata.acbf"
    xml = ET.parse(str(xml_path))
    schema = ET.XMLSchema(ET.parse(str(xsd_path)))
    schema.assertValid(xml)
    constants = ModuleType("constants")
    constants.default_font = ""
    constants.PLATFORM = "linux"
    sys.modules["constants"] = constants
    spec = importlib.util.spec_from_file_location("upstream_acbfdocument", reader_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reader = module.ACBFDocument(SimpleNamespace(tempdir=str(target), base_dir=str(target)), str(xml_path))
    if not reader.valid:
        raise ValueError("upstream Android metadata parser rejected document")
    expected = [xml.find(".//{*}coverpage"), *xml.findall("{*}body/{*}page")]
    actual = []
    for i, node in enumerate(expected, 1):
        image = Path(reader.load_page_image(i)[0]).name
        expected_image = node.find("{*}image").attrib["href"]
        frames = reader.load_page_frames(i)
        expected_frames = [[tuple(map(int, point.split(","))) for point in frame.attrib["points"].split()] for frame in node.findall("{*}frame")]
        if image != expected_image or [frame[0] for frame in frames] != expected_frames:
            raise ValueError(f"reader order/image/geometry mismatch at page {i}")
        actual.append({"page": i, "image": image, "frame_count": len(frames)})
    if reader.pages_total + 1 != len(expected):
        raise ValueError("reader page count mismatch")
    return {"archive": str(archive_path), "schema_valid": True, "reader_valid": True,
            "reader_has_frames": reader.has_frames, "reader_body_pages": reader.pages_total,
            "image_and_frame_order_match": True, "pages": actual,
            "scratch": str(target), "ui_tested": False,
            "constants_stub": {"default_font": "", "PLATFORM": "linux"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--xsd", type=Path, required=True)
    parser.add_argument("--reader", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.archive, args.xsd, args.reader)
    result_path = args.archive.with_suffix(".reader-check.json")
    with result_path.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
