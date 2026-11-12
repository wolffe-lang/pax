#!/usr/bin/env bash
# notes/px129/rig/pty-rate.sh N ACCEL FIRMWARE — run by step.sh's `ptyrate` in the rig's container, in the
# checkout: tests/mpx5-pty's session image through the suite once (its build, its first boot), then N-1 more
# boots of the same image, each run's rows cut and checked as the suite does (check.py against the Linux
# reference and ruled.txt). pax#382: the session's driver resized the pty the moment a command's marker came,
# and whether pelt redrew its prompt for it turned on how far pelt had got, so S|4 differed in some boots and
# not others. A line a boot, two spaces in; then `PASS Y3 …` or `FAIL Y3 …` at column 0 with the counts;
# exit 1 when any boot's run differs or a boot did not end as the suite's Y5 wants.
set -u
N=${1:?boots} ACCEL=${2:?kvm or tcg} FW=${3:?bios or uefi}
. tools/lib.sh
work=$PAX_BUILD/mpx5-pty; ref=tests/mpx5-pty.d
id="native $FW $ACCEL session"
cut_run() { # norm k out: the run's rows, as tests/mpx5-pty cuts them
    awk -v k="$2" '$0 ~ "^run " k ": " { on = 1; next }
         on && (/^run [0-9]+: / || /^run: [0-9]+ commands/ || /^user: frames free /) { exit }
         on { i = index($0, "user: "); if (i == 1) next; if (i > 1) { printf "%s", substr($0, 1, i - 1); next } print }' "$1" > "$3"
}
bad_root=0 bad_user=0 bad_end=0 rows=
judge() { # boot norm halt-status
    local b=$1 norm=$2 hrc=$3 line="  boot $1:" k name out gate
    for k in 1 2; do
        case $k in 1) name=session-root ;; *) name=session-user ;; esac
        out=$PAX_BUILD/pty-rate-$b.$name.txt
        cut_run "$norm" "$k" "$out"
        if gate=$(python3 -I "$ref/check.py" "$name" "$ref/linux/$name.txt" "$ref/ruled.txt" "$out" 2>&1); then
            line+=" $name PASS"
        else
            line+=" $name $(printf '%s\n' "$gate" | grep '^FAIL' | head -n 3 | cut -c1-110 | tr '\n' '|')"
            rows+="$(printf '%s\n' "$gate" | grep '^FAIL' | cut -d: -f1 | sed "s/^FAIL /$name\//" | tr '\n' ' ')"
            case $k in 1) bad_root=$((bad_root + 1)) ;; *) bad_user=$((bad_user + 1)) ;; esac
        fi
    done
    if [ "$hrc" = 0 ] && grep -q '^PAX: init .* ended with status 0; nothing left to run$' "$norm" && ! grep -q '^PANIC ' "$norm"; then
        line+=" ended"
    else
        line+=" NOT ENDED (halt $hrc)"; bad_end=$((bad_end + 1))
    fi
    echo "$line"
}
PAX_PTY_IMAGES=session tests/mpx5-pty --tier native --firmware "$FW" --accel "$ACCEL" > "$PAX_BUILD/pty-rate-1.suite.txt" 2>&1
[ -f "$work/native/session.iso" ] || { sed 's/^/  /' "$PAX_BUILD/pty-rate-1.suite.txt"; echo "FAIL Y3 $id: the suite built no session image"; exit 1; }
log=$PAX_BUILD/mpx5-pty-native-$FW-$ACCEL-session.serial.log
serial_norm "$log" > "$PAX_BUILD/pty-rate-1.norm"
hrc=$(awk -v fw="$FW" -v a="$ACCEL" '$2 == fw && $3 == a && $4 == "session" { sub("halt-status=", "", $5); print $5 }' "$PAX_BUILD/mpx5-pty-runs.txt")
judge 1 "$PAX_BUILD/pty-rate-1.norm" "${hrc:-1}"
elf=$(cat "$work/native/elf.path")
for b in $(seq 2 "$N"); do
    log=$PAX_BUILD/pty-rate-$b.serial.log
    rm -f "$log" "$log.verdict"
    hrc=0
    tools/qemu-halt --accel "$ACCEL" --firmware "$FW" --serial "$log" --timeout 1200 --qemu -m --qemu 512M \
        --elf "$elf" --marker 'halt|PANIC .*' "$work/native/session.iso" > "$log.verdict" 2>&1 || hrc=$?
    serial_norm "$log" > "$PAX_BUILD/pty-rate-$b.norm"
    judge "$b" "$PAX_BUILD/pty-rate-$b.norm" "$hrc"
done
if [ $((bad_root + bad_user + bad_end)) = 0 ]; then
    echo "PASS Y3 $id: $N of $N boots, session-root and session-user each Linux's or its ruled line"
    exit 0
fi
echo "FAIL Y3 $id: session-root differs in $bad_root of $N boots, session-user in $bad_user, $bad_end not ended; rows: $(printf '%s\n' $rows | sort | uniq -c | tr -s ' ' | tr '\n' ';')"
exit 1
