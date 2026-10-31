"""Store a same-length slice into machine.mem_backup() and report whether the board survives.

Runs on the board, not on the host:

    mpremote connect /dev/tty.usbserial-XXXX run probe.py

``machine.mem_backup()`` returns a memoryview whose object lives in flash
(``static const mp_obj_array_t machine_mem_backup_regions[]`` in
ports/esp32/machine_mem_backup.c). Up to v1.29.0, a slice store into any
array or memoryview unconditionally rewrote the object's ``len`` and ``free``
fields, even when the slice did not change size. Writing to a const object in
DROM is a LoadStoreError on the ESP32: the board panics and reboots, so the
last line this script prints is the one before the store.

The steps are the same as tests/extmod/machine_mem_backup_slice.py upstream,
which was added together with the fix. Element stores are done first to show
that they are fine; only the slice store is affected.

Prints SKIP where there is no ``machine.mem_backup`` (every port but esp32 as of
v1.29.0) and OK on a fixed firmware. Writes to the first five bytes of the RTC
user memory, the same bytes the upstream test writes; back them up if you keep
anything there (RTC.memory() shares the buffer on esp32).
"""

import sys

try:
    import machine

    mem = machine.mem_backup()
except (ImportError, AttributeError):
    print("SKIP\tno machine.mem_backup on this port")
    raise SystemExit

print("runtime\t%s" % sys.version)
print("region\t%d bytes, itemsize %d" % (len(mem), mem.itemsize))

saved = bytes(mem[0:5])
print("saved\t%s" % saved.hex())

# Element stores never touched len/free: these are fine on every version.
mem[0] = 0x11
print("element_store\tOK\t%02x" % mem[0])

# Same-length slice store: len_adj == 0, yet v1.29.0 writes o->free and o->len.
print("slice_store\tabout to store mem[0:1] = b'\\x11' (board reboots here on v1.29.0)")
mem[0:1] = b"\x11"
print("slice_store\tOK\t%s" % mem[0:1].hex())
mem[0:3] = b"\x22\x33\x44"
print("slice_store\tOK\t%s" % mem[0:3].hex())
mem[1:5] = b"\x55\x66\x77\x88"
print("slice_store\tOK\t%s" % mem[1:5].hex())

mem[0:5] = saved
print("restored\t%s" % bytes(mem[0:5]).hex())
print("OK")
