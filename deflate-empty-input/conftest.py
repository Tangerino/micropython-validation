"""pytest options and fixtures for the deflate probe."""

import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, 'probe.py')


def pytest_addoption(parser):
    parser.addoption(
        '--interpreter',
        action='append',
        default=[],
        help='MicroPython binary to test, repeatable',
    )


@pytest.fixture(scope='session')
def interpreters(request):
    found = {'cpython': sys.executable}
    for entry in request.config.getoption('--interpreter'):
        name, _, command = entry.partition('=')
        found[name if command else os.path.basename(name)] = command or name
    return found


def run_probe(command):
    """``{(kind, format): [fields]}`` from one interpreter."""
    completed = subprocess.run([command, PROBE], capture_output=True, text=True)
    results = {}
    for line in completed.stdout.splitlines():
        fields = line.split('\t')
        if len(fields) >= 2:
            results[(fields[0], fields[1])] = fields[2:]
    results['_returncode'] = completed.returncode
    results['_stderr'] = completed.stderr
    return results


@pytest.fixture(scope='session')
def results(interpreters):
    collected = {}
    for name, command in interpreters.items():
        collected[name] = run_probe(command)
    return collected
