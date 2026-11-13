#!/usr/bin/env bash
# The screen's warmed minimum-of-five at its first attach, held through a
# real console boot. Test-only words replace costs, not framebuffer I/O:
# one slow read and five slow reads, plus the two existing forced ways.
# Called by mpx6-triage with its already-built console kernel; standalone
# builds that same kernel. --case outlier is the single-sample plant's row.
set -euo pipefail
. "$(dirname "$0")/../../tools/lib.sh"
tier=native firmware=both elf= only=all
while [ $# -gt 0 ]; do
    case $1 in
        --tier) tier=$2; shift 2;;
        --firmware) firmware=$2; shift 2;;
        --elf) elf=$2; shift 2;;
        --case) only=$2; shift 2;;
        *) die 'usage: mpx3-screen-probe [--tier native|release] [--firmware bios|uefi|both] [--elf ELF] [--case all|outlier]';;
    esac
done
case $tier in native|release) ;; *) die 'bad tier';; esac
case $firmware in both) legs='bios uefi';; bios|uefi) legs=$firmware;; *) die 'bad firmware';; esac
case $only in all) cases='plain outlier slow fbread fbwrite none';; outlier) cases=outlier;; *) die 'bad case';; esac
work=$PAX_BUILD/mpx3-screen-probe/$tier
mkdir -p "$work"
"$PAX_ROOT/tools/fetch-limine"
flags=(); [ "$tier" != release ] || flags=(--release)
if [ -z "$elf" ]; then
    elf=$("$PAX_ROOT/tools/build-kernel" ${flags[@]+"${flags[@]}"} --src "$PAX_ROOT/kernel/kmain_console.lu" "$work")
fi
printf '# no command: report boot and halt\n' > "$work/pax-run"
"$PAX_ROOT/tools/mkinitramfs" "$work/probe.cpio" "/etc/pax-run=$work/pax-run" > "$work/initramfs.txt"
fail=0
for fw in $legs; do
    for c in $cases; do
        words=pax.nobeep
        extra=()
        case $c in
            outlier) words+=' pax.fbprobe=outlier';;
            slow) words+=' pax.fbprobe=slow';;
            fbread|fbwrite) words+=" pax.fbprobe=slow $c";;
            none) extra=(--no-screen);;
        esac
        conf=$work/$c.conf
        cp "$PAX_ROOT/boot/limine-initramfs.conf" "$conf"
        printf '    resolution: 1280x800\n    cmdline: %s\n' "$words" >> "$conf"
        iso=$work/$c.iso
        "$PAX_ROOT/tools/mkimage" --conf "$conf" --add "$work/probe.cpio" initramfs.cpio "$elf" "$iso" > /dev/null
        log=$work/$fw-$c.serial.log
        rc=0
        "$PAX_ROOT/tools/qemu-halt" --firmware "$fw" --serial "$log" --timeout 150 \
            --elf "$elf" --marker halt ${extra[@]+"${extra[@]}"} "$iso" > "$log.verdict" 2>&1 || rc=$?
        if [ "$rc" != 0 ]; then
            printf 'FAIL P-%s %s %s: boot did not halt (exit %s)\n' "$c" "$tier" "$fw" "$rc"
            fail=1
            continue
        fi
        python3 -I "$PAX_ROOT/tests/mpx6-triage.d/probe-check.py" "$c" "$log" "$tier" "$fw" || fail=1
    done
done
exit "$fail"
