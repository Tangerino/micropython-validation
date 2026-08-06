# `unittest`: a run can be aborted, and failures can exit 0

**micropython-lib's `unittest` calls `setUp` and `tearDown` outside the block that handles
exceptions, so anything raised there aborts the entire run — every test after it silently
never executes. Separately, `main()` exits 0 even when tests fail.**

Together these mean a test suite can look green when it is not: the runner reports the
outcome correctly to a human reading the output, and incorrectly to any program reading the
exit code.

## Result

| Case | | CPython | MicroPython |
|---|---|---|---|
| `skipTest()` in `setUp` | tests run | 2 | **0** |
| | exit | 0 | 1 |
| | outcome | completed | **aborted** |
| Exception in `tearDown` | tests run | 2 | **0** |
| | exit | 1 | 1 |
| | outcome | failed | **aborted** |
| A failing test | tests run | 1 | 1 |
| | exit | 1 | **0** |
| No tests collected | exit | 5 | **0** |

## The cause

`run_one()` in `python-stdlib/unittest/unittest/__init__.py`:

```python
def run_one(test_function):
    print("%s (%s) ..." % (name, suite_name), end="")
    set_up()                          # <- outside the try
    ...
    try:
        ...
        test_function()
    except Exception as ex:
        _handle_test_exception((name, c), test_result, ex)
    finally:
        ...
        tear_down()                   # <- in the finally, unprotected
```

`set_up()` runs before the `try`, and `tear_down()` runs in the `finally` but is not itself
guarded. An exception from either escapes `run_one`, then `_run_suite`, then the whole run.

`skipTest()` raises `SkipTest`, so calling it in `setUp` — the documented way to skip a whole
class on CPython — takes the runner down.

## Why it matters

**Tests that never ran look like tests that passed.** When the run aborts, the report that
would have said "2 tests, 1 skipped" is precisely what does not get printed. A file with
thirty tests where the fifth uses `skipTest` in `setUp` silently exercises four.

**Skipping on missing hardware is the normal case in this ecosystem.** A test suite that
runs on both a desktop and a board needs to skip what the desktop cannot do, and `setUp` is
where CPython's documentation says to do it.

**The exit code is what CI reads.** A job that runs `micropython test_all.py` and trusts the
status gets a pass from a suite that printed `FAILED`.

We hit exactly this: a run printed `FAILED (errors=2)` and our harness reported *ALL OK*,
because the exit status said 0.

## Reproduce

```python
import unittest

class First(unittest.TestCase):
    def setUp(self):
        self.skipTest('needs hardware')
    def test_a(self):
        pass

class Second(unittest.TestCase):
    def test_b(self):
        pass

unittest.main()
```

CPython: `Ran 2 tests ... OK (skipped=1)`.
MicroPython: an uncaught `SkipTest` traceback, and `Second.test_b` never runs.

```python
import unittest

class T(unittest.TestCase):
    def test_fails(self):
        self.assertEqual(1, 2)

unittest.main()
```

```sh
micropython failing_test.py > /dev/null 2>&1 ; echo $?   # 0
python3     failing_test.py > /dev/null 2>&1 ; echo $?   # 1
```

## Environment

| | |
|---|---|
| MicroPython | `v1.29.0-preview.673.g06bcfd5b74`, commit `06bcfd5b7` |
| Port | unix, `build-standard` |
| micropython-lib | commit `dbb3b45` |
| CPython | 3.13.3 |
| Host | macOS 15.5, arm64 |
| Date | 2026-08-06 |

Also reproduced on an ESP32-P4 (Waveshare ESP32-P4-NANO) with the same micropython-lib.

## Running

```sh
python3 probe.py python3                                        # CPython reference
python3 probe.py /path/to/micropython /path/to/micropython-lib/python-stdlib/unittest
```

Or through pytest, which compares them:

```sh
pip install pytest
pytest --interpreter /path/to/micropython \
       --unittest-path /path/to/micropython-lib/python-stdlib/unittest
```

**The tests fail while the bugs are present** — seven of them today. That is deliberate:
this folder is a verification tool, so applying a fix and watching the suite turn green is
the check. CPython passes every one, so the expected behaviour is CPython's rather than an
invention of this suite.

## Files

| File | Role |
|---|---|
| `cases/` | four self-contained reproduction scripts, each demonstrating one behaviour |
| `probe.py` | runs each case under one interpreter; reports exit code, tests run, and outcome |
| `conftest.py` | pytest options and fixtures |
| `test_unittest_behaviour.py` | the assertions |

Three things are measured per case, because a test runner can go wrong in three different
ways: the exit code (what CI reads), how many tests actually ran (parsed from the runner's
own `Ran N tests` line), and whether the run completed, aborted, or reported failures.

## Suggested fix

Move `set_up()` inside the `try`, and guard `tear_down()`, handling `SkipTest` in both the
same way it is already handled when raised from a test body. Have `main()` return a non-zero
status when `result.wasSuccessful()` is false — `TestResult` already carries `failuresNum`,
`errorsNum` and `wasSuccessful()`; what is missing is `main()` acting on them.

The "no tests collected" case is arguably by design and is included for completeness rather
than as a defect claim. CPython exits 5 there, which at least lets a caller tell the
difference between "everything passed" and "nothing ran".

## Workaround

Until this is fixed, put the skip guard on the first line of each test rather than in
`setUp`, and wrap `main()` so the process exits properly:

```python
def run():
    result = unittest.main(__name__)
    failures = getattr(result, 'failuresNum', 0) + getattr(result, 'errorsNum', 0)
    if getattr(result, 'testsRun', 0) == 0:
        raise SystemExit('no tests were executed')
    if failures:
        raise SystemExit('{} test(s) failed'.format(failures))
```
