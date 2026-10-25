#!/usr/bin/env bash
# px80 item 2: the linker control on PAX's kernel. kasumi, CPUs 0-3 (run under
# the block's lock), in px65's container (notes/px65/Containerfile built as
# localhost/px80-ubuntu: Ubuntu 24.04 by digest, its lld 18.1.3). For each
# tier, tools/build-kernel builds kmain_console's objects ONCE (and links them
# with the container's lld, row c-bk); every input is hashed; then the same
# inputs are linked in build-kernel's argv order by
#   a  the dev ISO's static lld 17.0.6 (user/wolf-link.sums before px80)
#   b  the new static lld 18.1.8 (notes/px80/build-lld.sh)
#   c  the container's Ubuntu lld 18.1.3
#   a-norelax  lld 17.0.6 with --no-relax (as01's control; never the fix)
# and the ELFs compared (notes/px80/elfcmp.py). Output: $L/control/.
set -euo pipefail
ulimit -c 0
L=$HOME/lanes/px80
O=$L/control
rm -rf "$O"; mkdir -p "$O" "$L/cache" "$L/tmp"
taskset -c 0-3 podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" -e O="$O" \
    localhost/px80-ubuntu bash -c '
set -euo pipefail
cd "$L/pax"; git config --global --add safe.directory "*"
echo "tree $(git rev-parse HEAD)"
export PAX_CACHE=$L/cache TMPDIR=$L/tmp
export PAX_WOLF=$(tools/fetch-wolf | tail -n 1)
echo "wolf $PAX_WOLF: $($PAX_WOLF --version | head -n 1)"
declare -A BIN=([a]=$L/link-old/ld.lld [b]=$L/lld-out/ld.lld [c]=/usr/bin/ld.lld [a-norelax]=$L/link-old/ld.lld)
for r in a b c; do printf "%s %s: %s\n" "$r" "${BIN[$r]}" "$(${BIN[$r]} --version)"; done
for tier in release native; do
    D=$O/$tier; mkdir -p "$D"
    flag=(); [ "$tier" = release ] && flag=(--release)
    t0=$(date +%s)
    elf=$(tools/build-kernel "${flag[@]}" --src kernel/kmain_console.lu "$D" 2>"$D/build-kernel.log")
    echo "$tier: build-kernel $(( $(date +%s) - t0 ))s -> $elf"
    mv "$elf" "$D/c-bk.elf"
    asm=() wobj=() rt=()
    for f in "$D"/kmain_console.asm-*.o; do asm+=("$f"); done
    if [ -f "$D/kmain_console.o" ]; then wobj=("$D/kmain_console.o"); else
        for f in "$D"/kmain_console.*.o; do case $f in "$D"/kmain_console.asm-*.o) ;; *) wobj+=("$f") ;; esac; done
    fi
    [ -f "$D/kmain_console.rt-none.a" ] && rt=("$D/kmain_console.rt-none.a")
    inputs=("$D/start.o" "${asm[@]}" "${wobj[@]}" "${rt[@]}")
    sha256sum "${inputs[@]}" boot/kernel.ld > "$D/inputs.sha256"
    sha256sum "${inputs[@]}" boot/kernel.ld | cmp -s - "$D/inputs.sha256" && echo "$tier: ${#inputs[@]} inputs hashed twice, the same"
    for r in a b c a-norelax; do
        extra=(); [ "$r" = a-norelax ] && extra=(--no-relax)
        argv=("${BIN[$r]}" -nostdlib -static -z max-page-size=0x1000 "${extra[@]}" -T "$L/pax/boot/kernel.ld" -o "$D/$r.elf" "${inputs[@]}")
        printf "%s\n" "${argv[@]}" > "$D/$r.argv"
        rc=0; "${argv[@]}" > "$D/$r.stdout" 2> "$D/$r.stderr" || rc=$?
        echo "$rc" > "$D/$r.status"
        s=-; [ "$rc" = 0 ] && s="$(sha256sum "$D/$r.elf" | cut -d" " -f1) $(wc -c < "$D/$r.elf")"
        printf "%s %-9s status %s %s\n" "$tier" "$r" "$rc" "$s"
        [ -s "$D/$r.stderr" ] && sed "s/^/    /" "$D/$r.stderr"
    done
    for p in "b c" "c c-bk" "a b" "a-norelax b"; do
        set -- $p
        [ -f "$D/$1.elf" ] && [ -f "$D/$2.elf" ] || { echo "$tier: $1 vs $2: one side did not link"; continue; }
        python3 -I "$L/pax/notes/px80/elfcmp.py" "$D/$1.elf" "$D/$2.elf" > "$D/cmp-$1-$2.txt"
        echo "$tier: $1 vs $2: $(tail -n 1 "$D/cmp-$1-$2.txt")"
    done
done
'
echo "control.sh done $(date -Is)"
