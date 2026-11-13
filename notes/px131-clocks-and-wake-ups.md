# px131, the second part — the clocks from the clock, and device-driven wake-ups at once

The first part (`notes/px131-long-kernel-paths.md`) measured how long the kernel holds the processor and proposed a
general rule in an order. Its bound, its second proposal (the clocks counted from the clock) and its third (the
network's and the keyboard's wake-ups run at once) were taken, and this part builds the last two, each seen red first
under the guard.

- **The clocks.** A tick due while interrupts were off waited in the APIC and every further one in the same stretch was
  lost, so CLOCK_MONOTONIC, CLOCK_REALTIME and every sleep and timeout counted in ticks stood still through a long call:
  beside 64 KiB console writes both clocks kept 7 % of the time-stamp counter's time, beside 64 MiB file writes 31 to
  40 %. Now the tick count follows `kernel/clock` (the HPET, else the ACPI PM timer, the counter the tick is calibrated
  against): both clocks
  keep the counter's time within 0.7 %, and a long call makes a deadline late by at most the call, never wrong. This
  closes pax#384 (the wall clock stood still on the real machine during a console flood), and the console's lane's
  recommendation of the same.
- **The wake-ups.** A host's ping beside a process that only computes waited a quantum a hop: 27 to 30 ms in the median,
  37 to 40 ms at the 99th percentile, against under 1.5 ms at idle. Now the network thread, the readers it wakes and
  the console's readers go to the head of the queue and run at once: 0.72 to 0.75 ms in the median and 1.9 to 2.0 ms at the 99th percentile, 1.40 to 1.45 times idle's.
- **The risk named:** under a ping flood every frame takes the processor from the hog. Measured: the hog kept 82 to 85 % of its share while the host sent 99,000 to 103,000 pings in 3 s. A budget, if a
  faster flood needs one, is described in section 4.

**Rebased with the first part onto trunk `bbe91e16`** (the console's lane's drawing). The commits this note names
are those of `px131-clocks-wake3` (`be83835c`), replayed unchanged; the records before the rebase are for that code.
At the rebased head the guard holds on BIOS at 1 GiB under KVM (record sha256
`e3b269fe68e9815337fee1d33de9d1a68f6b7db364ceb38217a33ba6cc4ff090`, at `fcad7eef`): both clocks 0.992 and 0.994 of
the counter's time beside console and file writes, the ping beside `spin` 1.42 times idle's, and the hog under the flood
0.61 of its share (0.81 to 0.90 before the rebase, with 80,561 pings in the window against 98,000 to 129,000: one boot;
the head's take says more). The console's write with COM1 is as before (1.17 s for 64 KiB), so L4's load is unchanged.

**Restacked on the first part's fix for clef** (its entry paths call the latency close through a word, so the assembly
needs no `.weak`, which clef does not take): the same commits replayed unchanged once more, `px131b-clocks-wake`
(`a56d9948`) the code before it. On top, the delivered-tick count moves from a module variable to a word with a stable
name, `boot/isr.S`'s `pax_tick_delivered` beside `pax_tick_count`, and the USB session reads it by that name (section 3).

Footprint: cross-cutting (`kernel/timer`, `kernel/sched`, `kernel/latency`, `kernel/xhci`, `kernel/kmain_console.lu`,
`boot/isr.S`'s `pax_tick_delivered`;
`tests/mpx6-latency` and its probe and host side gain the clock, wake-up and flood rows).

## 1. Forbidden, and what was read

No kernel's source. Read: the Intel SDM vol. 3A on the local APIC timer and interrupt priority (a pending interrupt
of one vector is held, further ones at the same vector are lost), the IA-PC HPET specification, POSIX's
`clock_gettime`, `nanosleep` and `poll` (a timeout is a minimum, and lateness is allowed), QEMU's documentation of
`-mem-prealloc` and `-netdev user`. Linux was not run for this part: the first part's column stands.

## 2. The prediction, scored

Committed first (`73357a24`, `notes/px131/prediction-2.txt`), before the rows and any change:

- **C1** (the clocks count delivered ticks and stand still through a stretch): held.
- **C2** (beside console writes the clocks keep about 8 %, beside file writes about a quarter; a 2 % bound red by more
  than tenfold): held for the console (7.1 and 7.3 %), partly for the file write (31 to 40 %, more than a quarter);
  red by 30 to 47 times the bound.
