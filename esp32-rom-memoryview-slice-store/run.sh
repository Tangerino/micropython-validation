#!/usr/bin/env bash
# Reproduce the ESP32 slice-store panic. One argument: the board's serial port.
#
#   ./run.sh /dev/tty.usbserial-XXXX
#
# This one needs hardware: the fault is a write to a const object in flash, and
# only the esp32 port places a memoryview there (machine.mem_backup). It runs
# probe.py on the board with mpremote and shows the serial output. On v1.29.0
# the board panics with LoadStoreError at the first slice store and reboots;
# on a firmware with the fix (master after 2026-08-27) it prints OK.
#
# The board must be idle at a REPL: stop or rename main.py first if an
# application runs there, and expect the first five bytes of RTC user memory
# to be touched (they are restored on a fixed firmware; on a faulty one the
# board reboots before the restore, with byte 0 set to 0x11).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-}"
if [ -z "$PORT" ]; then
    echo "error: pass the board's serial port:  ./run.sh /dev/tty.usbserial-XXXX" >&2
    exit 1
fi
if ! command -v mpremote >/dev/null; then
    echo "error: mpremote not found.  pip install mpremote" >&2
    exit 1
fi

echo ">> port: $PORT" >&2
echo ">> $(mpremote connect "$PORT" exec 'import sys; print(sys.version)' 2>/dev/null || echo 'board did not answer')" >&2
echo >&2
echo "== on the board =="
echo "   (a reboot here, after 'about to store', is the bug)"
mpremote connect "$PORT" run "$HERE/probe.py" || {
    echo >&2
    echo ">> mpremote lost the board: it rebooted. Watch the serial console for the Guru Meditation dump." >&2
    exit 1
}
