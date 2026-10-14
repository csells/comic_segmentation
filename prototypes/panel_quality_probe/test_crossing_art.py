import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from auto_convert import Converter
from automatic_escalation import RunBlocked
from crossing_art import OCCLUSION_QUESTIONS, occlusion_request_body, partial_overlap_pairs, request_body


class CrossingArtTests(unittest.TestCase):
    def test_contained_inset_and_disjoint_views_need_no_ownership_audit(self):
        background={'order':1,'box':[0,0,500,1000]}
        inset={'order':2,'box':[200,200,400,800]}
        next_view={'order':3,'box':[510,0,1000,1000]}
        self.assertEqual(partial_overlap_pairs([background,inset,next_view]),[])
        protruding={'order':3,'box':[400,0,1000,1000]}
        self.assertEqual(partial_overlap_pairs([background,protruding]),[[1,3]])

    def check(self,probability):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.jpg';source.write_bytes(b'original source bytes')
            client=Mock();client.request.return_value=({'model':'gpt-6-luna','answers':[
                {'type':'predicate','name':'crossing_art','probability':probability}]},{'request_id':'risk'})
            converter=Converter(client,Path(tmp))
            bundle={'classification':'panels','images':[{'path':str(source)}],
                    'panels':[{'order':1,'box':[0,0,600,1000]}, {'order':2,'box':[500,0,1000,1000]}]}
            return converter.check_crossing_art(bundle)

    def test_uncertainty_routes_to_stronger_check_but_is_not_a_defect_verdict(self):
        self.assertEqual(self.check(.49)['targets'],[1,2])
        self.assertEqual(self.check(.2)['targets'],[1,2])
        self.assertEqual(self.check(.08)['targets'],[])
        with self.assertRaises(RunBlocked):self.check(float('nan'))

    def test_risk_request_has_source_only_no_candidate_anchoring(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.jpg';source.write_bytes(b'original')
            content=request_body(source)['input'][0]['content']
            self.assertEqual([v['type'] for v in content],['input_text','input_image'])
            self.assertNotIn('Candidate geometry',content[0]['text'])

    def test_occlusion_request_is_source_only_and_preserves_old_crossing_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source.jpg'; source.write_bytes(b'original-source')
            old = request_body(source)
            body = occlusion_request_body(source)
            self.assertEqual(body['model'], 'gpt-6-luna')
            self.assertEqual(body['questions'], OCCLUSION_QUESTIONS)
            self.assertNotEqual(body['questions'], old['questions'])
            self.assertEqual(body['input'], old['input'])
            content = body['input'][0]['content']
            self.assertEqual([item['type'] for item in content], ['input_text', 'input_image'])
            self.assertEqual(base64.b64decode(content[1]['image_url'].split(',', 1)[1]), b'original-source')
            self.assertNotIn(str(source), str(body))
            self.assertNotIn('Candidate geometry', str(body))
            self.assertEqual(request_body(source), old)

    def test_risk_forces_stronger_target_inspection_even_when_cheap_check_passes(self):
        converter=Converter(None,Path('/unused'))
        converter.bundles['c']={'classification':'panels','reading_direction':'ltr','panels':[],
            'images':[{'label':'Original complete page','path':'source'},
                      {'label':'Candidate crop 2 in reading order','path':'crop'}]}
        converter.judgments['c']={'global_crop_flags':[],'semantic_flags':[], 'target_flags':[],
                                'crossing_art':{'targets':[2]}}
        converter.verification=Mock(return_value=({'route':'escalate'},{}))
        result=converter.verify(None,{'identity':'c','tier':'sol-high'})
        self.assertEqual(result['route'],'escalate')
        self.assertEqual(converter.verification.call_args.kwargs['model'],'gpt-6-astra')
        converter.verification.return_value=({'route':'keep'}, {})
        self.assertEqual(converter.verify(None,{'identity':'c','tier':'sol-high'})['route'],'keep')

    def test_stronger_target_acceptance_cannot_clear_independent_global_failure(self):
        converter=Converter(None,Path('/unused'))
        converter.bundles['c']={'images':[]}
        converter.judgments['c']={'global_crop_flags':['art_clipping'],'semantic_flags':[],
                                'target_flags':[], 'crossing_art':{'targets':[2]}}
        converter.verification=Mock(side_effect=[({'route':'escalate'},{}),({'route':'keep'}, {})])
        self.assertEqual(converter.verify(None,{'identity':'c','tier':'sol-high'})['route'],'escalate')

    def test_final_crossing_candidate_uses_stronger_global_verifier_and_preserves_target_failure(self):
        converter=Converter(None,Path('/unused'))
        converter.bundles['c']={'images':[]}
        converter.judgments['c']={'global_crop_flags':['art_clipping'],'semantic_flags':[],
                                'target_flags':[], 'crossing_art':{'targets':[2]}}
        for global_result,target_result,expected in [('keep','escalate','escalate'),
                                                    ('escalate','keep','escalate'),
                                                    ('keep','keep','keep')]:
            converter.verification=Mock(side_effect=[({'route':global_result},{}),({'route':target_result}, {})])
            self.assertEqual(converter.verify(None,{'identity':'c','tier':'astra'})['route'],expected)
            self.assertTrue(all(c.kwargs['model']=='gpt-6-astra' for c in converter.verification.call_args_list))


if __name__=='__main__':unittest.main()
