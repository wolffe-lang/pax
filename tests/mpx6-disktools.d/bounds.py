#!/usr/bin/env python3
"""GPT above 2 TiB with a fixed 64 MiB FAT32 ESP; bounded independent reads."""
import os
from pathlib import Path
import struct
import subprocess
import sys
import zlib

binary, out, oracle = map(Path, sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)
os.environ['SOURCE_DATE_EPOCH'] = '1700000000'
image = out / 'large-gpt.img'
size = 3 << 40


def run(name, args):
    p = subprocess.run([str(x) for x in args], capture_output=True)
    (out / (name + '.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, (name, p.returncode, p.stdout, p.stderr)
    return p.stdout + p.stderr


try:
    run('B-gpt-create', [binary / 'paxgpt', '--size', size, image,
        '1:esp:4096:135167:esp', '2:linux:135168:%d:root' % (size // 512 - 34), '3:bios:2048:4095:bios'])
    with image.open('rb') as f:
        mbr = f.read(512)
        assert mbr[450] == 0xee and mbr[510:] == b'\x55\xaa'
        assert struct.unpack_from('<II', mbr, 454) == (1, 0xffffffff), 'B-protective-mbr-saturation'
        for lba, alternate in [(1, size // 512 - 1), (size // 512 - 1, 1)]:
            f.seek(lba * 512)
            header = bytearray(f.read(512))
            assert header[:8] == b'EFI PART'
            assert struct.unpack_from('<QQ', header, 24) == (lba, alternate)
            length, crc = struct.unpack_from('<II', header, 12)
            struct.pack_into('<I', header, 16, 0)
            assert zlib.crc32(header[:length]) == crc
            entries = struct.unpack_from('<Q', header, 72)[0]
            f.seek(entries * 512)
            assert zlib.crc32(f.read(16384)) == struct.unpack_from('<I', header, 88)[0]
    text = run('B-gpt-oracle', [oracle / 'sgdisk', '-v', image])
    assert b'No problems found' in text and b'Warning' not in text and b'error' not in text.lower(), text
    run('B-fat-create', [binary / 'paxfat', '--offset', '2097152', 'mkfs', image, '67108864'])
    fat = out / 'esp.img'
    with image.open('rb') as f:
        f.seek(2097152)
        fat.write_bytes(f.read(67108864))
    boot = fat.read_bytes()[:512]
    assert struct.unpack_from('<H', boot, 11)[0] == 512
    assert struct.unpack_from('<I', boot, 32)[0] == 131072
    text = run('B-fat-oracle', [oracle / 'fsck.fat', '-n', fat])
    assert len(text.decode().splitlines()) == 2 and b'files,' in text, text
    fat.unlink()
    print('PASS B-gpt-fat: 3 TiB GPT, saturated protective MBR, both CRCs, unchanged 64 MiB FAT32 ESP', flush=True)
finally:
    image.unlink(missing_ok=True)
