#!/usr/bin/env bash
# run.sh 'CMD' — CMD (a bash line) in px75's rig: block B's lock, CPUs 6-11 by
# taskset inside the container, 12 GiB, /dev/kvm, the host's Linux kernel and
# modules read-only for the guest side. Output on stdout; exit CMD's.
export PATH=$HOME/lanes/hasu-env/bin:$HOME/lanes/hasu-env/profile/bin:$PATH
L=/home/mfwolffe/lanes/px75
K=$(readlink -f /run/current-system/kernel)
M=$(readlink -f /run/current-system/kernel-modules/lib/modules/$(uname -r))
exec flock $L/../hasu-block-B.lock podman run --rm --init --memory 12g --device /dev/kvm --security-opt label=disable \
  --pids-limit 16384 --tmpfs /ram:rw,size=3g,mode=1777 -v $L:$L -v /nix/store:/nix/store:ro \
  -e PAX_LINUX_KERNEL=$K -e PAX_LINUX_MODULES=$M -e PAX_ENGINE=podman -e HOME=$L/home \
  -e PATH=$L/rig/shim:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  -w $L/pax localhost/px75-ubuntu:2 taskset -c 6-11 bash -c "$1"
