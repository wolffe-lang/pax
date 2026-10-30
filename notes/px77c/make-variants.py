#!/usr/bin/env python3
"""px77c: two lane-local copies of px78's tests/mpx6-install.d/metal.py, each edit
asserted to apply exactly once (the diffs are kept beside them):

  metal-noappend.py  the leg unchanged but for the one line that appends the
      target's allow-list line from the host by paxfat: the copy it runs on
      already carries the line (written on macOS by hdiutil, or by the
      runbook's commands under Linux), and the leg's own M0 read-back
      (paxfat cat), M2 (the target alone on the list) and M6 (the stick's
      log: "1 line(s)") say whether the installer read it.
  metal-onedisk.py   kasumi as the maintainer has it on 2026-10-29: every
      drive out but the target SATA SSD. noappend's leg with the NVMe and
      the two other SATA disks removed, so the target is /dev/sda and the
      stick /dev/sdb; the target's identity is the qualify machines'
      (b-old, b-new): model "Samsung SSD 870 EVO 500GB", serial
      S6PXNM0T612345A. With no other disk the no-write witness (M5) has
      nothing to hold; it is kept, over an empty set, and said so.

  make-variants.py REPO OUTDIR
"""
from pathlib import Path
import difflib
import sys

repo, out = map(Path, sys.argv[1:3])
src = (repo/'tests/mpx6-install.d/metal.py').read_text()


def edit(text, old, new):
    n = text.count(old)
    assert n == 1, (n, old)
    return text.replace(old, new)


APPEND = "    run([paxfat, '--offset', esp, 'append', stick, line, '/pax/install-targets'])\n"
noappend = edit(src, APPEND,
                "    # px77c: the copy already carries the line (macOS or Linux wrote it); no append here.\n")

one = noappend
one = edit(one, "TARGET = {'model': 'Samsung SSD 870 EVO 500GB', 'serial': 'PX78-TARGET-0001', 'bytes': 500107862016}",
           "TARGET = {'model': 'Samsung SSD 870 EVO 500GB', 'serial': 'S6PXNM0T612345A', 'bytes': 500107862016}")
one = edit(one, """    foreign_disk(d/'nvme.img', NVME, [('esp', 2048, 2048 + gib - 1), ('linux', 2048 + gib, None)])
    foreign_disk(d/'steam.img', STEAM, [('linux', 2048, None)])
    q = SANDISK['bytes'] // 512 // 4
    foreign_disk(d/'sandisk.img', SANDISK, [('linux', 2048, q - 1), ('linux', q, 2 * q - 1), ('linux', 2 * q, 3 * q - 1), ('linux', 3 * q, None)])
""", "    # px77c: kasumi on 2026-10-29: the target alone.\n")
one = edit(one, "    return {n: extents_sha(d/(n + '.img')) for n in ('nvme', 'steam', 'sandisk')}",
           "    return {}  # px77c: no disk but the target")
one = edit(one, """    a += ['-device', 'usb-kbd,bus=xhci.0',
          '-drive', f'file={d/"nvme.img"},if=none,id=nv,format=raw', '-device', f'nvme,serial={NVME["serial"]},drive=nv',
          '-drive', f'file={d/"steam.img"},if=none,id=sa,format=raw',
          '-device', f'ide-hd,bus=ide.0,drive=sa,model={STEAM["model"]},serial={STEAM["serial"]}',
          '-drive', f'file={d/"sandisk.img"},if=none,id=sb,format=raw',
          '-device', f'ide-hd,bus=ide.1,drive=sb,model={SANDISK["model"]},serial={SANDISK["serial"]}',
          '-drive', f'file={d/"target.img"},if=none,id=sc,format=raw,discard=unmap,detect-zeroes=unmap',
          '-device', f'ide-hd,bus=ide.2,drive=sc,model={TARGET["model"]},serial={TARGET["serial"]}'""",
           """    a += ['-device', 'usb-kbd,bus=xhci.0',
          '-drive', f'file={d/"target.img"},if=none,id=sc,format=raw,discard=unmap,detect-zeroes=unmap',
          '-device', f'ide-hd,bus=ide.0,drive=sc,model={TARGET["model"]},serial={TARGET["serial"]}'""")
