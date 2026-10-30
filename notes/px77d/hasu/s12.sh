# px77d s12: pax#252's two red rows (run 41014032632), red at 23d25bfa, green at the new head.
#   kernel-as (r41-toolchain: clang, lld, GNU as, Rust 1.97.1 for the seam wolf), both tiers;
#   a K8 plant (the head's test with K8 expecting the old 17): red, naming the count;
#   mpx6-nmi release (px75-ubuntu, KVM) red at 23d25bfa (pci.scan inlined), green at the head
#   on both tiers and firmwares, and without /dev/kvm (CI's TCG); the old tree at pci.scan_bus.
set -u
L=/home/mfwolffe/lanes/px77d
P=/home/mfwolffe/lanes/hasu-env/bin/podman
RED=23d25bfa59dae1693cbc708f7195425ab196f46e
HEAD_SHA=$1
step() { echo "=== $(date -u +%FT%TZ) $*"; }
end() { echo "END $1 exit=$2 $(date -u +%FT%TZ)"; }
cd $L/pax && git fetch -q origin px77d && git checkout -q -f "$HEAD_SHA" && git clean -fdq && git rev-parse HEAD || exit 3
rm -rf $L/tree-red && git clone -q $L/pax $L/tree-red && git -C $L/tree-red checkout -q -f "$RED" && git -C $L/tree-red rev-parse HEAD || exit 3
rm -rf $L/tree-k8 && git clone -q $L/pax $L/tree-k8 && git -C $L/tree-k8 checkout -q -f "$HEAD_SHA" || exit 3
sed -i 's/\[ "\$c" = 0 \] && \[ "\$s" = 18 \]; then/[ "$c" = 0 ] \&\& [ "$s" = 17 ]; then/' $L/tree-k8/tests/kernel-as
grep -n '"\$s" = 17 \]; then' $L/tree-k8/tests/kernel-as || { echo "plant did not apply"; exit 3; }
cp $L/pax/tests/mpx6-nmi.d/inject.py $L/old-tree/tests/mpx6-nmi.d/inject.py
mkdir -p $L/tmp $L/logs/s12
r41() { # tree build log cmd
  $P run --rm --name px77d-kas --memory 12g --pids-limit 16384 --ulimit core=0:0 \
   -v "$L:$L" -w "$1" -e PAX_CACHE=$L/cache -e PAX_BUILD=$2 -e TMPDIR=$L/tmp -e CARGO_INCREMENTAL=0 \
   -e PATH=/opt/s263-rust/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
   -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
   localhost/r41-toolchain:1 /usr/bin/taskset.real -c 0-5 bash -c "$4" > "$3" 2>&1
}
px75() { # tree build log kvm(1/0) cmd
  dev=(); [ "$4" = 1 ] && dev=(--device /dev/kvm)
  $P run --rm --name px77d-nmi --memory 12g --pids-limit 16384 --ulimit core=0:0 "${dev[@]}" \
   -v "$L:$L" -w "$1" -e PAX_CACHE=$L/cache -e PAX_BUILD=$2 -e TMPDIR=$L/tmp \
   -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
   localhost/px75-ubuntu:2 taskset -c 0-5 bash -c "export PAX_WOLF=\$(tools/fetch-wolf) && $5" > "$3" 2>&1
}
SEAM='export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && export PAX_SEAM_WOLF=$(PAX_WOLF_PIN=tests/kernel-as.d/wolf.pin tools/fetch-wolf | tail -n 1) && "$PAX_SEAM_WOLF" --version &&'
step "J1 kernel-as at the red head $RED (expect FAIL K1 K4 K5 K8)"
rm -rf $L/build-kas-red; r41 $L/tree-red $L/build-kas-red $L/logs/s12/kas-red.log "$SEAM time tests/kernel-as --tier both"; end J1 $?
step "J2 kernel-as at the head $HEAD_SHA (expect PASS)"
rm -rf $L/build-kas-green; r41 $L/pax $L/build-kas-green $L/logs/s12/kas-green.log "$SEAM time tests/kernel-as --tier both"; end J2 $?
step "J3 kernel-as K8 plant (the head's test expecting 17) native (expect FAIL K8 naming 18 (17))"
rm -rf $L/build-kas-k8; r41 $L/tree-k8 $L/build-kas-k8 $L/logs/s12/kas-plant-k8.log "$SEAM time tests/kernel-as --tier native"; end J3 $?
step "J4 mpx6-nmi release bios at the red head (KVM; expect FAIL no single symbol for pci.scan)"
rm -rf $L/build-nmi-red; px75 $L/tree-red $L/build-nmi-red $L/logs/s12/nmi-red-release.log 1 "time tests/mpx6-nmi --tier release --firmware bios"; end J4 $?
step "J5 mpx6-nmi at the head, both tiers, both firmwares (KVM; expect PASS, 0 skipped)"
rm -rf $L/build-nmi-green; px75 $L/pax $L/build-nmi-green $L/logs/s12/nmi-green.log 1 "time tests/mpx6-nmi --tier release --firmware both && time tests/mpx6-nmi --tier native --firmware both"; end J5 $?
step "J6 mpx6-nmi at the head, release bios, no /dev/kvm (CI's TCG; expect N0 N2 PASS, N1 skipped)"
rm -rf $L/build-nmi-tcg; px75 $L/pax $L/build-nmi-tcg $L/logs/s12/nmi-tcg-release.log 0 "time tests/mpx6-nmi --tier release --firmware bios"; end J6 $?
step "J7 the old tree (1ced6284) at pci.scan_bus, both tiers, uefi (KVM; outcomes recorded: expect nmi PANIC, mce reset)"
rm -rf $L/build-nmi-old2; px75 $L/old-tree $L/build-nmi-old2 $L/logs/s12/nmi-old-scan-bus.log 1 'set -e; . tools/lib.sh; tools/fetch-limine; for t in native release; do w=$PAX_BUILD/$t; mkdir -p $w; fl=; [ $t = release ] && fl=--release; elf=$(tools/build-kernel $fl --src kernel/kmain_console.lu $w); printf "# none\n" > $w/pax-run; tools/mkinitramfs $w/nmi.cpio /etc/pax-run=$w/pax-run >/dev/null; tools/mkimage --conf boot/limine-initramfs.conf --add $w/nmi.cpio initramfs.cpio $elf $w/nmi.iso >/dev/null; for k in nmi:pci.scan_bus mce:pci.scan_bus; do echo "old $t ${k%%:*} at ${k#*:}:"; python3 -I tests/mpx6-nmi.d/inject.py --image $w/nmi.iso --elf $elf --output $w/uefi/${k%%:*}-${k#*:} --firmware uefi --kind ${k%%:*} --at ${k#*:} --expect survive || true; cat $w/uefi/${k%%:*}-${k#*:}/outcome.json 2>/dev/null; done; done'; end J7 $?
step "s12 done"
