# Lock ranks, `pax.smpdebug` and the ledger per lock word (written before the first change)

Base: trunk `0197fc4e` (SMP stage 3's first unit, the kernel lock's ledger, merged). This is stage 3a's first unit. It
changes the test build alone; the shipped kernel stays byte-equal to trunk's where the machine loads it, and that
comparison stays a gated row.

## Why
Stage 3a splits the kernel lock, and the ledger set the order. `brk` and `mmap` hold the lock 0.69-0.83 of all hold
time at four jobs, so the memory calls come off it first, under a per-space lock and a frames lock. Before any new
lock lands, two things must exist:
- **an order check**, so the first new lock taken in the wrong order is a named stop in a test boot, not a hang in the
  field. Nothing checks lock order today: `kernel/sync`'s eight words document their order in comments only;
- **the ledger per lock word**, so a split that only moves the wait from the kernel lock to the frames lock shows as
  that. The ledger times the kernel lock alone today.

Both live in the test build (`tools/build-kernel --test-words`), as the ledger does. The cost take showed that a
shipped hook makes a claim one cannot measure cheaply, so the shipped kernel gains nothing.

## What it adds to the test build
**A test-build module, `lockled`** (`tests/mpx6-smp.d/lockled.lu`, copied to the test build's `kernel/lockled/`). It
uses only `kernel/percpu`, so `kernel/sync` can call it without an import cycle (sync, lockled, percpu). Per processor
and per lock word (the eight `kernel/sync` words, by their index; any other address is not counted):
- acquisitions, releases, contended acquisitions (a spin over 10,000 cycles), spin cycles, hold cycles, the longest
  hold;
- a held-words mask, and the first order violation seen, with the word taken and the word held.

Its tables are pages the test kernel takes from kernel/frames at its boot. Before that, every call returns at once,
so the boot's early acquisitions are not counted. Each processor writes only its own rows, so nothing new is
synchronized.

**Hooks in the test build's copy of `kernel/sync`**, by `tests/mpx6-smp.d/ledger.patch`, in the ledger's forms only:
- `use lockled`;
- `acquire`: the TSC before the spin and `lockled.took(lock, t0)` after the exchange succeeds;
- `release`: `lockled.gave(lock)` before the release store.

LEDGER-PATCH keeps its guarantee: no new lock, no interrupt mask, no other path. It now allows kernel/sync and those
forms.

**The ranks.** Lower is taken first:

| word | rank | the order it states |
|---|---|---|
| the kernel lock | 0 | outermost; nothing takes it holding a word (kernel/klock) |
| tcp | 10 | before ip, arp and net; never with udp |
| udp | 11 | before ip, arp and net |
| ip | 12 | before arp and net |
| icmp | 13 | never held across a call into ip |
| arp | 14 | before net |
| net | 15 | |
| console | 20 | whole lines written under it; nothing taken inside it but the heap |
| heap | 21 | innermost: an allocation can happen anywhere |

- The network's five come from kernel/sync's comments.
- The console and the heap come from where they are taken: console around whole lines, the heap by any allocation.
- **Checked under `pax.smpdebug`** (a new test word): taking a word whose rank is at or below one already held on
  that processor is a violation.
- The kernel lock's own checks run in the ledger's existing hooks. Taking it fresh while holding a word is a
  violation, and so is giving it back while holding one, which would carry the word into ring 3 or the idle loop.
- A violation is noted where it happens and reported at that processor's next fresh take of the kernel lock (the
  ledger's hook, in kernel/interrupts' entry). There, a line names it and the kernel panics:
  ```
  testwords: LOCK-RANK cpu C took WORD (rank R) holding WORD (rank S)
  PANIC lock rank: a word taken out of order, cpu 0x…
  ```
  kernel/sync cannot call kernel/panic itself without an import cycle, which is why the report waits for that hook.
- **`pax.rankflip`** (a new test word): one second after CPU 0's ticks begin, CPU 0's tick takes console and then net,
  out of order, once, and gives both back. Under the kernel lock neither word can be contended, so it cannot hang.

**`/proc/pax-klock`** gains one line per word and processor that took it:
```
lock WORD cpu C took N gave G contended K spin S hold H longest L
```
and a `lock-ranks checked|off` line.

