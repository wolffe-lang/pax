# px77d s14: the gates of pax#252's two rows on the head rebased onto trunk e6f6acf7 (px78b's #255):
# kernel-as both tiers (18 assembly calls a tier); mpx6-nmi N0/N1/N2 both tiers and firmwares under
# KVM; mpx6-nmi under TCG (CI's accelerator), both tiers, bios.
set -u
L=/home/mfwolffe/lanes/px77d
P=/home/mfwolffe/lanes/hasu-env/bin/podman
HEAD_SHA=$1
step() { echo "=== $(date -u +%FT%TZ) $*"; }
end() { echo "END $1 exit=$2 $(date -u +%FT%TZ)"; }
cd $L/pax && git checkout -q -f "$HEAD_SHA" && git clean -fdq && git rev-parse HEAD || exit 3
git merge-base --is-ancestor e6f6acf7c9c1831a49b3cd500bc7eda9c64802c3 HEAD && echo "trunk e6f6acf7 is an ancestor" || exit 3
mkdir -p $L/tmp $L/logs/s14
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
step "J10 kernel-as at the rebased head $HEAD_SHA, both tiers (expect PASS)"
rm -rf $L/build-kas-r2; r41 $L/pax $L/build-kas-r2 $L/logs/s14/kas-rebased.log "$SEAM time tests/kernel-as --tier both"; end J10 $?
step "J11 mpx6-nmi at the rebased head, both tiers, both firmwares (KVM; expect PASS, 0 skipped)"
rm -rf $L/build-nmi-r2; px75 $L/pax $L/build-nmi-r2 $L/logs/s14/nmi-green.log 1 "time tests/mpx6-nmi --tier release --firmware both && time tests/mpx6-nmi --tier native --firmware both"; end J11 $?
step "J12 mpx6-nmi at the rebased head, both tiers, bios, no /dev/kvm (CI's TCG; expect N0 N2 PASS, N1 skipped)"
rm -rf $L/build-nmi-r2-tcg; px75 $L/pax $L/build-nmi-r2-tcg $L/logs/s14/nmi-tcg.log 0 "time tests/mpx6-nmi --tier release --firmware bios && time tests/mpx6-nmi --tier native --firmware bios"; end J12 $?
step "s14 done"
