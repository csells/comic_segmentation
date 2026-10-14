"""Transport-only failure tests. Run in staging with no credentials or network."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from auto_convert import Client, POLICY, TRANSPORT_POLICY, transient_server_rejection
from automatic_escalation import RunBlocked
from gemini_budget import Budget


ERROR = 'HTTP 503: {"error":{"message":"Inference unavailable.","type":"server_error","param":null,"code":null}}'
ANSWER = {'usage': {'input_tokens': 100, 'output_tokens': 0, 'total_tokens': 100}}
BODY = {'input': 'synthetic transport guard; no comic or real request'}


def fingerprint(body=BODY):
    return hashlib.sha256(b'https://api.openai.com/v1/decisions\n' + json.dumps(body, sort_keys=True).encode()).hexdigest()


def recovery_id(original=None, kind='transient-server'):
    return hashlib.sha256(('explicit-' + kind + '-recovery-1:' + (original or fingerprint())).encode()).hexdigest()


class TransientRecoveryTests(unittest.TestCase):
    def setUp(self):
        # Even a test mistake cannot reach the provider through Client.http.
        self.network = patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden'))
        self.network.start(); self.addCleanup(self.network.stop)
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.budget = Budget(self.root / 'ledger.jsonl', cap=5_000_000).__enter__()
        self.addCleanup(self.budget.__exit__)

    def client(self, name='calls', **kwargs):
        return Client('synthetic-not-a-credential', self.budget, self.root / name, **kwargs)

    def fail_original(self, error=ERROR):
        client = self.client('original')
        with patch.object(client, 'http', side_effect=RunBlocked(error)) as http:
            with self.assertRaises(RunBlocked):client.request('decisions', BODY, 'native')
            self.assertEqual(http.call_count, 1)
        return Path(self.budget.entries[fingerprint()]['path'])

    def test_structured_503_is_narrow_and_not_specific_to_provider_message(self):
        self.assertEqual(POLICY, 'automatic-marked-target-completeness-v63')
        self.assertEqual(TRANSPORT_POLICY, 'explicit-connection-recovery-v6')
        self.assertTrue(transient_server_rejection(ERROR))
        self.assertTrue(transient_server_rejection(ERROR.replace('Inference unavailable.', 'Different temporary outage.')))
        for error in (None, {}, 'HTTP 503: unavailable', ERROR.replace('503', '500'),
                      ERROR.replace('503', '429'), ERROR.replace('server_error', 'invalid_request_error'),
                      ERROR.replace('"code":null', '"code":"rate_limit"'),
                      ERROR.replace('"param":null,', ''), ERROR.replace(',"code":null', ''),
                      ERROR.replace('Inference unavailable.', ' '), 'HTTP 503: []',
                      'HTTP 503: {"message":"server_error","error":null}', 'timed out'):
            with self.subTest(error=error):self.assertFalse(transient_server_rejection(error))

    def test_no_automatic_recovery_even_after_known_503(self):
        self.fail_original()
        client = self.client('normal')
        with patch.object(client, 'http') as http:
            with self.assertRaisesRegex(RunBlocked, 'no automatic replay'):
                client.request('decisions', BODY, 'native')
            http.assert_not_called()
        self.assertEqual((len(self.budget.entries), self.budget.used()), (1, 1_000_000))

    def test_exact_once_reservation_same_body_and_cache_across_clients(self):
        original = self.fail_original()
        unchanged = {name: (original / name).read_bytes() for name in ('request.json', 'error.json')}
        client = self.client('recovery', retry_transient={fingerprint()})
        def respond(endpoint, body):
            self.assertEqual((endpoint, body), ('decisions', BODY))
            self.assertIn(recovery_id(), self.budget.entries)
            self.assertEqual(self.budget.used(), 2_000_000)  # Both holds exist before dispatch.
            return ANSWER
        with patch.object(client, 'http', side_effect=respond) as http:
            raw, record = client.request('decisions', BODY, 'native')
            again, cached = client.request('decisions', BODY, 'native')
            self.assertEqual(http.call_count, 1)
        self.assertEqual((raw, again), (ANSWER, ANSWER))
        self.assertEqual(record['request_id'], recovery_id())
        self.assertEqual(record['retry_of'], fingerprint())
        self.assertTrue(cached['cached'])
        request = json.loads((Path(record['path']) / 'request.json').read_text())
        self.assertEqual(request['request_fingerprint'], fingerprint())
        self.assertEqual(request['body_without_image_bytes'], BODY)
        self.assertEqual(self.budget.entries[fingerprint()]['cost'], 1_000_000)
        self.assertEqual(len(self.budget.entries), 2)
        for name, value in unchanged.items():self.assertEqual((original / name).read_bytes(), value)
        fresh = self.client('fresh')
        with patch.object(fresh, 'http') as http:
            self.assertEqual(fresh.request('decisions', BODY, 'native')[1]['request_id'], recovery_id())
            http.assert_not_called()

    def test_success_is_reused_despite_explicit_recovery_flag(self):
        first = self.client('success')
        with patch.object(first, 'http', return_value=ANSWER):first.request('decisions', BODY, 'native')
        recovered = self.client(retry_transient={fingerprint()})
        with patch.object(recovered, 'http') as http:
            self.assertTrue(recovered.request('decisions', BODY, 'native')[1]['cached'])
            http.assert_not_called()
        self.assertEqual(len(self.budget.entries), 1)

    def test_wrong_error_or_wrong_fingerprint_cannot_recover(self):
        self.fail_original('HTTP 503: {"error":{"type":"invalid_request_error"}}')
        client = self.client(retry_transient={fingerprint()})
        with patch.object(client, 'http') as http:
            with self.assertRaisesRegex(RunBlocked, 'structured HTTP 503'):
                client.request('decisions', BODY, 'native')
            http.assert_not_called()
        wrong = self.client('wrong', retry_transient={'0' * 64})
        with patch.object(wrong, 'http') as http:
            with self.assertRaisesRegex(RunBlocked, 'no automatic replay'):
                wrong.request('decisions', BODY, 'native')
            http.assert_not_called()

    def test_original_provenance_required(self):
        original = self.fail_original(); path = original / 'request.json'
        value = json.loads(path.read_text())
        for key, changed in (('retry_of', '0' * 64), ('request_id', '0' * 64),
                             ('request_fingerprint', '0' * 64), ('endpoint', 'responses'), ('kind', 'detector')):
            path.write_text(json.dumps({**value, key: changed}))
            client = self.client(retry_transient={fingerprint()})
            with self.subTest(key=key), patch.object(client, 'http') as http:
                with self.assertRaisesRegex(RunBlocked, 'original request provenance'):
                    client.request('decisions', BODY, 'native')
                http.assert_not_called()
        path.unlink()
        with patch.object(client, 'http') as http:
            with self.assertRaisesRegex(RunBlocked, 'original request provenance'):
                client.request('decisions', BODY, 'native')
            http.assert_not_called()

    def test_second_failure_blocks_every_recovery_type_and_recovery_fingerprint(self):
        self.fail_original()
        client = self.client(retry_transient={fingerprint()})
        with patch.object(client, 'http', side_effect=RunBlocked(ERROR)) as http:
            with self.assertRaises(RunBlocked):client.request('decisions', BODY, 'native')
            self.assertEqual(http.call_count, 1)
        options = ({}, {'retry_transient': {fingerprint()}}, {'retry_unknown': {fingerprint()}},
                   {'retry_rejected': {fingerprint()}}, {'retry_transient': {recovery_id()}})
        for kwargs in options:
            next_client = self.client(**kwargs)
            with self.subTest(kwargs=kwargs), patch.object(next_client, 'http') as http:
                with self.assertRaisesRegex(RunBlocked, 'no further replay'):
                    next_client.request('decisions', BODY, 'native')
                http.assert_not_called()
        self.assertEqual((len(self.budget.entries), self.budget.used()), (2, 2_000_000))

    def test_legacy_recovery_reservation_blocks_new_family(self):
        for kind in ('timeout', 'quota'):
            with self.subTest(kind=kind), Budget(self.root / (kind + '.jsonl'), cap=5_000_000) as budget:
                original = self.root / (kind + '-original'); original.mkdir()
                budget.reserve(fingerprint(), original, 1_000_000, .1, .5)
                identity = recovery_id(kind=kind); path = self.root / kind; path.mkdir()
                budget.reserve(identity, path, 1_000_000, .1, .5)
                client = Client('synthetic', budget, self.root / (kind + '-new'), retry_transient={fingerprint()})
                with patch.object(client, 'http') as http:
                    with self.assertRaisesRegex(RunBlocked, 'no further replay'):
                        client.request('decisions', BODY, 'native')
                    http.assert_not_called()
                self.assertEqual(len(budget.entries), 2)

    def test_ambiguous_recovery_flags_rejected(self):
        for other in ('retry_unknown', 'retry_rejected'):
            with self.assertRaisesRegex(ValueError, 'Ambiguous recovery'):
                self.client(retry_transient={fingerprint()}, **{other: {fingerprint()}})

    def test_cap_counts_original_hold_and_prevents_new_dispatch(self):
        self.fail_original(); self.budget.approve_cap(1_999_999, 'synthetic test cap')
        client = self.client(retry_transient={fingerprint()})
        with patch.object(client, 'http') as http:
            with self.assertRaisesRegex(RunBlocked, 'spending cap reached'):
                client.request('decisions', BODY, 'native')
            http.assert_not_called()
        self.assertEqual((len(self.budget.entries), self.budget.used()), (1, 1_000_000))

    def test_shared_client_threads_cannot_dispatch_duplicate_recovery(self):
        self.fail_original()
        client = self.client(retry_transient={fingerprint()})
        entered = threading.Event(); release = threading.Event()
        def respond(endpoint, body):
            entered.set(); self.assertTrue(release.wait(3)); return ANSWER
        with patch.object(client, 'http', side_effect=respond) as http, ThreadPoolExecutor(3) as pool:
            first = pool.submit(client.request, 'decisions', BODY, 'native')
            self.assertTrue(entered.wait(3))
            others = [pool.submit(client.request, 'decisions', BODY, 'native') for _ in range(2)]
            try:
                for pending in others:
                    with self.assertRaisesRegex(RunBlocked, 'no further replay'):pending.result(timeout=3)
            finally:release.set()
            self.assertFalse(first.result(timeout=3)[1]['cached'])
            self.assertEqual(http.call_count, 1)
        self.assertEqual(len(self.budget.entries), 2)

    def test_ledger_file_lock_prevents_second_owner_and_durable_reopen_reuses_success(self):
        with self.assertRaises(BlockingIOError):
            with Budget(self.budget.path, cap=5_000_000):pass
        self.fail_original()
        client = self.client(retry_transient={fingerprint()})
        with patch.object(client, 'http', return_value=ANSWER):client.request('decisions', BODY, 'native')
        self.budget.__exit__()
        with Budget(self.budget.path, cap=5_000_000) as reopened:
            fresh = Client('synthetic', reopened, self.root / 'durable')
            with patch.object(fresh, 'http') as http:
                self.assertTrue(fresh.request('decisions', BODY, 'native')[1]['cached'])
                http.assert_not_called()
            self.assertEqual(reopened.entries[fingerprint()]['cost'], 1_000_000)
            self.assertEqual(len(reopened.entries), 2)


if __name__ == '__main__':unittest.main()


class InterruptedRecoveryTests(unittest.TestCase):
    setUp = TransientRecoveryTests.setUp
    client = TransientRecoveryTests.client

    def interrupted(self):
        client = self.client('interrupted')
        with patch.object(client, 'http', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):client.request('decisions', BODY, 'native')
        original = Path(self.budget.entries[fingerprint()]['path'])
        evidence = {'kind':'confirmed_process_loss', 'request_id':fingerprint(),
                    'request_sha256':hashlib.sha256((original/'request.json').read_bytes()).hexdigest(),
                    'process_not_running':True, 'observed_at':'2026-10-12T00:00:00Z',
                    'evidence':'Synthetic process exited before saving a response.'}
        (original/'interruption.json').write_text(json.dumps(evidence))
        return original

    def test_confirmed_interruption_recovers_once_with_both_holds_and_reuses_cache(self):
        original=self.interrupted(); saved=(original/'request.json').read_bytes()
        client=self.client('recovery',retry_interrupted={fingerprint()})
        def respond(endpoint,body):
            self.assertEqual((endpoint,body),('decisions',BODY))
            self.assertEqual(self.budget.used(),2_000_000)
            return ANSWER
        with patch.object(client,'http',side_effect=respond) as http:
            _,meta=client.request('decisions',BODY,'native');self.assertEqual(http.call_count,1)
        self.assertEqual(meta['request_id'],recovery_id(kind='interruption'))
        self.assertEqual(meta['retry_of'],fingerprint())
        self.assertEqual(self.budget.entries[fingerprint()]['cost'],1_000_000)
        self.assertEqual((original/'request.json').read_bytes(),saved)
        self.assertFalse((original/'error.json').exists())
        with patch.object(self.client('fresh'),'http',side_effect=AssertionError('no HTTP')):
            fresh=self.client('fresh2')
            with patch.object(fresh,'http') as http:
                self.assertTrue(fresh.request('decisions',BODY,'native')[1]['cached']);http.assert_not_called()

    def test_no_recovery_without_explicit_flag_and_bound_process_loss_evidence(self):
        original=self.interrupted();client=self.client()
        with patch.object(client,'http') as http:
            with self.assertRaisesRegex(RunBlocked,'no automatic replay'):client.request('decisions',BODY,'native')
            http.assert_not_called()
        path=original/'interruption.json';e=json.loads(path.read_text())
        for field,value in [('kind','timeout'),('request_id','0'*64),('request_sha256','0'*64),('process_not_running',False),('evidence','')]:
            path.write_text(json.dumps({**e,field:value}));client=self.client(retry_interrupted={fingerprint()})
            with self.subTest(field=field),patch.object(client,'http') as http:
                with self.assertRaisesRegex(RunBlocked,'confirmed process-loss evidence'):client.request('decisions',BODY,'native')
                http.assert_not_called()
        path.unlink();client=self.client(retry_interrupted={fingerprint()})
        with patch.object(client,'http') as http:
            with self.assertRaisesRegex(RunBlocked,'confirmed process-loss evidence'):client.request('decisions',BODY,'native')
            http.assert_not_called()

    def test_second_interruption_cannot_repeat_or_cross_recovery_family(self):
        self.interrupted();client=self.client('recovery',retry_interrupted={fingerprint()})
        with patch.object(client,'http',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):client.request('decisions',BODY,'native')
        for option in ({},{'retry_interrupted':{fingerprint()}},{'retry_unknown':{fingerprint()}},{'retry_transient':{fingerprint()}}):
            client=self.client(**option)
            with patch.object(client,'http') as http:
                with self.assertRaisesRegex(RunBlocked,'no further replay'):client.request('decisions',BODY,'native')
                http.assert_not_called()
        self.assertEqual(self.budget.used(),2_000_000)

    def test_interruption_flag_cannot_overlap_or_bypass_budget(self):
        self.interrupted()
        with self.assertRaisesRegex(ValueError,'Ambiguous recovery'):
            self.client(retry_interrupted={fingerprint()},retry_unknown={fingerprint()})
        self.budget.approve_cap(1_999_999,'synthetic test cap')
        client=self.client(retry_interrupted={fingerprint()})
        with patch.object(client,'http') as http:
            with self.assertRaisesRegex(RunBlocked,'spending cap reached'):client.request('decisions',BODY,'native')
            http.assert_not_called()


class NetworkRecoveryTests(unittest.TestCase):
    setUp = TransientRecoveryTests.setUp
    client = TransientRecoveryTests.client
    fail_original = TransientRecoveryTests.fail_original

    def test_connection_failure_recovery_preserves_hold_and_replays_success(self):
        error='<urlopen error [Errno 101] Network is unreachable>'
        original=self.fail_original(error);saved=(original/'error.json').read_bytes()
        client=self.client('recovery',retry_transient={fingerprint()})
        with patch.object(client,'http',return_value=ANSWER) as http:
            _,meta=client.request('decisions',BODY,'native')
            self.assertEqual(http.call_count,1)
        self.assertEqual(meta['retry_of'],fingerprint())
        self.assertEqual(self.budget.entries[fingerprint()]['cost'],1_000_000)
        self.assertEqual((original/'error.json').read_bytes(),saved)
        fresh=self.client('fresh')
        with patch.object(fresh,'http') as http:
            self.assertTrue(fresh.request('decisions',BODY,'native')[1]['cached']);http.assert_not_called()

    def test_connection_failure_classifier_is_narrow(self):
        from auto_convert import transient_network_failure
        for number,message in [(101,'Network is unreachable'),(113,'No route to host'),(111,'Connection refused'),(100,'Network is down')]:
            self.assertTrue(transient_network_failure(f'<urlopen error [Errno {number}] {message}>'))
        for value in [None,'timed out','HTTP 401: Network is unreachable','<urlopen error certificate verify failed>',
                      '<urlopen error [Errno 5] Network is unreachable>','<urlopen error [Errno 101] certificate verify failed>']:
            self.assertFalse(transient_network_failure(value))

    def test_connection_failure_is_never_automatically_replayed(self):
        self.fail_original('<urlopen error [Errno 101] Network is unreachable>')
        client=self.client()
        with patch.object(client,'http') as http:
            with self.assertRaisesRegex(RunBlocked,'no automatic replay'):client.request('decisions',BODY,'native')
            http.assert_not_called()

    def test_remote_disconnect_recovery_preserves_hold_and_replays_success(self):
        # A relay or connection drop after upload; provider outcome unknown, so the original hold stays.
        from http.client import RemoteDisconnected
        original_client=self.client('original')
        with patch.object(original_client,'http',side_effect=RemoteDisconnected('Remote end closed connection without response')):
            with self.assertRaises(RunBlocked):original_client.request('decisions',BODY,'native')
        original=Path(self.budget.entries[fingerprint()]['path'])
        self.assertEqual(json.loads((original/'error.json').read_text())['error'],'Remote end closed connection without response')
        client=self.client('recovery',retry_transient={fingerprint()})
        with patch.object(client,'http',return_value=ANSWER) as http:
            _,meta=client.request('decisions',BODY,'native')
            self.assertEqual(http.call_count,1)
        self.assertEqual(meta['retry_of'],fingerprint())
        self.assertEqual(self.budget.entries[fingerprint()]['cost'],1_000_000)
        fresh=self.client('fresh')
        with patch.object(fresh,'http') as http:
            self.assertTrue(fresh.request('decisions',BODY,'native')[1]['cached']);http.assert_not_called()

    def test_remote_disconnect_classifier_is_exact(self):
        from auto_convert import transient_network_failure
        self.assertTrue(transient_network_failure('Remote end closed connection without response'))
        for value in ['Remote end closed connection','remote end closed connection without response',
                      'HTTP 500: Remote end closed connection without response','The read operation timed out']:
            self.assertFalse(transient_network_failure(value))


EDGE_RESET = 'HTTP 503: upstream connect error or disconnect/reset before headers. reset reason: connection termination'


def second_id(original=None):
    return hashlib.sha256(('explicit-second-transient-recovery-1:' + (original or fingerprint())).encode()).hexdigest()


class SecondRecoveryTests(unittest.TestCase):
    setUp = TransientRecoveryTests.setUp
    client = TransientRecoveryTests.client
    fail_original = TransientRecoveryTests.fail_original

    def fail_first_recovery(self, error=EDGE_RESET):
        self.fail_original('Remote end closed connection without response')
        client = self.client('first', retry_transient={fingerprint()})
        with patch.object(client, 'http', side_effect=RunBlocked(error)) as http:
            with self.assertRaises(RunBlocked):client.request('decisions', BODY, 'native')
            self.assertEqual(http.call_count, 1)
        return Path(self.budget.entries[recovery_id()]['path'])

    def test_edge_reset_503_is_exact_transient(self):
        self.assertTrue(transient_server_rejection(EDGE_RESET))
        for value in (EDGE_RESET.replace('503', '502'), EDGE_RESET.replace('connection termination', 'overflow'),
                      'HTTP 503: upstream connect error or disconnect/reset before headers.'):
            with self.subTest(value=value):self.assertFalse(transient_server_rejection(value))

    def test_second_recovery_keeps_all_holds_dispatches_once_and_replays(self):
        self.fail_first_recovery()
        client = self.client('second', retry_second={fingerprint()})
        def respond(endpoint, body):
            self.assertEqual((endpoint, body), ('decisions', BODY))
            self.assertEqual(self.budget.used(), 3_000_000)  # Original, first recovery and second hold.
            return ANSWER
        with patch.object(client, 'http', side_effect=respond) as http:
            raw, record = client.request('decisions', BODY, 'native')
            self.assertEqual(http.call_count, 1)
        self.assertEqual((raw, record['request_id'], record['retry_of']), (ANSWER, second_id(), fingerprint()))
        request = json.loads((Path(record['path']) / 'request.json').read_text())
        self.assertEqual((request['request_fingerprint'], request['retry_of']), (fingerprint(), fingerprint()))
        for identity in (fingerprint(), recovery_id()):self.assertEqual(self.budget.entries[identity]['cost'], 1_000_000)
        fresh = self.client('fresh')
        with patch.object(fresh, 'http') as http:
            self.assertEqual(fresh.request('decisions', BODY, 'native')[1]['request_id'], second_id())
            http.assert_not_called()

    def test_second_recovery_requires_explicit_flag(self):
        self.fail_first_recovery()
        for kwargs in ({}, {'retry_transient': {fingerprint()}}, {'retry_second': {'0' * 64}}):
            client = self.client(**kwargs)
            with self.subTest(kwargs=kwargs), patch.object(client, 'http') as http:
                with self.assertRaisesRegex(RunBlocked, 'no further replay'):client.request('decisions', BODY, 'native')
                http.assert_not_called()
        self.assertEqual(len(self.budget.entries), 2)

    def test_second_recovery_requires_transient_first_failure_and_provenance(self):
        first = self.fail_first_recovery('HTTP 400: bad request')
        client = self.client(retry_second={fingerprint()})
        with patch.object(client, 'http') as http:
            with self.assertRaisesRegex(RunBlocked, 'transient failure of the first recovery'):
                client.request('decisions', BODY, 'native')
            http.assert_not_called()
        (first / 'error.json').write_text(json.dumps({'error': EDGE_RESET}))
        path = first / 'request.json'; value = json.loads(path.read_text())
        for key in ('request_id', 'request_fingerprint', 'retry_of'):
            path.write_text(json.dumps({**value, key: '0' * 64}))
            with self.subTest(key=key), patch.object(client, 'http') as http:
                with self.assertRaisesRegex(RunBlocked, 'first recovery provenance'):client.request('decisions', BODY, 'native')
                http.assert_not_called()
        self.assertEqual(len(self.budget.entries), 2)

    def test_failed_second_recovery_is_final(self):
        self.fail_first_recovery()
        client = self.client('second', retry_second={fingerprint()})
        with patch.object(client, 'http', side_effect=RunBlocked(EDGE_RESET)):
            with self.assertRaises(RunBlocked):client.request('decisions', BODY, 'native')
        for kwargs in ({}, {'retry_second': {fingerprint()}}, {'retry_transient': {fingerprint()}}):
            next_client = self.client(**kwargs)
            with self.subTest(kwargs=kwargs), patch.object(next_client, 'http') as http:
                with self.assertRaisesRegex(RunBlocked, 'second recovery also unknown; no further replay'):
                    next_client.request('decisions', BODY, 'native')
                http.assert_not_called()
        self.assertEqual((len(self.budget.entries), self.budget.used()), (3, 3_000_000))

    def test_second_flag_overlap_is_ambiguous(self):
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            self.client(retry_transient={fingerprint()}, retry_second={fingerprint()})


class PageSpendLimitTests(unittest.TestCase):
    """V59: an optional per-page spend limit stops new paid calls; cached answers stay free."""
    setUp = TransientRecoveryTests.setUp

    def test_limit_charges_cached_answers_like_a_cold_first_pass(self):
        # V63: a cached answer costs nothing now but is charged its recorded cost, so the page makes the
        # same limit decisions it would make on a cold first pass.
        from automatic_escalation import PageBudgetExhausted
        client = Client('synthetic-not-a-credential', self.budget, self.root / 'calls', page_cap=5)
        client.start_page()
        with patch.object(client, 'http', return_value=ANSWER):
            client.request('decisions', BODY, 'native')
        paid = client.page_spent; self.assertGreaterEqual(paid, 5)
        with patch.object(client, 'http') as http:
            with self.assertRaisesRegex(PageBudgetExhausted, 'page spend limit reached'):
                client.request('decisions', BODY, 'native')
            http.assert_not_called()
        client.start_page()
        with patch.object(client, 'http') as http:
            self.assertTrue(client.request('decisions', BODY, 'native')[1]['cached'])
            http.assert_not_called()
        self.assertEqual(client.page_spent, paid)
        with self.assertRaisesRegex(PageBudgetExhausted, 'page spend limit reached'):
            client.request('decisions', {'input': 'another synthetic body'}, 'native')

    def test_no_limit_means_cache_is_free_and_unbounded(self):
        client = Client('synthetic-not-a-credential', self.budget, self.root / 'calls')
        with patch.object(client, 'http', return_value=ANSWER):client.request('decisions', BODY, 'native')
        with patch.object(client, 'http') as http:
            for _ in range(3):self.assertTrue(client.request('decisions', BODY, 'native')[1]['cached'])
            http.assert_not_called()

    def test_reservations_held_by_parallel_calls_do_not_trip_the_limit(self):
        # V60 regression: V59 counted held reservations ($1 per decision call), so parallel checks
        # tripped a $0.50 limit after about a cent of real spend.
        client = Client('synthetic-not-a-credential', self.budget, self.root / 'calls', page_cap=500_000)
        client.start_page()
        held = self.root / 'held'; held.mkdir()
        self.budget.reserve('f' * 64, held, 1_000_000, .1, .5)  # an in-flight sibling call's hold
        with patch.object(client, 'http', return_value=ANSWER) as http:
            client.request('decisions', BODY, 'native')
            self.assertEqual(http.call_count, 1)
        self.assertLess(client.page_spent, 500_000)

    def test_unsettled_failure_counts_its_full_reservation(self):
        from automatic_escalation import PageBudgetExhausted
        client = Client('synthetic-not-a-credential', self.budget, self.root / 'calls', page_cap=500_000)
        client.start_page()
        with patch.object(client, 'http', side_effect=RunBlocked('HTTP 500: synthetic')):
            with self.assertRaises(RunBlocked):client.request('decisions', BODY, 'native')
        self.assertEqual(client.page_spent, 1_000_000)
        with self.assertRaises(PageBudgetExhausted):client.request('decisions', {'input': 'other'}, 'native')

    def test_final_completeness_grace_extends_limit_only_while_set(self):
        from automatic_escalation import PageBudgetExhausted
        from auto_convert import PAGE_GRACE
        client = Client('synthetic-not-a-credential', self.budget, self.root / 'calls', page_cap=500_000)
        client.start_page(); client.page_spent = 600_000
        with self.assertRaises(PageBudgetExhausted):client.request('decisions', BODY, 'native')
        client.page_grace = True
        with patch.object(client, 'http', return_value=ANSWER) as http:
            client.request('decisions', BODY, 'native'); self.assertEqual(http.call_count, 1)
        client.page_spent = 500_000 + PAGE_GRACE
        with self.assertRaises(PageBudgetExhausted):client.request('decisions', {'input': 'other'}, 'native')
        client.start_page(); self.assertFalse(client.page_grace); self.assertEqual(client.page_remaining(), 500_000)

    def test_invalid_limit_rejected_and_none_means_unlimited(self):
        with self.assertRaises(ValueError):
            Client('synthetic', self.budget, self.root / 'c', page_cap=0)
        client = Client('synthetic', self.budget, self.root / 'c')
        self.assertIsNone(client.page_cap)


GATEWAY_502 = 'HTTP 502: <html>\r\n<head><title>502 Bad Gateway</title></head>\r\n<body>\r\n<center><h1>502 Bad Gateway</h1></center>\r\n<hr><center>cloudflare</center>\r\n</body>\r\n</html>\r\n'


class AutomaticTransientRecoveryTests(unittest.TestCase):
    """V62: optional single automatic recovery of recorded transient transport or gateway failures."""
    setUp = TransientRecoveryTests.setUp

    def client(self, name='calls', **kwargs):
        return Client('synthetic-not-a-credential', self.budget, self.root / name, **kwargs)

    def test_gateway_classifier_is_narrow(self):
        from auto_convert import gateway_failure
        self.assertTrue(gateway_failure(GATEWAY_502))
        self.assertTrue(gateway_failure('HTTP 504: <html><head><title>504 Gateway Time-out</title></head></html>'))
        for value in ('HTTP 502: {"error":{"message":"bad"}}', 'HTTP 400: <html>Bad Gateway</html>',
                      'HTTP 502: plain text', 'HTTP 429: <html>Bad Gateway</html>', None):
            self.assertFalse(gateway_failure(value))

    def test_dispatch_failure_recovers_once_automatically_with_both_holds(self):
        client = self.client(auto_transient=True)
        answers = [RunBlocked(GATEWAY_502), ANSWER]
        def respond(endpoint, body):
            value = answers.pop(0)
            if isinstance(value, Exception): raise value
            return value
        with patch.object(client, 'http', side_effect=respond) as http:
            raw, meta = client.request('decisions', BODY, 'native')
            self.assertEqual(http.call_count, 2)
        self.assertEqual((raw, meta['retry_of'], meta['request_id']), (ANSWER, fingerprint(), recovery_id()))
        self.assertEqual(self.budget.entries[fingerprint()]['cost'], 1_000_000)

    def test_second_transient_failure_stops_and_disabled_by_default(self):
        client = self.client(auto_transient=True)
        with patch.object(client, 'http', side_effect=RunBlocked(GATEWAY_502)) as http:
            with self.assertRaises(RunBlocked):client.request('decisions', BODY, 'native')
            self.assertEqual(http.call_count, 2)
        plain = self.client('plain')
        with patch.object(plain, 'http') as http:
            with self.assertRaisesRegex(RunBlocked, 'no further replay'):plain.request('decisions', BODY, 'native')
            http.assert_not_called()

    def test_recorded_failure_from_an_earlier_run_recovers_on_resume(self):
        first = self.client('first')
        with patch.object(first, 'http', side_effect=RunBlocked(GATEWAY_502)):
            with self.assertRaises(RunBlocked):first.request('decisions', BODY, 'native')
        resumed = self.client('resumed', auto_transient=True)
        with patch.object(resumed, 'http', return_value=ANSWER) as http:
            self.assertEqual(resumed.request('decisions', BODY, 'native')[1]['retry_of'], fingerprint())
            self.assertEqual(http.call_count, 1)
        other = {'input': 'other synthetic'}
        with patch.object(first, 'http', side_effect=RunBlocked('HTTP 400: <html>Bad Request</html>')):
            with self.assertRaises(RunBlocked):first.request('decisions', other, 'native')
        with patch.object(resumed, 'http') as http:
            with self.assertRaisesRegex(RunBlocked, 'no automatic replay'):resumed.request('decisions', other, 'native')
            http.assert_not_called()
