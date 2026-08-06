#!/usr/bin/env bash
# Run the JSON conformance report. One argument, no flags to get wrong.
#
#   ./run.sh                        # find micropython on PATH
#   ./run.sh /path/to/micropython   # use a specific build
#
# The test corpus is downloaded on first run and cached next to this script, so
# there is nothing to clone by hand and nothing to pass in.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORPUS="$HERE/.JSONTestSuite"

# --------------------------------------------------------------- interpreter
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

# -------------------------------------------------------------------- corpus
# Already have JSONTestSuite cloned somewhere? Point JSON_TEST_SUITE at it.
if [ -n "${JSON_TEST_SUITE:-}" ]; then
    CORPUS="$JSON_TEST_SUITE"
    if [ ! -d "$CORPUS/test_parsing" ]; then
        echo "error: JSON_TEST_SUITE=$CORPUS has no test_parsing/ directory." >&2
        exit 1
    fi
elif [ ! -d "$CORPUS/test_parsing" ]; then
    echo ">> downloading the test corpus (once)" >&2
    rm -rf "$CORPUS"
    git clone --depth 1 --quiet https://github.com/nst/JSONTestSuite.git "$CORPUS"
fi

echo ">> interpreter: $MICROPYTHON" >&2
echo ">> $("$MICROPYTHON" -c 'import sys; print(sys.version)' 2>/dev/null || echo 'version unknown')" >&2
echo ">> corpus:      $CORPUS/test_parsing" >&2
echo >&2

exec python3 "$HERE/report.py" \
    --suite "$CORPUS/test_parsing" \
    --interpreter "micropython=$MICROPYTHON"
