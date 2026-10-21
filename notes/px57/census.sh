#!/bin/bash
# px57 on kasumi: the syscall census of aspen and of the musl lupin, `strace -f -n` of their own runs on
# Linux 7.2.8 in px13-ubuntu (a throwaway container; strace(1) as documentation, black-box), with PAX's
# environment (HOME=/ TERM=linux PAX=1 PATH=/bin):
#   aspen: `aspen --version`, and the four commands of the session (user/console/aspen.keys) over a tree
#          made as tests/mpx5-aspen makes its image's, chrooted;
#   lupin: `lupin --version`; `lupin run` of three programs of its own corpus (vendor/upstream/corpus at
#          the tag: hello.lu, fs/roundtrip.lu, procs.lu), each alone in a directory (a directory is a
#          module, D32), and `lupin conform-run --json` of os/args_cwd.lu; then the session's programs
#          (user/lupin/*.lu at /usr/share/lupin) run and conform-run the way the session runs them.
# Each run's calls by name and number, their failures, and the union -> OUTDIR (~/lanes/px57/ev/census).
#   census.sh ASPEN LUPIN   (the tree: PX57_TREE)
L=$HOME/lanes/px57; X=${PX57_TREE:-$L/pax}; A=$1 U=$2
O=$L/ev/census; rm -rf $O; mkdir -p $O
sha256sum $A $U | tee $O/binaries.txt
podman run --rm --network none --cpuset-cpus 4-15 -v $L:$L:Z localhost/px13-ubuntu bash -c "
set -u
O=$O; X=$X
strace -V | head -n 1 > \$O/strace-version.txt; uname -r >> \$O/strace-version.txt
E='env -i HOME=/ TERM=linux PAX=1 PATH=/bin'
tr() { # name dir cmd... : strace the command in dir, its output kept
  n=\$1 d=\$2; shift 2
  (cd \$d && strace -f -n -qq -o \$O/\$n.strace \"\$@\" > \$O/\$n.out 2>&1; echo \$? > \$O/\$n.rc)
}
# aspen's tree, as tests/mpx5-aspen's image (and the binary at /bin/aspen)
R=/r; mkdir -p \$R/bin \$R/etc \$R/home/pax/Script \$R/usr/share/pax/keys \$R/usr/lib
cp $A \$R/bin/aspen
printf '/bin/sh -i -m\n' > \$R/etc/pax-run; printf 'pax\n' > \$R/etc/hostname; printf 'PAX: aspen at the console (px57)\n' > \$R/etc/motd
printf '# pax profile\n' > \$R/home/pax/.profile; printf 'a note\n' > \$R/home/pax/notes.txt; printf 'echo hi\n' > \$R/home/pax/Script/greet.sh
printf 'PAX: a Linux-compatible system written in wolf.\n' > \$R/usr/share/pax/README; cp \$X/user/console/aspen.keys \$R/usr/share/pax/keys/
for b in env head sh pelt as; do : > \$R/bin/\$b; done
tr aspen-version / \$E chroot \$R /bin/aspen --version
tr aspen-etc / \$E chroot \$R /bin/aspen /etc
tr aspen-home / \$E chroot \$R /bin/aspen -a -L 2 /home/pax
tr aspen-json / \$E chroot \$R /bin/aspen -J /bin
tr aspen-du / \$E chroot \$R /bin/aspen --du /usr
# lupin: its corpus at the tag
git clone -q --depth 1 --branch v0.1.55 https://github.com/wolffe-lang/wolf-interp /src 2>/dev/null || cp -a $L/src/wolf-interp /src
C=/src/vendor/upstream/corpus
for p in hello fs/roundtrip procs os/args_cwd; do d=/w/\$(echo \$p | tr / -); mkdir -p \$d; cp \$C/\$p.lu \$d/; done
tr lupin-version / \$E $U --version
tr lupin-hello /w/hello \$E $U run hello.lu
tr lupin-roundtrip /w/fs-roundtrip \$E $U run roundtrip.lu
tr lupin-procs /w/procs \$E $U run procs.lu
tr lupin-conform-args_cwd /w/os-args_cwd \$E $U conform-run --json args_cwd.lu
mkdir -p /usr/share/lupin && cp \$X/user/lupin/*.lu /usr/share/lupin/
printf '//! member: false\nfn main() -> !int {\n    print(\"typed\")\n    0\n}\n' > /x.lu
tr lupin-s-hello / \$E $U run /usr/share/lupin/hello.lu
tr lupin-s-x / \$E $U run x.lu
tr lupin-s-loop / \$E $U conform-run --json /usr/share/lupin/loop.lu
tr lupin-s-signal / \$E $U run /usr/share/lupin/signal.lu
tr lupin-s-host / \$E $U conform-run --json /usr/share/lupin/host.lu
"
cd $O
for f in *.strace; do
  n=${f%.strace}
  # PID [ NR] name(... ) = R ; the calls by number and name, and the failures
  sed -nE 's/^[0-9]+ +\[ *([0-9]+)\] ([a-z0-9_]+)\(.*/\1 \2/p' $f | sort -n | uniq -c | awk '{print $2, $3, $1}' > $n.calls
  sed -nE 's/^[0-9]+ +\[ *([0-9]+)\] ([a-z0-9_]+)\(.* = -1 ([A-Z0-9]+) .*/\1 \2 \3/p' $f | sort -n | uniq -c | awk '{print $2, $3, $4, $1}' > $n.fails
done
for t in aspen lupin; do
  cat $t-*.calls | awk '{print $1, $2}' | sort -n -u > $t.union
  echo "== $t: $(wc -l < $t.union) calls by name"; cat $t.union | tr '\n' ' '; echo
  echo "-- $t failures:"; cat $t-*.fails | awk '{print $1, $2, $3}' | sort -u | tr '\n' ';'; echo
done
for f in *.rc; do printf '%s %s; ' ${f%.rc} $(cat $f); done; echo
