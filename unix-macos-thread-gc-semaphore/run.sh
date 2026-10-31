#!/usr/bin/env bash
# Reproduce the macOS thread/GC semaphore collision. One argument, no flags to get wrong.
#
#   ./run.sh                        # find micropython on PATH
#   ./run.sh /path/to/micropython   # use a specific build
#
# Runs the stress alone, then 8 copies at once, three times, and prints what
# happened to each process. Then the pytest comparison if pytest is installed.
# On Linux everything passes: that is the control, the unix port uses sem_init()
# there and no name is involved.
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

echo ">> interpreter: $MICROPYTHON" >&2
echo ">> $("$MICROPYTHON" -c 'import sys; print(sys.version)' 2>/dev/null || echo 'version unknown')" >&2
echo ">> host:        $(uname -s) $(uname -m)" >&2
echo >&2

echo "== what happens to concurrent processes =="
python3 "$HERE/probe.py" "$MICROPYTHON" || true
echo >&2

if python3 -c 'import pytest' 2>/dev/null; then
    echo "== checks =="
    echo "   (tests fail while the bug is present -- that is the point)"
    echo >&2
    exec python3 -m pytest "$HERE/test_thread_gc_semaphore.py" --interpreter "$MICROPYTHON"
else
    echo "install pytest for the checks:  pip install pytest"
fi
