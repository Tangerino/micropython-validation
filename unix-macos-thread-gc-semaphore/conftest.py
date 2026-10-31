"""pytest options and fixtures for the thread/GC semaphore probe."""

import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, 'probe.py')


def pytest_addoption(parser):
    parser.addoption('--interpreter', required=True, help='MicroPython binary to test')
    parser.addoption('--procs', type=int, default=8, help='concurrent processes per round')
    parser.addoption('--rounds', type=int, default=3, help='rounds of concurrent processes')


@pytest.fixture(scope='session')
def interpreter(request):
    return request.config.getoption('--interpreter')


@pytest.fixture(scope='session')
def results(request, interpreter):
    """``{key: [fields]}`` from one probe run; ``concurrent`` collects all rounds."""
    completed = subprocess.run(
        [
            sys.executable,
            PROBE,
            interpreter,
            '--procs',
            str(request.config.getoption('--procs')),
            '--rounds',
            str(request.config.getoption('--rounds')),
        ],
        capture_output=True,
        text=True,
    )
    table = {'concurrent': [], 'solo': {}}
    for line in completed.stdout.splitlines():
        fields = line.split('\t')
        if fields[0] == 'concurrent':
            table['concurrent'].append(fields[1:])
        elif fields[0] == 'solo':
            table['solo'][fields[1]] = fields[2]
        else:
            table[fields[0]] = fields[1:]
    table['_returncode'] = completed.returncode
    table['_stderr'] = completed.stderr
    return table
