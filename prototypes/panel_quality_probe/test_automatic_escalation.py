import inspect
import unittest
from unittest.mock import Mock
from automatic_escalation import run_page, RunBlocked


class AutomaticEscalationTests(unittest.TestCase):
    def callbacks(self, routes, confirmations):
        self.detected=[]; self.verified=[]
        # Explicit unit-scope completeness substitute; not a quality claim.
        self.final_accept=Mock(return_value={'route':'keep'})
        def detect(page,tier): self.detected.append(tier); return {'id':tier}
        def refine(page,candidate): return {**candidate,'refined':True}
        def judge(page,candidate):
            self.assertTrue(candidate['refined'])
            return {'route':routes[candidate['id']]}
        def verify(page,candidate):
            self.verified.append(candidate['id'])
            return {'route':confirmations[candidate['id']]}
        return detect,refine,judge,verify

    def test_keep_avoids_stronger_models(self):
        result=run_page('page',*self.callbacks({'low':'keep'},{}),tiers=('low','high'),final_accept=self.final_accept)
        self.assertEqual(result['status'],'accepted')
        self.assertEqual(self.detected,['low']); self.assertEqual(self.verified,[])
        self.final_accept.assert_called_once_with('page',result['selected'])

    def test_false_alarm_verified_without_redetection(self):
        result=run_page('page',*self.callbacks({'low':'escalate'},{'low':'keep'}),tiers=('low','high'),final_accept=self.final_accept)
        self.assertEqual(result['status'],'accepted'); self.assertEqual(self.detected,['low'])
        self.assertEqual(self.verified,['low'])
        self.final_accept.assert_called_once_with('page',result['selected'])

    def test_confirmed_defect_redetects_and_rechecks(self):
        result=run_page('page',*self.callbacks({'low':'escalate','high':'keep'},
                                              {'low':'escalate'}),tiers=('low','high'),final_accept=self.final_accept)
        self.assertEqual(result['selected']['id'],'high')
        self.assertEqual(self.detected,['low','high'])
        self.assertEqual(len(result['attempts']),2)
        self.final_accept.assert_called_once_with('page',result['selected'])

    def test_exhaustion_is_explicit_whole_page_fallback(self):
        result=run_page('page',*self.callbacks({'low':'escalate','high':'escalate'},
            {'low':'escalate','high':'escalate'}),tiers=('low','high'),final_accept=self.final_accept)
        self.assertEqual(result['status'],'whole_page_fallback')
        self.assertIsNone(result['selected']); self.assertEqual(len(self.detected),2)
        self.final_accept.assert_not_called()

    def test_budget_or_account_failure_stops_resumably(self):
        callbacks=list(self.callbacks({'low':'escalate'},{}))
        def blocked(*args): raise RunBlocked('budget exhausted')
        callbacks[3]=blocked
        result=run_page('page',*callbacks,tiers=('low','high'),final_accept=self.final_accept)
        self.assertEqual(result['status'],'blocked'); self.assertEqual(self.detected,['low'])
        self.final_accept.assert_not_called()

    def test_malformed_judge_cannot_be_accepted(self):
        result=run_page('page',*self.callbacks({'low':'made-up'},{'low':'keep'}),tiers=('low','high'),final_accept=self.final_accept)
        self.assertEqual(result['status'],'blocked'); self.assertEqual(self.verified,[])
        self.final_accept.assert_not_called()


