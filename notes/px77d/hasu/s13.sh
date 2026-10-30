# px77d s13: kernel-as at the want= head, both tiers; the K8 plant editing only K8's want= (18 -> 17).
set -u
L=/home/mfwolffe/lanes/px77d
P=/home/mfwolffe/lanes/hasu-env/bin/podman
HEAD_SHA=$1
step() { echo "=== $(date -u +%FT%TZ) $*"; }
end() { echo "END $1 exit=$2 $(date -u +%FT%TZ)"; }
cd $L/pax && git fetch -q origin px77d && git checkout -q -f "$HEAD_SHA" && git clean -fdq && git rev-parse HEAD || exit 3
rm -rf $L/tree-k8b && git clone -q $L/pax $L/tree-k8b && git -C $L/tree-k8b checkout -q -f "$HEAD_SHA" || exit 3
sed -i '/# K8: boot\/start.S answered with text./,/# K9: no output/ s/ want=18 # K4.s$/ want=17 # K4'"'"'s/' $L/tree-k8b/tests/kernel-as
git -C $L/tree-k8b diff --stat; git -C $L/tree-k8b diff | grep '^[-+] ' || { echo "plant did not apply"; exit 3; }
[ "$(git -C $L/tree-k8b diff | grep -c '^[-+] ')" = 2 ] || { echo "plant touched more than K8's want="; exit 3; }
mkdir -p $L/tmp $L/logs/s13
r41() { # tree build log cmd
  $P run --rm --name px77d-kas --memory 12g --pids-limit 16384 --ulimit core=0:0 \
   -v "$L:$L" -w "$1" -e PAX_CACHE=$L/cache -e PAX_BUILD=$2 -e TMPDIR=$L/tmp -e CARGO_INCREMENTAL=0 \
   -e PATH=/opt/s263-rust/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
   -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
   localhost/r41-toolchain:1 /usr/bin/taskset.real -c 0-5 bash -c "$4" > "$3" 2>&1
}
SEAM='export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && export PAX_SEAM_WOLF=$(PAX_WOLF_PIN=tests/kernel-as.d/wolf.pin tools/fetch-wolf | tail -n 1) && "$PAX_SEAM_WOLF" --version &&'
step "J8 kernel-as at the head $HEAD_SHA, both tiers (expect PASS)"
rm -rf $L/build-kas-head; r41 $L/pax $L/build-kas-head $L/logs/s13/kas-head.log "$SEAM time tests/kernel-as --tier both"; end J8 $?
step "J9 the K8 plant: only K8's want= 18 -> 17, native (expect FAIL K8 '18 through WOLF_AS (17)')"
rm -rf $L/build-kas-k8b; r41 $L/tree-k8b $L/build-kas-k8b $L/logs/s13/kas-plant-k8-want.log "$SEAM time tests/kernel-as --tier native"; end J9 $?
grep -F 'FAIL K8 native: refused; by name yes (yes), 0 assembly calls through cc (0), 18 through WOLF_AS (17)' $L/logs/s13/kas-plant-k8-want.log && echo "J9 the planted expectation printed"
step "s13 done"
