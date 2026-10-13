#!/bin/bash
# px39, on kasumi: the credentials programs as uid 1000 of a rootless
# podman container: a SECOND witness for a user's rows, beside the real
# root's recording (linux-vm.sh). The container's root is root of a user
# namespace (px38: 99 of its lines differ from real root's); it is used
# here only to run `as 1000 1000`, never as a reference for root. Nothing
# of the host is mounted but the programs (read-only) and the output
# directory; /tn is a nosuid tmpfs of the container; no network.
#
#   linux-ct.sh BINDIR OUTDIR [IMAGE]
#
# OUTDIR gets cred-user.txt, ident-user.txt and soak-user.txt (the same
# three sessions linux-vm.sh records after `as 1000 1000`) and ct.meta.
set -uo pipefail
bin=$1 out=$2 image=${3:-localhost/px13-ubuntu}
mkdir -p "$out"
cat > "$out/ct-inner.sh" <<'IN'
#!/bin/bash
# inside the container, as its root
echo "=== px39 ct: $(uname -srm); $(id); uid_map $(tr -s ' ' < /proc/self/uid_map | tr '\n' ';') fs.suid_dumpable $(cat /proc/sys/fs/suid_dumpable)" > /out/ct.head
umask 022
chmod 0777 /tn
cp /p/ident /tn/ident-setid && chmod 6755 /tn/ident-setid
echo "=== px39 ct: /tn/ident-setid $(stat -c '%a %u:%g' /tn/ident-setid)" >> /out/ct.head
/p/as 1000 1000 /p/cred > /out/cred-user.txt 2>&1; echo $? > /out/cred-user.rc
/p/as 1000 1000 /p/ident /tn/ident-setid > /out/ident-user.txt 2>&1; echo $? > /out/ident-user.rc
/p/as 1000 1000 /p/ident soak 100000 > /out/soak-user.txt 2>&1; echo $? > /out/soak-user.rc
echo "=== px39 ct: done" >> /out/ct.head
IN
podman run --rm --network none --tmpfs /tn:rw,exec,nosuid,size=64m,mode=0777 \
    -v "$bin:/p:ro" -v "$out:/out" "$image" bash /out/ct-inner.sh
rc=$?
{
    echo "podman: $(podman --version); image $image $(podman image inspect --format '{{.Id}}' "$image" | cut -c1-12)"
    cat "$out/ct.head"
    for p in cred ident as; do echo "$p: $(sha256sum "$bin/$p" | cut -d' ' -f1)"; done
    for s in cred-user ident-user soak-user; do echo "$s: $(wc -l < "$out/$s.txt") lines, status $(cat "$out/$s.rc")"; done
    echo "exit: $rc"
} > "$out/ct.meta"
rm -f "$out/ct.head" "$out/ct-inner.sh"
grep -q '^=== px39 ct: done' "$out/ct.meta" || { echo "linux-ct: the container did not reach its last marker" >&2; exit 1; }
