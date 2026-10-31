"""Do concurrent MicroPython processes survive thread + GC stress on this host?

    python3 probe.py /path/to/micropython [--procs 8] [--rounds 3]

Runs stress.py (a worker thread holding objects on its stack while the main
thread collects) once alone as a control, then --procs copies at the same time,
--rounds times. Also asks the interpreter, through its ``ffi`` module, for
pthread_self() of its main thread in several separate processes: the unpatched
unix port builds the name of its GC semaphore from that value, and it is the
same in every process, which is the collision.

Output is one tab-separated line per measurement::

    runtime         micropython  3.4.0; MicroPython v1.30.0-preview...
    host            darwin       arm64
    pthread_self    8528822144   8528822144   8528822144   (same in every process)
    solo            before       OK
    concurrent      1            1/8   OK SIGSEGV SIGSEGV exception corrupted ...
    solo            after        OK
    summary         solo_ok=2/2  concurrent_ok=3/24

A process whose semaphore could not be opened runs its collector without
waiting for the other threads. One that then dies by signal never reaches
mp_thread_deinit(), so the semaphore name stays registered in the kernel and
poisons the next process to start -- until some process exits normally and
unlinks it. The probe therefore runs a plain ``micropython -c pass`` before and
after the measurement so it neither inherits nor leaves such a stale name.
"""

import argparse
import os
import platform
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STRESS = os.path.join(HERE, 'stress.py')
TIMEOUT = 120

PTHREAD_SELF_SNIPPET = (
    'import ffi; l = ffi.open(None); print(l.func("l", "pthread_self", "")())'
)


def emit(*fields):
    sys.stdout.write('\t'.join(str(f) for f in fields) + '\n')
    sys.stdout.flush()


def classify(proc, out):
    rc = proc.returncode
    if rc is None:
        return 'timeout'
    if rc < 0:
        try:
            return signal.Signals(-rc).name
        except ValueError:
            return 'signal%d' % -rc
    first = out.strip().splitlines()[-1] if out.strip() else ''
    if rc == 0 and first.startswith('OK'):
        return 'OK'
    if 'corrupted' in out:
        return 'corrupted'
    return 'exception'


def run_many(mp, count):
    procs = [
        subprocess.Popen(
            [mp, STRESS], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for _ in range(count)
    ]
    outcomes = []
    for p in procs:
        try:
            out, _ = p.communicate(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            p.kill()
            out, _ = p.communicate()
            p.returncode = None
        outcomes.append(classify(p, out))
    return outcomes


def heal(mp):
    """A normal exit unlinks the (possibly stale) semaphore name."""
    subprocess.run([mp, '-c', 'pass'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main_thread_ids(mp, count):
    ids = []
    for _ in range(count):
        r = subprocess.run([mp, '-c', PTHREAD_SELF_SNIPPET], capture_output=True, text=True)
        ids.append(r.stdout.strip() if r.returncode == 0 else 'unavailable')
    return ids


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('micropython')
    ap.add_argument('--procs', type=int, default=8)
    ap.add_argument('--rounds', type=int, default=3)
    args = ap.parse_args()
    mp = args.micropython

    version = subprocess.run(
        [mp, '-c', 'import sys; print(sys.version)'], capture_output=True, text=True
    ).stdout.strip()
    emit('runtime', 'micropython', version)
    emit('host', sys.platform, platform.machine())

    has_thread = subprocess.run(
        [mp, '-c', 'import _thread'], capture_output=True, text=True
    ).returncode == 0
    if not has_thread:
        emit('error', 'no-thread', 'this build has no _thread module; nothing to measure')
        return 2

    if sys.platform == 'darwin':
        emit('pthread_self', *main_thread_ids(mp, 3))
    else:
        emit('pthread_self', 'n/a', 'this platform uses sem_init(), no name involved')

    heal(mp)
    solo_ok = 0
    before = run_many(mp, 1)[0]
    solo_ok += before == 'OK'
    emit('solo', 'before', before)

    conc_ok = 0
    total = 0
    for rnd in range(1, args.rounds + 1):
        outcomes = run_many(mp, args.procs)
        ok = outcomes.count('OK')
        conc_ok += ok
        total += len(outcomes)
        emit('concurrent', rnd, '%d/%d' % (ok, len(outcomes)), *outcomes)

    heal(mp)
    after = run_many(mp, 1)[0]
    solo_ok += after == 'OK'
    emit('solo', 'after', after)

    emit('summary', 'solo_ok=%d/2' % solo_ok, 'concurrent_ok=%d/%d' % (conc_ok, total))
    return 0 if conc_ok == total and solo_ok == 2 else 1


if __name__ == '__main__':
    sys.exit(main())
