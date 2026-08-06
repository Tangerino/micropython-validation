"""skipTest() inside setUp should skip the test and let the run continue.

CPython: 2 tests run, 1 skipped, exit 0.
MicroPython: SkipTest escapes the runner, Second.test_b never runs.
"""

import unittest


class First(unittest.TestCase):
    def setUp(self):
        self.skipTest('needs hardware')

    def test_a(self):
        pass


class Second(unittest.TestCase):
    def test_b(self):
        pass


unittest.main()