class CompletenessRedetectionTests(unittest.TestCase):
    # Controller-scope proof substitutes only. Actual bound proofs and provider
    # request construction are exercised in test_inventory_guard.
    MISSING={'route':'escalate','disposition':'missing','unresolved':[],
             'proof':{'path':'unit-scope-only','sha256':'0'*64}}

    def invoke(self,*,new_final='keep',new_quality='keep',repeated=False,rejection=None,blocked=False):
        self.refined=[];self.judged=[];self.verified=[];self.finalized=[]
        def detect(_page,tier):return {'identity':tier,'tier':tier}
        def refine(_page,candidate):self.refined.append(candidate['identity']);return {**candidate,'refined':True}
        def judge(_page,candidate):
            self.assertTrue(candidate['refined']);self.judged.append(candidate['identity']);return {'route':'escalate'}
        def verify(_page,candidate):
            self.verified.append(candidate['identity']);return {'route':new_quality if candidate.get('fresh') else 'keep'}
        def final(_page,candidate):
            self.finalized.append(candidate['identity'])
            return {'route':'keep'} if candidate.get('fresh') and new_final=='keep' else dict(rejection or self.MISSING)
        def redetect(_page,attempt):
            self.assertEqual(attempt['candidate']['identity'],'astra')
            self.assertEqual(attempt['completeness'],dict(rejection or self.MISSING))
            if blocked:raise RunBlocked('synthetic shared cap')
            return {'identity':'astra' if repeated else 'new','tier':'astra','fresh':True,
                    'completeness_redetection_of':attempt['candidate']['identity']}
        self.redetect=Mock(side_effect=redetect);self.repair=Mock(return_value=None)
        self.pixel=Mock(return_value=None)
        kwargs={'completeness_redetect':self.redetect} if 'completeness_redetect' in inspect.signature(run_page).parameters else {}
        return run_page('page',detect,refine,judge,verify,repair=self.repair,pixel_repair=self.pixel,final_accept=final,**kwargs)

    def test_missing_rejection_gets_one_new_candidate_and_all_checks(self):
        result=self.invoke()
        self.assertEqual(result['status'],'accepted')
        expected=['sol-low','sol-high','astra','new']
        self.assertEqual(self.refined,expected);self.assertEqual(self.judged,expected)
        self.assertEqual(self.verified,expected);self.assertEqual(self.finalized,expected)
        self.redetect.assert_called_once();self.pixel.assert_called_once()
        self.assertEqual(result['attempts'][-1]['stage'],'completeness-redetection')
        self.assertEqual(result['attempts'][-2]['completeness'],self.MISSING)
        self.assertNotIn('repair_of',result['selected'])

    def test_uncertainty_or_nonmissing_rejection_cannot_trigger_redetection(self):
        for rejection in ({'route':'escalate','disposition':'uncertain','unresolved':[]},
                {'route':'escalate','disposition':'missing','unresolved':['source_uncertainty']},
                {'route':'escalate','reason':'No complete source evidence'}):
            with self.subTest(rejection=rejection):
                self.assertEqual(self.invoke(rejection=rejection)['status'],'whole_page_fallback')
                self.redetect.assert_not_called()

    def test_repeated_proposal_or_new_failure_cannot_reenter_redetection(self):
        for repeated,quality in ((True,'keep'),(False,'keep'),(False,'escalate')):
            with self.subTest(repeated=repeated,quality=quality):
                result=self.invoke(new_final='escalate',new_quality=quality,repeated=repeated)
                self.assertEqual(result['status'],'whole_page_fallback');self.assertIsNone(result['selected'])
                self.assertEqual(len(result['attempts']),4);self.redetect.assert_called_once()
                self.pixel.assert_called_once();self.assertEqual(self.repair.call_count,2)
                if quality=='escalate':self.assertNotIn('completeness',result['attempts'][-1])

    def test_post_redetection_has_one_separate_repair_without_resetting_original_two(self):
        for repaired_passes in (True,False):
            with self.subTest(repaired_passes=repaired_passes):
                repairs=[]
                def detect(_page,tier):return {'identity':tier,'tier':tier}
                def judge(_page,_candidate):return {'route':'escalate'}
                def verify(_page,candidate):
                    passes=candidate['identity']=='geometry-2' or candidate['identity']=='geometry-3' and repaired_passes
                    return {'route':'keep' if passes else 'escalate'}
                def final(_page,candidate):return {'route':'keep'} if candidate['identity']=='geometry-3' else dict(self.MISSING)
                def repair(_page,attempt):
                    repairs.append(attempt['candidate']['identity'])
                    return {'identity':f'geometry-{len(repairs)}','tier':'astra','repair_of':attempt['candidate']['identity']}
                redetect=Mock(return_value={'identity':'new','tier':'astra','completeness_redetection_of':'geometry-2'})
                pixel=Mock(return_value=None)
                result=run_page('page',detect,lambda _p,c:c,judge,verify,repair=repair,pixel_repair=pixel,
                    final_accept=final,completeness_redetect=redetect)
                self.assertEqual(result['status'],'accepted' if repaired_passes else 'whole_page_fallback')
                self.assertEqual(repairs,['astra','geometry-1','new']);redetect.assert_called_once();pixel.assert_called_once()
                self.assertEqual(len(result['attempts']),7)
                tail=result['attempts'][-1]
                self.assertEqual(tail['stage'],'post-completeness-geometry-repair');self.assertEqual(tail['repair_round'],1)
                self.assertEqual(tail['completeness_redetection_candidate'],'new')
                self.assertEqual([a['repair_round'] for a in result['attempts'] if a.get('stage')=='geometry-repair'],[1,2])

    def test_redetection_budget_block_preserves_original_rejection(self):
        result=self.invoke(blocked=True)
        self.assertEqual(result['status'],'blocked');self.assertEqual(len(result['attempts']),3)
        self.assertEqual(result['attempts'][-1]['completeness'],self.MISSING)
        self.assertIn('shared cap',result['reason']);self.redetect.assert_called_once()


