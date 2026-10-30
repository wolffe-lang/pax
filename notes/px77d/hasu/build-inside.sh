#!/usr/bin/env bash
# px77d: px77b's build-inside.sh (px77a's, px82's release-pair recipe), at the px77d head; copied payloads remain digest-verified.
set -euo pipefail
L=/home/mfwolffe/lanes/px77d
cd "$L/pax"
export PAX_CACHE=$L/cache PAX_BUILD=$L/build TMPDIR=$L/tmp
export PAX_LOPE_REPO=$L/inputs/lope-local CARGO_INCREMENTAL=0
export PAX_WOLF=$(tools/fetch-wolf)
[ "$(git rev-parse HEAD)" = fedb6f5f4353619008970e21a11124300bf46552 ]
[ -z "$(git status --porcelain --untracked-files=no)" ]
printf '%s START release-pair\n' "$(date -u +%FT%TZ)"
tools/mkdistribution "$L/inputs/base-dev.cpio" "$L/build/inputs" "$L/out" > "$L/logs/distribution.log" 2>&1
printf '%s END release-pair\n' "$(date -u +%FT%TZ)"
python3 -I "$L/live-payload.py" "$L/pax" "$L/out"
for n in 1 2; do sha256sum "$L/cache/wolf-0.2.35-4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a.tar.gz"; done | tee "$L/archive-reads.txt"
for n in 1 2; do sha256sum "$L/inputs/limine-download/limine-binary.tar.gz" | tee "$L/limine-read-$n.sha256"; done
nm "$L/out/kernel/kmain_console.elf" > "$L/out/kernel.symbols"
qemu-system-x86_64 --version | head -1
ls /usr/share/OVMF/
