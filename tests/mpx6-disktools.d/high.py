#!/usr/bin/env python3
"""PAX file I/O above 2 TiB through virtio and NVMe; Linux round trip optional.
The local lane requires a live Linux kernel. CI uses the same deterministic
byte oracle and real e2fsck, never a checksum of terabytes of holes.
"""
import argparse
import os
from pathlib import Path
import struct
import subprocess

p = argparse.ArgumentParser()
p.add_argument('repo', type=Path)
p.add_argument('work', type=Path)
p.add_argument('formatter', type=Path)
p.add_argument('kernel', type=Path)
p.add_argument('--linux-kernel', type=Path)
p.add_argument('--linux-modules', type=Path)
a = p.parse_args()
a.work.mkdir(parents=True, exist_ok=True)


def run(name, args):
    r = subprocess.run([str(x) for x in args], capture_output=True)
    (a.work / (name + '.log')).write_bytes(r.stdout + r.stderr)
    assert r.returncode == 0, (name, r.returncode, r.stdout[-5000:], r.stderr[-5000:])
    return r


probe = a.work / 'bigdisk'
run('compile', ['cc', '-static', '-no-pie', '-O1', '-Wall', '-Wextra', '-Werror', a.repo / 'user/elf/bigdisk.c', '-o', probe])
for transport, dev in [('virtio', 'vda'), ('nvme', 'nvme0n1')]:
    image = a.work / (transport + '.img')
    try:
        run(transport + '-fixture', ['python3', '-I', a.repo / 'tests/mpx6-disktools.d/high-fixture.py', a.formatter, image])
        expected, length = 11, 4096
        if a.linux_kernel:
            # Linux writes the already-high inode; PAX must read its bytes.
            linux = a.work / (transport + '-linux-before')
            run(transport + '-linux-before', [a.repo / 'tools/linux-blk', '--kernel', a.linux_kernel,
                '--modules', a.linux_modules, '--busybox', '/usr/bin/busybox', linux, image, probe,
                '--', '/bin/bigdisk - 11 23 4096'])
            log = (linux / 'serial.log').read_text(errors='replace')
            assert 'linux-blk: run 1 status 0' in log and 'linux-blk: unmount 0' in log, log
            expected, length = 23, 8192
        commands = a.work / (transport + '.run')
        commands.write_text('/bin/bigdisk /dev/%s %d 29 %d\n' % (dev, expected, length))
        archive = a.work / (transport + '.cpio')
        iso = a.work / (transport + '.iso')
        run(transport + '-archive', [a.repo / 'tools/mkinitramfs', archive,
            '/bin/bigdisk=' + str(probe) + ':755', '/etc/pax-run=' + str(commands) + ':644'])
        run(transport + '-iso', [a.repo / 'tools/mkimage', '--conf', a.repo / 'boot/limine-initramfs.conf',
            '--add', archive, 'initramfs.cpio', a.kernel, iso])
        serial = a.work / (transport + '.serial')
        drive = '--drive' if transport == 'virtio' else '--nvme'
        run(transport + '-boot', [a.repo / 'tools/qemu-halt', '--firmware', 'bios', '--timeout', '180',
            '--elf', a.kernel, '--serial', serial, '--marker', 'halt', drive, image, iso])
        text = serial.read_text(errors='replace')
        assert 'PASS B-high-file: complete' in text and 'bigdisk pid 1 exit_group 0' in text, text
        assert 'FAIL ' not in text and 'PANIC' not in text and 'wolf-trap' not in text, text
        run(transport + '-fsck', ['e2fsck', '-fn', image])
        # Independent physical readback checks all new data, including the
        # allocation on the inode's high group when Linux was not requested.
        with image.open('rb') as f:
            def read(at, count):
                f.seek(at)
                b = f.read(count)
                assert len(b) == count
                return b
            sb = read(1024, 1024)
            ipg = struct.unpack_from('<I', sb, 40)[0]
            bpg = struct.unpack_from('<I', sb, 32)[0]
            group = (1 << 29) // bpg + 1
            gd = read(4096 + group * 32, 32)
            inode = read(struct.unpack_from('<I', gd, 8)[0] * 4096, 256)
            assert struct.unpack_from('<I', inode, 4)[0] == 8192
            blocks = struct.unpack_from('<II', inode, 40)
            for i, block in enumerate(blocks):
                assert block * 4096 > 1 << 41, (transport, 'B-high-allocation', block)
                want = bytes(((i * 4096 + j) * 17 + 29) & 255 for j in range(4096))
                assert read(block * 4096, 4096) == want, (transport, 'B-high-bytes', i)
        if a.linux_kernel:
            linux = a.work / (transport + '-linux-after')
            run(transport + '-linux-after', [a.repo / 'tools/linux-blk', '--kernel', a.linux_kernel,
                '--modules', a.linux_modules, '--busybox', '/usr/bin/busybox', linux, image, probe,
                '--', '/bin/bigdisk - 29 -1 8192'])
            log = (linux / 'serial.log').read_text(errors='replace')
            assert 'linux-blk: run 1 status 0' in log and 'linux-blk: unmount 0' in log, log
            print('PASS B-high-linux-%s: Linux writes/PAX reads; PAX writes/Linux reads' % transport, flush=True)
        print('PASS B-high-%s: inode, both data blocks and readback beyond 2 TiB; e2fsck clean' % transport, flush=True)
    finally:
        image.unlink(missing_ok=True)
print('HIGH DISK: PASS; 0 SKIP; live Linux=%s' % bool(a.linux_kernel), flush=True)
