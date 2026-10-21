#!/bin/bash
# px58 on kasumi: what yew asks of Linux in the typed session, black-box:
# tests/mpx5-yew's session (user/console/yew.keys) typed by
# tools/linux-tty into the suite's own binaries on a pseudo-terminal in
# localhost/px13-ubuntu, PAX's environment (TERM=linux), as `pax`
# (1000:1000, HOME=/home/pax), the whole session under `strace -f` (pelt,
# yew, its guard, cat); the session's transcript kept beside the trace.
#   census-session.sh SESSION-TREE OUTDIR
L=$HOME/lanes/px58; T=$1; O=$2
mkdir -p $O
podman run --rm --cap-add SYS_PTRACE --security-opt seccomp=unconfined --network none --ulimit core=0:0 \
    --cpuset-cpus 4-15 -v $L:$L:Z localhost/px13-ubuntu bash -c "
set -u
mkdir -p /w/bin /home/pax
cp $T/bin/sh $T/bin/as /w/bin/ && cp $T/bin/yew /bin/yew
cp $T/home/pax/notes.txt /home/pax/notes.txt
chown -R 1000:1000 /home/pax && chmod 755 /home/pax && chmod 644 /home/pax/notes.txt
python3 $L/pax/tools/linux-tty --keys $L/pax/user/console/yew.keys --prompt '\$ ' $O/session.tty -- \
    /usr/bin/strace -f -qq -n -v -xx -s 1048576 -o $O/session.strace /w/bin/as 1000 1000 /usr/bin/env HOME=/home/pax /w/bin/sh -i -m
echo \"linux-tty: \$? status \$(cat $O/session.tty.rc)\"
cat /home/pax/notes.txt
ls -la /home/pax /home/pax/.local 2>&1 | head -20
find /home/pax -xdev | sort
"
