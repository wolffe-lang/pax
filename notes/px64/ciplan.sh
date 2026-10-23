#!/bin/bash
# px64, kasumi: tests/ci-plan (python3 and bash, no QEMU) in the lane's container.
set -u
L=$HOME/lanes/px64
P=${PX64_SRC:-$L/pax}
podman run --rm --cpuset-cpus 12-15 -v "$L:$L:Z" localhost/px64-ubuntu bash -c "cd $P && git config --global --add safe.directory '*' && tests/ci-plan > $L/ciplan.log 2>&1; echo \"ci-plan rc=\$?\"; grep -E 'FAIL|WARN' $L/ciplan.log | head -20; grep -c PASS $L/ciplan.log"
