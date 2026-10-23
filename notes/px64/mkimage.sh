#!/bin/bash
# px64, kasumi: build the lane's own container image on CPUs 12-15.
set -u
L=$HOME/lanes/px64
printf '%s\n' $$ > "$L/mkimage.pid"
cd "$L"
podman build --cpuset-cpus 12-15 -t localhost/px64-ubuntu -f "$L/Containerfile" "$L/ctx" 
echo "build rc=$?"
podman run --rm --cpuset-cpus 12-15 localhost/px64-ubuntu bash -c 'dpkg-query -W -f "\${Package} \${Version}\n" libc6 libc6-dev gcc-13 clang-18 lld-18 qemu-system-x86 ovmf xorriso binutils python3.12 | sort; ldd --version | head -1; qemu-system-x86_64 --version | head -1'
podman image inspect localhost/px64-ubuntu --format '{{.Id}}'
echo "mkimage.sh done $(date -Is)"
