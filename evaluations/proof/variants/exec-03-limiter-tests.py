"""Plausible mistakes for exec-03-limiter-tests. Each is the good exemplar's test file with one edit:
a test weakened until one faulty implementation survives, or a test that asserts more than SPEC.md states."""
TESTS = 'test_limiter.py'
SHIPPED = 'passes on the shipped implementation'
ERRORS = 'passes on a correct rewrite with other error text and internals'
FLOATS = 'passes on a correct rewrite that returns float waits'
READS = 'passes on a correct rewrite that reads the clock twice in a call'
AT_WINDOW_END = "        self.clock.now = 13\n        self.assertIs(limiter.allow('k', 2), True)\n"
AFTER_WINDOW = "        self.clock.now = 11\n        self.assertEqual(limiter.remaining('k'), 3)\n"
CATCHES = ['catches a limit of 0 that is accepted', 'catches one hit more than the limit',
           'catches a hit that still counts at exactly t + window', 'catches a denied call that moves recorded hits',
           'catches a denied call that records part of its cost', 'catches a cost above the limit that returns False',
           'catches keys compared as text', 'catches remaining that counts hits outside the window',
           'catches retry_after that waits for the newest hit', 'catches retry_after that waits only for the oldest hit',
           'catches reset that forgets every key', 'catches limiters on one clock that share hits']

VARIANTS = [
    ('a limit of 0 is never tried',
     {TESTS: [("for limit in (0, -1,", "for limit in (-1,")]},
     ['catches a limit of 0 that is accepted']),
    ('the limit is reached but the next call is never tried',
     {TESTS: [("        self.assertIs(limiter.allow('k'), False)\n", "")]},
     ['catches one hit more than the limit']),
    ('the window is checked after its end, not at it',
     {TESTS: [(AT_WINDOW_END, AT_WINDOW_END.replace('13', '13.5'))]},
     ['catches a hit that still counts at exactly t + window']),
    ('the denied call is made at the instant the hits were recorded',
     {TESTS: [("        self.clock.now = 4\n        self.assertIs(limiter.allow('k', 2), False)\n"
               "        self.assertEqual(limiter.retry_after('k'), 6)\n",
               "        self.assertIs(limiter.allow('k', 2), False)\n"
               "        self.assertEqual(limiter.retry_after('k'), 10)\n")]},
     ['catches a denied call that moves recorded hits']),
    ('only the return value of a denied call is checked',
     {TESTS: [("        self.assertEqual(limiter.remaining('k'), 2)\n        self.assertIs(limiter.allow('k', 2), True)\n", "")]},
     ['catches a denied call that records part of its cost']),
    ('a cost above the limit is never tried',
     {TESTS: [("for cost in (0, -1, 4, 1.0,", "for cost in (0, -1, 1.0,")]},
     ['catches a cost above the limit that returns False']),
    ('equal keys of two types and unequal keys with one text are never tried',
     {TESTS: [("limiter.allow(1.0)", "limiter.allow(1)"), ("limiter.remaining('1'), 2", "limiter.remaining('one'), 2")]},
     ['catches keys compared as text']),
    ('remaining is read only after allow has run at the later time',
     {TESTS: [(AFTER_WINDOW, "        self.clock.now = 11\n        self.assertIs(limiter.allow('k'), True)\n"
                             "        self.assertEqual(limiter.remaining('k'), 2)\n")]},
     ['catches remaining that counts hits outside the window']),
    ('retry_after is checked only for a cost of the whole limit',
     {TESTS: [("        self.assertEqual(limiter.retry_after('k'), 5)\n"
               "        self.assertEqual(limiter.retry_after('k', 2), 7)\n", "")]},
     ['catches retry_after that waits for the newest hit']),
    ('retry_after is checked only with the default cost',
     {TESTS: [("        self.assertEqual(limiter.retry_after('k', 2), 7)\n"
               "        self.assertEqual(limiter.retry_after('k', 3), 9)\n", "")]},
     ['catches retry_after that waits only for the oldest hit']),
    ('reset is checked only on the key it names',
     {TESTS: [("        self.assertEqual(limiter.remaining('b'), 0)\n", "")]},
     ['catches reset that forgets every key']),
    ('the two limiters are given a clock each',
     {TESTS: [("other = Limiter(1, 10, self.clock)", "other = Limiter(1, 10, Clock())")]},
     ['catches limiters on one clock that share hits']),
    ('the file never runs its tests',
     {TESTS: [("if __name__ == '__main__':\n    unittest.main()\n", "")]},
     CATCHES),
    ('rule 3 misread: the hit is expected to count at exactly t + window',
     {TESTS: [(AT_WINDOW_END, AT_WINDOW_END.replace('True', 'False'))]},
     [SHIPPED, ERRORS, FLOATS, READS, 'catches a hit that still counts at exactly t + window']),
    ('an error message is asserted',
     {TESTS: [("self.subTest(limit=limit), self.assertRaises(ValueError):",
               "self.subTest(limit=limit), self.assertRaisesRegex(ValueError, 'limit'):")]},
     [ERRORS]),
    ('a private attribute is asserted',
     {TESTS: [("        self.assertIsNone(limiter.reset('never seen'))\n",
               "        self.assertIsNone(limiter.reset('never seen'))\n"
               "        self.assertNotIn('never seen', limiter._hits)\n")]},
     [ERRORS, FLOATS, READS]),
    ('retry_after is asserted to return an int',
     {TESTS: [("        self.assertEqual(limiter.retry_after('k', 3), 0)\n",
               "        self.assertIsInstance(limiter.retry_after('k', 3), int)\n")]},
     [FLOATS]),
    ('the clock is a script with one reading per call',
     {TESTS: [("        limiter = self.limiter(limit=5)\n",
               "        readings = iter([0, 0, 0, 0])\n        limiter = Limiter(5, 10, lambda: next(readings))\n")]},
     [READS]),
    ('the clock is turned back',
     {TESTS: [(AFTER_WINDOW, AFTER_WINDOW + "        self.clock.now = 5\n        self.assertEqual(limiter.remaining('k'), 3)\n")]},
     [FLOATS]),
]
