#!/bin/bash
# px67, kasumi (notes/px67/play/run.sh): the playground and the measurements that use its programs, one
# job under the cores lock, from a snapshot of the clone taken now:
#   play.sh [build] [assemble] [boot] [timing] [term] [crash]   (default: all)
set -u
L=$HOME/lanes/px67; S=$L/snap/play; out=$L/play.txt
ulimit -c 0
echo $$ > $L/play.pid
steps=${*:-build assemble boot timing term crash}
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
for st in $steps; do
    echo "== $st $(date -Is)" >> $out
    case $st in
        build) notes/px67/play/build.sh >> $out 2>&1 ;;
        assemble) PX67_HEAD=$HEAD PX67_EPOCH=$EPOCH notes/px67/play/assemble.sh >> $out 2>&1 ;;
        boot) EDK2=$L/play/edk2-x86_64-code.fd notes/px67/play/boot.sh bios uefi >> $out 2>&1 ;;
        timing)
            SOURCE_DATE_EPOCH=$EPOCH PAX_CACHE=$L/play/cache TMPDIR=$L/play/tmp taskset -c 0-3 tools/mkdisk --gpt --kernel "$(cat $L/play/w/elf.path)" \
                --initramfs $L/play/w/play.cpio --conf boot/limine-initramfs-quiet.conf --esp 192M --label pax-playground 512M \
                $L/play/out/initramfs-disk.img > $L/play/out/initramfs-disk.mkdisk.txt 2>&1; echo "mkdisk --initramfs rc=$?" >> $out
            notes/px67/timing.sh $L/play/out/initramfs-disk.img $L/play/out/pax-disk.img >> $out 2>&1
            rm -f $L/play/out/initramfs-disk.img ;;
        term)
            T=$L/play/term; rm -rf $T; mkdir -p $T
            podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -e S=$S -e T=$T localhost/px13-ubuntu bash -c 'cd $S && tools/mkrootprobe $T/bin' >> $out 2>&1
            printf 'sleep 100\n' > $T/sleep.sh
            printf '/bin/mounts term 1 /bin/sleep 100\n/bin/mounts term 1 /bin/sh /etc/px67-sleep.sh\n/bin/mounts term 2 /bin/sh -i\n/bin/mounts term 3 /bin/yew /tmp/px67.txt\n' > $T/run
            W=$L/play/w
            tools/mkinitramfs $T/term.cpio /bin/mounts=$T/bin/mounts:755 /bin/sleep=$W/strip/sleep:755 /bin/sh=$W/strip/pelt:755 \
                /bin/yew=$W/strip/yew:755 /etc/px67-sleep.sh=$T/sleep.sh:644 /etc/pax-run=$T/run:644 /tmp/:1777 > $T/cpio.txt 2>&1
            SOURCE_DATE_EPOCH=$EPOCH PAX_CACHE=$L/play/cache TMPDIR=$L/play/tmp tools/mkimage --conf boot/limine-initramfs.conf --add $T/term.cpio initramfs.cpio "$(cat $W/elf.path)" $T/term.iso > $T/mkimage.txt 2>&1
            echo "term iso rc=$?" >> $out
            PAX_CACHE=$L/play/cache PAX_BUILD=$T taskset -c 0-3 tools/qemu-halt --timeout 240 --elf "$(cat $W/elf.path)" --marker '^halt$' --serial $T/serial.log $T/term.iso >> $out 2>&1
            echo "qemu-halt rc=$?" >> $out
            tr -d '\r' < $T/serial.log | grep -a -E '^(~term|term:|PAX: the end)' >> $out ;;
        crash)
            C=$L/play/crash; rm -rf $C; mkdir -p $C
            PAX_BUILD=$C PAX_CACHE=$L/play/cache TMPDIR=$L/play/tmp taskset -c 0-3 python3 tools/root-crash --kernel "$(cat $L/play/w/elf.path)" \
                --probe $L/play/term/bin/mounts --n ${CRASH_N:-24} --seed 67 $C >> $out 2>&1
            echo "root-crash rc=$?" >> $out
            rm -f $C/*.img ;;
    esac
done
uptime >> $out
echo "play done $(date -Is)" >> $out
rm -f $L/play.pid
