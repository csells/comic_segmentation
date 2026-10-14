import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from target_detail import with_source_detail, needs_source_detail


class TargetDetailTests(unittest.TestCase):
    def clipping(self):
        return {'route': 'escalate', 'decision': 'escalate', 'scene_inventory': 'pass',
                'reading_order': 'pass', 'crop_coverage': 'fail',
                'issues': [{'kind': 'clipped_art', 'panels': [1], 'evidence': 'Missing target edge.'}]}

    def test_only_confirmed_localized_clipping_on_final_repair_is_eligible(self):
        candidate = {'tier': 'astra', 'repair_of': 'earlier'}
        self.assertTrue(needs_source_detail(candidate, self.clipping(), 1))
        self.assertFalse(needs_source_detail({'tier': 'astra'}, self.clipping(), 1))
        self.assertFalse(needs_source_detail(candidate, self.clipping(), 2))
        for field, value in [('decision', 'uncertain'), ('scene_inventory', 'fail'),
                             ('reading_order', 'fail'), ('issues', [])]:
            verdict = self.clipping(); verdict[field] = value
            self.assertFalse(needs_source_detail(candidate, verdict, 1))
        verdict = self.clipping(); verdict['issues'][0]['kind'] = 'missing_scene'
        self.assertFalse(needs_source_detail(candidate, verdict, 1))

    def test_detail_pass_cannot_clear_global_failure_or_detail_uncertainty(self):
        from auto_convert import Converter
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); converter = Converter(None, root)
            bundle = self.fixture(root); converter.bundles['candidate'] = bundle
            converter.judgments['candidate'] = {'global_crop_flags': ['art_clipping'],
                'semantic_flags': [], 'target_flags': [1], 'split_checks': []}
            candidate = {'identity': 'candidate', 'tier': 'astra', 'repair_of': 'earlier',
                         'bundle': str(root / 'bundle.json')}
            for global_route, detail_route, expected in [('keep', 'keep', 'keep'),
                                                        ('escalate', 'keep', 'escalate'),
                                                        ('keep', 'escalate', 'escalate')]:
                answers = [({'route': global_route}, {}), (self.clipping(), {}),
                           ({'route': detail_route}, {})]
                with patch.object(converter, 'verification', side_effect=answers), \
                     patch('auto_convert.with_source_detail', return_value=bundle):
                    result = converter.verify(None, candidate)
                self.assertEqual(result['route'], expected)
                self.assertEqual(len(result['evidence']), 3)
                self.assertEqual(result['evidence'][1]['verdict'], self.clipping())

    def fixture(self, root):
        source = root / 'source.png'; Image.new('RGB', (400, 600), '#123456').save(source)
        crop = root / 'crop.png'; Image.new('RGB', (81, 121), '#123456').save(crop)
        return {'classification': 'panels', 'reading_direction': 'ltr',
                'panels': [{'order': 1, 'box': [400, 400, 600, 600]}],
                'images': [{'label': 'Original complete page', 'path': str(source),
                            'sha256': hashlib.sha256(source.read_bytes()).hexdigest()},
                           {'label': 'Candidate crop 1 in reading order', 'path': str(crop),
                            'points': '160,240 240,240 240,360 160,360'}]}

    def test_context_extends_outside_crop_without_changing_source_or_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); bundle = self.fixture(root); before = copy.deepcopy(bundle)
            value = with_source_detail(bundle, 1, root / 'detail')
            self.assertEqual(bundle, before)
            self.assertEqual(value['images'][:2], before['images'])
            self.assertIn('[96, 176, 304, 424]', value['images'][2]['label'])
            with Image.open(value['images'][2]['path']) as im:
                self.assertEqual(im.size, (416, 496))
            self.assertEqual(value, with_source_detail(bundle, 1, root / 'detail'))
            self.assertEqual(hashlib.sha256(Path(bundle['images'][0]['path']).read_bytes()).hexdigest(),
                             bundle['images'][0]['sha256'])

    def test_changed_source_or_existing_detail_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); bundle = self.fixture(root)
            value = with_source_detail(bundle, 1, root / 'detail')
            Path(value['images'][2]['path']).write_bytes(b'stale')
            with self.assertRaisesRegex(ValueError, 'existing source detail differs'):
                with_source_detail(bundle, 1, root / 'detail')
            Path(bundle['images'][0]['path']).write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError, 'source detail input changed'):
                with_source_detail(bundle, 1, root / 'other')

    def test_context_stops_at_source_edges(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); bundle = self.fixture(root)
            bundle['panels'][0]['box'] = [0, 0, 1000, 1000]
            value = with_source_detail(bundle, 1, root / 'detail')
            self.assertIn('[0, 0, 400, 600]', value['images'][2]['label'])

    def test_boundary_uses_actual_inclusive_crop_points_and_preserves_unmarked_context(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); bundle = self.fixture(root)
            plain = with_source_detail(bundle, 1, root / 'detail')
            value = with_source_detail(bundle, 1, root / 'detail', mark_boundary=True)
            self.assertEqual(value['images'][:3], plain['images'])
            self.assertIn('[160, 240, 241, 361]', value['images'][3]['label'])
            with Image.open(value['images'][3]['path']) as im:
                red = im.getpixel((128, 128))
                self.assertGreater(red[0], red[1] + 50)
            Image.new('RGB', (80, 120)).save(bundle['images'][1]['path'])
            with self.assertRaisesRegex(ValueError, 'dimensions differ'):
                with_source_detail(bundle, 1, root / 'detail', mark_boundary=True)


if __name__ == '__main__':
    unittest.main()
