#!/bin/bash
# px58 on kasumi: tests/mpx5-yew as px54's notes/px54/suite.sh runs a
# suite — `--only build` in localhost/px13-ubuntu (cpus 4-15), `--only
# linux --images` (its containers, rootless podman) and the boots on
# kasumi itself under taskset -c 0-3 — the build tree kept for reuse
# (KEEP=1) or pruned, the logs kept.
#   suite.sh TAG TIER FIRMWARE [PHASES: build,linux,boot]
L=$HOME/lanes/px58
T=$1 TI=$2 FW=$3 PH=${4:-build,linux,boot}
B=$L/build/$T
S=mpx5-yew
mkdir -p $B
cd $L/pax
git log --oneline -1
case ,$PH, in *,build,*)
podman run --rm --privileged --cpuset-cpus 4-15 --ulimit core=0:0 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B \
    localhost/px13-ubuntu bash -c "cd $L/pax && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/$S --only build --tier $TI" > $B.build.log 2>&1
echo "$S build: $? ($(tail -n 1 $B.build.log))" ;;
esac
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
W=$B/$S
case ,$PH, in *,linux,*)
tests/$S --only linux --images $W > $B.linux.log 2>&1
echo "$S linux: $? ($(tail -n 1 $B.linux.log))" ;;
esac
case ,$PH, in *,boot,*)
taskset -c 0-3 tests/$S --images $W --tier $TI --firmware $FW > $B.boot.log 2>&1
rc=$?
echo "$S boot: $rc ($TI $FW; load $(cut -d' ' -f1-3 /proc/loadavg))"
grep -a 'PASS\|FAIL\|SKIP' $B.boot.log | cut -c1-600
tail -n 1 $B.boot.log ;;
esac
[ "${KEEP:-1}" = 1 ] || { podman unshare rm -rf $W 2>/dev/null || rm -rf $W; }
exit ${rc:-0}
