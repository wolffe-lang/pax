# Changelog

pax has no release yet; this file starts with px17, whose contract asks
for a paragraph under an Unreleased heading. Earlier work is told in
`notes/` (one note per lane) and the planning repository's
`sprints/pax/index.md`.

## Unreleased

- **The writable tree (px27).** PAX's file tree is writable, in memory:
  `kernel/tree` keeps inodes (files whose bytes are frames under an
  index that grows with the file, with holes; directories of records)
  and the initramfs is its first contents, each file read in place from
  the archive until something writes to it. `openat` takes `O_CREAT`,
  `O_EXCL`, `O_TRUNC`, `O_APPEND`, `O_WRONLY`, `O_RDWR` and
  `O_NOFOLLOW`, with the mode and the process's `umask`; `write`,
  `pwrite64`, `ftruncate`, `truncate`, `mkdir`, `mkdirat`, `rmdir`,
  `unlink`, `unlinkat`, `rename`, `renameat`, `renameat2` (no flag),
  `fsync`, `fdatasync`, `access`, `faccessat`, `faccessat2` and `umask`
  answer; `copy_file_range` and `sendfile` copy between files, `splice`
  from a pipe into one; `statx`, `fstat` and `getdents64` answer from
  the inodes, with tmpfs's sizes and link counts for a directory and
  real times from the wall clock. A file unlinked while open lives
  until its last close; a directory removed under a process stays,
  empty, until the process leaves; `rename` is every check, then the
  change. Paths are resolved a directory at a time. The tree holds at
  most half the frames that were free at boot and never takes the
  machine's last 2,048: `ENOSPC`. Refused by name, each counted: hard
  and symbolic links, device nodes, changes of mode, owner and times,
  `O_DIRECT`, `O_SYNC`, `O_DSYNC`, `O_NOATIME`, `O_PATH`, `O_TMPFILE`,
  a `renameat2` flag, anything made or removed under `/dev`, and the
  `execve` of a program written since boot. The shell's image carries
  boreutils at bu21 (`abc59f5`), with `mkdir`, `rmdir`, `rm`, `mv` and
  `cp`; `tests/mpx3-tree` holds a static probe and a typed session to
  Linux's tmpfs byte for byte, the Linux side in a throwaway container.
  No disk: the tree is gone at halt. No link of either kind, no `chmod`,
  no `touch`, no `mmap` of a file, no AF_UNIX path socket, no `/proc`
  or `/sys` beyond `/proc/self/exe`.
