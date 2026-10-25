#!/usr/bin/env bash
# kasumi: full installed tree, all-Wolf formatters, independent Linux tools,
# Linux guest find, and the playground session. Caller owns the core lock.
set -euo pipefail
L=$HOME/lanes/px69
P=$L/pax
W=$L/installed
mkdir -p "$W" "$W/find"
export PAX_CACHE=$L/cache PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px69-ubuntu TMPDIR=$L/tmp SOURCE_DATE_EPOCH=1700000000
ulimit -c 0
python3 -I - "$P" "$L" "$W" <<'PY'
from importlib.machinery import SourceFileLoader
from pathlib import Path
import sys
p,l,w=map(Path,sys.argv[1:])
m=SourceFileLoader('pax_mkdisk',str(p/'tools/mkdisk')).load_module()
stage=w/'stage'; stage.mkdir()
tree,attrs,n=m.root_tree(str(l/'play/w/play.cpio'),str(stage))
guid=m.uuid_of('pax-gpt-part:pax-playground:1700000000:2')
conf=m.root_conf(str(p/'boot/limine-initramfs-quiet.conf'),guid,m.uuid_of('pax-disk:pax-root:1700000000'),False)
Path(tree,'boot/limine/limine.conf').write_text(conf)
with open(attrs,'a') as f:f.write('/boot/limine/limine.conf 644 0 0 0\n')
print('installed archive entries',n,flush=True)
PY
printf 'reference root start\n'
"$P/tools/mkdisk" --from "$W/stage/tree" --attrs "$W/stage/attrs" --label pax-root --inodes 16384 467644416 "$W/oracle-root.img" > "$W/oracle-build.log" 2>&1
printf 'Wolf root and disk start\n'
podman run --rm -i --cpuset-cpus 8-11 -v "$L:$L:Z" -e L="$L" -e P="$P" -e W="$W" -e SOURCE_DATE_EPOCH localhost/px69-ubuntu bash -s <<'INNER'
set -euo pipefail
strace -f -c -o "$W/paxext2.census" "$L/bin/paxext2" --from "$W/stage/tree" --attrs "$W/stage/attrs" --label pax-root --inodes 16384 467644416 "$W/wolf-root.img"
strace -f -c -o "$W/paxgpt.census" "$L/bin/paxgpt" --seed pax-playground --size 512M "$W/disk.img" 1:esp:4096:135167:esp 2:linux:135168:1048535:root 3:bios:2048:4095:bios
strace -f -c -o "$W/paxfat.census" "$L/bin/paxfat" --offset 2M --seed pax-playground mkfs "$W/disk.img" 64M
for d in /EFI /EFI/BOOT /boot /boot/limine; do "$L/bin/paxfat" --offset 2M mkdir "$W/disk.img" "$d"; done
for pair in 'boot/EFI/BOOT/BOOTX64.EFI:EFI/BOOT/BOOTX64.EFI' 'boot/limine/limine.conf:boot/limine/limine.conf' 'boot/limine/limine-bios.sys:boot/limine/limine-bios.sys' 'boot/pax:boot/pax'; do
 "$L/bin/paxfat" --offset 2M copy "$W/disk.img" "$W/stage/tree/${pair%:*}" "/${pair#*:}"
done
# Read-only extraction/copy avoids reformatting any portion outside the root window.
python3 -I - "$W" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
with (p/'wolf-root.img').open('rb') as src,(p/'disk.img').open('r+b') as dst:
 dst.seek(135168*512)
 while b:=src.read(1048576):dst.write(b)
PY
cp --sparse=always "$W/disk.img" "$W/dynamic.img"
"$L/cache/limine-12.9.1/limine" bios-install "$W/dynamic.img" 3 > "$W/limine-dynamic.log" 2>&1
strace -f -o "$W/limine.strace" "$L/limine-static/limine" bios-install "$W/disk.img" 3 > "$W/limine-static.log" 2>&1
cmp "$W/dynamic.img" "$W/disk.img"
sha256sum "$L/cache/limine-12.9.1/limine" "$L/limine-static/limine" > "$W/limine.sha256"
sha256sum -c "$W/limine.sha256" > "$W/limine.verify1"
sha256sum -c "$W/limine.sha256" > "$W/limine.verify2"
printf 'PASS: dynamic and static Limine install identical bytes over entire disk\n' > "$W/limine.compare"
# Copy binaries and their libraries, never their source, for the real Linux guest.
cp /usr/bin/find "$W/find/find"
ldd /usr/bin/find | awk '{for(i=1;i<=NF;i++) if($i ~ /^\//) print $i}' | while IFS= read -r lib; do
 mkdir -p "$W/find$(dirname "$lib")"; cp -L "$lib" "$W/find$lib"
done
cp /usr/bin/busybox "$W/find/busybox"
INNER
printf 'tree oracle start\n'
"$P/tools/e2fs" "$W" e2fsck -fn "$W/wolf-root.img" > "$W/e2fsck.log" 2>&1
"$P/tools/e2tree" "$W/oracle-root.img" > "$W/oracle.tree"
"$P/tools/e2tree" "$W/wolf-root.img" > "$W/wolf.tree"
cmp "$W/oracle.tree" "$W/wolf.tree"
printf 'PASS installed tree: %s exact e2tree rows\n' "$(wc -l < "$W/wolf.tree")"
files=()
while IFS= read -r -d '' f; do files+=(--file "$f=${f#"$W/find"}"); done < <(find "$W/find/lib" "$W/find/lib64" -type f -print0)
for kind in oracle wolf; do
 printf 'Linux guest find: %s\n' "$kind"
 "$P/tools/linux-blk" --kernel /usr/lib/modules/7.3.0-4-cachyos/vmlinuz --modules /usr/lib/modules/7.3.0-4-cachyos --busybox "$W/find/busybox" --ro "${files[@]}" "$W/guest-$kind" "$W/$kind-root.img" "$W/find/find" -- '/bin/find /mnt -printf "%P\t%y\t%m\t%U\t%G\t%n\t%s\t%A@\t%T@\t%C@\t%l\n"' > "$W/guest-$kind.log" 2>&1
 done
python3 -I - "$W" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); rows=[]
for kind in ['oracle','wolf']:
 text=(p/f'guest-{kind}/serial.log').read_text()
 assert 'linux-blk: mount 0' in text,text
 assert 'linux-blk: run 1 status 0' in text,text
 assert 'linux-blk: unmount 0' in text,text
 data=sorted(l for l in text.splitlines() if len(l.split('\t'))==11)
 assert len(data)>200,len(data)
 (p/f'{kind}.find').write_text('\n'.join(data)+'\n');rows.append(data)
assert rows[0]==rows[1],(set(rows[0])-set(rows[1]),set(rows[1])-set(rows[0]))
(p/'find.compare').write_text(f'PASS: Linux 7.3.0-4 mounts both images; GNU find -printf identical, {len(rows[0])} rows\n')
print((p/'find.compare').read_text(),end='')
PY
# Playground sessions are checked by the separate driver, using copies.
printf 'installed Linux comparisons complete\n'
