# PAX

A Linux-compatible operating system written in wolf: a kernel that runs Linux's userspace unmodified, and a userspace built in wolf.

PAX is a clean-room implementation of Linux's userspace ABI. It does not contain, translate or derive from Linux kernel source. See `CLAUDE.md` for the rule and `docs/SOURCES.md` for what each part was written from.

Users (P5, px38 to px47): PAX has accounts, root, `pax` (1000) and the service account `lobo` (990), in its image's `/etc/passwd` and `/etc/group`. There are no passwords yet and the image boots to root's shell; `su`, written in wolf (`user/su`), is root becoming a user, a user's `su` is refused as Linux refuses one who cannot authenticate, and a set-ID bit is not honoured, so privilege only drops. A process has Linux's real, effective, saved and file-system ids and a group list; a file has an owner, a group and a mode; and `open`, `exec`, every path walk, making, removing, renaming and linking a name, changing a mode, an owner or a time, signals, ports below 1024, raw sockets, the speaker, `/dev`'s nodes and `/proc`'s files are checked by Linux's rules, each rule measured against a real Linux (`tests/mpx5-users`, `tests/mpx5-accounts`). Since px47 every suite that runs programs on PAX — the tree, the shell, boreutils, Unix sockets, TCP, UDP, the speaker and lobo — runs them again as a user beside root, each run held byte for byte to the same binaries run as the same user on Linux. These checks are enforced for honest programs; not a boundary against an attacker: the kernel has never been fuzzed or audited, and it loads programs at fixed addresses. `login` waits for job control, and passwords for a memory-hard hash.

grep is scent (px64): `/bin/grep` is scent, grep in wolf (Track 15; `user/scent.pin`, `tools/mkscent`), byte-identical to GNU grep 3.12 (configured `--disable-perl-regexp`) in the C locale on its M1 options (the default syntax, `-E` and `-F` across the whole M1 interface) but for the differences rulings #115 to #117 publish and eight rows blocked upstream. `/bin/scent` is the unmodified static binary, built twice to one digest by scent's own toolchain (wolf 0.2.35, the std its archive bundles); `/bin/grep` is a symbolic link to it, which an image's archive can now carry (`tools/mkinitramfs`' `/PATH->TARGET`, cpio's link entry; the kernel's tree adopts it at boot as `symlink(2)` would make it); `/bin/egrep` and `/bin/fgrep` are scent's own wrappers, byte for byte, shell scripts run by `/bin/sh` (pelt) through the kernel's `#!`, which warn on standard error and run `grep -E` or `grep -F` from their own directory, so they work with `/bin` gone from `PATH`. A typed session of 52 commands (the default syntax with a backreference, `-E` classes and alternation, `-F` punctuation, `-i`, `-v`, `-c`, `-n`, `-b`, `-o`, `-w`, `-x`, merged context, `-m` with context, `-e` with `-f`, standard input and files, `-z`, the binary-file policy, statuses 1 and 2, the `-P` refusal, the wrappers' warnings and conflicts, `PATH` changes, the C locale with no `LANG` and no locale data, the three rulings' witnesses), as root and as `pax`, is byte-identical to the same binaries in a Linux container and holds 49 rows to GNU 3.12's answers, the pinned build's run as a black box (`tests/mpx5-scent`); every call scent makes (27 by name) PAX already served, but `set_robust_list` and `rseq`, -ENOSYS as for every glibc program. What a PAX user sees that GNU's grep would not show: `--help` and `--version` are scent's own prose; a diagnostic says `grep:` whatever name ran it (`/bin/grep --bad` says `grep:` where GNU says `/bin/grep:`; wolf-lang#899, #904); an argument that is not UTF-8 aborts in wolf's runtime with status 134 (wolf-lang#406), which pelt cannot even pass (its `$'\377'` is `?`) but a `#!` line can; `-r` and colour are not yet (scent's M2), refused by name.

The disk (px63): a virtio block device (`kernel/vblk`, on px20's transport), a block layer with a buffer cache (`kernel/block`), and ext2 read and written (`kernel/ext2`: the superblock, the groups, the bitmaps, inodes and their single, double and triple indirect blocks, directories, fast and slow symbolic links, owners past 65535 and times past 2038), mounted by the kernel from `/etc/fstab` (`user/fstab`: the disk at `/home`) as the tree's second store before the first program, write-back with a flusher every 5 seconds, written and marked clean at the halt and by root's `reboot(2)`, which resets the machine. `fsync`, `fdatasync`, `syncfs`, `sync`, `statfs` and `fstatfs` serve it. A host-made `mkfs.ext2` image reads on PAX as on Linux 7.2.8 line for line (`ls -l`, `stat`, `readlink`, `cat`, a 100 MiB file's sum, statfs), a write session leaves the tree Linux's does and `e2fsck -fn` finds it clean, and a note written before a reboot is read after it (`tests/mpx6-blk`, `tests/mpx6-ext2`). `/` is still the in-memory tree.

Mappings, FIFOs and locks (px62): `mmap` of a file of the tree, private (the file's own frames mapped read-only and a page copied at its first write, so a page not yet written shows a later `write(2)` as on Linux) and shared (every mapping, a forked child's and `read` and `write` of the file are one set of bytes, so `msync` has nothing to write), and shared memory (`MAP_SHARED|MAP_ANONYMOUS`, `/dev/zero`) across `fork`, with SIGBUS for a page past a file's end and a file cut under its mappings unmapped past its new end in every process; `mremap` with `MREMAP_MAYMOVE`, grown in place or moved without copying a byte (`MREMAP_FIXED` and `MREMAP_DONTUNMAP` refused by name), so the musl wolf's allocator grows its blocks on PAX as on Linux; FIFOs made by `mkfifo` and `mknodat` and opened by fifo(7)'s rules; and `flock` on open files. Two static probes print the same lines on PAX and on Linux as root and as a user (`tests/mpx3-maps`), and pelt's FIFO row runs as on Linux, 22 of 22 (`tests/mpx5-pelt`).

