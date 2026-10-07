"""Contract tests: all fixtures and outputs live in disposable directories."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as ET

from PIL import Image
from adapter import build_cbz


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="comic-adapter-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pages = self.root / "pages"
        self.pages.mkdir()
        for name in ("page2.png", "page10.png"):
            Image.new("RGB", (100, 200), "white").save(self.pages / name)
        self.data = {"total_pages": 2, "reading_direction": "rtl", "pages": [
            {"page": 1, "image": "page2.png", "panels": [{"x": .5, "y": 0, "w": .5, "h": .5}, {"x": 0, "y": .5, "w": 1, "h": .5}]},
            {"page": 2, "image": "page10.png", "panels": []}]}

    def build(self, name="book.cbz"):
        return build_cbz(self.pages, self.data, self.root / name, title="Fixture")

    def test_cover_once_order_pixel_geometry_and_fallback(self):
        manifest = self.build()
        with zipfile.ZipFile(self.root / "book.cbz") as archive:
            xml = ET.fromstring(archive.read("metadata.acbf"))
            refs = [e.attrib["href"] for e in xml.findall(".//{*}image")]
            self.assertEqual(refs, ["0001.png", "0002.png"])
            self.assertEqual(len(xml.findall("{*}body/{*}page")), 1)
            self.assertIsNotNone(xml.find("{*}meta-data/{*}publish-info"))
            self.assertEqual(xml.find(".//{*}coverpage/{*}frame").attrib["points"], "50,0 99,0 99,100 50,100")
            self.assertEqual(xml.find("{*}body/{*}page/{*}frame").attrib["points"], "0,0 99,0 99,199 0,199")
            self.assertEqual(archive.read("0001.png"), (self.pages / "page2.png").read_bytes())
        self.assertEqual(manifest["pages"][1]["fallback_reason"], "empty_panels")
        self.assertEqual(manifest["reading_direction"], "rtl")

    def test_invalid_geometry_falls_back_with_reason(self):
        self.data["pages"][0]["panels"][0]["w"] = float("nan")
        result = self.build()
        self.assertIn("non-finite", result["pages"][0]["fallback_reason"])
        self.assertEqual(result["pages"][0]["frame_count"], 1)

    def test_mismatched_mapping_rejected_before_output(self):
        self.data["pages"][1]["image"] = "page2.png"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.build()
        self.assertFalse((self.root / "book.cbz").exists())

    def test_extraneous_page_is_not_silently_lost(self):
        Image.new("RGB", (100, 200)).save(self.pages / "page3.png")
        with self.assertRaisesRegex(ValueError, "unmapped"):
            self.build()

    def test_existing_outputs_remain_byte_identical(self):
        target = self.root / "book.cbz"
        target.write_bytes(b"USER DATA")
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(target.read_bytes(), b"USER DATA")

    def test_one_page_book_rejected_instead_of_duplicating_cover(self):
        self.data["pages"] = self.data["pages"][:1]
        self.data["total_pages"] = 1
        single = self.root / "single"
        single.mkdir()
        (single / "page2.png").write_bytes((self.pages / "page2.png").read_bytes())
        with self.assertRaisesRegex(ValueError, "cover plus at least one body page"):
            build_cbz(single, self.data, self.root / "single.cbz", title="Single page")

    def test_metadata_is_preserved_without_second_active_acbf(self):
        (self.pages / "ComicInfo.xml").write_bytes(b"<ComicInfo><Manga>YesAndRightToLeft</Manga></ComicInfo>")
        (self.pages / "old.acbf").write_bytes(b"original metadata")
        (self.pages / "notes.txt").write_bytes(b"notes")
        result = self.build()
        with zipfile.ZipFile(self.root / "book.cbz") as archive:
            self.assertEqual(archive.read("ComicInfo.xml"), (self.pages / "ComicInfo.xml").read_bytes())
            self.assertEqual(archive.read("notes.txt"), b"notes")
            self.assertEqual(archive.read("source-metadata/old.acbf.original"), b"original metadata")
            self.assertEqual([n for n in archive.namelist() if n.endswith(".acbf")], ["metadata.acbf"])
        self.assertEqual(len(result["preserved_auxiliary"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
