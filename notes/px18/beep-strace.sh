#!/bin/bash
# px18: black-box strace of Linux's `beep` (Ubuntu 24.04's beep 1.4.9,
# a disposable container on kasumi). Which interface does a Linux beep
# program use? Its console driver asks KIOCSOUND (0x4b2f) of a console
# descriptor it opens O_WRONLY; its evdev driver asks EVIOCGSND. The
# device paths are not consoles here (no VT in a container), so every
# call answers ENOTTY, which is what makes the requests visible.
podman run --rm docker.io/library/ubuntu:24.04 bash -c "
  apt-get update -qq >/dev/null 2>&1
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq beep strace >/dev/null 2>&1
  touch /tmp/f
  strace -f -e trace=openat,ioctl,newfstatat,write,clock_nanosleep,nanosleep beep -e /tmp/f -f 440 -l 100 2>&1 | tail -20; echo ---
  strace -f -e trace=openat,ioctl,newfstatat,write,clock_nanosleep,nanosleep beep -e /dev/null -f 440 -l 100 -n -f 880 -l 50 2>&1 | tail -20; echo ---
  strace -X raw -f -e trace=ioctl beep -e /dev/null -f 440 -l 100 2>&1 | tail -6"
