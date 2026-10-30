#!/usr/bin/env bash
# px78b: the plant (px78b-plant-y, y accepted as yes), locally (a module lane, rule 7 R2): the ui unit and the
# QEMU cancel-words row, each expected red by name. Runs after the stick chain; block A via ctr.sh.
set -uo pipefail
L=/home/mfwolffe/lanes/px78b
printf '%s\n' "$$" > $L/plant.pid
while kill -0 "$(cat $L/schain.pid)" 2>/dev/null; do python3 -I -c 'import time; time.sleep(15)'; done
rm -rf $L/w-plant; mkdir -p $L/w-plant; cp -a $L/w/inputs $L/w-plant/inputs
inner='cd '"$L"'/plant && git log --oneline -1
tests/mpx6-install --only ui --work '"$L"'/w-plant/units; echo "UNIT-UI-EXIT=$?"
tools/mkinstall '"$L"'/w-plant/inputs/build/install-gate/bin || exit 9
export SOURCE_DATE_EPOCH=1700000000 PAX_INSTALL_TIER=native
PAX_INSTALL_FAULT=cancel-words python3 -I tests/mpx6-install.d/install.py $PWD '"$L"'/w-plant/inputs '"$L"'/w-plant/fault-cancel-words no vdb; echo "ROW-CANCEL-WORDS-EXIT=$?"'
bash $L/ctr.sh plant localhost/px75-ubuntu:2 0 bash -c "$inner"
printf '%s PLANT DONE\n' "$(date -u +%FT%TZ)"
