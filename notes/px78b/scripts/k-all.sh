#!/usr/bin/env bash
# px78b (pax#254): the native kernels at f2aa9fd8 (last green) and 56b9f554 (first red) built as tests/mpx6-disktools
# builds them; the lookups' place in nm's output for those and the head's kernel; the trunk and fixed lines, mawk and
# GNU awk, 200 runs each. One blocking hold of block A.
set -uo pipefail
L=/home/mfwolffe/lanes/px78b
printf '%s\n' "$$" > $L/k-all.pid
GAWK=$(readlink -f /run/current-system/sw/bin/gawk)
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
flock 9
printf '%s block A acquired\n' "$(date -u +%FT%TZ)"
pod() { /home/mfwolffe/lanes/hasu-env/bin/podman run --rm --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
  -v /nix:/nix:ro -v "$L:$L" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
  -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/build -e TMPDIR=$L/tmp "$@"; }
pod -w $L localhost/px75-ubuntu:2 taskset -c 0-5 bash -c 'for c in f2aa9fd8 56b9f554; do (cd '"$L"'/k-$c && export PAX_WOLF=$(tools/fetch-wolf) && git log --oneline -1 && tools/build-kernel --src kernel/kmain_console.lu '"$L"'/kbuild-$c > '"$L"'/kbuild-$c.path 2> '"$L"'/kbuild-$c.log; echo "END kbuild $c exit=$?"); done'
head=$(cat $L/w/inputs/build/disktools/native.elf.path)
pod localhost/px78-ubuntu:1 taskset -c 0-5 bash $L/sigpipe-witness3.sh "$GAWK" $(cat $L/kbuild-f2aa9fd8.path) $(cat $L/kbuild-56b9f554.path) "$head"
pod localhost/px78-ubuntu:1 taskset -c 0-5 bash -c "bash $L/sigpipe-witness5.sh $head 200; PATH=$L/gawk-awk:\$PATH bash $L/sigpipe-witness5.sh $head 200"
flock -u 9; exec 9>&-
printf '%s block A RELEASED; K-ALL DONE\n' "$(date -u +%FT%TZ)"