- **Threads, futexes and signals (px26).** PAX's shell image runs the
  current pelt (sh05, `b32bebc`) and the current boreutils (bu20,
  `870815c`) unmodified. A process may have threads: `clone`/`clone3`
  with `CLONE_THREAD` makes one in the caller's group — the same
  address space, descriptors, working directory and signal actions; its
  own tid, stack, FS base, signal mask and x87/SSE/AVX state — `exit`
  ends a thread and `exit_group` the process, a thread's end zeroes its
  clear-child-tid word and wakes the futex there, and `execve` from a
  process with threads ends the others first. `kernel/futex` is wait
  and wake, with and without a bitset, private or not, with a timeout;
  every other operation is refused by name. `kernel/signal` delivers:
  `rt_sigaction` with handlers, `rt_sigprocmask` per thread,
  `rt_sigpending`, `kill`, `tgkill`, `tkill`, the frame a glibc
  handler expects on the thread's stack (siginfo, ucontext, the
  extended state as XSAVE wrote it) and `rt_sigreturn`, which puts
  back every register and that state; SA_RESTART, SA_SIGINFO,
  SA_NODEFER, SA_RESETHAND; the default actions terminate and ignore,
  with stop and continue refused by name; a signal ends a waiting
  `read`, `wait4`, `futex` or sleep with the call run again or -EINTR
  as Linux does each; SIGPIPE, SIGCHLD and a fault's signal reach
  handlers. The console's line discipline has ISIG: Ctrl-C, Ctrl-\
  and Ctrl-Z raise SIGINT, SIGQUIT and SIGTSTP for every process (PAX
  has one process group). Memory: a `PROT_NONE` mapping reserves
  addresses and takes no frame until `mprotect` gives it access (a
  thread's 128 MiB heap reservation costs 33 frames), and `madvise`
  honours MADV_DONTNEED and MADV_GUARD_INSTALL. For bu20's long
  listing: `readlink` and `readlinkat` answer `/proc/self/exe`,
  `sendfile` and `splice` copy to a pipe or the console,
  `copy_file_range` answers as Linux does where no file can be
  written, a file's blocks are whole pages, and CLOCK_REALTIME reads
  the CMOS clock (`kernel/rtc`), so a file from 1970 prints its year.
  `tests/mpx3-threads` runs one static glibc program
  (`user/elf/threads.c`) on Linux and on PAX and holds its 48 lines
  byte-identical — ids, every `futex` answer, handler order and
  siginfo, the frame's layout, 200 signals into a spinning thread
  whose handler overwrites every register, restarts and -EINTR, wait
  statuses, a fork and an `execve` from a second thread — and soaks
  10,000 threads and 12,000 signals with the kernel's counters flat.
  `tests/mpx3-shell` gains `shell-long` (`ls -l /bin`, `stat`,
  `readlink`, `env`) and `shell-sigs` over serial and the PS/2
  keyboard (`trap … INT` and Ctrl-C, Ctrl-C at an empty prompt, Ctrl-C
  on `sleep 30`, a pipeline whose reader ends first, `unset`, `exec`).
  Named limits: one CPU; no job control (no process groups, sessions
  or stopped processes); no `sigaltstack`, `rt_sigsuspend`,
  `rt_sigtimedwait`, timers, `rseq` or `set_robust_list` (glibc
  tolerates both last); real-time signals do not queue; the
  sigcontext's selectors
  are PAX's (0x23, 0x1b); sixteen slots hold every thread of every
  process.

- **TCP (px23).** An unmodified static Linux program listens,
  accepts, connects, reads, writes, shuts down and closes TCP
  connections on PAX, and so do two programs built by wolf.
  `kernel/tcp` is RFC 9293's state machine in 64 control blocks:
  active and passive open (and SYNs that cross), in-order delivery with
  up to four out-of-order intervals kept in the receive buffer,
  cumulative acknowledgements, a window that is never taken back and a
  zero window probed, the MSS option sent and honoured and every other
  option skipped by name, FIN each way and half-close, resets accepted
  only at RCV.NXT (elsewhere in the window they draw an ACK), RFC
  6298's retransmission timer with Karn's rule (floor 200 ms, not the
  RFC's 1 s), RFC 5681's slow start, congestion avoidance, fast
  retransmit and fast recovery, a bounded listen queue, 2 x MSL of 60 s
  in a table of 32,768 entries, initial sequence numbers per RFC 6528.
  A connection's buffers are 65,536 bytes each way in frames taken when
  it is established and given back when it ends. `kernel/socket` gains
  the stream forms of the socket calls and `listen`, `accept`,
  `accept4` and `shutdown`, each refusal's errno the one Linux gave the
  same program; a write to a connection that is over is `EPIPE` and
  SIGPIPE, as a pipe's. **Loopback is below IP now** (`kernel/ip`): a
  datagram of any protocol for the station's own address or 127/8
  waits on a queue of 64 frames and is delivered before the sending
  call returns, with no device needed; `kernel/udp`'s own loopback
  retired onto it, and the kernel pings itself at start-up.
  `tests/mpx4-tcp` runs ten witnesses three ways — against
  `tools/net-peer --tcp`, a TCP of the tools' own that injects loss,
  duplication, reordering, corruption and scripted single faults;
  against QEMU's user-mode network and its TCP; and with no device —
  each held byte for byte to the same binaries on Linux under the same
  script, with 16 MiB transfers each way, 10,000 connections each way
  and over loopback, and every captured segment judged by
  `tools/pcap-net`. Not here: `poll`, `epoll`, a thread for wolf's
  runtime to wait with, window scaling, SACK, timestamps, a delayed
  ACK, path MTU discovery, keep-alives.
- **UDP and the socket system calls (px22).** An unmodified static
  Linux program sends and receives UDP datagrams on PAX. `kernel/udp`
  judges a datagram's length and its pseudo-header checksum (zero
  means the sender made none; a wrong one is counted and dropped),
  hands it to the socket bound to its port, and answers one nobody
  takes with destination unreachable, code 3, through px21's limiter;
  it holds 16 sockets, each with a 65,536-byte receive queue in frames
  of its own, a port table with Linux's ephemeral range, and loopback:
  a datagram for the station's own address or 127/8 is handed to the
  receiving side in the sender's call and never touches the wire.
  `kernel/socket` is the calls — `socket`, `bind`, `connect`, `sendto`,
  `recvfrom`, `getsockname`, `getpeername`, `setsockopt`, `getsockopt`,
  and `read` and `write` on a socket — with each refusal's errno the
  one Linux gave the same program. A socket is an open file's node, so
  `dup`, `fork` and close-on-exec treat it as they treat a pipe's end,
  and the last close frees it. A receive with nothing queued parks the
  thread until a datagram or the socket's `SO_RCVTIMEO`.
  `tests/mpx4-udp` runs eight witnesses (`user/net/`) from the
  initramfs on a new kernel, `kmain_sockets`, two ways — against
  `tools/net-peer --udp`, which is the whole network and holds every
  frame to its bytes, and against QEMU's user-mode network with
  `tools/udp-host` at the host's end and QEMU's own DNS server — and
  holds each program's output and exit status to the same binary's on
  Linux, run by `tools/linux-net` in a network namespace addressed as
  PAX is with the same `net-peer` script on a tap device. Named
  limits: no TCP; no `poll`, `select` or `epoll`; no `sendmsg`,
  `recvmsg` or `shutdown`; one option set (`SO_RCVTIMEO`), two more
  read; no fragmentation (a datagram over 1472 bytes is `EMSGSIZE`)
  and no broadcast sends (`EACCES`); ICMP errors that arrive reach no
  socket; no loopback below UDP; no DHCP.

- **IP and ICMP (px21).** PAX answers ping. `kernel/ip` judges every
  received IPv4 header in one place — length, version, header length,
  the RFC 1071 checksum, total length against the frame, a time to
  live of 0, fragments, sources that name no single host, the option
  list, the destination — and counts each drop under its own name; it
  sends one datagram a frame, DF set, on-link or by way of the gateway
  from an address, netmask and gateway given at boot. `kernel/arp` is
  now a cache: eight entries that age out after a minute, a request
  repeated a second apart and given up after the third, two frames
  kept for each address still unresolved. `kernel/icmp` answers echo
  requests with the data intact, sends the kernel's own (`ping` on the
  kernel command line: six to the gateway, each round trip printed)
  and answers a protocol nothing speaks with destination unreachable,
  at most once a second. QEMU's user-mode gateway cannot send an echo
  request to a guest, so `tests/mpx4-net` gained a way to boot with a
  socket netdev whose other end is a script, `tools/net-peer`: it
  plays an on-link host, the gateway and a host behind it, sends echo
  requests that must be answered byte for byte, dozens of malformed
  and unwanted frames that must not be answered at all, and then
  10,000 more echoes.
  `tools/pcap-net` no longer knows a script: it judges every captured
  frame by a model written from the RFCs, recomputes every checksum,
  rebuilds every frame PAX sent and holds the kernel's counters to the
  capture's, one by one. Named limits: no fragmentation or reassembly
  (a 1500-byte MTU; a payload over 1480 bytes is refused), no UDP, TCP
  or sockets, one echo waited for at a time, IP options never sent, a
  source-routed datagram refused, the address a kernel's constant.

