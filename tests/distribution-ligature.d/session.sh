#!/bin/sh
# tests/distribution-ligature.d/session.sh — px128's session on the dev image, typed at its console as
# root (`sh /usr/share/distribution-ligature/session.sh`), so it runs with the console's own environment
# (/etc/shrc's exports). Every line the judge reads starts `DLIG `; ldtime's lines go to /tmp/l/ldtime.log
# and are printed at the end. Outputs are removed once read: the live image keeps its files in memory, so
# a linked program left behind would take memory from the next link. First, with nothing else in memory,
# pelt and den, each linked by ligature and by lld; then the default, the opt-in, hello, netproc, the
# self-link and a refusal.
S=/usr/share/distribution-ligature
T=/tmp/l
rm -rf $T && mkdir -p $T && cd $T || exit 1
cp -R $S/src/. $T/ || exit 1
LX=/usr/libexec/distribution-ligature/ldtime
echo "DLIG env WOLF_LD=[${WOLF_LD-unset}]"
if [ -x /usr/bin/ligature ]; then
    echo "DLIG version $(/usr/bin/ligature --version 2>&1 | head -n 1)"
else
    echo "DLIG version absent"
fi
echo "DLIG release $(grep '^ligature ' /etc/pax-release | cut -d ' ' -f 1-2)"
# build NAME LINKER DIR ENTRY OUT: a link measured by ldtime, by ligature (lig) or by the image's cc and
# ld.lld (lld): `wolf build` with WOLF_LD naming ldtime, which runs the linker as its one child.
build() {
    case $2 in lig) real=/usr/bin/ligature ;; lld) real=/usr/bin/cc ;; esac
    rm -f $5
    (cd $3 && LDTIME_REAL=$real LDTIME_LOG=$T/ldtime.log LDTIME_LABEL="$1-$2" WOLF_LD=$LX \
        wolf build $4 -o $5 > $T/$1-$2.build 2>&1)
    rc=$?
    if [ -f $5 ]; then have=yes; else have=no; fi
    echo "DLIG build $1 $2 rc=$rc output=$have"
    grep -e 'selected linker' -e 'ligature' -e 'memory allocation' $T/$1-$2.build | head -n 3 | cut -c1-200 |
        while IFS= read -r l; do echo "DLIG why $1-$2: $l"; done
}
# run NAME LINKER OUT ARGS...: the program's own output and status, digested
run() {
    n=$1 l=$2 o=$3; shift 3
    "$o" "$@" > $T/$n-$l.out 2>&1
    echo "status=$?" >> $T/$n-$l.out
    echo "DLIG run $n $l $(sha256sum < $T/$n-$l.out | cut -c1-16) $(tr '\n' '|' < $T/$n-$l.out | cut -c1-160)"
}
# pelt, and den, the largest of the image's programs its compiler builds on the live image (yew's
# compile does not fit it), each by both linkers.
for p in pelt den; do
    entry=$(cat $T/$p/ENTRY)
    build $p lig $T/$p $entry $T/$p.lig
    build $p lld $T/$p $entry $T/$p.lld
    for l in lig lld; do
        [ -f $T/$p.$l ] || continue
        case $p in
            pelt) run $p $l $T/$p.$l -c 'echo pelt-ok; exit 3' ;;
            den) run $p $l $T/$p.$l --version ;;
        esac
    done
    rm -rf $T/$p.lig $T/$p.lld $T/$p
done
# The default: no WOLF_LD, so wolf links through lld and names it in a note.
(cd $T/hello && wolf build hello.lu -o $T/hello.default > $T/default.build 2>&1)
echo "DLIG default rc=$? $(grep 'wolf build: note' $T/default.build | head -n 1 | cut -c1-200)"
run hello default $T/hello.default
# The opt-in: WOLF_LD names ligature, and no note is printed.
(cd $T/hello && WOLF_LD=/usr/bin/ligature wolf build hello.lu -o $T/hello.optin > $T/optin.build 2>&1)
echo "DLIG optin rc=$? notes=$(grep -c 'wolf build: note' $T/optin.build)"
run hello optin $T/hello.optin
build hello lig $T/hello hello.lu $T/hello.lig
run hello lig $T/hello.lig
build hello lld $T/hello hello.lu $T/hello.lld
run hello lld $T/hello.lld
d=
for k in default lld lig optin; do
    if [ -f $T/hello.$k ]; then d="$d $k=$(sha256sum < $T/hello.$k | cut -c1-64)"; else d="$d $k=none"; fi
done
echo "DLIG digests$d"
rm -f $T/hello.default $T/hello.lld $T/hello.optin
build netproc lig $T/netproc netproc.lu $T/netproc.lig
run netproc lig $T/netproc.lig
build netproc lld $T/netproc netproc.lu $T/netproc.lld
run netproc lld $T/netproc.lld
rm -rf $T/netproc.lig $T/netproc.lld $T/netproc
# The self-link: ligature's own source compiled here and linked by ligature; that linker then links
# hello, and must give the shipped ligature's bytes.
build ligature lig $T/ligature src/ligature.lu $T/ligature.lig
run ligature lig $T/ligature.lig --version
build ligature lld $T/ligature src/ligature.lu $T/ligature.lld
run ligature lld $T/ligature.lld --version
rm -rf $T/ligature.lld $T/ligature
(cd $T/hello && WOLF_LD=$T/ligature.lig wolf build hello.lu -o $T/hello.self > $T/self.build 2>&1)
echo "DLIG self rc=$? $(sha256sum < $T/hello.self | cut -c1-64)"
rm -f $T/ligature.lig $T/hello.self $T/hello.lig
# A refusal: no musl start files where ligature is told to look, so it refuses by name, wolf build
# fails, and nothing falls back to lld.
(cd $T/hello && LIGATURE_SYSROOT=$T/no-sysroot WOLF_LD=/usr/bin/ligature wolf build hello.lu -o $T/hello.refused > $T/refused.build 2>&1)
rc=$?
if [ -e $T/hello.refused ]; then have=yes; else have=no; fi
echo "DLIG refused rc=$rc output=$have"
grep -e 'selected linker' -e 'ligature' -e 'no-sysroot' $T/refused.build | head -n 3 | cut -c1-200 |
    while IFS= read -r l; do echo "DLIG why refused: $l"; done
# (the image has no sed: the shell's own loop prefixes each line)
[ -f $T/ldtime.log ] && while IFS= read -r l; do echo "DLIG $l"; done < $T/ldtime.log
echo "DLIG end session"
