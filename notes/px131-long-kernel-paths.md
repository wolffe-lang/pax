# px131 — what the kernel holds too long

A program that only wrote bytes to its own console starved an installed machine: its ssh session froze, pings took
2 s, a new ssh connection timed out at the banner. The console's own lane attributed that one path. This lane asked the
general question: is that a sign the kernel cannot handle much at once? It is, and the reason is one rule, not one path.

- **The rule:** every system call and every interrupt handler runs with interrupts off from entry to return, and a
  call gives up the processor only where it blocks. So any call that runs long holds everything: the tick, the network
  device's interrupt, the network thread, the scheduler and every other process. The console write is one such call.
  Measured under KVM, a user can hold interrupts off for 3 s with one munmap, 1.5 s with one getrandom, 0.4 s with one
  read of /proc/self/mem or one console write, 0.36 to 0.66 s with one write to a file, and up to 1 s with one fork;
  from the code, minutes to hours with larger arguments, and seconds to minutes when a disk stops answering.
- **What it costs:** a host pinging the machine every 5 ms waits as long as the longest call (1.5 to 3.1 s worst under
  those loads); a 1 ms sleeper wakes up to 3 s late; the tick clock keeps 6 to 9 % of real time, so every clock,
  sleep and timeout the kernel counts in ticks runs slow. Linux in a virtual machine of the same shape keeps the same
  loads under 2 ms (one console write at 145 ms and one large file write at 94 ms are its worst).
- **A second cost, without any long call:** one process that only computes makes every network round trip 27 ms in
  the median and 42 ms at worst (Linux: 0.6 and 1.5 ms), because the network thread waits behind its quantum and the
  answering process behind it again.
- **Built here:** three per-unit fixes, each seen red first under the new guard: munmap (and a truncate's cut of a
  file's mappings) visits only the pages that are mapped, getrandom fills a page at a time and gives at most 16 KiB a
  call, and /proc/<pid>/mem copies in blocks. Their loads went from 27 to 106 times the scheduler's own share to 1.0.
- **Proposed** (section 10): the bound, the clocks counted from the clock, the network's and the keyboard's wake-ups
  run at once, deferred work as a kernel service, interrupt-driven block I/O, reschedule points inside long calls, and,
  with the second processor, interrupts on in system calls; in that order.

Footprint: cross-cutting (the entry paths `boot/isr.S`, `boot/sched.S`, `boot/user.S`; `kernel/sched`,
`kernel/paging`, a new `kernel/latency`; `kernel/vm`, `kernel/user`, `kernel/process`, `kernel/trace_mem`,
`kernel/procfs`, `kernel/kmain_console.lu`; `.github/workflows/ci.yml` gains the `mpx6-latency` job,
`tools/ci-tiers.map` and `tests/ci-plan` its paths; new `tests/mpx6-latency`, `tests/mpx6-latency.d/`,
`tools/mklatprobe`, `user/elf/latprobe.c`, `user/elf/latinit.c`).

## 1. Forbidden, and what was read

- **The clean room.** No kernel's, driver's or C library's source was read. The rule and the inventory are read from
  PAX's own code; Linux was run as a black box in a virtual machine. Sources: the Intel SDM vol. 3A §6.8.1 (IF, CLI,
  STI), §6.10 to §6.14 (gates, the frame), vol. 3B §18.17 (the time-stamp counter), vol. 2 (RDTSC, RDRAND, CPUID,
  SYSCALL, SYSRET); getrandom(2), proc_pid_mem(5), munmap(2), clock_nanosleep(2), netdevice(7); QEMU's documentation of
  `-netdev user`; RFC 862. `docs/SOURCES.md` (px131) lists them.
- **Hosts.** A Linux build host (Intel Core i7-12700KF) for every build and boot, in an Ubuntu 24.04 container
  (QEMU 8.2.2, OVMF, gcc 13.3) with KVM, on a light slot (two P-cores); the build Mac for git only. QEMU only.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer; the
  console's drawing, the kernel log, the process slots and any second-processor support are named, not touched.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `0e2843cf` | the fresh clone's `git rev-parse` |
| wolf | 0.2.35 (`kernel/wolf.pin`) | `tools/fetch-wolf`, by digest |
| Limine | 12.9.1 | `tools/fetch-limine`, by digest |
| Linux for the comparison | the build host's own kernel, 7.2.4 (`CONFIG_PREEMPT_LAZY`, `CONFIG_HZ=1000`), its virtio modules | run, never read |
| the console's lane's report | its branch at `bbe91e16` (not merged) | read as a report and checked against trunk's code (section 3) |

## 3. The rule as it stands, from the code

