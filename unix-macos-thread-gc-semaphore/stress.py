"""Thread + GC stress: runs under MicroPython, exits 0 and prints ``OK 0`` when sane.

A worker thread keeps a few hundred small lists alive only through its own
locals (so they are reachable only from that thread's C stack) while the main
thread allocates garbage and forces collections. If the collector sweeps before
the worker's stack has been scanned, the worker's lists are freed and reused:
the check below sees foreign contents (``corrupted N``), the VM raises
nonsense (``NotImplementedError: opcode``, ``TypeError``) or the process dies
with SIGSEGV / SIGBUS.

Alone on a healthy build this takes well under a second and always prints OK.
It is driven by probe.py; it can also be run by hand:

    micropython stress.py
"""

import _thread
import gc

N = 400
ROUNDS = 300
done = [False]
bad = [0]


def worker():
    try:
        for r in range(ROUNDS):
            objs = [[r, i] for i in range(N)]
            gc.collect()
            for i in range(N):
                x = objs[i]
                if x[0] != r or x[1] != i:
                    bad[0] += 1
    except Exception as e:
        print("worker exception", repr(e))
        bad[0] += 1
    done[0] = True


_thread.start_new_thread(worker, ())
while not done[0]:
    junk = [[j] * 4 for j in range(200)]
    gc.collect()
print("corrupted" if bad[0] else "OK", bad[0])
