import unittest

import numpy as np

from gutter_refine import expand_dark_gutter_boxes


class GutterRefineTests(unittest.TestCase):
    def page(self):
        im = np.zeros((600, 400, 3), dtype=np.uint8)
        im[40:270, 30:190] = (100, 130, 170)
        im[40:270, 210:370] = (170, 130, 100)
        return im

    def test_expands_to_pixels_without_reordering(self):
        boxes = [[212, 42, 367, 266], [33, 43, 187, 267]]
        result, changes = expand_dark_gutter_boxes(self.page(), boxes)
        self.assertEqual(result, [[208, 38, 372, 272], [28, 38, 192, 272]])
        self.assertEqual(len(changes), 2)

    def test_never_contracts_generous_bounds(self):
        box = [25, 35, 195, 277]
        result, changes = expand_dark_gutter_boxes(self.page(), [box])
        self.assertEqual(result, [box])
        self.assertEqual(changes, [])

    def test_thin_panel_accepts_small_offset_without_contracting(self):
        im = self.page(); im[500:580, 30:370] = (120, 140, 190)
        result, changes = expand_dark_gutter_boxes(im, [[30, 493, 370, 573]])
        self.assertEqual(result, [[28, 493, 372, 582]])
        self.assertEqual(len(changes), 1)

    def test_skips_nonuniform_corner_background(self):
        im = self.page(); im[:10, :10] = 255
        box = [33, 43, 187, 267]
        result, changes = expand_dark_gutter_boxes(im, [box])
        self.assertEqual(result, [box])
        self.assertEqual(changes, [])

    def test_does_not_split_or_merge_scenes(self):
        # A merged model proposal cannot qualify as either smaller component.
        box = [30, 40, 370, 270]
        result, changes = expand_dark_gutter_boxes(self.page(), [box])
        self.assertEqual(result, [box])
        self.assertEqual(changes, [])

    def test_keeps_full_page_and_ambiguous_sparse_shapes(self):
        im = np.zeros((600, 400, 3), dtype=np.uint8)
        im[40:270, 30:33] = 180
        im[267:270, 30:190] = 180
        boxes = [[0, 0, 400, 600], [33, 43, 187, 267]]
        self.assertEqual(expand_dark_gutter_boxes(im, boxes), (boxes, []))


if __name__ == '__main__':
    unittest.main()
