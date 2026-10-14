import json
from pathlib import Path
import tempfile
import unittest

from escalation_probe import parse_verdict, cached_verdict, judge_payload


def response(value):
    return {'status':'completed','output':[{'type':'message','status':'completed',
            'content':[{'type':'output_text','text':json.dumps(value)}]}]}


class EscalationTests(unittest.TestCase):
    def test_accept_requires_complete_checks_and_no_issues(self):
        good={'decision':'accept','scene_inventory':'pass','reading_order':'pass',
              'crop_coverage':'pass','issues':[]}
        self.assertEqual(parse_verdict(response(good),3)['route'],'keep')
        for field in ['scene_inventory','reading_order','crop_coverage']:
            with self.subTest(field=field):
                self.assertEqual(parse_verdict(response({**good,field:'uncertain'}),3)['route'],'escalate')
        issue={'kind':'clipped_text','panels':[2],'evidence':'Balloon word ends at crop edge.'}
        self.assertEqual(parse_verdict(response({**good,'issues':[issue]}),3)['route'],'escalate')

    def test_nonaccept_never_keeps_candidate(self):
        for decision in ['escalate','uncertain']:
            verdict={'decision':decision,'scene_inventory':'pass','reading_order':'pass',
                     'crop_coverage':'pass','issues':[]}
            self.assertEqual(parse_verdict(response(verdict),2)['route'],'escalate')

    def test_incomplete_refused_and_invalid_verdicts_fail_closed(self):
        for value in [{'status':'incomplete','output':[]},
                      {'status':'completed','output':[{'type':'message','content':[{'type':'refusal'}]}]},
                      response({'decision':'accept'}),
                      response({'decision':'accept','scene_inventory':'pass','reading_order':'pass',
                                'crop_coverage':'pass','issues':[{'kind':'clipped_art','panels':[3], 'evidence':'x'}]})]:
            with self.subTest(value=value), self.assertRaises(ValueError):parse_verdict(value,2)

    def test_unknown_attempt_cannot_be_repeated(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);entries={'id':{'path':str(out)}}
            self.assertIsNone(cached_verdict({},'new'))
            with self.assertRaises(ValueError):cached_verdict(entries,'id')
            (out/'verdict.json').write_text('{}')
            self.assertEqual(cached_verdict(entries,'id'),out)

    def test_payload_uses_only_candidate_geometry_and_images(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'private-pass-sol-205.jpg';p.write_bytes(b'jpeg-fixture')
            bundle={'classification':'panels','reading_direction':'ltr',
                    'panels':[{'order':1,'box':[0,0,1000,1000]}],
                    'expected':'fail','detector':'sol','source_page':205,
                    'images':[{'label':'Original full page','path':str(p)}]}
            payload=judge_payload(bundle,'audit prompt')
            text=' '.join(x['text'] for x in payload if x['type']=='input_text')
            self.assertNotIn('expected',text);self.assertNotIn('sol',text)
            self.assertNotIn('205',text);self.assertNotIn(str(p),text)
            self.assertEqual(payload[-1]['type'],'input_image')


if __name__=='__main__':unittest.main()
