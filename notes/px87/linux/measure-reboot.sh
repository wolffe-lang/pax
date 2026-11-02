#!/usr/bin/env bash
# px87 (pax#265): what Linux's reboot tools say to a user, black-box, as uid 1000 in a rootless container
# (no CAP_SYS_BOOT in any namespace, so reboot(2) answers EPERM and nothing restarts). Never run as root.
# busybox is user/busybox.pin's (Ubuntu 24.04's busybox-static, by digest); systemd's reboot is the image's,
# when it has one. `busybox reboot` without -f signals pid 1 instead of calling reboot(2): not run.
set -u
L=/home/mfwolffe/lanes/px87
bb=$L/cache/busybox-dbac288c29ba568459550a2da9e7ae0ded6b1fc728ee9fad3044c44e62d6ac14
echo "id: $(id)"
sha256sum "$bb"
grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release
echo "kernel: $(uname -r)"
[ "$(id -u)" != 0 ] || { echo "REFUSED: running as root"; exit 2; }
run() {
    printf -- '--- %s\n' "$*"
    out=$("$@" 2>&1); rc=$?
    printf '%s\n' "$out" | sed 's/^/| /'
    printf 'exit %s\n' "$rc"
}
run "$bb" reboot -f
run "$bb" poweroff -f
run "$bb" halt -f
for t in /usr/sbin/reboot /sbin/reboot /usr/bin/systemctl; do
    [ -e "$t" ] && ls -l "$t"
done
if [ -x /usr/sbin/reboot ]; then
    run /usr/sbin/reboot -ff
    run /usr/sbin/poweroff -ff
    run /usr/sbin/reboot
fi