**When an interrupt can be taken.** Every IDT gate is an interrupt gate (`kernel/idt`: type 0xE), so IF is clear in
every handler. SYSCALL clears IF through FMASK (`kernel/user`: `FMASK_VALUE` 0x44700; `boot/user.S`
`pax_syscall_entry`), and the call runs in `kernel/interrupts` `pax_interrupt` → `route` → `kernel/user` `syscall` →
`serve` → `dispatch` with IF clear to SYSRETQ (`boot/isr.S` `pax_sysret`) or IRETQ. Nothing on those paths sets IF.
Kernel code sets IF in three places only: `boot/sched.S` `pax_irq_restore` (`kernel/sync` `irq_restore`, `release`,
`enable`), `boot/isr.S` `pax_wait` (STI; HLT; CLI, used only by test kernels: `kmain_timer`, `kmain_metal`,
`pax_tour`), and a frame resumed with IF in its RFLAGS: ring 3, the idle thread's HLT loop, a kernel thread's first
frame (`kernel/sched` `first_frame`: 0x202).

**What is preemptible.** Ring 3, and kernel threads (`netd`, the network's clock, `dhcpd`, the flusher, `usbd`,
kmain's own) outside their `irq_save`/`acquire` sections. No system call and no handler is: a call gives up the
processor only by blocking (`sched.block_pipe`, `block_input`, `sleep_current`, `futex_wait`, `vfork_wait`,
`suspend_current`, `yield_current`, the ends), which saves its frame, mostly rewound to run the call again, and
returns another thread's.

**The scheduler.** `kernel/sched` `preempt`, from the tick, wakes the sleepers (a scan of the 64 slots) and switches
only when the running thread has used its two-tick quantum (or is idle). `kick`, after a device's interrupt, switches
only away from the idle thread. The run queue is one FIFO; `wake_net`, `wake_input` and `wake_pipes` put the woken at
its tail.

**What is held.** The eight `kernel/sync` locks (console, heap, net, arp, ip, icmp, udp, tcp) clear IF and never
spin: on one processor, IF off is the lock, and a call needs no lock at all because nothing can run beside it. The
kernel's scratch is global on that ground: `pax_kbuf` (a call's paths), `pax_argbuf` and `pax_execbuf` (exec's
strings), `pax_syscall_state` (the user stack pointer at entry), and `kernel/uaccess`'s rule that nothing unmaps a
checked page during a call.

**The tick.** The local APIC timer, periodic at 100 Hz, vector 32 (`kernel/timer`). Its handler counts the tick, reads
the clock, acknowledges, ends a speaker tone, polls xHCI's timers, drains the pointer's records (drawing the pointer),
takes the console's signals, wakes console readers and calls `preempt`. Anything with IF clear delays it; one tick
waits in the APIC, every further tick due in the same stretch is lost.

**Network receive** is done in a kernel thread. The device's interrupt (`net.irq`) only acknowledges and calls
`sched.wake_net`; `netd` takes each frame, judges it and copies it into its socket (`tcp.input`, `udp.input`), which
wakes the reader (`wake_pipes`), whose rewound call then runs again and copies it out. Loopback traffic is delivered by
the sender's own call (`netd.drain` at the end of every call) and by the network's clock every tick.

**Storage** completes nothing by interrupt: virtio-blk, NVMe, AHCI and USB storage poll with IF clear, each request up
to its timeout (`vblk`/`nvme` `SPIN`, AHCI 30 s and 120 s for a flush, USB 30 s and 60 s), and the flusher thread
writes under `irq_save`.

**The clocks.** CLOCK_MONOTONIC is the tick count times 10 ms (`kernel/user` `now_ns`), CLOCK_REALTIME the RTC at boot
plus the same (`wall_ns`); a sleep, a poll's and a receive's timeout, a futex's deadline end on a tick; TCP's timers
and ARP's ageing turn on the network clock's `sleep(1)`; DHCP's lease is counted in ticks. Only the kernel's own device
waits read the clock (`kernel/clock`: the HPET, else the PM timer).

The console's lane's report holds against this code: a console write draws inside its call (`kernel/user` `write`,
`serial.put` a byte, `screen.put` in it), so one write is one stretch with interrupts off, and after it `preempt`
waits out the quantum while `netd` waits at the queue's tail.

## 4. The prediction, scored

The prediction (`notes/px131/prediction.txt`, `e2ab8d7a`) was committed before the instrument and any change.

