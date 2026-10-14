"""Ownership selection tests with no image/model imports; execute in VM."""
import copy
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("semantic_points_probe", Path(__file__).with_name("probe.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

SOURCE_SHA = "a" * 64


def manifest():
    return {"version": 1, "source_sha256": SOURCE_SHA,
            "scenes": [{"order": 1, "exclusive_points": [[250, 350]], "uncertain": False},
                       {"order": 2, "exclusive_points": [[650, 750], [850, 150]], "uncertain": False},
                       {"order": 3, "exclusive_points": [[150, 850]], "uncertain": True}]}


class OwnershipPointContract(unittest.TestCase):
    def parse(self, value=None, width=10, height=10):
        return probe.validate_points(value or manifest(), SOURCE_SHA, width, height, [1, 2, 3])

    def test_exact_float_mapping_and_floor_only_for_mask_lookup(self):
        scenes = self.parse(width=17, height=23)
        point = scenes[1]["points"][0]
        self.assertEqual(point["source_xy"], [4.25, 8.05])
        self.assertEqual(point["lookup_pixel_xy"], [4, 8])

    def test_only_exclusive_rival_points_inside_baseline_mask_become_negative(self):
        scenes = self.parse()
        prompts = probe.select_prompts(1, scenes, lambda x, y: (x, y) in {(6, 7), (1, 8)})
        self.assertEqual(prompts["status"], "prompted")
        self.assertEqual([p["normalized_xy"] for p in prompts["positives"]], [[250, 350]])
        self.assertEqual([p["normalized_xy"] for p in prompts["negatives"]], [[650, 750]])
        # Target positive remains usable outside baseline; uncertain rival at (1,8) is never negative.

    def test_uncertain_target_abstains_even_when_it_has_points(self):
        prompts = probe.select_prompts(3, self.parse(), lambda x, y: True)
        self.assertEqual(prompts, {"status": "abstain_uncertain_target", "positives": [], "negatives": []})

    def test_uncertain_target_can_have_no_points(self):
        value = manifest()
        value["scenes"][2]["exclusive_points"] = []
        self.assertTrue(self.parse(value)[3]["uncertain"])

    def test_no_rival_mask_support_means_no_negatives(self):
        self.assertEqual(probe.select_prompts(1, self.parse(), lambda x, y: False)["negatives"], [])

    def test_boundary_outside_nonfinite_and_boolean_coordinates_rejected(self):
        for point in [[0, 500], [1000, 500], [-1, 500], [500, 1001],
                      [float("nan"), 500], [float("inf"), 500], [True, 500]]:
            with self.subTest(point=point):
                value = manifest()
                value["scenes"][0]["exclusive_points"] = [point]
                with self.assertRaisesRegex(ValueError, "strictly inside"):
                    self.parse(value)

    def test_duplicate_point_or_same_pixel_collision_rejected(self):
        for duplicate in [[250, 350], [251, 351]]:
            value = manifest()
            value["scenes"][0]["exclusive_points"].append(duplicate)
            with self.assertRaisesRegex(ValueError, "Duplicate pixel"):
                self.parse(value)

    def test_contradictory_scene_ownership_rejected(self):
        value = manifest()
        value["scenes"][1]["exclusive_points"] = [[250, 350]]
        with self.assertRaisesRegex(ValueError, "contradictory"):
            self.parse(value)

    def test_three_point_limit_and_unambiguous_empty_set(self):
        for points in [[], [[100, 100], [200, 200], [300, 300], [400, 400]]]:
            value = manifest()
            value["scenes"][0]["exclusive_points"] = points
            with self.assertRaises(ValueError):
                self.parse(value)

    def test_source_inventory_and_uncertainty_must_match(self):
        variants = []
        value = manifest(); value["source_sha256"] = "b" * 64; variants.append(value)
        value = manifest(); value["scenes"][1]["order"] = 1; variants.append(value)
        value = manifest(); value["scenes"].pop(); variants.append(value)
        value = manifest(); value["scenes"][0]["uncertain"] = "false"; variants.append(value)
        for value in variants:
            with self.assertRaises(ValueError):
                self.parse(copy.deepcopy(value))


if __name__ == "__main__":
    unittest.main()
