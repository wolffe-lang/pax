#!/bin/bash
# px57 on kasumi: the maintainer's playground image with aspen and lupin (item 4), by the orchestrator's own
# scripts (~/lanes/orch-paxplay/build.sh, then assemble.sh), extended as px54 and px56 extended them, the
# pre-edit copies kept (~/lanes/px57/ev/orch-*.before): build.sh builds aspen (tools/mkaspen, in
# px13-ubuntu with the rest) and the musl lupin (tools/mklupin, in the throwaway Rust image, made from
# notes/px57/rust/Containerfile when it is not there); assemble.sh puts /bin/aspen and /bin/lupin (stripped
# copies, as the playground's others) and the four programs at /usr/share/lupin in the archive, and its motd
# names the pins, aspen and lupin. The playground's pax clone moves to this branch's COMMIT.
# Each script's sha256 before and after, and the ISOs'.   playground.sh COMMIT
set -u
O=$HOME/lanes/orch-paxplay E=$HOME/lanes/px57/ev
C=$1
mkdir -p $E
[ -f $E/orch-build.sh.before ] || cp -p $O/build.sh $E/orch-build.sh.before
[ -f $E/orch-assemble.sh.before ] || cp -p $O/assemble.sh $E/orch-assemble.sh.before
sha256sum $E/orch-build.sh.before $E/orch-assemble.sh.before $O/out/pax-playground.iso
git -C $O/pax fetch -q origin px57 && git -C $O/pax checkout -q --detach "$C" || exit 2
git -C $O/pax log --oneline -1
python3 - "$O" "$C" <<'PY'
import sys
o, c = sys.argv[1], sys.argv[2][:7]
p = o + "/build.sh"
s = open(p).read()
if "mkaspen" not in s:
    old = 'tools/mklope $W/lope > $W/lope.txt 2>&1; echo "mklope rc=$?"\n'
    assert old in s
    s = s.replace(old, old + 'tools/mkaspen $W/aspen > $W/aspen.txt 2>&1; echo "mkaspen rc=$?"\n')
    s = s.replace("# shell, boreutils, su, as, play, lope) from pax trunk,", "# shell, boreutils, su, as, play, lope, aspen, lupin) from pax trunk,")
    s = s.replace("ls -la $W/pelt $W/lope $W/bore $W/bin $W/su $W/play", "ls -la $W/pelt $W/lope $W/aspen $W/bore $W/bin $W/su $W/play")
    old = 'echo "build.sh done rc=$?"\n'
    assert old in s
    s = s.replace(old, '''rc=$?
# px57: the musl lupin, built in the throwaway Rust image (px13-ubuntu with rustup inside it).
R=${PAX_RUST_IMAGE:-localhost/px57-rust}
podman image exists $R || podman build -t $R -f $L/pax/notes/px57/rust/Containerfile $L/pax/notes/px57/rust
podman run --rm --cpuset-cpus 10-15 -v $L:$L:Z -e L="$L" $R bash -c 'cd $L/pax && tools/mklupin $L/w/lupin > $L/w/lupin.txt 2>&1; echo "mklupin rc=$?"; ls -la $L/w/lupin'
echo "build.sh done rc=$rc"
''')
    open(p, "w").write(s)
p = o + "/assemble.sh"
s = open(p).read()
old = 'strip -o $S/lope $W/lope/lope; '
assert old in s
if "$S/aspen" not in s:
    s = s.replace(old, old + 'strip -o $S/aspen $W/aspen/aspen; strip -o $S/lupin $W/lupin/lupin; ')
lines = s.split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith("PAX playground: "))
j = next(k for k, l in enumerate(lines) if l == "MOTD" and k > i)
lines[i:j] = [
    "PAX playground: pax px57 %s, wolf 0.2.34, pelt 90d7c64, boreutils cc64f68, lope 5ac37df," % c,
    "aspen 103ba46, lupin 0.1.55 (static musl). pelt is pid 1 with job control (sh -i -m).",
    "Try: ls -l /bin, jobs, Ctrl-Z, bg, fg, kill %1, timeout, su pax, play mambo.",
    "lope jumps (its hook in /etc/shrc): cd /etc, cd /bin, then etc alone, g -, gi.",
    "aspen is tree(1) in wolf: aspen /, aspen -a -L 2 /home/pax, aspen -J /bin, aspen --du /usr.",
    "lupin runs wolf programs: cd /usr/share/lupin; lupin run hello.lu (or write one: cat > x.lu).",
    "Files and lope's store are in memory, gone at the next boot. exit (or Ctrl-D) halts.",
]
s = "\n".join(lines)
old = 'for t in user/tunes/*; do args+=(/usr/share/tunes/${t##*/}=$t:644); done'
assert old in s
if "/usr/share/lupin/" not in s:
    s = s.replace(old, old + '\nfor t in user/lupin/*.lu; do args+=(/usr/share/lupin/${t##*/}=$t:644); done')
open(p, "w").write(s)
PY
sha256sum $O/build.sh $O/assemble.sh
diff $E/orch-build.sh.before $O/build.sh; diff $E/orch-assemble.sh.before $O/assemble.sh
bash $O/build.sh && bash $O/assemble.sh
cat $O/w/aspen.txt $O/w/lupin.txt $O/w/pelt.txt $O/w/lope.txt | grep -E '^(aspen|lupin|pelt|lope) [0-9a-f]{64}'
sha256sum $O/out/pax-playground.iso $O/out/pax-playground.iso $O/out/pax-smoke.iso
ls -l $O/out/pax-playground.iso