## Rows
- **LOCK-RANK** (new, gated): a new kind, `rank`, boots the test build with `pax.smpdebug pax.rankflip` at 2
  processors. Wanted: the line `testwords: LOCK-RANK cpu 0 took net (rank 15) holding console (rank 20)` and the
  panic after it.
  - Red first at the tree with the row and `pax.rankflip`, before the check: the boot runs to its end, no line.
- **LOCK-RANK-CLEAN** (new, gated): every other test-built boot (end-nooff, panic, panic2, leave, ledger) now runs
  with `pax.smpdebug`. Each must print `lock-ranks checked` and no LOCK-RANK line.
- **KLOCK-LEDGER (d)** (new clause, gated): at every read of `/proc/pax-klock` in the ledger kind, each word's
  acquisitions equal its releases on every processor. The reader holds the kernel lock, and every word is taken
  inside it, so none can be open at a read.
- **LOCK-WAIT** (new, printed, never gated here): per word, its spin cycles over the window summed over the
  processors, its contended count, and its holds.
- **TESTWORDS-LEDGER-ELF:**
  - the test build must hold two more marks, the text `LOCK-RANK ` and lockled's symbols;
  - the shipped kernel must hold neither, and no `smpdebug` or `rankflip` text;
  - with `SMP_SHIPPED_AGAINST`, the shipped kernel must equal trunk's where the machine loads it, as now.
- **KERNEL-NO-LEDGER:** kernel/ and boot/ also name no `lockled`, `smpdebug`, `rankflip` or `LOCK-RANK`.

## Plants (one file, one hunk each)
- `rankblind`: testwords never reports a noted violation. Wanted red: LOCK-RANK.
- `lockopen`: lockled's `gave` counts no release. Wanted red: KLOCK-LEDGER (d).
- `rankship`: the shipped `kernel/sync` gains a `smpdebug` function. Wanted red: KERNEL-NO-LEDGER, and
  TESTWORDS-LEDGER-ELF's comparison against trunk's kernel.

## Prediction (each falsifier stated before the first change)
- **LOCK-RANK:** the named line and the panic in every `rank` boot, both tiers and both firmwares.
  - Wrong if any `rank` boot runs to its end. That would be the instrument's own failure.
- **LOCK-RANK-CLEAN:** no violation in any other test-built boot with the declared table.
  - Wrong if one appears. Then either the table is wrong or the kernel has a real inversion. Either way the path is
    named here, and the table changes only with that path written beside it.
- **Which words the suite's boots take:** console alone.
  - The suite boots `nonet`, so the network's five are never taken, and the multi-processor kernel never starts the
    heap (SMP-NOHEAP).
  - Wrong if any other word is taken: an unexpected path, named.
  - So in this unit the network's ranks are kernel/sync's documented order, checked by no boot. That is said plainly.
- **LOCK-WAIT for console** at 2 and 4 processors: under 0.1% of the window, and 0 contended.
  - Every taker of console holds the kernel lock, so console can never be contended.
  - Wrong if any acquisition is contended: some path takes console outside the kernel lock, and the census must
    find it before 3a.2.
- **KLOCK-LEDGER (d):** green in every ledger boot. (a)-(c) stay green, and the known hold stays 20 ms ± 5%.
- **The shipped kernel:** byte-equal to trunk's but the commit stamp. kernel/ is not touched.
- **No timing claim** is made for the test kernel's extra hooks. Any timing claim is held to stage 3a's timing terms:
  the whole host quiet, separately built images rotated, a pre-registered margin and interval, an A/A check, sized
  in advance.

## Order, red first
1. rows-selftest cases for LOCK-RANK, LOCK-RANK-CLEAN, KLOCK-LEDGER (d) and LOCK-WAIT, red at the rows.py before
   them.
2. rows.py, the `rank` kind, `pax.smpdebug` on the test-built kinds, `pax.rankflip` in the test words. LOCK-RANK red
   in a test boot: there is no check yet.
3. lockled, the sync hooks in the patch, tools/build-kernel copying lockled, ledger-patch.py's forms and names, the
   ELF marks. The rows green.
