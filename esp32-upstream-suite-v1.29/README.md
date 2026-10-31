# The upstream test suite on an ESP32 running v1.29.0

**The whole upstream `run-tests.py` suite from master `321fba0d1`, run on a production ESP32
board with MicroPython v1.29.0, in bytecode and through the native Xtensa emitter, against
the unix port built from the v1.29.0 tag as a control. 960 of 964 bytecode tests and 706 of
709 native tests pass. Three failures are version skew. One is a real crash, already fixed
upstream.**

This is a results folder rather than a probe: it records what the suite looks like on
hardware, how to run it there without disturbing an application, and how to tell a port
problem from a test that simply postdates the firmware.

## Result

| Run | Performed | Passed | Failed | Skipped |
|---|---|---|---|---|
| ESP32, bytecode (basics, micropython, misc, extmod, stress, thread, float, unicode, ports/esp32) | 964 | 960 | 4 | 81 |
| ESP32, `--via-mpy --emit native` (basics, micropython, float, misc) | 709 | 706 | 3 | 61 |
| unix port built from the `v1.29.0` tag, same suite, macOS arm64 (control) | 1001 | 998 | 3 | 142 |

**Three failures are version skew**, they fail identically on the unix v1.29.0 build:

| Test | Behaviour the suite now expects | Changed on master by |
|---|---|---|
| `basics/builtin_len_user.py` | `len()` rejects a non-int from `__len__` | `3ad3d917b` py/objtype: Validate that `__len__` returns an int (2026-08-24) |
| `basics/set_intersection.py` | `set.intersection()` takes several arguments | `cf632499f` py/objset: Allow intersection() to take multiple sets as args |
| `basics/ordereddict_fromkeys.py` | `OrderedDict.fromkeys()` returns an `OrderedDict` | `249736605` py/objdict: Make OrderedDict.fromkeys return an OrderedDict (2026-08-22) |

**One failure is specific to the board**: `extmod/machine_mem_backup_slice.py` panics the
ESP32 with `LoadStoreError` and reboots it. Root cause, dump and upstream fix are in
[`esp32-rom-memoryview-slice-store`](../esp32-rom-memoryview-slice-store/).

**No skip is caused by hardware.** The 81 bytecode skips are features v1.29.0 does not have
(t-strings, `weakref`, `marshal`, function `__code__`), modules not in this build
(`vfs_lfs`, `vfs_posix`, `ssl`, `cryptolib`, the `cexample` user module) and PC-only tests
(`sys.settrace`, `sys.atexit`). Ten tests pass in bytecode and are skipped under the native
emitter by the runner's own tables; they are listed in `RESULTS.md`.

The 52 `micropython/native_*` and `micropython/viper_*` tests all pass on the Xtensa
emitter, in both runs. They cannot run on an arm64 host at all (the unix port has no AArch64
emitter), so this board run is the only place in this campaign where they were exercised.

## How it was run

The board runs an application from `/main.py`. The runner enters the raw REPL with a soft
reset before **every** test, and a soft reset executes `/main.py`, so the application would
start 964 times and hold the REPL. The procedure:

1. Back up `/main.py` to the host, then rename it on the board (`/main.py.bak`); the board
   now boots to a clean REPL with no watchdog armed.
2. Install `unittest` from micropython-lib into `/lib/unittest/__init__.py`. Without it the
   runner aborts at the first unittest-based test (`error: test ... requires unittest`).
3. Exclude the tests that write to peripherals the application owns. Here: NVS (holds the
   application's credentials), UART, SPI, I2S and RTC.
4. Run, then remove `/lib`, rename `main.py` back, reset, and confirm the application
   comes up.

```sh
cd tests
# bytecode, default directories for a remote target
./run-tests.py -t /dev/cu.usbserial-XXXX -e esp32_nvs -e 'machine_(i2s|spi|uart|rtc)' \
    -r results_esp32_bytecode

# native emitter: a remote target needs --via-mpy, and mpy-cross must emit the board's
# .mpy version (v1.29.0 is mpy v6.3), so use the mpy-cross built from the same tag
MICROPY_MPYCROSS=/path/to/v1.29.0/mpy-cross/build/mpy-cross \
./run-tests.py -t /dev/cu.usbserial-XXXX --via-mpy --emit native \
    -e esp32_nvs -e 'machine_(i2s|spi|uart|rtc)' -d basics micropython float misc \
    -r results_esp32_native

# the control: unix port built from the same tag, same test files
git worktree add /tmp/mp_v129 v1.29.0 && make -C /tmp/mp_v129/mpy-cross && make -C /tmp/mp_v129/ports/unix
MICROPY_MICROPYTHON=/tmp/mp_v129/ports/unix/build-standard/micropython ./run-tests.py -r results_unix_v129
```

`MICROPY_TEST_TIMEOUT=90` was used on the board; the default 30 s is tight for the stress
tests over 115200 baud. Then:

```sh
./run.sh      # regenerates RESULTS.md from results/*.json with crossref.py
```

Two things worth knowing about the transport. A CH340 bridge sometimes resets the board
when the port is opened (DTR/RTS toggle) and sometimes does not; after the adapter
re-enumerated mid-campaign it stopped doing so, and the runner then timed out waiting for
the first prompt. An explicit esptool-style pulse on open (`dtr=False; rts=True; sleep 0.2;
rts=False`) makes the boot deterministic. And the crash test above reboots the board; the
runner recovers on the next test by itself.

## Environment

| | |
|---|---|
| Board | ESP32 (Xtensa LX6), 8 MB flash, PSRAM (2 MB heap), float 32-bit, GIL; custom board `COIOTE_ESP32_8M` |
| Firmware | MicroPython v1.29.0 (2026-08-25), ESP-IDF v5.5.2, mpy v6.3 (`xtensawin`) |
| Test suite | `tests/` from master `321fba0d1` (`v1.30.0-preview.216`), 2026-10-31 |
| Control | unix port, `standard` variant, built from tag `v1.29.0` on macOS 27.0.1 arm64, Apple clang 21 |
| Host tools | Python 3.11.13, `tools/pyboard.py` over `/dev/cu.usbserial-*` at 115200 |

## Files

| File | Role |
|---|---|
| `run.sh` | regenerates `RESULTS.md` |
| `crossref.py` | splits a board's failures into version skew vs. board-specific, using the control run |
| `results/esp32_bytecode.json` | `_results.json` of the bytecode run (every test with pass/fail/skip and reason) |
| `results/esp32_native_via_mpy.json` | same, native emitter via `.mpy` |
| `results/unix_v1.29.0_baseline.json` | same, unix port from the v1.29.0 tag |
| `logs/*.txt` | the runner's console output for the two board runs |
| `RESULTS.md` | the generated cross-reference |
