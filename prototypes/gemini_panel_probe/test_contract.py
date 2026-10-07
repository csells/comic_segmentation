"""Offline behavioral tests for normalized Gemini output, no API calls."""
import copy
import unittest

from contract import validate_page, pannello_page, extract_generation, source_pages, api_retryable


def page(boxes=None):
    boxes = boxes if boxes is not None else [[100, 600, 300, 900], [100, 100, 300, 500]]
    return {
        "classification": "panels",
        "orientation": "upright",
        "reading_direction": "ltr",
        "panels": [{"order": i, "box": box} for i, box in enumerate(boxes, 1)],
    }


class ContractTests(unittest.TestCase):
    def test_hard_quota_stops_but_service_overload_can_retry(self):
        self.assertTrue(api_retryable(503, {"error": {"message": "high demand"}}))
        self.assertTrue(api_retryable(429, {"error": {"message": "requests per minute"}}))
        self.assertFalse(api_retryable(401, {}))
        self.assertFalse(api_retryable(429, {"error": {"message": "Quota exceeded, limit: 0"}}))
        self.assertFalse(api_retryable(429, {"error": {"details": [{
            "@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{
                "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}))
        self.assertFalse(api_retryable(429, {"error": {"details": [{
            "@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "1909s"}]}}))

    def test_source_page_selection_is_explicit_bounded_and_unique(self):
        self.assertEqual(source_pages("5,25"), [5, 25])
        self.assertEqual(source_pages("1,3,5,25"), [1, 3, 5, 25])
        for value in ["", "0,1", "1,1", "1,2,3,4,5", "one,2"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                source_pages(value)

    def test_preserves_array_order_and_yx_to_xy_mapping(self):
        result = pannello_page(validate_page(page()), 3, "0003.png")
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["image"], "0003.png")
        self.assertEqual(result["panels"], [
            {"x": .6, "y": .1, "w": .3, "h": .2},
            {"x": .1, "y": .1, "w": .4, "h": .2},
        ])

    def test_rejects_bad_bounds_without_clamping(self):
        for box in [[-1, 0, 1000, 1000], [0, 0, 1001, 1000],
                    [200, 10, 200, 100], [200, 200, 400, 100],
                    [0., 0, 100, 100], [False, 0, 100, 100], [0, 100, 200]]:
            with self.subTest(box=box), self.assertRaises(ValueError):
                validate_page(page([box]))

    def test_rejects_disagreed_order_without_sorting(self):
        bad = page()
        bad["panels"][0]["order"] = 2
        with self.assertRaises(ValueError):
            validate_page(bad)

    def test_rejects_empty_and_non_upright_and_wrong_direction(self):
        for key, value in [("panels", []), ("orientation", "rotate_90"),
                           ("reading_direction", "rtl")]:
            bad = page()
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_page(bad)

    def test_whole_page_requires_full_extent(self):
        valid = page([[0, 0, 1000, 1000]])
        valid["classification"] = "whole_page"
        self.assertEqual(validate_page(valid), valid)
        invalid = copy.deepcopy(valid)
        invalid["panels"][0]["box"][0] = 1
        with self.assertRaises(ValueError):
            validate_page(invalid)

    def test_content_extract_requires_successful_completion(self):
        import json
        response = {"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"thought": True, "text": "not output"},
                      {"text": json.dumps(page())}]}}]}
        self.assertEqual(extract_generation(response), page())
        for reason in ["MAX_TOKENS", "SAFETY", None]:
            response["candidates"][0]["finishReason"] = reason
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                extract_generation(response)


if __name__ == "__main__":
    unittest.main()
