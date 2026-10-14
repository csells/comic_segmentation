import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from protocol import (SpikeBudget, LIMIT, auxiliary, identity_body, parse_identities,
                      verifier_body, fingerprint)
from run import structural_score


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        path = self.root/'private-reviewer-negative-150.jpg'
        path.write_bytes(b'fixture-image')
        self.bundle = {'classification': 'panels', 'reading_direction': 'ltr',
                       'panels': [{'order': 1, 'box': [1, 2, 900, 950]}],
                       'images': [{'label': 'Original complete page', 'path': str(path),
                                   'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}],
                       'expected': 'EVALUATION_SENTINEL', 'reviewer_notes': 'MISSING_FLOWER_SENTINEL'}
        self.ids = {'scenes': [{'order': i, 'identity': f'scene-{i}', 'owned_content': ['figure'],
                               'ownership_cues': ['connected'], 'distinguish_from_neighbors': [],
                               'uncertain': False} for i in (1, 2, 3)]}

    def tearDown(self):
        self.temp.cleanup()

    def test_request_whitelists_exclude_evaluation_and_paths(self):
        for body in (identity_body(self.bundle), verifier_body(self.bundle, self.ids, 'identity')):
            value = json.dumps(body)
            for sentinel in ('EVALUATION_SENTINEL', 'MISSING_FLOWER_SENTINEL', 'private-reviewer-negative', str(self.root)):
                self.assertNotIn(sentinel, value)

    def test_only_added_prompt_differs_across_conditions(self):
        baseline = verifier_body(self.bundle)
        changed = verifier_body(self.bundle, self.ids, 'identity')
        self.assertNotEqual(fingerprint(baseline), fingerprint(changed))
        self.assertEqual(baseline['input'][0]['content'][1:], changed['input'][0]['content'][1:])
        for field in baseline.keys() - {'input'}:
            self.assertEqual(baseline[field], changed[field])
        self.assertIn('Candidate geometry:', changed['input'][0]['content'][0]['text'])

    def test_rotations_do_not_mutate_original_and_omission_keeps_wrapper(self):
        before = copy.deepcopy(self.ids)
        rotated = auxiliary(self.ids, 'rotated')
        self.assertEqual(self.ids, before)
        parsed = json.loads(rotated.split('\n')[-1])
        self.assertEqual([(s['order'], s['identity']) for s in parsed['scenes']], [(1, 'scene-2'), (2, 'scene-3'), (3, 'scene-1')])
        omitted = auxiliary(self.ids, 'omitted')
        self.assertEqual(omitted.rsplit('\n', 1)[0], rotated.rsplit('\n', 1)[0])
        self.assertEqual(json.loads(omitted.split('\n')[-1]), {'scenes': []})

    def test_source_tampering_blocks_request(self):
        Path(self.bundle['images'][0]['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            identity_body(self.bundle)
        with self.assertRaises(ValueError):
            verifier_body(self.bundle)

    def test_unsettled_hold_counts_against_local_limit(self):
        budget = SpikeBudget(self.root/'ledger', self.root)
        budget.entries = {'unsettled': {'path': str(self.root/'calls'/'unknown'), 'cost': LIMIT}}
        with patch('protocol.Budget.reserve') as parent:
            with self.assertRaises(ValueError):
                budget.reserve('new', self.root/'calls'/'new', 1, 1, 1)
            parent.assert_not_called()

    def test_invalid_generator_inventory_or_verdict_rejected(self):
        raw = {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(self.ids)}]}]}
        self.assertEqual(parse_identities(raw, [1, 2, 3]), self.ids)
        with self.assertRaises(ValueError):
            parse_identities(raw, [1, 3, 2])
        raw['status'] = 'incomplete'
        with self.assertRaises(ValueError):
            parse_identities(raw, [1, 2, 3])

    def test_uncertainty_cannot_satisfy_quality_gate(self):
        value = {'route': 'escalate', 'decision': 'uncertain', 'scene_inventory': 'pass',
                 'reading_order': 'pass', 'crop_coverage': 'uncertain', 'issues': []}
        self.assertFalse(structural_score(value, 'defect', 3)['routing_pass'])
        self.assertFalse(structural_score(value, 'intact', 3)['routing_pass'])
        value.update(crop_coverage='fail', issues=[{'kind': 'clipped_art', 'panels': [3]}])
        self.assertFalse(structural_score(value, 'defect', 3)['routing_pass'])
        value['route'] = 'keep'
        self.assertTrue(structural_score(value, 'defect', 3)['harmful_accept'])


if __name__ == '__main__':
    unittest.main()
