#!/bin/bash
# px65, kasumi: px57's recordings redone at the new pins: real root's
# guest (kasumi's own kernel image under QEMU, notes/px48/linux-vm.sh,
# never read) with the vmjob each recording was made with (px50's for
# pjobs, groups and sigs; px52's for execs, xsh, eds and hostq; built
# static in px13-ubuntu, as they were, so their digests are the metas'),
# from a mpx5-jobs build's own archives, four boots at a time on CPUs
# 12-15. Then each recording compared with the committed one.
#   vm-rec.sh BUILDTAG OUTDIR [NAME...]   (default: every pjobs case as
#   root and as 1000:1000, groups, sigs, execs, xsh, eds, hostq, each
#   with its -user twin)
L=$HOME/lanes/px65
W=$L/build/$1/mpx5-jobs; O=$2; shift 2
P=$L/pax
set -u
mkdir -p "$O" "$L/bin"
podman run --rm --network none -v "$L:$L:Z" localhost/px13-ubuntu bash -c "cc -static -O1 -o $L/bin/vmjob50 $P/notes/px50/vmjob.c && cc -static -O1 -o $L/bin/vmjob52 $P/notes/px52/vmjob.c && sha256sum $L/bin/vmjob50 $L/bin/vmjob52" || exit 1
sha256sum "$W"/pjobs.cpio "$W"/sigs.cpio "$W"/execs.cpio "$W"/eds.cpio
: > "$L/bin/empty.keys"
cases=$(sed -n 's/^PCASES="\(.*\)/\1/p; /^    c_jc/p' "$P/tests/mpx5-jobs" | tr -d '"' | tr -s ' \n' ' ')
names=("$@")
if [ ${#names[@]} = 0 ]; then
    for c in $cases; do names+=("pjobs-$c" "pjobs-user-$c"); done
    names+=(groups groups-user sigs sigs-user execs execs-user xsh xsh-user eds eds-user hostq hostq-user)
fi
E=$L/bin/empty.keys
n=0
for nm in "${names[@]}"; do
    A=$W/pjobs.cpio V=$L/bin/vmjob50
    case $nm in
        sigs) A=$W/sigs.cpio k=$E av="/bin/sigwolf" ;;
        sigs-user) A=$W/sigs.cpio k=$E av="/bin/as 1000 1000 /bin/sigwolf" ;;
        pjobs-user-*) k=$P/user/console/pjobs/${nm#pjobs-user-}.keys av="/bin/as 1000 1000 /bin/sh -i -m" ;;
        pjobs-*) k=$P/user/console/pjobs/${nm#pjobs-}.keys av="/bin/sh -i -m" ;;
        groups) k=$P/user/console/groups.keys av="/bin/sh -i -m" ;;
        groups-user) k=$P/user/console/groups.keys av="/bin/as 1000 1000 /bin/sh -i -m" ;;
        execs) A=$W/execs.cpio V=$L/bin/vmjob52 k=$E av="/bin/execs" ;;
        execs-user) A=$W/execs.cpio V=$L/bin/vmjob52 k=$E av="/bin/as 1000 1000 /bin/execs" ;;
        xsh) A=$W/execs.cpio V=$L/bin/vmjob52 k=$P/user/console/execs.keys av="/bin/sh -i -m" ;;
        xsh-user) A=$W/execs.cpio V=$L/bin/vmjob52 k=$P/user/console/execs.keys av="/bin/as 1000 1000 /bin/sh -i -m" ;;
        eds) A=$W/eds.cpio V=$L/bin/vmjob52 k=$E av="/bin/edwolf" ;;
        eds-user) A=$W/eds.cpio V=$L/bin/vmjob52 k=$E av="/bin/as 1000 1000 /bin/edwolf" ;;
        hostq) A=$W/eds.cpio V=$L/bin/vmjob52 k=$E av="/bin/hostq" ;;
        hostq-user) A=$W/eds.cpio V=$L/bin/vmjob52 k=$E av="/bin/as 1000 1000 /bin/hostq" ;;
        *) echo "unknown recording $nm"; continue ;;
    esac
    [ -f "$k" ] || { echo "no keys $k"; continue; }
    taskset -c 12-15 "$P/notes/px48/linux-vm.sh" "$P" "$V" "$A" "$k" "$av" "$O" "$nm" > "$O/$nm.vm.out" 2>&1 &
    n=$((n + 1))
    if [ $((n % 4)) = 0 ]; then wait; echo "$n boots done $(date -Is)"; fi
done
wait
for nm in "${names[@]}"; do
    for f in "$nm.tty" "$nm.tty.rc"; do
        c=$P/tests/mpx5-jobs.d/linux/$f
        if [ ! -f "$O/$f" ]; then echo "MISSING $f"
        elif [ -f "$c" ]; then cmp -s "$O/$f" "$c" && echo "committed-same $f" || echo "committed-DIFFERS $f"
        else echo "new $f"; fi
    done
done
