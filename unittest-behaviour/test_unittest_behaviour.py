"""micropython-lib's unittest: a run can be aborted, and failures can exit 0.

    pytest --interpreter /path/to/micropython \\
           --unittest-path /path/to/micropython-lib/python-stdlib/unittest

CPython is always run as the reference, and passes everything here — the expected
behaviour is CPython's, not an invention of this suite.

The tests fail while the bugs are present. That is the point: this folder is a
verification tool, so applying a fix and watching the suite turn green is the
check.
"""

import probe


def _report(results, targets, case, field, index, expected):
    """Collect every target that got ``field`` wrong, for one case."""
    wrong = []
    for name in targets:
        actual = results[name][case][index]
        if actual != expected:
            wrong.append('{}: {}={} (expected {})'.format(name, field, actual, expected))
    return wrong


def test_the_whole_run_completes(results, targets, case):
    """Nothing in a test file should stop the runner reaching the end.

    A test that raises, skips or fails is ordinary; the runner absorbing it and
    carrying on is the entire job of a test runner. When it aborts instead, every
    test after the offending one silently never executes — and the report that
    would have said so is exactly what did not get printed.
    """
    expected = probe.EXPECTED[case]['outcome']
    wrong = _report(results, targets, case, 'outcome', 2, expected)
    assert not wrong, '{}: {}'.format(case, '; '.join(wrong))


def test_every_test_is_executed(results, targets, case):
    """The expected number of tests actually ran."""
    expected = probe.EXPECTED[case]['ran']
    wrong = _report(results, targets, case, 'ran', 1, expected)
    assert not wrong, '{}: {}'.format(case, '; '.join(wrong))


def test_the_exit_code_reflects_the_result(results, targets, case):
    """A failing or incomplete run must not exit 0.

    The exit code is what CI reads. A runner that prints FAILED and exits 0
    reports the outcome correctly to a human and incorrectly to a program, which
    is the worse of the two audiences to be wrong about.
    """
    expected = probe.EXPECTED[case]['exit']
    wrong = _report(results, targets, case, 'exit', 0, expected)
    assert not wrong, '{}: {}'.format(case, '; '.join(wrong))


def test_summary(results, targets, capsys):
    """Print the comparison. Never fails — it is the report, not a check."""
    lines = ['', 'unittest behaviour', '']
    header = '{:<26} {:<14} {:>6} {:>5}  {}'.format(
        'case', 'runtime', 'exit', 'ran', 'outcome'
    )
    lines.append(header)
    lines.append('-' * len(header))
    for case in probe.cases():
        for name in sorted(targets):
            code, ran, outcome = results[name][case]
            lines.append(
                '{:<26} {:<14} {:>6} {:>5}  {}'.format(case, name, code, ran, outcome)
            )
        lines.append('')
    with capsys.disabled():
        print('\n'.join(lines))