- **C3** (the count follows the clock; both clocks within one tick): held, 0.3 to 0.7 % over windows of 3.2 to 3.7 s
  (a tick or two of 10 ms).
- **W1** (a ping beside a hog waits a quantum a hop: p50 about 27 ms, p99 about 36; red by about tenfold): the figures
  held (p50 27 to 30 ms, p99 37 to 40); the ratio was 26 to 30 times, not ten.
- **W2** (the fix: within three times idle's p99): held: p50 0.70 to 0.75 ms, p99 1.40 to 1.45 times idle's.
- **W3** (under a flood the hog keeps well over half its share): held: the hog kept 82 to 85 % of its share under 33,000 pings a second (before the change: 100 %, under the 3,000 a second the old wake-ups let through).
- **W4** (the loopback echo between two processes stays a quantum a hop beside the hog): partly wrong: the loopback echo beside `spin` went from 55 to 25 ms in the median (idle: 15 ms), because loopback's frames are delivered by the network thread too and its readers are woken from it; the hop left is the sender's own wake-up, a quantum.

## 3. The clocks

**Before.** `kernel/timer`'s count rose by one for each tick interrupt delivered. `kernel/user` reads CLOCK_MONOTONIC as
ticks times 10 ms and CLOCK_REALTIME as the RTC's time at boot plus the same; `kernel/sched`'s sleeps, `kernel/ready`'s
poll and epoll, `kernel/socket`'s receive timeouts, `kernel/futex`, `kernel/tcp`, `kernel/arp`, `kernel/dhcp` and
`kernel/xhci` count their deadlines in ticks. A stretch with interrupts off longer than a tick delivers one tick, so
every one of them stood still for the stretch less 10 ms.

**Now.** With `timer.follow_clock()` (called by `kmain_console`, the kernel the images ship), each delivered tick sets
the count to the larger of itself plus one and the ticks `kernel/clock` says are due since the tick was armed. The
clock is read at every tick already (it samples its wrapping counters there), so this costs a division. Every
deadline above is then a deadline in real time at the tick's resolution: a long call makes a sleep, a poll's timeout or
a retransmission late by at most the call, and both clocks keep the clock's time. The interrupts themselves are counted
apart (`timer.delivered`): the timer's own drift report and the instrument's lost ticks read that. The test kernels
(`kmain_timer`, `kmain_sched`, `kmain_metal`, which fakes its clock's readings for its rows) count interrupts as before.

**A deadline after a stretch.** A wait that looked at its deadline before its event could now time out after a long
stretch although its event came during it. Every wait in the tree was read for it: the system calls (`poll`, `epoll`,
a receive, a futex) look at their event first each time they run again, `kernel/sched`'s sleepers are woken by the
deadline itself, and TCP's, ARP's and DHCP's timers are deadlines. Two loops looked first at the deadline: `kernel/xhci`'s
command and control-transfer waits, where a timeout quarantines the controller. They look at the completion first now.

**A harness that leaned on lost ticks: the USB keyboard's repeat.** `tools/usb-session` holds `a` for 100 of the
guest's ticks and judges the repeat from the probe's CLOCK_MONOTONIC stamps (`user/elf/usbkeys.c`): a 250 ms delay
(220 to 320), then a 33 ms period (median 20 to 45, mean 31 to 37). Its own note said why it read the guest's ticks:
a stalled vCPU loses ticks while the host's clock runs on, and the repeat, the poll timeout and CLOCK_MONOTONIC all
counted those ticks, so a stall cost the stamps nothing. With the count following the clock, a stall's lost ticks
come back as a jump, and the stamps show the stall. Measured on the build host, the same session at each part's head:

- **five boots each, the session as it stands:** the first part's stamps were the same in all five (250 ms, then 30
  and 40 ms, mean 33.2); this part's in three, one tick early in one (240 ms), and uneven in one (280 ms, then 10 to
  50 ms, mean 32.2, inside the bounds); the head's take met one worse (300 ms, median 50 ms, mean 42.4).
- **four boots each, the hold's polls logged** (the count and the interrupts taken, from an instrumented copy of the
  session): the first part's count never stood still for more than 12 to 23 ms; in one of this part's boots the
  host's own polls came 57 ms apart, the guest took 3 interrupts where 6 were due, the count caught them up at the next
  one, and the intervals around it were 50 and 20 ms; the other three were as the first part's.
