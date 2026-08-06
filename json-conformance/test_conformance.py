"""JSON parser conformance against JSONTestSuite.

The corpus is Nicolas Seriot's JSONTestSuite, from *Parsing JSON is a Minefield*
(https://github.com/nst/JSONTestSuite), which is the de-facto standard for this.
It encodes the expectation in each file name:

===========  ==========================================================
``y_``       RFC 8259 says this **must be accepted**
``n_``       RFC 8259 says this **must be rejected**
``i_``       the specification leaves it to the implementation
===========  ==========================================================

Run it::

    pytest --suite /path/to/JSONTestSuite/test_parsing \\
           --interpreter micropython=/path/to/micropython

CPython is always included as the reference. The useful question is not how many
cases a parser fails in the abstract, but how it differs from the implementation
everyone writing JSON is already working against.

``i_`` cases are reported and never asserted: failing a test over behaviour the
specification declines to define would be noise.
"""



def accepts_only(prefix):
    """Restrict a test to one class of case, via the name convention."""

    def decorate(function):
        function._case_prefix = prefix
        return function

    return decorate


def _deviation(results, baseline, interpreter, case, expected):
    """Whether this case deviates, and whether the deviation is already known."""
    actual = results[interpreter].get(case, 'missing')
    deviates = actual != expected
    known = baseline.get(interpreter, {}).get(case) == actual
    return actual, deviates, known


@accepts_only('y_')
def test_must_accept(results, baseline, interpreters, case):
    """RFC 8259 requires these to parse."""
    failures = []
    for name in interpreters:
        actual, deviates, known = _deviation(results, baseline, name, case, 'y')
        if deviates and not known:
            failures.append('{} rejected it (result: {})'.format(name, actual))
    assert not failures, '{}: {}'.format(case, '; '.join(failures))


@accepts_only('n_')
def test_must_reject(results, baseline, interpreters, case):
    """RFC 8259 requires these to be rejected.

    This is where a permissive parser shows up, and where the consequences live:
    a document accepted here is one whose meaning is not defined, so two
    implementations can disagree about what it says.
    """
    failures = []
    for name in interpreters:
        actual, deviates, known = _deviation(results, baseline, name, case, 'n')
        if deviates and not known:
            failures.append('{} accepted it (result: {})'.format(name, actual))
    assert not failures, '{}: {}'.format(case, '; '.join(failures))


@accepts_only('')
def test_no_interpreter_crashes(results, interpreters, case):
    """No input should take the process down.

    Separate from acceptance: rejecting malformed input is correct behaviour,
    crashing on it is a denial-of-service on anything that parses input it did
    not write.
    """
    crashed = [
        name for name in interpreters if results[name].get(case) == 'crash'
    ]
    assert not crashed, '{} crashed on {}'.format(', '.join(crashed), case)


@accepts_only('')
def test_every_case_was_evaluated(results, interpreters, case):
    """Every interpreter produced a verdict for every case.

    Guards the harness itself: a missing result would otherwise read as a pass.
    """
    missing = [name for name in interpreters if case not in results[name]]
    assert not missing, '{} produced no result for {}'.format(', '.join(missing), case)


def test_summary(results, interpreters, capsys):
    """Print the comparison table. Never fails — it is the report, not a check."""
    lines = ['', 'JSON conformance (JSONTestSuite)', '']
    header = '{:<14} {:>13} {:>13} {:>10}'.format(
        'interpreter', 'must-accept', 'must-reject', 'crashes'
    )
    lines.append(header)
    lines.append('-' * len(header))

    for name in sorted(interpreters):
        table = results[name]
        must_accept = [c for c in table if c.startswith('y_')]
        must_reject = [c for c in table if c.startswith('n_')]
        accepted = sum(1 for c in must_accept if table[c] == 'y')
        rejected = sum(1 for c in must_reject if table[c] == 'n')
        crashes = sum(1 for c in table if table[c] == 'crash')
        lines.append(
            '{:<14} {:>13} {:>13} {:>10}'.format(
                name,
                '{}/{}'.format(accepted, len(must_accept)),
                '{}/{}'.format(rejected, len(must_reject)),
                crashes,
            )
        )

    with capsys.disabled():
        print('\n'.join(lines))
        print('For the per-case breakdown, run report.py.')
        print()
