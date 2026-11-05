#!/usr/bin/env bash
# px89: CI's mpx4-dhcp and mpx4-igb jobs mirrored whole: each SUITE run
# from TREE as runner (uid 1001, password-less sudo: Containerfile.ci),
# with CI's environment for them (PAX_REQUIRE_UEFI=1,
# PAX_REQUIRE_DHCP_WIRE=1, PAX_WOLF from tools/fetch-wolf, tools/
# fetch-limine first) and the leg CI ran red in run 41967637438
# (--tier native --firmware bios), the build and the boots the suite's
# own. runner's cache: copies of the lane's Limine, disktools and busybox,
# the lane's wolf by a link (read only).
#
#   ci-mirror-suites.sh OUT TREE SUITE...
#
# Prints each suite's verdict lines and exit, and every file of its build
# directory runner cannot read (what CI's artifact upload met as EACCES).
set -uo pipefail
L=/home/mfwolffe/lanes/px89
out=$1 tree=$2; shift 2
rm -rf "$out"; mkdir -p "$out/cache" "$out/tmp"
cp -a "$L"/cache/limine-* "$L"/cache/disktools-* "$L"/cache/busybox-* "$out/cache/"
for w in "$L"/cache/wolf-0.2.35*; do ln -s "$w" "$out/cache/${w##*/}"; done
chown -R -h 1001:1001 "$out"
asrun() { setpriv --reuid=1001 --regid=1001 --init-groups env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/home/runner USER=runner "$@"; }
cat /etc/px89-ci-packages.txt
echo "== tree $(git -C "$tree" rev-parse --short=8 HEAD): $(git -C "$tree" log -1 --format=%s | cut -c1-110)"
echo "== as runner: uid $(asrun id -u), sudo -n: $(asrun sudo -n true 2>&1 && echo yes)"
rc=0
for s in "$@"; do
    echo "== $s as runner, --tier native --firmware bios"
    asrun TMPDIR="$out/tmp" PAX_CACHE="$out/cache" PAX_BUILD="$out/$s" PAX_REQUIRE_UEFI=1 PAX_REQUIRE_DHCP_WIRE=1 \
        bash -c 'cd "$1" && export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && tools/fetch-limine >/dev/null && tests/"$2" --tier native --firmware bios; echo "== $2: exit=$?"' x "$tree" "$s" \
        > "$out/$s.log" 2>&1
    grep -E '^[a-z0-9-]+: (PASS|FAIL|SKIP)|^== .*exit=' "$out/$s.log" | cut -c1-230
    grep -q "^== $s: exit=0$" "$out/$s.log" || rc=1
    u=$(asrun find "$out/$s" ! -readable 2>/dev/null | sed "s#^$out/##" | paste -sd' ' -)
    echo "   not readable by runner: ${u:-none}"
done
exit $rc
