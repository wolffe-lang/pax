#!/bin/bash
# px53 on kasumi: the maintainer's playground image at the new pins, by
# the orchestrator's own scripts (~/lanes/orch-paxplay/build.sh, then
# assemble.sh), unchanged but for their pins: the playground's pax clone
# moved to this branch's commit and assemble.sh's motd line naming it and
# the new pins. The ISO's sha256 is read, and the old one's before it.
#   playground.sh COMMIT
O=$HOME/lanes/orch-paxplay
sha256sum $O/out/pax-playground.iso
git -C $O/pax fetch -q origin px53 && git -C $O/pax checkout -q --detach "$1" && git -C $O/pax log --oneline -1
sed -i "s/^PAX playground: pax trunk d6fbcdc, wolf 0.2.32, pelt 2676879, boreutils 43ee185\./PAX playground: pax px53 $1, wolf 0.2.33, pelt be1a75d, boreutils cc64f68./" $O/assemble.sh
grep -n 'PAX playground:' $O/assemble.sh
bash $O/build.sh && bash $O/assemble.sh
sha256sum $O/out/pax-playground.iso $O/out/pax-smoke.iso
