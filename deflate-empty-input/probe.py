"""Measure what MicroPython's `deflate` produces for empty input.

Runs under MicroPython (using `deflate`) and under CPython (using `zlib` and
`gzip`), reporting the same measurements from both so they can be compared
directly.

    micropython  probe.py
    python3      probe.py

Output is one tab-separated line per measurement::

    compress	RAW	0
    roundtrip	RAW	FAIL	EOFError
    read_reference	RAW	OK

⚠️ Compression is **not** enabled in a default MicroPython build:
``MICROPY_PY_DEFLATE_COMPRESS`` only turns on at ROM level FULL_FEATURES, and the
unix port defaults to CORE_FEATURES. See the README for the build line.

No f-strings and no argparse: this has to run on a bare MicroPython build.
"""

import io
import sys

MICROPYTHON = sys.implementation.name == 'micropython'

#: A raw deflate stream for empty input, produced by zlib. Used to check that
#: the decompressor is fine even when the compressor is not.
REFERENCE = {
    'RAW': b'\x03\x00',
    'ZLIB': b'\x78\xda\x03\x00\x00\x00\x00\x01',
}


def emit(*fields):
    sys.stdout.write('\t'.join(str(f) for f in fields) + '\n')


def formats():
    """``[(name, compress, decompress)]`` for this runtime."""
    if MICROPYTHON:
        import deflate

        def make(fmt):
            def compress(data):
                buf = io.BytesIO()
                stream = deflate.DeflateIO(buf, fmt, 15, False)
                if data:
                    stream.write(data)
                stream.close()
                return buf.getvalue()

            def decompress(blob):
                return deflate.DeflateIO(io.BytesIO(blob), fmt, 15, False).read()

            return compress, decompress

        return [
            ('RAW',) + make(deflate.RAW),
            ('ZLIB',) + make(deflate.ZLIB),
            ('GZIP',) + make(deflate.GZIP),
        ]

    import gzip
    import zlib

    def raw_compress(data):
        c = zlib.compressobj(9, zlib.DEFLATED, -15)
        return c.compress(data) + c.flush()

    def zlib_compress(data):
        c = zlib.compressobj(9, zlib.DEFLATED, 15)
        return c.compress(data) + c.flush()

    def gzip_compress(data):
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0) as f:
            if data:
                f.write(data)
        return buf.getvalue()

    return [
        ('RAW', raw_compress, lambda blob: zlib.decompressobj(-15).decompress(blob)),
        ('ZLIB', zlib_compress, zlib.decompress),
        ('GZIP', gzip_compress, gzip.decompress),
    ]


def has_compression():
    """Whether this build can compress at all."""
    if not MICROPYTHON:
        return True
    try:
        import deflate

        return hasattr(deflate.DeflateIO(io.BytesIO(), deflate.RAW, 15, False), 'write')
    except Exception:
        return False


def main():
    emit('runtime', sys.implementation.name, sys.version)

    if not has_compression():
        emit(
            'error',
            'no-compression',
            'build with CFLAGS_EXTRA=-DMICROPY_PY_DEFLATE_COMPRESS=1',
        )
        return 1

    for name, compress, decompress in formats():
        # 1. How many bytes does empty input produce?
        try:
            blob = compress(b'')
            emit('compress', name, len(blob))
        except Exception as exc:
            emit('compress', name, 'ERROR', type(exc).__name__)
            continue

        # 2. Can the same implementation read its own output back?
        #    This is the property that matters: a compressor whose output its
        #    own decompressor rejects is broken regardless of what any other
        #    implementation does.
        try:
            back = decompress(blob)
            emit('roundtrip', name, 'OK' if back == b'' else 'WRONG', repr(back))
        except Exception as exc:
            emit('roundtrip', name, 'FAIL', type(exc).__name__)

        # 3. Sanity: non-empty input still works, so the fault is specific.
        try:
            blob = compress(b'hello')
            back = decompress(blob)
            emit('nonempty', name, 'OK' if back == b'hello' else 'WRONG', len(blob))
        except Exception as exc:
            emit('nonempty', name, 'FAIL', type(exc).__name__)

        # 4. Can it read a reference stream produced by zlib?
        #    Separates a broken compressor from a broken decompressor.
        if name in REFERENCE:
            try:
                back = decompress(REFERENCE[name])
                emit('read_reference', name, 'OK' if back == b'' else 'WRONG')
            except Exception as exc:
                emit('read_reference', name, 'FAIL', type(exc).__name__)

    return 0


if __name__ == '__main__':
    sys.exit(main())
