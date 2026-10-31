"""Concurrent MicroPython processes must not corrupt each other's garbage collection.

    pytest --interpreter /path/to/micropython

The tests fail while the bug is present: on macOS the unix port names its GC
semaphore after pthread_self() of the main thread, which is the same value in
every process, so only one process at a time actually owns the semaphore and the
others collect without waiting for their threads to scan their stacks.
"""

import pytest


def _usable(table):
    if 'error' in table:
        pytest.skip(' '.join(table['error']))
    if table['_returncode'] not in (0, 1):
        pytest.fail('probe failed: {}'.format(table['_stderr']))


def test_solo_process_is_clean(results):
    """One process on its own always passes. This is the control."""
    _usable(results)
    assert results['solo'] == {'before': 'OK', 'after': 'OK'}


def test_concurrent_processes_survive(results):
    """Every concurrent process finishes with OK.

    The failing outcomes are the symptom: SIGSEGV, SIGBUS, 'corrupted N'
    (foreign data inside objects the worker still holds) or an impossible
    exception from the VM such as 'NotImplementedError: opcode'.
    """
    _usable(results)
    bad = []
    for rnd in results['concurrent']:
        bad.extend(o for o in rnd[2:] if o != 'OK')
    total = sum(len(rnd) - 2 for rnd in results['concurrent'])
    assert not bad, '{} of {} processes failed: {}'.format(len(bad), total, ' '.join(bad))


def test_summary(results, capsys):
    """Print the comparison. Never fails -- it is the report, not a check."""
    lines = ['', 'thread + GC stress, {}'.format(' '.join(results.get('runtime', ['?'])[1:])), '']
    lines.append('pthread_self():  {}'.format('  '.join(results.get('pthread_self', ['?']))))
    lines.append('solo:            before {}  after {}'.format(
        results['solo'].get('before', '?'), results['solo'].get('after', '?')))
    for rnd in results['concurrent']:
        lines.append('concurrent {:>2}:   {:>5}   {}'.format(rnd[0], rnd[1], ' '.join(rnd[2:])))
    with capsys.disabled():
        print('\n'.join(lines))
        print()
