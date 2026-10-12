#!/bin/bash
# px36, on kasumi: the strace container (no network; a tmpfs /t; the
# binaries read-only; the output under st/straces).
L=~/lanes/px36; O=$L/st/straces
mkdir -p $O
podman run --rm --network none --cap-add SYS_PTRACE --tmpfs /t:rw,size=256m,mode=1777 \
  -v $L/st/bore:/bore:ro -v $L/st/peltbin:/pelt:ro -v $O:/out -v $L/st/strace-changes.sh:/s.sh:ro \
  localhost/px13-ubuntu bash /s.sh > $L/st/strace-run.out 2>&1
echo "rc=$?" >> $L/st/strace-run.out
