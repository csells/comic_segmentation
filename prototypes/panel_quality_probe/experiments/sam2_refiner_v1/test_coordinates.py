"""Standard-library-only coordinate contract tests; run in the disposable VM."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("sam2_refiner_probe", Path(__file__).with_name("probe.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def bundle(points):
    return {"panels": [{"order": 1, "box": [0, 0, 1000, 1000]}],
            "images": [{"sha256": "unused-coordinate-only-fixture"}, {"points": points}]}


class CropCoordinateContract(unittest.TestCase):
    def test_inclusive_corner_pixels_preserve_last_row_and_column(self):
        result = probe.proposal_boxes(bundle("2,3 6,3 6,8 2,8"), 17, 23)[0]
        self.assertEqual(result["box_xyxy"], [2, 3, 7, 9])
        self.assertEqual((result["box_xyxy"][2] - 2, result["box_xyxy"][3] - 3), (5, 6))
        self.assertTrue(result["crop_extent_exact"])

    def test_full_page_inclusive_corners_become_full_half_open_source(self):
        result = probe.proposal_boxes(bundle("0,0 16,0 16,22 0,22"), 17, 23)[0]
        self.assertEqual(result["box_xyxy"], [0, 0, 17, 23])

    def test_saved_page57_crop6_extent_matches_converter_plus_one(self):
        # Existing automatic bundle points; these are not runtime prompt edits.
        result = probe.proposal_boxes(bundle("742,858 1081,858 1081,1078 742,1078"), 1128, 1648)[0]
        self.assertEqual(result["box_xyxy"], [742, 858, 1082, 1079])

    def test_inclusive_point_at_width_is_outside_source(self):
        with self.assertRaisesRegex(ValueError, "outside source"):
            probe.proposal_boxes(bundle("0,0 17,0 17,22 0,22"), 17, 23)

    def test_nonrectangular_points_fail(self):
        with self.assertRaisesRegex(ValueError, "rectangular"):
            probe.proposal_boxes(bundle("2,3 6,3 5,8 2,8"), 17, 23)

    def test_normalized_fallback_is_explicitly_an_estimate(self):
        proposal = {"panels": [{"order": 1, "box": [100, 200, 800, 900]}]}
        result = probe.proposal_boxes(proposal, 17, 23)[0]
        self.assertEqual(result["box_xyxy"], [3, 2, 16, 19])
        self.assertFalse(result["crop_extent_exact"])
        self.assertTrue(result["mapping_rule"].startswith("estimated_"))


if __name__ == "__main__":
    unittest.main()
