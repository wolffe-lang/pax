#!/usr/bin/env bash
set -euo pipefail
L=/home/mfwolffe/lanes/px74
export PAX_CACHE=$L/cache PAX_BUILD=$L/build TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1
export PAX_ENGINE=$L/reference-engine PAX_TREE_IMAGE=docker.io/library/python:3.12-slim
cd "$L/pax-final"
name=shell-sibling
[ "${1:-}" != --resume ] || name=shell-sibling2
printf '%s\n' "$$" > "$L/runs/$name.pid"
exec > "$L/runs/$name.log" 2>&1
trap 'rc=$?; printf "%s\n" "$rc" > "$L/runs/$name.exit"' EXIT
printf 'shell sibling queued %s\n' "$(date -Is)"
exec 9>/home/mfwolffe/lanes/kasumi-cores-12-15.lock; flock 9
ctr() {
    podman run --rm --memory 12g --ulimit core=0:0 -v "$L:$L:Z" \
        -e PAX_CACHE -e PAX_BUILD -e TMPDIR -e PAX_REQUIRE_UEFI -e SOURCE_DATE_EPOCH=1700000000 \
        -w "$L/pax-final" localhost/px80-ubuntu taskset -c 12-15 "$L/in.sh" "$@" 9>&-
}
printf 'shell build %s\n' "$(date -Is)"
rc=1
if [ "${1:-}" != --resume ]; then
    rc=0
    ctr tests/mpx3-shell --only build --tier native --firmware both --pelt "$PAX_BUILD/mpx3-console/peltbin" \
        > "$L/runs/shell-build.log" 2>&1 || rc=$?
fi
if [ "$rc" != 0 ]; then
    # This old --only build still attempts root Linux references. Accept
    # ONLY that known staging failure, never a compiler or assertion error.
    python3 -I - "$L/runs/shell-build.log" <<'PY'
import re,sys
text=open(sys.argv[1]).read()
rows=[x for x in text.splitlines() if 'FAIL S0:' in x]
assert len(rows)==1, rows
reasons=rows[0].split('FAIL S0:',1)[1]
assert re.fullmatch(r'( tools/linux-tty [a-z0-9-]+;)+',reasons), reasons
assert text.count('linux-tty: cannot bind /dev into ')==7
assert 'build-kernel: ok: step 3' in text
print('STAGING ONLY: seven unavailable nested reference namespaces; rebuild every reference in siblings next')
PY
fi
d=$PAX_BUILD/mpx3-shell
for s in shell-serial shell-ps2 shell-howl shell-plumb shell-long shell-sigs procs; do
    p=shell; prog=pelt; key=$s
    case $s in shell-serial) key=shell;; procs) p=procs; prog=procs;; esac
    keys=user/console/$key.keys
    [ "$s" != procs ] || keys=$d/procs.keys
    printf 'sibling Linux %s %s\n' "$s" "$(date -Is)"
    tools/linux-tree --root "$d/$p/root" --keys "$keys" --prompt '$ ' --argv0 "/bin/$prog" \
        --size 512m --rdev "$d/linux/$s.tty" -- "/bin/$prog"
done
# These two user references already have an explicit host-side phase.
tests/mpx3-shell --only linux --images "$d" --tier native --firmware both
ctr tests/mpx3-shell --images "$d" --tier native --firmware both
ctr python3 -I tools/usb-typing mpx3-shell --tier native --firmware both
printf 'shell siblings complete %s\n' "$(date -Is)"
