#!/usr/bin/env bash
# px68, kasumi only: the journal's first boots. kmain_console built in
# px13-ubuntu, then tools/root-crash on the journalled disk with a few
# kills (and the torn row, and the gate), all on CPUs 0-3 (the caller
# holds the lock), QEMU under TCG.
#   smoke.sh NAME [ROOT-CRASH ARGS...]
set -uo pipefail
L=$HOME/lanes/px68; T=${PAX_TREE:-$L/pax}
name=$1; shift
export PAX_CACHE=$L/cache PAX_ENGINE=podman TMPDIR=$L/tmp
ulimit -c 0
cd "$T"
taskset -c 0-3 tools/fetch-limine > /dev/null || exit 2
bash notes/px68/kbuild.sh kmain_console native "$name" > "$L/logs/$name.kbuild.log" 2>&1 || { tail -5 "$L/logs/$name.kbuild.log"; exit 2; }
echo "kernel: $(sha256sum "$L/kb/$name/kmain_console.elf" | cut -c1-16)"
rm -rf "$L/smoke/$name"; mkdir -p "$L/smoke"
taskset -c 0-3 python3 tools/root-crash --kernel "$L/kb/$name/kmain_console.elf" --probe "$L/guest/probe/mounts" "$@" "$L/smoke/$name"
