# `deflate`: empty input produces an unreadable stream

**MicroPython's `deflate` writes zero bytes when asked to compress nothing, in all three
formats. The result cannot be read back — not even by MicroPython's own decompressor.**

A compressed stream is never empty. Raw deflate needs at least a final block; zlib adds a
header and a checksum; gzip has a mandatory 10-byte header and 8-byte trailer. Zero bytes
is not a valid stream in any of them.

## Result

| Format | MicroPython | CPython | MicroPython reads it back |
|---|---|---|---|
| `RAW` | **0 bytes** | 2 bytes | ❌ `EOFError` |
| `ZLIB` | **0 bytes** | 8 bytes | ❌ `EOFError` |
| `GZIP` | **0 bytes** | 20 bytes | ❌ `EOFError` |

Two measurements localise the fault:

- **Non-empty input is byte-for-byte the same size as CPython** (7, 13 and 25 bytes for
  `b'hello'`), and round-trips correctly. Only the empty case is affected.
- **The decompressor reads a zlib-produced empty stream without complaint.** So reading is
  correct and only the compressor is at fault.

## Reproduce

```python
import io, deflate

buf = io.BytesIO()
stream = deflate.DeflateIO(buf, deflate.RAW, 15, False)
stream.close()

print(len(buf.getvalue()))          # 0

deflate.DeflateIO(io.BytesIO(buf.getvalue()), deflate.RAW, 15, False).read()
# EOFError
```

CPython, for comparison:

```python
import zlib
zlib.compressobj(9, zlib.DEFLATED, -15).flush()   # b'\x03\x00'
```

`write(b'')` before `close()` behaves the same way — the trigger is that nothing was
written, not the absence of a `write` call.

## Why it matters

The failure surfaces far from its cause.

A ZIP archive stores each member's compressed data along with its method. An empty member —
an `__init__.py`, a placeholder, a truncated log — is written with method *deflate* and zero
bytes of data. The archive looks complete, the writer reports success, and it is only when
someone opens it later, possibly on another machine, that the member turns out to be
undecodable. Empty files are common enough in a Python package that this is not an edge
case in practice.

The same applies to anything that writes gzip: a zero-byte body is not a truncated gzip
stream, it is not a gzip stream at all.

## Environment

| | |
|---|---|
| MicroPython | `v1.29.0-preview.673.g06bcfd5b74`, commit `06bcfd5b7` |
| Port | unix, built with `MICROPY_PY_DEFLATE_COMPRESS=1` |
| CPython | 3.13.3 |
| Host | macOS 15.5, arm64 |
| Date | 2026-08-06 |

Also reproduced on an ESP32-P4 (Waveshare ESP32-P4-NANO) running the same commit.

## Reproducing

```sh
./run.sh /path/to/micropython
```

That is the whole thing. It prints what MicroPython produces, what CPython produces, and
then the comparison. With no argument it looks for `micropython` on your `PATH`.

**Compression is off in a default build** — `MICROPY_PY_DEFLATE_COMPRESS` only turns on at
ROM level `FULL_FEATURES` and the unix port defaults to `CORE_FEATURES`, so `DeflateIO`
exists with no `write` method and there is nothing to measure. `run.sh` detects this and
builds a `build-compress` variant for you. To do it by hand:

```sh
make -C /path/to/micropython/ports/unix BUILD=build-compress CFLAGS_EXTRA=-DMICROPY_PY_DEFLATE_COMPRESS=1
```

<details>
<summary>Running the pieces directly</summary>

```sh
/path/to/micropython probe.py    # what MicroPython produces
python3              probe.py    # the CPython reference
```

```sh
pip install pytest
pytest --interpreter /path/to/micropython
```

</details>

## Running

```sh
python3 probe.py                                   # CPython reference
./ports/unix/build-compress/micropython probe.py   # MicroPython
```

Or through pytest, which compares them:

```sh
pip install pytest
pytest --interpreter micropython=./ports/unix/build-compress/micropython
```

**The tests fail while the bug is present.** That is deliberate: this folder is a
verification tool, so applying a fix and seeing the suite turn green is the check. Six
assertions fail today — zero bytes and a failed round trip, for each of the three formats.

## Files

| File | Role |
|---|---|
| `run.sh` | one-command entry point: builds a compression-enabled interpreter if needed, runs everything |
| `probe.py` | measures compression of empty input. Runs under MicroPython (`deflate`) and CPython (`zlib`/`gzip`), reporting the same measurements from both |
| `conftest.py` | pytest options and fixtures |
| `test_deflate_empty.py` | the assertions |

## Suggested fix

`close()` on a `DeflateIO` opened for writing should flush a final empty block, and emit the
format's header and trailer where the format has them, so the output is decodable even when
nothing was written.

The round trip is the property worth testing: an implementation that cannot read back what
it just wrote is broken independently of what any other implementation does.
