#!/usr/bin/env bash
# px89: CI's red at D5 (pax#298, run 41967637438) mirrored in the lane:
# tests/mpx4-dhcp's renew way run as a user that is not root (runner,
# uid 1001) with `sudo -n`, as GitHub's runner runs it, in
# localhost/px89-dhcp-ci:1 (Containerfile.ci).
#
#   ci-mirror.sh OUT IMGTREE TREE...
#
# As root: the renew images (kmain_sockets, native) from IMGTREE, once
# (the kernel is the same in every TREE: their commits touch only tests/
# and tools/). Then for each TREE, as runner: `tests/mpx4-dhcp --images
# ... --ways renew --tier native --firmware bios`, the wire directory's
# modes and owners, and every file there runner cannot read (what CI's
# artifact upload met as EACCES).
set -uo pipefail
out=$1 img=$2; shift 2
rm -rf "$out"; mkdir -p "$out"
asrun() { setpriv --reuid=1001 --regid=1001 --init-groups env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/home/runner USER=runner "$@"; }
cat /etc/px89-ci-packages.txt
echo "== images as root from $img at $(git -C "$img" rev-parse --short=8 HEAD)"
( cd "$img" && export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && PAX_BUILD=$out/imgbuild tests/mpx4-dhcp --no-boot --ways renew --tier native --firmware bios ) > "$out/images.log" 2>&1
rc=$?; tail -n 3 "$out/images.log"; [ "$rc" = 0 ] || { echo "== images: exit $rc"; exit 1; }
images=$out/imgbuild/mpx4-dhcp
chown -R 1001:1001 "$out"
echo "== as runner: uid $(asrun id -u), sudo -n: $(asrun sudo -n true 2>&1 && echo yes)"
for t in "$@"; do
    n=$(git -C "$t" rev-parse --short=8 HEAD)
    echo "== tree $n: $(git -C "$t" log -1 --format=%s | cut -c1-110)"
    mkdir -p "$out/$n/tmp"; chown -R 1001:1001 "$out/$n"
    asrun TMPDIR="$out/$n/tmp" PAX_BUILD="$out/$n" PAX_REQUIRE_DHCP_WIRE=1 bash -c 'cd "$1" && tests/mpx4-dhcp --images "$2" --ways renew --tier native --firmware bios; echo "== tree $3: tests/mpx4-dhcp exit=$?"' x "$t" "$images" "$n" 2>&1 | grep -E '^mpx4-dhcp: (PASS|FAIL|SKIP)|exit=|mpx4-dhcp: .*(PASS|FAIL)$'
    for f in "$out/$n"/*.wire/*; do echo "   $(stat -c '%a %U:%G' "$f") ${f#$out/}"; done
    grep -h 'stopped' "$out/$n"/*.wire/account.txt | sed 's/^/   /'
    u=$(asrun find "$out/$n" ! -readable 2>/dev/null | sed "s#^$out/##" | paste -sd' ' -)
    echo "   not readable by runner: ${u:-none}"
done
