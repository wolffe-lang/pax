#!/bin/bash
# px38, on kasumi: build the probes and take every Linux run again.
#   run-all.sh LANE      (LANE: ~/lanes/px38, holding pax/ and out/)
set -uo pipefail
L=$1
mkdir -p "$L/bin" "$L/out"
podman run --rm --network none -v "$L/pax/notes/px38/probes:/src:ro" -v "$L/bin:/out" localhost/px13-ubuntu bash /src/build.sh /src /out > "$L/out/build.txt" 2>&1 || { tail "$L/out/build.txt"; exit 2; }
bash "$L/pax/notes/px38/vm-run.sh" "$L/pax" "$L/bin" "$L/out/vm.log" || exit 1
bash "$L/pax/notes/px38/vm-run.sh" "$L/pax" "$L/bin" "$L/out/vm-protected.log" ids,cred,perm,setid,sig,priv px38prot=1 || exit 1
bash "$L/pax/notes/px38/ct-run.sh" "$L/bin" "$L/out/ct" || exit 1
grep -c . "$L/out/vm.log.txt" "$L/out/vm-protected.log.txt" "$L/out/ct/ct.txt"
if grep -n '^!\|\*\*\*' "$L/out/vm.log.txt" "$L/out/vm-protected.log.txt" "$L/out/ct/ct.txt"; then echo "run-all: a probe complained"; exit 1; fi
echo "run-all: ok"
