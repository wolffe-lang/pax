# Changelog

pax has no release yet; this file starts with px17, whose contract asks
for a paragraph under an Unreleased heading. Earlier work is told in
`notes/` (one note per lane) and the planning repository's
`sprints/pax/index.md`.

## Unreleased

- **The screen (px19).** PAX draws its console on the framebuffer
  Limine hands it as well as on the serial port: the same bytes, a
  160×50 grid of Spleen 8×16 glyphs (BSD-2-Clause, vendored in `font/`)
  at QEMU's 1280×800, the common SGR colours (0 1 7 30–37 39 40–47 49
  90–97), deferred wrap, scrolling, a steady cursor, the boot replayed
  from the kernel's first line. The framebuffer is mapped
  write-combining through PAT entry 5 (uncached without the PAT).
  `TIOCGWINSZ` answers the grid when the screen is the console; a
  machine with no display device keeps 0 by 0. The shell's and the
  tour's kernels draw it and print nothing new. `tests/mpx3-screen`
  holds every headless screendump to `tools/screen-ref`'s picture of
  the same serial bytes, pixel for pixel, on both tiers, BIOS and
  UEFI; `tools/qemu-run --no-screen` boots with no display device.
  Named drift: no cursor movement or erase sequences (read and
  ignored), no back buffer (a scroll reads the framebuffer), no blink.

- **The speaker (px18).** PAX plays music through the PC speaker: the
  8254's channel 2 in square-wave mode gated through port 0x61
  (`kernel/speaker`), answering Linux's console ioctls KIOCSOUND and
  KDMKTONE (the interface a Linux beep program asks, measured by
  strace). `/bin/play` (`user/play`, wolf, one routine of assembly for
  the ioctl) plays plain-text note files (`title`, `tempo`, `gap`, a
  note and octave with a length, rests, dots and ties), checks a whole
  file before a sound and refuses a bad line by name, keeps an absolute
  schedule so no error accumulates, and lists `/usr/share/tunes` when
  called alone: `mambo` (Paxito, an original mambo-flavoured tune),
  `entertainer` (Joplin, 1902, public domain) and `scale`.
  `tests/mpx3-speaker` captures QEMU's speaker to a WAV file and holds
  every note of the scale within 1% of its pitch (measured: 0.25% at
  worst) and every onset of both tunes within 30 ms of its score
  (measured: 19 ms), from the kernel's own timeline read through the
  monitor. Named drift from Linux, on purpose: a tone stops when the
  process that started it ends, and every halt silences the speaker.
  Not yet: `/dev/tty0`, `/dev/console`, the evdev speaker.
- **Pipes, redirection and `cd` (px17).** pelt `3e7516c` (H2, wolf
  0.2.26) is the shell PAX boots, and its plumbing runs as on Linux:
  `ls /bin | wc -l`, `cat /etc/motd > /dev/null`, `cd /etc; cat motd`,
  a group reading one file through two children, `cd`'s errors — each
  typed session byte-identical to Linux's (`tests/mpx3-shell`,
  `shell-plumb`). New system calls: `pipe`, `pipe2`, `socketpair`,
  `sendto`, `recvfrom`, `fcntl`, `chdir`, `fchdir`; `getcwd` answers the
  real directory; `clone` without CLONE_VM is a **fork** (wolf 0.2.26's
  spawn forks, measured) on a copy of the caller's address space.
  Descriptors now share open files (one offset across `dup` and a
  child's copy, Linux's rule; px14's per-descriptor position is gone);
  pipes hold 65536 bytes, block, end at the last writer, and a write
  with no reader dies of SIGPIPE (status 13) under the default action
  (not pid 1) or answers -EPIPE; every process's end closes its
  descriptors. The tour's closing line now reads "All in wolf. Linux
  programs run on it unmodified: a shell, its pipes, its tools."
  Named drift: a seqpacket socket's record boundaries, a SIGPIPE
  handler not run, CLONE_CHILD_CLEARTID not kept, a fork copies every
  page.
