import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from frame_refine import expand_frame_boxes
from auto_convert import Converter


class FrameTests(unittest.TestCase):
    def artwork(self, protrusion=True):
        rgb = np.full((1000, 800, 3), 255, dtype=np.uint8)
        cv2.rectangle(rgb, (420, 60), (740, 500), (0, 0, 0), 3)
        if protrusion:
            cv2.circle(rgb, (600, 65), 18, (0, 0, 0), -1)
        return rgb

    def test_recovers_art_above_frame_without_contracting_or_reordering(self):
        box = [418, 58, 743, 503]
        other = [50, 600, 300, 900]
        result, changes = expand_frame_boxes(self.artwork(), [box, other])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1], other)
        self.assertLessEqual(result[0][1], 45)
        self.assertLessEqual(result[0][0], box[0])
        self.assertGreaterEqual(result[0][2], box[2])
        self.assertGreaterEqual(result[0][3], box[3])
        self.assertEqual(changes[0]['index'], 0)
        self.assertEqual(expand_frame_boxes(self.artwork(), result), (result, []))

    def test_ignores_border_thickness_and_rounding(self):
        box = [420, 60, 741, 501]
        self.assertEqual(expand_frame_boxes(self.artwork(False), [box]), ([box], []))

    def test_does_not_follow_ink_connected_to_neighbor_panel(self):
        rgb = self.artwork()
        cv2.rectangle(rgb, (420, 550), (740, 900), (0, 0, 0), 3)
        cv2.line(rgb, (600, 500), (600, 550), (0, 0, 0), 3)
        box = [418, 58, 743, 503]
        self.assertEqual(expand_frame_boxes(rgb, [box]), ([box], []))

    def test_requires_rectangular_frame_not_matching_colored_shape(self):
        rgb = np.full((1000, 800, 3), 255, dtype=np.uint8)
        cv2.rectangle(rgb, (420, 47), (740, 500), (150, 180, 200), -1)
        box = [418, 58, 743, 503]
        self.assertEqual(expand_frame_boxes(rgb, [box]), ([box], []))

    def test_actual_converter_recovers_protrusion_and_preserves_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'page.png'
            Image.fromarray(self.artwork()).save(source)
            value = {'classification': 'panels', 'orientation': 'upright',
                     'reading_direction': 'ltr', 'panels': [
                         {'order': 1, 'description': 'Framed scene',
                          'box': [58, 522, 503, 929]}]}
            out = Converter(None, root).refine(source, {'panels': value, 'tier': 'sol-low'})
            self.assertLessEqual(out['panels']['panels'][0]['box'][0], 45)
            self.assertEqual(value['panels'][0]['box'][0], 58)


if __name__ == '__main__':
    unittest.main()
