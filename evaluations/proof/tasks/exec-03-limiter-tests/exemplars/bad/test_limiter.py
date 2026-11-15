import unittest

from limiter.window import Limiter


class LimiterTest(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.limiter = Limiter(3, 10, lambda: self.now)

    def test_allows_up_to_the_limit(self):
        for _ in range(3):
            self.assertTrue(self.limiter.allow('a'))
        self.assertFalse(self.limiter.allow('a'))

    def test_window_expires(self):
        self.limiter.allow('a', 3)
        self.now = 9
        self.assertFalse(self.limiter.allow('a'))
        self.now = 10
        self.assertTrue(self.limiter.allow('a'))

    def test_remaining(self):
        self.limiter.allow('a', 2)
        self.assertEqual(self.limiter.remaining('a'), 1)

    def test_retry_after(self):
        self.assertEqual(self.limiter.retry_after('a'), 0)
        self.limiter.allow('a', 3)
        self.now = 4
        self.assertEqual(self.limiter.retry_after('a'), 6)

    def test_keys_are_independent(self):
        self.limiter.allow('a', 3)
        self.assertTrue(self.limiter.allow('b'))

    def test_reset(self):
        self.limiter.allow('a', 3)
        self.limiter.reset('a')
        self.assertNotIn('a', self.limiter._hits)
        self.assertTrue(self.limiter.allow('a'))

    def test_invalid_arguments(self):
        with self.assertRaisesRegex(ValueError, 'limit'):
            Limiter(0, 10, lambda: 0)
        with self.assertRaises(ValueError):
            Limiter(3, 0, lambda: 0)
        with self.assertRaises(ValueError):
            self.limiter.allow('a', 0)


if __name__ == '__main__':
    unittest.main()
