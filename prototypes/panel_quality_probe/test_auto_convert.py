import copy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
import zipfile
from unittest.mock import patch

from auto_convert import Client, Converter, prepare_input, quality_route, overlap_risk_pairs
from automatic_escalation import RunBlocked
from gemini_budget import Budget
from PIL import Image
from split_check import source_region


class AutoConvertTests(unittest.TestCase):
    def test_intermediate_rejection_skips_redundant_checks_but_final_tier_collects_them(self):
        cases=[('sol-high',True,['escalate'],1,'escalate'),
               ('sol-high',False,['escalate'],1,'escalate'),
               ('sol-high',False,['keep','keep'],2,'keep'),
               ('sol-high',True,['keep','escalate'],2,'escalate'),
               ('astra',False,['escalate','keep'],2,'escalate'),
               ('astra',True,['escalate','keep','keep'],3,'escalate')]
        for tier,global_flag,routes,count,expected in cases:
            with self.subTest(tier=tier,global_flag=global_flag,routes=routes), tempfile.TemporaryDirectory() as tmp:
                converter=Converter(None,Path(tmp))
                converter.bundles['candidate']={'images':[],'panels':[{'order':1},{'order':2}]}
                converter.judgments['candidate']={'global_crop_flags':['art_clipping'] if global_flag else [],
                    'semantic_flags':[],'target_flags':[1,2],'split_checks':[]}
                with patch.object(converter,'verification',side_effect=[({'route':r},{}) for r in routes]) as verify:
                    result=converter.verify(None,{'identity':'candidate','tier':tier})
                self.assertEqual(result['route'],expected);self.assertEqual(verify.call_count,count)

    def test_explicit_timeout_recovery_keeps_original_hold_and_reuses_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);body={'input':'synthetic'}
            identity=hashlib.sha256(b'https://api.openai.com/v1/decisions\n'+json.dumps(body,sort_keys=True).encode()).hexdigest()
            answer={'usage':{'input_tokens':100,'output_tokens':0,'total_tokens':100}}
            with Budget(p/'ledger',cap=20000000) as budget:
                original=Client('not-a-real-key',budget,p/'original')
                with patch.object(original,'http',side_effect=TimeoutError('synthetic timeout')):
                    with self.assertRaises(RunBlocked):original.request('decisions',body,'native')
                recovery=Client('not-a-real-key',budget,p/'recovery',retry_unknown={identity})
                with patch.object(recovery,'http',return_value=answer) as call:
                    raw,record=recovery.request('decisions',body,'native')
                    self.assertEqual(call.call_count,1)
                self.assertEqual(raw,answer)
                self.assertNotEqual(record['request_id'],identity)
                self.assertEqual(budget.entries[identity]['cost'],1000000)
                self.assertFalse((p/'original'/identity/'response.json').exists())
                self.assertEqual(len(budget.entries),2)
                resumed=Client('not-a-real-key',budget,p/'resumed')
                with patch.object(resumed,'http') as call:
                    self.assertEqual(resumed.request('decisions',body,'native')[0],answer)
                    call.assert_not_called()

    def test_explicit_timeout_recovery_is_once_only_and_budgeted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);body={'input':'synthetic'}
            identity=hashlib.sha256(b'https://api.openai.com/v1/decisions\n'+json.dumps(body,sort_keys=True).encode()).hexdigest()
            with Budget(p/'ledger',cap=20000000) as budget:
                client=Client('not-a-real-key',budget,p/'calls',retry_unknown={identity})
                with patch.object(client,'http',side_effect=TimeoutError('synthetic timeout')) as call:
                    for _ in range(3):
                        with self.assertRaises(RunBlocked):client.request('decisions',body,'native')
                    self.assertEqual(call.call_count,2)
                    self.assertEqual(budget.used(),2000000)

    def test_timeout_recovery_does_not_repeat_other_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);body={'input':'synthetic'}
            identity=hashlib.sha256(b'https://api.openai.com/v1/decisions\n'+json.dumps(body,sort_keys=True).encode()).hexdigest()
            with Budget(p/'ledger',cap=20000000) as budget:
                client=Client('not-a-real-key',budget,p/'calls',retry_unknown={identity})
                with patch.object(client,'http',side_effect=RunBlocked('HTTP 429: quota')) as call:
                    for _ in range(2):
                        with self.assertRaises(RunBlocked):client.request('decisions',body,'native')
                    self.assertEqual(call.call_count,1)

    def test_timeout_recovery_cannot_exceed_shared_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);body={'input':'synthetic'}
            identity=hashlib.sha256(b'https://api.openai.com/v1/decisions\n'+json.dumps(body,sort_keys=True).encode()).hexdigest()
            with Budget(p/'ledger',cap=1500000) as budget:
                client=Client('not-a-real-key',budget,p/'calls',retry_unknown={identity})
                with patch.object(client,'http',side_effect=TimeoutError('synthetic timeout')) as call:
                    for _ in range(2):
                        with self.assertRaises(RunBlocked):client.request('decisions',body,'native')
                    self.assertEqual(call.call_count,1)
                    self.assertEqual(budget.used(),1000000)

    def test_split_region_preserves_source_pixels_between_candidate_boxes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.png';destination=root/'region.jpg'
            im=Image.new('RGB',(100,40),'blue')
            im.paste('lime',(40,0,60,40));im.save(source)
            source_region(source,[{'box':[0,0,1000,400]},
                                  {'box':[0,600,1000,1000]}],destination)
            with Image.open(destination) as region:
                self.assertEqual(region.size,(100,40))
                r,g,b=region.getpixel((50,20));self.assertGreater(g,max(r,b)+150)

    def test_split_warning_requires_redetection_at_every_tier(self):
        with tempfile.TemporaryDirectory() as tmp:
            converter=Converter(None,Path(tmp))
            converter.bundles['candidate']={'classification':'panels','images':[],
                'panels':[{'order':1,'box':[0,0,500,500]},
                          {'order':2,'box':[0,510,500,1000]}]}
            for tier in ('sol-low','sol-high','astra'):
                with self.subTest(tier=tier):
                    candidate={'identity':'candidate','tier':tier}
                    # create=True makes the regression run against the old policy.
                    with patch.object(converter,'check_splits',create=True,
                                      return_value={'flags':[[1,2]],'checks':[]}):
                        probabilities={k:0.0 for k in ('scene_defect','order_defect','text_clipping','art_clipping')}
                        converter.client=SimpleNamespace(budget=SimpleNamespace(cap=20000000,used=lambda:0))
                        with patch.object(converter,'decision',return_value=({'probabilities':probabilities},{})) as general:
                            self.assertEqual(converter.judge(None,candidate)['route'],'escalate')
                            general.assert_not_called()
                    with patch.object(converter,'verification') as verifier:
                        self.assertEqual(converter.verify(None,candidate)['route'],'escalate')
                        verifier.assert_not_called()

    def test_contained_insets_require_redetection_but_small_border_overlap_does_not(self):
        p=lambda n,box:{'order':n,'box':box}
        self.assertEqual(overlap_risk_pairs([p(1,[0,0,1000,1000]),p(2,[100,100,300,300])]),[[1,2]])
        self.assertEqual(overlap_risk_pairs([p(1,[0,0,500,1000]),p(2,[490,0,1000,1000])]),[])
        self.assertEqual(overlap_risk_pairs([p(1,[0,0,400,1000]),p(2,[600,0,1000,1000])]),[])

    def test_overlapping_first_pass_requires_redetection_even_when_judges_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            client=SimpleNamespace(budget=SimpleNamespace(cap=20000000,used=lambda:0))
            converter=Converter(client,Path(tmp))
            converter.bundles['candidate']={'classification':'panels','images':[],
                'panels':[{'order':1,'box':[0,0,600,400]},
                          {'order':2,'box':[400,0,1000,400]}]}
            candidate={'identity':'candidate','tier':'sol-low'}
            probabilities={k:0.0 for k in ('scene_defect','order_defect','text_clipping','art_clipping')}
            with patch.object(converter,'decision',return_value=({'probabilities':probabilities},{})):
                self.assertEqual(converter.judge(None,candidate)['route'],'escalate')
            with patch.object(converter,'verification',return_value=({'route':'keep'},{})) as verifier:
                self.assertEqual(converter.verify(None,candidate)['route'],'escalate')
                verifier.assert_not_called()

    def test_contained_first_pass_cannot_be_cleared_by_passing_judges(self):
        with tempfile.TemporaryDirectory() as tmp:
            client=SimpleNamespace(budget=SimpleNamespace(cap=20000000,used=lambda:0))
            converter=Converter(client,Path(tmp))
            converter.bundles['candidate']={'classification':'panels','images':[],
                'panels':[{'order':1,'box':[0,0,1000,1000]},
                          {'order':2,'box':[200,300,700,900]}]}
            candidate={'identity':'candidate','tier':'sol-low'}
            probabilities={k:0.0 for k in ('scene_defect','order_defect','text_clipping','art_clipping')}
            with patch.object(converter,'decision',return_value=({'probabilities':probabilities},{})):
                self.assertEqual(converter.judge(None,candidate)['route'],'escalate')
            with patch.object(converter,'verification') as verifier:
                self.assertEqual(converter.verify(None,candidate)['route'],'escalate')
                verifier.assert_not_called()

    def test_semantic_verifier_clipping_failure_survives_target_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            converter=Converter(None,Path(tmp))
            converter.bundles['candidate']={'images':[], 'panels':[{'order':1}]}
            converter.judgments['candidate']={'global_crop_flags':[],
                'semantic_flags':['scene_defect'],'target_flags':[1]}
            answers=[({'route':'escalate','scene_inventory':'pass',
                       'reading_order':'pass','crop_coverage':'fail'},{}),
                     ({'route':'keep'}, {})]
            with patch.object(converter,'verification',side_effect=answers):
                result=converter.verify(None,{'identity':'candidate','tier':'sol-high'})
            self.assertEqual(result['route'],'escalate')

    def test_global_warning_requires_redetection_before_verifier_can_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            converter=Converter(None,Path(tmp));converter.bundles['candidate']={'images':[],'panels':[]}
            converter.judgments['candidate']={'global_crop_flags':['art_clipping'],
                                              'semantic_flags':[],'target_flags':[]}
            with patch.object(converter,'verification',return_value=({'route':'keep'},{})) as verifier:
                low=converter.verify(None,{'identity':'candidate','tier':'sol-low'})
                self.assertEqual(low['route'],'escalate');verifier.assert_not_called()
                high=converter.verify(None,{'identity':'candidate','tier':'sol-high'})
                self.assertEqual(high['route'],'keep');self.assertEqual(verifier.call_args.args[-1],'high')

    def test_global_clipping_warning_is_not_dismissed_by_target_passes(self):
        result=quality_route({'scene_defect':0.04,'order_defect':0.09,
                              'text_clipping':0.34,'art_clipping':0.77},
                             {1:{'text_clipping':0.0,'art_clipping':0.05}})
        self.assertEqual(result['route'],'escalate')
        self.assertEqual(result['global_crop_flags'],['art_clipping'])

    def test_incomplete_preparation_never_overwrites_existing_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);source=p/'source';source.mkdir()
            existing=p/'work/pages/0001.jpg';existing.parent.mkdir(parents=True)
            existing.write_bytes(b'preserve incomplete evidence')
            with self.assertRaisesRegex(ValueError,'incomplete input preparation'):
                prepare_input(source,p/'work',None)
            self.assertEqual(existing.read_bytes(),b'preserve incomplete evidence')

    def test_archive_traversal_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); archive=p/'bad.cbz'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape.jpg',b'bad')
            with self.assertRaises(ValueError):prepare_input(archive,p/'work',None)
            self.assertFalse((p/'escape.jpg').exists())

    def test_cache_miss_calls_provider_and_second_request_reuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with Budget(p/'ledger',cap=20000000) as budget:
                client=Client('not-a-real-key',budget,p/'calls')
                answer={'model':'gpt-6-luna','answers':[],
                        'usage':{'input_tokens':100,'output_tokens':0,'total_tokens':100}}
                with patch.object(client,'http',return_value=answer) as call:
                    first=client.request('decisions',{'model':'gpt-6-luna','input':'synthetic','questions':[]},'native')
                    second=client.request('decisions',{'model':'gpt-6-luna','input':'synthetic','questions':[]},'native')
                    self.assertEqual(first[0],second[0]);self.assertEqual(call.call_count,1)
                    self.assertEqual(client.new_calls,1);self.assertEqual(client.cache_hits,1)

    def test_unknown_dispatched_request_cannot_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with Budget(p/'ledger',cap=20000000) as budget:
                client=Client('not-a-real-key',budget,p/'calls')
                with patch.object(client,'http',side_effect=TimeoutError('synthetic timeout')) as call:
                    for _ in range(2):
                        with self.assertRaises(RunBlocked):client.request('decisions',{'input':'synthetic'},'native')
                    self.assertEqual(call.call_count,1)
                    self.assertEqual(budget.used(),1000000)

    def test_target_flags_are_not_dismissed_by_global_pass(self):
        result=quality_route({'scene_defect':0.0,'order_defect':0.0},
                             {1:{'text_clipping':0.8,'art_clipping':0.0}})
        self.assertEqual(result['route'],'escalate');self.assertEqual(result['target_flags'],[1])


