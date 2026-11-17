#!/usr/bin/env python3
"""Make small scratch copies reproducing a temporary name's damaged inode.

Uses installed e2fsprogs executables, not their source. Nothing is mounted.
Each case starts from a clean 16 MiB ext2 image. The allocated-zero case
matches issue #442: the directory and allocation bit survive, the inode
is all zero. The unused case retains the inode but clears its bitmap bit.
Only recipes, logs, and assertions belong in the repository.
"""
import argparse
import re
import shutil
import subprocess
from pathlib import Path

NAME = '/bin/burrowd.pax-tmp'


def run(argv, **kwargs):
    return subprocess.run([str(a) for a in argv], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)


def debug(image, command, write=False):
    p = run(['debugfs', *(['-w'] if write else []), '-R', command, image], check=True)
    # debugfs exits zero for many command failures. Callers verify the result
    # independently rather than interpreting that exit as a mutation witness.
    return p.stdout


def make(work):
    work.mkdir(parents=True, exist_ok=False)
    clean = work / 'clean.img'
    with clean.open('wb') as f:
        f.truncate(16 * 1024 * 1024)
    p = run(['mke2fs', '-q', '-F', '-t', 'ext2', '-b', '4096', '-I', '256',
             '-O', 'filetype,sparse_super,large_file,^resize_inode,^dir_index,^ext_attr',
             clean], check=True)
    (work / 'mke2fs.log').write_text(p.stdout)
    empty = work / 'empty'
    empty.write_bytes(b'')
    debug(clean, 'mkdir /bin', True)
    debug(clean, f'write {empty} /bin/kept', True)
    debug(clean, f'write {empty} {NAME}', True)
    stat = debug(clean, f'stat {NAME}')
    ino = int(re.search(r'Inode:\s+(\d+)', stat)[1])
    p = run(['e2fsck', '-fn', clean])
    (work / 'clean.fsck').write_text(p.stdout)
    assert p.returncode == 0, p.stdout
    for case, command in [('zero', f'clri <{ino}>'), ('unused', f'freei <{ino}>')]:
        image = work / f'{case}.img'
        shutil.copyfile(clean, image)
        mutation = debug(image, command, True)
        listing = debug(image, 'ls -l /bin')
        stat = debug(image, f'stat <{ino}>')
        bit = debug(image, f'testi <{ino}>')
        fsck = run(['e2fsck', '-fn', image])
        (work / f'{case}.before.txt').write_text(mutation + listing + stat + bit + fsck.stdout)
        assert listing.count('burrowd.pax-tmp') == 1, listing
        assert fsck.returncode == 4, fsck.stdout
        if case == 'zero':
            assert 'deleted/unused inode' in fsck.stdout, fsck.stdout
            assert re.search(r'Mode:\s+0000\b', stat), stat
            assert re.search(r'Links:\s+0\b', stat), stat
            assert re.search(r'Size:\s+0\b', stat), stat
            assert 'is marked in use' in bit, bit
        else:
            assert 'not in use' in bit, bit
            assert re.search(r'Mode:\s+0644\b', stat), stat
        print(f'PASS fixture-{case}: one temporary name, inode {ino}, verified damage', flush=True)
    (work / 'inode.txt').write_text(f'{ino}\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('work', type=Path)
    make(p.parse_args().work.resolve())
