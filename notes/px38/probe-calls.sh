#!/bin/bash
# px38, on kasumi: which system calls the probes themselves make, counted
# by strace in the container ("ct" root), so every number the note
# proposes is in a trace this lane took.
#   probe-calls.sh BINDIR OUTDIR
set -uo pipefail
bin=$1 out=$2
mkdir -p "$out"
cat > "$out/inner.sh" <<'IN'
#!/bin/bash
chmod 0777 /t /tn; cp /p/ids /t/ids
mkdir -m 0777 /t/perm /t/setid /tn/setid /t/sig /t/priv
c() { n=$1; shift; strace -f -c -S name -o "/out/$n.calls" setpriv --clear-groups "$@" > /dev/null 2>&1; echo "$n rc=$?"; }
c ids /t/ids /t/idsw
c cred /p/cred
c perm /p/perm /t/perm
c setid /p/setid /t/setid /tn/setid
c sig /p/sig /t/sig
c priv /p/priv /t/priv
IN
podman run --rm --network none --cap-add SYS_PTRACE --tmpfs /t:rw,exec,suid,dev,size=256m,mode=0777 --tmpfs /tn:rw,exec,nosuid,size=64m,mode=0777 \
    -v "$bin:/p:ro" -v "$out:/out" localhost/px13-ubuntu bash /out/inner.sh
rm -f "$out/inner.sh"
# one line a probe: the names, sorted
for f in "$out"/*.calls; do
    printf '%s: ' "$(basename "$f" .calls)"
    awk 'NR > 2 && $NF !~ /^(total|-+)$/ && NF >= 4 { print $NF }' "$f" | sort -u | tr '\n' ' '
    echo
done > "$out/probe-calls.txt"
