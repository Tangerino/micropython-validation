"""Finding no tests at all should not report success.

Both runtimes print OK after running nothing, which turns a suite that failed to
load into a green result. Included for completeness; arguably by design.
"""

import unittest


class NotATestCase:
    def test_never_collected(self):
        raise AssertionError('never reached')


unittest.main()
