"""Research spend limits must count unknown holds and preserve the shared cap."""
import tempfile
import unittest
from pathlib import Path

from generate import Budget, OUTPUT, SpikeBudget


class OwnershipBudgetContract(unittest.TestCase):
    def test_unknown_holds_block_third_call_before_reservation(self):
        with tempfile.TemporaryDirectory() as work:
            with SpikeBudget(Path(work)/'ledger.jsonl', cap=100000000) as budget:
                budget.reserve('a', OUTPUT/'calls/a', 700000, 12.5, 50)
                budget.reserve('b', OUTPUT/'calls/b', 700000, 12.5, 50)
                with self.assertRaisesRegex(ValueError, 'spike'):
                    budget.reserve('c', OUTPUT/'calls/c', 700000, 12.5, 50)
                self.assertEqual(set(budget.entries), {'a', 'b'})
                self.assertEqual(budget.used(), 1400000)

    def test_other_experiments_count_toward_global_not_local_limit(self):
        with tempfile.TemporaryDirectory() as work:
            with SpikeBudget(Path(work)/'ledger.jsonl', cap=100000000) as budget:
                Budget.reserve(budget, 'older', OUTPUT.parent/'other/calls/older', 99500000, 1, 1)
                with self.assertRaisesRegex(ValueError, 'spending cap'):
                    budget.reserve('new', OUTPUT/'calls/new', 700000, 12.5, 50)
                self.assertEqual(set(budget.entries), {'older'})


if __name__ == '__main__':
    unittest.main()
