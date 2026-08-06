"""A failing test should make the process exit non-zero.

CPython: exit 1.
MicroPython: reports FAILED and exits 0.
"""

import unittest


class T(unittest.TestCase):
    def test_fails(self):
        self.assertEqual(1, 2)


unittest.main()
