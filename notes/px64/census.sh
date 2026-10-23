#!/bin/bash
# px64, kasumi: the calls scent makes, by name, on Linux (strace 6.8 in the
# lane's own container, CPUs 12-15), over the session's kinds of run: a
# file, a pattern file, standard input from a pipe, -z, a binary file, a
# missing file, the -P refusal, a conflict, -r's refusal, --help,
# --version, a 5,000-row file, the abort on a non-UTF-8 argument (by a
# `#!` line). Not a gate: the census beside A3's (what PAX logs as
# -ENOSYS). Writes notes/px64/census.out.
set -u
L=$HOME/lanes/px64
P=${PX64_SRC:-$L/pax}
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 --cap-add SYS_PTRACE --security-opt seccomp=unconfined \
    -v "$L:$L:Z" -e L="$L" -e P="$P" localhost/px64-ubuntu bash -c '
set -u
T=$(mktemp -d); mkdir -p $T/bin $T/fx $T/tr
cp $L/scent-out/scent $L/scent-out/egrep $L/scent-out/fgrep $T/bin/; ln -s scent $T/bin/grep
python3 $P/tests/mpx5-scent.d/fixture.py $T/fx >/dev/null
printf "#!$T/bin/scent -F\377\n" > $T/fx/ff-arg; chmod 755 $T/fx/ff-arg
cd $T/fx
k=0
run() { k=$((k+1)); strace -f -qq -o $T/tr/$k.txt "$@" >/dev/null 2>&1 </dev/null; echo "run $k rc=$?: $*"; }
run $T/bin/grep cat words.txt
run $T/bin/grep -e cat -f pats.txt words.txt
k=$((k+1)); cat words.txt | strace -f -qq -o $T/tr/$k.txt $T/bin/grep -c cat - ctx.txt >/dev/null 2>&1; echo "run $k: a pipe on standard input"
run $T/bin/grep -z b z.dat
run $T/bin/grep match nul.dat
run $T/bin/grep cat nosuch
run $T/bin/grep -P x words.txt
run $T/bin/grep -E -F x words.txt
run $T/bin/grep -r cat .
run $T/bin/grep --help
run $T/bin/grep --version
run $T/bin/grep -n -C1 -m3 alpha big.txt
run $T/bin/grep -c alpha big.txt
run ./ff-arg
sed -E "s/^[0-9]+ +//; s/\(.*//; s/^<\.\.\. ([a-z0-9_]+) resumed>.*/\1/" $T/tr/*.txt | grep -E "^[a-z_0-9]+$" | sort | uniq -c | sort -k2 > $T/names
echo "distinct calls: $(wc -l < $T/names)"
cat $T/names
grep -h "= -1 E" $T/tr/*.txt | sed -E "s/^[0-9]+ +//" | sed -E "s/\(.*= -1 (E[A-Z]+).*/ -> \1/" | sort | uniq -c
' > "$P/notes/px64/census.out" 2>&1
echo "census rc=$?"
tail -5 "$P/notes/px64/census.out"
