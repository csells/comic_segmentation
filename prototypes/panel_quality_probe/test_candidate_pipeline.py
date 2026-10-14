"""Integration boundaries that could invalidate source pixels or repair lineage."""
import copy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from auto_convert import Client, Converter, HERE, credit_balance_rejection, prepare_input, prepare_analysis_image, source_page_context, sha
from automatic_escalation import RunBlocked
from gemini_budget import Budget
from openai_probe import response_panels


class CandidatePipelineTests(unittest.TestCase):
    def test_explicit_quota_recovery_is_once_reserved_and_never_replays_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); body = {'input': 'synthetic'}
            fingerprint = hashlib.sha256(b'https://api.openai.com/v1/decisions\n' + json.dumps(body, sort_keys=True).encode()).hexdigest()
            with Budget(root / 'ledger', cap=5000000) as budget:
                first = Client('synthetic', budget, root / 'original')
                failure = RunBlocked('HTTP 429: {"error":{"code":"credit_balance_exhausted"}}')
                with patch.object(first, 'http', side_effect=failure):
                    with self.assertRaises(RunBlocked):first.request('decisions', body, 'native')
                normal = Client('synthetic', budget, root / 'no-retry')
                with patch.object(normal, 'http') as http:
                    with self.assertRaisesRegex(RunBlocked, 'no automatic replay'):
                        normal.request('decisions', body, 'native')
                    http.assert_not_called()
                recovery = Client('synthetic', budget, root / 'recovery', retry_rejected={fingerprint})
                answer = {'usage': {'input_tokens': 100, 'output_tokens': 0, 'total_tokens': 100}}
                with patch.object(recovery, 'http', return_value=answer) as http:
                    raw, record = recovery.request('decisions', body, 'native')
                    again, cached = recovery.request('decisions', body, 'native')
                    self.assertEqual(http.call_count, 1)
                self.assertEqual((raw, again), (answer, answer))
                self.assertEqual(record['retry_of'], fingerprint)
                self.assertTrue(cached['cached'])
                self.assertEqual(budget.entries[fingerprint]['cost'], 1000000)
                self.assertEqual(len(budget.entries), 2)
                fresh = Client('synthetic', budget, root / 'fresh')
                with patch.object(fresh, 'http') as http:
                    self.assertEqual(fresh.request('decisions', body, 'native')[1]['retry_of'], fingerprint)
                    http.assert_not_called()

    def test_quota_recovery_cannot_clear_timeout_or_retry_failed_recovery(self):
        for failure in (TimeoutError('timed out'), RunBlocked('HTTP 429: {"error":{"code":"credit_balance_exhausted"}}')):
            with self.subTest(failure=str(failure)), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); body = {'input': 'synthetic'}
                fingerprint = hashlib.sha256(b'https://api.openai.com/v1/decisions\n' + json.dumps(body, sort_keys=True).encode()).hexdigest()
                with Budget(root / 'ledger', cap=5000000) as budget:
                    client = Client('synthetic', budget, root / 'calls', retry_rejected={fingerprint})
                    with patch.object(client, 'http', side_effect=failure) as http:
                        for _ in range(3):
                            with self.assertRaises(RunBlocked):client.request('decisions', body, 'native')
                        self.assertEqual(http.call_count, 1 if isinstance(failure, TimeoutError) else 2)

    def test_quota_code_must_be_structured_provider_error(self):
        self.assertTrue(credit_balance_rejection('HTTP 429: {"error":{"code":"credit_balance_exhausted"}}'))
        for error in ('HTTP 429: malformed', 'HTTP 500: {"error":{"code":"credit_balance_exhausted"}}',
                      'HTTP 429: {"code":"credit_balance_exhausted"}',
                      'HTTP 429: {"error":{"code":"rate_limit"},"message":{"code":"credit_balance_exhausted"}}'):
            self.assertFalse(credit_balance_rejection(error))

    def test_quota_recovery_cannot_dispatch_beyond_held_cap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); body = {'input': 'synthetic'}
            fingerprint = hashlib.sha256(b'https://api.openai.com/v1/decisions\n' + json.dumps(body, sort_keys=True).encode()).hexdigest()
            with Budget(root / 'ledger', cap=1500000) as budget:
                client = Client('synthetic', budget, root / 'calls', retry_rejected={fingerprint})
                failure = RunBlocked('HTTP 429: {"error":{"code":"credit_balance_exhausted"}}')
                with patch.object(client, 'http', side_effect=failure):
                    with self.assertRaises(RunBlocked):client.request('decisions', body, 'native')
                with patch.object(client, 'http') as http:
                    with self.assertRaisesRegex(RunBlocked, 'spending cap reached'):
                        client.request('decisions', body, 'native')
                    http.assert_not_called()
                self.assertEqual(len(budget.entries), 1)
                self.assertEqual(budget.used(), 1000000)
                budget.approve_cap(2500000, 'synthetic explicit approval')
                answer = {'usage': {'input_tokens': 100, 'output_tokens': 0, 'total_tokens': 100}}
                with patch.object(client, 'http', return_value=answer) as http:
                    client.request('decisions', body, 'native')
                    self.assertEqual(http.call_count, 1)

    def test_real_response_parser_accepts_rtl_only_for_matching_or_auto_direction(self):
        value = {'classification': 'panels', 'orientation': 'upright', 'reading_direction': 'rtl',
                 'panels': [{'order': 1, 'description': 'Right scene',
                             'bounds': {'top': 0, 'left': 600, 'bottom': 500, 'right': 1000}},
                            {'order': 2, 'description': 'Left scene',
                             'bounds': {'top': 0, 'left': 0, 'bottom': 500, 'right': 400}}]}
        raw = {'status': 'completed', 'output': [{'type': 'message', 'content': [
            {'type': 'output_text', 'text': json.dumps(value)}]}]}
        for direction in ('rtl', 'auto'):
            parsed = response_panels(raw, expected_direction=direction)
            self.assertEqual([p['box'][1] for p in parsed['panels']], [600, 0])
        with self.assertRaisesRegex(ValueError, 'reading direction'):response_panels(raw)

    def test_png_analysis_resumes_and_preceding_context_names_analysis_pixels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = []
            for number in range(1, 4):
                source = root / f'{number}.png'
                Image.new('RGBA', (40, 60), (0, 0, 0, 0)).save(source)
                analysis = prepare_analysis_image(source, root, number)
                before = sha(analysis)
                self.assertEqual(prepare_analysis_image(source, root, number), analysis)
                self.assertEqual(sha(analysis), before)
                with Image.open(analysis) as im:self.assertEqual(im.getpixel((10, 10)), (255, 255, 255))
                paths.append(analysis)
            context = source_page_context([{'image': str(p)} for p in paths], root)
            self.assertEqual(context[str(paths[2])], [str(p) for p in paths[:2]])
            paths[2].write_bytes(b'corrupt cache')
            with self.assertRaisesRegex(ValueError, 'cached pixels changed'):
                prepare_analysis_image(root / '3.png', root, 3)

    def test_large_verifier_reserves_full_output_allowance_before_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            body = {'model': 'gpt-6-astra', 'max_output_tokens': 17408,
                    'input': [], 'text': {}, 'reasoning': {'effort': 'high'}}
            with Budget(root / 'ledger', cap=5000000) as budget:
                client = Client('synthetic-no-key', budget, root / 'calls')
                def http(endpoint, _body):
                    if endpoint == 'responses/input_tokens':
                        self.assertEqual(budget.used(), 0)
                        return {'input_tokens': 100}
                    self.assertEqual(budget.used(), 60000 * 12.5 + 17408 * 50)
                    return {'usage': {'input_tokens': 100, 'output_tokens': 17000, 'total_tokens': 17100}}
                with patch.object(client, 'http', side_effect=http):
                    client.request('responses', body, 'verifier')
                self.assertEqual(budget.used(), 100 * 12.5 + 17000 * 50)
                body['max_output_tokens'] = 1000000
                with patch.object(client, 'http') as dispatch:
                    with self.assertRaisesRegex(RunBlocked, 'output allowance'):
                        client.request('responses', body, 'verifier')
                    dispatch.assert_not_called()

    def test_publication_import_preserves_order_pixels_and_resumes_without_conversion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'source'; source.mkdir()
            Image.new('RGB', (80, 120), 'red').save(source / 'page2.bmp')
            Image.new('RGBA', (80, 120), (0, 0, 255, 0)).save(source / 'page10.png')
            (source / 'notes.txt').write_text('source attribution')
            before = {p.name: sha(p) for p in source.iterdir()}
            result = prepare_input(source, root / 'work', None)
            self.assertEqual([r['locator'] for r in result['pages']], ['page2.bmp', 'page10.png'])
            self.assertEqual([r['image'] for r in result['pages']], ['0001.png', '0002.png'])
            self.assertEqual(result['pages'][1]['sha256'], before['page10.png'])
            self.assertEqual((root / 'work/pages/source-auxiliary/notes.txt').read_text(), 'source attribution')
            self.assertEqual({p.name: sha(p) for p in source.iterdir()}, before)
            with patch('auto_convert.prepare_publication_image', side_effect=AssertionError('must reuse prepared pixels')):
                self.assertEqual(prepare_input(source, root / 'work', None), result)

    def test_refining_a_repair_does_not_compound_reading_margin(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); page = root / 'page.jpg'
            Image.new('RGB', (1000, 1500), 'white').save(page)
            converter = Converter(None, root, reading_margin=True, reading_direction='rtl')
            proposal = {'tier': 'astra', 'panels': {'classification': 'panels',
                'orientation': 'upright', 'reading_direction': 'rtl', 'panels': [
                    {'order': 1, 'box': [100, 600, 400, 950], 'description': 'Right scene'},
                    {'order': 2, 'box': [100, 50, 400, 450], 'description': 'Left scene'}]}}
            original = copy.deepcopy(proposal)
            first = converter.refine(page, proposal)
            self.assertEqual(proposal, original)
            self.assertTrue(first['viewport_padding_applied'])
            self.assertNotEqual(first['panels'], original['panels'])
            repair = {**first, 'repair_of': first['identity']}
            second = converter.refine(page, repair)
            self.assertEqual(second['panels'], first['panels'])
            self.assertEqual(second['identity'], first['identity'])
            self.assertEqual(second['panels']['reading_direction'], 'rtl')
            self.assertNotIn('description', converter.bundles[first['identity']]['panels'][0])

    def test_explicit_ltr_keeps_legacy_request_and_rtl_cannot_silently_flip(self):
        class Capture:
            def __init__(self): self.body = None
            def request(self, endpoint, body, kind):
                self.body = body
                return {}, {'request_id': 'synthetic'}

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); page = root / 'source.jpg'
            Image.new('RGB', (80, 120), 'white').save(page)
            value = {'classification': 'whole_page', 'orientation': 'upright',
                'reading_direction': 'ltr', 'panels': [{'order': 1, 'box': [0, 0, 1000, 1000], 'description': 'Cover'}]}
            client = Capture()
            with patch('auto_convert.response_panels', return_value=value):
                legacy = Converter(client, root, reading_direction='ltr').detect(page, 'sol-low')
                self.assertNotIn('invalid', legacy)
                self.assertEqual(client.body['input'][0]['content'][0]['text'], (HERE / 'prompt-v6.txt').read_text())
                rtl = Converter(client, root, reading_direction='rtl').detect(page, 'sol-low')
                self.assertIn('reading direction', rtl['invalid'])
                self.assertIn('This book reads right-to-left.', client.body['input'][0]['content'][0]['text'])
                auto = Converter(client, root, reading_direction='auto').detect(page, 'sol-low')
                self.assertNotIn('invalid', auto)
                self.assertEqual(client.body['input'][0]['content'][0]['text'], (HERE / 'prompt-v7-direction.txt').read_text())


if __name__ == '__main__': unittest.main()
