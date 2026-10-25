#!/usr/bin/env bash
# kasumi only: build the existing compact fixture and complete playground
# payload. No installer verdict is claimed by these prerequisite builds.
# Caller: setsid -f bash bootstrap.sh > bootstrap-03.log 2>&1 < /dev/null
# No signal handlers; the outer shell records the inner shell's exit.
L=$HOME/lanes/px71
mkdir -p "$L/logs-03" "$L/build" "$L/tmp" "$L/cache"
printf '%s\n' "$$" > "$L/bootstrap-03.pid"
printf 'px71 bootstrap-03 start %s\n' "$(date -Is)"
bash -s <<'INNER'
set -euo pipefail
L=$HOME/lanes/px71
P=$L/pax
W=$L/build/full
mkdir -p "$W"
export PAX_CACHE=$L/cache PAX_BUILD=$L/build/common TMPDIR=$L/tmp
export PAX_LOPE_REPO=$L/lope CARGO_INCREMENTAL=0 SOURCE_DATE_EPOCH=1700000000
step() {
    local name=$1 rc=0; shift
    [ "$(df -Pk "$L" | awk 'NR==2 {print $4}')" -gt 12582912 ] || { echo 'FAIL disk floor (12 GiB)'; return 3; }
    [ "$(du -sk "$L" | cut -f1)" -lt 15728640 ] || { echo 'FAIL lane cap (15 GiB)'; return 3; }
    printf '%s waiting for CPUs 8-11 %s\n' "$name" "$(date -Is)"
    exec 9> "$HOME/lanes/kasumi-cores-8-11.lock"
    flock 9
    printf '%s start %s\n' "$name" "$(date -Is)"
    podman run --rm --memory 8g --ulimit core=0:0 \
        -v "$L:$L:Z" -e PAX_CACHE -e PAX_BUILD -e TMPDIR -e PAX_LOPE_REPO \
        -e CARGO_INCREMENTAL -e SOURCE_DATE_EPOCH -e TZ=UTC -w "$P" \
        localhost/px80-ubuntu taskset -c 8-11 bash -c '
            set -euo pipefail
            PAX_WOLF=$(tools/fetch-wolf)
            export PAX_WOLF
            export PATH="$(dirname "$PAX_WOLF"):$PATH"
            "$PAX_WOLF" --version
            exec "$@"
        ' px71-build "$@" 9>&- > "$L/logs-03/$name.log" 2>&1 || rc=$?
    flock -u 9
    exec 9>&-
    printf '%s exit=%s %s\n' "$name" "$rc" "$(date -Is)"
    if [ "$rc" -ne 0 ]; then tail -40 "$L/logs-03/$name.log"; return "$rc"; fi
}
git -C "$PAX_LOPE_REPO" cat-file -e 'e6f623c778dd486436bcb0a7d481333e0463b906^{commit}'
step pack tools/mkpack "$W/pack"
step disktools-build tests/mpx6-disktools --only build --work "$L/build/disktools" --tier both
step pelt tools/mkpelt "$W/pelt"
step lope tools/mklope "$W/lope"
step aspen tools/mkaspen "$W/aspen"
step scent tools/mkscent "$W/scent"
step std tools/fetch-std "$W/std"
step yew tools/mkyew "$W/yew"
step bore tools/mkboreutils "$W/bore" base32 base64 basename cat chgrp chmod chown comm cp cut dirname echo env expand false fold groups head id join kill link ln logname ls mkdir mkfifo mktemp mv nl nproc paste printenv printf pwd readlink realpath rm rmdir seq shuf sleep sort stat sync tac tail tee timeout touch tr true truncate tsort tty unexpand uniq unlink wc whoami yes
step as tools/mkas "$W/bin"
step su tools/mksu "$W/su"
step play tools/mkplay "$W/play"
step zone tools/mkzone "$W/localtime"
step probe tools/mkdiskprobe "$W/probe"
step lupin tools/mklupin "$W/lupin"
find "$W" -type f -executable -print0 | sort -z | xargs -0 sha256sum > "$L/build/full-binaries.sha256"
sha256sum -c "$L/build/full-binaries.sha256" > "$L/logs-03/full-readback-1.log"
sha256sum -c "$L/build/full-binaries.sha256" > "$L/logs-03/full-readback-2.log"
printf 'prerequisite payload builds complete %s\n' "$(date -Is)"
INNER
rc=$?
printf '%s\n' "$rc" > "$L/bootstrap-03.exit"
printf 'px71 bootstrap-03 exit=%s %s\n' "$rc" "$(date -Is)"
exit "$rc"
