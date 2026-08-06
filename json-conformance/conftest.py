"""Fixtures for the JSON conformance suite.

Each interpreter is run **once** per session over the whole corpus, and the
per-case tests read from that result. Spawning a process per case would turn a
30-millisecond run into a minute of process creation and tell us nothing extra.
"""

import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, 'probe.py')
DEFAULT_BASELINE = os.path.join(HERE, 'baseline.json')


def pytest_addoption(parser):
    parser.addoption(
        '--suite',
        action='store',
        default=os.environ.get('JSON_TEST_SUITE', ''),
        help='path to JSONTestSuite/test_parsing',
    )
    parser.addoption(
        '--interpreter',
        action='append',
        default=[],
        help='interpreter to test, repeatable. Example: '
        '--interpreter micropython=/path/to/micropython',
    )
    parser.addoption(
        '--baseline',
        action='store',
        default=DEFAULT_BASELINE,
        help='known deviations to tolerate; CI then fails only on new ones',
    )
    parser.addoption(
        '--no-baseline',
        action='store_true',
        default=False,
        help='ignore the baseline and report every deviation as a failure',
    )
    parser.addoption(
        '--write-baseline',
        action='store_true',
        default=False,
        help='record the current results as the baseline and exit',
    )


@pytest.fixture(scope='session')
def suite_dir(request):
    """Where the JSONTestSuite parsing corpus lives."""
    path = request.config.getoption('--suite')
    if not path:
        pytest.skip(
            'no corpus: pass --suite /path/to/JSONTestSuite/test_parsing '
            'or set JSON_TEST_SUITE'
        )
    if not os.path.isdir(path):
        pytest.fail('corpus not found: {}'.format(path))
    return path


@pytest.fixture(scope='session')
def interpreters(request):
    """``{name: command}`` for every interpreter under test.

    CPython is always included as the reference: the interesting number is not
    "how many cases does this parser fail" in the abstract, but how it compares
    to the implementation everyone else is working against.
    """
    found = {'cpython': sys.executable}
    for entry in request.config.getoption('--interpreter'):
        if '=' in entry:
            name, command = entry.split('=', 1)
        else:
            name, command = os.path.basename(entry), entry
        found[name.strip()] = command.strip()
    return found


def run_probe(command, suite_dir, out_path):
    """Run the probe under one interpreter; return ``{case: result}``.

    A crash is not an error here — the corpus is designed to provoke one. The
    probe flushes each result, so whatever was written before the crash is kept
    and the first missing case names the file that killed the process.
    """
    completed = subprocess.run(
        [command, PROBE, suite_dir, out_path],
        capture_output=True,
        text=True,
    )

    results = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                line = line.rstrip('\n')
                if '\t' in line:
                    result, name = line.split('\t', 1)
                    results[name] = result

    if completed.returncode != 0:
        done = set(results)
        remaining = [
            n for n in sorted(os.listdir(suite_dir)) if n.endswith('.json') and n not in done
        ]
        if remaining:
            # The first case the probe did not report is the one that killed it.
            results[remaining[0]] = 'crash'

    return results


@pytest.fixture(scope='session')
def results(request, suite_dir, interpreters, tmp_path_factory):
    """``{interpreter: {case: result}}`` for the whole corpus."""
    tmp = tmp_path_factory.mktemp('json-conformance')
    collected = {}
    for name, command in interpreters.items():
        out_path = str(tmp / '{}.tsv'.format(name))
        collected[name] = run_probe(command, suite_dir, out_path)
        if not collected[name]:
            pytest.fail('{} ({}) produced no results'.format(name, command))
    return collected


@pytest.fixture(scope='session')
def baseline(request, results):
    """Known deviations, so CI fails on new ones rather than on the backlog.

    Without this, adopting the suite in a project that already deviates means
    starting with dozens of red tests, which is how a useful check gets disabled
    on its first day.
    """
    if request.config.getoption('--write-baseline'):
        path = request.config.getoption('--baseline')
        with open(path, 'w') as f:
            json.dump(results, f, indent=2, sort_keys=True)
        print('\nbaseline written to {}'.format(path))
        return results

    if request.config.getoption('--no-baseline'):
        return {}

    path = request.config.getoption('--baseline')
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def pytest_generate_tests(metafunc):
    """Parametrise over the corpus, split by what the name promises.

    JSONTestSuite encodes the expectation in the file name: ``y_`` must be
    accepted, ``n_`` must be rejected, ``i_`` is left to the implementation by
    the specification.
    """
    if 'case' not in metafunc.fixturenames:
        return

    path = metafunc.config.getoption('--suite')
    if not path or not os.path.isdir(path):
        metafunc.parametrize('case', [])
        return

    names = sorted(n for n in os.listdir(path) if n.endswith('.json'))
    wanted = getattr(metafunc.function, '_case_prefix', None)
    if wanted:
        names = [n for n in names if n.startswith(wanted)]
    metafunc.parametrize('case', names)
