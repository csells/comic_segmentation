import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
from auto_convert import Converter, source_page_context
from narrative_context import request_body


def verdict(kind):
    value={'classification':kind,'views':['first','second'] if kind=='distinct' else ['one'], 'evidence':'Visual and narrative evidence.'}
    return {'output':[{'content':[{'type':'output_text','text':json.dumps(value)}]}]}


class NarrativeContextTests(unittest.TestCase):
    def check(self, final, primary='continuous', has_context=True, tier='astra'):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);files=[]
            for i,color in enumerate(['red','green','blue']):
                p=root/f'{i}.jpg';Image.new('RGB',(100,100),color).save(p);files.append(p)
            client=Mock();replies=[({'model':'gpt-6-luna','answers':[{'type':'predicate','name':'false_split','probability':.95}]},{})]
            if tier=='astra':replies.append((verdict(primary),{}))
            if tier=='astra' and primary!='distinct' and has_context:replies.append((verdict(final),{}))
            client.request.side_effect=replies
            context={str(files[-1]):[str(p) for p in files[:-1]]} if has_context else {}
            converter=Converter(client,root,context)
            converter.bundles['test']={'classification':'panels','panels':[{'order':1,'box':[0,0,500,1000]}, {'order':2,'box':[500,0,1000,1000]}], 'images':[{'path':str(files[-1])}]}
            result=converter.check_splits({'identity':'test','bundle':str(root/'bundle.json'),'tier':tier})
            return result,client.request.call_args_list

    def test_distinct_context_clears_only_final_tier_warning(self):
        result,calls=self.check('distinct')
        self.assertEqual(result['flags'],[]);self.assertEqual(len(calls),3)
        evidence=result['checks'][0]['preceding_page_disambiguation']
        self.assertEqual(len(evidence['source_pages']),2)
        self.assertTrue(all(len(p['sha256'])==64 for p in evidence['source_pages']))
        self.assertEqual(len([c for c in calls[-1].args[1]['input'][0]['content'] if c['type']=='input_image']),4)

    def test_uncertain_or_continuous_context_retains_warning(self):
        for kind in ['continuous','uncertain']:
            with self.subTest(kind=kind):self.assertEqual(self.check(kind)[0]['flags'],[[1,2]])

    def test_no_context_cannot_clear_and_existing_distinct_needs_no_extra_call(self):
        result,calls=self.check('distinct',has_context=False)
        self.assertEqual(result['flags'],[[1,2]]);self.assertEqual(len(calls),2)
        result,calls=self.check('distinct',primary='distinct')
        self.assertEqual(result['flags'],[]);self.assertEqual(len(calls),2)
        result,calls=self.check('distinct',tier='sol-high')
        self.assertEqual(result['flags'],[[1,2]]);self.assertEqual(len(calls),1)

    def test_actual_predecessors_come_from_complete_input_order(self):
        records=[{'image':f'{i:04}.jpg'} for i in range(1,7)]
        root=Path('/example/input/pages');context=source_page_context(records,root)
        self.assertEqual(context[str(root/'0001.jpg')],[])
        self.assertEqual(context[str(root/'0002.jpg')],[str(root/'0001.jpg')])
        # A bounded selection of pages2/6 must still use4/5 as context for6.
        self.assertEqual(context[str(root/'0006.jpg')],[str(root/'0004.jpg'),str(root/'0005.jpg')])

    def test_invalid_context_window_is_rejected(self):
        for pages in [[],['a','b','c']]:
            with self.assertRaises(ValueError):request_body(pages,'target','region')


class ContextualTargetTests(unittest.TestCase):
    def verify_target(self, resolved=True, stronger='keep', global_failure=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.jpg';previous=root/'previous.jpg'
            source.write_bytes(b'source');previous.write_bytes(b'previous')
            converter=Converter(None,root,{str(source):[str(previous)]})
            bundle={'classification':'panels','reading_direction':'ltr','panels':[{'order':1},{'order':2}],
                    'images':[{'label':'Original complete page','path':str(source)},
                              {'label':'Candidate crop 2 in reading order','path':'unused'}]}
            converter.bundles['candidate']=bundle
            checks=[{'pair':[1,2],'preceding_page_disambiguation':{'verdict':{'classification':'distinct'}}}] if resolved else []
            converter.judgments['candidate']={'global_crop_flags':[],'semantic_flags':['scene_defect'] if global_failure else [],'target_flags':[2], 'split_checks':checks}
            replies=[({'route':'escalate'}, {})]
            if global_failure:replies.insert(0,({'route':'escalate'}, {}))
            if resolved:replies.append(({'route':stronger}, {}))
            with patch.object(converter,'verification',side_effect=replies) as verify:
                result=converter.verify(source,{'identity':'candidate','tier':'astra'})
                return result,verify.call_args_list

    def test_context_can_clear_only_target_with_resolved_narrative_disagreement(self):
        result,calls=self.verify_target()
        self.assertEqual(result['route'],'keep');self.assertEqual(len(calls),2)
        self.assertEqual(calls[-1].kwargs['model'],'gpt-6-astra')
        self.assertEqual(len(calls[-1].args[0]['images']),3)
        result,calls=self.verify_target(resolved=False)
        self.assertEqual(result['route'],'escalate');self.assertEqual(len(calls),1)

    def test_stronger_target_failure_remains_failure(self):
        self.assertEqual(self.verify_target(stronger='escalate')[0]['route'],'escalate')

    def test_target_context_pass_cannot_erase_global_failure(self):
        result,calls=self.verify_target(global_failure=True)
        self.assertEqual(result['route'],'escalate');self.assertEqual(len(calls),3)

if __name__=='__main__':unittest.main()
