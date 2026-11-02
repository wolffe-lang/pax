#!/usr/bin/env bash
# px88: tests/mpx6-install's unattended install row (`install.py … no vdb`,
# TCG, as CI's smoke rows run it) at one commit, for I-peak (pax#248), inside
# a chain that holds the block. The installer's other inputs (the disk tools,
# pelt, lope, the probes, the games) are px86's gauntlet's, copied, never
# moved (/home/mfwolffe/lanes/px86/w-gaunt/install/inputs: built at px86's
# head, and nothing of them changes in px88); the installer itself and the
# kernel are rebuilt at SHA into the copy (tools/mkinstall, tools/build-kernel
# kmain_console, native), the kernel's path written where install.py reads it.
#
#   inst.sh BLOCK RUN SHA
set -uo pipefail
B=$1 RUN=$2 SHA=$3
L=/home/mfwolffe/lanes/px88
S=$L/scripts
export PATH=/home/mfwolffe/lanes/hasu-env/bin:$PATH
# The lane's clone is shared by its chains (one a block): its git steps
# take a lane-local lock (never a block's).
G="flock /home/mfwolffe/lanes/px88/git.lock git"
[ -d "$L/pax/.git" ] || $G clone -q https://github.com/wolffe-lang/pax.git "$L/pax"
$G -C "$L/pax" fetch -q origin '+refs/heads/px88*:refs/remotes/origin/px88*' || { echo "END fetch exit=1"; exit 1; }
WT=$L/wt-${SHA:0:8}
[ -d "$WT" ] || $G -C "$L/pax" worktree add -q --detach "$WT" "$SHA" || { echo "END worktree exit=1"; exit 1; }
[ "$(git -C "$WT" rev-parse HEAD)" = "$(git -C "$L/pax" rev-parse "$SHA^{commit}")" ] || { echo "END worktree exit=1 (not at $SHA)"; exit 1; }
R=$L/build/$RUN
I=$R/inputs
rm -rf "$R"; mkdir -p "$R" "$L/tmp"
cp -a /home/mfwolffe/lanes/px86/w-gaunt/install/inputs "$I" || { echo "END $RUN-inputs exit=1"; exit 1; }
echo "inputs copied: $(du -sh "$I" | cut -f1); px86's installer $(sha256sum "$I/build/install-gate/bin/pax-install" | cut -c1-16)"
CTR_WD=$WT bash "$S/ctr.sh" "$B" "$RUN-build" localhost/px75-ubuntu:2 -- env PAX_BUILD="$R/pbuild" bash -c '
    set -eu; export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); "$PAX_WOLF" --version | head -n 1
    tools/mkinstall "$1/build/install-gate/bin"
    sha256sum "$1/build/install-gate/bin/pax-install"
    rm -rf "$1/build/disktools/native"; mkdir -p "$1/build/disktools/native"
    elf=$(tools/build-kernel --src kernel/kmain_console.lu "$1/build/disktools/native")
    echo "$elf" > "$1/build/disktools/native.elf.path"
    echo "kernel $elf $(sha256sum "$elf" | cut -c1-16)"' x "$I" > "$R/build.log" 2>&1
brc=$?
tail -n 4 "$R/build.log"
echo "END $RUN-build exit=$brc"
[ "$brc" = 0 ] || exit "$brc"
CTR_WD=$WT bash "$S/ctr.sh" "$B" "$RUN-install" localhost/px75-ubuntu:2 -- env PAX_BUILD="$R/pbuild" SOURCE_DATE_EPOCH=1700000000 PAX_INSTALL_TIER=native bash -c '
    set -u; export PAX_WOLF=$(tools/fetch-wolf | tail -n 1)
    python3 -I tests/mpx6-install.d/install.py "$PWD" "$1" "$2/install-no-vdb" no vdb' x "$I" "$R" > "$R/install.log" 2>&1
irc=$?
grep -E '^(PASS|FAIL)|I-peak|AssertionError' "$R/install.log" | cut -c1-400
grep -aE 'peak RSS' "$R/install-no-vdb/install.serial" | tr -d '\r' | head -n 4
echo "END $RUN-install exit=$irc"
exit "$irc"
