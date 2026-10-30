#!/usr/bin/env bash
# px78b: px77b's build-inside.sh (px77c's, px82's release-pair recipe) at the stick head $HEAD:
# px78b's branch merged with pax#252's head 23d25bfa (px77d's early IDT); copied payloads remain digest-verified.
set -euo pipefail
L=/home/mfwolffe/lanes/px78b
cd "$L/stick"
export PAX_CACHE=$L/cache PAX_BUILD=$L/sb TMPDIR=$L/tmp
export PAX_LOPE_REPO=$L/inputs/lope-local CARGO_INCREMENTAL=0
export PAX_WOLF=$(tools/fetch-wolf)
[ "$(git rev-parse HEAD)" = 197330ad4042dd349ad698a5e60f3c66f65c9c2c ]
[ -z "$(git status --porcelain --untracked-files=no)" ]
printf '%s START release-pair\n' "$(date -u +%FT%TZ)"
tools/mkdistribution "$L/inputs/base-dev.cpio" "$L/sb/inputs" "$L/sout" > "$L/slogs/distribution.log" 2>&1
printf '%s END release-pair\n' "$(date -u +%FT%TZ)"
python3 -I "$L/live-payload.py" "$L/stick" "$L/sout"
for n in 1 2; do sha256sum "$L/cache/wolf-0.2.35-4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a.tar.gz"; done | tee "$L/archive-reads.txt"
for n in 1 2; do sha256sum "$L/inputs/limine-download/limine-binary.tar.gz" | tee "$L/limine-read-$n.sha256"; done
nm "$L/sout/kernel/kmain_console.elf" > "$L/sout/kernel.symbols"
qemu-system-x86_64 --version | head -1
