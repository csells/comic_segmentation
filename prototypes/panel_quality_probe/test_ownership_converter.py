"""Offline controller invariants; run only in disposable staging."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image, ImageDraw

from auto_convert import Converter
from automatic_escalation import RunBlocked, run_page
from geometry_repair import request_body as repair_request_body
from ownership_converter import AUXILIARY, OwnershipConverter
from scene_evidence import request_fingerprint


class OwnershipConverterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        source = self.root / 'source.png'
        Image.new('RGB', (1000, 1000), 'white').save(source)
        self.source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        self.source = {'label': 'Original complete page', 'path': str(source), 'sha256': self.source_sha}
        self.audit_uncertain = False
        self.exhausted_limits = set()
        self.occlusion_probability = .01
        self.client = SimpleNamespace(request=Mock(side_effect=self.audit))
        self.converter = OwnershipConverter(self.client, self.root)
        self.candidate = self.add_candidate('candidate')

    def tearDown(self):
        self.temp.cleanup()

    def audit(self, endpoint, body, kind):
        if endpoint == 'decisions':
            from crossing_art import occlusion_request_body
            self.assertEqual(kind, 'native')
            self.assertEqual(body, occlusion_request_body(self.source['path']))
            return {'model': 'gpt-6-luna', 'answers': [{'type': 'predicate', 'name': 'source_occlusion',
                    'probability': self.occlusion_probability}]}, {'request_id': 'source-risk'}
        self.assertEqual((endpoint, kind, body['model']), ('responses', 'verifier', 'gpt-6-astra'))
        fingerprint = hashlib.sha256(b'comic-escalation-judge-v1:' + json.dumps(body, sort_keys=True).encode()).hexdigest()
        if body['max_output_tokens'] in self.exhausted_limits:
            return ({'status': 'incomplete', 'model': body['model'], 'incomplete_details': {'reason': 'max_output_tokens'},
                     'output': [{'type': 'reasoning', 'summary': []}]},
                    {'request_id': fingerprint, 'cached': False, 'retry_of': None})
        supplied = json.loads(body['input'][0]['content'][0]['text'].rsplit('\n', 1)[1])
        result = {'inventory_status': 'complete', 'issues': [], 'scenes': [
            {'order': panel['order'], 'identity': 'Source view', 'owned_content': ['subject and setting'],
             'ownership_cues': ['Continuous ground links the subject to its setting.'],
             'distinguish_from_neighbors': [], 'uncertain': self.audit_uncertain}
            for panel in supplied['panels']]}
        raw = {'status': 'completed', 'model': body['model'], 'output': [{'type': 'message',
               'content': [{'type': 'output_text', 'text': json.dumps(result)}]}]}
        fingerprint = hashlib.sha256(b'comic-escalation-judge-v1:' + json.dumps(body, sort_keys=True).encode()).hexdigest()
        return raw, {'request_id': fingerprint, 'cached': False, 'retry_of': None}

    def add_candidate(self, identity, *, parent=None, tier='sol-high', boxes=None, description='View'):
        boxes = boxes or [[100, 100, 650, 900], [500, 100, 900, 900]]
        panels = [{'order': i, 'box': box, 'description': f'{description} {i}'} for i, box in enumerate(boxes, 1)]
        value = {'classification': 'panels', 'orientation': 'upright', 'reading_direction': 'ltr', 'panels': panels}
        bundle = {key: value[key] for key in ('classification', 'reading_direction')}
        bundle['panels'] = [{key: panel[key] for key in ('order', 'box')} for panel in panels]
        bundle['images'] = [self.source]
        directory = self.root / identity
        directory.mkdir(exist_ok=True)
        with Image.open(self.source['path']) as source:
            for panel in panels:
                top, left, bottom, right = panel['box']
                path = directory / f"crop-{panel['order']}.png"
                source.crop((left, top, right, bottom)).save(path)
                bundle['images'].append({
                    'label': f"Candidate crop {panel['order']} in reading order",
                    'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'points': f'{left},{top} {right-1},{top} {right-1},{bottom-1} {left},{bottom-1}'})
        candidate = {'identity': identity, 'tier': tier, 'panels': value, 'source_sha256': self.source_sha,
                     'bundle': str(self.root / identity / 'bundle.json')}
        if parent is not None:
            candidate['repair_of'] = parent
        self.converter.bundles[identity] = bundle
        self.converter.history.setdefault(self.source_sha, []).append(candidate)
        return candidate

    @staticmethod
    def native_keep():
        return {'route': 'keep', 'semantic_flags': [], 'global_crop_flags': [], 'target_flags': [],
                'crossing_art': {'targets': []}, 'split_checks': [], 'inventory_checks': []}

    def prime(self, candidate=None, verdict=None):
        candidate = candidate or self.candidate
        def native(_page, current):
            value = copy.deepcopy(verdict or self.native_keep())
            self.converter.judgments[current['identity']] = value
            return value
        with patch.object(Converter, 'judge', side_effect=native):
            return self.converter.judge(None, candidate)

    def test_normal_path_retains_legacy_requests(self):
        from crossing_art import occlusion_request_body
        normal = self.add_candidate('normal', boxes=[[100, 100, 400, 900], [500, 100, 900, 900]])
        self.assertEqual(self.prime(normal)['route'], 'keep')
        with patch.object(Converter, 'verify', return_value={'route': 'keep'}) as verify:
            self.assertEqual(self.converter.verify(None, normal)['route'], 'keep')
            verify.assert_called_once()
        self.client.request.assert_called_once_with('decisions', occlusion_request_body(self.source['path']), 'native')

    def test_native_keep_on_risky_layout_requires_confirmation(self):
        verdict = self.prime()
        self.assertEqual(verdict['route'], 'escalate')
        self.assertTrue(verdict['ownership_confirmation_required'])
        self.assertNotIn('description', self.converter.bundles['candidate']['panels'][0])
        self.assertIn('_ownership_hypotheses', self.converter.bundles['candidate'])

    def test_source_occlusion_closes_quiet_nonoverlap_acceptance_without_accepting(self):
        for probability in (.2, .49, .99):
            with self.subTest(probability=probability):
                self.occlusion_probability = probability
                if hasattr(self.converter, 'source_occlusion'):
                    self.converter.source_occlusion.clear()
                candidate = self.add_candidate('quiet-' + str(probability), tier='astra', boxes=[
                    [0, 0, 400, 400], [0, 500, 400, 900]])
                verdict = self.prime(candidate)
                self.assertEqual(verdict['route'], 'escalate')
                self.assertEqual(verdict['ownership_required_targets'], [1, 2])
                self.assertEqual(verdict['source_occlusion_risk']['probability'], probability)
                with patch('ownership_converter.with_source_detail', side_effect=lambda bundle, *_a, **_k: bundle), \
                        patch.object(self.converter, 'verification', side_effect=[
                            ({'route': 'escalate'}, {}), ({'route': 'keep'}, {}), ({'route': 'keep'}, {})]) as verify:
                    result = self.converter.verify(None, candidate)
                self.assertEqual(result['route'], 'escalate')
                self.assertEqual(verify.call_count, 3)
                self.assertEqual([item['panel'] for item in result['evidence'] if 'panel' in item], [1, 2])

    def test_source_occlusion_also_checks_ordinary_verifier_clearance(self):
        self.occlusion_probability = .7
        candidate = self.add_candidate('ordinary-clearance', tier='astra', boxes=[
            [0, 0, 400, 400], [0, 500, 400, 900]])
        native = self.native_keep(); native.update(route='escalate', semantic_flags=['order_defect'])
        self.assertEqual(self.prime(candidate, native)['route'], 'escalate')
        self.client.request.assert_not_called()
        with patch.object(Converter, 'verify', return_value={'route': 'keep', 'evidence': [
                {'scope': 'ordinary confirmation', 'verdict': {'route': 'keep'}, 'request': {}}]}) as ordinary, \
                patch('ownership_converter.with_source_detail', side_effect=lambda bundle, *_a, **_k: bundle), \
                patch.object(self.converter, 'verification', side_effect=[
                    ({'route': 'keep'}, {}), ({'route': 'escalate'}, {}), ({'route': 'keep'}, {})]) as verify:
            result = self.converter.verify(None, candidate)
        ordinary.assert_called_once()
        self.assertEqual(result['route'], 'escalate')
        self.assertEqual(verify.call_count, 3)
        self.assertEqual(result['evidence'][0]['scope'], 'ordinary confirmation')
        self.assertEqual(self.converter.judgments[candidate['identity']]['ownership_required_targets'], [1, 2])

    def test_source_risk_survives_new_detector_inventory_and_required_only_descendants(self):
        self.occlusion_probability = .8
        parent = self.add_candidate('source-parent', tier='sol-low', boxes=[
            [0, 0, 300, 300], [0, 500, 300, 800]])
        self.assertEqual(self.prime(parent)['ownership_required_targets'], [1, 2])
        later = self.add_candidate('new-detector', tier='sol-high', boxes=[
            [0, 0, 300, 300], [0, 500, 300, 800], [600, 0, 900, 900]])
        self.assertEqual(self.prime(later)['ownership_required_targets'], [1, 2, 3])
        self.assertEqual(sum(call.args[0] == 'decisions' for call in self.client.request.call_args_list), 1)
        # Even without the in-memory source cache, a saved required-only parent
        # and a quiet native recheck must retain its child's ownership duties.
        self.converter.source_occlusion.clear()
        child = self.add_candidate('required-only-child', parent=parent['identity'], tier='sol-high', boxes=[
            [0, 0, 320, 320], [0, 480, 320, 820]])
        self.assertEqual(self.converter._risk_orders(child), {1, 2})
        self.assertEqual(self.prime(child)['ownership_required_targets'], [1, 2])
        with patch('ownership_converter.with_source_detail', side_effect=lambda bundle, *_a, **_k: bundle), \
                patch.object(self.converter, 'verification', side_effect=[
                    ({'route': 'keep'}, {}), ({'route': 'keep'}, {}), ({'route': 'escalate'}, {})]) as verify:
            result = self.converter.verify(None, child)
        self.assertEqual(result['route'], 'escalate')
        self.assertEqual(verify.call_count, 3)
        self.assertEqual(sum(call.args[0] == 'decisions' for call in self.client.request.call_args_list), 1)

    def test_source_screen_invalid_blocks_and_rejected_or_whole_pages_skip(self):
        candidate = self.add_candidate('invalid-screen', boxes=[
            [0, 0, 300, 300], [0, 500, 300, 800]])
        self.occlusion_probability = float('nan')
        with self.assertRaisesRegex(RunBlocked, 'Source ownership screen invalid'):
            self.prime(candidate)
        self.assertNotIn(self.source_sha, self.converter.source_occlusion)
        self.client.request.reset_mock()
        rejected = self.native_keep(); rejected.update(route='escalate', target_flags=[1])
        self.prime(candidate, rejected)
        with patch.object(Converter, 'verify', return_value={'route': 'escalate', 'evidence': []}):
            self.assertEqual(self.converter.verify(None, candidate)['route'], 'escalate')
        self.client.request.assert_not_called()
        whole = self.add_candidate('whole', boxes=[[0, 0, 1000, 1000]])
        whole['panels']['classification'] = 'whole_page'
        self.converter.bundles[whole['identity']]['classification'] = 'whole_page'
        self.assertEqual(self.prime(whole)['route'], 'keep')
        self.client.request.assert_not_called()

    def draw_source(self, bounds, color='black'):
        with Image.open(self.source['path']) as original:
            image = original.convert('RGB')
        ImageDraw.Draw(image).rectangle(bounds, fill=color)
        image.save(self.source['path'])
        self.source_sha = hashlib.sha256(Path(self.source['path']).read_bytes()).hexdigest()
        self.source['sha256'] = self.source_sha

    def test_uncovered_art_forces_all_target_checks_and_global_failure_binds(self):
        # A thin disconnected monochrome strip at the page edge is substantive.
        # No overlap or positive model risk answer is needed to find the gap.
        self.draw_source((500, 0, 999, 1), color=(100, 100, 100))
        self.occlusion_probability = 0.0
        candidate = self.add_candidate('uncovered', tier='astra', boxes=[
            [100, 0, 500, 400], [100, 600, 500, 1000]])
        geometry = copy.deepcopy(candidate['panels'])
        images = copy.deepcopy(self.converter.bundles[candidate['identity']]['images'])
        verdict = self.prime(candidate)
        self.assertEqual(verdict['route'], 'escalate')
        self.assertEqual(verdict['ownership_required_targets'], [1, 2])
        self.assertTrue(verdict['uncovered_content_risk']['requires_ownership'])
        self.assertEqual(verdict['uncovered_content_risk']['components'][0]['pixels'], 1000)
        self.assertFalse(any(call.args[0] == 'decisions' for call in self.client.request.call_args_list))
        with patch.object(self.converter, 'verification', side_effect=[
                ({'route': 'escalate'}, {}), ({'route': 'keep'}, {}), ({'route': 'keep'}, {})]) as verify:
            result = self.converter.verify(None, candidate)
        self.assertEqual(result['route'], 'escalate')
        self.assertEqual(verify.call_count, 3)
        self.assertEqual([item['panel'] for item in result['evidence'] if 'panel' in item], [1, 2])
        for call in verify.call_args_list[1:]:
            self.assertEqual(len(call.args[0]['images']), 4)
            self.assertIn('exact actual crop extent', call.args[0]['images'][3]['label'])
        self.assertEqual(candidate['panels'], geometry)
        self.assertEqual(self.converter.bundles[candidate['identity']]['images'], images)
        self.assertNotIn('uncovered_content_risk', self.converter.bundles[candidate['identity']])

    def test_uncovered_risk_recomputes_after_negative_and_persists_across_tiers_and_repair(self):
        self.draw_source((500, 0, 999, 1))
        self.occlusion_probability = 0.0
        covered = self.add_candidate('covered-first', tier='sol-low', boxes=[
            [0, 0, 10, 1000], [100, 0, 500, 1000]])
        self.assertEqual(self.prime(covered)['route'], 'keep')
        missing = self.add_candidate('missing-later', tier='sol-high', boxes=[
            [100, 0, 400, 400], [500, 600, 900, 1000]])
        verdict = self.prime(missing)
        self.assertEqual(verdict['route'], 'escalate')
        self.assertEqual(verdict['ownership_required_targets'], [1, 2])
        self.assertTrue(verdict['uncovered_content_risk']['requires_ownership'])
        repaired = self.add_candidate('covered-repair', parent=missing['identity'], tier='astra', boxes=[
            [0, 0, 400, 1000], [500, 600, 900, 1000]])
        fresh = self.add_candidate('covered-new-inventory', tier='astra', boxes=[
            [0, 0, 10, 1000], [100, 0, 400, 400], [500, 600, 900, 1000]])
        for candidate, orders in ((repaired, [1, 2]), (fresh, [1, 2, 3])):
            with self.subTest(candidate=candidate['identity']):
                result = self.prime(candidate)
                self.assertEqual(result['route'], 'escalate')
                self.assertFalse(result['uncovered_content_risk']['requires_ownership'])
                self.assertTrue(result['uncovered_content_risk']['retained_source_risk'])
                self.assertEqual(result['ownership_required_targets'], orders)
        self.assertEqual(sum(call.args[0] == 'decisions' for call in self.client.request.call_args_list), 1)

    def test_saved_inclusive_crop_edge_counts_as_covered(self):
        # Excluding the saved bottom/right pixel would leave >500 pixels.
        self.draw_source((0, 999, 999, 999))
        self.draw_source((999, 0, 999, 999))
        candidate = self.add_candidate('inclusive-edges', tier='astra', boxes=[
            [0, 0, 1000, 1000]])
        verdict = self.prime(candidate)
        self.assertEqual(verdict['route'], 'keep')
        self.assertFalse(verdict['uncovered_content_risk']['requires_ownership'])
        self.assertEqual(verdict['uncovered_content_risk']['uncovered_nonpaper_pixels'], 0)

    def test_actual_repair_request_preserves_plain_bytes_and_uses_validated_ownership(self):
        bundle = self.converter.bundles[self.candidate['identity']]
        original = copy.deepcopy(bundle)
        issues = [{'kind': 'clipped_art', 'panels': [1],
                   'evidence': 'Visible scene content continues beyond the crop.'}]
        attempt = {'candidate': self.candidate, 'judge': {}, 'verifier': {
            'route': 'escalate', 'evidence': [{'verdict': {
                'route': 'escalate', 'decision': 'escalate', 'scene_inventory': 'pass',
                'reading_order': 'pass', 'crop_coverage': 'fail', 'issues': issues}}]}}
        baseline = repair_request_body(bundle, issues)
        source = Path(self.source['path'])

        def capture(converter):
            with patch.object(converter.client, 'request', side_effect=RunBlocked('Captured repair request')) as request:
                with self.assertRaisesRegex(RunBlocked, 'Captured repair request'):
                    converter.repair(source, attempt)
            request.assert_called_once()
            endpoint, body, kind = request.call_args.args
            self.assertEqual((endpoint, kind), ('responses', 'detector'))
            return body

        ordinary = Converter(self.client, self.root)
        ordinary.bundles[self.candidate['identity']] = copy.deepcopy(bundle)
        for converter in (ordinary, self.converter):
            self.assertEqual(json.dumps(capture(converter), sort_keys=True).encode(),
                             json.dumps(baseline, sort_keys=True).encode())

        # The real source-audit validation path supplies context; the test does
        # not inject descriptions or proposed repair geometry into the bundle.
        self.assertEqual(self.converter._ensure_evidence(self.candidate)['route'], 'keep')
        validated = copy.deepcopy(bundle)
        expected = copy.deepcopy(baseline)
        expected['input'][0]['content'][0]['text'] += (
            AUXILIARY + '\n' + json.dumps(bundle['_ownership_hypotheses'], sort_keys=True))
        self.assertEqual(capture(self.converter), expected)
        self.assertEqual(bundle, validated)
        self.assertEqual({key: value for key, value in bundle.items()
                          if key != '_ownership_hypotheses'}, original)

    def test_uncertain_source_blocks_both_acceptance_paths(self):
        self.audit_uncertain = True
        with patch.object(Converter, 'judge') as judge:
            self.assertEqual(self.converter.judge(None, self.candidate)['route'], 'escalate')
            judge.assert_not_called()
        with patch.object(self.converter, 'verification') as verify:
            self.assertEqual(self.converter.verify(None, self.candidate)['route'], 'escalate')
            verify.assert_not_called()
        self.assertEqual(self.client.request.call_count, 1)

    def test_monotonic_descendant_reuses_audit_but_shrink_fails(self):
        self.assertEqual(self.converter._ensure_evidence(self.candidate)['route'], 'keep')
        expanded = self.add_candidate('expanded', parent='candidate', boxes=[[90, 90, 660, 910], [490, 90, 910, 910]])
        self.assertEqual(self.converter._ensure_evidence(expanded)['route'], 'keep')
        shrunk = self.add_candidate('shrunk', parent='candidate', boxes=[[110, 100, 650, 900], [500, 100, 900, 900]])
        self.assertEqual(self.converter._ensure_evidence(shrunk)['route'], 'escalate')
        # Still encloses the initial proposal but illegally shrinks its parent.
        later_shrink = self.add_candidate('later-shrink', parent='expanded',
                                         boxes=[[95, 95, 655, 905], [495, 95, 905, 905]])
        self.assertEqual(self.converter._ensure_evidence(later_shrink)['route'], 'escalate')
        self.assertEqual(self.client.request.call_count, 1)

    def test_repair_below_overlap_threshold_still_requires_marked_checks(self):
        parent = self.add_candidate('threshold-parent', tier='astra',
                                    boxes=[[100, 100, 300, 300], [280, 100, 480, 300]])
        self.prime(parent)
        child = self.add_candidate('threshold-child', parent=parent['identity'], tier='astra',
                                   boxes=[[80, 100, 300, 300], [280, 100, 500, 300]])
        # Both crops expand away from their shared edge: overlap drops from 10%
        # to 9.09%, but the same source ownership obligations remain.
        self.assertEqual(self.converter._risk_orders(child), {1, 2})
        verdict = self.prime(child)
        self.assertEqual(verdict['route'], 'escalate')
        self.assertEqual(verdict['ownership_required_targets'], [1, 2])
        self.assertEqual(self.client.request.call_count, 1)
        with patch('ownership_converter.with_source_detail', side_effect=lambda bundle, *_args, **_kwargs: bundle), \
                patch.object(self.converter, 'verification', side_effect=[({'route': route}, {}) for route in
                                                                         ('keep', 'escalate', 'keep')]):
            result = self.converter.verify(None, child)
        self.assertEqual(result['route'], 'escalate')
        self.assertEqual([entry['panel'] for entry in result['evidence'] if 'panel' in entry], [1, 2])

    def test_controller_cannot_accept_diluted_repair_with_failed_marked_target(self):
        parent = self.add_candidate('controller-parent', tier='astra',
                                    boxes=[[100, 100, 300, 300], [280, 100, 480, 300]])
        child = self.add_candidate('controller-child', parent=parent['identity'], tier='astra',
                                   boxes=[[80, 100, 300, 300], [280, 100, 500, 300]])
        final_accept=Mock(side_effect=AssertionError('Failed marked target must precede final gate'))
        with patch.object(Converter, 'judge', side_effect=lambda *_args: self.native_keep()), \
                patch('ownership_converter.with_source_detail', side_effect=lambda bundle, *_args, **_kwargs: bundle), \
                patch.object(self.converter, 'verification', side_effect=[({'route': route}, {}) for route in
                                                                         ('keep', 'escalate', 'keep') * 2]) as verify:
            result = run_page(None, lambda *_args: parent, lambda _page, candidate: candidate,
                              self.converter.judge, self.converter.verify, tiers=('astra',),
                              repair=lambda *_args: child, max_repairs=1,final_accept=final_accept)
        self.assertEqual(result['status'], 'whole_page_fallback')
        self.assertIsNone(result['selected'])
        self.assertEqual(verify.call_count, 6)
        final_accept.assert_not_called()
        self.assertEqual(self.client.request.call_count, 1)
        self.assertEqual(result['attempts'][-1]['stage'], 'geometry-repair')

    def test_later_descendant_retains_risk_and_fresh_detector_does_not(self):
        parent = self.add_candidate('lineage-root', tier='astra',
                                    boxes=[[100, 100, 300, 300], [280, 100, 480, 300]])
        self.prime(parent)
        child = self.add_candidate('lineage-child', parent=parent['identity'], tier='astra',
                                   boxes=[[80, 100, 300, 300], [280, 100, 500, 300]])
        self.prime(child)
        later = self.add_candidate('lineage-later', parent=child['identity'], tier='astra',
                                   boxes=[[60, 100, 300, 300], [280, 100, 520, 300]])
        self.assertEqual(self.converter._risk_orders(later), {1, 2})
        self.assertEqual(self.prime(later)['route'], 'escalate')
        fresh = self.add_candidate('fresh-detector', tier='astra',
                                   boxes=[[60, 100, 300, 300], [280, 100, 520, 300]])
        self.assertEqual(self.converter._risk_orders(fresh), set())
        self.assertEqual(self.prime(fresh)['route'], 'keep')
        self.assertEqual(self.client.request.call_count, 2)
        self.assertEqual(sum(call.args[0] == 'decisions' for call in self.client.request.call_args_list), 1)

    def test_inherited_risk_cannot_clear_source_or_inventory_changes(self):
        parent = self.add_candidate('binding-parent', tier='astra',
                                    boxes=[[100, 100, 300, 300], [280, 100, 480, 300]])
        self.prime(parent)
        for key in ('source', 'classification', 'direction', 'inventory', 'order', 'shrink'):
            with self.subTest(change=key):
                child = self.add_candidate('binding-' + key, parent=parent['identity'], tier='astra',
                                           boxes=[[80, 100, 300, 300], [280, 100, 500, 300]])
                if key == 'source': child['source_sha256'] = '0' * 64
                elif key == 'classification': child['panels']['classification'] = 'whole_page'
                elif key == 'direction': child['panels']['reading_direction'] = 'rtl'
                elif key == 'inventory': child['panels']['panels'].pop()
                elif key == 'order': child['panels']['panels'].reverse()
                else: child['panels']['panels'][0]['box'][0] = 101
                if key == 'source':
                    with self.assertRaisesRegex(RunBlocked, 'Uncovered-content source changed'):
                        self.prime(child)
                    with self.assertRaisesRegex(RunBlocked, 'Uncovered-content source changed'):
                        self.converter.verify(None, child)
                    continue
                self.assertEqual(self.prime(child)['route'], 'escalate')
                with patch.object(self.converter, 'verification') as verify:
                    self.assertEqual(self.converter.verify(None, child)['route'], 'escalate')
                    verify.assert_not_called()
        self.assertEqual(self.client.request.call_count, 1)

    def test_same_identity_noop_repair_resolves_earlier_parent(self):
        self.prime()
        child = copy.deepcopy(self.candidate)
        child['repair_of'] = self.candidate['identity']
        self.converter.history[self.source_sha].append(child)
        self.assertEqual(self.converter._risk_orders(child), {1, 2})
        self.assertEqual(self.prime(child)['route'], 'escalate')
        self.assertEqual(self.client.request.call_count, 1)

    def test_same_identity_quiet_recheck_retains_earlier_native_target(self):
        parent = self.add_candidate('same-identity', tier='astra', boxes=[
            [100, 100, 300, 300], [280, 100, 480, 300], [600, 600, 800, 800]])
        verdict = self.native_keep(); verdict['target_flags'] = [3]
        self.prime(parent, verdict)
        child = copy.deepcopy(parent); child['repair_of'] = parent['identity']
        self.converter.history[self.source_sha].append(child)
        # Mimic the real base judge overwriting its identity-keyed verdict.
        def quiet(*_args):
            value = self.native_keep()
            self.converter.judgments[child['identity']] = value
            return value
        with patch.object(Converter, 'judge', side_effect=quiet):
            self.assertEqual(self.converter.judge(None, child)['ownership_required_targets'], [1, 2, 3])
        self.assertEqual(self.converter._risk_orders(child), {1, 2, 3})
        self.assertEqual(self.client.request.call_count, 1)

    def test_ordinary_repair_issue_alone_does_not_enable_ownership(self):
        parent = self.add_candidate('ordinary-parent', boxes=[
            [100, 100, 200, 200], [600, 600, 800, 800]])
        child = self.add_candidate('ordinary-child', parent=parent['identity'], boxes=[
            [80, 100, 200, 200], [600, 600, 800, 800]])
        child['repair_issues'] = [{'kind': 'clipped_art', 'panels': [1], 'evidence': 'Top clipped.'}]
        self.assertEqual(self.converter._risk_orders(child), set())
        self.assertEqual(self.prime(child)['route'], 'keep')
        self.assertEqual(self.client.request.call_count, 1)
        self.assertEqual(self.client.request.call_args.args[0], 'decisions')

    def test_missing_and_cyclic_lineage_block_before_native_acceptance(self):
        orphan = self.add_candidate('orphan', parent='absent',
                                    boxes=[[100, 100, 200, 200], [500, 500, 600, 600]])
        with self.assertRaisesRegex(RunBlocked, 'no frozen proposal ancestor'):
            self.prime(orphan)
        cycle = self.add_candidate('cycle', parent='cycle')
        with self.assertRaisesRegex(RunBlocked, 'Cyclic repair ownership lineage'):
            self.prime(cycle)
        self.client.request.assert_not_called()

    def test_native_and_repair_targets_remain_required_after_quiet_recheck(self):
        for reason in ('native', 'global-repair'):
            with self.subTest(reason=reason):
                parent = self.add_candidate('obligation-parent-' + reason, tier='astra', boxes=[
                    [100, 100, 300, 300], [280, 100, 480, 300], [600, 600, 800, 800]])
                verdict = self.native_keep()
                if reason == 'native': verdict['target_flags'] = [3]
                self.prime(parent, verdict)
                child = self.add_candidate('obligation-child-' + reason, parent=parent['identity'], tier='astra', boxes=[
                    [80, 100, 300, 300], [280, 100, 500, 300], [580, 600, 800, 800]])
                if reason == 'global-repair':
                    child['repair_issues'] = [{'kind': 'clipped_art', 'panels': [3], 'evidence': 'Target top clipped.'}]
                self.assertEqual(self.prime(child)['ownership_required_targets'], [1, 2, 3])
                with patch('ownership_converter.with_source_detail', side_effect=lambda bundle, *_args, **_kwargs: bundle), \
                        patch.object(self.converter, 'verification', side_effect=[({'route': route}, {}) for route in
                                                                                 ('keep', 'keep', 'keep', 'escalate')]):
                    result = self.converter.verify(None, child)
                self.assertEqual(result['route'], 'escalate')
                self.assertEqual([entry['panel'] for entry in result['evidence'] if 'panel' in entry], [1, 2, 3])

    def test_new_detector_inventory_receives_separate_audit(self):
        self.converter._ensure_evidence(self.candidate)
        other = self.add_candidate('other', tier='astra', description='Different detector locator')
        self.converter._ensure_evidence(other)
        self.assertEqual(self.client.request.call_count, 2)
        self.assertNotEqual(self.converter.scene_evidence['candidate']['proposal_sha256'],
                            self.converter.scene_evidence['other']['proposal_sha256'])

    def test_new_risk_can_audit_its_saved_ordinary_ancestor(self):
        normal = self.add_candidate('normal', boxes=[[100, 100, 400, 900], [500, 100, 900, 900]])
        repaired = self.add_candidate('new-risk', parent=normal['identity'])
        self.assertEqual(self.converter._ensure_evidence(repaired)['route'], 'keep')
        self.assertEqual(self.client.request.call_count, 1)
        self.assertEqual(self.converter.scene_links['new-risk'], self.converter.scene_evidence['normal']['proposal_sha256'])

    def test_every_overlap_target_checked_even_when_native_is_quiet(self):
        self.prime()
        with patch('ownership_converter.with_source_detail', side_effect=lambda bundle, *_args, **_kwargs: bundle), \
                patch.object(self.converter, 'verification', return_value=({'route': 'keep'}, {})) as verify:
            result = self.converter.verify(None, self.candidate)
        self.assertEqual(result['route'], 'keep')
        self.assertEqual([entry['panel'] for entry in result['evidence'] if 'panel' in entry], [1, 2])
        self.assertEqual(verify.call_count, 3)
        self.assertTrue(all(call.kwargs['model'] == 'gpt-6-sol' for call in verify.call_args_list))

    def test_global_failure_cannot_be_erased_by_good_target_checks(self):
        final = self.add_candidate('final', tier='astra')
        self.prime(final)
        with patch('ownership_converter.with_source_detail', side_effect=lambda bundle, *_args, **_kwargs: bundle), \
                patch.object(self.converter, 'verification', side_effect=[({'route': route}, {}) for route in
                                                                         ('escalate', 'keep', 'keep')]) as verify:
            result = self.converter.verify(None, final)
        self.assertEqual(result['route'], 'escalate')
        self.assertEqual(verify.call_count, 3)

    def repaired_adjudication_candidate(self):
        suffix = str(len(self.converter.history[self.source_sha]))
        parent = self.add_candidate('adjudication-parent-' + suffix, tier='astra')
        self.prime(parent)
        child = self.add_candidate('adjudication-child-' + suffix, parent=parent['identity'], tier='astra')
        self.prime(child)
        return child

    @staticmethod
    def clipping_verdict(target=1):
        return {'route': 'escalate', 'decision': 'escalate', 'scene_inventory': 'pass',
                'reading_order': 'pass', 'crop_coverage': 'fail', 'issues': [
                    {'kind': 'clipped_art', 'panels': [target], 'evidence': 'A scene edge appears clipped.'}]}

    def adjudication_detail(self, bundle, target, directory, *, mark_boundary):
        self.assertTrue(mark_boundary)
        crop = next(image for image in bundle['images']
                    if image['label'] == f'Candidate crop {target} in reading order')
        return {**bundle, 'images': [bundle['images'][0], crop,
            {**self.source, 'label': f'Clean source context for {target}'},
            {**self.source, 'label': f'Marked source context for {target}'}]}

    def test_crossing_target_uses_astra_and_repair_receives_its_rejection(self):
        candidate = self.add_candidate('crossing-rejection', tier='astra')
        native = self.native_keep()
        native.update(route='escalate', target_flags=[1], crossing_art={'targets': [1]})
        judge = self.prime(candidate, native)
        original = copy.deepcopy(candidate['panels'])
        failed = self.clipping_verdict(1)
        failed['issues'][0]['evidence'] = 'The source-drawn tapered background continues past the actual crop.'

        def provider(bundle, prompt, effort, model):
            local = len(bundle['images']) == 4
            target = local and bundle['images'][1]['label'] == 'Candidate crop 1 in reading order'
            answer = failed if model == 'gpt-6-astra' and target else {'route': 'keep'}
            return copy.deepcopy(answer), {'request_id': model + ('-target' if target else '-other')}

        with patch.object(self.converter, 'verification', side_effect=provider) as verify:
            result = self.converter.verify(None, candidate)
        # This fails on V45's actual routing: every Sol response says keep.
        self.assertEqual(result['route'], 'escalate')
        self.assertEqual([call.kwargs['model'] for call in verify.call_args_list],
                         ['gpt-6-astra', 'gpt-6-astra', 'gpt-6-sol'])
        item = next(item for item in result['evidence'] if item.get('panel') == 1)
        self.assertEqual(item['verdict'], failed)
        self.assertEqual(item['model'], 'gpt-6-astra')
        self.assertEqual(item['request']['request_id'], 'gpt-6-astra-target')
        self.assertTrue(item['crossing_art_risk'])
        self.assertNotIn('adjudication', item)
        self.assertNotIn('original_verdict', item)
        self.assertEqual(len(item['source_details']), 2)
        self.assertIn('exact actual crop extent', item['source_details'][1]['label'])
        attempt = {'candidate': candidate, 'judge': judge, 'verifier': result}
        with patch.object(self.client, 'request', side_effect=RunBlocked('Captured repair')) as request:
            with self.assertRaisesRegex(RunBlocked, 'Captured repair'):
                self.converter.repair(Path(self.source['path']), attempt)
        request.assert_called_once()
        endpoint, body, kind = request.call_args.args
        self.assertEqual((endpoint, kind), ('responses', 'detector'))
        findings = body['input'][0]['content'][-1]['text'].split('\n', 1)[1]
        self.assertEqual(json.loads(findings), failed['issues'])
        self.assertEqual(candidate['panels'], original)

    def test_direct_astra_global_rejection_is_binding_without_readjudication(self):
        candidate = self.add_candidate('crossing-global', tier='astra')
        native = self.native_keep(); native['crossing_art'] = {'targets': [1]}
        self.prime(candidate, native)
        failed = self.clipping_verdict(2)

        def provider(bundle, prompt, effort, model):
            answer = failed if model == 'gpt-6-astra' and len(bundle['images']) == 3 else {'route': 'keep'}
            return copy.deepcopy(answer), {'request_id': 'global' if len(bundle['images']) == 3 else 'target'}

        with patch.object(self.converter, 'verification', side_effect=provider) as verify:
            result = self.converter.verify(None, candidate)
        self.assertEqual(result['route'], 'escalate')
        self.assertEqual(verify.call_count, 3)
        self.assertEqual(result['evidence'][0]['verdict'], failed)
        self.assertEqual(result['evidence'][0]['model'], 'gpt-6-astra')
        self.assertTrue(all(item['verdict']['route'] == 'keep' for item in result['evidence'][1:]))
        self.assertTrue(all('adjudication' not in item for item in result['evidence']))

    def test_crossing_model_selection_preserves_non_crossing_prompts_and_inputs(self):
        from ownership_converter import AUTHORED_BOUNDARY_CLARIFICATION
        global_prompt = (Path(__file__).parent / 'judge-prompt-v2.txt').read_text()
        target_prompt = (Path(__file__).parent / 'judge-target-detail-prompt-v2.txt').read_text()
        for tier in ('sol-low', 'sol-high', 'astra'):
            for crossing in (False, True):
                with self.subTest(tier=tier, crossing=crossing):
                    candidate = self.add_candidate('routing-' + tier + str(crossing), tier=tier)
                    native = self.native_keep()
                    native['crossing_art'] = {'targets': [1] if crossing else []}
                    self.prime(candidate, native)
                    original = copy.deepcopy(self.converter.bundles[candidate['identity']])
                    with patch.object(self.converter, 'verification', return_value=({'route': 'keep'}, {})) as verify:
                        result = self.converter.verify(None, candidate)
                    self.assertEqual(result['route'], 'keep')
                    expected = ['gpt-6-astra' if tier == 'astra' and crossing else 'gpt-6-sol',
                                'gpt-6-astra' if crossing else 'gpt-6-sol', 'gpt-6-sol']
                    self.assertEqual([call.kwargs['model'] for call in verify.call_args_list], expected)
                    for index, call in enumerate(verify.call_args_list):
                        prompt = global_prompt if index == 0 else target_prompt
                        if expected[index] == 'gpt-6-astra':
                            prompt += AUTHORED_BOUNDARY_CLARIFICATION
                        self.assertEqual(call.args[1:], (prompt, 'high'))
                        self.assertEqual(call.args[0]['_ownership_hypotheses'], original['_ownership_hypotheses'])
                        self.assertEqual(call.args[0]['panels'], original['panels'])
                        if index == 0:
                            self.assertEqual(call.args[0]['images'], original['images'])
                        else:
                            self.assertEqual(call.args[0]['images'][:2], [original['images'][0], original['images'][index]])
                            self.assertEqual(len(call.args[0]['images']), 4)
                    self.assertEqual(self.converter.bundles[candidate['identity']], original)

    def test_repair_adjudication_strict_eligibility_through_actual_verify(self):
        mutations = [
            lambda candidate, verdict: candidate.update(tier='sol-low'),
            lambda candidate, verdict: verdict.update(decision='uncertain'),
            lambda candidate, verdict: verdict.update(route='keep'),
            lambda candidate, verdict: verdict.update(scene_inventory='fail'),
            lambda candidate, verdict: verdict.update(reading_order='uncertain'),
            lambda candidate, verdict: verdict.update(crop_coverage='uncertain'),
            lambda candidate, verdict: verdict.update(issues=[]),
            lambda candidate, verdict: verdict['issues'][0].update(kind='missing_scene'),
            lambda candidate, verdict: verdict['issues'].append(
                {'kind': 'missing_scene', 'panels': [2], 'evidence': 'Mixed non-clipping defect.'}),
            lambda candidate, verdict: verdict['issues'][0].update(panels=[]),
            lambda candidate, verdict: verdict['issues'][0].update(panels=[3]),
            lambda candidate, verdict: verdict['issues'][0].update(panels=[True]),
            lambda candidate, verdict: verdict['issues'][0].update(evidence=''),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(ineligible=index):
                candidate = self.repaired_adjudication_candidate()
                failed = self.clipping_verdict()
                mutate(candidate, failed)
                with patch('ownership_converter.with_source_detail', side_effect=self.adjudication_detail), \
                        patch.object(self.converter, 'verification', side_effect=[
                            (failed, {}), ({'route': 'keep'}, {}), ({'route': 'keep'}, {})]) as verify:
                    result = self.converter.verify(None, candidate)
                self.assertTrue(all(call.kwargs['model'] == 'gpt-6-sol' for call in verify.call_args_list))
                self.assertTrue(all('original_verdict' not in entry for entry in result['evidence']))
        # A local failure naming another target cannot be cleared at this scope.
        candidate = self.repaired_adjudication_candidate()
        with patch('ownership_converter.with_source_detail', side_effect=self.adjudication_detail), \
                patch.object(self.converter, 'verification', side_effect=[
                    ({'route': 'keep'}, {}), (self.clipping_verdict(2), {}), ({'route': 'keep'}, {})]) as verify:
            result = self.converter.verify(None, candidate)
        self.assertEqual(result['route'], 'escalate')
        self.assertTrue(all(call.kwargs['model'] == 'gpt-6-sol' for call in verify.call_args_list))

    def test_unrepaired_stronger_candidates_adjudicate_clipping_with_scoped_prompt(self):
        for tier in ('sol-high', 'astra'):
            with self.subTest(tier=tier):
                candidate = self.add_candidate('unrepaired-' + tier, tier=tier)
                self.prime(candidate)
                geometry = copy.deepcopy(candidate['panels'])
                bundle = self.converter.bundles[candidate['identity']]
                original = copy.deepcopy(bundle)
                global_failure = self.clipping_verdict(2); target_failure = self.clipping_verdict(1)
                with patch('ownership_converter.with_source_detail', side_effect=self.adjudication_detail), \
                        patch.object(self.converter, 'verification', side_effect=[
                            (global_failure, {'id': 'sol-global'}), ({'route': 'keep'}, {'id': 'astra-global'}),
                            (target_failure, {'id': 'sol-target'}), ({'route': 'keep'}, {'id': 'astra-target'}),
                            ({'route': 'keep'}, {'id': 'sol-other'})]) as verify:
                    result = self.converter.verify(None, candidate)
                self.assertEqual(result['route'], 'keep')
                self.assertNotIn('repair_of', candidate)
                self.assertEqual([call.kwargs['model'] for call in verify.call_args_list],
                                 ['gpt-6-sol', 'gpt-6-astra', 'gpt-6-sol', 'gpt-6-astra', 'gpt-6-sol'])
                from ownership_converter import AUTHORED_BOUNDARY_CLARIFICATION
                global_sol, global_astra, local_sol, local_astra, other = verify.call_args_list
                for original_call, strong_call in ((global_sol, global_astra), (local_sol, local_astra)):
                    self.assertNotIn(AUTHORED_BOUNDARY_CLARIFICATION, original_call.args[1])
                    self.assertEqual(strong_call.args[1], original_call.args[1] + AUTHORED_BOUNDARY_CLARIFICATION)
                    self.assertEqual(strong_call.args[2], 'high')
                self.assertNotIn(AUTHORED_BOUNDARY_CLARIFICATION, other.args[1])
                self.assertEqual(global_astra.args[0]['images'][:len(bundle['images'])], bundle['images'])
                self.assertIs(local_sol.args[0], local_astra.args[0])
                self.assertEqual(result['evidence'][0]['original_verdict'], global_failure)
                self.assertEqual(result['evidence'][0]['original_request'], {'id': 'sol-global'})
                self.assertEqual(result['evidence'][1]['original_verdict'], target_failure)
                self.assertEqual(result['evidence'][1]['original_request'], {'id': 'sol-target'})
                self.assertEqual(result['evidence'][1]['adjudication']['target'], 1)
                self.assertEqual(candidate['panels'], geometry)
                self.assertEqual(bundle, original)

    def test_unrepaired_stronger_rejection_or_uncertainty_remains_binding(self):
        for tier in ('sol-high', 'astra'):
            for decision in ('escalate', 'uncertain'):
                with self.subTest(tier=tier, decision=decision):
                    candidate = self.add_candidate('unrepaired-reject-' + tier + decision, tier=tier)
                    self.prime(candidate)
                    first = self.clipping_verdict(); stronger = self.clipping_verdict()
                    stronger['decision'] = decision
                    with patch('ownership_converter.with_source_detail', side_effect=self.adjudication_detail), \
                            patch.object(self.converter, 'verification', side_effect=[
                                (first, {'id': 'sol-global'}), (stronger, {'id': 'astra-global'}),
                                ({'route': 'keep'}, {}), ({'route': 'keep'}, {})]) as verify:
                        result = self.converter.verify(None, candidate)
                    self.assertEqual(result['route'], 'escalate')
                    self.assertEqual(verify.call_count, 2 if tier == 'sol-high' else 4)
                    self.assertEqual(sum(call.kwargs['model'] == 'gpt-6-astra' for call in verify.call_args_list), 1)
                    self.assertEqual(result['evidence'][0]['original_verdict'], first)
                    self.assertEqual(result['evidence'][0]['verdict'], stronger)

    def test_stronger_global_rejection_remains_binding_despite_target_passes(self):
        candidate = self.repaired_adjudication_candidate()
        first = self.clipping_verdict(2); stronger = self.clipping_verdict(2)
        stronger['issues'][0]['evidence'] = 'Independent global check confirms missing content.'
        with patch('ownership_converter.with_source_detail', side_effect=self.adjudication_detail), \
                patch.object(self.converter, 'verification', side_effect=[
                    (first, {'id': 'sol-global'}), (stronger, {'id': 'astra-global'}),
                    ({'route': 'keep'}, {}), ({'route': 'keep'}, {})]) as verify:
            result = self.converter.verify(None, candidate)
        self.assertEqual(result['route'], 'escalate')
        self.assertEqual([call.kwargs['model'] for call in verify.call_args_list],
                         ['gpt-6-sol', 'gpt-6-astra', 'gpt-6-sol', 'gpt-6-sol'])
        item = result['evidence'][0]
        self.assertEqual(item['original_verdict'], first)
        self.assertEqual(item['original_request'], {'id': 'sol-global'})
        self.assertEqual(item['verdict'], stronger)
        self.assertEqual(item['request'], {'id': 'astra-global'})
        self.assertEqual(item['adjudication']['scope'], item['scope'])
        self.assertIsNone(item['adjudication']['target'])

    def test_stronger_target_rejection_or_uncertainty_cannot_loop_or_accept(self):
        for decision in ('escalate', 'uncertain'):
            with self.subTest(decision=decision):
                candidate = self.repaired_adjudication_candidate()
                first = self.clipping_verdict(); stronger = self.clipping_verdict()
                stronger['decision'] = decision
                with patch('ownership_converter.with_source_detail', side_effect=self.adjudication_detail), \
                        patch.object(self.converter, 'verification', side_effect=[
                            ({'route': 'keep'}, {}), (first, {'id': 'sol-target'}),
                            (stronger, {'id': 'astra-target'}), ({'route': 'keep'}, {})]) as verify:
                    result = self.converter.verify(None, candidate)
                self.assertEqual(result['route'], 'escalate')
                self.assertEqual(sum(call.kwargs['model'] == 'gpt-6-astra'
                                     for call in verify.call_args_list), 1)
                item = result['evidence'][1]
                self.assertEqual(item['panel'], item['adjudication']['target'])
                self.assertEqual(item['original_verdict'], first)
                self.assertEqual(item['original_request'], {'id': 'sol-target'})
                self.assertEqual(item['verdict'], stronger)
                self.assertEqual(item['request'], {'id': 'astra-target'})

    def test_adjudication_preserves_full_global_and_exact_local_scope(self):
        for other_failure in (False, True):
            with self.subTest(other_failure=other_failure):
                candidate = self.repaired_adjudication_candidate()
                bundle = self.converter.bundles[candidate['identity']]
                original_bundle = copy.deepcopy(bundle)
                global_failure = self.clipping_verdict(2); target_failure = self.clipping_verdict()
                last = self.clipping_verdict(2) if other_failure else {'route': 'keep'}
                if other_failure: last['issues'][0]['kind'] = 'missing_scene'
                with patch('ownership_converter.with_source_detail', side_effect=self.adjudication_detail), \
                        patch.object(self.converter, 'verification', side_effect=[
                            (global_failure, {'id': 'sol-global'}), ({'route': 'keep'}, {'id': 'astra-global'}),
                            (target_failure, {'id': 'sol-target'}), ({'route': 'keep'}, {'id': 'astra-target'}),
                            (last, {'id': 'other-target'})]) as verify:
                    result = self.converter.verify(None, candidate)
                self.assertEqual(result['route'], 'escalate' if other_failure else 'keep')
                self.assertEqual([call.kwargs['model'] for call in verify.call_args_list],
                                 ['gpt-6-sol', 'gpt-6-astra', 'gpt-6-sol', 'gpt-6-astra', 'gpt-6-sol'])
                global_sol, global_astra, target_sol, target_astra, _ = verify.call_args_list
                strong_bundle = global_astra.args[0]
                self.assertEqual(strong_bundle['images'][:len(bundle['images'])], bundle['images'])
                self.assertEqual(strong_bundle['images'][len(bundle['images']):],
                                 self.adjudication_detail(bundle, 2, None, mark_boundary=True)['images'][2:])
                for key in ('panels', 'classification', 'reading_direction', '_ownership_hypotheses'):
                    self.assertEqual(strong_bundle[key], bundle[key])
                from ownership_converter import AUTHORED_BOUNDARY_CLARIFICATION
                self.assertEqual(global_astra.args[1], global_sol.args[1] + AUTHORED_BOUNDARY_CLARIFICATION)
                self.assertEqual(global_sol.args[2:], global_astra.args[2:])
                self.assertIs(target_sol.args[0], target_astra.args[0])
                self.assertEqual(target_astra.args[1], target_sol.args[1] + AUTHORED_BOUNDARY_CLARIFICATION)
                self.assertEqual(target_sol.args[2:], target_astra.args[2:])
                self.assertEqual(result['evidence'][0]['original_verdict'], global_failure)
                self.assertEqual(result['evidence'][1]['original_verdict'], target_failure)
                self.assertEqual(result['evidence'][2]['verdict'], last)
                self.assertNotIn('original_verdict', result['evidence'][2])
                self.assertEqual(bundle, original_bundle)

    def test_intermediate_global_failure_skips_futile_target_calls(self):
        self.prime()
        with patch.object(self.converter, 'verification', return_value=({'route': 'escalate'}, {})) as verify:
            result = self.converter.verify(None, self.candidate)
        self.assertEqual(result['route'], 'escalate')
        self.assertEqual(verify.call_count, 1)

    def test_layout_failure_remains_binding(self):
        verdict = self.native_keep()
        verdict.update(route='escalate', split_flags=[[1, 2]])
        self.prime(verdict=verdict)
        with patch.object(self.converter, 'verification') as verify:
            result = self.converter.verify(None, self.candidate)
        self.assertEqual(result['route'], 'escalate')
        verify.assert_not_called()

    def test_source_audit_matches_qualified_verifier_cache_namespace(self):
        self.converter._ensure_evidence(self.candidate)
        artifact = self.converter.scene_evidence['candidate']
        expected = request_fingerprint(self.converter._proposal_bundle(self.candidate),
                                       model='gpt-6-astra', request_kind='verifier')
        self.assertEqual(artifact['request_fingerprint'], expected)
        self.assertEqual(artifact['request']['request_id'], expected)
        self.assertEqual(artifact['request_kind'], 'verifier')
        self.assertNotEqual(expected, request_fingerprint(self.converter._proposal_bundle(self.candidate),
                                                        model='gpt-6-astra', request_kind='detector'))

    def test_exhausted_source_audit_gets_one_bounded_larger_audit(self):
        from scene_evidence import recovery_output_limit, source_output_limit
        default, larger = source_output_limit(2), recovery_output_limit(2)
        self.exhausted_limits = {default}
        self.converter._ensure_evidence(self.candidate)
        artifact = self.converter.scene_evidence['candidate']
        limits = [call.args[1]['max_output_tokens'] for call in self.client.request.call_args_list
                  if call.args[0] == 'responses']
        self.assertEqual(limits, [default, larger])
        self.assertEqual(artifact['output_limit'], larger)
        self.assertEqual(artifact['request_fingerprint'],
                         request_fingerprint(self.converter._proposal_bundle(self.candidate), model='gpt-6-astra',
                                             request_kind='verifier', output_limit=larger))
        from scene_evidence import evidence_gate
        self.assertEqual(evidence_gate(artifact, self.converter._proposal_bundle(self.candidate))['route'], 'keep')

    def test_second_source_audit_exhaustion_still_blocks(self):
        from scene_evidence import recovery_output_limit, source_output_limit
        self.exhausted_limits = {source_output_limit(2), recovery_output_limit(2)}
        with self.assertRaisesRegex(RunBlocked, 'Source ownership audit invalid'):
            self.converter._ensure_evidence(self.candidate)

    def test_base_guard_clearance_cannot_skip_ownership_confirmation(self):
        for flag in ('overlap_pairs', 'split_flags', 'inventory_flags'):
            with self.subTest(flag=flag):
                verdict = self.native_keep()
                verdict.update(route='escalate', **{flag: [[1, 2]]})
                self.converter.judgments['candidate'] = verdict
                with patch.object(Converter, 'verify', return_value={'route': 'keep', 'evidence': []}) as base, \
                        patch('ownership_converter.with_source_detail', side_effect=lambda bundle, *_args, **_kwargs: bundle), \
                        patch.object(self.converter, 'verification', side_effect=[({'route': route}, {}) for route in
                                                                                 ('keep', 'keep', 'escalate')]) as check:
                    result = self.converter.verify(None, self.candidate)
                base.assert_called_once()
                self.assertEqual(check.call_count, 3)
                self.assertEqual(result['route'], 'escalate')
                self.assertEqual([entry['panel'] for entry in result['evidence'] if 'panel' in entry], [1, 2])

    def test_unexpected_low_tier_keep_cannot_skip_risky_confirmation(self):
        low = self.add_candidate('low', tier='sol-low')
        verdict = self.prime(low)
        self.assertEqual(verdict['route'], 'escalate')
        self.assertTrue(verdict['ownership_confirmation_required'])
        self.assertEqual(self.client.request.call_count, 1)

    def test_marked_request_body_exactly_matches_qualified_experiment(self):
        self.prime()
        bundle = self.converter.bundles['candidate']
        hypotheses = bundle['_ownership_hypotheses']
        path = Path(__file__).parent / 'experiments/scene_identity_v1/protocol.py'
        spec = importlib.util.spec_from_file_location('qualified_scene_identity_protocol', path)
        protocol = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(protocol)
        expected = protocol.verifier_body(bundle, hypotheses, 'identity')
        raw = {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text',
               'text': json.dumps({'decision': 'accept', 'scene_inventory': 'pass', 'reading_order': 'pass',
                                   'crop_coverage': 'pass', 'issues': []})}]}]}
        with patch.object(self.client, 'request', return_value=(raw, {})) as request:
            self.converter.verification(bundle, (Path(__file__).parent / 'judge-target-detail-prompt-v2.txt').read_text(),
                                        'high', model='gpt-6-sol')
        self.assertEqual(request.call_args.args, ('responses', expected, 'verifier'))


if __name__ == '__main__':
    unittest.main()
