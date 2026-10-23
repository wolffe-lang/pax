#!/bin/bash
# px64, kasumi: the two plant branches, each px64's head plus one break,
# never merged.
set -eu
cd $HOME/lanes/px64/pax
base=$(git rev-parse px64)
git checkout -q -b px64-plant-wrapper "$base"
python3 - <<'PY'
p = "tests/mpx5-scent"
s = open(p).read()
old = '''    for f in "$r"/bin/*; do [ -L "$f" ] || args+=("/bin/${f##*/}=$f:755"); done'''
new = '''    for f in "$r"/bin/*; do [ -L "$f" ] || [ "${f##*/}" = egrep ] || args+=("/bin/${f##*/}=$f:755"); done # PLANT: the image without /bin/egrep'''
assert old in s
open(p, "w").write(s.replace(old, new))
PY
git commit -q -am "PLANT: leave /bin/egrep out of mpx5-scent's image"
git checkout -q -b px64-plant-link "$base"
git revert --no-edit 8dac9af >/dev/null
git commit -q --amend -m "PLANT: the tree adopts no archive link (revert 8dac9af)"
git checkout -q px64
git log --oneline -1 px64-plant-wrapper; git log --oneline -1 px64-plant-link; git branch --show-current
git push -q origin px64 px64-plant-wrapper px64-plant-link 2>&1 | tail -3
git ls-remote origin 'refs/heads/px64*'