| # | predicted | found |
|---|---|---|
| P1 | the five worst: console write (seconds a MiB), fork (0.3-1 s a GiB), a file write (50-200 ms for 256 MiB), exit/munmap/exec (tens to hundreds of ms a GiB), a polled sync | **partly wrong.** The console, fork and the file write are there, the file write worse than predicted (4-5 ms a MiB: 359 ms for 64 MiB). Missed: munmap of an empty range (3 s for 1 TiB, any length up to 128 TiB), getrandom (1.5 s for 8 MiB: a VM exit every 8 bytes), /proc/self/mem (0.4 s for 8 MiB: a page walk a byte). Exit and munmap of real memory are tens of ms (39 ms for a 128 MiB child's exit). The polled sync is confirmed from the code, not loaded |
| P2 | wake-up lateness about the longest call plus up to two quanta | right: 3.09 s beside a 3.06 s munmap, 0.75 s beside 0.37 s writes (two writes back to back) |
| P3 | an echo waits about two of the hog's calls a hop | right for the host's ping: 1.47 s beside 0.37 s console writes; and a hog with no calls costs 27 ms a round trip (not predicted) |
| P4 | lost ticks slow every tick-counted clock and timeout | right: 6-9 % of ticks kept beside the worst loads |
| P5 | Linux within a few ms of idle | right but for two outliers: a console write (145 ms, once) and a 128 MiB file write (94 ms, once) |
| P6 | the cheap fixes are local loops that can stop or skip | right: all three are per-unit costs (an empty table walked a page at a time, CPUID a word, a page walk a byte) |
| P7 | the guard's red three: console, fork, file write | **changed**: those three are structural (or the console's lane's), so the guard bounds the three fixed here and measures those as pending rows (decision 9) |

## 5. The inventory

Every kernel path whose running time grows with a size a user controls or a device decides, read from the code and
ranked by its worst case. "IF" is off for every row (a call or a handler), unless it says a kernel thread; no row can
be switched away from part-way unless it says it blocks. Measured rows carry the table's figure (section 7).

| path (file: function) | entered by | bound | per unit | worst a user (or a device) can cause |
|---|---|---|---|---|
| `vm`: `munmap` → `unmap_range`; `madvise`, `msync`, `mprotect`, `mremap`'s shrink | munmap … | any range below 128 TiB, holes included | a 4-level walk a page | **measured 3.1 s for 1 TiB of nothing**; 128 TiB minutes; fixed here for munmap and truncate |
| `vm`: `pick`, `place` | mmap, mremap | the request's length | a walk, 256 reservations and 192 records scanned a page | 128 MiB: part of the 60 ms measured; a huge PROT_NONE reservation: hours |
| `vm`: `cut_maps` from `files.resize` | truncate, ftruncate, O_TRUNC | every mapping of the file in 64 slots, a file mapped up to 128 TiB past its end | a walk a page | minutes; fixed here |
| `trace_mem`: `transfer` | read/write of /proc/<pid>/mem | 0x7ffff000 a call | a page walk a byte | **measured 0.39 s for 8 MiB**; 2 GiB about 100 s; fixed here |
| `user`: `getrandom` → `process.random_word` | getrandom, /dev/urandom | 32 MiB | CPUID (a VM exit) and RDRAND a word, a page walk a byte | **measured 1.5 s for 8 MiB**; fixed here (getrandom(2) 16 KiB a call; /dev/urandom pending) |
| `user`: `write` → `serial.put` → `screen.put` | write, writev, sendfile, splice to the console | **none** (sendfile to a file's size) | a byte: the UART's THRE wait (one byte in flight), two or three cells drawn, a scroll per line at the bottom | **measured 0.37 s for 64 KiB** (QEMU's UART); a real 16550: about 87 µs a byte; the console's lane |
| `tree`: `write` (`file_write`, `pwrite`, `file_put`) | write, pwrite, sendfile, copy_file_range, splice | 0x7ffff000 a call, 1 GiB a file | a frame taken and **zeroed**, then copied over | **measured 0.36 s for 64 MiB, 0.66 s for 128 MiB**; 1 GiB about 5 s |
| `paging`: `copy_user` from `process.fork` | fork, clone without CLONE_VM | the resident pages (no copy-on-write for anonymous memory) | a frame, 512 word copies, two walks | **measured 40 ms for 128 MiB, 1.05 s for 256 MiB at 2 GiB** (worse than linear: the frame search) |
| `elf`: `load`, `page_at`; `build_stack` | execve | the binary (1 GiB in the tree), p_memsz up to 127 TiB | a page zeroed and copied; argv a byte with a walk | **measured 22-171 ms for a 32 MiB binary** |
| `vm`: `map_zero` | mmap, mprotect, mremap's growth | free memory | a frame zeroed | **measured 60 ms for 128 MiB** with `pick`; munmap of it 16-41 ms |
| `sched`: `reap` (`paging.user_pages`, `free_user`) | wait4, fork, clone (anyone's) | a dead process's memory | a frame freed | measured 18-21 ms in wait4 beside the mmap load |
| `paging`: `user_pages` via `vm.note_peak` | every munmap, brk down, MADV_DONTNEED | every present table of the space | 512 entries a table | a sparse space: seconds for a 4 KiB munmap |
| `files`: `mark_gone` → `tpath` → `tree.name_of` | unlink, rmdir, rename | open files × path depth × records a page | quadratic in a directory page | from the code, minutes with deep paths and many links |
| `files`: `walk_as` → `tree.find`; `getdents` → `tree.entry_at` | every path call; getdents64 | directory size (no cap), 40 links | a linear scan a component; quadratic per page | measured 4.2 ms for getdents over 4000 names |
| `user`: `writev`'s checks; `socket.send`, a pty's slave write | writev, send, write | 1024 parts, each up to 2 GiB; a 64 KiB or 20 KiB take | `readable()` walks (and faults in) the whole buffer first | 1024 × 1 GiB: seconds |
| `vblk`, `nvme`, `ahci`, `usb_storage` waits; `block.victim`, `sync`, `journal.commit` | any block I/O: read, write, fsync, sync, the flusher, mount, halt | the device's timeout per request: 4e8 PAUSEs, 30-120 s, 30-60 s | a polled request | a dead disk: each miss retried up to 1,536 times; hours |
| `ext2`: `wspan`, `rspan`; `tree.writeback` | write, writev, read, fsync, sync, the flusher | no total cap on writev or a read | a polled request a block; a mapped file rewritten whole | seconds to minutes a call |
| `net`: the transmit-buffer wait | every sender, `tcp.tick` | 200,000 spins a frame, all 64 buffers out | PAUSE and reclaim | a device that stops returning buffers: seconds in one tick |
| `tcp`: `tick` (kernel thread under the tcp lock) | the network clock, every tick | 1,024 control blocks | a line a block | 10-100 µs; all timers due: 3-100 ms |
| `console`: `irq` → `input`: ^U, ^W echo | the keyboard's and COM1's interrupts | a 4,095-byte line | the echo through `serial.put` | 12,000-25,000 bytes drawn in one handler (the console's lane) |
| `netd`: `drain` | the end of every call | the 64-datagram loop queue | a delivery | 0.1-0.5 ms for a loopback stream |
| `ready`: `poll` | poll, epoll_wait | 1,024 entries, an epoll's 256 | byte-wise walks | measured 1 ms for 1,000 descriptors |

Bounded and short: pipes (64 KiB), a pty's queues (20 KiB), the signal and job-control loops (64 slots, though they
grow with the cube of the slot count, which the process-slot work raises to 1,024), the tick's own work, procfs (a
page a read), USB enumeration (a kernel thread that sleeps between its polls, not an interrupt).

## 6. The instrument and the probe

- **`kernel/latency`**, off unless the command line has `latency`; off, each hook costs one test of a word. An
  interval opens where IF goes from set to clear and closes where it is set again, timed with RDTSC: `boot/isr.S`'s
  common path opens on entry from a context with IF set (its RIP, its vector, its %rax: a call's number) and closes on
  resuming any frame with IF set; `boot/sched.S`'s `pax_irq_save` and `pax_irq_restore`, `pax_wait`, and
  `pax_enter_user` open and close their own. It keeps the longest interval since boot and since the last read with
  where it began, a histogram, the longest per system call number, per vector and per thread slot's `irq_save`
  sections, the longest gap between two chances the scheduler had (`preempt`, `kick`, `run_next`), and the ticks
  delivered against the ticks the clock says were due. `/proc/pax-latency` shows it; opening it starts the next
  window. (The kernel log ring is not merged, so procfs is the only reader.)
- **`user/elf/latprobe.c`** (`tools/mklatprobe`, static glibc; the same binary on PAX and Linux) measures each load in
  turn: the load's child sets up and says ready; the window starts; for 3 s a 1 ms sleeper records how late each
  sleep ends, a loopback UDP echo is sent every 5 ms and timed from when it was due, and the **host pings the
  guest's echo through virtio-net every 5 ms** (`tests/mpx6-latency.d/echo-host.py`, through QEMU's user network:
  the stand-in for a person typing over ssh); then the window is read. Each line also goes to the host as a datagram,
  so a boot with no COM1 reports.
- **The loads:** idle; spin (a CPU-bound loop, no calls); console writes of 64 KiB of 80-column lines; a pty's slave
  written 16 KiB at a time; pwrite of MiB/16 of memory to a file of the tree, then ftruncate; fork of a process with
  MiB/8 touched; execve of a 32 MiB binary; mmap and munmap of MiB/8; munmap of 1 TiB where nothing is mapped;
  pread of 8 MiB of /proc/self/mem; getrandom of 8 MiB; a pipe and a loopback TCP connection written 64 KiB at a
  time; getdents64 over 4,000 names; poll of 1,000 descriptors.
- **Linux:** the same probe and loads on the build host's own Linux 7.2.4 in QEMU, one CPU, the same memory and
  accelerator, `user/elf/latinit.c` as init (proc, a tmpfs at /tmp, devtmpfs, devpts, the virtio network's modules,
  10.0.2.15/24).

## 7. The measurements

QEMU 8.2.2 with KVM, COM1 present (the harness's machine), virtio-net; the worst of four boots (BIOS and UEFI, 1 and
2 GiB) unless the row names its memory; milliseconds. "net" is the host's ping, its median and worst. Linux is its
sleeper's worst and its ping's worst.

| load | worst interrupts-off (call) | sleeper's worst | net p50 / worst | ticks kept | Linux: sleeper / net |
|---|---|---|---|---|---|
| idle | 1.1 (fork) | 19.2 | 0.7 / 1.6 | 100 % | 0.1-0.6 / 1.2 |
| spin (no calls) | 1.2 (fork) | 29.2 | 27 / 42 | 100 % | 0.7 / 1.5 |
| console write, 64 KiB | **378** (write) | 752 | 948 / 1,492 | 8-9 % | 1.3 (145 once) / 2.0 (143 once) |
| pty write, 16 KiB | 2.8 (write) | 23 | 2.7 / 7-29 | 100 % | 0.1 / 1.1 |
| file write, 64 MiB (1 GiB) | **359** (pwrite) | 625 | 375 / 1,021 | 24-26 % | 1.4 / 1.8 |
| file write, 128 MiB (2 GiB) | **663** (pwrite) | 945 | 916 / 1,719 | 9-10 % | 94 / 91 |
| fork, 128 MiB touched (1 GiB) | 40 (fork; the child's exit 39) | 99 | 43 / 97 | 40-42 % | 0.7 / 3.1 |
| fork, 256 MiB touched (2 GiB) | **460-1,045** (fork) | 1,795 | 261 / 1,778 | 12-24 % | 0.7 / 1.6 |
| exec of a 32 MiB binary | 22-171 (execve) | 196 | 12 / 25-176 | 55-58 % | 0.2 / 1.3 |
| mmap and munmap, 128 MiB (1 GiB) | 60 (mmap) | 128 | 99 / 187 | 34 % | 0.4 / 1.2 |
| mmap and munmap, 256 MiB (2 GiB) | 146 (mmap) | 189 | 192 / 330 | 20-21 % | 0.6 / 1.8 |
| munmap of 1 TiB of nothing | **3,129** (munmap) | 3,164 | 1,468 / 3,131 | 6-7 % | 0.8 / 1.6 |
| /proc/self/mem, 8 MiB | **393** (pread) | 790 | 1,083 / 1,822 | 9 % | 0.8 / 1.4 |
| getrandom, 8 MiB | **1,498** (getrandom) | 3,023 | 1,399 / 2,992 | 7-8 % | 0.8 / 2.1 |
| pipe, 64 KiB writes | 0.9 | 19.2 | 0.7 / 3.5 | 100 % | 0.4 / 1.4 |
| loopback TCP, 64 KiB writes | 1.7 | 19.4 | 0.9 / 4.1 | 100 % | 0.3 / 1.6 |
| getdents64, 4,000 names | 4.4 (getdents64) | 31 | 31 / 43 | 100 % | 0.7 / 1.3 |
| poll, 1,000 descriptors | 1.1 | 29 | 31 / 43 | 100 % | 0.7 / 1.4 |

**What the numbers say.**
- **The longest call is the latency.** Beside every load whose calls run long, the sleeper's worst and the ping's
  worst are one to two of those calls; nothing else matters. The calls a user can make long are the ones in bold.
- **The scheduler's own share is a quantum a hop.** Beside `spin`, which makes no long call, a ping's round trip is
  27 ms in the median: the device's interrupt wakes `netd` to the back of the queue, the hog keeps its quantum, and the
  echo's reader then waits behind the hog again. A 1 ms sleep takes 19 ms at idle (the tick after next) and 29 ms
  beside a hog. With N runnable hogs, each of these multiplies by N.
- **Ticks.** Beside the worst loads the tick clock kept 6 to 9 % of real time: a 3 s munmap is 1 tick. CLOCK_MONOTONIC
  stood still for the whole of each long call.
- **The scheduler's longest gap** between two chances to choose was, beside every load whose calls run long, that
  load's longest stretch with interrupts off plus a few microseconds (a 370,456 µs console write, a 370,484 µs gap),
  and beside the others about a tick: the scheduler has no chance at all inside a call, and one every tick outside.
- **Two oddities, measured and left:** fork of 256 MiB at 2 GiB took 0.46 s on one boot and 1.05 s on another, where
  128 MiB took 40 ms: the frame allocator's next-fit search when the free frames are spread (`frames.alloc`); exec of
  the same binary took 22 ms on three boots and 171 ms on one, after the file-write load had freed 64 MiB.
- **Linux** keeps every load within 2 ms but for two single outliers (a console write and a 128 MiB file write); it
  keeps interrupts on in system calls and preempts a call at its reschedule points.
- **Under TCG** (CI's leg) every figure is the emulator's first: the sleeper's worst beside `spin` is 75 ms; the
  console's write costs less there than under KVM, where each byte's two port accesses leave the guest for QEMU.

## 8. Lost ticks: what the clocks and timeouts do

A tick due while interrupts are off waits in the APIC; every further tick due in the same stretch is lost
(`kernel/timer`: the count is only incremented by a delivered tick). So, for every stretch longer than 10 ms:

- **CLOCK_MONOTONIC and its kin** (`kernel/user` `now_ns`: ticks times 10 ms) stand still: a program timing anything
  across a long call sees too little time. Measured: 6 to 9 % of real time kept beside the worst loads.
- **CLOCK_REALTIME** (`wall_ns`: the RTC at boot plus ticks) falls behind for good: PAX reads the RTC once and has no
  NTP. A machine that runs long calls all day shows the wrong date by the end of it.
- **Every sleep and every timeout** counted in ticks (nanosleep, a poll's, an epoll's, a receive's, a futex's) ends
  late in real time by the ticks lost while it waited.
- **TCP's retransmission, persist and user timers, ARP's ageing and DHCP's retransmission and lease** turn on the
  network clock thread's `sleep(1)`: they run slow, so a lease is renewed late in real time and can run out at the
  server first.
- **The kernel's own device waits** (AHCI's and NVMe's deadlines, the timer's calibration) read `kernel/clock` and
  are right.
The fix is the clocks' (section 10, the third proposal): user clocks, sleeps and timeouts from `kernel/clock` as
deadlines in nanoseconds; then a lost tick costs timeliness only. The console's lane recommended the same.

## 9. What the kernel assumes about one processor

IF off is every lock (the `kernel/sync` words never contend), and a system call takes no lock because nothing runs
beside it. Global scratch serves one call at a time (`pax_kbuf`, `pax_argbuf`, `pax_execbuf`, `pax_syscall_state`'s
user stack word, so SYSCALL has no SWAPGS and no per-CPU area). One run queue and one current thread live in
`pax_sched_state`. `kernel/uaccess` trusts that nothing unmaps a checked page during a call. The TSS's RSP0 and
SYSCALL's stack word are one each. A second processor needs every one of these replaced, and that is the same work as
letting a call be preempted (section 10's last two proposals).

## 10. The proposals

**The bound (decision 1).** For any path a user can drive: interrupts off at most 1 ms; for anything at all, at most
10 ms (one tick, so no tick is lost); a wake-up at most three times the scheduler's own share (the same boot's
`spin`), with the guard as the check. Today's worst is 3,000 times the first.

**The general rule, with options and costs** (decisions 2 to 8; the recommended order is the list's):

1. **Per-unit fixes now** (decision 2; built here for three paths): a loop whose cost is in the wrong unit (an empty
   table walked a page at a time, CPUID a word, a page walk a byte) or a copy done twice. Cheap, local, certain, and each
   bounds its call by real work. The next of the same size: `vm.pick` by intervals, `note_peak`'s whole-space walk as a
   running count, the quadratic directory scans, the frame zeroed before a whole-page copy in `tree.write`, writev's
   and read's totals held to 0x7ffff000, the UART's 16-byte FIFO used, `readable()` over the slice a call takes.
2. **The clocks from the clock** (decision 3): CLOCK_MONOTONIC and CLOCK_REALTIME from `kernel/clock`, sleeps and
   timeouts as deadlines. Cheap; turns every lost tick from wrong time into late time.
3. **Device-driven wake-ups run at once** (decision 4): `netd`, the readers `netd` wakes and the console's readers go to
   the head of the queue, and a device's interrupt that lands where the tick could preempt (ring 3, a kernel thread
   with IF on) switches to them then. Cheap (`kernel/sched`, `kernel/interrupts`). Beside a hog with no calls a ping's
   round trip goes from a quantum a hop to about nothing; beside a hog of long calls, from two calls a hop to the rest
   of one. Cost: a packet flood can starve a CPU-bound process until it has a budget.
4. **Deferred work as a kernel service** (decision 5): a worker thread (interrupts on, preemptible like `netd`) that
   takes work a call need not finish before it returns: a dead process's frames, a truncated file's frames, a pool of
   frames zeroed ahead, the flusher's writes outside `irq_save`. Medium; removes the teardown half of many calls.
5. **Interrupt-driven block I/O** (decision 6): completion interrupts, a call that waits for its request blocks (as a
   pipe's reader does) instead of polling, and a controller reset on a timeout instead of retries. Medium to large, a
   driver at a time; it is also what disks need to be fast.
6. **Reschedule points inside long calls** (decision 7): a call reaching a point where it holds no global scratch and
   no half-made structure may yield (its kernel stack keeps its place). It needs per-thread scratch for the buffers it
   holds across the point and sleeping locks per inode and per address space, so a write, a truncate, a fork or an
   mmap stays atomic to others. Medium to large, one loop at a time: the file write, fork (or copy-on-write instead),
   exec's load, mmap's zeroing (or zero on first touch instead), the console's write.
7. **Interrupts on in system calls** (decision 8): a preemptible kernel, with every shared structure under a real lock,
   per-thread or per-CPU scratch, and the scheduler under its own lock. Large; it is the second processor's work, so
   do it with that.

**For the multiplexer (many ptys drawing at once):** a pty's write is bounded (20 KiB, 3 ms), so the panes cost
quanta, not stretches: with N panes busy, a keystroke waits up to N quanta. The third proposal helps the key's arrival;
the console's own write, which draws them, is the console's lane's. **For ssh under load:** a keystroke crosses the
device, `netd`, the ssh server, the pty and the shell and back; each hop waits behind a hog's quantum or a long call.
The third proposal takes the device and `netd` hops off the queue; the first and the sixth shorten the calls; the
process-to-process hops stay a quantum each until the scheduler favours a thread that has just woken, which is the
next step after the third (a woken thread ahead of a preempted one, with a budget). **For a second processor:**
section 9; every proposal from the sixth on is shared with it.

## 11. What was built

Each fix was seen red first under the guard (section 12) at the rows' commit, with trunk's kernel paths.

| fix | commit | before (KVM, 1 GiB) | after |
|---|---|---|---|
| munmap and a truncate's cut visit only mapped pages (`paging.next_leaf` steps over absent tables whole; `vm.unmap_range`, `vm.cut_maps`) | `80cbe96d`, `856c9063` | munmap of 1 TiB of nothing 3,061 ms with interrupts off | under 0.24 ms; the load's sleeper 1.00 times `spin`'s |
| getrandom fills a kernel page at a time, CPUID once a page, copied out whole (`process.random_fill`, `user.getrandom`); getrandom(2) gives at most 16 KiB a call (decision 10) | `42b9f123`, `48cae32b`, `fa020c2b` | 8 MiB in one call 1,494 ms | 320 ms for 8 MiB with the page fill alone; 0.69 ms a call with the cap; the load's sleeper 1.01 times `spin`'s |
| /proc/<pid>/mem copies a piece at a time with the block copy (`trace_mem.transfer`) | `59070c2d` | 8 MiB 393 ms | 1.55 ms; 1.01 times |

## 12. The guard and the plant

`tests/mpx6-latency` (`--loads guard`, the default): idle, `spin`, the three guarded loads and three pending ones on
native kmain_console with `latency`, under KVM. Rows: L0 the build; L1 every load's line with samples, the end line,
the instrument on; **L2** for each guarded load, the sleeper's worst, the loopback echo's worst and the host's ping's
worst, each over the same boot's `spin`, at most 3 (SKIPPED by name under TCG); `~L2` the pending loads (the console's
write, a file write of MiB/16, fork of MiB/8) measured the same way and named with the work that will bound them;
`~L3` every load's figures. CI's job runs it on the plan's legs under TCG (decision 11).

- **Red at the rows' commit** (`6a892cf8`, trunk's kernel paths): all three rows on both firmwares, 28 to 141 times
  `spin` (record sha256 `c7d03d64…`, the evidence index).
- **Green at the head:** L2 1.00 for munmap of a hole, 1.01 for getrandom, 1.01 for /proc/self/mem (sleeper; the
  echoes 0.89 to 1.04).
- **The plant** (`px131-plant-*`): the head with `vm.unmap_range` walking every page again; red by name at L2 for
  munmap of a hole.

## 13. Fit for an image, and what to try at the machine

The head is fit for an image: the instrument is off without its word, and the three fixes change no answer but
getrandom(2)'s count above 16 KiB (which the call allows above 256 bytes). With `latency` added to the image's command
line, `cat /proc/pax-latency` shows the longest stretch and the call that made it. At the machine, one run of under
ten seconds shows the general rule at work, bounded and unable to starve the machine for longer:

- from another machine, `ping -i 0.2 <machine>` while, over ssh, `dd if=/dev/zero of=/tmp/f bs=64M count=4; rm
  /tmp/f` runs once: four writes of 64 MiB, each one call; the pings stall for each call (about 0.4 s under KVM), and
  the ssh session's echo with them. That is what the general rule (section 10), not a fix a path, ends.

## 14. Evidence index

| what | where | result |
|---|---|---|
| the prediction | `e2ab8d7a` | before the instrument |
| the instrument | `d7305412`, `f6212ea3`, `321b1e57`, `ff234c30`, `9c6afe98`, `d8923425`, `4ac5913f`, `ce0eadd5` | |
| the probe, the suite, the Linux column | `92afa259`, `3aed4c37`, `fa75a076`, `66efb1fe`, `db422e4d`, `792b28a5`, `dbd47988`, `5feeded7` | |
| the measurement table | the suite with `--loads all --mem 1024,2048 --firmware both --linux` at `792b28a5` (PAX) and `5feeded7` (Linux), the lane's evidence | section 7 |
| the guard's rows | `cf81dd33`; the rig `6a892cf8` | |
| **red at the rows' commit** | `notes/px131/rig/red.manifest` at `6a892cf8` (trunk's kernel paths, the rows, the rig), a light take, record sha256 `c7d03d6480aa94b6a6ebac4892e0bfdf2cbd442287982ee402efa97d5aad0b22` | six rows red by name, both firmwares: `FAIL L2 native-bios-1024 hole:1024` (the sleeper 141 times `spin`, munmap 4,086 ms with interrupts off), `FAIL L2 … random:8` (124 times; getrandom 1,852 ms), `FAIL L2 … procmem:8` (33 times; pread 500 ms), and the same three on UEFI (110, 121 and 28 times); `END latency exit=1 secs=89` |
| the fixes | `80cbe96d`, `856c9063`, `42b9f123`, `48cae32b`, `59070c2d`, `fa020c2b` | |
| CI's job and paths | `b1073dc4`, `7106409a`, `886103ee` | |
| the takes at the head, native and release, and the plant | `notes/px131/rig/{quick-a,quick-b,release,plant}.manifest` | their records and `END` lines are in the PR |

## 15. Decisions

1. **The bound.** (A) a path a user can drive keeps interrupts off at most 1 ms, anything at most 10 ms, a wake-up at
   most three times the same boot's `spin` (recommended; taken); (B) 10 ms everywhere as a first milestone.
2. **Per-unit fixes now.** (A) build the clearly local ones here, red first, and list the rest as small follow-ups
   (implemented for munmap and truncate's cut, getrandom, /proc/<pid>/mem; recommended); (B) leave every path to the
   general rule.
3. **The clocks.** (A) user clocks, sleeps and timeouts from `kernel/clock` as deadlines (recommended, next; with the
   console's lane's same recommendation; taken, and built in the second part, `notes/px131-clocks-and-wake-ups.md`);
   (B) keep ticks and shorten every stretch below 10 ms first.
4. **Device-driven wake-ups.** (A) `netd`, the readers it wakes and the console's readers to the queue's head, and a
   device's interrupt switches to them where the tick could (recommended, next; taken, and built in the second part
   with the flood's row); (B) leave the FIFO.
5. **Deferred work.** (A) a kernel worker thread for teardown, frame zeroing and writeback (recommended, after 3 and 4);
   (B) keep teardown in the calls.
6. **Block I/O.** (A) completion interrupts, blocking waits, resets on timeout (recommended, with 5); (B) polling with
   shorter timeouts.
7. **Reschedule points in long calls.** (A) one loop at a time once per-thread scratch and sleeping locks exist
   (recommended, after 5 and 6); (B) none until the kernel is preemptible.
8. **Interrupts on in system calls.** (A) with the second processor, which needs the same locks (recommended); (B) now,
   on one processor.
9. **The guard's loads.** (A) bound the loads whose fixes have landed (munmap of a hole, getrandom, /proc/self/mem) and
   measure the worst structural ones as pending rows that name their owners, each bounded when its fix lands
   (implemented, recommended); (B) bound the worst three whatever their state: red at every head until structural work
   lands.
10. **getrandom's count.** (A) getrandom(2) gives at most 16 KiB a call, as getrandom(2) allows above 256 bytes, so a
   call's stretch stays near a millisecond; /dev/random and /dev/urandom keep Linux's whole reads (implemented,
   recommended); (B) cap the device reads too: `dd bs=1M` would read short blocks where Linux reads whole ones; (C) no
   cap: 8 MiB still holds 320 ms.
11. **The rows' yardstick and TCG.** (A) each L2 a ratio of the worst beside a load to the worst beside `spin` in the
   same boot, under KVM, held by local records; CI's TCG leg runs L1 and prints the figures (implemented, recommended);
   (B) the same bound under TCG: it held at the head (0.39 to 0.63) but was never seen red there.
12. **The network probe.** (A) the host pings the guest every 5 ms and times each from when it was due (implemented,
   recommended: a person's keystrokes do not wait for the machine); (B) the guest pings the host, which hides a stall
   between two pings.

## 16. Done-when

- [x] the rule as it stands, from the code (section 3), and the prediction scored (section 4)
- [x] the inventory (section 5)
- [x] the instrument, the probe, the table at 1 and 2 GiB on both firmwares under KVM, the Linux column (sections 6, 7)
- [x] what lost ticks do to the clocks and timeouts (section 8), and what one processor is assumed for (section 9)
- [x] the ranked proposals and the general rule with options, costs and an order (section 10)
- [x] three cheap fixes, each red first and green after (section 11)
- [x] the standing guard, red at the rows' commit (section 12)
- [x] one plant, red by name
