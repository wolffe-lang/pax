# The kernel lock's ledger: what it records, and the prediction (written before the first change)

Base: trunk `c316d799` (SMP stage 2). Two pin changes are queued on trunk (README, tests/mpx6-install*, tools/mkpxg,
user/*.pin, yew's image inputs), none in a file this branch touches. Expect one mechanical rebase.

## Why
Stage 2 put every processor's kernel work under one lock, and the build workload's scaling shows its price.
- SMP-BUILD's four pack jobs at four processors take 2.30 times one job's wall in a gated hold, and 2.12-2.52 over
  seven takes, against a 1.6 bound that stage 3a keeps.
- Nothing in the kernel says where that time goes: `kernel/klock` keeps an owner and a depth and times nothing.
- The figures so far are inferences. At four processors the four jobs' accounted user time is 1,261 ms against
  4 × 154 ms for one job, while their system time stays near 4 × 59 ms. That suggests about 40% of the wall spent
  spinning for the lock, but nothing measured it.

The ledger measures it, in the test kernel only (`tools/build-kernel --test-words`, as `pax.slowleave` is), and
changes nothing the shipped kernel does.

## What it records
**At every fresh acquisition** of the kernel lock (`klock.enter` returning true in `pax_interrupt`, under the lock):
- **the entry's key:**
  - a system call by its number (vector 0x100, the frame's %rax);
  - a trap from ring 3 by its vector (vector 14 is the page fault);
  - any trap from ring 0 as one key;
  - each vector from 32 up by its number (each processor's tick, RESCHED, each device);
  - `boot` for kmain's first hold, and `test` for the known hold below;
- **the spin:** the TSC cycles from just before `klock.enter` to just after it. One over 10,000 cycles is also counted
  as contended;
- **the hold's start:** the TSC, the processor's current thread, and its count of switches to a kernel thread.

**At every release store**, still holding: the hold's length, added to its key.
- The two release stores are `pax_klock_resumed`'s and `klock.leave`'s.
- A hold is marked `switched` if the processor's current thread changed during it, and `kthread` if a kernel thread
  ran during it. A kernel thread holds the lock for as long as it runs, so its run is charged to the entry that
  switched to it, usually CPU 0's tick.

**Kept:** per processor, spin cycles, fresh acquisitions, contended ones, hold cycles, holds closed, and the longest
hold with its key. Per key, the count and cycles of each kind of hold, and the spin of the entries with that key.
- The tables are 16 pages (64 KB) the test kernel takes from kernel/frames at its boot.
- Every write is made by the lock's holder, so the lock orders them and nothing new is synchronized.

**Read as `/proc/pax-klock`.**
- The test kernel writes the counters, which are never reset; readers subtract snapshots. It also writes the TSC at
  the read.
- The shipped kernel writes one line: `klock-ledger: not a test kernel`.

## What the shipped kernel keeps
- calls to empty functions around the entry's `klock.enter` and at the two release stores, plus the same pair on the
  slow leave's second entry, which never runs as shipped;
- one procfs file with one line.

The shipped entry reads no TSC: the shipped `ledger_now` returns 0.

## Rows
- **KLOCK-LEDGER** (gated; the instrument's own truth, no timing) is held in the `ledger` kind. That kind is a test
  kernel at 2 and 4 processors whose probe runs a mixed load (system calls, a pipe's writes and reads, page faults) on
  every processor between two reads of `/proc/pax-klock`.
  - **(a) Closure:** every processor's holds closed equal its fresh acquisitions, but for the one open hold of the
    reader's own processor.
  - **(b) Exclusion:** the holds of all processors over the window are at most its wall plus 1%.
  - **(c) A known hold is counted:** `pax.klockhold=20` (a new test word) has CPU 0's tick hold the lock 20 ms once a
    second under the key `test`. The window's seconds, ±1, are wanted as `test` holds of 20 ms ± 5%, and the longest
    hold at least 20 ms.
- **KLOCK-WAIT** (printed): per processor, spin cycles over the window's wall.
- **KLOCK-HOLDS** (printed): each key's share of the hold cycles, its mean and count, and the longest hold.
  - KLOCK-WAIT and KLOCK-HOLDS are printed for the `ledger` kind, and for SMP-BUILD's batches when the build image
    boots the test kernel.
- **TESTWORDS-LEDGER-ELF** (per tier) counts two marks: the ledger's text `klock-ledger tsc ` in the ELF's bytes, and
  its static `_Wtestwords.ledger.` among the symbols. Both are wanted in the test build and neither in the shipped one.
- **SMP-TESTWORDS** reads `/proc/pax-klock` in its shipped boot: exactly the one line.
- **SMP-BUILD-COST** (printed) gives the cost of the shipped stub calls. The build image boots the head's shipped
  kernel and trunk's in turn, three boots each at four processors. Printed for each kernel: the one-job and four-job
  batch walls (the host's minimum of three per boot), the noise (each kernel's own spread over its three boots), and
  whether the head and trunk differ by more than that noise.

## Plants
- `ledgerblind`: the release in `pax_klock_resumed` closes no hold. Red at KLOCK-LEDGER (a).
- `ledgership`: the shipped `kernel/testwords` carries the ledger's state and text. Red at TESTWORDS-LEDGER-ELF.

## The measurement
- **Workload:** SMP-BUILD's own, the pinned den's `pack-objects --window=0` over 2 MiB of incompressible objects per
  job, in three interleaved rounds of one job and then J, timed by the host. The build image boots the test kernel
  and bench prints the ledger before and after each batch.
- **Shapes:** J processors with J jobs for J = 1, 2, 3 and 4; four processors with one job; and J = 4 on four host CPUs
  that make two whole cores, beside the same on six host threads (three cores).
- **Boots:** each shape three times, native and release, BIOS: 30 boots, and 6 on two whole cores. SMP-BUILD-COST adds
  6 boots of the shipped kernels.
- **Where:** a six-thread section of the test host reserved for the hold. About 1 h 20 min.

## Prediction
**These numbers are guesses.** Before stage 2's record I predicted SMP-BUILD at 1.15-1.45 times and it measured
2.30, so my model of where the time goes under one lock was off by about 1.6 times. The figures below come from the
same kind of reasoning.
- **The spin share** (spin cycles over the batch's wall, the mean over the processors running jobs): under 1% at
  J = 1; 3-10% at 2; 20-35% at 3; 30-50% at 4.
  - **Wrong if** J = 4 is under 20% or over 60%. Under 20% would mean most of the 2.30 is not the lock (host threads
    sharing a core, caches, the tick), and splitting the lock alone could not reach 1.6.
- **The lock's use at J = 4** (all processors' holds over the wall): 0.6-0.9.
  - **Wrong if** under 0.4: the lock would then be free most of the time while processors still wait.
- **The hold shares at J = 4:**
  - system calls together 55-80%, read and write together at least 30% of all holds;
  - ring-3 page faults 10-35%;
  - the ticks, RESCHED and kernel-thread holds together 2-15%;
  - everything else at most 5%.
  - **Wrong if** page faults exceed 50% or system calls fall under 40%. The earlier sketch of the next stage guessed
    page faults first; I lean to system calls because one job's counted system time is 28% of its processor time,
    while its 11,000 faults at a few microseconds each come to about 10%.
- **The longest hold:** an execve or a kernel thread's run under the tick, 0.2-5 ms.
  - **Wrong if** over 10 ms: something would hold the lock for whole ticks, which comes before any split.
- **Two whole cores against three at J = 4:** the spin share on two whole cores at most that on six threads.
  - **Wrong if** higher: then placement on a core's two threads is not what inflates it.
- **The test kernel's own cost:** its four-job ratio within 5% of the shipped kernel's in the same hold.
  - **Wrong if** over 5%: the instrument would then disturb what it measures, and its numbers would need correcting
    first.
- **SMP-BUILD-COST:** the head's shipped one-job and four-job walls each within the larger of the two kernels' own
  spreads of trunk's. I expect that spread at most 8% at one job and 10% at four.
  - **Wrong if** the head is slower by more than that spread at either count.
- **KLOCK-LEDGER (a)-(c):** green in every boot. A red boot's numbers are void. This tests the instrument, not the
  kernel.

## What it is for
- The order of stage 3a's splits, by the hold time each moves out of the one lock, with a predicted SMP-BUILD ratio
  written before each.
- The bound for KLOCK-WAIT.
- The path to SMP-BUILD's 1.6.
- The ledger stays as the instrument every later unit reports.

## The stub calls' cost, decided (written before the take that decides it)
**Why.** SMP-BUILD-COST at `202a4f9c` read the head's shipped kernel 20% slower than trunk's at four jobs, against a
noise of 14%. Boot by boot the four-job walls were 508, 466 and 486 ms for the head, and 443, 442 and 389 ms for trunk,
so every head boot was slower than every trunk boot. The code difference is a few calls on each kernel entry, which I
cannot see costing that. But three boots a side cannot tell a cost apart from the hold's drift or the boots' order.

**The take.**
- **Three shipped kernels,** each built with `tools/build-kernel` at the native tier from a commit:
  - H, the head's;
  - T and U, trunk's (`9836b43e`) built twice: the A/A control.
- **The fixture:** one for all three, SMP-BUILD's own (den, bench, the same boot line), with one image per kernel.
- **The boots:** 12 blocks of three at four processors, BIOS, in one hold. The six orders of H, T and U run in turn,
  so each kernel sits in each place four times: 36 boots, 12 of each.
- **Each boot's figure** at one job and at four is its least of three batch walls, as SMP-BUILD-COST takes it.

**The rule**, at each job count:
- m_H, m_T, m_U are the medians of each kernel's boots, and m_TU is the median of T's and U's together;
- the A/A spread c = |m_T - m_U| / m_TU;
- the head's excess e = (m_H - m_TU) / m_TU;
- p is the one-sided Mann-Whitney p that H's walls are larger than T's and U's, and q is the two-sided one of T against
  U.

| verdict | when | what follows |
|---|---|---|
| VOID | q < 0.01 at either count: the two trunk builds differ, so the hold drifted or the order told | the take is taken again |
| COSTS | otherwise, at either count, e > c and p < 0.025: the head slower than the control's own spread, and not by chance | the stub calls cost what the shipped kernel must not pay. The hooks move behind the test build another way (the call sites themselves only in the test build), the shipped-kernel claim above changes, and no record is taken at this head |
| NOTHING MEASURABLE | otherwise, at both counts, e ≤ c: the head within the A/A spread | the claim stands as written, and the record is taken |
| UNSETTLED | anything else: outside the spread, but not significantly | the claim is unshown. A second take of the same size runs, its boots are pooled with this one's, and the rule is applied once to all 24 a side. That reading is final |

**The odds, said before.** With no cost at all, the head still lands outside the A/A spread in about 23% of such takes,
since the spread is itself a difference of medians. Nearly all of those are UNSETTLED; COSTS comes about 2% of the time.

**My prediction:** NOTHING MEASURABLE at both counts, because a call costs nanoseconds and a batch makes no more than
100,000 entries. COSTS is a live outcome, given the three boots a side above, and I put it at three in ten.
