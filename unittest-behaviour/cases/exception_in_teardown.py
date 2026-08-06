"""An exception in tearDown should be recorded and the run should continue.

CPython: 2 tests run, 1 error, exit 1.
MicroPython: the exception escapes the runner, Second.test_b never runs.
"""

import unittest


class First(unittest.TestCase):
    def test_a(self):
        pass

    def tearDown(self):
        raise RuntimeError('failure while cleaning up')


class Second(unittest.TestCase):
    def test_b(self):
        pass


unittest.main()
