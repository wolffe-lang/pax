#!/usr/bin/env bash
# px78b (pax#254): one hold of block A (a blocking flock, as the block's other user waits): the native kernels at
# f2aa9fd8 (last green) and 56b9f554 (first red) and the lookups' place in nm's output; then the noserial row
# (tests/mpx6-install --only noserial, TCG, px78-ubuntu:1) from trunk's qemu-halt (the red worktree) and from the
# fix (44fb33ea, the green worktree), 3 runs each with GNU awk first on PATH, and once from the fix with mawk.
set -uo pipefail
L=/home/mfwolffe/lanes/px78b
printf '%s\n' "$$" > $L/ns-all.pid
GAWK=$(readlink -f /run/current-system/sw/bin/gawk)
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
printf '%s px78b ns-all acquiring block A (blocking)\n' "$(date -u +%FT%TZ)"
flock 9
printf '%s block A acquired\n' "$(date -u +%FT%TZ)"
pod() { /home/mfwolffe/lanes/hasu-env/bin/podman run --rm --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
  -v /nix:/nix:ro -v "$L:$L" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
  -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/build -e TMPDIR=$L/tmp "$@"; }
pod -w $L localhost/px75-ubuntu:2 taskset -c 0-5 bash -c 'for c in f2aa9fd8 56b9f554; do (cd '"$L"'/k-$c && tools/build-kernel --src kernel/kmain_console.lu '"$L"'/kbuild-$c > '"$L"'/kbuild-$c.path 2> '"$L"'/kbuild-$c.log; echo "END kbuild $c exit=$?"); done'
pod localhost/px78-ubuntu:1 taskset -c 0-5 bash $L/sigpipe-witness3.sh "$GAWK" $(cat $L/kbuild-f2aa9fd8.path) $(cat $L/kbuild-56b9f554.path)
for side in red green; do
 tree=$L/$side
 for r in 1 2 3; do
  rm -rf $L/w-ns-$side-$r
  pod -w $tree localhost/px78-ubuntu:1 taskset -c 0-5 bash -c "export PATH=$L/gawk-awk:\$PATH; awk --version | head -1; git log --oneline -1; tests/mpx6-install --only noserial --work $L/w-ns-$side-$r --inputs $L/w/inputs"
  echo "END ns $side gawk run $r exit=$?"
 done
done
rm -rf $L/w-ns-green-mawk
pod -w $L/green localhost/px78-ubuntu:1 taskset -c 0-5 bash -c "awk -W version 2>&1 | head -1; git log --oneline -1; tests/mpx6-install --only noserial --work $L/w-ns-green-mawk --inputs $L/w/inputs"
echo "END ns green mawk run 1 exit=$?"
flock -u 9; exec 9>&-
printf '%s block A RELEASED; NS-ALL DONE\n' "$(date -u +%FT%TZ)"
