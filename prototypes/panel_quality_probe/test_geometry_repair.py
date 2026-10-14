import copy
import unittest
from unittest.mock import Mock

from automatic_escalation import run_page, RunBlocked
from geometry_repair import clipping_feedback, apply_expansions


def geometry():
    return {'classification':'panels','orientation':'upright','reading_direction':'ltr','panels':[
        {'order':1,'box':[0,0,400,1000],'description':'first'},
        {'order':2,'box':[500,0,1000,1000],'description':'second'}]}


def issue():return {'kind':'clipped_art','panels':[1],'evidence':'Visible artwork extends below the crop.'}


def attempt():
    return {'candidate':{'panels':geometry()},'judge':{},'verifier':{'route':'escalate','evidence':[
        {'verdict':{'route':'escalate','decision':'escalate','scene_inventory':'pass','reading_order':'pass',
                    'crop_coverage':'fail','issues':[issue()]}}]}}


class GeometryRepairTests(unittest.TestCase):
    def test_only_confirmed_localized_clipping_can_request_repair(self):
        self.assertEqual(clipping_feedback(attempt()),[issue()])
        for kind in ['missing_scene','wrong_order','uncertain']:
            a=attempt();a['verifier']['evidence'][0]['verdict']['issues'][0]['kind']=kind
            self.assertEqual(clipping_feedback(a),[])
        for flag in ['overlap_pairs','split_flags','inventory_flags','structural_error']:
            a=attempt();a['judge'][flag]=[1];self.assertEqual(clipping_feedback(a),[])
        a=attempt();a['verifier']['evidence'][0]['verdict']['decision']='uncertain'
        self.assertEqual(clipping_feedback(a),[])

    def test_semantic_failure_or_nonexistent_target_cannot_be_repaired(self):
        a=attempt();a['verifier']['evidence'][0]['verdict']['scene_inventory']='fail'
        self.assertEqual(clipping_feedback(a),[])
        a=attempt();a['verifier']['evidence'][0]['verdict']['issues'][0]['panels']=[3]
        self.assertEqual(clipping_feedback(a),[])

    def test_repair_uses_only_unresolved_target_findings_and_keeps_global_failures(self):
        a=attempt();e=a['verifier']['evidence'];e[0]['panel']=1
        e.append({'panel':1,'verdict':{'route':'keep'}})
        remaining=issue();remaining['panels']=[2]
        e.append({'panel':2,'verdict':{'route':'escalate','decision':'escalate',
            'scene_inventory':'pass','reading_order':'pass','issues':[remaining]}})
        self.assertEqual(clipping_feedback(a),[remaining])
        e.append({'scope':'complete candidate','verdict':{'route':'escalate','decision':'escalate',
            'scene_inventory':'fail','reading_order':'pass','issues':[issue()]}})
        self.assertEqual(clipping_feedback(a),[])

    def test_uncertain_only_target_does_not_prevent_repairing_concrete_clips(self):
        a=attempt();e=a['verifier']['evidence'];e[0]['panel']=1
        e.append({'panel':2,'verdict':{'route':'escalate','decision':'uncertain','scene_inventory':'pass',
            'reading_order':'pass','issues':[{'kind':'uncertain','panels':[2],'evidence':'Unclear taper at the edge.'}]}})
        self.assertEqual(clipping_feedback(a),[issue()])
        only=attempt();only['verifier']['evidence'][0]['verdict']['issues'][0]['kind']='uncertain'
        self.assertEqual(clipping_feedback(only),[])
        failed=copy.deepcopy(a);failed['verifier']['evidence'][1]['verdict']['scene_inventory']='fail'
        self.assertEqual(clipping_feedback(failed),[])

    def test_expansion_preserves_unflagged_boxes_and_original_identity(self):
        before=geometry();after=copy.deepcopy(before);after['panels'][0]['box'][2]=450
        after['panels'][0]['description']='model wording is discarded'
        value=apply_expansions(before,after,[issue()])
        self.assertEqual(before,geometry());self.assertEqual(value['panels'][0]['description'],'first')
        self.assertEqual(value['panels'][0]['box'],[0,0,450,1000])
        self.assertEqual(value['panels'][1],before['panels'][1])
        self.assertIsNone(apply_expansions(before,before,[issue()]))

    def test_expansion_cannot_shrink_reorder_or_touch_unflagged_content(self):
        mutations=[lambda g:g['panels'][0]['box'].__setitem__(0,1),
                   lambda g:g['panels'][1]['box'].__setitem__(0,490),
                   lambda g:g['panels'].reverse(),lambda g:g['panels'].pop(),
                   lambda g:g.__setitem__('reading_direction','rtl')]
        for mutate in mutations:
            proposed=geometry();mutate(proposed)
            with self.assertRaises(ValueError):apply_expansions(geometry(),proposed,[issue()])

    def run_controller(self,repaired_route='keep',failure=None):
        detect=Mock(return_value={'tier':'astra'});refine=Mock(side_effect=lambda p,r:r)
        judge=Mock(side_effect=[{'route':'escalate'},{'route':repaired_route},{'route':repaired_route}])
        verify=Mock(return_value={'route':'escalate'})
        repair=Mock(side_effect=failure,return_value={'tier':'astra','repaired':True})
        final_accept=Mock(return_value={'route':'keep'})  # Unit scope: repair routing only.
        result=run_page('source',detect,refine,judge,verify,tiers=('astra',),repair=repair,
                        final_accept=final_accept)
        if result['status']=='accepted':
            final_accept.assert_called_once_with('source',result['selected'])
        else:final_accept.assert_not_called()
        return result,detect,judge,verify,repair

    def test_repaired_candidate_is_independently_rechecked(self):
        result,detect,judge,verify,repair=self.run_controller()
        self.assertEqual(result['status'],'accepted');self.assertEqual(judge.call_count,2)
        self.assertEqual(repair.call_count,1);self.assertEqual(detect.call_count,1)
        self.assertEqual(result['attempts'][-1]['stage'],'geometry-repair')

    def test_repairs_stop_at_two_and_cannot_certify_failed_page(self):
        result,detect,judge,verify,repair=self.run_controller('escalate')
        self.assertEqual(result['status'],'whole_page_fallback');self.assertEqual(repair.call_count,2)
        self.assertEqual(verify.call_count,3)
        self.assertEqual([a['repair_round'] for a in result['attempts'][1:]],[1,2])
        result,*_=self.run_controller(failure=RunBlocked('budget exhausted'))
        self.assertEqual(result['status'],'blocked')

    def test_no_change_stops_before_another_repair_and_invalid_bound_is_rejected(self):
        repair=Mock(return_value={'tier':'astra','repair_changed':False})
        final_accept=Mock(return_value={'route':'keep'})
        result=run_page('source',lambda *a:{'tier':'astra'},lambda p,r:r,
                        lambda *a:{'route':'escalate'},lambda *a:{'route':'escalate'},
                        tiers=('astra',),repair=repair,final_accept=final_accept)
        self.assertEqual(result['status'],'whole_page_fallback');self.assertEqual(repair.call_count,1)
        final_accept.assert_not_called()
        for limit in [-1,3,True]:
            with self.assertRaises(ValueError):run_page(None,None,None,None,None,max_repairs=limit,final_accept=final_accept)

    def test_passing_detector_never_requests_repair(self):
        repair=Mock();final_accept=Mock(return_value={'route':'keep'})
        result=run_page('source',lambda *a:{'tier':'astra'},lambda p,r:r,
                        lambda *a:{'route':'keep'},Mock(),tiers=('astra',),repair=repair,
                        final_accept=final_accept)
        self.assertEqual(result['status'],'accepted');repair.assert_not_called()
        final_accept.assert_called_once_with('source',result['selected'])


