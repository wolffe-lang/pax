#!/usr/bin/env python3
# px62 (kasumi, debug only): the guest pages QEMU's write-to-code path
# (trace event memory_notdirty_write_access) saw most, split by whether
# the guest wrote them through the HHDM (0xffff8...) or another address
# (the kernel stacks are at 0xffffd00000000000 + slot * 64 KiB).
#   notdirty-pages.py TRACE.log
import collections
import sys
hh = collections.Counter()
other = collections.Counter()
va_of = {}
with open(sys.argv[1]) as f:
    for line in f:
        if not line.startswith("memory_notdirty_write_access"):
            continue
        p = line.split()
        va, ra = int(p[1], 16), int(p[3], 16)
        if va >> 44 == 0xffff8:
            hh[ra >> 12] += 1
        else:
            other[ra >> 12] += 1
            va_of[ra >> 12] = va
print("notdirty writes through the HHDM: %d on %d pages (at most 512 a page: a page written whole once)" % (sum(hh.values()), len(hh)))
print("most written pages through other addresses:")
for k, v in other.most_common(8):
    print("  frame %#x: %d writes, last at %#x" % (k << 12, v, va_of[k]))
