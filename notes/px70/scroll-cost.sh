#!/usr/bin/env bash
# Called while the final validation owns the CPUs12-15 lock.
set -euo pipefail
L=$HOME/lanes/px70
export PAX_CACHE="$L/cache" TMPDIR="$L/tmp"
mkdir -p "$L/build/timing" "$L/out/timing"
if [ "${1:-}" != --summarize ]; then
for kind in trunk packed final; do
    if [ "$kind" = final ]; then tree="$L/pax"; else tree="$L/timing-$kind"; fi
    podman run --rm --name "px70-timing-$kind" --cpuset-cpus 12-15 --ulimit core=0:0 \
        -v "$L:$L:Z" -e L="$L" -e TREE="$tree" -e KIND="$kind" -e PAX_CACHE -e TMPDIR \
        localhost/px13-ubuntu bash -c '
        set -euo pipefail; cd "$TREE"; git rev-parse HEAD
        export PAX_WOLF=$(tools/fetch-wolf)
        out="$L/build/timing/$KIND"; mkdir -p "$out"
        elf=$(tools/build-kernel --src kernel/kmain_screen.lu "$out")
        tools/mkimage "$elf" "$out/screen.iso"
        sha256sum "$elf" "$out/screen.iso"
        nm -S "$elf" | grep pax_screen_cells
        readelf -lW "$elf"'
done
for repeat in 1 2 3; do
    case $repeat in 1) order='trunk packed final';; 2) order='packed final trunk';; 3) order='final trunk packed';; esac
    for kind in $order; do
        echo "$(date -Is) timing $repeat $kind load=$(cut -d' ' -f1-3 /proc/loadavg)"
        out="$L/build/timing/$kind"
        taskset -c 12-15 "$L/pax/tools/qemu-halt" --accel tcg --firmware bios \
            --serial "$L/out/timing/$kind-$repeat.serial.log" --timeout 120 \
            --elf "$out/kmain_screen.elf" --marker halt "$out/screen.iso"
        grep -a '^scroll:' "$L/out/timing/$kind-$repeat.serial.log"
    done
done
fi
python3 - "$L" <<'PY'
from pathlib import Path
import re,sys,statistics
L=Path(sys.argv[1]); values={}
for kind in ('trunk','packed','final'):
    values[kind]=[]
    for run in (1,2,3):
        text=(L/f'out/timing/{kind}-{run}.serial.log').read_text(encoding="latin-1")
        assert 'PANIC' not in text
        a,b,n=map(int,re.search(r'scroll: 400 lines in (\d+) ticks without scrolling, 400 in (\d+) with (\d+) scrolls',text).groups())
        assert 0<n<=400 and b>=a
        values[kind].append((b-a)*10/n)
lines=[f'{kind}: '+', '.join(f'{x:.6f} ms' for x in v)+f'; mean={statistics.mean(v):.6f} ms' for kind,v in values.items()]
ratios=[f/t for f,t in zip(values['final'],values['trunk'])]
lines.append('paired final/trunk ratios: '+', '.join(f'{r:.6f}' for r in ratios))
lines.append(f'all below 1.2: {all(r<1.2 for r in ratios)}; mean ratio={statistics.mean(values["final"])/statistics.mean(values["trunk"]):.6f}')
(L/'out/scroll-cost.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
