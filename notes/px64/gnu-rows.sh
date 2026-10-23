#!/bin/bash
# px64, kasumi: notes/px64/gnu-rows.py in scent's oracle container
# (localhost/px64-scent-oracle, scent's ci/oracle.Containerfile), with the
# GNU 3.12 build scent's tools/fetch-oracle made (digest checked first).
set -u
L=$HOME/lanes/px64
G=$L/scent/.oracle/grep
sha256sum "$G"
podman run --rm --cpuset-cpus 12-15 --network none -v "$L:$L:Z" -e LC_ALL=C localhost/px64-scent-oracle \
    bash -c "ldd --version | head -1; $G --version | head -1; python3 -I $L/pax/notes/px64/gnu-rows.py $L/pax $G"
echo "gnu-rows rc=$?"