- **virtio-net (px20).** PAX sends and receives Ethernet frames. The
  kernel walks the PCI bus through configuration mechanism #1
  (`kernel/pci`; the census is printed with `pci` on the kernel
  command line), finds QEMU's virtio network device, transitional or
  1.x-only, and drives it through the virtio 1.x interface: the PCI
  capabilities' registers mapped in the device slot, the status
  handshake, two feature bits taken (VERSION_1 and MAC) and every
  other declined, two 64-entry split virtqueues with their parts
  aligned as the specification orders (`kernel/virtio`,
  `kernel/net`). The device interrupts on the 8259 line the firmware
  routed it to, level-triggered; the handler only reads the cause and
  wakes a kernel thread (`kernel/netd`), which hands each frame to its
  protocol. The kernel-internal frame interface is `net.send`,
  `net.rx_take`/`rx_give` and counters by cause; ARP (RFC 826,
  `kernel/arp`) is its witness: PAX, as 10.0.2.15, answers the
  gateway's request and resolves 10.0.2.2. `tests/mpx4-net` holds
  QEMU's capture of the whole exchange to the expected frames byte by
  byte (`tools/pcap-net`), runs 10,000 request-and-reply exchanges
  with the frame allocator's and the heap's books flat, sends 25,000
  frames in two bursts, and boots with no device and with a
  legacy-only one: each a named line and no panic. No IP, no sockets,
  nothing user-visible yet. Named limits: INTx only (no MSI-X), one
  buffer a frame (no merged buffers, no offloads), a four-entry ARP
  table with no ageing, the address a boot-time constant.

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
- **wolf 0.2.27, a region across a switch, `/dev/tty0` and
  `/dev/console` (px21a).** pax builds with wolf 0.2.27 and lupin
  0.1.50, by archive digest; its three manifests that declare C list
  the `ffi` capability the release asks for. `kernel/sched` saves the
  freestanding runtime's ambient-region slot in the outgoing thread's
  record and restores the incoming thread's at every switch
  (`wolf_rt_ambient_get`/`_set`, through `kernel/heap`), so a kernel
  thread may hold a `region` open across a yield, a preemption or a
  wait and its allocations stay its own: `tests/mpx2-heap` H11 now
  asserts where the List lands, and H12 and H13 hold a region's bytes
  to a single-threaded control across preemptions and across a
  blocked `wait_all` and a sleep, with the heap's ledger at zero. The
  rule that remains: no allocation in an interrupt handler, and no
  region left open where a system call gives up its kernel stack.
  Every kernel now links `kernel/heap` and the runtime archive (the
  pair lives there). `/dev/tty0` and `/dev/console` open the console
  and answer its ioctls; Ubuntu's `beep`, built static from its
  source package by `tools/mkbeep` (the packaged binary is dynamic,
  and PAX has no loader for that yet), sounds 440 Hz and 880 Hz
  through them within 1% (`tests/mpx3-speaker` K7). wolf-lang#653 is
  still open at this pin; `kernel/net`'s literal stays.
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