- **CI's runners** (the same suite, one run each): the first part's root session took 1.257 s of wall clock for its
  100 ticks (about 26 ticks lost), with stamps as even as ever; this part's had two stalls at the hold's end, intervals
  of 140 and 130 ms, mean 44.2 ms, and failed.

So the kernel's repeat did not change; what changed is what the stamps can hide. At a real keyboard nothing moves
while interrupts stay on: 250 ms, then 30 and 40 ms in turn. After a stretch with interrupts off (a 64 KiB console
write at the screen is 120 ms), the reports due inside it are dropped, as before (never a burst), and the next comes
on the clock's schedule rather than as if no time had passed: a tick's difference at most. The session now holds for
the interrupts the guest took (`boot/isr.S`'s `pax_tick_delivered`, written by `kernel/timer` and read as the tick
count is), so a stall lengthens the hold as
it used to, and leaves out of the period's figures every interval that spans ticks the guest lost (the probe prints
its first read's time, `USBT0`, to place the stamps on the ticks); at least 8 intervals must be left
(`tests/usb-session-selftest` U10 to U13: CI's failing stamps are refused without the losses and pass with them; U14:
the hold reads the word by its name). `repeat.txt` says which word the hold counted (`hold_counts`).

**What it does not do.** The resolution stays a tick (10 ms): reading CLOCK_MONOTONIC from `kernel/clock`'s nanoseconds
directly is a later choice (decision 14). A clock counter that wraps inside one stretch loses its wraps: `kernel/clock`
reads the HPET where there is one (32 or 64 bits), else the ACPI PM timer (24 bits wrap after 4.7 s, longer than any
stretch the first part measured once its three fixes landed), else the PIT, whose 54.9 ms wrap any long call outlasts:
on a machine with neither of the others the clocks still lose time through a stretch, as before. CLOCK_REALTIME still starts from the RTC with no NTP: it now keeps the clock's rate, not the world's.

## 4. The wake-ups

**Before.** The device's interrupt queued the network thread at the tail; a switch happened only from idle or when the
running thread's two-tick quantum ran out; the thread's deliveries queued their readers at the tail again. Beside one
process that only computes, a ping's round trip was a quantum a hop.

**Now** (`kernel/sched`). `wake_urgent` puts a thread a device's work woke at the head of the queue and marks it:
`wake_net` (the network thread, by its device's interrupt), `wake_input` (a reader of the console, by a key) and
`wake_pipes` when the network thread calls it (the readers its deliveries wake; `block_net` names that thread). `kick`,
after a device's interrupt, and `preempt`, at the tick, switch to an urgent head at once when the running thread is not
urgent itself; the running thread goes to the tail as a preempted one does. An interrupt reaches `kick` only where it
was taken, so with IF set: in ring 3, or in a kernel thread outside its locks, where the tick could have preempted
already. A thread keeps its mark while it runs and loses it when it leaves the processor, so an urgent thread is not
taken off the processor for another urgent one.

**The risk: a flood.** Each frame now preempts a hog. The flood row (L6) runs `flood`, the hog's loop, while the host
sends pings as fast as the guest answers (16 in flight), and holds the hog to half of its share beside `spin`:
`flood` kept 82 to 85 % of `spin`'s ops while the host sent 99,000 to 103,000 pings in the 3 s window (33,000 a second, p50 0.44 ms, none lost); before the change the old wake-ups let through 8,000 to 9,300. QEMU's user network is the limit here, at about 33,000 pings a second; a real network device can
deliver more. **A budget, if one is needed** (not built; decision 17): a thread loses its urgent mark when urgent
work has had more than half of the current tick, or an urgent switch happens at most once a millisecond; the rest go
to the tail as before. Either keeps a hog at half its share under any flood, and costs a ping at most a quantum.

**What it does not do** (prediction W4). Two processes that talk over a pipe or loopback still wait behind a hog's
quantum a hop: their wake-ups are not a device's. The next step (the first part's section 10) is a woken thread ahead
of a preempted one, with the same kind of budget. And a long call still holds everything: the first part's proposals
from the fourth on are for that.

## 5. The rows

