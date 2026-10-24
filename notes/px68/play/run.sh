#!/bin/bash
# px68, kasumi: the playground (px67's notes/px67/play/run.sh, its build,
# assemble and boot steps) from a snapshot of the clone taken now, one job
# under the cores lock (the caller holds it).
#   run.sh [build] [assemble] [boot]   (default: all three)
set -u
L=$HOME/lanes/px68; S=$L/snap/play; out=$L/logs/play.txt
ulimit -c 0
steps=${*:-build assemble boot}
: > $out
if [ ! -d "$S" ] || [[ " $steps " == *" build "* ]]; then
    rm -rf $S; mkdir -p $S
    rsync -a --exclude /build $L/pax/ $S/
fi
export P=$S
cd $S
HEAD=$(git rev-parse --short=8 HEAD); EPOCH=$(git log -1 --format=%ct)
echo "snapshot $S at $HEAD (epoch $EPOCH) $(date -Is); steps: $steps" >> $out
uptime >> $out; df -h /home | tail -1 >> $out
mkdir -p $L/play
for st in $steps; do
    echo "== $st $(date -Is)" >> $out
    case $st in
        build) bash notes/px68/play/build.sh >> $out 2>&1 ;;
        assemble) PX68_HEAD=$HEAD PX68_EPOCH=$EPOCH bash notes/px68/play/assemble.sh >> $out 2>&1 ;;
        boot) EDK2=${EDK2:-/usr/share/qemu/edk2-x86_64-code.fd} bash notes/px68/play/boot.sh bios uefi >> $out 2>&1 ;;
    esac
done
uptime >> $out
echo "play done $(date -Is)" >> $out
