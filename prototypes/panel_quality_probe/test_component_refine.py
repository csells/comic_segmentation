import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

from component_refine import expand_component_boxes
from automatic_escalation import run_page
from auto_convert import Converter


class ComponentRefineTests(unittest.TestCase):
    def test_black_paper_margins_quiet_but_uncovered_light_art_routes(self):
        from component_refine import uncovered_content_risk
        rgb = np.full((200, 200, 3), 25, dtype=np.uint8)
        rgb[30:170, 30:170] = 220
        boxes = [[30, 30, 170, 170]]
        result = uncovered_content_risk(rgb, boxes)
        self.assertFalse(result['requires_ownership'])
        self.assertEqual(result['uncovered_nonpaper_pixels'], 0)
        self.assertEqual(result['paper_polarity'], 'black')
        self.assertEqual(result['corner_size'], 2)
        self.assertEqual(result['corner_max_rgb_95th_percentiles'], [25.0] * 4)
        self.assertEqual(result['foreground_above'], 25)
        self.assertIsNone(result['foreground_below'])
        # One channel above25 is foreground, including at the edge of the page.
        rgb[70:74, 0:5] = [26, 0, 0]
        result = uncovered_content_risk(rgb, boxes)
        self.assertTrue(result['requires_ownership'])
        self.assertEqual(result['components'], [{'bounds': [0, 70, 5, 74], 'pixels': 20}])

    def test_one_nonblack_corner_keeps_conservative_light_paper_mask(self):
        from component_refine import uncovered_content_risk
        rgb = np.zeros((200, 200, 3), dtype=np.uint8)
        rgb[0:2, 0:2] = [26, 0, 0]
        result = uncovered_content_risk(rgb, [[30, 30, 170, 170]])
        self.assertTrue(result['requires_ownership'])
        self.assertEqual(result['paper_polarity'], 'light_or_mixed')
        self.assertEqual(result['corner_max_rgb_95th_percentiles'], [26.0, 0.0, 0.0, 0.0])
        self.assertEqual(result['foreground_below'], 245)
        self.assertIsNone(result['foreground_above'])

    def test_uncovered_components_include_thin_edges_and_disconnected_monochrome(self):
        from component_refine import uncovered_content_risk
        rgb = np.full((200, 200, 3), 255, dtype=np.uint8)
        rgb[0, 0:30] = 0
        rgb[40:45, 40:45] = 100
        rgb[100:150, 100:150] = [30, 80, 90]
        boxes = [[100, 100, 150, 150]]
        before, original = copy.deepcopy(boxes), rgb.copy()
        result = uncovered_content_risk(rgb, boxes)
        self.assertTrue(result['requires_ownership'])
        self.assertEqual(result['minimum_component_pixels'], 20)
        self.assertEqual(result['components'], [
            {'bounds': [0, 0, 30, 1], 'pixels': 30},
            {'bounds': [40, 40, 45, 45], 'pixels': 25}])
        self.assertEqual(boxes, before)
        np.testing.assert_array_equal(rgb, original)

    def test_union_coverage_and_small_noise_do_not_trigger(self):
        from component_refine import uncovered_content_risk
        rgb = np.full((101, 200, 3), 255, dtype=np.uint8)
        rgb[20:80, 30:180] = 40
        rgb[0:3, 0:5] = 0  # Below the minimum16, despite touching the edge.
        rgb[0:10, 190:200] = 245  # Existing paper threshold is exclusive.
        result = uncovered_content_risk(rgb, [[30, 20, 110, 80], [100, 20, 180, 80]])
        self.assertEqual(result['minimum_component_pixels'], 16)
        self.assertEqual(result['uncovered_nonpaper_pixels'], 15)
        self.assertFalse(result['requires_ownership'])
        large = np.full((201, 200, 3), 255, dtype=np.uint8)
        self.assertEqual(uncovered_content_risk(large, [])['minimum_component_pixels'], 21)

    def test_tiny_missing_color_edge_expands_only_outward(self):
        rgb=np.full((300,400,3),255,dtype=np.uint8);rgb[100:200,100:250]=[80,150,190]
        boxes=[[102,100,250,200]];before=copy.deepcopy(boxes)
        updated,changes=expand_component_boxes(rgb,boxes)
        self.assertEqual(boxes,before);self.assertEqual(updated,[[97,100,250,200]])
        self.assertEqual(len(changes),1)
        self.assertEqual(expand_component_boxes(rgb,updated)[1],[])

    def test_large_omission_and_monochrome_component_do_not_qualify(self):
        rgb=np.full((300,400,3),255,dtype=np.uint8);rgb[100:200,100:250]=[80,150,190]
        self.assertEqual(expand_component_boxes(rgb,[[120,100,250,200]])[1],[])
        rgb[100:200,100:250]=30
        self.assertEqual(expand_component_boxes(rgb,[[102,100,250,200]])[1],[])

    def test_two_qualifying_regions_are_ambiguous(self):
        rgb=np.full((300,400,3),255,dtype=np.uint8)
        rgb[100:200,100:170]=[80,150,190];rgb[100:200,180:250]=[190,150,80]
        self.assertEqual(expand_component_boxes(rgb,[[101,100,249,200]])[1],[])

    def test_runtime_changes_only_flagged_boxes_and_requires_all_flags_to_be_repairable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source.png';Image.new('RGB',(400,300),'white').save(source)
            geometry={'classification':'panels','orientation':'upright','reading_direction':'ltr','panels':[
                {'order':1,'box':[334,255,663,622],'description':'first'},
                {'order':2,'box':[334,255,663,622],'description':'second'}]}
            converter=Converter(None,root)
            converter.bundles['previous']={'images':[{'label':'Original complete page','path':str(source)}]+
                [{'points':'102,100 249,100 249,199 102,199'} for _ in range(2)]}
            issue={'kind':'clipped_art','panels':[1],'evidence':'Narrow target edge missing.'}
            attempt={'candidate':{'identity':'previous','panels':geometry,'detector':{}},'judge':{},
                'verifier':{'route':'escalate','evidence':[{'panel':1,'verdict':{'route':'escalate',
                    'decision':'escalate','scene_inventory':'pass','reading_order':'pass','issues':[issue]}}]}}
            changes=[{'index':0},{'index':1}]
            with patch('auto_convert.expand_component_boxes',return_value=([[97,100,250,200]]*2,changes)):
                value=converter.pixel_repair(source,attempt)
            self.assertEqual(value['panels']['panels'][1],geometry['panels'][1])
            self.assertLess(value['panels']['panels'][0]['box'][1],geometry['panels'][0]['box'][1])
            self.assertEqual(value['panels']['panels'][0]['box'],[334,242,663,622])
            self.assertEqual([v['index'] for v in value['component_changes']],[0])
            issue['panels']=[1,2]
            with patch('auto_convert.expand_component_boxes',return_value=([[97,100,250,200]]*2,[{'index':0}])):
                self.assertIsNone(converter.pixel_repair(source,attempt))

    def test_final_pixel_correction_is_checked_once_and_cannot_clear_failed_quality(self):
        for final_route in ['keep','escalate']:
            pixel=Mock(return_value={'tier':'astra'})
            final_accept=Mock(return_value={'route':'keep'})  # Unit scope: pixel repair.
            judgments=iter([{'route':'escalate'},{'route':final_route}])
            result=run_page(None,lambda *a:{'tier':'astra'},lambda p,r:r,lambda *a:next(judgments),
                lambda *a:{'route':'escalate'},tiers=('astra',),pixel_repair=pixel,
                final_accept=final_accept)
            self.assertEqual(pixel.call_count,1)
            self.assertEqual(result['attempts'][-1]['stage'],'component-repair')
            self.assertEqual(result['status'],'accepted' if final_route=='keep' else 'whole_page_fallback')
            if final_route=='keep':final_accept.assert_called_once_with(None,result['selected'])
            else:final_accept.assert_not_called()


if __name__=='__main__':unittest.main()
