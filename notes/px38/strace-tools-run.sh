#!/bin/bash
# px38, on kasumi: the strace container (no network; a tmpfs /t; the
# output under OUTDIR). --cap-add SYS_PTRACE for strace; the container's
# root is root in a user namespace (rootless podman): "ct".
#   strace-tools-run.sh SCRIPT OUTDIR
set -uo pipefail
s=$1 o=$2
mkdir -p "$o"
podman run --rm --network none --cap-add SYS_PTRACE --cap-add AUDIT_WRITE --tmpfs /t:rw,exec,suid,size=64m,mode=1777 \
    -v "$o:/out" -v "$s:/s.sh:ro" -v "$(dirname "$s")/pty-type.py:/pty-type.py:ro" localhost/px13-ubuntu bash /s.sh > "$o/run.out" 2>&1
echo "rc=$?" >> "$o/run.out"
# The throwaway accounts' password hashes are in what the tools read:
# cut them from the kept traces (the method and its parameters stay).
sed -i -E 's/\$y\$j9T\$[.\/A-Za-z0-9]+\$[.\/A-Za-z0-9]+/$y$j9T$<salt and hash cut>/g' "$o"/*.strace
