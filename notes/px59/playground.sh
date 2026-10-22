#!/bin/bash
# px59 on kasumi: the maintainer's playground image with the console for
# an editor (item 4), by the orchestrator's own scripts
# (~/lanes/orch-paxplay/build.sh, then assemble.sh), changed as px57's
# notes/px57/playground.sh changed them: the playground's pax clone moves
# to this branch's COMMIT (the new kernel, built by build.sh as before);
# build.sh builds yew (tools/mkyew, in px13-ubuntu with the rest);
# assemble.sh puts /bin/yew (a stripped copy, as the playground's others)
# in the archive and its motd names the commit and yew. The pre-edit
# copies kept (~/lanes/px59/ev/orch-*.before); each script's sha256
# before and after, and the ISOs', twice.   playground.sh COMMIT
set -u
O=$HOME/lanes/orch-paxplay E=$HOME/lanes/px59/ev
C=$1
mkdir -p $E
[ -f $E/orch-build.sh.before ] || cp -p $O/build.sh $E/orch-build.sh.before
[ -f $E/orch-assemble.sh.before ] || cp -p $O/assemble.sh $E/orch-assemble.sh.before
sha256sum $E/orch-build.sh.before $E/orch-assemble.sh.before $O/out/pax-playground.iso
git -C $O/pax fetch -q origin px59 && git -C $O/pax checkout -q --detach "$C" || exit 2
git -C $O/pax log --oneline -1
python3 - "$O" "$C" <<'PY'
import sys
o, c = sys.argv[1], sys.argv[2][:7]
p = o + "/build.sh"
s = open(p).read()
if "mkyew" not in s:
    old = 'tools/mkaspen $W/aspen > $W/aspen.txt 2>&1; echo "mkaspen rc=$?"\n'
    assert old in s
    s = s.replace(old, old + 'tools/mkyew $W/yew > $W/yew.txt 2>&1; echo "mkyew rc=$?"\n')
    s = s.replace("# shell, boreutils, su, as, play, lope, aspen, lupin) from pax trunk,",
                  "# shell, boreutils, su, as, play, lope, aspen, lupin, yew) from pax trunk,")
    s = s.replace("ls -la $W/pelt $W/lope $W/aspen $W/bore", "ls -la $W/pelt $W/lope $W/aspen $W/yew $W/bore")
    open(p, "w").write(s)
p = o + "/assemble.sh"
s = open(p).read()
old = 'strip -o $S/aspen $W/aspen/aspen; '
assert old in s
if "$S/yew" not in s:
    s = s.replace(old, old + 'strip -o $S/yew $W/yew/yew; ')
lines = s.split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith("PAX playground: "))
lines[i] = "PAX playground: pax px59 %s, wolf 0.2.34, pelt 90d7c64, boreutils cc64f68, lope 5ac37df," % c
j = next(k for k, l in enumerate(lines) if l.startswith("lupin runs wolf programs: "))
if not lines[j + 1].startswith("yew is the editor"):
    lines.insert(j + 1, "yew is the editor (77c1083), on this screen as on a Linux VT: yew notes.txt; i types, Esc, :w saves, :q quits, C-z and fg.")
s = "\n".join(lines)
open(p, "w").write(s)
PY
sha256sum $O/build.sh $O/assemble.sh
diff $E/orch-build.sh.before $O/build.sh; diff $E/orch-assemble.sh.before $O/assemble.sh
# (the motd sits inside assemble.sh's single-quoted script: no apostrophe in it)
! sed -n '/^PAX playground: /,/^MOTD$/p' $O/assemble.sh | grep -q "'" || { echo "playground: an apostrophe in the motd"; exit 2; }
if [ -z "${PX59_PLAY_SKIP_BUILD:-}" ]; then bash $O/build.sh || exit 1; fi
bash $O/assemble.sh
cat $O/w/yew.txt $O/w/pelt.txt | grep -E '^(yew|pelt) [0-9a-f]{64}'
sha256sum $O/w/strip/yew $O/out/pax-playground.iso $O/out/pax-playground.iso $O/out/pax-smoke.iso
ls -l $O/out/pax-playground.iso
