#!/bin/bash
# px53 on kasumi: real root's recordings of the pjobs, groups and sigs sessions.
# notes/px50/vmjob.c (unchanged; built static in px13-ubuntu) as pid 1 of
# kasumi's own kernel under QEMU (notes/px48/linux-vm.sh), the suite
# build's own pjobs archive, one boot a session: each of sh18's cases as
# root (`/bin/sh -i -m`) and as 1000:1000 (`/bin/as 1000 1000 /bin/sh -i
# -m`), and groups as both; px53: sigs (`/bin/sigwolf`, then through
# `as`, nothing typed) from the build's sigs archive. Eight boots at a
# time, on cpus 4-15.
#   vm-rec.sh BUILDTAG OUTDIR [NAME...]   (NAME: pjobs-<case>, pjobs-user-<case>, groups, groups-user, sigs, sigs-user; default all)
L=$HOME/lanes/px53
W=$L/build/$1/mpx5-jobs; O=$2; shift 2
P=$L/pax
set -u
mkdir -p $O $L/bin
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cc -static -O1 -o $L/bin/vmjob51 $P/notes/px50/vmjob.c && sha256sum $L/bin/vmjob51 $P/notes/px50/vmjob.c" || exit 1
sha256sum $W/pjobs.cpio $W/sigs.cpio
: > $L/bin/empty.keys
cases=$(sed -n 's/^PCASES="\(.*\)/\1/p; /^    c_jc/p' $P/tests/mpx5-jobs | tr -d '"' | tr -s ' \n' ' ')
names=("$@")
if [ ${#names[@]} = 0 ]; then
  for c in $cases; do names+=("pjobs-$c" "pjobs-user-$c"); done
  names+=(groups groups-user sigs sigs-user)
fi
n=0
for nm in "${names[@]}"; do
  A=$W/pjobs.cpio
  case $nm in
    sigs) A=$W/sigs.cpio; k=$L/bin/empty.keys; av="/bin/sigwolf" ;;
    sigs-user) A=$W/sigs.cpio; k=$L/bin/empty.keys; av="/bin/as 1000 1000 /bin/sigwolf" ;;
    pjobs-user-*) k=$P/user/console/pjobs/${nm#pjobs-user-}.keys; av="/bin/as 1000 1000 /bin/sh -i -m" ;;
    pjobs-*) k=$P/user/console/pjobs/${nm#pjobs-}.keys; av="/bin/sh -i -m" ;;
    groups) k=$P/user/console/groups.keys; av="/bin/sh -i -m" ;;
    groups-user) k=$P/user/console/groups.keys; av="/bin/as 1000 1000 /bin/sh -i -m" ;;
  esac
  [ -f "$k" ] || { echo "no keys $k"; continue; }
  taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $L/bin/vmjob51 $A "$k" "$av" $O $nm > $O/$nm.vm.out 2>&1 &
  n=$((n + 1))
  if [ $((n % 8)) = 0 ]; then wait; echo "$n boots done"; fi
done
wait
for nm in "${names[@]}"; do printf '%s: %s\n' "$nm" "$(tail -n 1 $O/vm-$nm.meta 2>/dev/null)"; done
