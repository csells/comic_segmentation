import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from PIL import Image
from auto_convert import Client,Converter
from automatic_escalation import RunBlocked
from gemini_budget import Budget
from continuity_verifier import response_verdict


def response(value):
    return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(value)}]}]}


def verdict(kind):
    return {'classification':kind,'views':['first view','second view'] if kind=='distinct' else ['one view'],
            'evidence':'Source perspective and framing evidence.'}

class ContinuityDisambiguationTests(unittest.TestCase):
    def check(self,tier,probability,secondary=None):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.png';Image.new('RGB',(100,100),'white').save(source)
            client=Mock();replies=[({'model':'gpt-6-luna','answers':[{'type':'predicate','name':'false_split','probability':probability}]},{'request_id':'primary'})]
            if secondary is not None:replies.append((response(verdict(secondary)),{'request_id':'adjudication'}))
            client.request.side_effect=replies
            converter=Converter(client,root)
            converter.bundles['candidate']={'classification':'panels','images':[{'path':str(source)}],
                'panels':[{'order':1,'box':[0,0,400,1000]},{'order':2,'box':[500,0,1000,1000]}]}
            out=converter.check_splits({'identity':'candidate','bundle':str(root/'bundle.json'),'tier':tier})
            return out,client.request.call_args_list

    def test_lower_tiers_keep_mandatory_redetection(self):
        for tier in ('sol-low','sol-high'):
            with self.subTest(tier=tier):
                out,calls=self.check(tier,.95);self.assertEqual(out['flags'],[[1,2]]);self.assertEqual(len(calls),1)

    def test_final_tier_distinct_verdict_clears_only_split_flag(self):
        out,calls=self.check('astra',.95,'distinct');self.assertEqual(out['flags'],[]);self.assertEqual(len(calls),2)
        self.assertEqual(out['checks'][0]['probability'],.95)
        self.assertEqual(out['checks'][0]['final_tier_disambiguation']['verdict']['classification'],'distinct')
        self.assertEqual(calls[1].args[0],'responses')
        content=calls[1].args[1]['input'][0]['content']
        self.assertEqual(len([v for v in content if v['type']=='input_image']),1)
        self.assertNotIn('Candidate crop',json.dumps(content))

    def test_uncertainty_or_continuity_retains_warning(self):
        for kind in ('continuous','uncertain'):
            with self.subTest(kind=kind):
                out,calls=self.check('astra',.95,kind);self.assertEqual(out['flags'],[[1,2]]);self.assertEqual(len(calls),2)

    def test_no_secondary_call_for_original_clear_result(self):
        out,calls=self.check('astra',.0);self.assertEqual(out['flags'],[]);self.assertEqual(len(calls),1)

    def test_invalid_or_unsupported_adjudication_is_not_acceptance(self):
        for value in [dict(verdict('distinct'),views=['single']),dict(verdict('continuous'),views=['a','b']),
                      dict(verdict('distinct'),evidence=''),dict(verdict('distinct'),classification='accept')]:
            with self.subTest(value=value),self.assertRaises(ValueError):response_verdict(response(value))
        raw=response(verdict('distinct'));raw['status']='incomplete'
        with self.assertRaises(ValueError):response_verdict(raw)

