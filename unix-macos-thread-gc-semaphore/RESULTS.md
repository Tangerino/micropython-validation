# Raw output, 2026-10-31

Host: macOS 27.0.1 arm64, Apple clang 21. Both binaries built from master `321fba0d1`,
unix port, `standard` variant; the second one with `mpthreadport-pid-semaphore.patch`
applied (`make -C ports/unix BUILD=build-patched`).

## Unpatched

```
$ ./run.sh ports/unix/build-standard/micropython
>> interpreter: ports/unix/build-standard/micropython
>> 3.4.0; MicroPython v1.30.0-preview.216.g321fba0d16 on 2026-10-31
>> host:        Darwin arm64

== what happens to concurrent processes ==
runtime	micropython	3.4.0; MicroPython v1.30.0-preview.216.g321fba0d16 on 2026-10-31
host	darwin	arm64
pthread_self	8528822144	8528822144	8528822144
solo	before	OK
concurrent	1	3/8	OK	exception	SIGSEGV	OK	exception	SIGSEGV	OK	SIGSEGV
concurrent	2	2/8	OK	SIGSEGV	SIGSEGV	exception	SIGSEGV	exception	SIGSEGV	OK
concurrent	3	1/8	OK	SIGSEGV	SIGSEGV	SIGSEGV	SIGSEGV	SIGSEGV	exception	SIGSEGV
solo	after	OK
summary	solo_ok=2/2	concurrent_ok=6/24

== checks ==
FAILED test_thread_gc_semaphore.py::test_concurrent_processes_survive
  AssertionError: 16 of 24 processes failed: SIGSEGV SIGSEGV SIGSEGV exception SIGSEGV SIGBUS
  exception exception SIGSEGV corrupted exception SIGSEGV SIGSEGV SIGSEGV SIGBUS exception
1 failed, 2 passed
```

(The pytest run is a second, independent measurement, hence 16/24 rather than 18/24.)

The `exception` outcomes were, in the order seen across runs:

```
NotImplementedError: opcode
TypeError: () takes 0 positional arguments but 1 were given
worker exception ... / corrupted 65
```

## Patched

```
$ ./run.sh ports/unix/build-patched/micropython
>> 3.4.0; MicroPython v1.30.0-preview.216.g321fba0d16.dirty on 2026-10-31

pthread_self	8528822144	8528822144	8528822144
solo	before	OK
concurrent	1	8/8	OK	OK	OK	OK	OK	OK	OK	OK
concurrent	2	8/8	OK	OK	OK	OK	OK	OK	OK	OK
concurrent	3	8/8	OK	OK	OK	OK	OK	OK	OK	OK
solo	after	OK
summary	solo_ok=2/2	concurrent_ok=24/24

3 passed
```

`pthread_self()` is still identical across processes, as it must be: the patch stops using it
for the name.

## Stale name after a crash (by hand, unpatched)

```
$ micropython -c 'import time; time.sleep(30)' &  kill -9 $!
$ for i in 1 2 3 4 5; do micropython stress.py; echo rc=$?; done
rc=139                              # SIGSEGV: inherited the dead process's name, no sync
NotImplementedError: opcode  rc=1   # same, but exited normally -> unlinked the name
OK 0  rc=0                          # healed from here on
OK 0  rc=0
OK 0  rc=0
```
