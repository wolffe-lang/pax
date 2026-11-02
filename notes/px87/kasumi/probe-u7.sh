#!/usr/bin/env bash
# px87: tests/usb-stick's U7 alone (the live-only root login on the USB topology, both firmwares), its
# commands as the suite runs them, at a worktree's commit; then U7's assertions, the px87 one included.
# Run by hostchain.sh: the build and the boots in the container, the stick image (tools/mkdisk, whose
# disktools want a container engine) on the host with podman.
#   probe-u7.sh WORKTREE BUILD_DIR
set -uo pipefail
W=$1 B=$2
work=$B/u7
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; [ "$rc" = 0 ] || exit "$rc"; }
rm -rf "$work"; mkdir -p "$work/k"
cat > "$work/build.sh" <<EOF
set -euo pipefail
cd $W
export PAX_CACHE=$L/cache PAX_BUILD=$B SOURCE_DATE_EPOCH=1700000000
export PAX_WOLF=\$(tools/fetch-wolf)
tools/fetch-limine > /dev/null
printf 'commit %s\n' "\$(git rev-parse HEAD)"
tools/mkpelt $work/pelt > $work/pelt.log 2>&1
tools/build-kernel --src kernel/kmain_console.lu $work/k > $work/elf.path 2> $work/k.log
printf '/bin/pelt /etc/pax-live-login\n' > $work/live.run
tools/mkinitramfs $work/live.cpio /root/:700 /tmp/:1777 "/bin/pelt=$work/pelt/pelt:755" \
    "/etc/pax-live-login=$W/user/usb-login.sh:644" "/etc/pax-run=$work/live.run:644" > $work/live.initramfs.log
EOF
cat > "$work/boot.sh" <<'EOF'
set -uo pipefail
L=/home/mfwolffe/lanes/px87
cd "$1"; work=$2
. tools/lib.sh
export PAX_CACHE=$L/cache SOURCE_DATE_EPOCH=1700000000 PAX_REQUIRE_UEFI=1
elf=$(cat "$work/elf.path")
printf 'nobody\nroot\n^~echo USB-LIVE-ROOT\n^~exit\n' > "$work/login.keys"
rc=0
for fw in bios uefi; do
    tools/qemu-halt --accel tcg --usb-stick --firmware "$fw" --timeout 120 --elf "$elf" \
        --serial "$work/login-$fw.serial" --marker halt --type "$work/login.keys" --prompt 'login: ' \
        "$work/live.img" > "$work/login-$fw.verdict" 2>&1 || { echo "qemu-halt $fw: $(tail -n 2 "$work/login-$fw.verdict")"; rc=1; }
    tr -d '\r' < "$work/login-$fw.serial" > "$work/login-$fw.norm"
    grep -q '^Only root is available on the live medium\.' "$work/login-$fw.norm" || { echo "FAIL U7 $fw: no refusal line"; rc=1; }
    grep -qx USB-LIVE-ROOT "$work/login-$fw.norm" || { echo "FAIL U7 $fw: no USB-LIVE-ROOT"; rc=1; }
    if grep -Eq '^user: (exec pid |[^ ]+ pid [0-9]+ (exit_group|exit) [0-9]+ after )' "$work/login-$fw.norm"; then
        echo "FAIL U7 $fw: the live session printed a per-program line: $(grep -m1 -E '^user: (exec pid |[^ ]+ pid [0-9]+ (exit_group|exit) [0-9]+ after )' "$work/login-$fw.norm")"
        echo "  ($(grep -cE '^user: ' "$work/login-$fw.norm") user: lines in all)"
        rc=1
    else
        echo "PASS U7 $fw: refusal, USB-LIVE-ROOT, no per-program line ($(grep -cE '^user: ' "$work/login-$fw.norm") user: lines in all)"
    fi
done
exit $rc
EOF
step u7-build ctr bash "$work/build.sh"
step u7-disk bash -c "cd $W && export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman SOURCE_DATE_EPOCH=1700000000 TMPDIR=$L/tmp && cat boot/limine-usb.conf && tools/mkdisk --usb --kernel \$(cat $work/elf.path) --initramfs $work/live.cpio --conf $W/boot/limine-usb.conf $work/live.img > $work/live.build.log"
step u7-boot ctr bash "$work/boot.sh" "$W" "$work"
