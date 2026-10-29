#!/usr/bin/env bash
# Adapt px82's release-pair recipe; copied payloads remain digest-verified.
set -euo pipefail
L=/home/mfwolffe/lanes/px77a
cd "$L/pax"
export PAX_CACHE=$L/cache PAX_BUILD=$L/build TMPDIR=$L/tmp
export PAX_LOPE_REPO=$L/inputs/lope-local CARGO_INCREMENTAL=0
export PAX_WOLF=$(tools/fetch-wolf)
[ "$(git rev-parse --short=8 HEAD)" = f8a3292b ]
[ -z "$(git status --porcelain --untracked-files=no)" ]
printf '%s START release-pair\n' "$(date -u +%FT%TZ)"
tools/mkdistribution "$L/inputs/base-dev.cpio" "$L/build/inputs" "$L/out" > "$L/logs/distribution-smoke.log" 2>&1
printf '%s END release-pair\n' "$(date -u +%FT%TZ)"
python3 -I "$L/live-payload.py" "$L/pax" "$L/out"
sha256sum "$L/cache/wolf-0.2.35.tar.gz" 2>/dev/null || find "$L/cache" -maxdepth 2 -type f -name '*.tar*' -exec sha256sum {} +
nm "$L/out/kernel/kmain_console.elf" > "$L/out/kernel.symbols"
command -v gdb || true
ls /usr/share/OVMF/
