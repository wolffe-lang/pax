#!/usr/bin/env bash
# px77c: the qualify boots, the Linux spelling oracle, then the record leg (A), one after another;
# each takes and releases block A itself. A step's failure is recorded and the chain goes on.
L=/home/mfwolffe/lanes/px77c
printf '%s\n' "$$" > "$L/chain-1.pid"
for m in s-old s-new b-old b-new c-new; do bash "$L/qualify.sh" "$m"; done
bash "$L/linux-oracle.sh" ident
cp "$L/out/pax-install-56b9f554.img" "$L/copy-legA.img"
bash "$L/leg.sh" A "$L/copy-legA.img" tcg
printf '%s CHAIN-1 DONE\n' "$(date -u +%FT%TZ)"
