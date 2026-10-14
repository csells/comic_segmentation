import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from fringe_refine import expand_dark_fringe_boxes
from auto_convert import Converter

class FringeTests(unittest.TestCase):
    def artwork(self):
        rgb=np.zeros((1000,800,3),dtype=np.uint8)
        rgb[100:500,100:400]=150
        cv2.line(rgb,(300,498),(285,524),(130,130,130),2)
        cv2.line(rgb,(350,504),(337,526),(130,130,130),2)
        return rgb

    def test_keeps_connected_and_disconnected_marks_without_mutating(self):
        boxes=[[98,98,402,502],[450,600,700,900]]
        result,changes=expand_dark_fringe_boxes(self.artwork(),boxes)
        self.assertGreaterEqual(result[0][3],528)
        self.assertEqual(result[1],boxes[1])
        self.assertEqual(boxes[0],[98,98,402,502])
        self.assertEqual(len(changes),1)
        self.assertEqual(expand_dark_fringe_boxes(self.artwork(),result),(result,[]))

    def test_does_not_include_neighbor_art(self):
        boxes=[[98,98,402,502],[280,502,360,550]]
        self.assertEqual(expand_dark_fringe_boxes(self.artwork(),boxes),(boxes,[]))

    def test_does_not_follow_remote_marks_or_noise(self):
        rgb=np.zeros((1000,800,3),dtype=np.uint8)
        rgb[100:500,100:400]=150
        rgb[512:520,300:305]=150
        rgb[504,350]=150
        box=[98,98,402,502]
        self.assertEqual(expand_dark_fringe_boxes(rgb,[box]),([box],[]))

    def test_does_not_follow_long_connection_into_other_scene(self):
        rgb=self.artwork();cv2.line(rgb,(350,504),(337,580),(130,130,130),2)
        box=[98,98,402,502]
        result,_=expand_dark_fringe_boxes(rgb,[box])
        self.assertLess(result[0][3],550)

    def test_leaves_full_bleed_and_light_backgrounds(self):
        box=[0,98,402,502]
        self.assertEqual(expand_dark_fringe_boxes(self.artwork(),[box]),([box],[]))
        rgb=self.artwork();rgb[:15,:15]=255;box=[98,98,402,502]
        self.assertEqual(expand_dark_fringe_boxes(rgb,[box]),([box],[]))

    def test_converter_includes_disconnected_marks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'page.png';Image.fromarray(self.artwork()).save(source)
            value={'classification':'panels','orientation':'upright','reading_direction':'ltr','panels':[
                {'order':1,'description':'Scene with marks outside its frame','box':[98,122,502,503]}]}
            out=Converter(None,root).refine(source,{'panels':value,'tier':'sol-low'})
            self.assertGreaterEqual(out['panels']['panels'][0]['box'][2],528)
            self.assertEqual(value['panels'][0]['box'][2],502)

if __name__=='__main__':unittest.main()
