#!/bin/bash
# px38, on kasumi: run the probes as the root of a rootless podman
# container: the "ct" root, root of a user namespace (uid 0 inside is the
# invoking user outside; ids 1 to 65536 map to its subordinate range).
# Nothing of the host is mounted but the probes (read-only) and the
# output directory; /t and /tn are tmpfs of the container; no network.
#
#   ct-run.sh BINDIR OUTDIR [IMAGE]
set -uo pipefail
bin=$1 out=$2 image=${3:-localhost/px13-ubuntu}
mkdir -p "$out"
cat > "$out/ct-inner.sh" <<'IN'
#!/bin/bash
# inside the container
exec > /out/ct.txt 2>&1
echo "=== px38 ct: $(uname -srm); $(id); CapEff $(sed -n 's/^CapEff:\t//p' /proc/self/status) CapBnd $(sed -n 's/^CapBnd:\t//p' /proc/self/status)"
echo "=== px38 ct: uid_map $(tr -s ' ' < /proc/self/uid_map | tr '\n' ';') gid_map $(tr -s ' ' < /proc/self/gid_map | tr '\n' ';')"
echo "=== px38 ct: fs.suid_dumpable $(cat /proc/sys/fs/suid_dumpable)"
umask 022
chmod 0777 /t /tn
cp /p/ids /t/ids
run() { echo "=== BEGIN $1"; "${@:2}"; echo "=== END $1 status $?"; }
# every probe starts with no supplementary group, as pid 1 of the vm has none
run ids setpriv --clear-groups /t/ids /t/idsw
run cred setpriv --clear-groups /p/cred
mkdir -m 0777 /t/perm /t/setid /tn/setid /t/sig
run perm setpriv --clear-groups /p/perm /t/perm
run setid setpriv --clear-groups /p/setid /t/setid /tn/setid
run sig setpriv --clear-groups /p/sig /t/sig
echo "=== px38 ct: done"
IN
podman run --rm --network none --tmpfs /t:rw,exec,suid,dev,size=256m,mode=0777 --tmpfs /tn:rw,exec,nosuid,size=64m,mode=0777 \
    -v "$bin:/p:ro" -v "$out:/out" "$image" bash /out/ct-inner.sh
rc=$?
{
    echo "podman: $(podman --version); image $image $(podman image inspect --format '{{.Id}}' "$image" | cut -c1-12)"
    echo "exit: $rc"
} > "$out/ct.meta"
grep -q '^=== px38 ct: done' "$out/ct.txt" || { echo "ct-run: the container did not reach its last marker" >&2; exit 1; }
