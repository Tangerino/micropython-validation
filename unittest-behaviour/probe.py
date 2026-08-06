"""Run each reproduction case under one interpreter and report what happened.

    python3 probe.py <interpreter> [micropython-lib/python-stdlib/unittest]

Output is one tab-separated line per case::

    skip_in_setup	exit=1	ran=0	aborted
    failing_test	exit=0	ran=1	failed

Three things are measured per case, because a test runner can go wrong in three
different ways:

**exit code** — what CI reads.
**tests run** — parsed from the runner's own "Ran N tests" line.
**outcome** — whether the run completed, aborted on an uncaught exception, or
reported failures.

This one is a plain CPython script: it drives interpreters rather than being
driven by one.
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, 'cases')

#: What each case should do, per CPython's documented behaviour.
EXPECTED = {
    'skip_in_setup': {'ran': 2, 'exit': 0, 'outcome': 'completed'},
    'exception_in_teardown': {'ran': 2, 'exit': 1, 'outcome': 'failed'},
    'failing_test': {'ran': 1, 'exit': 1, 'outcome': 'failed'},
    # CPython exits 5 when nothing was collected (since 3.12). MicroPython
    # exits 0, so a suite that failed to load reads as a pass.
    'no_tests_found': {'ran': 0, 'exit': 5, 'outcome': 'completed'},
}

RAN = re.compile(r'Ran (\d+) tests?')


def cases():
    return sorted(n[:-3] for n in os.listdir(CASES) if n.endswith('.py'))


def run_case(interpreter, name, unittest_path=None):
    """Run one case and return ``(exit_code, tests_run, outcome)``."""
    env = dict(os.environ)
    if unittest_path:
        # MicroPython needs micropython-lib's unittest on the path, and .frozen
        # must stay on it: setting MICROPYPATH replaces the default entirely.
        env['MICROPYPATH'] = '.frozen:' + unittest_path

    completed = subprocess.run(
        [interpreter, os.path.join(CASES, name + '.py')],
        capture_output=True,
        text=True,
        env=env,
    )
    output = completed.stdout + completed.stderr

    match = RAN.search(output)
    ran = int(match.group(1)) if match else 0

    # The runner's own "Ran N tests" line is the reliable signal that it got to
    # the end and produced a report. A traceback inside a failure report is
    # normal; a traceback *instead of* the report means the run was aborted.
    if match is None:
        outcome = 'aborted' if 'Traceback' in output else 'no-report'
    elif 'FAILED' in output:
        outcome = 'failed'
    else:
        outcome = 'completed'

    return completed.returncode, ran, outcome


def main(argv):
    if len(argv) < 2:
        print('usage: probe.py <interpreter> [path/to/micropython-lib/python-stdlib/unittest]')
        return 2

    interpreter = argv[1]
    unittest_path = argv[2] if len(argv) > 2 else None

    for name in cases():
        code, ran, outcome = run_case(interpreter, name, unittest_path)
        print('{}\texit={}\tran={}\t{}'.format(name, code, ran, outcome))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
