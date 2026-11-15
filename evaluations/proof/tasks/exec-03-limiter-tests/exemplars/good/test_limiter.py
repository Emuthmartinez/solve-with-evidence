"""Tests that hold limiter.window.Limiter to SPEC.md. Each test name starts with its rule number.

    python3 test_limiter.py
"""
import unittest

from limiter.window import Limiter


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now


class LimiterTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()

    def limiter(self, limit=3, window=10):
        return Limiter(limit, window, self.clock)

    def test_r01_limit_must_be_an_int_above_zero(self):
        for limit in (0, -1, 2.5, '3', None, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                Limiter(limit, 10, self.clock)

    def test_r01_window_must_be_a_number_above_zero(self):
        for window in (0, -1, 0.0, float('nan'), '10', None, True):
            with self.subTest(window=window), self.assertRaises(ValueError):
                Limiter(3, window, self.clock)

    def test_r01_window_may_be_a_float(self):
        limiter = self.limiter(limit=1, window=0.5)
        self.assertIs(limiter.allow('k'), True)
        self.clock.now = 0.25
        self.assertEqual(limiter.remaining('k'), 0)
        self.clock.now = 0.75
        self.assertIs(limiter.allow('k'), True)

    def test_r02_allows_until_the_limit_is_spent(self):
        limiter = self.limiter(limit=3)
        for _ in range(3):
            self.assertIs(limiter.allow('k'), True)
        self.assertIs(limiter.allow('k'), False)

    def test_r02_a_call_spends_its_cost(self):
        limiter = self.limiter(limit=5)
        self.assertIs(limiter.allow('k', 2), True)
        self.assertEqual(limiter.remaining('k'), 3)
        self.assertIs(limiter.allow('k', cost=3), True)
        self.assertEqual(limiter.remaining('k'), 0)

    def test_r03_a_hit_leaves_at_exactly_t_plus_window(self):
        limiter = self.limiter(limit=2, window=10)
        self.clock.now = 3
        self.assertIs(limiter.allow('k', 2), True)
        self.clock.now = 12.5
        self.assertEqual(limiter.remaining('k'), 0)
        self.clock.now = 13
        self.assertIs(limiter.allow('k', 2), True)

    def test_r03_each_hit_leaves_on_its_own(self):
        limiter = self.limiter(limit=2, window=10)
        self.assertIs(limiter.allow('k'), True)
        self.clock.now = 6
        self.assertIs(limiter.allow('k'), True)
        self.clock.now = 11
        self.assertIs(limiter.allow('k'), True)
        self.assertEqual(limiter.remaining('k'), 0)

    def test_r04_a_denied_call_moves_no_hit(self):
        limiter = self.limiter(limit=2, window=10)
        self.assertIs(limiter.allow('k', 2), True)
        self.clock.now = 4
        self.assertIs(limiter.allow('k', 2), False)
        self.assertEqual(limiter.retry_after('k'), 6)
        self.clock.now = 11
        self.assertIs(limiter.allow('k', 2), True)

    def test_r04_a_denied_call_records_no_hit(self):
        limiter = self.limiter(limit=4)
        self.assertIs(limiter.allow('k', 2), True)
        self.assertIs(limiter.allow('k', 4), False)
        self.assertEqual(limiter.remaining('k'), 2)
        self.assertIs(limiter.allow('k', 2), True)

    def test_r05_cost_must_be_an_int_from_1_to_the_limit(self):
        limiter = self.limiter(limit=3)
        for cost in (0, -1, 4, 1.0, '1', None, True):
            with self.subTest(cost=cost):
                self.assertRaises(ValueError, limiter.allow, 'k', cost)
                self.assertRaises(ValueError, limiter.retry_after, 'k', cost)
        self.assertEqual(limiter.remaining('k'), 3)

    def test_r05_cost_may_equal_the_limit(self):
        limiter = self.limiter(limit=3, window=10)
        self.assertIs(limiter.allow('k', 3), True)
        self.assertEqual(limiter.retry_after('k', 3), 10)

    def test_r06_keys_are_independent(self):
        limiter = self.limiter(limit=1)
        self.assertIs(limiter.allow('a'), True)
        self.assertEqual(limiter.remaining('a'), 0)
        self.assertEqual(limiter.remaining('b'), 1)
        self.assertIs(limiter.allow('b'), True)

    def test_r06_keys_are_the_same_key_exactly_when_equal(self):
        limiter = self.limiter(limit=2)
        self.assertIs(limiter.allow(1), True)
        self.assertIs(limiter.allow(1.0), True)
        self.assertEqual(limiter.remaining(1), 0)
        self.assertEqual(limiter.remaining('1'), 2)
        self.assertEqual(limiter.remaining((1,)), 2)

    def test_r07_remaining_counts_only_hits_in_the_window(self):
        limiter = self.limiter(limit=3, window=10)
        self.assertEqual(limiter.remaining('k'), 3)
        self.assertIs(limiter.allow('k', 2), True)
        self.assertEqual(limiter.remaining('k'), 1)
        self.clock.now = 11
        self.assertEqual(limiter.remaining('k'), 3)

    def test_r07_remaining_changes_nothing(self):
        limiter = self.limiter(limit=1)
        for _ in range(3):
            self.assertEqual(limiter.remaining('k'), 1)
        self.assertIs(limiter.allow('k'), True)

    def test_r08_retry_after_is_zero_when_the_call_fits(self):
        limiter = self.limiter(limit=3)
        self.assertEqual(limiter.retry_after('k'), 0)
        self.assertEqual(limiter.retry_after('k', 3), 0)
        self.assertIs(limiter.allow('k', 2), True)
        self.assertEqual(limiter.retry_after('k'), 0)

    def test_r08_retry_after_waits_for_the_kth_oldest_hit(self):
        limiter = self.limiter(limit=3, window=10)
        for now in (0, 2, 4):
            self.clock.now = now
            self.assertIs(limiter.allow('k'), True)
        self.clock.now = 5
        self.assertEqual(limiter.retry_after('k'), 5)
        self.assertEqual(limiter.retry_after('k', 2), 7)
        self.assertEqual(limiter.retry_after('k', 3), 9)

    def test_r08_retry_after_changes_nothing(self):
        limiter = self.limiter(limit=1, window=10)
        self.assertIs(limiter.allow('k'), True)
        self.clock.now = 4
        for _ in range(3):
            self.assertEqual(limiter.retry_after('k'), 6)
        self.assertEqual(limiter.remaining('k'), 0)

    def test_r09_reset_forgets_that_key_only(self):
        limiter = self.limiter(limit=1)
        self.assertIs(limiter.allow('a'), True)
        self.assertIs(limiter.allow('b'), True)
        self.assertIsNone(limiter.reset('a'))
        self.assertEqual(limiter.remaining('a'), 1)
        self.assertEqual(limiter.remaining('b'), 0)

    def test_r09_reset_of_a_key_without_hits_is_not_an_error(self):
        limiter = self.limiter(limit=1)
        self.assertIsNone(limiter.reset('never seen'))
        self.assertEqual(limiter.remaining('never seen'), 1)

    def test_r10_limiters_sharing_a_clock_are_independent(self):
        one = Limiter(1, 10, self.clock)
        other = Limiter(1, 10, self.clock)
        self.assertIs(one.allow('k'), True)
        self.assertEqual(other.remaining('k'), 1)
        self.assertIs(other.allow('k'), True)


if __name__ == '__main__':
    unittest.main()
