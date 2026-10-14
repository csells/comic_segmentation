import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

from auto_convert import Converter
from gutter_audit import edge_gutters, reconcile_regions


def panel(order,box):return {'order':order,'description':'Synthetic scene','box':box}
def page(panels):return {'classification':'panels','orientation':'upright','reading_direction':'ltr','panels':panels}


class GutterAuditTests(unittest.TestCase):
    def test_first_pass_gutter_risk_cannot_be_cleared_by_passing_judges(self):
        with tempfile.TemporaryDirectory() as tmp:
            converter=Converter(None,Path(tmp))
            converter.bundles['candidate']={'classification':'panels','images':[],
                'panels':[panel(1,[0,0,1000,1000])]}
            candidate={'identity':'candidate','tier':'sol-low','gutter_risks':[{'target':1}]}
            with patch.object(converter,'decision') as decision:
                self.assertEqual(converter.judge(None,candidate)['route'],'escalate')
                decision.assert_not_called()
            with patch.object(converter,'verification') as verifier:
                self.assertEqual(converter.verify(None,candidate)['route'],'escalate')
                verifier.assert_not_called()

    def test_stronger_candidate_uses_regional_detection_for_hidden_gutter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.jpg'
            im=Image.new('RGB',(250,250),'gray');im.paste('white',(122,0,128,250));im.save(source,quality=95)
            converter=Converter(None,root/'run');converter.root.mkdir()
            raw={'tier':'sol-high','panels':page([panel(1,[0,0,1000,1000])]),'detector':{},'source_sha256':'synthetic'}
            regional={'panels':page([panel(1,[0,0,1000,510]),panel(2,[0,490,1000,1000])]),'detector':{'cached':True}}
            with patch.object(converter,'detect',return_value=regional) as detector, patch.object(converter,'review_region',return_value={'answer':{'distinct_scenes':True,'context_matches':[]},'request':{}}):
                result=converter.refine(source,raw)
                self.assertEqual(len(result['panels']['panels']),2)
                self.assertEqual(detector.call_count,1)

    def test_narrow_gutter_is_a_risk_but_wide_background_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.png'
            im=Image.new('RGB',(250,250),'gray');im.paste('white',(122,0,128,250));im.save(path)
            self.assertTrue(edge_gutters(path))
            im.paste('white',(70,0,180,250));im.save(path)
            self.assertFalse(edge_gutters(path))

    def test_existing_partial_neighbor_is_not_inserted_as_a_new_panel(self):
        value=page([panel(1,[0,0,600,1000]),panel(2,[500,0,1000,1000])])
        # Crop of target2 includes only the bottom strip of already-known panel1.
        regional=page([panel(1,[0,0,200,1000]),panel(2,[190,0,1000,1000])])
        result,audit=reconcile_regions(value,2,regional,(0,500,1000,1000),(1000,1000))
        self.assertEqual(result,value);self.assertFalse(audit['replaced'])
        self.assertEqual(audit['context_matches'][0]['existing_orders'],[1])

    def test_contained_fragment_requires_independent_confirmation(self):
        value=page([panel(1,[0,0,600,1000]),panel(2,[400,300,1000,1000])])
        regional=page([panel(1,[0,0,1000,1000]),panel(2,[800,700,1000,950])])
        # A small head inside a much larger neighboring rectangle has low IoU.
        result,audit=reconcile_regions(value,1,regional,(0,0,1000,600),(1000,1000))
        self.assertTrue(audit['replaced'])
        result,audit=reconcile_regions(value,1,regional,(0,0,1000,600),(1000,1000),{2:2})
        self.assertEqual(result,value);self.assertFalse(audit['replaced'])
        with self.assertRaisesRegex(ValueError,'spatially supported'):
            reconcile_regions(value,1,regional,(0,0,1000,600),(1000,1000),{1:2})

    def test_unconfirmed_regional_proposal_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            converter=Converter(None,Path(tmp))
            converter.bundles['candidate']={'classification':'panels','images':[],'panels':[]}
            candidate={'identity':'candidate','tier':'sol-high','gutter_risks':[{}],
                       'regional_audits':[{'unresolved':True}]}
            with patch.object(converter,'check_splits') as check:
                self.assertEqual(converter.judge(None,candidate)['route'],'escalate')
                check.assert_not_called()

    def test_regional_certificate_only_clears_its_exact_sibling_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.jpg';Image.new('RGB',(100,100),'gray').save(source)
            converter=Converter(None,root)
            candidate=converter.bundle_candidate(source,{'tier':'sol-high'},page([
                panel(1,[0,0,400,1000]),panel(2,[400,0,700,1000]),panel(3,[700,0,1000,1000])]),[])
            candidate['regional_audits']=[{'replaced':True,'replacement_boxes':[[0,0,400,1000],[400,0,700,1000]],
                'review':{'answer':{'distinct_scenes':True}}}]
            from types import SimpleNamespace
            converter.client=SimpleNamespace(request=lambda *args:({},{}))
            with patch('auto_convert.parse_answers',return_value={'probabilities':{'false_split':.99}}):
                result=converter.check_splits(candidate)
                self.assertEqual(result['flags'],[[2,3]])
                self.assertEqual([c['regional_split_certified'] for c in result['checks']],[True,False])
                candidate['regional_audits'][0]['review']['answer']['distinct_scenes']=False
                self.assertEqual(converter.check_splits(candidate)['flags'],[[1,2],[2,3]])

    def test_new_views_map_back_to_page_pixels_in_regional_order(self):
        value=page([panel(1,[0,0,200,1000]),panel(2,[200,100,800,900]),panel(3,[800,0,1000,1000])])
        regional=page([panel(1,[0,500,1000,1000]),panel(2,[0,0,1000,500])])
        result,audit=reconcile_regions(value,2,regional,(100,200,900,800),(1000,1000))
        self.assertTrue(audit['replaced'])
        self.assertEqual([p['box'] for p in result['panels']],[[0,0,200,1000],[200,500,800,900],[200,100,800,500],[800,0,1000,1000]])
        self.assertEqual([p['order'] for p in result['panels']],[1,2,3,4])
        self.assertEqual(len(value['panels']),3)

if __name__=='__main__':unittest.main()
