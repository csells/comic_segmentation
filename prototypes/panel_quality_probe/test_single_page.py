"""Offline publication checks with a stubbed detector outcome, not quality tests."""
from contextlib import redirect_stdout
import io
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
import zipfile

from PIL import Image

import auto_convert


class SinglePageTests(unittest.TestCase):
    def test_single_image_import_is_preserved_and_empty_folder_rejects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root/'source'; source.mkdir()
            image = source/'only.png'; Image.new('RGB', (40, 60), 'white').save(image)
            original = image.read_bytes()
            result = auto_convert.prepare_input(source, root/'prepared', None)
            self.assertEqual(len(result['pages']), 1)
            self.assertEqual((root/'prepared/pages/0001.png').read_bytes(), original)
            empty = root/'empty'; empty.mkdir()
            with self.assertRaisesRegex(ValueError, 'no comic page images'):
                auto_convert.prepare_input(empty, root/'empty-prepared', None)

    def test_single_input_and_single_selected_page_keep_first_page_panel_counts(self):
        for source_count, selected in ((1, 1), (2, 2)):
            with self.subTest(source_count=source_count, selected=selected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); source = root/'source'; source.mkdir()
                for ordinal in range(1, source_count + 1):
                    Image.new('RGB', (40, 60), 'white').save(source/f'{ordinal:04d}.png')
                selected_bytes = (source/f'{selected:04d}.png').read_bytes()
                output = root/'run'
                # Publication-only fixture. This is deliberately not detector or
                # completeness evidence; real proof validation is tested separately.
                value={'classification':'panels','orientation':'upright','reading_direction':'ltr','panels':[
                    {'order':1,'box':[0,0,500,1000]},
                    {'order':2,'box':[500,0,1000,1000]}]}
                expected={}
                def publication_fixture(page,*_args,final_accept,**_kwargs):
                    self.assertTrue(callable(final_accept))
                    candidate={'identity':'publication-unit-fixture','source_sha256':auto_convert.sha(page),
                               'panels':copy.deepcopy(value),'refinement_changes':[]}
                    proof_path=root/'unit-only-proof.json'
                    proof_path.write_text(json.dumps({'unit_only':True,'candidate':candidate},sort_keys=True))
                    verdict={'route':'keep','reason':'Publication unit fixture, no quality claim',
                             'proof':{'path':str(proof_path),'sha256':auto_convert.sha(proof_path)}}
                    expected.update(page=page,candidate=copy.deepcopy(candidate),verdict=copy.deepcopy(verdict))
                    return {'status':'accepted','selected':candidate,'attempts':[
                        {'tier':'offline-fixture','candidate':copy.deepcopy(candidate),
                         'judge':{'route':'keep'},'completeness':verdict}]}
                def unit_proof_validator(page,candidate,receipt,*,require_keep):
                    self.assertTrue(require_keep)
                    self.assertEqual(page,expected['page'])
                    self.assertEqual(candidate,expected['candidate'])
                    self.assertEqual(receipt,expected['verdict']['proof'])
                    self.assertEqual(auto_convert.sha(receipt['path']),receipt['sha256'])
                    self.assertEqual(json.loads(Path(receipt['path']).read_text())['candidate'],candidate)
                    return copy.deepcopy(expected['verdict'])
                argv = ['auto_convert', str(source), str(output), '--ledger', str(root/'offline-ledger.jsonl'),
                        '--pages', str(selected), '--reading-direction', 'ltr', '--execute-approved']
                with patch('sys.argv', argv), patch('sys.stdin', io.StringIO('sk-' + 'offline-fixture-'*3)), \
                     patch.object(auto_convert, 'run_page', side_effect=publication_fixture) as analysis, \
                     patch.object(auto_convert, 'validate_proof', side_effect=unit_proof_validator) as proof, \
                     patch.object(auto_convert, 'SourceCompleteness') as guard, \
                     patch.object(auto_convert.Client, 'http', side_effect=AssertionError('HTTP forbidden')) as http, \
                     redirect_stdout(io.StringIO()):
                    auto_convert.main()
                analysis.assert_called_once(); http.assert_not_called()
                guard.return_value.check.assert_not_called()
                self.assertEqual(proof.call_count,2)  # Save and prepublication binding checks.
                self.assertEqual(json.loads((output/'counts.json').read_text()), [])
                self.assertEqual(json.loads((output/'all-page-counts.json').read_text()), [2])
                summary = json.loads(next(output.glob('completed-*.json')).read_text())
                self.assertEqual(summary['pages'], 1)
                self.assertEqual(summary['source_pages'], [selected])
                self.assertEqual(summary['panel_counts'], [2])
                self.assertEqual(summary['panel_steps'], 2)
                self.assertEqual(summary['body_panel_steps'], 0)
                self.assertEqual(summary['new_calls'], 0)
                with zipfile.ZipFile(output/'automatic-panels.cbz') as archive:
                    xml = ET.fromstring(archive.read('metadata.acbf'))
                    self.assertIsNone(xml.find('{*}body'))
                    self.assertEqual(len(xml.findall('.//{*}image')), 1)
                    self.assertEqual(len(xml.findall('.//{*}coverpage/{*}frame')), 2)
                    self.assertEqual(archive.read('0001.png'), selected_bytes)


if __name__ == '__main__': unittest.main()
