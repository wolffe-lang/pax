# The memory calls off the kernel lock: a per-space `mm` word and a frames word (written before the first change)

Base: trunk `ce322118` (stage 3a's first unit, lock ranks and the ledger per lock word, merged). This is stage 3a's
second unit, and the first to change the shipped kernel. Nothing here is a timing claim. Every reading is a share
inside one boot, a count, or a correctness row.

## Why
At four jobs the build's `brk` and `mmap` hold the kernel lock 0.69-0.83 of all hold time. In the ledger kind's load,
`munmap` holds 0.78-0.86 of it. These calls touch one process's page tables and kernel/frames, and nothing else the
kernel lock covers. So they come off it first.

## The words
| word | rank | where | covers |
|---|---|---|---|
| the kernel lock | 0 | kernel/klock | everything below does not |
| tcp, udp, ip, icmp, arp, net | 10-15 | kernel/sync | as now |
| **mm**, one per space | 16 | a word in the area of the process that owns the space | the space's page tables; the vm words of every area whose calls use that space; the peak count |
| **shoot** | 17 | kernel/sync | one shootdown request at a time |
| console, heap | 20, 21 | kernel/sync | as now |
| **frames** | 22 | kernel/sync | kernel/frames' bitmaps, hint and counts, inside `alloc` and `free` only |

**Placement.**
- The mm word belongs to the space, not to the caller's area. A vfork child runs in its suspended parent's space
  while the parent's other threads may still run there, so `sched.mm_take` resolves the word from the thread: the
  word of its leader when that leader owns its space, else its vparent's, up the chain.
- frames is innermost, because the heap grows by `frames.alloc` while holding its own word.
- shoot and frames each sit alone in a 64-byte line after kernel/sync's eight words.

**The mm and shoot spins answer the shootdown mailbox,** as `klock.enter`'s spin does. They live in kernel/tlb, since
kernel/sync cannot import it.

**Why nothing deadlocks:**
- Every mm take happens under the kernel lock, so at most one processor ever waits for an mm word. Off the lock, an mm
  word is only given back. `sched.mm_take` checks this by name.
- An off-lock holder never waits for the kernel lock or for an mm word. It waits only for frames, whose holders never
  wait, and for shoot, whose holder waits only for answers, which every spinner gives.

## The calls that leave the kernel lock
`brk`, private anonymous `mmap` (PROT_NONE reservations included), `munmap` and `mprotect`.

kernel/user's dispatch wraps them:
1. Holding the kernel lock, take the caller's space's mm word.
2. Check that the thread has not been ended in place, and that the word still guards its live PML4.
3. Decide by the fallback rule below.
4. Give the kernel lock back (`klock.give_for_call`) and run the call under mm alone, interrupts off as today.
5. Give mm back, then take the kernel lock again (`klock.take_after_call`). The kernel lock is never taken while
   holding mm.

**The fallback rule.** A call leaves the kernel lock only when all of these hold:
- the caller owns its space (a vfork child's calls stay);
- an `mmap` is private and anonymous, with no descriptor and not shared, and with MAP_FIXED it overlaps no record;
- a `munmap` or `mprotect` range overlaps no record;
- `brk` always qualifies.

Everything else stays under the kernel lock and takes mm inside it: file and shared mappings, `/dev/zero`, `mremap`,
`msync`, `madvise`, faults, and every other site in the census. The decision is made once, before the kernel lock is
given back.

**Three rules for code that runs off the lock:**
- It answers shootdowns at every page, so a long eager `mmap` cannot outlast the shootdown's 1 s bound.
- It makes no runtime allocation. The runtime's ambient slot is one kernel-wide word until the heap unit.
- It reads nothing of the scheduler's: the area and the PML4 are passed in.

## Everyone who must take mm, and how a miss is caught
**The census lists every call outside kernel/vm and kernel/paging** that touches a user space's tables or an area's vm
words: kernel/user, uaccess, tree, futex, signal, trace_mem, procfs, files, process, elf and sched. Three kinds of
site are exempt by name:
- kernel-half unmaps;
- the test kernels;
- the free of a parked space, which no word guards and which runs under the kernel lock once no CR3 holds it.

**A miss is caught three ways:**
- **MM-CENSUS** (static, gated): every such call sits in a function that takes the word first. It is red at trunk,
  listing every site.
- **Kind 5 in the test build:** a user page table written while holding no mm word taken for that space. This also
  catches taking the wrong word.
- **A plant:** uaccess's check-then-copy without the word.

## Teardown
**Exit, the reap, exec, the area's move at a sibling's exec, and a fatal end** all run under the kernel lock and take
the space's mm word first.
- An off-lock call takes the word before it gives the kernel lock back, so it never starts against a space that is
  ending.
- An ending that comes later waits for the call in flight, answering shootdowns.
- `mm_take` refuses an ended thread. So an exec's parked space, still loaded by siblings ended in place, is touched by
  nothing but its free.
- The mm word travels with the area when it moves.

## Shootdowns
**The requester holds shoot,** plus either the kernel lock or that space's mm word. The mailbox, its three service
points and its 1 s bound stay. Two service points are added: the new spins, and kernel/vm's per-page loops while a
call runs off the lock.

**The end's STOP can now meet a requester waiting for answers.** Before this unit, every requester held the kernel
lock, as the end's sender does. So the requester's wait answers its own mailbox, where only a STOP can be, and counts
a STOPPED target as answered.

**Batching** is not in this unit.

## Interrupts off for the whole call
**What the processor loses.** Over a long call it loses its ticks: one stays pending and the rest fold into it.
- If it is CPU 0, sleepers everywhere wake late by up to the call's length.
- Time does not drift, because kernel/clock reads the HPET.
- Charges stay exact, because they are TSC cycles.
- Today the whole machine loses those ticks for such a call. After this unit only that processor does.

**What can ask it for something,** now that it may be doing memory-call work:
- a kernel-half INVLPG: it waits, panics after 1 s, and is answered per page;
- the end's STOP: it polls for 1 s and names a late processor;
- a panic's STOP: it polls for 100 ms;
- the test build's op 3;
- RESCHED: nothing waits for it, so it is taken when the call ends.

## Rows
| row | gated | what |
|---|---|---|
| MM-OFF-KLOCK | yes | `brk` and `mmap` under 5% of the kernel lock's hold cycles at four jobs of the build (test kernel), and `munmap` under 5% in the ledger kind. Red at trunk in every boot |
| MM-CENSUS | yes | static, above |
| MEM-FRAMES-EXACT | yes | the memory kind at 2 and 16: processes and threads churning `brk`, `mmap`, `munmap` and `mprotect` with faults; after they exit and the reap settles, free memory is exactly what it was. A test-build audit adds that every user leaf's frame is marked used and none is in two leaves unless it is borrowed |
| MEM-BRK-ONE | yes | two threads racing `brk`: one break, every page under it readable and writable, the page above it not mapped, and no frame lost |
| MEM-TLB | yes | 64 rounds: a reader loads a page on one processor while its sibling `munmap`s it on another; once the sibling says so, the reader's next load must fault |
| MEM-CONVOY | printed | one thread's eager 64 MiB `mmap` while its sibling calls `brk`: the call's time, the sibling's wait, the other processors' longest kernel lock wait |
| MEM-END | yes | the memory kind ends while another process's `munmap`s are asking shootdowns: every processor stops, no panic |
| LOCK-RANK-CLEAN | yes | as before, with mm, shoot and frames ranked and kinds 4 (switched holding a word), 5 and 6 (a runtime allocation holding no kernel lock) |
| LOCK-WAIT | printed | per word: contended (the first look found it held, or the first exchange failed), slow (over 10,000 cycles without either), takes, spin share, the longest single wait |
| KLOCK-WAIT | printed | as before, with the longest single wait |
| TESTWORDS-LEDGER-ELF | yes | the marks, and the head's shipped kernel built twice from two separate clones, equal but for the stamp |

**Before any lock moves,** LOCK-WAIT's new contended count answers the first unit's open question: ip showed
acquisitions over 10,000 cycles although every taker holds the kernel lock.

## Plants
| plant | what it breaks | forced by | red |
|---|---|---|---|
| `framesgap` | `frames.alloc` without the frames word | `pax.framesgap=US`, a gap between finding a free bit and claiming it | MEM-FRAMES-EXACT |
| `brkgap` | the mm word given back between `brk`'s check and its mapping | `pax.brkgap=US`, the same gap held open | MEM-BRK-ONE |
| `noshoot` | off-lock `munmap` frees its frames without the shootdown | 64 rounds a boot | MEM-TLB |
| `mmrank` | frames taken before mm | the first `mprotect` | LOCK-RANK-CLEAN |
| `uaccessbare` | uaccess's check-then-copy without the word | static | MM-CENSUS |
| `stopdeaf` | the requester's wait neither answers its own STOP nor counts a STOPPED target | `pax.shootslow=US`, every request's wait held open | MEM-END |

## Predictions, with what would falsify each
- **MM-OFF-KLOCK:** 0.00-0.02 of the hold cycles. Falsified at 0.05.
- **The kernel lock's use at four jobs:** from 0.83-0.89 of the wall to 0.15-0.35. Falsified over 0.5.
- **KLOCK-WAIT:** 5-20% at four jobs of the build, and 2-15% at four in the ledger kind. Falsified over 30%.
- **frames:** spins under 5% of the window. Falsified over 10%.
- **mm and ip:** contended 0 in the build and ledger kinds, whose workers are separate processes.
- **The memory kind's ordinary churn:** the longest single mm wait is under 5 ms at 2 and under 50 ms at 16; the
  longest kernel lock wait is under the same plus 1 ms.
- **MEM-CONVOY:** the sibling's wait, and the other processors' longest kernel lock wait, are each 0.5-1.5 times the
  `mmap`'s own time, which should be 15-60 ms at 2. Over any of these is a finding, not noise.
- **The mean `mmap` hold** (now an mm hold): within 20% of today's 3.7-5.3 ms.
