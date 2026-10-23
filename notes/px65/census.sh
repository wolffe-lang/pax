#!/bin/bash
# px65, kasumi: the calls boreutils' fourteen new utilities make, by name,
# on Linux (strace in the lane's own container, CPUs 12-15), over a short
# session of each one's common options — the typed sessions' commands, as
# root, in a scratch directory; tty on a pseudo-terminal (script(1)) and
# with a file on standard input. Not a gate: the census beside B3's (what
# PAX logs as -ENOSYS).   census.sh BINDIR OUT
#   BINDIR: a tests/mpx5-bore build's bore/ (user/boreutils.pin's binaries)
#   OUT:    OUT/<util>.calls (name count), OUT/<util>.fails, OUT/union.calls
L=$HOME/lanes/px65; P=$L/pax
B=$1 O=$2
mkdir -p "$O"
podman run --rm --name px65-census --cpuset-cpus 12-15 --ulimit core=0:0 --cap-add SYS_PTRACE --security-opt seccomp=unconfined \
    -v "$L:$L:Z" -e B="$B" -e O="$O" -e P="$P" localhost/px65-ubuntu bash -c '
set -u
T=$(mktemp -d); mkdir -p $T/tr $T/w $T/fx
python3 $P/tests/mpx5-bore.d/fixture.py $T/fx >/dev/null
cd $T/w; umask 022
echo hello > a; echo data > s1; mkdir d; ln -s a la; ln -s nowhere dangle; ln -s /etc le
n=0
run() { # util args...
    u=$1; shift; n=$((n+1))
    strace -f -qq -o $T/tr/$u.$n.txt $B/$u "$@" >/dev/null 2>&1 </dev/null; echo "$u rc=$?: $*"
}
run mkfifo f1; run mkfifo -m 600 f2; run mkfifo f1; run mkfifo nodir/f3
run link a b; run link a b; run link nosuch c
run unlink b; run unlink b; run unlink d
run truncate -s 10 a; run truncate -s +5 a; run truncate -s %8 a; run truncate -c -s 4 nonew; run truncate -r a r1; run truncate -s 4 d; run truncate -s 4 f1
run sync s1; run sync -d s1; run sync --data s1 d; run sync nosuch; run sync; run sync -f s1
run mktemp; run mktemp -d; run mktemp -p $T/w x.XXXXXX; run mktemp -u; run mktemp abc; run mktemp -p nodir
run realpath .; run realpath ./d/../a; run realpath la; run realpath -s la; run realpath dangle; run realpath -e dangle
run realpath -m nowhere/x/../y; run realpath --relative-to=/tmp a; run realpath -L le/..; run realpath -P le/..
n=$((n+1)); script -qec "strace -f -qq -o $T/tr/tty.$n.txt $B/tty" /dev/null >/dev/null 2>&1; echo "tty on a pty rc=$?"
n=$((n+1)); script -qec "strace -f -qq -o $T/tr/tty.$n.txt $B/tty -s" /dev/null >/dev/null 2>&1; echo "tty -s on a pty rc=$?"
n=$((n+1)); strace -f -qq -o $T/tr/tty.$n.txt $B/tty < a >/dev/null 2>&1; echo "tty < a rc=$?"
cd $T/fx
run base64 hello.txt; run base64 bytes.dat; run base64 -w 16 b64.txt; run base64 -d b64.txt; run base64 -d bad.txt; run base64 -d -i bad.txt; run base64 nosuch
run base32 hello.txt; run base32 -d b32.txt; run base32 -d bad.txt
run comm c1.txt c2.txt; run comm -12 c1.txt c2.txt; run comm --total c1.txt c2.txt; run comm cu.txt c2.txt
run join j1.txt j2.txt; run join -a 1 -a 2 -e NONE -o 0,1.2,2.2 j1.txt j2.txt; run join -t : -1 2 -2 1 p1.txt p2.txt; run join --header h1.txt h2.txt; run join j1.txt nosuch
run tsort ts.txt; run tsort tcyc.txt; run tsort todd.txt
run shuf -i 1-10; run shuf -e a b c d; run shuf lines.txt; run shuf -n 3 -i 1-100; run shuf -r -n 4 -e x; run shuf -i 5-1; run shuf --random-source=lines.txt -i 1-3
n=$((n+1)); echo aGVsbG8K | strace -f -qq -o $T/tr/base64.$n.txt $B/base64 -d >/dev/null 2>&1; echo "base64 -d of a pipe rc=$?"
norm() { sed -E "s/^[0-9]+ +//; s/^<\.\.\. ([a-z0-9_]+) resumed>.*/\1(/" "$@" | grep -E "^[a-z_0-9]+\(" | sed -E "s/\(.*//"; }
for u in mkfifo link unlink truncate sync mktemp realpath tty base64 base32 comm join tsort shuf; do
    norm $T/tr/$u.*.txt | sort | uniq -c | awk "{print \$2, \$1}" > $O/$u.calls
    grep -h "= -1 E" $T/tr/$u.*.txt | sed -E "s/^[0-9]+ +//" | sed -E "s/^([a-z0-9_]+)\(.*= -1 (E[A-Z0-9]+).*/\1 \2/" | sort | uniq -c | awk "{print \$2, \$3, \$1}" > $O/$u.fails
    echo "$u: $(wc -l < $O/$u.calls) calls: $(cut -d" " -f1 $O/$u.calls | tr "\n" " ")"
done
cat $O/*.calls | awk "{c[\$1]+=\$2} END {for (k in c) print k, c[k]}" | sort > $O/union.calls
echo "union: $(wc -l < $O/union.calls) distinct calls"
strace -V | head -n 1
'
