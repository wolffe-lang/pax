#!/usr/bin/env bash
# px77c: Linux 7.2.4 (hasu's own kernel and modules, run as binaries, never read) as the black-box
# oracle, under hasu block A, through tools/linux-nodes (px78's usb-storage modules).
#   linux-oracle.sh ident    the spelling machine's four SATA disks (qualify.py's s-old/s-new devices,
#                            the same -device ide-hd strings): what Linux's sysfs shows for each.
#   linux-oracle.sh cachyos  docs/INSTALL-METAL.md step 2's commands against a COPY of the install
#                            stick on usb-storage, the leg's target (PX78-TARGET-0001) on AHCI:
#                            the line a CachyOS user would write, written to the copy.
set -uo pipefail
L=/home/mfwolffe/lanes/px77c
WHAT=$1
K=/nix/store/j66ih4hz9b6k8fm6qhspnxancdfwsbda-linux-7.2.4/bzImage
MODS=/nix/store/5c4bsam2da6n36gd3bmq1iwzxw801f5j-linux-7.2.4-modules/lib/modules/7.2.4
O=$L/linux-$WHAT
[ ! -e "$O" ] || { echo "$O exists"; exit 2; }
mkdir -p "$O/disks" "$O/fat"
printf '%s\n' "$$" > "$O.pid"
for m in fat vfat nls_cp437 nls_iso8859-1 nls_utf8; do
 p=$(grep -E "/$m\.ko(\.xz)?:" "$MODS/modules.dep" | head -1 | cut -d: -f1)
 xz -d -c "$MODS/$p" > "$O/fat/$m.ko"
done
printf '#!/bin/busybox sh\n# the guest runs as root: sudo runs its arguments\nexec "$@"\n' > "$O/sudo"
chmod +x "$O/sudo"
args=()
if [ "$WHAT" = ident ]; then
 k=0
 while IFS='|' read -r model serial; do
  truncate -s 64M "$O/disks/sata$k.img"
  args+=(--qemu -drive --qemu "file=$O/disks/sata$k.img,if=none,id=sa$k,format=raw"
         --qemu -device --qemu "ide-hd,bus=ide.$k,drive=sa$k,model=$model,serial=$serial")
  k=$((k + 1))
 done <<'LIST'
Samsung SSD 870 EVO 500GB|S6PXNM0T612345A
CT500MX500SSD1|ABCDEFGHIJ0123456789
WDC WDS500G2B0A-00SM50|   21021X801234
SanDisk SDSSDH3 512G|2104AB401234
LIST
 cmd=(/bin/busybox sh /ident.sh)
 files=(--file "$L/pax/notes/px78/ident.sh=/ident.sh")
else
 copy=$2
 truncate -s 64M "$O/disks/target.img"
 args+=(--qemu -drive --qemu "file=$O/disks/target.img,if=none,id=t,format=raw"
        --qemu -device --qemu "ide-hd,bus=ide.0,drive=t,model=Samsung SSD 870 EVO 500GB,serial=PX78-TARGET-0001"
        --qemu -device --qemu "qemu-xhci,id=x"
        --qemu -drive --qemu "file=$copy,if=none,id=st,format=raw"
        --qemu -device --qemu "usb-storage,bus=x.0,drive=st,removable=on")
 cmd=(/bin/busybox sh /step2.sh)
 files=(--file "$L/cachyos-step2.sh=/step2.sh" --file "$O/sudo=/bin/sudo")
 sha256sum "$copy" > "$O/copy-before.sha256"
fi
for m in fat vfat nls_cp437 nls_iso8859-1 nls_utf8; do files+=(--file "$O/fat/$m.ko=/lib/fat/$m.ko"); done
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
printf '%s px77c linux %s acquiring block A\n' "$(date -u +%FT%TZ)" "$WHAT"
until flock -n 9; do
 printf '%s block A held by another lane; waiting\n' "$(date -u +%FT%TZ)"
 python3 -I -c 'import time; time.sleep(30)'
done
printf '%s block A acquired\n' "$(date -u +%FT%TZ)"
rc=0
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name "px77c-linux-$WHAT" --memory 12g --pids-limit 16384 --ulimit core=0:0 \
 -v "$L:$L" -v /nix/store:/nix/store:ro -w "$L/pax" -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp \
 localhost/px75-ubuntu:2 taskset -c 0-5 bash -c '
  set -e
  bb=$(tools/fetch-busybox "$1/bb" | tail -1); echo "$bb"
  shift
  exec tools/linux-nodes --kernel '"$K"' --modules '"$MODS"' --busybox "$0/bb/busybox" "$@"' \
 "$O" "$O" "${args[@]}" "${files[@]}" "$O/guest" -- "${cmd[*]}" || rc=$?
flock -u 9
exec 9>&-
printf '%s block A RELEASED linux %s rc=%s\n' "$(date -u +%FT%TZ)" "$WHAT" "$rc"
[ "$WHAT" = ident ] || sha256sum "$copy" > "$O/copy-after.sha256"
echo "$rc" > "$O.exit"
printf '%s END linux %s exit=%s\n' "$(date -u +%FT%TZ)" "$WHAT" "$rc"
exit "$rc"
