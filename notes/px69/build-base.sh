#!/usr/bin/env bash
# px69, kasumi only: the #144 witness first, then the full installed-tree
# input for paxext2's differential and the later from-PAX disk boot.
# Launch with setsid -f; the caller never waits on this long job.
set -euo pipefail
L=$HOME/lanes/px69
printf '%s\n' "$$" > "$L/base.pid"
trap 'rc=$?; printf "%s\n" "$rc" > "$L/base.exit"; printf "base job exit=%s %s\n" "$rc" "$(date -Is)"' EXIT
exec 9> "$HOME/lanes/kasumi-cores-8-11.lock"
printf 'base job starting %s; acquiring CPUs 8-11\n' "$(date -Is)"
flock 9
ulimit -c 0
export L
P=$L/pax
export P
mkdir -p "$L/play/w" "$L/cache" "$L/tmp" "$L/evidence"
# All commands and subprocesses inherit this affinity, including image builds.
taskset -pc 8-11 $$
[ "$(git -C "$P" rev-parse --short=8 HEAD)" = 105d0d1f ]
[ "$(du -sk "$L" | cut -f1)" -lt 15728640 ]
[ "$(df -Pk "$L" | awk 'NR==2 { print $4 }')" -gt 16777216 ]
[ -d "$L/lope" ] || git clone --quiet "$L/lope.bundle" "$L/lope"
git -C "$L/lope" cat-file -e e6f623c778dd486436bcb0a7d481333e0463b906
export SOURCE_DATE_EPOCH=1700000000
# Build unmodified source on the Ubuntu baseline, never CachyOS glibc.
podman run --rm -i --name px69-base-preflight --cpuset-cpus 8-11 --ulimit core=0:0 \
    -v "$L:$L:Z" -e L -e P -e SOURCE_DATE_EPOCH \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" \
    localhost/px69-ubuntu bash -s <<'INNER'
set -euo pipefail
cd "$P"
W=$L/play/w
PAX_WOLF=$(tools/fetch-wolf)
export PAX_WOLF
echo "compiler: $PAX_WOLF"
"$PAX_WOLF" --version
# fetch-limine builds the pinned release's tool without reading its source.
tools/fetch-limine
cc -static -no-pie -O1 -Wall -Wextra -Werror -Wl,--build-id=none -Wl,-z,noexecstack \
    user/elf/disktools-preflight.c -o "$W/disktools-preflight"
readelf -hW "$W/disktools-preflight" | grep -E 'Type: +EXEC'
if readelf -lW "$W/disktools-preflight" | grep -q INTERP; then exit 1; fi
mkdir -p "$W/native"
tools/build-kernel --src kernel/kmain_console.lu "$W/native" > "$W/elf.path" 2> "$W/kernel.log"
printf '/bin/disktools-preflight\n' > "$W/preflight.run"
printf '' > "$W/fstab"
tools/mkinitramfs "$W/preflight.cpio" /bin/disktools-preflight="$W/disktools-preflight":755 \
    /etc/pax-run="$W/preflight.run":644 /etc/fstab="$W/fstab":644 > "$W/preflight.initramfs.txt"
tools/mkimage --conf boot/limine-initramfs.conf --add "$W/preflight.cpio" initramfs.cpio \
    "$(cat "$W/elf.path")" "$W/preflight.iso"
INNER
printf 'preflight build complete %s\n' "$(date -Is)"
W=$L/play/w
truncate -s 128M "$W/blank-a.img"
truncate -s 128M "$W/blank-b.img"
PAX_CACHE=$L/cache PAX_BUILD=$W TMPDIR=$L/tmp "$P/tools/qemu-halt" --firmware bios \
    --elf "$(cat "$W/elf.path")" --marker halt --serial "$L/evidence/preflight.serial" \
    --qemu -drive --qemu "file=$W/blank-a.img,if=none,id=d0,format=raw" \
    --qemu -device --qemu virtio-blk-pci,drive=d0 \
    --qemu -drive --qemu "file=$W/blank-b.img,if=none,id=d1,format=raw" \
    --qemu -device --qemu virtio-blk-pci,drive=d1 "$W/preflight.iso" \
    > "$L/evidence/preflight.boot" 2>&1
grep -a 'disktools-preflight:' "$L/evidence/preflight.serial" | tr -d '\r' > "$L/evidence/preflight.rows"
grep -q 'disktools-preflight: end' "$L/evidence/preflight.rows"
cat "$L/evidence/preflight.rows"
printf 'baseline programs starting %s\n' "$(date -Is)"
podman run --rm -i --name px69-base-programs --cpuset-cpus 8-11 --ulimit core=0:0 \
    -v "$L:$L:Z" -e L -e P -e SOURCE_DATE_EPOCH \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" -e PAX_LOPE_REPO="$L/lope" \
    -e CARGO_INCREMENTAL=0 localhost/px69-ubuntu bash -s <<'INNER'
set -euo pipefail
cd "$P"
W=$L/play/w
step() {
    local name=$1; shift
    printf '%s start %s\n' "$name" "$(date -Is)"
    "$@" > "$W/$name.log" 2>&1
    printf '%s PASS %s\n' "$name" "$(date -Is)"
    [ "$(du -sk "$L" | cut -f1)" -lt 15728640 ]
}
step pelt tools/mkpelt "$W/pelt"
step lope tools/mklope "$W/lope"
step aspen tools/mkaspen "$W/aspen"
step scent tools/mkscent "$W/scent"
step std tools/fetch-std "$W/std"
step yew tools/mkyew "$W/yew"
step bore tools/mkboreutils "$W/bore" base32 base64 basename cat chgrp chmod chown comm cp cut dirname echo env expand false fold groups head id join kill link ln logname ls mkdir mkfifo mktemp mv nl nproc paste printenv printf pwd readlink realpath rm rmdir seq shuf sleep sort stat sync tac tail tee timeout touch tr true truncate tsort tty unexpand uniq unlink wc whoami yes
step as tools/mkas "$W/bin"
step su tools/mksu "$W/su"
step play tools/mkplay "$W/play"
step zone tools/mkzone "$W/localtime"
step probe tools/mkdiskprobe "$W/probe"
step lupin tools/mklupin "$W/lupin"
find "$W" -type f -executable -print0 | sort -z | xargs -0 sha256sum > "$L/evidence/base-binaries.sha256"
sha256sum -c "$L/evidence/base-binaries.sha256" > "$L/evidence/base-binaries.verify1"
sha256sum -c "$L/evidence/base-binaries.sha256" > "$L/evidence/base-binaries.verify2"
INNER
du -sh "$L" "$L/play/w" "$L/cache" "$L/tmp"
printf 'baseline inputs complete %s\n' "$(date -Is)"
