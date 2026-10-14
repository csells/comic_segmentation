import tempfile,unittest
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from balloon_refine import expand_balloon_boxes
from auto_convert import Converter

class BalloonTests(unittest.TestCase):
    def artwork(self):
        rgb=np.full((400,400,3),120,dtype=np.uint8)
        cv2.ellipse(rgb,(300,100),(50,40),0,0,360,(0,0,0),5)
        cv2.ellipse(rgb,(300,100),(47,37),0,0,360,(255,255,255),-1)
        for x in (280,293,306,319):cv2.rectangle(rgb,(x,92),(x+4,104),(0,0,0),-1)
        return rgb

    def test_encloses_crossing_balloon_without_changing_inventory_or_contracting(self):
        box=[150,20,335,300];other=[0,200,100,400]
        result,changes=expand_balloon_boxes(self.artwork(),[box,other])
        self.assertEqual(len(result),2);self.assertEqual(result[1],other)
        self.assertGreaterEqual(result[0][2],350);self.assertEqual(result[0][:2],box[:2]);self.assertEqual(result[0][3],box[3])
        self.assertEqual(changes[0]['index'],0)
        self.assertEqual(expand_balloon_boxes(self.artwork(),result),(result,[]))

    def test_minor_neighbor_fragment_does_not_expand(self):
        box=[0,0,265,200]
        self.assertEqual(expand_balloon_boxes(self.artwork(),[box]),([box],[]))

    def test_blank_white_object_and_page_background_are_not_balloon_evidence(self):
        rgb=self.artwork();rgb[80:120,270:330]=255
        box=[150,20,335,300]
        self.assertEqual(expand_balloon_boxes(rgb,[box]),([box],[]))
        self.assertEqual(expand_balloon_boxes(np.full((400,400,3),255,dtype=np.uint8),[box]),([box],[]))

    def test_actual_refinement_includes_enclosed_balloon(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'page.png';Image.fromarray(self.artwork()).save(source)
            value={'classification':'panels','orientation':'upright','reading_direction':'ltr','panels':[{'order':1,'description':'Scene','box':[50,375,750,838]}]}
            out=Converter(None,root).refine(source,{'panels':value,'tier':'sol-low'})
            self.assertGreaterEqual(out['panels']['panels'][0]['box'][3],875)
            self.assertEqual(value['panels'][0]['box'][3],838)

if __name__=='__main__':unittest.main()
