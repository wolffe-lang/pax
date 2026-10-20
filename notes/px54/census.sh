#!/bin/bash
# px54 on kasumi: what lope asks of Linux, black-box. lope's own runs, as
# PAX's hook makes them (`lope init pelt`, `add -- DIR`, `query --cwd --
# WORD`, `query -- WORD`, `query --all --`, `list`), under `strace -f -n`
# in localhost/px13-ubuntu, with PAX's environment (HOME a scratch
# directory, TERM=linux, PAX=1, PATH=/bin, no XDG variable), the store
# missing, then present, then its directory unwritable (a file where
# ~/.local is). Each run's calls by name and number with their counts and
# their failures, then the union.   census.sh LOPE OUTDIR
L=$HOME/lanes/px54
B=$(cd "$(dirname "$1")" && pwd) O=$2
mkdir -p "$O"
podman run --rm --cap-add SYS_PTRACE --security-opt seccomp=unconfined --network none \
    -v "$B:/w/b:ro,Z" -v "$O:/w/o:Z" localhost/px13-ubuntu bash -c '
set -u
strace -V | head -n 1
cp /w/b/lope /bin/lope
mkdir -p /w/h /w/h2 /w/t/alpha /w/t/beta; touch /w/h2/.local
E="env -i HOME=/w/h TERM=linux PAX=1 PATH=/bin"  # strace started under it, lope the only program traced
n=0
run() { # name dir cmd...
    local name=$1 dir=$2; shift 2
    n=$((n + 1))
    (cd "$dir" && $E /usr/bin/strace -f -n -qq -o /w/o/$n-$name.strace "$@" > /w/o/$n-$name.out 2> /w/o/$n-$name.err; echo $? > /w/o/$n-$name.rc)
    echo "$n $name: rc $(cat /w/o/$n-$name.rc), $(wc -l < /w/o/$n-$name.strace) calls"
}
run version /w/h /bin/lope --version
run init /w/h /bin/lope init pelt
run list-missing /w/h /bin/lope list
run add-first /etc /bin/lope add -- /etc
run add-second /bin /bin/lope add -- /bin
run add-tree /w/t /bin/lope add -- /w/t/alpha
run list /w/h /bin/lope list
run query-cwd /bin /bin/lope query --cwd -- etc
run query-cwd-hit /w/t /bin/lope query --cwd -- beta
run query /bin /bin/lope query -- etc
run query-all /bin /bin/lope query --all --
run query-none /bin /bin/lope query -- zzqqxx
E="env -i HOME=/w/h2 TERM=linux PAX=1 PATH=/bin"
run add-unwritable /etc /bin/lope add -- /etc
for f in /w/o/*.strace; do
    sed -E "s/^[0-9]+ +//" "$f" | sed -n -E "s/^\[ *([0-9]+)\] ([a-z0-9_]+)\(.*/\2 \1/p" | sort | uniq -c | sort -k2 > "${f%.strace}.calls"
    grep -E "= -1 E[A-Z]+" "$f" | sed -E "s/^[0-9]+ +//; s/^\[ *([0-9]+)\] ([a-z0-9_]+)\((.*)\) += -1 (E[A-Z]+).*/\2 \4 \3/" | cut -c1-160 > "${f%.strace}.errors"
done
cat /w/o/*.calls | awk "{ c[\$2\" \"\$3] += \$1 } END { for (k in c) print k, c[k] }" | sort > /w/o/union.calls
echo "union: $(wc -l < /w/o/union.calls) calls by name"
cat /w/o/union.calls
'