Job control (px48): process groups and sessions, the console as a controlling terminal (`TIOCSCTTY`, `TIOCNOTTY`, `TIOCGPGRP`, `TIOCSPGRP`, `TIOCGSID`), `kill` to a group, stops and continues and the waits that report them, Ctrl-C, Ctrl-\\ and Ctrl-Z for the console's foreground group only, the background rules (`SIGTTIN`, `TOSTOP`'s `SIGTTOU`), hangup and the orphaned group, and `/proc/<pid>/stat`, each measured against real Linux as root and as a user; a distribution's static Almquist shell (Ubuntu's `busybox-static`, `sh -i`) runs `sleep 100 &`, `jobs`, Ctrl-Z, `bg`, `fg`, `kill %2` and `wait` on PAX's console byte for byte as on Linux (`tests/mpx5-jobs`). The image's shell, pid 1, leads its session with the console as its terminal, as a getty would give it on Linux.

The pins at 0.2.34, aspen and lupin (px57): the kernel is built from wolf 0.2.34 with no source change and no byte of any section moved; a probe of 0.2.34's calls (`user/edwolf`: the fork and its `busy` rule, one wait over several descriptors, the terminal restored at exit, the syncs and the exclusive create, `realpath`, the nanosecond clock) and of s253's (`user/elf/hostq.c`) answers as real Linux under QEMU as root and as `pax`, but for what PAX does differently by name (its monotonic clock ticks every 10 ms; it calls itself `PAX`; it refuses every set of a limit); aspen, tree(1) in wolf (`/bin/aspen`), and lupin, the reference interpreter for wolf, built static for musl (`/bin/lupin`, with programs in `/usr/share/lupin`; ruling #110), run at the console byte-identical to Linux (`tests/mpx5-aspen`, `tests/mpx5-lupin`).

lope on PAX (px54, ruling #91 R4): lope, the directory jumper in wolf (the maintainer's gump ported and renamed; `user/lope.pin`, `tools/mklope`), is preinstalled as `/bin/lope`, and the console shell runs its hook before its first prompt: `/etc/pax-run` starts it as `/bin/env ENV=/etc/shrc /bin/sh -i -m`, and `/etc/shrc` (`user/shrc`) is `eval "$(lope init pelt)"`, run by pelt as POSIX's `$ENV` file, with pelt at `90d7c64` (sh21: `command_not_found_handle`). So `cd` records each directory, a word that names no command jumps to the directory lope knows by it (`etc` alone lands in `/etc`), `g -` goes back, `g` goes home and `gi` offers a numbered menu (PAX has no fzf); a typed session of all of it is byte-identical to the same binaries in a Linux container, as root and as `pax`, with no kernel change (`tests/mpx5-lope`). Every call lope makes is one PAX already served. **lope's store lives in memory**: `$HOME/.local/share/lope/store` (`/.local/share/lope/store` for root, whose `HOME` is `/`) in PAX's in-memory tree, kept while the machine runs and gone at reboot until PAX has storage. lope's repository is private for now, so pax's CI checks it out with the org's token.

Exec from the tree, and `#!` (px56): `execve` and `execveat` run any program of the tree its mode allows — copied, written, rewritten in place or unlinked while open since boot — with the mode rule and every refusal (ETXTBSY included) as Linux answers; `#!` interpreter lines as Linux reads them (one argument, the script's path appended, five deep), and ENOEXEC for a file with neither, so pelt runs a script with no `#!` itself: the maintainer's `echo 'echo hi' > Script/greet.sh; chmod +x Script/greet.sh; ./Script/greet.sh` prints `hi` on PAX, as root and as `pax`, byte for byte as on real Linux under QEMU and in a container (`tests/mpx5-jobs`' execs image).

The small fixes, two (px55): `/dev/fd` as Linux's link to `/proc/self/fd` (`readlink`, `lstat`, the listing, `ls -l /dev/fd/` and `cat /dev/fd/0`'s rows, as root and as `pax`, byte-identical to real Linux under QEMU and a container: `tests/mpx5-jobs`' fds image); `prlimit64`'s core limit soft 0 and hard unlimited, as Linux boots (PAX writes no core); `/proc/self/limits` (and `/proc/<pid>/limits`) in Linux's layout with PAX's values from the one table `prlimit64` reads, and `/proc/sys/kernel/core_pattern` reading `core` (`tests/mpx3-tree`'s tree probe: the layout held to Linux, the values to PAX's own text); mpx4-session's and lobo-session's host ports picked outside the ephemeral range (#86's race, in two more places); and mpx4-ready booting every way whatever an earlier one did, each its own verdict, with a CI dispatch that names its ways (`ways`).

The pins at 0.2.33 (px53): the kernel is built from wolf 0.2.33 (lupin 0.1.54 unchanged), PAX runs boreutils `cc64f68` (bu28: `timeout -s SEGV`, `-s RTMIN` and a host number ignore the signal and send it to timeout's own group, a command dead of a signal leaves timeout dead of it, `kill -L`'s row 0) and pelt `be1a75d` (sh19's leak and `cd` join), and a probe of wolf 0.2.33's five new signal calls (`user/sigwolf`: one meaning ignored or defaulted in the sending shape, the end by a signal, the core siblings, `text(0)`) answers as on Linux, as root and as `pax`, with no kernel change: the groups session and the probe byte-identical to real Linux under QEMU at the first boot, every pelt session as recorded at 0.2.32 (`tests/mpx5-jobs`). PAX writes no core, as Linux writes none at its boot's `RLIMIT_CORE` of 0.

The small fixes (px52): `eventfd` with `EFD_SEMAPHORE` as Linux serves it (a read takes 1 and leaves the rest; `tests/mpx4-ready`'s evprobe, held to the same binary on Linux); `/dev/stdin`, `/dev/stdout` and `/dev/stderr` as symbolic links to `/proc/self/fd/0`, `1` and `2` (`readlink`, `lstat`, the listing, and `stat` and `open` through each, as root and as `pax`, byte-identical to real Linux under QEMU and a container: `tests/mpx5-jobs`' fds image, and pelt's `> /dev/stderr` and boreutils' `readlink` and `cat /dev/stdin` in `tests/mpx3-tree`'s shell-inout sessions); a CI dispatch that names mpx5-jobs' images (`jobs_boots`), so a plant's red at a later image is seen in CI; and the one silent UEFI boot of mpx4-udp's user image (pax#86) found to be QEMU refusing its own port forward, the port taken in the host's ephemeral range between the probe and QEMU's bind: the network suites now pick ports outside that range.

The pins at 0.2.32 (px51): the kernel is built from wolf 0.2.32 and lupin 0.1.54, and PAX runs pelt's own job control (sh18: `jobs`, `fg`, `bg`, job ids, Ctrl-Z and Ctrl-C reaching the job alone, a background reader stopped, a job's group killed) and boreutils' `kill` to a process group and `timeout` (bu27: the command in timeout's own group, the group sent to at expiry) as Linux does, as root and as `pax`: 26 typed job-control sessions and a session of group sends and timeouts, each byte-identical to real Linux under QEMU, with no kernel change (`tests/mpx5-jobs`).

The descriptor table (px50): `/proc/<pid>/fd` and `/proc/<pid>/fdinfo` as Linux serves them — `readlink` of each kind of descriptor, `stat` and `open` through an entry, the listings, fdinfo's `pos`, `flags`, `mnt_id` and `ino`, who may read another process's — so boreutils' `cat` refuses an input that is its output on PAX exactly where it does on Linux, as root and as `pax`; a user's `rmdir` and `rename` of `/proc` and `/sys`; each measured against real Linux (`tests/mpx5-jobs`' fds image, `tests/mpx3-tree`'s shell-inout sessions).

The small gaps (px49): `pause`, `rt_sigsuspend` across a stop and another thread's take, TIOCSTI, `tcflush`, `tcdrain` and `tcsendbreak` on the console, SIGTTOU for a background `sendfile` or `splice` under TOSTOP, a socket's owner to `fstat`, `faccessat2`'s AT_SYMLINK_NOFOLLOW and AT_EMPTY_PATH, `fallocate`'s KEEP_SIZE and PUNCH_HOLE, and a user's `unlink("/dev")`, each measured against real Linux as root and as a user (`tests/mpx5-jobs`' gaps image).

Status: `/bin/play` plays an orchestra (px32): a part format of independent parts with dynamics, hairpins, articulation and 17 synthesised instrument timbres (`notes/px32-format.md`), 16+ voices in real time under TCG through the sound device (`tests/mpx3-orchestra`). Before that, PAX plays sampled sound (px30): QEMU's virtio sound device behind Linux's OSS `/dev/dsp`, so an unmodified static Linux program writes PCM and the capture holds exactly what it wrote, and `/bin/play` mixes a chord's pitches into one stream (`tests/mpx3-sound`). Before that, PAX waits for more than one descriptor (px24): `poll`, `epoll` (level- and edge-triggered, one-shot) and `eventfd` (`kernel/ready`, `kernel/event`), with `writev`, `sigaltstack`, `sched_getaffinity` and the rest of what wolf's hosted runtime and lobo were straced asking of Linux; a wolf server that serves twelve connections at once and a wolf client that waits run unmodified and print on PAX what they print on Linux, as do five probes and an echo server on `epoll` that holds 64 connections, is made ready on all of them at once and then serves 10,000 more (`tests/mpx4-ready`: over loopback, against `tools/net-peer --ready`, and through QEMU's user-mode network; the Linux side run by `tools/linux-net --ready`). A process has 128 descriptors, a machine 64 threads and 256 TCP connections. Before that, PAX's file tree is writable (px27): inodes in memory with the initramfs as their first contents, files that grow, shrink and have holes, directories that gain and lose entries, `rename` that replaces at once, a file that outlives its name while it is open, and a cap with `ENOSPC` at it — so boreutils' `mkdir`, `rmdir`, `rm`, `mv` and `cp` and pelt's `>` and `>>` run unmodified, a typed session that makes, copies, moves, lists and removes a tree (and is refused `rm -rf /`) is byte-identical to Linux, and one static glibc program prints on PAX what it prints on Linux's tmpfs about all of it, the Linux side in a throwaway container (`tests/mpx3-tree`). No disk. Since px36 a file also changes after it is made: hard and symbolic links, modes, times to the nanosecond and root's `chown`, so boreutils' `chmod`, `touch` and `ln` run unmodified and a typed session with them is byte-identical to Linux (`tests/mpx3-tree`'s `shell-changes`). Before that, PAX runs threads and delivers signals (px26): the current pelt and boreutils run unmodified — a second thread by `clone3` with `CLONE_THREAD`, `futex` wait and wake, handlers entered on a frame glibc expects and left by `rt_sigreturn` with every register and the x87/SSE/AVX state put back, `kill` and `tgkill`, Ctrl-C from the console as SIGINT for every process, `ls -l` with owners and dates from a wall clock — and one static glibc program prints on PAX what it prints on Linux about all of it (`tests/mpx3-threads`), with `ls -l /bin`, a `trap`, Ctrl-C on a running `sleep` and `exec` typed at pelt's prompt byte-identical to Linux (`tests/mpx3-shell`'s `shell-long` and `shell-sigs`). No job control, one CPU. Before that, PAX speaks TCP to Linux programs (px23): static Linux binaries — and two built by wolf — `listen`, `accept`, `connect`, read, write, `shutdown` and close stream sockets over `kernel/tcp` (RFC 9293's state machine, RFC 6298's retransmission timer, RFC 5681's congestion control, a bounded listen queue, time-wait), over the wire and over a loopback that is now below IP (`kernel/ip`), and an echo server, a client, 16 MiB transfers each way and 10,000 connections print on PAX what they print on Linux, and stay exact under loss, duplication, reordering and corruption injected by `tools/net-peer --tcp`, a TCP of the tools' own (`tests/mpx4-tcp`: against that script, against QEMU's user-mode network, and with no device at all; the Linux side run by `tools/linux-net --tcp`). No `poll` or `epoll` yet. Before that, PAX spoke UDP to Linux programs (px22): static Linux binaries call `socket`, `bind`, `connect`, `sendto`, `recvfrom`, `getsockname`, `getpeername` and the two option calls on AF_INET datagram sockets (`kernel/socket`) over `kernel/udp` — the pseudo-header checksum, a port table, a bounded receive queue a socket, a port unreachable for a datagram nobody takes, loopback that never touches the wire — and an echo server, a client, a resolver and four more witnesses (`user/net/`) print on PAX what they print on Linux (`tests/mpx4-udp`: against `tools/net-peer` and against QEMU's user-mode network, the Linux side run by `tools/linux-net`). No TCP, no `poll`. Before that, PAX answers ping (px21): it speaks IPv4 (`kernel/ip`: every received header held to RFC 791 and RFC 1122's rules with a counter per drop cause; a route that is on-link or by way of the gateway, from a boot-time address, netmask and gateway; DF set, a 1500-byte MTU, no fragments either way) over an ARP cache (`kernel/arp`: eight entries that age, a request retried three times a second apart, two frames kept per unresolved address), answers ICMP echo requests, sends its own and times the replies, and tells the sender of a protocol it does not speak so, at most once a second (`kernel/icmp`). An echo request reaches PAX from `tools/net-peer`, a script that is the whole network at the other end of a QEMU socket netdev; QEMU's capture is rebuilt byte by byte, every checksum recomputed, and held against the kernel's own counters (`tests/mpx4-net`). No UDP, no TCP and no sockets yet. Before it: PAX sends and receives Ethernet frames (px20): the kernel finds QEMU's virtio network device on the PCI bus (`kernel/pci`, configuration mechanism #1), drives it through the virtio 1.x interface (`kernel/virtio`, `kernel/net`: the capabilities' registers, two feature bits, two split virtqueues, INTx on the 8259) and, through a kernel-internal frame interface, speaks ARP with QEMU's user-mode gateway (`kernel/arp`): it answers a request for 10.0.2.15 and resolves 10.0.2.2, and QEMU's capture of the exchange is held to the expected frames byte by byte (`tests/mpx4-net`); no IP and no sockets yet. Before it: PAX plays music (px18): the PC speaker (the 8254's channel 2 gated through port 0x61, `kernel/speaker`) answers Linux's console ioctls KIOCSOUND and KDMKTONE, and `/bin/play`, a wolf program, sounds note files from `/usr/share/tunes` at pelt's prompt — `play mambo` (Paxito, an original mambo-flavoured tune), `play entertainer` (Joplin, 1902, public domain), `play scale`; a tone stops when the process that started it ends, and every halt silences the speaker; QEMU's speaker captured to a WAV file measures each note within 1% of its pitch (`tests/mpx3-speaker`). Before it: the console is drawn on the screen too (px19: the framebuffer Limine hands over, mapped write-combining through the PAT, a 160×50 text grid in Spleen 8×16 at QEMU's 1280×800, the common SGR colours, deferred wrap, scrolling and a steady cursor, fed the same bytes as the serial console and replayed from the first line; `TIOCGWINSZ` answers the grid when the screen is the console; every headless screendump equals a host-side reference renderer's picture of the same serial bytes, pixel for pixel; `tests/mpx3-screen`); pelt's pipelines, redirections and `cd` run on PAX as on Linux (px17: pelt `3e7516c`, whose spawn forks — a copy of the address space — and hears `execve` through a socketpair; pipes that block and end at their last writer, open files whose offset `dup` and a child share, `fcntl`, `chdir`/`fchdir`/`getcwd`, SIGPIPE's default; `ls /bin | wc -l`, `cat /etc/motd > /dev/null` and `cd /etc; cat motd` byte-identical to Linux in `tests/mpx3-shell`'s `shell-plumb`); the kernel builds from wolf 0.2.26 and lupin 0.1.49, the release archives by digest (px16, which also took out four workarounds 0.2.26 made unneeded: `m.K` for constants, `p[0].f = v` for a header's fields, `!` for masks, `-> never` for the panic path); the shell's image runs only programs built by wolf (px15: pelt and boreutils' `cat echo false head ls sleep tail true wc`, `ls` boreutils' own; `quiet` on the kernel command line keeps the per-program `user:` lines off the console; `tests/mpx3-shell`) on the console (px13: what a person types reaches a program — COM1's receive interrupt and the PS/2 keyboard (i8042, scancode set 1, a US layout) feed one line discipline, canonical and non-canonical, with echo, erase, kill, word erase and Ctrl-D, the settings a Linux pseudo-terminal starts with less ISIG and IXON; `read(0)` sleeps the thread until a line is ready; TCGETS, TCSETS, TIOCGWINSZ answered, other terminal ioctls refused by name; pelt, the POSIX shell in wolf, built static from its own tree, runs as PID 1 and answers its built-ins at a prompt, Ctrl-D ends it and the kernel halts; every typed session byte-identical to the same session on a Linux pseudo-terminal; `tests/mpx3-console`) on Linux programs (px12, M-PX3: boreutils' utilities, built from boreutils' own tree and linked static against a baseline glibc, run unmodified on PAX from the initramfs — `echo`, `cat` of a file, `wc`, `head`, `tail`, `pwd`, `sleep`, and `ls` of a directory (busybox-static's until px15) — their output and exit status byte-identical to the same binaries on Linux; `brk`, anonymous `mmap`/`munmap`/`mprotect`, `arch_prctl(ARCH_SET_FS)` with FS per thread, a descriptor table over the read-only initramfs and a synthetic `/dev`, `openat`/`read`/`pread64`/`lseek`/`fstat`/`statx`/`getdents64`, `getcwd`, `getrandom`, the clocks and `clock_nanosleep`; `tests/mpx3-boreutils`) on the loader (px10, M-PX3's next step: static x86-64 Linux executables, read from a `newc` initramfs Limine hands over as a module, run unmodified in ring 3 with the psABI's initial stack — argc, argv, envp and an auxiliary vector — and print what they print on Linux, byte for byte; `exit_group` 231; each thread's x87/SSE/AVX state saved and restored at every switch; a PIE, a dynamic program and a file that is not an x86-64 ELF are refused by name; wolf 0.2.25 and lupin 0.1.48 by archive digest; `tests/mpx3-loader`) on user mode (px09, M-PX3's first step: programs run in ring 3, each in an address space of its own with the kernel half shared, call the kernel through `syscall` with Linux's x86-64 numbers — `write` 1 to the serial console with every page of the buffer checked first, else -EFAULT; `exit` 60; anything else -ENOSYS — and return by `sysretq`; a page fault or a privileged instruction in ring 3 kills the program by name and the kernel goes on; SMEP and SMAP on; `tests/mpx3-user`) on preemptive kernel threads (px07, M-PX2's scheduler: the timer switches between threads, each on its own stack from frames above an unmapped guard; yield, sleep, exit; a spinlock on wolf's atomics; `tests/mpx2-sched`, wolf 0.2.24) and the kernel heap (px06: kernel code uses wolf's `List`, `Map`, string interpolation, capturing closures and `region`; wolf's freestanding runtime, `libwolf_rt_none.a` from the 0.2.24 archive, allocates through `wolf_alloc`/`wolf_free`, which PAX writes in wolf over its frames and paging, `kernel/heap`, PML4 slot 384: page runs and eight size classes; eight rounds of such code leave no block behind and the heap does not grow after the first, and a double free, a free outside the heap, running out and a page fault in the heap each panic by name, `tests/mpx2-heap`) on interrupts (kw10, M-PX2's interrupt and timer pieces) on paging (px03), physical frames (px02) and first light (M-PX1, px01). Every kernel loads its own GDT, TSS (with an IST1 stack for the double fault) and IDT before anything else (`kernel/gdt`, `kernel/idt`); all 32 exceptions and the 8259's 16 lines enter through `boot/isr.S`'s trampolines into wolf (`kernel/interrupts`, `[abi.interrupt]`), which panics by name (`PANIC page fault vector 14 error … cr2 …`), lets a breakpoint return, and counts the PIT's ticks (`kernel/timer`, through the local APIC's LINT0, `kernel/apic`) — each read back from the halted machine through QEMU's monitor (`tests/mpx2-interrupts`). wolf is the 0.2.23 release archive, fetched by digest (px05; kw08's packed structs and `offset_of`, kw09's module state and `extern "c" let`, all in a release), and `serial`, `frames` and `paging` use them: module `const`s, the allocator's state address in a module `var`, its header at `offset_of`. The kernel builds its own x86-64 four-level paging structures from its frame allocator (`kernel/paging`): its image mapped one permission per section (text read-execute, rodata read-only, data and bss read-write no-execute), Limine's HHDM kept for RAM (without a writable alias of the image), nothing in the lower half; it switches CR3 to them, maps and unmaps pages with INVLPG, and a write to its own text faults — each read back through QEMU's monitor (`tests/mpx2-paging`). The kernel's frame allocator (`kernel/frames`, two bitmaps over Limine's memory map, its state in frames it takes for itself) hands out every usable frame above 1 MiB exactly once and takes them back, and panics by name on a double free or a free of a frame never usable (`tests/mpx2-frames`). (From px02 to kw10 wolf was built from source, `eb955c3b` then `6a4e6151`, for features no release carried; px05 returned to the archive.) The wolf kernel owns the serial console (a 16550 driver in wolf), prints what Limine handed it (bootloader, firmware, memory map, HHDM offset) and halts; a trap reaches its panic path, which prints `PANIC <kind> <file>:<line>` and halts. Both of wolf's compiling tiers, under BIOS and UEFI (`tests/mpx1`). The harness's assembly proof (`tests/proof`) and M-KW's first wolf kernel (`tests/mkw`) still run. The plan lives in the wolf planning repository under `sprints/pax/`.

Licence: GPL-3.0, with the wolf Training Data Permission (`LICENSE-TRAINING-DATA`).

## Layout

    kernel/   the wolf kernel (serial, log, boot_info, frames, paging, panic;
              kernel/README.md), its wolf.pkg and the wolf/lupin pin
    boot/     boot-protocol glue: the Limine pin and config, the kernel's
              entry and requests, port I/O, the control registers, the
              interrupt trampolines and the descriptor tables' storage
              (start.S, io.S, cpu.S, isr.S, kernel.ld), and the assembly proof under
              boot/stub/
    user/     the first user programs (px09): flat assembly blobs the
              kernel copies into each process (programs.S); elf/ (px10);
              boreutils.pin and mpx3-boreutils.run (px12: the boreutils
              tree M-PX3 runs and the commands it runs); pelt.pin and
              console/ (px13: the shell PAX runs as PID 1, the typed
              sessions); play/ (px18: the note-file player, wolf) and
              tunes/ (its note files); net/ (px22: the eight UDP
              witnesses, C; px23: the eight TCP ones, C, and two in
              wolf) and mpx4-udp*.run, mpx4-tcp*.run (the commands
              tests/mpx4-udp and tests/mpx4-tcp run); lope.pin and
              shrc (px54: lope, preinstalled, and the console shell's
              $ENV file, its hook); fstab (px63: the images' mount
              table, the disk at /home); scent.pin (px64: the scent
              tree PAX carries as /bin/scent, /bin/grep a link to it,
              /bin/egrep and /bin/fgrep)
    tools/    the harness: fetch-limine, fetch-wolf, fetch-lupin,
              build-stub, build-kernel, mkimage, qemu-run, qemu-halt
              (--type: a typed session, px13; --no-screen, px19; --qemu, px18),
              qemu-fault, qemu-gdb, expect-serial, mkuser, mkboreutils,
              mkpelt, linux-run, linux-tty, mkfont and screen-ref (px19:
              the glyph table, the reference renderer), mkplay and
              wav-notes (px18), mkbeep (px21a: Ubuntu's beep from its
              source package, linked static), pcap-net (px20, px21: a capture held to
              what PAX must send, byte by byte), net-peer (px21: the
              other end of a socket netdev), gateway-probe (px21: what
              QEMU's user-mode gateway answers on this host), paxnet.py
              (px21: what the three share), mknet, linux-net and
              udp-host (px22: the UDP witnesses built; their run list on
              Linux in a namespace addressed as PAX is; the host's end
              of QEMU's user-mode network), paxtcp.py and tcp-host
              (px23: a TCP of the tools' own, with faults; the host's
              end of QEMU's network for TCP), mkprobes (px26, px27: the
              static C probes), linux-tree (px27: a session's Linux
              side in a throwaway container, its root a tmpfs: for
              programs that remove files), mklope (px54: lope static,
              from a clone of its private tree), e2fs, mkdisk, e2tree,
              linux-blk, mkdiskprobe and blk-pattern (px63: e2fsprogs
              from a container pinned by digest; a reproducible ext2
              image, empty, a home or a tree; an image's tree as debugfs
              lists it; the host's Linux on QEMU with the image as its
              disk; the disk probe and /bin/reboot; the self-test's
              pattern read from the host), mkscent (px64: scent static,
              built twice to one digest by its own toolchain, and its
              two wrappers)
    font/     the screen's font (px19): Spleen 8x16, BSD-2-Clause, with
              its licence
    tests/    scripted QEMU tests: proof, mkw (with M-KW's frozen kernels
              in mkw.d/), mpx1, mpx2-frames, mpx2-paging, mpx2-interrupts,
              mpx2-sched, mpx3-user, mpx3-loader, mpx3-boreutils, mpx3-console,
              mpx3-screen, mpx3-speaker (px18), mpx3-threads (px26), mpx3-tree (px27), mpx3-sound (px30), mpx4-net (px20, px21), mpx4-udp (px22), mpx4-tcp (px23), mpx5-lope (px54), mpx6-blk and mpx6-ext2 (px63), mpx5-scent (px64), gdb-attach,
              expect-serial-selftest
    docs/     BOOT.md (the boot protocol, argued), SOURCES.md (the
              consulted-sources log), ABI notes as they come
    notes/    one note per lane: its contract and evidence

## Booting it

PAX boots through the **Limine** protocol from one hybrid ISO that boots under BIOS and UEFI (`docs/BOOT.md` says why). Limine itself is fetched from its release by sha256 digest, never built here.

```sh
tools/fetch-limine                         # Limine 12.9.1, digest-checked, into .pax-cache/
tests/proof                                # build the stub + ISO, boot it under BIOS and UEFI, assert
tools/qemu-run --firmware uefi build/pax-stub.iso; echo $?    # 33 = the stub's success code
tools/expect-serial build/serial.log PAX "firmware: uefi"
tools/qemu-gdb build/pax-stub.iso build/stub/pax-stub.elf     # gdb, frozen at reset
PAX_WOLF=$(tools/fetch-wolf) tests/mpx1    # M-PX1: first light, both tiers, BIOS and UEFI
PAX_WOLF=$(tools/fetch-wolf) tests/mpx2-frames   # px02: the frame allocator, both tiers, BIOS and UEFI
tests/mpx2-frames --images build/mpx2      # boot them elsewhere (hasu under KVM)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx2-paging   # px03: paging, read back through QEMU's monitor
PAX_WOLF=$(tools/fetch-wolf) tests/mpx2-interrupts   # kw10: named panics, int3, #DF on IST1, the timer
PAX_WOLF=$(tools/fetch-wolf) tests/mpx2-sched   # px07: threads switched by the timer, sleep, exit, the lock, the guard
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-user   # px09: ring 3 — syscall write/exit, faults killed by name, SMEP/SMAP
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-boreutils   # px12, M-PX3: boreutils (ls too, px15) on PAX against Linux (sudo for the chroot)
tests/mpx3-boreutils --images build/mpx3-boreutils  # boot them elsewhere (hasu under KVM), Linux's side carried along
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-console   # px13: typed sessions (ask, pelt as PID 1) through COM1 and PS/2, against Linux
tests/mpx3-console --images build/mpx3-console    # boot them elsewhere (hasu under KVM)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-screen   # px19: screendumps against tools/screen-ref, the scroll's cost, winsize
tests/mpx3-screen --images build/mpx3-screen      # boot them elsewhere (hasu under KVM)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-speaker   # px18: play's scale through QEMU's speaker to a WAV, every pitch measured
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-sound     # px30: virtio sound and /dev/dsp; static OSS witnesses and play's mixed mode, captured at 48 kHz
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-orchestra # px32: play's part format, judged on the host (play -o) and from QEMU's capture
tools/linux-sound OUT PROG -- 'CMD'              # px30: the same programs on this host's Linux under QEMU with a sound device
PAX_WOLF=$(tools/fetch-wolf) tests/mpx4-net   # px20, px21: virtio-net, ARP, IPv4 and ICMP echo; QEMU's gateway and tools/net-peer; the captures byte by byte
tools/gateway-probe 127.0.0.1                # px21: what this host's QEMU gateway answers to ARP and ICMP echo, with no guest
tests/mpx4-net --images build/mpx4-net --accel kvm   # boot them elsewhere (hasu under KVM)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx4-udp   # px22: UDP and sockets; eight witnesses against tools/net-peer and QEMU's user network, each held to Linux (needs root for the Linux side: tools/linux-net)
tests/mpx4-udp --images build/mpx4-udp --accel kvm   # boot them elsewhere (hasu under KVM)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx4-tcp   # px23: TCP; ten witnesses against tools/net-peer --tcp (faults and all), QEMU's user network and no device, each held to Linux (needs root for the Linux side)
tests/mpx4-tcp --images build/mpx4-tcp --accel kvm   # boot them elsewhere (hasu under KVM)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-tree   # px27: the writable tree; a static probe and a typed session against Linux's tmpfs, a soak and a fill (the Linux side runs in a throwaway container: docker or podman; nothing under test runs on the host)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-maps   # px62: mremap, file and shared mappings, FIFOs and flock; two static probes against Linux's tmpfs, root and a user (the Linux side in throwaway containers)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx6-blk    # px63: the virtio block device's self-test: a pattern written, flushed, read back and read from the host; read-only; no disk
PAX_WOLF=$(tools/fetch-wolf) tests/mpx6-ext2   # px63: ext2 read, written and rebooted, held to Linux 7.2.8 on QEMU (live where the kernel is readable, else the record) and to e2fsck -fn (e2fsprogs in a container: docker or podman)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx5-scent  # px64: scent as /bin/grep (an archive link), egrep and fgrep through pelt's #!, typed as root and pax, held to the same binaries in a container and to GNU 3.12's answers
tools/mkdisk --home 128M pax-home.img          # px63: the disk an image mounts at /home (pax/ for the user pax), reproducible under SOURCE_DATE_EPOCH
tools/gateway-probe --dns dns.google         # px22: what this host's QEMU DNS server answers, with no guest
tools/qemu-halt --elf K.elf --marker halt --cmd 'info tlb' K.iso   # monitor answers on the halted machine (K.log.cmd1)
tools/qemu-fault --marker 'write: .*' K.iso                        # a kernel that must fault: CR2 from the stopped machine
tests/mpx1 --images build/mpx1             # boot ISOs built elsewhere (any host with QEMU)
tools/qemu-halt --elf build/mpx1/native/kmain.elf --marker halt build/mpx1/native/kmain.iso   # is it halted?
PAX_WOLF=$(tools/fetch-wolf) PAX_LUPIN=$(tools/fetch-lupin) tests/mkw   # M-KW: the first wolf kernel, both tiers
tests/mkw --images build/mkw               # boot ISOs built elsewhere (any host with QEMU)
```

`tools/qemu-run` runs QEMU headless (`-nographic`, COM1 to a file, `-no-reboot`, a timeout, `isa-debug-exit` at port `0xf4`) and returns QEMU's status: `(v << 1) | 1` when the kernel writes `v` to the exit port, 0 for a reset or triple fault, 124 for a timeout. A kernel that halts never exits QEMU, so `tools/qemu-halt` boots it with QEMU's monitor on a pipe and, after the kernel's last line, holds it to RIP inside `pax_halt`, IF clear and HLT=1 at two probes a second apart, with no further serial output. Each tool's header comment states its usage; `qemu-run` and `qemu-gdb` print it with `--help`.

## Seeing the screen (px19)

The harness boots headless; to see PAX's screen, give QEMU a window. On
macOS (Homebrew's QEMU, TCG):

```sh
qemu-system-x86_64 -machine q35 -cpu max -m 256M -display cocoa \
    -serial file:serial.log -nic none -no-reboot -cdrom IMAGE.iso
```

(`-display gtk` or `-display sdl` on Linux, where `-accel kvm` makes it
fast.) The window is QEMU's display device: Limine hands PAX its
framebuffer, PAX draws the console there from its first line, and the
window's keyboard is the PS/2 keyboard px13's console reads, so a shell
image (`tests/mpx3-console`'s `console-pelt.iso`, `tests/mpx3-shell`'s
`console-shell.iso`) is typed into from the window; COM1 still gets
every byte (`serial.log`). With `-display none` the screen is drawn
where nobody sees it, and `-vga none` (`tools/qemu-run --no-screen`)
boots a machine with no display at all: the console is serial only.

## A disk that outlives the boot (px63)

Everything an image holds is in memory and gone at the next boot, but
for a disk: give QEMU an ext2 image as a virtio block device and the
kernel mounts it where the image's `/etc/fstab` says (`user/fstab`,
the playground's: `/home`):

```sh
tools/mkdisk --home 128M pax-home.img
qemu-system-x86_64 -machine q35 -cpu max -m 512M -display cocoa \
    -serial file:serial.log -nic none -cdrom IMAGE.iso \
    -drive file=pax-home.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0
```

Without `-no-reboot`, root's `reboot` restarts the machine and the same
disk boots again; `e2fsck -fn pax-home.img` and `debugfs` read it on the
host between boots (the file is the file system: no partition table).

## The dev image (px60)

The dev variant adds a musl-static `wolf` at `/usr/bin/wolf` and its
pinned standard library at `/usr/share/wolf/std`. It leaves the base
image unchanged. `tools/mkwolf`, `tools/mkwolf-std` and `tools/mkdev`
build and stage those additions; `user/wolf.pin` records the source,
portability patch and recipe, and `user/wolf.sums` records the bytes.
The shell environment selects the std tree through `WOLF_STD`. The full
dev ISO also carries static lld 17, a link-only `cc` front end, and musl's
binary CRT/libc inputs (`user/wolf-link.sums`). It can build and run native
wolf programs; the link front end is not a C or assembly compiler. Since
px64 it also carries scent as `/bin/grep` (the unmodified `/bin/scent`,
the link, `/bin/egrep` and `/bin/fgrep`) and `tests/mpx5-scent`'s
fixture at `/usr/share/scent` (`cd /usr/share/scent; grep -n -C1 cat
words.txt`); its recipe is `notes/px64/dev-iso/`.

At the dev console, write a program in your home directory and use:

```sh
wolf fmt hello.lu
wolf fmt --check hello.lu
wolf conform-run --json --phase=typecheck hello.lu
wolf conform-run --json --checked hello.lu
wolf build hello.lu
./hello
```

At 0.2.34 there is no `wolf check` command. `wolf run --checked` is a
native build, **not** the checked machine; it requires a native link
step. `wolf build --no-cache --emit=obj hello.lu -o hello.o` emits a
native object without a linker. The default backend is Cranelift;
`--release` still needs external clang, which this image does not carry. The dev-image experiments and
remaining link requirements are recorded under `notes/px60/`.

`tests/mpx5-wolf` holds root and `pax` sessions byte for byte to the same
binaries on Linux. It also checks independent command/verdict witnesses,
so agreement on a broken compiler or missing std tree cannot pass. Its
fast CI root deliberately omits the native link bundle and checks the
missing-tool errors. `--only native --images DIR` validates the separate
live native probe's Linux/PAX recordings. The final dev ISO was tested
with 2 GiB RAM; lld's file-mapping refusals are visible, but its read/write
fallback links the measured programs successfully.

## Hosts

| host | build an image | boot one (`qemu-run`, `tests/proof --image`) | gdb (`qemu-gdb`) |
|---|---|---|---|
| linux x86-64 (CI's ubuntu, the pool) | yes: binutils, cc, make, curl, xorriso | yes: `qemu-system-x86_64`; OVMF for UEFI; KVM used when `/dev/kvm` is usable | yes: gdb |
| macOS arm64 | **no**: no x86-64 ELF binutils or xorriso in the base system | **yes**, TCG: Homebrew's `qemu`, which ships its own UEFI firmware; CI's `macos-run` job boots the linux-built ISO on every push | no gdb in the base system; `tools/qemu-run --gdb 1234` and lldb's `gdb-remote 1234` by hand |

Where each runs today (2026-10-02, px00):

- **CI**: `ubuntu-latest` with QEMU 8.2.2, OVMF and xorriso from apt (TCG); the `macos-run` job boots the same ISO, checked by digest, with Homebrew's QEMU 11.1.1 (TCG).
- **hasu** (NixOS): nothing system-wide is needed. QEMU and xorriso come from a nix-shell, and the UEFI firmware from nixpkgs' OVMF; use the **combined** `OVMF.fd` with no separate vars file, because split `OVMF_CODE.fd` + `OVMF_VARS.fd` hangs in the firmware under KVM there (5 of 6 boots):

  ```sh
  ovmf=$(nix-build --no-out-link '<nixpkgs>' -A OVMF.fd)/FV
  PAX_OVMF_CODE=$ovmf/OVMF.fd PAX_OVMF_VARS= \
    nix-shell -p qemu xorriso --run 'PAX_QEMU=$(command -v qemu-system-x86_64) tests/proof'
  ```
- **kasumi** (CachyOS): QEMU 11.1.1, xorriso and OVMF since the 2026-10-02 upgrade; the kernel builds (wolf, the objects, the ISOs) and boots here (TCG); px01 booted the same ISOs on hasu under KVM (`tests/mpx1 --images`).
- **macOS** (nomad-1, arm64): `tests/proof --image` on an ISO built elsewhere, as CI's `macos-run` does.

The QEMU binary is `$PAX_QEMU` (default `qemu-system-x86_64` on `PATH`) and the UEFI firmware `$PAX_OVMF_CODE` / `$PAX_OVMF_VARS`, so every host supplies its own. `tools/mkimage` is reproducible: every date in the ISO is `SOURCE_DATE_EPOCH`, default the last commit's time, so one commit builds one digest.

The harness never installs anything. A missing tool is named and the tool stops. The UEFI leg looks for OVMF at the distro paths in `tools/lib.sh`, or `PAX_OVMF_CODE` / `PAX_OVMF_VARS`; without it `tests/proof` skips that leg loudly, unless `PAX_REQUIRE_UEFI=1` (CI), when it fails.
