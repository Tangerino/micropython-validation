"""`deflate` produces an unreadable stream for empty input.

    pytest --interpreter /path/to/micropython

The interpreter must be built with compression enabled; a default build has none
(see the README). CPython is always run as the reference.

The assertion that matters is the round trip: a compressor whose output its own
decompressor rejects is broken regardless of what any other implementation does.
"""

import pytest

FORMATS = ('RAW', 'ZLIB', 'GZIP')


def _usable(table, name):
    if ('error', 'no-compression') in table:
        pytest.skip(
            '{} was built without compression; rebuild with '
            'CFLAGS_EXTRA=-DMICROPY_PY_DEFLATE_COMPRESS=1'.format(name)
        )
    if table['_returncode'] != 0:
        pytest.fail('{} failed: {}'.format(name, table['_stderr']))


@pytest.mark.parametrize('fmt', FORMATS)
def test_empty_input_produces_output(results, interpreters, fmt):
    """A stream for empty input is never empty itself.

    Raw deflate needs at least a final block; zlib adds a header and checksum;
    gzip has a mandatory 10-byte header and 8-byte trailer. Zero bytes cannot be
    a valid stream in any of the three.
    """
    failures = []
    for name in interpreters:
        table = results[name]
        _usable(table, name)
        size = table.get(('compress', fmt))
        if size and int(size[0]) == 0:
            failures.append(name)
    assert not failures, '{}: {} emitted 0 bytes for empty input'.format(
        fmt, ', '.join(failures)
    )


@pytest.mark.parametrize('fmt', FORMATS)
def test_empty_input_round_trips(results, interpreters, fmt):
    """Compressing nothing and decompressing it returns nothing.

    The strongest form of the bug: the implementation cannot read back what it
    just wrote.
    """
    failures = []
    for name in interpreters:
        table = results[name]
        _usable(table, name)
        outcome = table.get(('roundtrip', fmt))
        if outcome and outcome[0] != 'OK':
            failures.append('{} ({})'.format(name, ' '.join(outcome)))
    assert not failures, '{}: {}'.format(fmt, '; '.join(failures))


@pytest.mark.parametrize('fmt', FORMATS)
def test_non_empty_input_is_unaffected(results, interpreters, fmt):
    """Everything else works, which is what makes the empty case a bug rather
    than a missing feature."""
    failures = []
    for name in interpreters:
        table = results[name]
        _usable(table, name)
        outcome = table.get(('nonempty', fmt))
        if outcome and outcome[0] != 'OK':
            failures.append('{} ({})'.format(name, ' '.join(outcome)))
    assert not failures, '{}: {}'.format(fmt, '; '.join(failures))


@pytest.mark.parametrize('fmt', ('RAW', 'ZLIB'))
def test_reference_stream_is_readable(results, interpreters, fmt):
    """The decompressor handles a zlib-produced empty stream.

    This is what localises the fault: reading is correct, so only the compressor
    is at fault.
    """
    failures = []
    for name in interpreters:
        table = results[name]
        _usable(table, name)
        outcome = table.get(('read_reference', fmt))
        if outcome and outcome[0] != 'OK':
            failures.append('{} ({})'.format(name, ' '.join(outcome)))
    assert not failures, '{}: {}'.format(fmt, '; '.join(failures))


def test_summary(results, interpreters, capsys):
    """Print the comparison. Never fails — it is the report, not a check."""
    lines = ['', 'deflate: empty input', '']
    header = '{:<14} {:<7} {:>8} {:>12}'.format('runtime', 'format', 'bytes', 'round trip')
    lines.append(header)
    lines.append('-' * len(header))
    for name in sorted(interpreters):
        table = results[name]
        if ('error', 'no-compression') in table:
            lines.append('{:<14} (built without compression)'.format(name))
            continue
        for fmt in FORMATS:
            size = table.get(('compress', fmt), ['?'])[0]
            trip = ' '.join(table.get(('roundtrip', fmt), ['?']))
            lines.append('{:<14} {:<7} {:>8} {:>12}'.format(name, fmt, size, trip))
    with capsys.disabled():
        print('\n'.join(lines))
        print()
