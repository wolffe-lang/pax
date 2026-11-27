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

## The verdict: COSTS, and the hooks out of the shipped kernel
The take ran under the rule above at `b0d5c048`: 36 boots, 12 of each kernel, the two trunk builds byte-identical.

| | head | A/A spread | p (head larger) | q (trunk against trunk) |
|---|---|---|---|---|
| one job | +1.6% | 1.3% | 0.153 | 0.403 |
| four jobs | +2.3% | 0.0% | 0.017 | 0.795 |

So the verdict is COSTS, and it was applied as written; my prediction, NOTHING MEASURABLE, was wrong. The first
reading's 20% was noise from three boots; the cost is about 2%.

What follows, as the rule said:
- **The ledger's hooks left the shipped kernel.** The test build applies them, as `tests/mpx6-smp.d/ledger.patch`,
  to its own copy of `kernel/`.
- **`kernel/` is trunk's again**, so the paragraph "What the shipped kernel keeps" above no longer holds. The shipped
  kernel keeps nothing: no calls, no stubs, no `/proc/pax-klock`.
- **Rows hold it there:**
  - LEDGER-PATCH: the patch's lines are the ledger's own, and it applies exactly;
  - KERNEL-NO-LEDGER: `kernel/` names no ledger;
  - TESTWORDS-LEDGER-ELF: no ledger in the shipped ELF. With `SMP_SHIPPED_AGAINST`, the shipped kernel's loaded
    sections must equal trunk's, `.text` byte for byte;
  - SMP-TESTWORDS: no `/proc/pax-klock` in the shipped kernel.
- **The test kernel's sources are line for line those it had at `b0d5c048`,** only the patch's comments reworded. So
  every figure the ledger gave stands.

## A finding about measuring this kernel: about 2% from code placement alone
The head's shipped build at `b0d5c048` differed from trunk's `9836b43e` by an empty call or two at each kernel entry
and release, four empty functions and one more `/proc` entry. Its four-job SMP-BUILD wall was 2.3% longer, beyond the
A/A control (p = 0.017). The calls cannot account for that:
- the ledger counted about 11,700 kernel entries per four-job batch;
- even at 20 ns a call, every one serialized under the lock, they come to under 0.7 ms of a 392 ms batch (0.2%).

The measured difference was about 9 ms.

What the build did change is where nearly everything sits. Comparing the two linked kernels:
- **Section sizes:** `.text` grew by 768 bytes, `.rodata` by 64 and `.data` by 56.
- **`.bss` is unchanged:** every one of its 324 symbols is at the same address, the kernel lock's word and the
  scheduler's state among them.
- **Functions:** of 4,738 functions in both, the 1,673 linked before `interrupts.route` stayed put. The other 3,065,
  61% of the code's bytes, moved.
- **Cache lines:** 2,427 functions sit at a different offset within their 64-byte line.
- **The paths that hold the lock longest on this workload all moved and changed offset:**

  | function | moved | offset in its 64-byte line |
  |---|---|---|
  | `klock.enter` | +72 B | 42 → 50 |
  | `klock.leave` | +81 B | 4 → 21 |
  | `paging.map_user` | +88 B | 24 → 48 |
  | `vm.mmap` | +760 B | 8 → 0 |
  | `vm.mmap_file` | +760 B | 56 → 48 |
  | `vm.brk` | +760 B | 17 → 9 |
  | `uaccess.zero` | +760 B | 60 → 52 |

- **Unmoved or unchanged in offset:** `memset` and `memcpy` moved by 768 bytes, a multiple of 64, so they kept their
  offsets; `frames.alloc` did not move.

The attribution is by elimination: the build's only executed difference is far too small, and its placement
difference is large. A direct proof would build trunk with a pad of the same size and no other change.

**For later measurements:**
- A difference of about 2% between two builds on this workload is within what placement alone can do.
- Comparing two builds' timings needs an A/A control and a dozen boots a side.
- A difference that size is not evidence of a code change's cost without a placement control.

## A correction: the second cost take read VOID, so neither cost is shown
The take was rerun at `f983144e`. There the shipped kernel's loaded sections equal trunk's, `.text` byte for byte,
and the rest differs only in 35 bytes of the commit stamp. The two trunk builds, T and U, were byte-identical,
stamps included.

| | medians: head, T, U | A/A spread | head | p | q (T against U) |
|---|---|---|---|---|---|
| one job | 174.5, 171.3, 176.4 ms | 2.9% | +0.3% | 0.52 | 0.005 |
| four jobs | 382.3, 387.0, 388.6 ms | 0.4% | -1.5% | 0.95 | 0.84 |

The verdict is VOID: two byte-identical kernels differed at one job by 2.9%, with a permutation p of 0.004-0.005.
What it was not:
- **Not order or place.** The six orders ran in turn, and U was slower than T at every place in a block, after the
  same kernel and after another, and in each third of the take.
- **Not a neighbour's load in a window.** The boots ran within five minutes, eight seconds apart and interleaved, so
  a load at any moment fell on all three kernels alike.
- **Not the stamp.** T and U carry the same one.

That leaves chance (about one in two hundred for one count; about one in twenty-five over the four trunk-against-trunk
tests run so far), or something tied to each kernel's own image file, of which each take built one per kernel.

**What follows for the first take.** Its COSTS (+2.3% at four jobs, p = 0.017) was applied as written, and the hooks
stay out of the shipped kernel on their own merit: the shipped kernel is now trunk's, which a byte comparison proves.
But a method that produces 2.9% at p = 0.005 between identical kernels cannot show a 2.3% cost at p = 0.017. So:
- that the empty calls cost anything measurable is **not shown**;
- that code placement moved the build wall by about 2% (the section above) is **not shown** either. The placement
  facts stand (`.text` 768 bytes longer, 61% of the code moved, `.bss` unmoved), but their effect on the wall is
  unmeasured.

**A take that could show such a cost needs three things:**
1. **The whole host quiet** for the hold, not only its own section.
2. **Several images per kernel,** built apart and rotated, so that an image's own effect counts as noise within a
   kernel rather than as a difference between kernels.
3. **A pre-registered margin and an interval for the head's difference** in place of an A/A spread made of two
   medians. That spread came out 0.0% in the first take, which let any excess pass it. The A/A pair then serves as a
   check that the interval covers zero.