if __name__=='__main__': unittest.main()


class CompletenessMergeControllerTests(unittest.TestCase):
    """V55: one deterministic merge after a final bijection rejection; the merge is re-checked."""
    def run_with(self, merged_route='keep', rejection=None):
        rejection = rejection or {'route': 'escalate', 'unresolved': ['incomplete_bijection'], 'disposition': 'complete'}
        merges = []
        def detect(page, tier): return {'id': tier}
        def refine(page, raw): return {**raw, 'identity': raw.get('id', 'merged')}
        def judge(page, candidate): return {'route': 'keep'}
        def verify(page, candidate): return {'route': 'keep'}
        def final_accept(page, candidate):
            return {'route': merged_route} if candidate.get('stage_merge') else dict(rejection)
        def merge(page, attempt):
            merges.append(attempt['candidate']['identity'])
            return {'tier': 'astra', 'stage_merge': True, 'id': 'merged', 'completeness_merge_of': attempt['candidate']['identity']}
        result = run_page('page', detect, refine, judge, verify, tiers=('low', 'astra'),
                          final_accept=final_accept, completeness_merge=merge)
        return result, merges

    def test_bijection_rejection_merges_latest_candidate_once_and_rechecks(self):
        result, merges = self.run_with()
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(merges, ['astra'])
        self.assertEqual(result['attempts'][-1]['stage'], 'completeness-merge')
        self.assertEqual(result['selected']['identity'], 'merged')

    def test_failed_merge_falls_back_without_looping(self):
        result, merges = self.run_with(merged_route='escalate')
        self.assertEqual(result['status'], 'whole_page_fallback')
        self.assertEqual(merges, ['astra'])

    def test_other_rejections_never_merge(self):
        result, merges = self.run_with(rejection={'route': 'escalate', 'unresolved': ['astra_source_uncertainty']})
        self.assertEqual(result['status'], 'whole_page_fallback')
        self.assertEqual(merges, [])


class PageSpendLimitControllerTests(unittest.TestCase):
    def test_page_limit_becomes_whole_page_fallback_not_blocked_run(self):
        from automatic_escalation import PageBudgetExhausted
        def detect(page, tier):
            if tier == 'astra': raise PageBudgetExhausted('page spend limit reached: 300000 of 250000 micro-USD')
            return {'id': tier}
        result = run_page('page', detect, lambda p, c: {**c, 'identity': c['id']}, lambda p, c: {'route': 'escalate'},
                          lambda p, c: {'route': 'escalate'}, tiers=('low', 'astra'), final_accept=lambda p, c: {'route': 'keep'})
        self.assertEqual(result['status'], 'whole_page_fallback')
        self.assertIn('page spend limit reached', result['reason'])
        self.assertEqual([a['tier'] for a in result['attempts']], ['low', 'astra'])


class AstraTierBudgetTests(unittest.TestCase):
    def test_astra_tier_not_started_without_minimum_page_budget(self):
        from types import SimpleNamespace
        import auto_convert
        from automatic_escalation import PageBudgetExhausted
        converter = auto_convert.Converter.__new__(auto_convert.Converter)
        converter.client = SimpleNamespace(page_remaining=lambda: auto_convert.ASTRA_TIER_MIN - 1)
        with self.assertRaisesRegex(PageBudgetExhausted, 'too low to start the Astra tier'):
            converter.detect('page', 'astra')
