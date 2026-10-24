#!/usr/bin/env bash
# px68, kasumi: e2fsck's replay (the pinned e2fsprogs, tools/e2fs) of
# journals written by tools/mkjournal from the documented layout: which
# blocks it replays where a transaction revokes, escapes, wraps, tears or
# never commits. Each case a copy of one ext3 image (tools/mkdisk
# --journal 32M), its journal written, `e2fsck -fy`, then the target
# blocks' first bytes and the journal as left. Prints a line a case.
#   oracle.sh
set -uo pipefail
L=$HOME/lanes/px68; T=${PAX_TREE:-$L/pax}; O=$L/oracle
rm -rf "$O"; mkdir -p "$O"
export PAX_CACHE=$L/cache PAX_ENGINE=podman TMPDIR=$L/tmp
cd "$T"
SOURCE_DATE_EPOCH=1700000000 tools/mkdisk --journal --label px68-oracle 32M "$O/base.img" > "$O/mkdisk.txt" || { cat "$O/mkdisk.txt"; exit 2; }
cat "$O/mkdisk.txt"
tools/mkjournal "$O/base.img" --dump
# free blocks to aim at
fb=$(tools/e2fs "$O" debugfs -R "ffb 3 6000" base.img 2>/dev/null | sed -n 's/^Free blocks found: //p')
set -- $fb
B1=$1 B2=$2 B3=$3
echo "targets: $B1 $B2 $B3"
max=$(tools/mkjournal "$O/base.img" --dump | sed -n 's/.*maxlen \([0-9]*\),.*/\1/p')
peek() { # img block -> first 4 bytes hex
    dd if="$1" bs=4096 skip="$2" count=1 status=none | head -c 4 | od -An -tx1 | tr -d ' \n'
}
run_case() { # name spec-text
    local n=$1; shift
    cp "$O/base.img" "$O/$n.img"
    printf '%s\n' "$@" > "$O/$n.spec"
    tools/mkjournal "$O/$n.img" "$O/$n.spec" || { echo "$n: mkjournal failed"; return; }
    tools/mkjournal "$O/$n.img" --dump > "$O/$n.before"
    tools/e2fs "$O" debugfs -R logdump "$n.img" > "$O/$n.logdump" 2>&1
    rc=0; tools/e2fs "$O" e2fsck -fy "$n.img" > "$O/$n.fsck" 2>&1 || rc=$?
    printf '%-10s e2fsck %d (%s); %s=%s %s=%s %s=%s; after: %s\n' "$n" "$rc" \
        "$(grep -E 'recovering|journal|Journal' "$O/$n.fsck" | head -n 2 | tr '\n' '|')" \
        "$B1" "$(peek "$O/$n.img" "$B1")" "$B2" "$(peek "$O/$n.img" "$B2")" "$B3" "$(peek "$O/$n.img" "$B3")" \
        "$(tools/mkjournal "$O/$n.img" --dump | sed -n '1s/.*sequence \([0-9]*\), start \([0-9]*\).*/sequence \1 start \2/p')"
    grep -v '^debugfs' "$O/$n.logdump" | sed 's/^/    logdump: /' | head -n 12
}
run_case A   "start 1 1" "tx" "write $B1 a1" "write $B2 a2" "commit" "recover"
run_case B   "start 1 1" "feature revoke" "tx" "write $B1 b1" "commit" "tx" "revoke $B1" "commit" "recover"
run_case Bnf "start 1 1" "tx" "write $B1 b1" "commit" "tx" "revoke $B1" "commit" "recover"
run_case C   "start 1 1" "feature revoke" "tx" "write $B1 c1" "revoke $B1" "commit" "recover"
run_case C2  "start 1 1" "feature revoke" "tx" "write $B1 c1" "commit" "tx" "write $B1 c2" "revoke $B1" "commit" "recover"
run_case D   "start 1 1" "feature revoke" "tx" "revoke $B1" "commit" "tx" "write $B1 d3" "commit" "recover"
run_case D2  "start 1 1" "feature revoke" "tx" "write $B1 d1" "commit" "tx" "revoke $B1" "commit" "tx" "write $B1 d3" "commit" "recover"
run_case E   "start 1 1" "tx" "write $B1 magic" "write $B2 e2" "commit" "recover"
run_case F   "start 1 1" "tx" "write $B1 f1" "commit" "tx" "write $B1 f2" "write $B2 f2" "torn" "recover"
run_case G   "start 1 1" "tx" "write $B1 61" "write $B2 62" "end" "recover"
run_case H   "start 5 $((max - 2))" "tx" "write $B1 71" "write $B2 72" "write $B3 73" "commit" "recover"
run_case I   "start 9 1" "tx" "write $B1 81" "commit" "tx" "write $B2 82" "commit" "tx" "write $B3 83" "end" "recover"
run_case Z   "start 1 0" "recover"
