#!/usr/bin/env bash
# Reproduce the deflate empty-input defect. One argument, no flags to get wrong.
#
#   ./run.sh                        # find micropython on PATH
#   ./run.sh /path/to/micropython   # use a specific build
#
# Prints the measurement, then runs the pytest comparison against CPython if
# pytest is installed.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MICROPYTHON="${1:-}"
if [ -z "$MICROPYTHON" ]; then
    MICROPYTHON="$(command -v micropython || true)"
fi
if [ -z "$MICROPYTHON" ] || [ ! -x "$MICROPYTHON" ]; then
    echo "error: no MicroPython binary." >&2
    echo >&2
    echo "Pass one:" >&2
    echo "    ./run.sh /path/to/micropython" >&2
    echo >&2
    echo "Or build the unix port:" >&2
    echo "    make -C /path/to/micropython/ports/unix" >&2
    exit 1
fi

# Compression is off in a default build: MICROPY_PY_DEFLATE_COMPRESS only turns
# on at ROM level FULL_FEATURES and the unix port defaults to CORE_FEATURES. So
# DeflateIO exists with no write method, and there is nothing to measure.
has_compress() {
    "$1" -c 'import deflate, io; deflate.DeflateIO(io.BytesIO(), deflate.RAW).write' \
        >/dev/null 2>&1
}

if ! has_compress "$MICROPYTHON"; then
    echo ">> $MICROPYTHON was built without deflate compression." >&2

    # ports/unix/<build>/micropython -> the repository root, if that is the shape.
    ROOT="$(cd "$(dirname "$MICROPYTHON")/../../.." 2>/dev/null && pwd || true)"
    if [ -z "$ROOT" ] || [ ! -d "$ROOT/ports/unix" ]; then
        echo >&2
        echo "Build one with compression enabled:" >&2
        echo "    make -C /path/to/micropython/ports/unix BUILD=build-compress CFLAGS_EXTRA=-DMICROPY_PY_DEFLATE_COMPRESS=1" >&2
        exit 1
    fi

    BUILT="$ROOT/ports/unix/build-compress/micropython"
    if [ ! -x "$BUILT" ]; then
        echo ">> building one at $BUILT" >&2
        echo >&2
        make -C "$ROOT/ports/unix" submodules >/dev/null
        make -C "$ROOT/ports/unix" BUILD=build-compress \
            CFLAGS_EXTRA=-DMICROPY_PY_DEFLATE_COMPRESS=1 \
            -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)" >/dev/null
        echo >&2
    fi
    MICROPYTHON="$BUILT"
    has_compress "$MICROPYTHON" || { echo "error: the build still has no compression." >&2; exit 1; }
fi

echo ">> interpreter: $MICROPYTHON" >&2
echo ">> $("$MICROPYTHON" -c 'import sys; print(sys.version)' 2>/dev/null || echo 'version unknown')" >&2
echo >&2

echo "== what MicroPython produces =="
"$MICROPYTHON" "$HERE/probe.py"
echo >&2
echo "== what CPython produces (the reference) =="
python3 "$HERE/probe.py"
echo >&2

if python3 -c 'import pytest' 2>/dev/null; then
    echo "== comparison =="
    echo "   (tests fail while the bug is present -- that is the point)"
    echo >&2
    exec python3 -m pytest "$HERE/test_deflate_empty.py" --interpreter "$MICROPYTHON"
else
    echo "install pytest for the side-by-side comparison:  pip install pytest"
fi
