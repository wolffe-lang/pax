#!/usr/bin/env bash
# Full disk written on PAX to a second blank virtio device, then booted alone.
# Kernel/tools are px79 99b3bf3b until that prerequisite merges.
set -euo pipefail
L=$HOME/lanes/px69
P=$L/pax
K=$L/px79
W=$L/from-pax
mkdir -p "$W"
export PAX_CACHE=$L/cache PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px69-ubuntu TMPDIR=$L/tmp SOURCE_DATE_EPOCH=1700000000
ulimit -c 0
python3 -I - "$L" "$W" <<'PY'
from pathlib import Path
import shutil,sys
l,w=map(Path,sys.argv[1:]);t=w/'tree'
shutil.copytree(l/'installed/stage/tree',t,symlinks=True)
shutil.copyfile(Path((l/'kernel79/elf.path').read_text().strip()),t/'boot/pax')
attrs=(l/'installed/stage/attrs').read_text()
attrs+='/etc/disktools.attrs 644 0 0 0\n/etc/pax-run.play 644 0 0 0\n'
(w/'attrs').write_text(attrs);(t/'etc/disktools.attrs').write_text(attrs)
shutil.copyfile(t/'etc/pax-run',t/'etc/pax-run.play')
env='/bin/env SOURCE_DATE_EPOCH=1700000000 '
commands=['/bin/cp /etc/pax-run.play /etc/pax-run',env+'/bin/paxgpt --seed pax-playground /dev/vdb 1:esp:4096:135167:esp 2:linux:135168:1048535:root 3:bios:2048:4095:bios',env+'/bin/paxfat --offset 2M --seed pax-playground mkfs /dev/vdb 64M']
for d in ['/EFI','/EFI/BOOT','/boot','/boot/limine']:commands.append(env+f'/bin/paxfat --offset 2M mkdir /dev/vdb {d}')
for a,b in [('boot/EFI/BOOT/BOOTX64.EFI','EFI/BOOT/BOOTX64.EFI'),('boot/limine/limine.conf','boot/limine/limine.conf'),('boot/limine/limine-bios.sys','boot/limine/limine-bios.sys'),('boot/pax','boot/pax')]:commands.append(env+f'/bin/paxfat --offset 2M copy /dev/vdb /{a} /{b}')
commands += [env+'/bin/paxext2 --from / --attrs /etc/disktools.attrs --exclude /dev --exclude /proc --exclude /sys --exclude /tmp --exclude /lost+found --label pax-root --inodes 16384 --offset 66M 467644416 /dev/vdb','/bin/limine bios-install /dev/vdb 3']
(w/'install.run').write_text('\n'.join(commands)+'\n')
assert len(commands)==13
PY
printf 'expected installed tree start\n'
"$L/container-exec" "$L/bin/paxext2" --from "$W/tree" --attrs "$W/attrs" --label pax-root --inodes 16384 467644416 "$W/expected-root.img"
# Only the bootstrap's startup file differs; PAX's first command restores it
# before copying. kernel/tree.small_file snapshots the run list into a page.
cp "$W/install.run" "$W/tree/etc/pax-run"
python3 -I - "$P" "$W" <<'PY'
from pathlib import Path
import subprocess,sys
p,w=map(Path,sys.argv[1:]);args=[];attrs={}
import shlex
for l in (w/'attrs').read_text().splitlines():
 v=shlex.split(l)
 if v:attrs[v[0]]=v[1:4]
for f in sorted((w/'tree').rglob('*')):
 n='/'+str(f.relative_to(w/'tree'));a=attrs.get(n,['755' if f.is_dir() else '644','0','0'])
 if f.is_symlink():args.append(n+'->'+f.readlink().as_posix()+':'+':'.join(a[1:]))
 elif f.is_dir():args.append(n+'/:'+':'.join(a))
 else:args.append(n+'='+str(f)+':'+':'.join(a))
subprocess.run([str(p/'tools/mkinitramfs'),str(w/'bootstrap.cpio'),*args],check=True,stdout=(w/'cpio.log').open('w'))
PY
"$P/tools/mkdisk" --gpt --no-journal --kernel "$(cat "$L/kernel79/elf.path")" --root "$W/bootstrap.cpio" --label pax-bootstrap 512M "$W/bootstrap.img" > "$W/bootstrap.log" 2>&1
truncate -s 512M "$W/target.img"
printf 'PAX install on vdb start %s\n' "$(date -Is)"
PAX_BUILD=$W "$K/tools/qemu-halt" --boot-disk --drive "$W/target.img" --firmware bios --timeout 1200 --qemu -m --qemu 1G --serial "$W/install.serial" --elf "$(cat "$L/kernel79/elf.path")" --marker halt "$W/bootstrap.img" > "$W/install.boot" 2>&1
python3 -I - "$W" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=(p/'install.serial').read_text()
assert s.count('exit_group 0')==13,s
assert 'installed successfully' in s,s
assert 'block: vdb:' in s,s
assert not any(x in s for x in ['paxgpt: invalid','paxfat:','paxext2:','PANIC']),s
with (p/'target.img').open('rb') as src,(p/'target-root.img').open('wb') as dst:
 src.seek(135168*512);left=467644416
 while left:
  b=src.read(min(left,1048576));assert b;dst.write(b);left-=len(b)
print('PASS: 13 installation commands exit 0 on PAX; target raw disk written',flush=True)
PY
"$P/tools/e2fs" "$W" e2fsck -fn "$W/target-root.img" > "$W/target.fsck" 2>&1
"$P/tools/e2tree" "$W/expected-root.img" > "$W/expected.tree"
"$P/tools/e2tree" "$W/target-root.img" > "$W/target.tree"
cmp "$W/expected.tree" "$W/target.tree"
printf 'PASS: from-PAX root equals Linux writer tree (%s rows)\n' "$(wc -l < "$W/target.tree")"
. "$K/tools/lib.sh"
read -r code vars <<< "$(find_ovmf)"
[ -n "$code" ]
for fw in bios uefi; do
 printf 'target-alone playground %s start\n' "$fw"
 cp --sparse=always "$W/target.img" "$W/$fw.img"
 extra=(); [ "$fw" != uefi ] || extra=("$code")
 python3 -I "$L/session.py" "$W/$fw.img" "$W/$fw.serial" "${extra[@]}" > "$W/$fw.session" 2>&1
 python3 -I "$L/check-play.py" "$W/$fw.serial" > "$W/$fw.compare"
 cat "$W/$fw.compare"
 python3 -I - "$W/$fw.img" "$W/check-root.img" <<'PY'
import sys
with open(sys.argv[1],'rb') as a,open(sys.argv[2],'wb') as b:
 a.seek(135168*512);left=467644416
 while left:
  x=a.read(min(left,1048576));assert x;b.write(x);left-=len(x)
PY
 "$P/tools/e2fs" "$W" e2fsck -fn "$W/check-root.img" > "$W/$fw.fsck" 2>&1
 "$P/tools/e2fs" "$W" dumpe2fs -h "$W/check-root.img" > "$W/$fw.state" 2>&1
 grep -Eq '^Filesystem state: +clean$' "$W/$fw.state"
 grep -Eq '^Mount count: +2$' "$W/$fw.state"
 rm "$W/check-root.img"
done
sha256sum "$W/target.img" > "$W/target.sha256"
sha256sum -c "$W/target.sha256"
printf 'PASS: whole disk made on PAX boots alone under both firmwares; both playground sessions persisted and left root clean\n'