`tests/mpx6-latency` gains three rows; its guard run adds `flood` to `idle` and `spin`.

- **L4 the clocks:** over each clocked load's window (the console's write of 64 KiB, a file write of MiB/16), the time
  CLOCK_MONOTONIC and CLOCK_REALTIME say passed, each within 2 % of the time-stamp counter's. Under TCG too.
- **L5 the network's wake-ups:** beside `spin`, the host's ping's p99 at most three times its p99 at `idle`. KVM only.
- **L6 a hog under a ping flood:** `flood`'s ops (1 ms of CPU each) at least half of `spin`'s. KVM only.

And the guest's memory is backed before it boots (`-mem-prealloc`, found here and moved into the first part,
`1e5d8fd6`): a first touch of a guest frame otherwise costs the host a page fault, and a fork's, an mmap's or an exit's
frames showed those as stretches of 30 to 150 ms now and then, on trunk's kernel as on this one; with the network's
wake-ups at once, `spin`'s worst ping fell to a few milliseconds and such a stretch alone could fail L2.

Under KVM at 1 GiB, BIOS and UEFI (and BIOS at 2 GiB), red at the rows' commit and green with the fixes and the backed
memory. Both records were taken before this part was replayed onto the first part's later commits (a link fix, the
backed memory): at `736f0830` and `96986862`, kept as `px131-clocks-wake-before-rebase`; the green record's sha256
`f394c8f7385ff802038c6a22aead9831532bad065a30fff66f670f7c0c595af7`:

| row | before | after |
|---|---|---|
| L4 the clocks over a window of 64 KiB console writes, of the counter's time | 0.071 (BIOS), 0.073 (UEFI) | 0.994, 0.994; 0.993 at 2 GiB |
| L4 the same over 64 MiB file writes (128 MiB at 2 GiB) | 0.399, 0.309 | 0.993, 0.995; 0.994 |
| L5 the host's ping beside `spin`, p50 / p99, and p99 over idle's | 29.9 / 40.1 ms, 29.6 times; 27.1 / 37.1 ms, 26.3 times | 0.75 / 1.91 ms, 1.45 times; 0.72 / 1.90 ms, 1.40 times; 0.70 / 1.97 ms, 1.45 times |
| L6 `flood`'s ops over `spin`'s; the pings in its window | 1.00, 8,036; 1.00, 9,337 | 0.85, 103,219; 0.82, 99,058; 0.85, 102,725 |
| the loopback echo beside `spin`, p50 (idle: 15 ms) | 55 ms | 25 ms |
| L2, the first part's three guarded loads over `spin` | 0.94 to 1.06 | 0.68 to 1.73 (`spin`'s worst ping is now 3.7 to 4.0 ms, not 41 to 42) |

