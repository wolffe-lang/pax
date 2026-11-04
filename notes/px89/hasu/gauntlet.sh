#!/usr/bin/env bash
# px89: the gauntlet at the checkout's HEAD, run by planning's
# gauntlet-record.sh (gaunt-launch.sh). Each step takes the block's two
# locks for itself alone (the 2 h hold rule: the locks are never held
# across steps), runs in the container on the checkout, and prints its
# output indented two spaces; a suite's own `FAIL <row> …` lines are
# repeated unindented at the step's end (the plant record's names). A
# step's command is its CI job's `run: tests/…` lines with the PR leg
# (`--tier native --firmware bios`) for $PAX_LEGS.
#   gauntlet.sh BLOCK SUITE...   (from the checkout's root)
set -uo pipefail
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) # gaunt-launch.sh's snapshot of the scripts
. "$S/gauntlet-record.sh"
L=/home/mfwolffe/lanes/px89
B=$1; shift
WT=$(pwd)
HEAD=$(git rev-parse HEAD)
R=$L/build/g-${HEAD:0:8}-$$
mkdir -p "$R"
legs="--tier native --firmware bios"
# The CI job's test lines for SUITE, $PAX_LEGS replaced.
cmds_of() {
    python3 -I - "$1" "$legs" "$WT/.github/workflows/ci.yml" <<'PY'
import re, sys
job, legs = sys.argv[1], sys.argv[2]
text = open(sys.argv[3]).read()
body = text.split("\n  " + job + ":\n", 1)[1]
body = re.split(r"\n  [A-Za-z0-9_-]+:\n", body, maxsplit=1)[0]
want = re.compile(r"^(tests/\S|tools/ci-retry |python3 -I (tests|tools)/)")
lines = body.split("\n")
i = 0
while i < len(lines):
    m = re.match(r"^        run: (.*)$", lines[i])
    i += 1
    if not m:
        continue
    if m.group(1).strip() != "|":
        cmds = [m.group(1)]
    else:
        cmds = []
        while i < len(lines) and (lines[i].startswith("          ") or not lines[i].strip()):
            cmds.append(lines[i].strip())
            i += 1
    for c in cmds:
        if want.match(c):
            print(c.replace("$PAX_LEGS", legs))
PY
}
one() { # name kvm/net opts -- cmd
    local name=$1; shift
    local opts=()
    while [ "${1:-}" != -- ]; do opts+=("$1"); shift; done
    shift
    local f; f=$R/$(printf '%s' "$name" | tr -c 'A-Za-z0-9._-' '_').log
    flock -w 21600 /home/mfwolffe/lanes/hasu-block-$B.lock flock -w 21600 /home/mfwolffe/lanes/hasu-$B.lock \
        env CTR_WD="$WT" CTR_ENV="-e PAX_REQUIRE_UEFI=1 -e PAX_REQUIRE_DHCP_WIRE=1" \
        bash "$S/ctr2.sh" "$B" "g-${HEAD:0:8}-$name" localhost/px89-dhcp:1 ${opts[@]+"${opts[@]}"} -- \
        bash -c 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); for c in "$@"; do echo "+ $c"; eval "$c" || exit $?; done; exit 0' px89 "${CMDS[@]}" \
        > "$f" 2>&1
    local rc=$?
    sed 's/^/  /' "$f"
    grep -a -E '^[a-z0-9.-]+: FAIL [A-Za-z0-9_.:/-]+' "$f" | sed -E 's/^[a-z0-9.-]+: FAIL /FAIL /' | head -200
    return $rc
}
suite() {
    local s=$1
    mapfile -t CMDS < <(cmds_of "$s")
    [ "${#CMDS[@]}" -gt 0 ] || { echo "  no run: tests/ line in the $s job"; return 2; }
    one "$s" KVM=1 NET=1 ENGINE=1 --
}
for s in "$@"; do
    case $s in
        selftests)
            CMDS=("tests/ci-plan" "python3 -I tests/ci-retry.py" "python3 -I tests/mpx2-heap.d/budget.py" "python3 -I tests/ci-budgets.py"
                  "tests/fetch-retry-selftest" "tests/expect-serial-selftest" "sh tests/census")
            gauntlet_step selftests one selftests -- || exit $?
            ;;
        *)
            gauntlet_step "$s" suite "$s" || exit $?
            ;;
    esac
done
