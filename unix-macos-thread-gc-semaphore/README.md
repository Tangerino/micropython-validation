# unix port on macOS: concurrent processes break each other's garbage collector

**On macOS, the unix port names the semaphore that synchronises garbage collection across
threads after `pthread_self()` of the main thread. That value is the same in every process,
so with two or more MicroPython processes alive at once, all but one get `SEM_FAILED`, and
their collector sweeps the heap before the other threads have scanned their stacks. Objects
still in use are freed. Linux is not affected.**

The first thing it looks like is a random crash in a parallel test run. The suite runner
(`run-tests.py -j`) starts many interpreters at once; any test that uses `_thread` in one of
them can die with SIGSEGV, SIGBUS, an assertion deep in the VM, or an impossible exception
such as `NotImplementedError: opcode`. Alone, the same test always passes.

## Result

Eight copies of a thread + GC stress script started at the same time, three rounds, on the
same host. `stress.py` is a worker thread that keeps lists alive only through its own locals
while the main thread allocates and collects; it prints `OK 0` when its lists still hold
what it put there.

| Build | Alone | 24 concurrent processes |
|---|---|---|
| master `321fba0d1`, unpatched | OK | **8 OK, 16 failed** (SIGSEGV ×10, SIGBUS ×2, `corrupted`, exceptions) |
| same commit + `mpthreadport-pid-semaphore.patch` | OK | 24 OK |

The failure rate is not fixed (6/24 and 8/24 survived in other runs); the survivors are
mostly the process that happened to own the semaphore. The premise is deterministic, though:
asking three separate processes for `pthread_self()` of their main thread gives the same
number every time (`8528822144` on this host), so the name
`micropython_sem_8528822144` is the same for all of them.

A second consequence, confirmed by hand: a process that dies by signal never reaches
`mp_thread_deinit()`, so the name stays registered in the kernel. The next MicroPython
process to start, even alone, gets `SEM_FAILED` and is just as unsafe, until some process
exits normally and unlinks the name. One crash can poison the following run on the same
machine.

## Cause

`ports/unix/mpthreadport.c`, since commit `0b86ba565` (2019, "unix/mpthreadport: Use named
semaphores on Mac OS X"), because macOS has no `sem_init()`:

```c
#if defined(__APPLE__)
snprintf(thread_signal_done_name, sizeof(thread_signal_done_name), "micropython_sem_%ld", (long)thread->id);
thread_signal_done_p = sem_open(thread_signal_done_name, O_CREAT | O_EXCL, 0666, 0);
#else
sem_init(&thread_signal_done, 0, 0);
#endif
```

`thread->id` is `pthread_self()` of the main thread. On macOS that is a pointer into
`libsystem_pthread`'s main-thread structure, identical across processes of the same binary.
Named semaphores are system-wide, so with `O_EXCL` the second process gets `SEM_FAILED`
(`EEXIST`). The return value is not checked.

From then on, in that process, `mp_thread_gc_others()` signals each other thread with
`SIGUSR1` and calls `sem_wait(SEM_FAILED)`, which returns immediately with `EINVAL`. The
collector moves on to sweep while the signalled thread may not yet have run
`gc_helper_collect_regs_and_stack()`. Anything reachable only from that thread's registers
or C stack (its locals, its current frame) is unmarked and freed.

## Reproduce

```sh
./run.sh /path/to/micropython
```

With no argument it uses the `micropython` on your `PATH`. It prints one line per
measurement, then the pytest checks if pytest is installed. **The checks fail while the bug
is present**; apply the patch, rebuild, and watch them turn green. On Linux everything
passes, which is the control: that build uses `sem_init()` and no name is involved.

<details>
<summary>Running the pieces directly</summary>

```sh
python3 probe.py /path/to/micropython             # the measurement, tab-separated
/path/to/micropython stress.py                     # one copy of the stress, prints OK 0
pip install pytest
pytest --interpreter /path/to/micropython          # the checks
```

The probe runs `micropython -c pass` before and after measuring. A normal exit unlinks the
semaphore name, so this neither inherits a stale name from an earlier crash nor leaves one
behind.

</details>

## Environment

| | |
|---|---|
| MicroPython | master, `321fba0d1` (`v1.30.0-preview.216`), unix port, `standard` variant |
| Host | macOS 27.0.1 (26A434), arm64, Apple clang 21.0.0 |
| CPython | 3.11.13 (driver only; no behaviour compared) |
| Date | 2026-10-31 |

First seen as `Assertion failed: (mp_obj_get_type(code_state->frame) == &mp_type_frame),
py/profile.c:256` in `extmod/select_poll_eintr.py` during `make VARIANT=coverage test_full`,
36 times in 40 runs of ten copies at once, 0 in 40 with the patch. The same interpreter
alone passed the whole suite every time (standard 999/999, coverage 1056/1056). Searches of
the upstream tracker for `sem_open`, "named semaphore", `mpthreadport` and "macos thread gc"
found no earlier report.

## Files

| File | Role |
|---|---|
| `run.sh` | one-command entry point |
| `probe.py` | host driver: pthread_self() across processes, the stress alone, then 8 at a time |
| `stress.py` | runs under MicroPython: worker thread holding objects on its stack while the main thread collects |
| `conftest.py`, `test_thread_gc_semaphore.py` | the checks |
| `mpthreadport-pid-semaphore.patch` | the fix used for the "patched" column |
| `RESULTS.md` | the raw output of both runs above |

## Suggested fix

Name the semaphore after something unique per process, check the result, and remove a stale
name before creating it. That is what the patch does:

```c
snprintf(thread_signal_done_name, sizeof(thread_signal_done_name), "micropython_sem_%d", (int)getpid());
sem_unlink(thread_signal_done_name);
thread_signal_done_p = sem_open(thread_signal_done_name, O_CREAT | O_EXCL, 0666, 0);
if (thread_signal_done_p == SEM_FAILED) {
    perror("sem_open");
    abort();
}
```

`getpid()` is unique among live processes, and the `sem_unlink` before `sem_open` covers a
PID reused after a crash. An alternative that avoids the kernel namespace entirely is a
`pthread_mutex_t` + `pthread_cond_t` pair, or `dispatch_semaphore_t`, in place of the POSIX
semaphore on Darwin.
