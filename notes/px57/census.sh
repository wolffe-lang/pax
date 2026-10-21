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
# lupin's corpus at the tag (a clone on the host: git only, nothing built or run there)
[ -d $L/src/wolf-interp ] || git clone -q --depth 1 --branch v0.1.55 https://github.com/wolffe-lang/wolf-interp $L/src/wolf-interp
git -C $L/src/wolf-interp log --oneline -1 | tee -a $O/binaries.txt
podman run --rm --network none --cpuset-cpus 4-15 -v $L:$L:Z localhost/px13-ubuntu bash -c "
set -u
O=$O; X=$X
strace -V | head -n 1 > \$O/strace-version.txt; uname -r >> \$O/strace-version.txt
trc() { # name dir cmd... : strace the command in dir (PAX's environment), its output kept
  n=\$1 d=\$2; shift 2
  (cd \$d && /usr/bin/env -i HOME=/ TERM=linux PAX=1 PATH=/bin /usr/bin/strace -f -n -qq -o \$O/\$n.strace \"\$@\" > \$O/\$n.out 2>&1; echo \$? > \$O/\$n.rc)
}
# aspen's tree, as tests/mpx5-aspen's image (and the binary at /bin/aspen)
R=/r; mkdir -p \$R/bin \$R/etc \$R/home/pax/Script \$R/usr/share/pax/keys \$R/usr/lib
cp $A \$R/bin/aspen
printf '/bin/sh -i -m\n' > \$R/etc/pax-run; printf 'pax\n' > \$R/etc/hostname; printf 'PAX: aspen at the console (px57)\n' > \$R/etc/motd
printf '# pax profile\n' > \$R/home/pax/.profile; printf 'a note\n' > \$R/home/pax/notes.txt; printf 'echo hi\n' > \$R/home/pax/Script/greet.sh
printf 'PAX: a Linux-compatible system written in wolf.\n' > \$R/usr/share/pax/README; cp \$X/user/console/aspen.keys \$R/usr/share/pax/keys/
for b in env head sh pelt as; do : > \$R/bin/\$b; done
trc aspen-version / /usr/sbin/chroot \$R /bin/aspen --version
trc aspen-etc / /usr/sbin/chroot \$R /bin/aspen /etc
trc aspen-home / /usr/sbin/chroot \$R /bin/aspen -a -L 2 /home/pax
trc aspen-json / /usr/sbin/chroot \$R /bin/aspen -J /bin
trc aspen-du / /usr/sbin/chroot \$R /bin/aspen --du /usr
# lupin: its corpus at the tag
C=$L/src/wolf-interp/vendor/upstream/corpus
for p in hello fs/roundtrip procs os/args_cwd; do d=/w/\$(echo \$p | tr / -); mkdir -p \$d; cp \$C/\$p.lu \$d/; done
mkdir -p /w/fs-roundtrip/target # roundtrip.lu writes target/s38-fs-roundtrip.tmp (the corpus runner's tree)
trc lupin-version / $U --version
trc lupin-hello /w/hello $U run hello.lu
trc lupin-roundtrip /w/fs-roundtrip $U run roundtrip.lu
trc lupin-procs /w/procs $U run procs.lu
trc lupin-conform-args_cwd /w/os-args_cwd $U conform-run --json args_cwd.lu
mkdir -p /usr/share/lupin && cp \$X/user/lupin/*.lu /usr/share/lupin/
printf '//! member: false\nfn main() -> !int {\n    print(\"typed\")\n    0\n}\n' > /x.lu
trc lupin-s-hello / $U run /usr/share/lupin/hello.lu
trc lupin-s-x / $U run x.lu
trc lupin-s-loop / $U conform-run --json /usr/share/lupin/loop.lu
trc lupin-s-signal / $U run /usr/share/lupin/signal.lu
trc lupin-s-host / $U conform-run --json /usr/share/lupin/host.lu
"
cd $O
for f in *.strace; do
  n=${f%.strace}
  # The program's own calls: chroot's (aspen's runs) before its execve of the program are not, so each
  # pid's lines count from its successful execve of /bin/aspen or the lupin under test, and a pid first
  # seen after one (a thread, a child) counts whole.
  case $n in aspen-*) t=/bin/aspen ;; *) t=$U ;; esac
  awk -v t="$t" '
    { pid = $1 }
    !(pid in seen) { seen[pid] = 1; if (any) on[pid] = 1 }
    index($0, "execve(\"" t "\"") && / = 0$/ { on[pid] = 1; any = 1 }
    on[pid] { print }' $f > $n.own
  # PID [ NR] name(... ) = R ; the calls by number and name, and the failures
  sed -nE 's/^[0-9]+ +\[ *([0-9]+)\] ([a-z0-9_]+)\(.*/\1 \2/p' $n.own | sort -n | uniq -c | awk '{print $2, $3, $1}' > $n.calls
  sed -nE 's/^[0-9]+ +\[ *([0-9]+)\] ([a-z0-9_]+)\(.* = -1 ([A-Z0-9]+) .*/\1 \2 \3/p' $n.own | sort -n | uniq -c | awk '{print $2, $3, $4, $1}' > $n.fails
done
for t in aspen lupin; do
  cat $t-*.calls | awk '{print $1, $2}' | sort -n -u > $t.union
  echo "== $t: $(wc -l < $t.union) calls by name"; cat $t.union | tr '\n' ' '; echo
  echo "-- $t failures:"; cat $t-*.fails | awk '{print $1, $2, $3}' | sort -u | tr '\n' ';'; echo
done
for f in *.rc; do printf '%s %s; ' ${f%.rc} $(cat $f); done; echo
