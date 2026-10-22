#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/cost-and-std.pid"
ulimit -c 0
uptime
mkdir -p "$L/base" "$L/cost"
tar -xf "$L/base.tar" -C "$L/base"
podman run --rm --cpuset-cpus 8-11 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
set -euo pipefail
for side in base pax; do
  cd "$L/$side"
  export PAX_WOLF=$(tools/fetch-wolf | tail -1)
  for kernel in kmain_console kmain_session; do
    for tier in native release; do
      args=(); [ "$tier" != release ] || args=(--release)
      out=$L/cost/$side-$kernel-$tier
      elf=$(tools/build-kernel "${args[@]}" --src "kernel/$kernel.lu" "$out" 2>"$L/cost/$side-$kernel-$tier.log")
      echo "COST $side $kernel $tier $(sha256sum "$elf")"
      size -A "$elf" | grep -E "^\.(text|rodata|data|bss) "
    done
  done
done
cd "$L/pax"
tools/fetch-std "$L/std-1"
tools/fetch-std "$L/std-2"
cmp "$L/std-1/std.sha256" "$L/std-2/std.sha256"
sha256sum "$L/std-1/std.sha256" "$L/std-2/std.sha256"
'
echo 'cost-and-std PASS'
