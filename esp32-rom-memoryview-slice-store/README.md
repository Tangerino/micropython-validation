# esp32: a slice store into `machine.mem_backup()` panics the board (v1.29.0)

**On MicroPython v1.29.0 for the ESP32, `mem = machine.mem_backup(); mem[0:1] = b"\x11"`
raises a Guru Meditation `LoadStoreError` and reboots the board. The memoryview returned by
`mem_backup()` is a `const` object in flash, and up to v1.29.0 every slice store rewrote the
object's `len` and `free` fields, even when the slice did not change size. Fixed on master
on 2026-08-27, not yet in a tagged release as of 2026-10-31.**

Element stores (`mem[0] = 0x11`) and reads of any kind are fine. Only the slice store
touches the object header.

## Result

| Operation on `machine.mem_backup()` | v1.29.0 (ESP32) | master after `d89c63c68` |
|---|---|---|
| `mem[0]`, `mem[0:3]`, `bytes(mem)` | OK | OK |
| `mem[0] = 0x11` | OK | OK |
| `mem[0:1] = b"\x11"` (same length) | **LoadStoreError, reboot** | OK |

The upstream test `tests/extmod/machine_mem_backup_slice.py` (added with the fix) is the
only test of the whole upstream suite that fails on this board and does not also fail on the
unix port built from the same tag. The others are version skew; see
[`esp32-upstream-suite-v1.29`](../esp32-upstream-suite-v1.29/).

```
Guru Meditation Error: Core  1 panic'ed (LoadStoreError). Exception was unhandled.
EXCCAUSE: 0x00000003   EXCVADDR: 0x3f4270c0
MPY version : v1.29.0 on 2026-08-25
IDF version : v5.5.2
Rebooting...
```

`EXCVADDR 0x3f4270c0` is in the DROM window (`0x3F40_0000`–`0x3F7F_FFFF`): a write to flash.
The full dump, with the register set and backtrace, is in `crash.txt`.

## Cause

`ports/esp32/machine_mem_backup.c` declares the region table as
`static const mp_obj_array_t machine_mem_backup_regions[]`, and `machine.mem_backup()`
returns a pointer to one of those entries rather than a heap copy. In v1.29.0
`py/objarray.c`, `array_subscr()` ends every slice store with

```c
o->free -= len_adj;
o->len += len_adj;
```

For a memoryview `len_adj` is always 0 (a size change is rejected earlier with
`compat_error`), so the two lines write the values already there. On a heap object that is
harmless. On the ESP32 the object is in flash, and a store to that address is a bus error.

Upstream fix, commit `d89c63c6847cd96d43ae77fe4a770ea01634d97a` by Alessandro Gatti
("py/objarray: Update slice data only if necessary."), makes the update conditional:

```c
if (len_adj != 0) {
    o->free -= len_adj;
    o->len += len_adj;
}
```

A copy is in `upstream-fix-d89c63c68.patch`. The accompanying test is commit `816245185`.

## Reproduce

This one needs a board. The fault is a write to a const object in flash, and as of v1.29.0
only the esp32 port places a memoryview there (`MICROPY_PY_MACHINE_MEM_BACKUP` is on by
default for every ESP32 board). On the unix port `probe.py` prints `SKIP`.

```sh
pip install mpremote
./run.sh /dev/tty.usbserial-XXXX
```

Stop or rename `main.py` first if an application runs on the board: the probe needs a REPL.
It writes to the first five bytes of RTC user memory, the same bytes the upstream test
writes, and restores them on a fixed firmware. On a faulty firmware the board reboots before
the restore, with byte 0 left at `0x11`; `RTC.memory()` shares this buffer on esp32, so back
it up if you keep anything there.

<details>
<summary>What was actually run</summary>

The measurement came from the upstream runner, not from `probe.py`:

```sh
cd tests
./run-tests.py -t /dev/cu.usbserial-31220 extmod/machine_mem_backup_slice.py
```

whose log shows the dump above followed by `timeout waiting for first EOF reception` and
`CRASH`. `probe.py` performs the same stores one at a time with a line before each, so
the serial console shows exactly which one dies; it was checked on the unix port (prints
`SKIP`) and not re-run on the production board.

</details>

## Environment

| | |
|---|---|
| Board | ESP32 (Xtensa LX6, dual core), 8 MB flash, PSRAM; custom board definition `COIOTE_ESP32_8M` |
| Firmware | MicroPython v1.29.0 (2026-08-25), ESP-IDF v5.5.2 |
| Host | macOS 27.0.1 arm64, `mpremote`/`pyboard.py` over a CH340 at 115200 |
| Test | `tests/extmod/machine_mem_backup_slice.py` from master `321fba0d1` |
| Date | 2026-10-31 |

## Files

| File | Role |
|---|---|
| `run.sh` | runs `probe.py` on a board over mpremote |
| `probe.py` | the stores, one line before each, so the console shows which one panics |
| `crash.txt` | the Guru Meditation dump as captured by the runner |
| `upstream-fix-d89c63c68.patch` | the fix as merged on master |

## Why it matters

`machine.mem_backup()` was introduced in v1.29.0 as the cross-port way to keep bytes across
deep sleep. The documentation example stores one element at a time (`mem[0] = 0x12345678`)
and that path is fine. The natural way to persist a record, though, is a slice store of a
`struct.pack()` result or of a `bytes` object, and on a v1.29.0 ESP32 build the first such
store reboots the board; a program that does it at start-up is a reboot loop. Until a
release contains the fix, write element by element or use `RTC().memory()`, which goes
through a different path.
