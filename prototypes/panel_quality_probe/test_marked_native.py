"""Offline routing/provenance unit checks; provider fixtures are not quality evidence."""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import auto_convert as app
from acceptance_binding import validate_page_record
from decisions_probe import experiment_questions
from marked_native import MarkedNativeConverter, HERE
from ownership_converter import OwnershipConverter


class MarkedNativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        source=self.root/'source.jpg';Image.new('RGB',(200,300),'white').save(source)
        self.bundle={'classification':'panels','reading_direction':'ltr','panels':[
            {'order':1,'box':[0,0,400,1000]},{'order':2,'box':[600,0,1000,1000]}],
            'images':[{'label':'Original complete page','path':str(source),'sha256':app.sha(source)}]}
        for target,top,bottom in ((1,0,119),(2,180,299)):
            path=self.root/f'crop-{target}.jpg'
            Image.new('RGB',(200,bottom-top+1),'white').save(path)
            self.bundle['images'].append({'label':f'Candidate crop {target} in reading order',
                'path':str(path),'sha256':app.sha(path),'points':f'0,{top} 199,{top} 199,{bottom} 0,{bottom}'})
        self.calls=[]
        calls=self.calls
        class Budget:
            cap=4_000_000
            def used(self):return 0
        class Client:
            budget=Budget()
            def request(self,endpoint,body,kind):
                calls.append((endpoint,body,kind))
                # Explicit routing-unit provider fixture: target2 flags; target1 quiet.
                text=body['input'][0]['content'][0]['text']
                return {'model':'gpt-6-luna','answers':[{'type':'predicate','name':q['name'],
                    'probability':.9 if q['name']=='art_clipping' and 'ONLY judge TARGET scene 2.' in text else 0}
                    for q in body['questions']]}, {'cached':False,'request_id':'unit-fixture'}
        self.converter=MarkedNativeConverter(Client(),self.root/'converter')

    def target(self,number):
        bundle=copy.deepcopy(self.bundle)
        bundle['images']=[i for i in bundle['images'] if i['label'] in ('Original complete page',f'Candidate crop {number} in reading order')]
        prompt=(HERE/'base-prompt.txt').read_text()+f'\nONLY judge TARGET scene {number}. The second image is its actual crop. The other geometries provide context only; do not evaluate their crops.\n'
        return bundle,prompt

    def test_actual_judge_visits_every_target_and_derives_flags(self):
        self.converter.bundles['test']=self.bundle
        candidate={'identity':'test','tier':'sol-high','source_sha256':self.bundle['images'][0]['sha256'],
                   'bundle':str(self.root/'bundle.json'),'panels':{'classification':'panels','panels':self.bundle['panels']}}
        # Split detection is outside this routing unit; its original method is
        # separately covered by the existing suite and actual control runs.
        with patch.object(self.converter,'check_splits',return_value={'flags':[],'checks':[]}):
            result=self.converter.judge(Path(self.bundle['images'][0]['path']),candidate)
        self.assertEqual(result['route'],'escalate')
        self.assertEqual(result['target_flags'],[2])
        self.assertEqual(set(result['target_probabilities']),{1,2})
        target_calls=[body for _,body,_ in self.calls if len(body['questions'])==2]
        self.assertEqual(len(target_calls),2)
        self.assertTrue(all(sum(p['type']=='input_image' for p in b['input'][0]['content'])==4 for b in target_calls))
        self.assertIs(self.converter.judgments['test'],result)

    def test_native_target_strips_hypotheses_without_mutating_bundle(self):
        bundle,prompt=self.target(1)
        bundle['_ownership_hypotheses']={'sentinel':'UNSENT-HYPOTHESIS'}
        bundle['panels'][0]['description']='UNSENT-DESCRIPTION'
        previous=copy.deepcopy(bundle)
        self.converter.decision(bundle,prompt,experiment_questions('target-v3'))
        self.assertEqual(bundle,previous)
        self.assertNotIn('UNSENT',json.dumps(self.calls[-1][1]))

    def test_global_native_and_strong_verifier_remain_inherited(self):
        bundle,prompt=self.target(1)
        with patch.object(OwnershipConverter,'decision',return_value=('pass','through')) as parent:
            questions=experiment_questions('clean-v2')
            self.assertEqual(self.converter.decision(bundle,prompt,questions),('pass','through'))
            parent.assert_called_once_with(bundle,prompt,questions)
        for name in ('judge','verify','verification','_ensure_evidence'):
            self.assertIs(getattr(MarkedNativeConverter,name),getattr(OwnershipConverter,name))

    def test_bad_target_or_prompt_blocks_before_provider(self):
        for mutation in ('missing','unknown','prompt'):
            bundle,prompt=self.target(1)
            if mutation=='missing':bundle['images']=bundle['images'][:1]
            elif mutation=='unknown':bundle['images'][1]['label']='Candidate crop 999 in reading order'
            else:prompt+='Unqualified extra hint.'
            with self.assertRaises(app.RunBlocked):self.converter.decision(bundle,prompt,experiment_questions('target-v3'))
        self.assertEqual(self.calls,[])

    def test_old_page_policy_is_rejected_before_resume(self):
        with self.assertRaisesRegex(ValueError,'Old or unbound page policy'):
            validate_page_record(None,None,{'source_page':1},{'policy':'automatic-marked-target-completeness-v44'},1,None)

    def test_actual_main_instantiates_adapter_and_binds_assets_before_analysis(self):
        source=self.root/'input';source.mkdir();Image.new('RGB',(40,60),'white').save(source/'page.jpg')
        output=self.root/'output'
        argv=['auto_convert',str(source),str(output),'--ledger',str(self.root/'ledger.jsonl'),'--execute-approved']
        observed=[]
        def blocked_fixture(page,detect,refine,judge,verify,**kwargs):
            converter=judge.__self__
            self.assertIsInstance(converter,MarkedNativeConverter)
            self.assertIs(detect.__self__,converter);self.assertIs(verify.__self__,converter)
            self.assertTrue(callable(kwargs['final_accept']))
            self.assertIs(kwargs['completeness_redetect'].__self__,converter)
            observed.append(converter)
            return {'status':'blocked','selected':None,'attempts':[],'reason':'Unit fixture stops before inference'}
        def invoke():
            with patch('sys.argv',argv),patch('sys.stdin',io.StringIO('sk-'+'offline-fixture-'*3)), \
                 patch.object(app,'run_page',side_effect=blocked_fixture), \
                 patch.object(app.Client,'http',side_effect=AssertionError('HTTP forbidden')),redirect_stdout(io.StringIO()):
                app.main()
        with self.assertRaises(SystemExit):invoke()
        self.assertEqual(len(observed),1)
        config=json.loads((output/'run.json').read_text())
        self.assertEqual(config['policy'],'automatic-marked-target-completeness-v63')
        for name in ('marked_native.py','base-prompt.txt','questions.json','context-guidance.txt'):
            self.assertEqual(config['source_sha256s']['panel_quality_probe/'+name],app.sha(HERE/name))
        config['source_sha256s']['panel_quality_probe/context-guidance.txt']='0'*64
        (output/'run.json').write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError,'run identity changed'):invoke()
        self.assertEqual(len(observed),1)


if __name__=='__main__':unittest.main()
