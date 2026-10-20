#!/bin/bash
# px53 on kasumi: PAX's first boot of the new images (pax-first-new.sh)
# held to real root's first recording (vm/rec1), each session cut and
# normalised as tests/mpx5-jobs cuts and normalises it (its run_part and
# norm_session, copied; tools/lib.sh's serial_norm).
L=$HOME/lanes/px53
P=$L/pax
. $P/tools/lib.sh
norm_session() { serial_norm "$1" | sed -E 's/^(\[[0-9]+\]) [0-9]+$/\1 PID/'; }
run_part() { # norm k
    awk -v k="$2" '
        $0 ~ "^run " k ": " { on = 1; next }
        on && /^run [0-9]+: |^run: [0-9]+ commands$|^user: frames free / { exit }
        on { i = index($0, "user: "); if (i == 1) next; if (i > 1) { printf "%s", substr($0, 1, i - 1); next } print }' "$1"
}
O=$L/ev/first-new
for im in groups sigs; do
  serial_norm $O/$im.serial.log > $O/$im.norm
  for k in 1 2; do
    n=$im; [ $k = 2 ] && n=$im-user
    run_part $O/$im.norm $k > $O/$n.session
    norm_session $O/$n.session > $O/$n.cmp
    norm_session $L/vm/rec1/$n.tty > $O/rec-$n.cmp
    if cmp -s $O/$n.cmp $O/rec-$n.cmp; then echo "SAME $n: $(wc -l < $O/$n.cmp) lines, $(sha256sum < $O/$n.cmp | cut -c1-12)"
    else echo "DIFFERS $n"; diff $O/rec-$n.cmp $O/$n.cmp | head -20; fi
  done
  echo "$im -ENOSYS: $(sed -n -E 's/^user: [^ ]+ pid [0-9]+ syscall ([0-9]+): -ENOSYS$/\1/p' $O/$im.norm | sort -un | paste -sd' ' -); refused: $(grep -c ': refused: ' $O/$im.norm); $(grep -m1 '^PAX: init ' $O/$im.norm)"
done
