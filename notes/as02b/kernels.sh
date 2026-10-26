#!/usr/bin/env bash
# as02b, item 3's control at px80's head: the image's compiler (wolf 0.2.35)
# through as01's lane-local driver shims (clef notes/as01/seam/gas-driver and
# clef-driver at 996a3ccd: they stand in for WOLF_CLANG and cc and route only
# assembly), against which the explicit seam's kernels (tests/kernel-as K1, K4,
# K5, the seam wolf 9f2cff44) are held. Controls, never a default (the
# contract's item 3). Runs in clef's integration image on kasumi CPUs 0-3:
#   L=~/lanes/as02b notes/as02b/kernels.sh PKG-DIR KAS-BUILD OUT
# PKG-DIR the clef package (tools/mkclef), KAS-BUILD a tests/kernel-as run's
# PAX_BUILD, OUT where the three builds per tier and kernels.json go.
set -uo pipefail
pkg=$1 kas=$2/kernel-as out=$3
cd "$L/pax" || exit 2
W35=$L/cache/wolf-0.2.35/wolf-0.2.35-x86_64-unknown-linux-gnu/wolf
seam=$L/clef/notes/as01/seam
mkdir -p "$out/bin-gas" "$out/bin-clef"
for d in cc clang; do ln -sf "$seam/gas-driver" "$out/bin-gas/$d"; done
# as01's clef-driver names as01's own clef path; the copy names the package.
sed "s#/lane/clef/target/clef#$pkg/clef#" "$seam/clef-driver" > "$out/clef-driver"
chmod +x "$out/clef-driver"
for d in cc clang; do ln -sf "$out/clef-driver" "$out/bin-clef/$d"; done
for tier in native release; do
    flag=(); [ "$tier" = release ] && flag=(--release)
    for row in stock35 gas35 clef35; do
        d=$out/$tier/$row
        rm -rf "${d:?}" "${L:?}/pax/kernel/.lu-cache"
        mkdir -p "$d"
        export AS01_TRACE_LOG=$d/trace.tsv AS01_SEAM_LOG=$d/seam.tsv
        : > "$AS01_TRACE_LOG"; : > "$AS01_SEAM_LOG"
        case $row in
            stock35) env -u WOLF_AS -u WOLF_CLANG PAX_WOLF="$W35" tools/build-kernel "${flag[@]}" --src kernel/kmain_console.lu "$d/out" > "$d/elf.path" 2> "$d/build.log" ;;
            gas35) env -u WOLF_AS PATH="$out/bin-gas:$PATH" WOLF_CLANG="$out/bin-gas/clang" PAX_WOLF="$W35" tools/build-kernel "${flag[@]}" --src kernel/kmain_console.lu "$d/out" > "$d/elf.path" 2> "$d/build.log" ;;
            clef35) env -u WOLF_AS PATH="$out/bin-clef:$PATH" WOLF_CLANG="$out/bin-clef/clang" PAX_WOLF="$W35" tools/build-kernel "${flag[@]}" --src kernel/kmain_console.lu "$d/out" > "$d/elf.path" 2> "$d/build.log" ;;
        esac
        echo "$tier $row rc=$? $(sha256sum "$d/out/kmain_console.elf" 2>/dev/null | cut -c1-64) assembly=$(grep -c '^assembly' "$AS01_SEAM_LOG")"
    done
done
python3 -I - "$out" "$kas" <<'PY'
import hashlib, json, pathlib, sys
out = pathlib.Path(sys.argv[1]); kas = pathlib.Path(sys.argv[2])
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def first(a, b):
    x, y = a.read_bytes(), b.read_bytes()
    return next((i for i, (p, q) in enumerate(zip(x, y)) if p != q), None if len(x) == len(y) else min(len(x), len(y)))
def nonasm(d):
    return {p.name: h(p) for p in sorted(d.glob('kmain_console.*')) if p.suffix in ('.o', '.a') and '.asm-' not in p.name}
rows = []
for tier in ('native', 'release'):
    k = {r: out / tier / r / 'out' for r in ('stock35', 'gas35', 'clef35')}
    k.update({'seam-stock': kas / tier / 'K1' / 'out', 'seam-gas': kas / tier / 'K4' / 'out', 'seam-clef': kas / tier / 'K5' / 'out'})
    elf = {r: d / 'kmain_console.elf' for r, d in k.items()}
    row = {'tier': tier, 'kernels': {r: {'sha256': h(e), 'bytes': e.stat().st_size} for r, e in elf.items() if e.exists()}}
    row['clef35 == gas35'] = elf['clef35'].read_bytes() == elf['gas35'].read_bytes()
    row['seam-clef == seam-gas'] = elf['seam-clef'].read_bytes() == elf['seam-gas'].read_bytes()
    row['seam-gas == gas35'] = elf['seam-gas'].read_bytes() == elf['gas35'].read_bytes()
    row['seam-stock == stock35'] = elf['seam-stock'].read_bytes() == elf['stock35'].read_bytes()
    row['stock35 vs gas35 first differing byte'] = first(elf['stock35'], elf['gas35'])
    row['seam-stock vs seam-gas first differing byte'] = first(elf['seam-stock'], elf['seam-gas'])
    a, b = nonasm(k['gas35']), nonasm(k['seam-gas'])
    row['non-assembly inputs, 0.2.35 against the seam wolf'] = {'count': len(a), 'identical': sorted(n for n in a if a[n] == b.get(n)), 'differ': sorted(n for n in a if a[n] != b.get(n))}
    c = nonasm(k['clef35'])
    row['non-assembly inputs, clef35 against gas35 identical'] = a == c
    rows.append(row)
(out / 'kernels.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(rows, indent=2))
PY