Under TCG (CI's leg) L4 holds (0.997, 0.995) and L5 and L6 are printed and SKIPPED by name (1.18 and 0.62).

**A correction to the first part's table.** With the guest's memory backed, the calls that fill fresh frames hold
interrupts off for less than that table says, because part of what it measured was the host's page faults: a 64 MiB
file write 60 ms (the first part's takes: 113 to 359 ms), fork of 128 MiB 43 to 77 ms (40 to 115). The console's write
is not of that kind (1.15 s for 64 KiB with COM1 in these takes; each byte's port accesses leave the guest, and their
cost follows the host's load). The ranking stands; the file write's place is lower.

## 6. Fit for an image, and what to try at the machine

The head is fit for an image. The clocks change only where a stretch was long (they then keep time, where they stood
still); a device's wake-up changes only the order in which ready threads run. At the machine:

- **The wall clock** (pax#384): note `date` and a phone's clock, flood the console for a minute (`yes` at the console,
  then Ctrl-C), and look again: before, the machine's clock fell behind by most of the minute; now it keeps the phone's
  to the second.
- **A ping beside a hog:** from another machine `ping <machine>` while, over ssh, `while :; do :; done` runs: before,
  about 27 ms a reply; now about 1 ms, as at idle. The ssh session's echo improves by the device's and the network
  thread's hops only: the shell behind the pty still waits a hog's quantum (section 4).

## 7. Evidence index

| what | where | result |
|---|---|---|
| the prediction | `73357a24` | before the rows |
| the rows: the probe's clocks and `flood`, the host's flood, L4 to L6 | `f5a02ace`, `08109412`, `e2709ab5`; the rig `d29d7121` | |
| **red at the rows' commit** | `notes/px131/rig/red-2.manifest` at `736f0830` (before the replay; `d29d7121` after it): the first part's kernel, a light take, record sha256 `106be51c03ef7b2675231122ccc2919065663c08be1a7db52927b97e9a155805` | `FAIL L4 native-bios-1024 console:65536` (both clocks 0.071 of the counter's time), `FAIL L4 … write:64` (0.399), `FAIL L5 native-bios-1024` (the ping beside `spin` p99 40,147 us, at idle 1,357: 29.59 times), and the same three on UEFI (0.073, 0.309, 26.30 times); L6 held (1.00); `END latency exit=1 secs=93` |
| the clocks | `6d30b0ff`, `68a8ca9b`, `ccffc6b2`, `490cc70d` | |
| the wake-ups | `b03a6d12`, `3b68baee` | |
| the guest's memory backed | `1e5d8fd6` (the first part's) | |
| green at `96986862` (before the replay), the guard and the scheduler | `notes/px131/rig/green-2a.manifest`, a light take, sha256 `f394c8f7385ff802038c6a22aead9831532bad065a30fff66f670f7c0c595af7` | section 5's table; `END ci-plan exit=0 secs=111`, `END latency exit=0 secs=88`, `END latency-2g exit=0 secs=45`, `END latency-tcg exit=0 secs=50`, `END sched exit=0 secs=17`, `END interrupts exit=0 secs=41` |
| the delivered count by name | `tests/usb-session-selftest` U14 at `ec9c38a8`, red there; `d65baee7`, `b3ee7a36`, `b77b7548` | `FAIL U14: boot/isr.S lacks '.globl pax_tick_delivered'`, then `PASS U14` |
| the takes at the head, native and release, and the plant | `notes/px131/rig/{green-2a,green-2b,release-2,plant-2,final-2}.manifest` | their records and `END` lines are in the PR |

## 8. Decisions

The first part's decisions 1, 3 and 4 were taken as recommended: the bound (a path a user can drive keeps interrupts off
at most 1 ms, anything at most 10 ms, a wake-up at most three times the same boot's `spin`), the clocks from the clock,
and device-driven wake-ups at once with the flood named and held by a row. Its order for the rest (deferred work and
interrupt-driven block I/O, then reschedule points in long calls, then interrupts on in calls with the second
processor) is the plan.

14. **The clocks' form.** (A) the tick count follows `kernel/clock`, so every deadline already counted in ticks is one
    in real time at the tick's resolution, with no caller changed (implemented, recommended: cheap, local, certain);
    (B) CLOCK_MONOTONIC and CLOCK_REALTIME read `kernel/clock`'s nanoseconds at each call, and sleeps and timeouts
    become deadlines in nanoseconds: finer, but every caller changes and every clock read becomes a counter read.
    (B) can follow (A) at any time.
15. **Who is urgent.** (A) the network thread, the readers its deliveries wake, and the console's readers; the switch
    at a device's interrupt and at the tick (implemented, recommended); (B) every thread a wake-up makes ready: that is
    the next step's, and needs its budget first.
16. **A wait's deadline after its event.** (A) the two `kernel/xhci` loops look at their completion before their
    deadline (implemented, recommended: with real-time deadlines a stretch could otherwise quarantine a controller that
    answered); (B) leave them: a stretch of 2 s in a USB command's wait is rare.
17. **The flood's budget.** (A) none until a flood is seen to starve a process: the row holds the hog's share and will
    be red first (recommended); (B) the budget of section 4 now.
18. **The guest's memory in the guard.** (A) backed before boot, PAX's and Linux's alike (implemented in the first
    part, recommended: the host's page faults are not the guest's stretches); (B) left to fault: the yardstick of L2 is now a few milliseconds,
    so a fault of the host's could fail it.
19. **The USB session's repeat row.** (A) hold for the interrupts the guest took and leave out the intervals that span
    ticks it lost, a slow or uneven repeat with no loss still refused (implemented, recommended); (B) widen the bounds:
    a repeat broken slow would pass; (C) keep the repeat's deadlines on the interrupts taken: the stamps are the
    clock's now, so the stall would still show.
