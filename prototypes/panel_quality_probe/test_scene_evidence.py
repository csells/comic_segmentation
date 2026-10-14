"""Offline scene-evidence tests; execute only in disposable staging."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scene_evidence import (evidence_gate, proposal_sha256, request_body,
                            request_fingerprint, response_evidence, source_output_limit,
                            verifier_hypotheses)


class SceneEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        source = self.root / 'private-reviewer-file.jpg'
        source.write_bytes(b'source-fixture')
        self.bundle = {'classification': 'panels', 'reading_direction': 'ltr',
                       'panels': [{'order': 1, 'box': [100, 100, 400, 900], 'description': 'First view'},
                                  {'order': 2, 'box': [450, 100, 900, 900], 'description': 'Second view'}],
                       'images': [{'label': 'Original complete page', 'path': str(source),
                                   'sha256': hashlib.sha256(source.read_bytes()).hexdigest()},
                                  {'label': 'Candidate crop 1 in reading order', 'path': 'UNREAD_CROP_SENTINEL'}],
                       'expected': 'EVALUATION_SENTINEL', 'reviewer_notes': 'REVIEWER_SENTINEL'}
        self.result = {'inventory_status': 'complete', 'issues': [], 'scenes': [
            {'order': n, 'identity': f'View {n}', 'owned_content': ['figure and setting'],
             'ownership_cues': ['The figure stands on the continuous ground.'],
             'distinguish_from_neighbors': [], 'uncertain': False} for n in (1, 2)]}

    def tearDown(self):
        self.temp.cleanup()

    def artifact(self, result=None):
        raw = {'status': 'completed', 'output': [{'type': 'message', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': json.dumps(result or self.result)}]}]}
        return response_evidence(raw, self.bundle, {'request_id': request_fingerprint(self.bundle), 'secret': 'SECRET_SENTINEL'})

    def test_source_only_request_excludes_crops_paths_and_labels(self):
        body = request_body(self.bundle)
        content = body['input'][0]['content']
        self.assertEqual(sum(item['type'] == 'input_image' for item in content), 1)
        value = json.dumps(body)
        for sentinel in ('EVALUATION_SENTINEL', 'REVIEWER_SENTINEL', 'UNREAD_CROP_SENTINEL',
                         'private-reviewer-file', str(self.root)):
            self.assertNotIn(sentinel, value)
        self.assertEqual(body['model'], 'gpt-6-sol')
        self.assertIn('First view', value)

    def test_complete_evidence_is_source_linked_but_not_crop_approval(self):
        artifact = self.artifact()
        self.assertEqual(artifact['proposal_sha256'], proposal_sha256(self.bundle))
        self.assertNotIn('SECRET_SENTINEL', json.dumps(artifact))
        self.assertEqual(evidence_gate(artifact, self.bundle)['route'], 'keep')
        hypotheses = verifier_hypotheses(artifact, self.bundle)
        self.assertEqual(set(hypotheses), {'scenes'})
        self.assertEqual(hypotheses['scenes'], self.result['scenes'])
        hypotheses['scenes'][0]['identity'] = 'mutated'
        self.assertEqual(artifact['result']['scenes'][0]['identity'], 'View 1')

    def test_missing_uncertain_or_incomplete_never_passes(self):
        self.assertEqual(evidence_gate(None, self.bundle)['route'], 'escalate')
        for result in (dict(self.result, inventory_status='incomplete'),
                       dict(self.result, inventory_status='uncertain'),
                       dict(self.result, issues=[{'kind': 'uncertain', 'orders': [1], 'evidence': 'Ambiguous source'}])):
            artifact = self.artifact(result)
            self.assertEqual(evidence_gate(artifact, self.bundle)['route'], 'escalate')
            with self.assertRaises(ValueError):
                verifier_hypotheses(artifact, self.bundle)
        result = copy.deepcopy(self.result)
        result['scenes'][0]['uncertain'] = True
        self.assertEqual(evidence_gate(self.artifact(result), self.bundle)['route'], 'escalate')

    def test_shared_unowned_content_alone_does_not_block(self):
        shared = {'kind': 'shared_unowned', 'orders': [1, 2], 'evidence': 'Untailed caption straddles both panels.'}
        for status in ('complete', 'uncertain'):
            with self.subTest(status=status):
                result = dict(self.result, inventory_status=status, issues=[shared])
                self.assertEqual(evidence_gate(self.artifact(result), self.bundle)['route'], 'keep')
        edge = {'kind': 'shared_unowned', 'orders': [], 'evidence': 'Unreadable facing-page sliver at the outer edge.'}
        self.assertEqual(evidence_gate(self.artifact(dict(self.result, issues=[edge])), self.bundle)['route'], 'keep')

    def test_shared_unowned_never_excuses_other_problems(self):
        shared = {'kind': 'shared_unowned', 'orders': [1, 2], 'evidence': 'Loose debris between views.'}
        missing = {'kind': 'missing_scene', 'orders': [], 'evidence': 'An unproposed inset.'}
        for result in (dict(self.result, inventory_status='incomplete', issues=[shared]),
                       dict(self.result, inventory_status='uncertain', issues=[shared, missing]),
                       dict(self.result, issues=[shared, {'kind': 'uncertain', 'orders': [1], 'evidence': 'Ambiguous'}])):
            self.assertEqual(evidence_gate(self.artifact(result), self.bundle)['route'], 'escalate')
        result = copy.deepcopy(dict(self.result, issues=[shared]))
        result['scenes'][0]['uncertain'] = True
        self.assertEqual(evidence_gate(self.artifact(result), self.bundle)['route'], 'escalate')

    def test_prompt_and_schema_offer_shared_unowned(self):
        body = request_body(self.bundle)
        self.assertIn('shared_unowned', body['input'][0]['content'][0]['text'])
        enum = body['text']['format']['schema']['properties']['issues']['items']['properties']['kind']['enum']
        self.assertIn('shared_unowned', enum)

    def test_only_default_or_one_bounded_recovery_output_limit(self):
        from scene_evidence import recovery_output_limit, source_output_limit
        self.assertEqual(request_body(self.bundle)['max_output_tokens'], source_output_limit(2))
        larger = recovery_output_limit(2)
        self.assertEqual(request_body(self.bundle, output_limit=larger)['max_output_tokens'], larger)
        with self.assertRaisesRegex(ValueError, 'output allowance'):
            request_body(self.bundle, output_limit=larger + 1)
        raw = {'status': 'completed', 'output': [{'type': 'message', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': json.dumps(self.result)}]}]}
        fingerprint = request_fingerprint(self.bundle, output_limit=larger)
        artifact = response_evidence(raw, self.bundle, {'request_id': fingerprint}, output_limit=larger)
        self.assertEqual(artifact['output_limit'], larger)
        self.assertEqual(evidence_gate(artifact, self.bundle)['route'], 'keep')
        with self.assertRaises(ValueError):
            response_evidence(raw, self.bundle, {'request_id': request_fingerprint(self.bundle)}, output_limit=larger)

    def test_source_and_evidence_tampering_fail_safely(self):
        artifact = self.artifact()
        artifact['result']['scenes'][0]['identity'] = 'changed'
        self.assertEqual(evidence_gate(artifact, self.bundle)['route'], 'escalate')
        artifact = self.artifact()
        Path(self.bundle['images'][0]['path']).write_bytes(b'changed-source')
        self.assertEqual(evidence_gate(artifact, self.bundle)['route'], 'escalate')
        with self.assertRaises(ValueError):
            request_body(self.bundle)

    def test_monotonic_repair_requires_explicit_frozen_link(self):
        artifact = self.artifact()
        repaired = copy.deepcopy(self.bundle)
        repaired['panels'][0]['box'] = [80, 90, 420, 910]
        self.assertEqual(evidence_gate(artifact, repaired)['route'], 'escalate')
        gate = evidence_gate(artifact, repaired, frozen_proposal_sha256=artifact['proposal_sha256'])
        self.assertEqual(gate['route'], 'keep')
        repaired['panels'][0]['box'][0] = 110
        self.assertEqual(evidence_gate(artifact, repaired, frozen_proposal_sha256=artifact['proposal_sha256'])['route'], 'escalate')

    def test_inventory_order_direction_and_wrong_link_reject(self):
        artifact = self.artifact()
        for mutation in ('inventory', 'order', 'direction'):
            changed = copy.deepcopy(self.bundle)
            if mutation == 'inventory':
                changed['panels'].pop()
            elif mutation == 'order':
                changed['panels'].reverse()
            else:
                changed['reading_direction'] = 'rtl'
            self.assertEqual(evidence_gate(artifact, changed, frozen_proposal_sha256=artifact['proposal_sha256'])['route'], 'escalate')
        self.assertEqual(evidence_gate(artifact, self.bundle, frozen_proposal_sha256='0' * 64)['route'], 'escalate')

    def test_malformed_unmapped_and_refused_results_are_rejected(self):
        result = copy.deepcopy(self.result)
        result['scenes'].reverse()
        with self.assertRaises(ValueError):
            self.artifact(result)
        result = copy.deepcopy(self.result)
        result['scenes'][0]['ownership_cues'] = []
        with self.assertRaises(ValueError):
            self.artifact(result)
        for raw in ({'status': 'incomplete'},
                    {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'refusal'}]}]}):
            with self.assertRaises(ValueError):
                response_evidence(raw, self.bundle)

    def test_description_changes_invalidate_unlinked_evidence(self):
        artifact = self.artifact()
        changed = copy.deepcopy(self.bundle)
        changed['panels'][0]['description'] = 'Different locator'
        self.assertEqual(evidence_gate(artifact, changed)['route'], 'escalate')
        changed['panels'][0]['description'] = ''
        with self.assertRaises(ValueError):
            request_body(changed)

    def test_model_selection_preserves_default_body_and_binds_response(self):
        default = request_body(self.bundle)
        self.assertEqual(default, request_body(self.bundle, model='gpt-6-sol'))
        strong = request_body(self.bundle, model='gpt-6-astra')
        self.assertEqual({**default, 'model': 'gpt-6-astra'}, strong)
        raw = {'status': 'completed', 'model': 'gpt-6-astra', 'output': [{'type': 'message',
               'content': [{'type': 'output_text', 'text': json.dumps(self.result)}]}]}
        provenance = {'request_id': request_fingerprint(self.bundle, model='gpt-6-astra')}
        artifact = response_evidence(raw, self.bundle, provenance, model='gpt-6-astra')
        self.assertEqual(artifact['model'], 'gpt-6-astra')
        self.assertEqual(evidence_gate(artifact, self.bundle)['route'], 'keep')
        with self.assertRaises(ValueError):
            response_evidence(raw, self.bundle, provenance)
        with self.assertRaises(ValueError):
            request_body(self.bundle, model='unsupported')

    def test_output_capacity_cutoff_and_bound_are_count_based(self):
        for count, expected in ((1, 8192), (4, 8192), (5, 9216), (13, 17408),
                                (19, 23552), (20, 24576), (40, 24576)):
            with self.subTest(count=count):
                self.assertEqual(source_output_limit(count), expected)
        for invalid in (0, -1, True, 5.0):
            with self.assertRaises(ValueError):
                source_output_limit(invalid)

    def test_large_inventory_capacity_changes_request_fingerprint(self):
        small = request_body(self.bundle, model='gpt-6-astra')
        self.assertEqual(small['max_output_tokens'], 8192)
        large = copy.deepcopy(self.bundle)
        large['panels'] = [{'order': order, 'box': [100, 100, 900, 900],
                            'description': f'Proposed view {order}'} for order in range(1, 14)]
        body = request_body(large, model='gpt-6-astra')
        self.assertEqual(body['max_output_tokens'], 17408)
        old = {**body, 'max_output_tokens': 8192}
        old_fingerprint = hashlib.sha256(b'comic-escalation-judge-v1:' +
                                         json.dumps(old, sort_keys=True).encode()).hexdigest()
        self.assertNotEqual(request_fingerprint(large, model='gpt-6-astra', request_kind='verifier'),
                            old_fingerprint)


if __name__ == '__main__':
    unittest.main()
