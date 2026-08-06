#!/usr/bin/env bash
# Reproduce the unittest defects. One argument, no flags to get wrong.
#
#   ./run.sh                        # find micropython on PATH
#   ./run.sh /path/to/micropython   # use a specific build
#
# micropython-lib is downloaded on first run and cached next to this script, so
# there is nothing to clone by hand. Already have it? Point MICROPY_LIB at it.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB="$HERE/.micropython-lib"

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

if [ -n "${MICROPY_LIB:-}" ]; then
    LIB="$MICROPY_LIB"
fi
UNITTEST="$LIB/python-stdlib/unittest"
if [ ! -d "$UNITTEST" ]; then
    if [ -n "${MICROPY_LIB:-}" ]; then
        echo "error: MICROPY_LIB=$LIB has no python-stdlib/unittest directory." >&2
        exit 1
    fi
    echo ">> downloading micropython-lib (once)" >&2
    rm -rf "$LIB"
    git clone --depth 1 --quiet https://github.com/micropython/micropython-lib.git "$LIB"
fi

echo ">> interpreter: $MICROPYTHON" >&2
echo ">> $("$MICROPYTHON" -c 'import sys; print(sys.version)' 2>/dev/null || echo 'version unknown')" >&2
echo ">> unittest:    $UNITTEST" >&2
echo >&2

echo "== MicroPython =="
python3 "$HERE/probe.py" "$MICROPYTHON" "$UNITTEST"
echo >&2
echo "== CPython (the reference) =="
python3 "$HERE/probe.py" python3
echo >&2

if python3 -c 'import pytest' 2>/dev/null; then
    echo "== comparison =="
    echo "   (tests fail while the bugs are present -- that is the point)"
    echo >&2
    exec python3 -m pytest "$HERE/test_unittest_behaviour.py" \
        --interpreter "$MICROPYTHON" \
        --unittest-path "$UNITTEST"
else
    echo "install pytest for the side-by-side comparison:  pip install pytest"
fi