one = edit(one, """        need(flat, f'refused: not on the install allow-list: /dev/sda model={LINUX_MODEL} serial={STEAM["serial"]}', 'M2-right-model-wrong-serial')
        need(flat, f'refused: not on the install allow-list: /dev/nvme0n1 model=QEMU NVMe Ctrl serial={NVME["serial"]}', 'M2-nvme-refused')
        need(flat, f'refused: not on the install allow-list: /dev/sdb model={SANDISK["model"][:16].rstrip()} serial={SANDISK["serial"]}', 'M2-sdb-refused')
        need(flat, 'refused: a PAX live medium (the boot stick, or a copy of it): /dev/sdd', 'M2-stick-refused')
        need(flat, f'/dev/sdc bytes={TARGET["bytes"]} sector=512 model={LINUX_MODEL} serial={TARGET["serial"]}', 'M2-target-listed')
        print('PASS M2-check: the target alone on the list; sda (the right model, the wrong serial), sdb and the NVMe refused by name; the stick refused before the list', flush=True)""",
           """        need(flat, 'install allow-list /dev/sdb1:/pax/install-targets, 1 line(s)', 'M2-list-read')
        need(flat, 'refused: a PAX live medium (the boot stick, or a copy of it): /dev/sdb', 'M2-stick-refused')
        need(flat, f'/dev/sda bytes={TARGET["bytes"]} sector=512 model={LINUX_MODEL} serial={TARGET["serial"]}', 'M2-target-listed')
        need(flat, 'on the install allow-list', 'M2-target-allowed')
        print('PASS M2-check: the one disk, the target, on the list; the stick refused before the list', flush=True)""")
one = edit(one, r"num = re.search(r'^[> ] (\d+)\. /dev/sdc ', m.unwrapped(page), re.M)",
           r"num = re.search(r'^[> ] (\d+)\. /dev/sda ', m.unwrapped(page), re.M)")
one = edit(one, r"tok = re.search(r'^confirmation (ERASE /dev/sdc \S+ \d+ [0-9a-f]{64})$', m.unwrapped(plan), re.M)",
           r"tok = re.search(r'^confirmation (ERASE /dev/sda \S+ \d+ [0-9a-f]{64})$', m.unwrapped(plan), re.M)")
one = edit(one, "print(f'PASS M4-install: guided, to the listed /dev/sdc;", "print(f'PASS M4-install: guided, to the listed /dev/sda;")
one = edit(one, """    for needle in ['PAX install log /pax/logs/install-1.txt', 'install allow-list /dev/sdd1:/pax/install-targets, 1 line(s)',
                   f'refused: not on the install allow-list: /dev/sda model={LINUX_MODEL} serial={STEAM["serial"]}',
                   'refused: a PAX live medium (the boot stick, or a copy of it): /dev/sdd',
                   'confirmation ERASE /dev/sdc',""",
           """    for needle in ['PAX install log /pax/logs/install-1.txt', 'install allow-list /dev/sdb1:/pax/install-targets, 1 line(s)',
                   'refused: a PAX live medium (the boot stick, or a copy of it): /dev/sdb',
                   'confirmation ERASE /dev/sda',""")
one = edit(one, "need(logtext, f'sha256 /dev/sdc{k} first MiB (byte {at}): {want}', 'M6-stick-log')",
           "need(logtext, f'sha256 /dev/sda{k} first MiB (byte {at}): {want}', 'M6-stick-log')")
one = edit(one, "need(m.unwrapped(s), 'refused: the running root: /dev/sdc', 'M9-running-root')",
           "need(m.unwrapped(s), 'refused: the running root: /dev/sda', 'M9-running-root')")
one = edit(one, "    for n in ('nvme', 'steam', 'sandisk', 'target'):\n", "    for n in ('target',):\n")
one = edit(one, "    print('PASS M5-witness: the NVMe, the Steam and the SanDisk images byte-identical over their allocated extents before and after both boots: '\n          + ', '.join(f'{k} {v}' for k, v in result['witness_after'].items()), flush=True)",
           "    print('PASS M5-witness: no disk but the target on this machine (kasumi on 2026-10-29): nothing to hold', flush=True)")

out.mkdir(parents=True, exist_ok=True)
for name, text in (('metal-noappend.py', noappend), ('metal-onedisk.py', one)):
    (out/name).write_text(text)
    diff = difflib.unified_diff(src.splitlines(True), text.splitlines(True), 'tests/mpx6-install.d/metal.py', name)
    (out/(name + '.diff')).write_text(''.join(diff))
    print(name, len(text.splitlines()), 'lines')