class ContinuityOutputRecoveryTests(unittest.TestCase):
    """Real continuity routing and durable requests; synthetic HTTP only."""
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')))

    def fixture(self,name,answers,predecessor=False):
        root=self.root/name;root.mkdir()
        source=root/'source.png';Image.new('RGB',(100,100),'white').save(source)
        budget=self.enterContext(Budget(root/'ledger',cap=3000000))
        client=Client('synthetic-not-credential',budget,root/'calls')
        context={str(source.resolve()):[str(source)]} if predecessor else {}
        converter=Converter(client,root,source_context=context)
        panels=[{'order':1,'box':[0,0,400,1000]},{'order':2,'box':[500,0,1000,1000]}]
        images=[{'label':'Original complete page','path':str(source)}]
        for p in panels:
            crop=root/f'crop-{p["order"]}.jpg';Image.new('RGB',(100,40),'white').save(crop)
            images.append({'label':f'Candidate crop {p["order"]} in reading order','path':str(crop)})
        converter.bundles['candidate']={'classification':'panels','reading_direction':'ltr','images':images,'panels':panels}
        candidate={'identity':'candidate','bundle':str(root/'bundle.json'),'tier':'astra','source_sha256':'synthetic'}
        calls=[];response_calls=[]
        def http(endpoint,body):
            if endpoint=='responses/input_tokens':return {'input_tokens':10}
            calls.append((endpoint,copy.deepcopy(body)))
            if endpoint=='decisions':
                target_only=len(body['questions'])==2
                return {'model':'gpt-6-luna','answers':[{'type':'predicate','name':q['name'],
                    'probability':.95 if q['name']=='false_split' or (target_only and q['name']=='art_clipping') else 0.0}
                    for q in body['questions']],
                    'usage':{'input_tokens':10,'output_tokens':0,'total_tokens':10}}
            self.assertEqual(endpoint,'responses')
            identity=hashlib.sha256(b'comic-escalation-judge-v1:'+json.dumps(body,sort_keys=True).encode()).hexdigest()
            row=budget.entries[identity]
            response_calls.append({'body':copy.deepcopy(body),'request_id':identity,'reservation':row['reservation']})
            raw=copy.deepcopy(answers[len(response_calls)-1]);raw['model']=body['model']
            return raw
        self.enterContext(patch.object(client,'http',side_effect=http))
        return converter,candidate,budget,calls,response_calls

    @staticmethod
    def exhausted(limit=4096):
        return {'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'},
            'output':[{'type':'reasoning','summary':[]}],
            'usage':{'input_tokens':10,'output_tokens':limit,'total_tokens':limit+10,
                     'output_tokens_details':{'reasoning_tokens':limit}}}

    @staticmethod
    def completed(kind):
        raw=response(verdict(kind));raw['output'][0]['type']='message'
        raw['usage']={'input_tokens':10,'output_tokens':30,'total_tokens':40}
        return raw

    def test_regional_exhaustion_recovers_distinct_and_replays_cache(self):
        converter,candidate,budget,calls,responses=self.fixture('regional',[self.exhausted(),self.completed('distinct')])
        result=converter.check_splits(candidate)
        self.assertEqual(result['flags'],[])
        self.assertEqual(len(responses),2)
        first,second=responses
        self.assertEqual(first['body']['max_output_tokens'],4096)
        self.assertEqual(second['body'],{**first['body'],'max_output_tokens':8192})
        self.assertEqual([r['reservation'] for r in responses],[190960,231920])
        evidence=result['checks'][0]['final_tier_disambiguation']
        recovery=evidence['request']['output_limit_recovery']
        self.assertEqual(recovery['original_request']['request_id'],first['request_id'])
        self.assertEqual(evidence['request']['request_id'],second['request_id'])
        self.assertIsNone(evidence['request'].get('retry_of'))
        self.assertEqual((recovery['original_output_limit'],recovery['expanded_output_limit']),(4096,8192))
        original=Path(recovery['original_request']['path'])/'response.json'
        self.assertEqual(json.loads(original.read_text())['status'],'incomplete')
        self.assertEqual((len(budget.entries),budget.used()),(3,41311))
        before=budget.path.read_bytes()
        resumed=Client('synthetic-not-credential',budget,converter.root/'resumed')
        replay=Converter(resumed,converter.root);replay.bundles=converter.bundles
        with patch.object(resumed,'http',side_effect=AssertionError('cache replay attempted HTTP')):
            self.assertEqual(replay.check_splits(candidate)['flags'],[])
        self.assertEqual((resumed.cache_hits,resumed.new_calls),(3,0))
        self.assertEqual(budget.path.read_bytes(),before)
        # A recovered split warning cannot bypass downstream native crop checks.
        judged=converter.judge(None,candidate)
        self.assertEqual(judged['route'],'escalate')
        self.assertEqual(judged['target_flags'],[1,2])
        self.assertEqual(len(responses),2)
        self.assertEqual(sum(endpoint=='decisions' for endpoint,_ in calls),4)

    def test_recovered_continuous_or_uncertain_does_not_clear_warning(self):
        for kind in ('continuous','uncertain'):
            with self.subTest(kind=kind):
                converter,candidate,_,_,responses=self.fixture(kind,[self.exhausted(),self.completed(kind)])
                result=converter.check_splits(candidate)
                self.assertEqual(result['flags'],[[1,2]])
                self.assertEqual(result['checks'][0]['final_tier_disambiguation']['verdict']['classification'],kind)
                self.assertEqual(len(responses),2)

    def test_recovered_regional_uncertainty_still_requires_existing_context(self):
        for kind in ('distinct','uncertain'):
            with self.subTest(kind=kind):
                answers=[self.exhausted(),self.completed('uncertain'),self.exhausted(),self.completed(kind)]
                converter,candidate,_,_,responses=self.fixture(kind,answers,predecessor=True)
                result=converter.check_splits(candidate)
                self.assertEqual(result['flags'],[] if kind=='distinct' else [[1,2]])
                self.assertEqual([r['body']['model'] for r in responses],['gpt-6-sol']*2+['gpt-6-astra']*2)
                self.assertEqual(responses[3]['body'],{**responses[2]['body'],'max_output_tokens':8192})
                check=result['checks'][0]
                self.assertEqual(check['final_tier_disambiguation']['verdict']['classification'],'uncertain')
                self.assertEqual(check['preceding_page_disambiguation']['verdict']['classification'],kind)
                self.assertIn('output_limit_recovery',check['preceding_page_disambiguation']['request'])

    def test_second_exhaustion_blocks_without_third_continuity_request(self):
        converter,candidate,_,_,responses=self.fixture('twice',[self.exhausted(),self.exhausted(8192)])
        with self.assertRaisesRegex(RunBlocked,'incomplete source-continuity'):
            converter.check_splits(candidate)
        self.assertEqual(len(responses),2)

    def test_inventory_context_recovery_preserves_inventory_semantics(self):
        for kind in ('continuous','uncertain','distinct'):
            with self.subTest(kind=kind):
                answers=[self.exhausted(),self.completed('distinct'),self.exhausted(),self.completed(kind)]
                converter,candidate,_,_,responses=self.fixture(kind,answers)
                previous=copy.deepcopy(converter.bundles['candidate'])
                converter.history['synthetic']=[{'identity':'prior','tier':'sol-low','panels':previous}]
                converter.bundles['candidate']['panels']=[{'order':1,'box':[0,0,1000,1000]}]
                result=converter.check_inventory(candidate)
                self.assertEqual(result['flags'],[] if kind=='continuous' else [1])
                self.assertEqual(len(responses),4)
                self.assertEqual(responses[1]['body'],{**responses[0]['body'],'max_output_tokens':8192})
                self.assertEqual(responses[3]['body'],{**responses[2]['body'],'max_output_tokens':8192})
                check=result['checks'][0]
                self.assertEqual(check['source_verdict']['classification'],'distinct')
                self.assertEqual(check['context_verdict']['classification'],kind)
                self.assertIn('output_limit_recovery',check['source_request'])
                self.assertIn('output_limit_recovery',check['context_request'])


if __name__=='__main__':unittest.main()
