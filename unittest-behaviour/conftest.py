"""pytest options and fixtures for the unittest behaviour cases."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import probe  # noqa: E402

# The files under cases/ are reproduction scripts, not tests: they call
# unittest.main() at import time, and one of them is deliberately named
# *_test.py. Collecting them would run them inside pytest's own process.
collect_ignore_glob = ['cases/*']


def pytest_addoption(parser):
    parser.addoption(
        '--interpreter',
        action='store',
        default='',
        help='MicroPython binary to test',
    )
    parser.addoption(
        '--unittest-path',
        action='store',
        default=os.environ.get('MICROPY_UNITTEST', ''),
        help="path to micropython-lib's python-stdlib/unittest",
    )


@pytest.fixture(scope='session')
def targets(request):
    """``{name: (interpreter, unittest_path)}``. CPython is always included."""
    found = {'cpython': (sys.executable, None)}
    interpreter = request.config.getoption('--interpreter')
    if interpreter:
        unittest_path = request.config.getoption('--unittest-path')
        if not unittest_path:
            pytest.fail(
                'pass --unittest-path pointing at micropython-lib/python-stdlib/unittest, '
                'or set MICROPY_UNITTEST'
            )
        found['micropython'] = (interpreter, unittest_path)
    return found


@pytest.fixture(scope='session')
def results(targets):
    """``{name: {case: (exit_code, tests_run, outcome)}}``."""
    collected = {}
    for name, (interpreter, unittest_path) in targets.items():
        collected[name] = {
            case: probe.run_case(interpreter, case, unittest_path)
            for case in probe.cases()
        }
    return collected


def pytest_generate_tests(metafunc):
    if 'case' in metafunc.fixturenames:
        metafunc.parametrize('case', probe.cases())