class DetectorOutputRecoveryTests(unittest.TestCase):
    """Actual detect/Client/Budget boundary; only HTTP responses are synthetic."""
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')))

    def fixture(self,name,cap=3000000):
        root=self.root/name;root.mkdir()
        page=root/'source.jpg';Image.new('RGB',(100,100),'white').save(page)
        budget=self.enterContext(Budget(root/'ledger',cap=cap))
        client=Client('synthetic-not-credential',budget,root/'calls')
        return page,budget,client,Converter(client,root)

    @staticmethod
    def exhausted(limit=8192):
        return {'status':'incomplete','model':'gpt-6-astra',
            'incomplete_details':{'reason':'max_output_tokens'},
            'output':[{'id':'synthetic-reasoning','type':'reasoning','summary':[]}],
            'usage':{'input_tokens':10,'output_tokens':limit,'total_tokens':limit+10,
                     'output_tokens_details':{'reasoning_tokens':limit}}}

    @staticmethod
    def completed():
        panels={'classification':'whole_page','orientation':'upright','reading_direction':'ltr',
            'panels':[{'order':1,'description':'Synthetic page',
                       'bounds':{'left':0,'top':0,'right':1000,'bottom':1000}}]}
        return {'status':'completed','model':'gpt-6-astra',
            'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(panels)}]}],
            'usage':{'input_tokens':10,'output_tokens':30,'total_tokens':40}}

    def http_answers(self,client,budget,answers):
        dispatched=[]
        def http(endpoint,body):
            if endpoint=='responses/input_tokens':return {'input_tokens':10}
            self.assertEqual(endpoint,'responses')
            identity=hashlib.sha256(b'openai-responses:'+json.dumps(body,sort_keys=True).encode()).hexdigest()
            row=budget.entries[identity]
            # The reservation is durable before the synthetic paid boundary.
            rows=[json.loads(line) for line in budget.path.read_text().splitlines()]
            self.assertTrue(any(r.get('kind')=='reserve' and r['id']==identity for r in rows))
            dispatched.append({'body':copy.deepcopy(body),'reservation':row['reservation'],'identity':identity})
            answer=answers[len(dispatched)-1]
            if isinstance(answer,Exception):raise answer
            return copy.deepcopy(answer)
        self.enterContext(patch.object(client,'http',side_effect=http))
        return dispatched

    def test_exhaustion_retries_once_with_larger_budget_and_reuses_both_records(self):
        page,budget,client,converter=self.fixture('success')
        dispatched=self.http_answers(client,budget,[self.exhausted(),self.completed()])
        result=converter.detect(page,'astra')
        self.assertNotIn('invalid',result)
        self.assertEqual(len(dispatched),2)
        first,second=dispatched
        self.assertEqual(first['body']['max_output_tokens'],8192)
        self.assertEqual(second['body'],{**first['body'],'max_output_tokens':16384})
        self.assertEqual([r['reservation'] for r in dispatched],[700000,1069200])
        recovery=result['detector']['output_limit_recovery']
        self.assertEqual(recovery['original_request']['request_id'],first['identity'])
        self.assertEqual(result['detector']['request_id'],second['identity'])
        self.assertNotEqual(first['identity'],second['identity'])
        self.assertIsNone(result['detector'].get('retry_of'))
        self.assertEqual(recovery['original_status'],'incomplete')
        self.assertEqual(recovery['incomplete_details'],{'reason':'max_output_tokens'})
        self.assertEqual((recovery['original_output_limit'],recovery['expanded_output_limit']),(8192,16384))
        self.assertEqual([budget.entries[r['identity']]['cost'] for r in dispatched],[409725,1625])
        self.assertEqual((budget.used(),len(budget.entries),client.new_calls),(411350,2,2))
        files={path:path.read_bytes() for row in budget.entries.values()
               for path in Path(row['path']).iterdir() if path.is_file()}
        original=Path(recovery['original_request']['path'])/'response.json'
        self.assertEqual(json.loads(original.read_text())['status'],'incomplete')
        resumed=Client('synthetic-not-credential',budget,page.parent/'resumed-calls')
        with patch.object(resumed,'http',side_effect=AssertionError('cache replay attempted HTTP')):
            replay=Converter(resumed,page.parent).detect(page,'astra')
        self.assertEqual(replay['panels'],result['panels'])
        self.assertEqual(replay['detector']['request_id'],second['identity'])
        self.assertEqual(replay['detector']['output_limit_recovery']['original_request']['request_id'],first['identity'])
        self.assertEqual((resumed.cache_hits,resumed.new_calls,budget.used()),(2,0,411350))
        self.assertTrue(all(path.read_bytes()==data for path,data in files.items()))

    def test_second_exhaustion_stays_invalid_without_third_request(self):
        page,budget,client,converter=self.fixture('twice')
        dispatched=self.http_answers(client,budget,[self.exhausted(),self.exhausted(16384)])
        result=converter.detect(page,'astra')
        self.assertEqual(result['invalid'],'response did not complete')
        self.assertEqual(len(dispatched),2)
        self.assertEqual(result['detector']['output_limit_recovery']['original_request']['request_id'],dispatched[0]['identity'])
        self.assertEqual((len(budget.entries),budget.used()),(2,1229050))
        with patch.object(client,'http',side_effect=AssertionError('cache replay attempted HTTP')):
            self.assertEqual(converter.detect(page,'astra')['invalid'],result['invalid'])
        self.assertEqual((client.new_calls,client.cache_hits),(2,2))

    def test_non_exhaustion_refusal_and_malformed_responses_never_expand(self):
        completed=self.completed()
        malformed=copy.deepcopy(completed);malformed['output'][0]['content'][0]['text']='not JSON'
        refusal=copy.deepcopy(completed);refusal['output'][0]['content']=[{'type':'refusal','refusal':'Synthetic refusal'}]
        variants=[('completed',completed),('malformed-completed',malformed),('refusal-completed',refusal)]
        for reason in ('content_filter','unknown',None):
            raw=self.exhausted();raw['incomplete_details']={'reason':reason}
            variants.append((str(reason),raw))
        for label,output in [('refusal',[{'type':'message','content':[{'type':'refusal','refusal':'Synthetic refusal'}]}]),
                ('unknown-item',[{}]),('unknown-kind',[{'type':'tool_call','content':[]}]),
                ('missing-message-content',[{'type':'message'}]),
                ('invalid-text',[{'type':'message','content':[{'type':'output_text','text':None}]}]),
                ('invalid-summary',[{'type':'reasoning','summary':[{'type':'summary_text','text':None}]}]),
                ('invalid-output',{})]:
            raw=self.exhausted();raw['output']=output;variants.append((label,raw))
        for label,raw in variants:
            with self.subTest(label=label):
                page,budget,client,converter=self.fixture(label)
                dispatched=self.http_answers(client,budget,[raw])
                result=converter.detect(page,'astra')
                self.assertEqual(len(dispatched),1)
                self.assertNotIn('output_limit_recovery',result['detector'])
                if label=='completed':self.assertNotIn('invalid',result)
                else:self.assertIn('invalid',result)

    def test_empty_and_partial_text_exhaustion_use_the_same_bounded_route(self):
        for label,output in [('empty',[]),('partial',[{'type':'message','status':'incomplete',
                'content':[{'type':'output_text','text':'{"classification":'}]}])]:
            with self.subTest(label=label):
                page,budget,client,converter=self.fixture(label)
                raw=self.exhausted();raw['output']=output
                dispatched=self.http_answers(client,budget,[raw,self.completed()])
                self.assertNotIn('invalid',converter.detect(page,'astra'))
                self.assertEqual(len(dispatched),2)

    def test_cap_blocks_larger_request_before_paid_dispatch(self):
        page,budget,client,converter=self.fixture('cap',cap=1300000)
        dispatched=self.http_answers(client,budget,[self.exhausted()])
        with self.assertRaisesRegex(RunBlocked,'spending cap reached'):
            converter.detect(page,'astra')
        self.assertEqual(len(dispatched),1)
        self.assertEqual((len(budget.entries),budget.used(),client.new_calls),(1,409725,1))
        original=Path(next(iter(budget.entries.values()))['path'])/'response.json'
        self.assertEqual(json.loads(original.read_text())['status'],'incomplete')
        self.assertEqual(len(list((page.parent/'calls').glob('*/response.json'))),1)

    def test_unknown_transport_failure_never_gets_output_recovery(self):
        page,budget,client,converter=self.fixture('transport')
        dispatched=self.http_answers(client,budget,[TimeoutError('synthetic timeout')])
        for _ in range(2):
            with self.assertRaises(RunBlocked):converter.detect(page,'astra')
        self.assertEqual(len(dispatched),1)
        self.assertEqual((len(budget.entries),budget.used(),client.new_calls),(1,700000,1))
        self.assertEqual(len(list((page.parent/'calls').glob('*/request.json'))),1)
        self.assertFalse(list((page.parent/'calls').glob('*/response.json')))


if __name__=='__main__':unittest.main()
