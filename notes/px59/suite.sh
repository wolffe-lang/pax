#!/bin/bash
# px59 on kasumi: one suite as px58's notes/px58/suite.sh runs mpx5-yew —
# the build in localhost/px13-ubuntu (cpus 4-15, ulimit -c 0), the Linux
# side (a suite's --only linux, rootless podman) and the boots on kasumi
# itself under taskset -c 0-3 — the build tree kept (KEEP=1) or pruned,
# the logs kept. A suite with --only build takes it; one with --no-boot
# (mpx3-screen) builds with that.
#   suite.sh SUITE TAG TIER FIRMWARE [PHASES: build,linux,boot]
L=$HOME/lanes/px59
S=$1 T=$2 TI=$3 FW=$4 PH=${5:-build,linux,boot}
B=$L/build/$T
mkdir -p $B $L/tmp
cd $L/pax
git log --oneline -1
if grep -q -- '--only build' tests/$S; then bflag="--only build"; else bflag="--no-boot"; fi
case ,$PH, in *,build,*)
podman run --rm --privileged --cpuset-cpus 4-15 --ulimit core=0:0 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B \
    localhost/px13-ubuntu bash -c "ulimit -c 0; cd $L/pax && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/$S $bflag --tier $TI" > $B.$S.build.log 2>&1
echo "$S build: $? ($(tail -n 1 $B.$S.build.log))" ;;
esac
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
W=$B/$S
case ,$PH, in *,linux,*)
if grep -q -- '--only linux' tests/$S; then
  tests/$S --only linux --images $W > $B.$S.linux.log 2>&1
  echo "$S linux: $? ($(tail -n 1 $B.$S.linux.log))"
fi ;;
esac
case ,$PH, in *,boot,*)
taskset -c 0-3 tests/$S --images $W --tier $TI --firmware $FW > $B.$S.boot.log 2>&1
rc=$?
echo "$S boot: $rc ($TI $FW; load $(cut -d' ' -f1-3 /proc/loadavg))"
grep -a 'PASS\|FAIL\|SKIP' $B.$S.boot.log | cut -c1-700
tail -n 1 $B.$S.boot.log ;;
esac
[ "${KEEP:-1}" = 1 ] || { podman unshare rm -rf $W 2>/dev/null || rm -rf $W; }
exit ${rc:-0}
