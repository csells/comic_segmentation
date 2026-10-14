import tempfile
import unittest
import json
from pathlib import Path
from gemini_budget import Budget, usage_cost
from gemini_probe import prior_request


class BudgetTests(unittest.TestCase):
    def test_fractional_model_rates_are_not_rounded_before_multiplication(self):
        self.assertEqual(usage_cost({'promptTokenCount':1000,'totalTokenCount':3000}, .125, .5),1125)
        self.assertEqual(usage_cost({'promptTokenCount':1,'totalTokenCount':1}, .125, .5),1)

    def test_explicit_cap_amendment_retains_old_reservations_and_model_rates(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'budget.jsonl'
            with Budget(path,cap=10000000) as budget:
                budget.reserve('flash','one')
                budget.approve_cap(20000000,'User explicitly approved $20')
            with Budget(path,cap=20000000) as budget:
                self.assertEqual(budget.used(),300000)
                budget.reserve('pro','two',750000,1.25,10.0)
                budget.settle('pro',{'promptTokenCount':2000,'totalTokenCount':4000})
                self.assertEqual(budget.used(),322500)

    def test_retry_never_replays_success_unknown_or_exhausted_request(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            entries={'a':{'path':str(base)}}
            with self.assertRaises(ValueError):
                prior_request(entries,'a',True)
            (base/'result.json').write_text(json.dumps({'error':'HTTP 503: busy'}))
            with self.assertRaises(ValueError):
                prior_request(entries,'a',False)
            self.assertEqual(prior_request(entries,'a',True),('a:retry1',None))
            entries['a:retry1']={'path':str(base)}
            with self.assertRaises(ValueError):
                prior_request(entries,'a',True)
            (base/'panels.json').write_text('{}')
            self.assertEqual(prior_request(entries,'a',True),('a',base))

    def test_reservation_survives_restart_and_blocks_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'budget.jsonl'
            with Budget(path, cap=300000) as budget:
                budget.reserve('a', 'request-a')
            with Budget(path, cap=300000) as budget:
                self.assertEqual(budget.used(), 300000)
                with self.assertRaises(ValueError):
                    budget.reserve('a', 'request-a')
                with self.assertRaises(ValueError):
                    budget.reserve('b', 'request-b')

    def test_settlement_releases_only_reported_usage(self):
        with tempfile.TemporaryDirectory() as temp:
            with Budget(Path(temp) / 'budget.jsonl', cap=310000) as budget:
                budget.reserve('a', 'request-a')
                budget.settle('a', {'promptTokenCount': 2000, 'totalTokenCount': 4000})
                self.assertEqual(budget.used(), 9000)
                budget.reserve('b', 'request-b')
                budget.settle('b', {})
                self.assertEqual(budget.used(), 309000)

    def test_missing_invalid_or_over_reservation_usage_is_not_free(self):
        self.assertIsNone(usage_cost({}))
        for usage in ({'promptTokenCount': True,'totalTokenCount': 4},
                      {'promptTokenCount': 5,'totalTokenCount': 4}):
            with self.assertRaises(ValueError):
                usage_cost(usage)
        with tempfile.TemporaryDirectory() as temp:
            with Budget(Path(temp) / 'budget.jsonl') as budget:
                budget.reserve('a', 'request-a')
                with self.assertRaises(ValueError):
                    budget.settle('a', {'promptTokenCount': 2000,'totalTokenCount': 1000000})
                self.assertEqual(budget.used(), 300000)

    def test_existing_cap_cannot_silently_change(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'budget.jsonl'
            with Budget(path, cap=300000):
                pass
            with self.assertRaises(ValueError):
                with Budget(path, cap=10000000):
                    pass


if __name__ == '__main__':
    unittest.main()
