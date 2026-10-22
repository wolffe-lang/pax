#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/probe-retake.pid"
ulimit -c 0
uptime
B=$L/build/mpx5-pelt-probes
W=$B/mpx5-pelt
old=$L/build/mpx5-pelt-r2/mpx5-pelt
mkdir -p "$W/root" "$W/native" "$W/keys"
cp -a --reflink=auto "$old/root/." "$W/root/"
cp --reflink=auto "$old/native/kmain_console.elf" "$W/native/"
cp "$old/owners" "$W/owners"
cp "$old/keys/probes-root.keys" "$old/keys/probes-pax.keys" "$W/keys/"
printf 'probes-root\nprobes-pax\n' > "$W/run-names"
export PAX_CACHE=$L/cache PAX_BUILD=$B TMPDIR=$L/tmp PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
podman run --rm --cpuset-cpus 8-11 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" -e PAX_CACHE -e TMPDIR localhost/px13-ubuntu bash -c '
set -euo pipefail
cd "$L/pax"
tools/mkpspgid "$L/bin/pspgid-1"
tools/mkpspgid "$L/bin/pspgid-2"
cmp "$L/bin/pspgid-1/sums.txt" "$L/bin/pspgid-2/sums.txt"
python3 -I - "$L/bin/pspgid-1/ps" <<"PY"
import os, subprocess, sys
p=sys.argv[1]
r=subprocess.run([p,"-o","pgid=","-p",str(os.getpid())],capture_output=True,text=True)
assert r.returncode==0 and int(r.stdout)==os.getpgid(0)
for args in ([],["-o","bad","-p","1"],["-o","pgid=","-p","-1"],["-o","pgid=","-p","nope"]):
    r=subprocess.run([p,*args],capture_output=True,text=True)
    assert r.returncode==2 and r.stderr.startswith("ps-pgid:")
r=subprocess.run([p,"-o","pgid=","-p","2147483647"],capture_output=True,text=True)
assert r.returncode==1 and r.stderr.startswith("ps-pgid: getpgid")
print("ps-pgid: PASS real group, wrong options, invalid PID, missing PID; two identical builds")
PY
'
cp "$L/bin/pspgid-1/ps" "$W/root/bin/ps"
# The guest recorder uses this archive unchanged; /etc/pax-run is its
# original run list because vmjob supplies its own argv.
args=(/tmp/:1777 /home/pax/:755:1000:1000)
while IFS= read -r -d '' f; do
    mode=644; case "$f" in "$W/root/bin/"*) mode=755 ;; esac
    args+=("${f#"$W/root"}=$f:$mode")
done < <(find "$W/root" -type f -print0)
"$L/pax/tools/mkinitramfs" "$W/pelt.cpio" "${args[@]}" > "$W/initramfs.txt"
cd "$L/pax"
PAX_PELT_CASES=probes taskset -c 8-11 tests/mpx5-pelt --only linux --images "$W" > "$B.linux.log" 2>&1
while ! awk '{exit !($1 < 16)}' /proc/loadavg; do echo 'WAIT corrected probes: load below 16'; uptime; sleep 60; done
uptime
taskset -c 8-11 tests/mpx5-pelt --images "$W" --tier native --firmware bios > "$B.boot.log" 2>&1
uptime
echo 'corrected probes: PASS'
