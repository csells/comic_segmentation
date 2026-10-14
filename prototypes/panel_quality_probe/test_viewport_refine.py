import copy
import unittest
from viewport_refine import reading_viewports


class ViewportTests(unittest.TestCase):
    def test_preserves_identity_order_and_source_proposal(self):
        value={'classification':'panels','reading_direction':'rtl','panels':[
            {'order':1,'description':'right view','box':[100,600,300,950]},
            {'order':2,'description':'left view','box':[100,50,300,450]}]}
        before=copy.deepcopy(value)
        result,changes=reading_viewports(value,1000,1500)
        self.assertEqual(value,before)
        self.assertEqual([(p['order'],p['description']) for p in result['panels']],[(1,'right view'),(2,'left view')])
        self.assertEqual(result['reading_direction'],'rtl')
        self.assertEqual(changes[0]['margin_source_pixels'],[10,10])
        for old,new in zip(value['panels'],result['panels']):
            self.assertLess(new['box'][0],old['box'][0]);self.assertLess(new['box'][1],old['box'][1])
            self.assertGreater(new['box'][2],old['box'][2]);self.assertGreater(new['box'][3],old['box'][3])

    def test_page_edge_clamping_and_thin_panel_zoom_cap(self):
        value={'classification':'panels','panels':[{'order':1,'box':[0,0,50,1000]}]}
        result,changes=reading_viewports(value,1000,1000)
        self.assertEqual(result['panels'][0]['box'],[0,0,53,1000])
        self.assertEqual(changes[0]['margin_source_pixels'],[10,3])

    def test_whole_page_is_identical(self):
        value={'classification':'whole_page','panels':[{'order':1,'box':[0,0,1000,1000]}]}
        result,changes=reading_viewports(value,1000,1500)
        self.assertEqual(result,value);self.assertEqual(changes,[])

    def test_invalid_geometry_cannot_expand_to_plausible_box(self):
        value={'classification':'panels','panels':[{'order':1,'box':[20,900,20,100]}]}
        with self.assertRaises(ValueError):reading_viewports(value,1000,1500)
        with self.assertRaises(ValueError):reading_viewports(value,0,1500)


if __name__=='__main__':unittest.main()
