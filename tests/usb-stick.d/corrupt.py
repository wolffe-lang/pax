#!/usr/bin/env python3
"""Two deliberate on-image faults; regular disposable images only."""
from pathlib import Path
import stat
import struct
import sys

image = Path(sys.argv[1])
assert stat.S_ISREG(image.stat().st_mode)
with image.open("r+b") as f:
    if sys.argv[2] == "mbr":
        f.seek(458)
        f.write(struct.pack("<I", 1))
    elif sys.argv[2] == "efi":
        # FAT's short directory record is an 11-byte name. Change the
        # BOOTX64.EFI short name, leaving the FAT and file bytes intact.
        data = f.read()
        name = b"BOOTX64 EFI"
        offsets = [i for i in range(2097152, len(data) - 32, 32)
                   if data[i:i + 11] == name and data[i + 11] == 0x20]
        assert len(offsets) == 1, offsets
        f.seek(offsets[0])
        f.write(b"NOTBOOT EFI")
    else:
        raise ValueError("expected mbr or efi")
