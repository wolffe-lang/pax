#!/bin/bash
# px54 on kasumi: the maintainer's playground image with lope (item 5),
# by the orchestrator's own scripts (~/lanes/orch-paxplay/build.sh, then
# assemble.sh), changed only as the contract says: build.sh builds lope
# (tools/mklope, from a clone of lope's pin inside the playground's
# directory, since lope is private), assemble.sh puts /bin/lope (a
# stripped copy, as the playground's others) and /etc/shrc in the
# archive, starts the console shell with the hook
# (`/bin/env ENV=/etc/shrc /bin/sh -i -m`), and its motd names the pins
# and lope. The playground's pax clone moves to this branch's COMMIT.
# Each script's sha256 before and after, and the ISOs'.
#   playground.sh COMMIT BUNDLE
set -u
O=$HOME/lanes/orch-paxplay
C=$1 BUNDLE=$2
sha256sum $O/build.sh $O/assemble.sh $O/out/pax-playground.iso
if [ ! -d $O/lope ]; then
  git init -q -b scratch $O/lope && git -C $O/lope fetch -q "$BUNDLE" refs/remotes/origin/trunk:refs/heads/trunk || exit 2
fi
git -C $O/lope checkout -q --detach 5ac37df22866e8fd418c67b611f48ff30e8a2630 || exit 2
git -C $O/lope log --oneline -1
git -C $O/pax fetch -q origin px54 && git -C $O/pax checkout -q --detach "$C" || exit 2
git -C $O/pax log --oneline -1
python3 - "$O" "$C" <<'PY'
import sys
o, c = sys.argv[1], sys.argv[2][:7]
p = o + "/build.sh"
s = open(p).read()
if "mklope" not in s:
    old = '-e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e U="$U" -e L="$L" localhost/px13-ubuntu'
    assert old in s
    s = s.replace(old, '-e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_LOPE_REPO=$L/lope -e U="$U" -e L="$L" localhost/px13-ubuntu')
    old = 'tools/mkpelt $W/pelt > $W/pelt.txt 2>&1; echo "mkpelt rc=$?"\n'
    assert old in s
    s = s.replace(old, old + 'tools/mklope $W/lope > $W/lope.txt 2>&1; echo "mklope rc=$?"\n')
    s = s.replace("# shell, boreutils, su, as, play) from pax trunk,", "# shell, boreutils, su, as, play, lope) from pax trunk,")
    s = s.replace("ls -la $W/pelt $W/bore $W/bin $W/su $W/play", "ls -la $W/pelt $W/lope $W/bore $W/bin $W/su $W/play")
    open(p, "w").write(s)
p = o + "/assemble.sh"
s = open(p).read()
old = 'strip -o $S/pelt $W/pelt/pelt; '
assert old in s
if "$S/lope" not in s:
    s = s.replace(old, old + 'strip -o $S/lope $W/lope/lope; ')
lines = s.split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith("PAX playground: "))
j = next(k for k, l in enumerate(lines) if l == "MOTD" and k > i)
lines[i:j] = [
    "PAX playground: pax px54 %s, wolf 0.2.33, pelt 90d7c64, boreutils cc64f68." % c,
    "pelt is pid 1 with job control (sh -i -m). Try: ls -l /bin, jobs, Ctrl-Z, bg, fg,",
    "kill %1, timeout, su pax, play mambo. exit (or Ctrl-D) halts the machine.",
    "lope 5ac37df jumps (its hook in /etc/shrc): cd /etc, cd /bin, then etc alone,",
    "g -, g, gi, lope list. Its store is in memory, gone at the next boot.",
]
s = "\n".join(lines)
old = 'printf "/bin/sh -i -m\\n" > $W/play.run'
if old in s:
    s = s.replace(old, 'printf "/bin/env ENV=/etc/shrc /bin/sh -i -m\\n" > $W/play.run')
assert 'ENV=/etc/shrc /bin/sh -i -m' in s
old = '/etc/motd=$W/motd:644)'
if "/etc/shrc=user/shrc" not in s:
    assert old in s
    s = s.replace(old, '/etc/motd=$W/motd:644 /etc/shrc=user/shrc:644)')
open(p, "w").write(s)
PY
sha256sum $O/build.sh $O/assemble.sh
diff ~/lanes/px54/orch-before/build.sh $O/build.sh; diff ~/lanes/px54/orch-before/assemble.sh $O/assemble.sh
bash $O/build.sh && bash $O/assemble.sh
cat $O/w/lope.txt $O/w/pelt.txt | grep -E '^(lope|pelt) '
sha256sum $O/out/pax-playground.iso $O/out/pax-playground.iso $O/out/pax-smoke.iso
ls -l $O/out/pax-playground.iso