if __name__=='__main__':unittest.main()


class CompletenessMergeGeometryTests(unittest.TestCase):
    """V55 converter merge: only steps nested inside a referenced step are dropped."""
    def converter_and_attempt(self, boxes):
        from unittest.mock import patch
        import tempfile,json
        from pathlib import Path
        import auto_convert
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        page = Path(tmp.name) / 'page.jpg'; page.write_bytes(b'page')
        bundle = Path(tmp.name) / 'bundle.json'; bundle.write_text(json.dumps({'k': 1}))
        panels = {'classification': 'panels', 'orientation': 'upright', 'reading_direction': 'ltr',
                  'panels': [{'order': i, 'box': b, 'description': f'v{i}'} for i, b in enumerate(boxes, 1)]}
        converter = auto_convert.Converter.__new__(auto_convert.Converter)
        converter.bundles = {'cand': {'k': 1}}
        attempt = {'candidate': {'identity': 'cand', 'bundle': str(bundle), 'panels': panels},
                   'completeness': {'route': 'escalate', 'proof': {'path': 'p', 'sha256': 's'}}}
        return converter, attempt, page, patch

    def test_nested_unreferenced_step_is_dropped_and_orders_renumbered(self):
        converter, attempt, page, patch = self.converter_and_attempt(
            [[0, 0, 400, 1000], [500, 0, 1000, 1000], [520, 50, 980, 450]])
        with patch('auto_convert.extra_feedback', return_value={'referenced': [1, 2], 'unreferenced': [3]}):
            raw = converter.completeness_merge(page, attempt)
        self.assertEqual([p['order'] for p in raw['panels']['panels']], [1, 2])
        self.assertEqual([p['box'] for p in raw['panels']['panels']], [[0, 0, 400, 1000], [500, 0, 1000, 1000]])
        self.assertEqual(raw['merged_orders'], [3]); self.assertEqual(raw['completeness_merge_of'], 'cand')

    def test_unreferenced_step_outside_every_kept_step_is_never_dropped(self):
        converter, attempt, page, patch = self.converter_and_attempt(
            [[0, 0, 400, 1000], [500, 0, 1000, 1000], [300, 0, 700, 500]])
        with patch('auto_convert.extra_feedback', return_value={'referenced': [1, 2], 'unreferenced': [3]}):
            self.assertIsNone(converter.completeness_merge(page, attempt))
        with patch('auto_convert.extra_feedback', return_value=None):
            self.assertIsNone(converter.completeness_merge(page, attempt))


class CompositeUnionMergeTests(CompletenessMergeGeometryTests):
    """V56: an overlapping composite merges into its panel by bounding-box union, never swallowing neighbors."""
    def test_partially_overlapping_composite_unions_into_its_panel(self):
        converter, attempt, page, patch = self.converter_and_attempt(
            [[17, 48, 352, 514], [17, 184, 352, 951], [348, 49, 658, 349]])
        with patch('auto_convert.extra_feedback', return_value={'referenced': [2, 3], 'unreferenced': [1]}):
            raw = converter.completeness_merge(page, attempt)
        self.assertEqual([p['box'] for p in raw['panels']['panels']], [[17, 48, 352, 951], [348, 49, 658, 349]])
        self.assertEqual([p['order'] for p in raw['panels']['panels']], [1, 2])

    def test_union_that_would_swallow_a_neighbor_is_refused(self):
        converter, attempt, page, patch = self.converter_and_attempt(
            [[0, 0, 400, 500], [0, 500, 400, 1000], [100, 300, 400, 900]])
        with patch('auto_convert.extra_feedback', return_value={'referenced': [1, 2], 'unreferenced': [3]}):
            self.assertIsNone(converter.completeness_merge(page, attempt))
