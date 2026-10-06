# px06 — the kernel heap

Contract: `sprints/pax/06-the-heap/px06-the-heap.md` (planning trunk
`c4f30dc`); its five sections are the empty commit `5e3938b`, committed
before the first change. Branch `px06` off `e53018d` (px05), PR pax#10.

## What changed

- **The pin.** `kernel/wolf.pin` is the wolf 0.2.24 release archive by
  digest (`501d6d3f…`, wolf-lang `294d626d`, release 404332628): it
  carries kw12's allocator hook and `libwolf_rt_none.a`. lupin stays at
  0.1.44 (px05's reason: `tests/mkw` step 6 records its refusal).
- **`tools/build-kernel`.** A kernel that allocates gets
  `NAME.rt-none.a` from wolf; the script admits the object's
  `__wolf_rt_*` imports when the archive defines them, requires
  `wolf_alloc`/`wolf_free` defined by the kernel's own objects, asserts
  that the archive, taken whole, imports only `wolf_alloc`, `wolf_free`
  and `wolf_trap`, links it after every kernel object, and disassembles
  the whole linked ELF (archive included) for xmm/ymm.
- **`kernel/heap`.** wolf's hook pair as `export fn`s over `alloc`/
  `free`, in PML4 slot 384:
  - `0xffffc00000000000`: the state page, `#[repr(c)] struct HeapState`
    (eight class-list heads, top, descriptor-page counts, the free-run
    list's head, live blocks and bytes, allocs, frees, table frames,
    frames taken), each field a `u64` at its `offset_of`;
    `0xffffc00000001000`: 64-byte page descriptors, mapped a page at a
    time as the heap grows;
  - `0xffffc04000000000`: the run zone. Pages for blocks above 2048
    bytes, in runs; free runs on one doubly linked list **in address
    order**, first-fit, boundary tags (head with the length, tail with
    the head) so a freed run merges with both neighbours in O(1); every
    page of a free run is tagged free, so a free of any page-aligned
    address in one is a double free; a free run ending at `top` is
    extended rather than stranded;
  - `0xffffc05000000000`: the class zone. Eight power-of-two classes,
    16 to 2048; a class page is carved into equal blocks threaded on its
    class's list through their first word, with a 256-bit allocated map
    in its descriptor; class pages are bumped, never returned.
  - Pages come from `frames.alloc()` and are mapped RW+NX by
    `paging.map` in the live PML4 (CR3); never unmapped. Limit 32768
    pages (128 MiB) across both zones.
  - Named panics: `heap: double free`, `free outside the heap`, `free
    with the wrong size`, `free of an address inside a block`, `free of
    an address no block starts at`, `alloc with a bad alignment`, `alloc
    of a size that is not positive`, `alloc before heap.start`, `out of
    memory, asked`.
  - No lock: wolf's freestanding runtime takes none (one CPU at a
    time), PAX runs on one CPU, and no interrupt handler allocates.
- **`kernel/interrupts`.** A page fault whose CR2 lies in slot 384 ends
  ` (heap)`; every other line is unchanged (no existing assertion
  moved).
- **Kernels.** `kmain_heap` (eight rounds, each in one `region`: a
  `List[int]` of 100000, a `Map[str, int]` of 1000 interpolated keys, a
  capturing closure, a nested `region`, one interpolated line; the
  heap's books after each round; a wolf-lang#598 witness);
  `kmain_heap_double_free`, `kmain_heap_wild_free`, `kmain_heap_oom`,
  `kmain_heap_fault`. `kmain.lu` is untouched (px07 shares it, and
  `--tail` transcripts would move).
- **`tests/mpx2-heap`** and its CI job (H1-H10, below).

## Drift (re-deriving §2)

None against the contract's §2. Two findings past it: wolf-lang#600 (a
release-tier wrong answer, below), and module `var`s readable only in
`unsafe` (E1301, by design), which moved the heap's scalars into its
own page as `frames` keeps its own.

## Prediction against measurement

| predicted (5e3938b) | measured | |
|---|---|---|
| slot 384, page runs first-fit with boundary tags, eight classes, never unmapped, limit 128 MiB, OOM a named panic | as predicted, with two changes the measurements forced (next rows) | held |
| first-fit over the free-run list (unordered) | a LIFO list grew the heap by one page in round 2 (1155 -> 1156, then flat); address order did not fix it | **changed**: the list is address-ordered |
| class pages taken from the page layer | a class page carved in round 1 after the nested region's chunks were freed landed in their hole and split it in round 2 | **changed**: class pages have their own zone; with no large block live the run layer is one free run again, and every round lands where the first did |
| heap top after round 1: 800..1100 pages | **1156** (1151 run pages + 5 class pages) | **missed**: I counted the List's 768 pages and nothing else. The round's region takes one more 1 MiB chunk for everything after the List (the ladder is at its 1 MiB ceiling), 1024 run pages together, and the nested region's chunks (~127 pages) are live beside them |
| rounds 2..8 identical top and identical free frames | identical from round 1: 1156 pages; frames 63556 (BIOS native), 63575/63573 (BIOS release), 52076/53152 (UEFI) every round | held (after the two changes) |
| live blocks and bytes back to the pre-round count | 0 blocks, 0 bytes after every round; 32217 allocs = 32217 frees | held |
| table frames for slot 384: 4..8 | **11** (3 at `start`, 8 more) | **missed**: the books, the run zone and the class zone are three separate 1 GiB ranges, each needing its own PD and PT under the slot's PDPT |
| no other suite's assertion moves | every suite green on 0.2.24 before any heap change (kasumi, `base0224`) and at head | held |

The books close exactly: frames taken = pages + book pages + table
frames = (frames before the heap) - (frames after a round), on every leg
(1187 = 1156 + 20 + 11 = 64743 - 63556 on BIOS native).

## The transcript (head, native, BIOS; kasumi, serial `6a57aa05…`)

```
PAX heap test
frames: 64799 usable, 44 below 1 MiB, 4 allocator, 64751 free
paging: limine cr3 0x000000000fe1a000, pax cr3 0x0000000000104000, 8 table frames
frames before the heap: 64743
heap: slot 384 at 0xffffc04000000000, 0 pages, 0 class pages, 0 free, 0 live blocks, 0 live bytes, 0 allocs, 0 frees, 1 book pages, 3 table frames, 4 frames taken
598: up false -> true, pages 0 -> 16, live 0 -> 1 -> 0
interp: n=100000 hex=186a0 neg=-7 pad=[  100000] ok=true c=w s=pax r=1
round 1: list 100000 sum 4999950000 bad 0, map 1000 keys bad 0 absent ok, closure 42, nested ok
after 1: live 0 blocks 0 bytes, regions 0 bytes, heap 1156 pages, frames 63556 free
… rounds 2-7 the same but for r …
interp: n=100000 hex=186a0 neg=-7 pad=[  100000] ok=true c=w s=pax r=8
round 8: list 100000 sum 4999950000 bad 0, map 1000 keys bad 0 absent ok, closure 42, nested ok
after 8: live 0 blocks 0 bytes, regions 0 bytes, heap 1156 pages, frames 63556 free
heap: slot 384 at 0xffffc04000000000, 1156 pages, 5 class pages, 1151 free, 0 live blocks, 0 live bytes, 32217 allocs, 32217 frees, 20 book pages, 11 table frames, 1187 frames taken
halt
```

The fault kernels (release, UEFI):

```
free twice: 0xffffc05000000000
PANIC heap: double free 0xffffc05000000000
block 0xffffc05000000000, free outside: 0xffff800000200000
PANIC heap: free outside the heap 0xffff800000200000
oom: 128 blocks of 1 MiB, heap 32768 pages; one more
PANIC heap: out of memory, asked 0x0000000000100000
block 0xffffc04000000000, read past the heap: 0xffffc04000001000
PANIC page fault vector 14 error 0x0000000000000000 rip 0xffffffff800048f4 rsp 0xffff80000bfa3fb0 frame 0xffff80000bfa3f00 cr2 0xffffc04000001000 (heap)
```

## The assertion table, red then green

| row | red | green |
|---|---|---|
| H1 build (the runtime archive linked, the hook pair from wolf) | `138ed6d`, kasumi: no kernels (log `c3914fa5…`) | kasumi `a78b6c9`, `1346bfd`; CI 37523293609, 37524851354 |
| H2 the empty heap | `138ed6d` (no kernels); `0390351` kasumi and CI 37522116420: the test's own regex escape (GNU sed) | as H1 |
| H3 eight rounds, every value | as H2 | as H1 |
| H4 no leak | as H2; **the plant** `3b157d1`, CI 37526582366 (job 112485006449, log `d1aada77…`): 32 FAIL H4, the heap 1172 -> 2323 -> 3474 … pages with live 0 | as H1; the revert `ecb4b4a` |
| H5 halted | `138ed6d` | as H1 |
| H6 double free | `138ed6d` | as H1 |
| H7 wild free | `138ed6d` | as H1 |
| H8 out of memory | `138ed6d` | as H1 |
| H9 heap page fault | `138ed6d`; `0390351` release BIOS and UEFI (kasumi log `8a403621…`, CI 37522116420): wolf-lang#600 deleted the branch | `f61f558` on |
| H10 the #598 witness | (added at `1346bfd`; a regression guard, see #598 below) | kasumi `1346bfd` (log `92b2fcfe…`), CI 37524851354 |

Every red run above has its FAIL lines and 0 SKIP lines. The CI rows'
counts per leg: 46 rows plus the summary at `a78b6c9`, 50 plus the
summary from `1346bfd` (H10).

## Evidence index

- Baseline: every suite on the 0.2.24 pin before any heap change
  (kasumi, `238e685`'s tree): mkw 17, mpx1 27, mpx2-frames 45,
  mpx2-paging 27, mpx2-interrupts 35 PASS; 0 FAIL, 0 SKIP lines; logs
  `a55a3060…`, `1df67e64…`, `be4b5f6d…`, `d2ed6b59…`, `88957a90…`.
- The gauntlet at head's tree (`1346bfd` = `ecb4b4a`'s; kasumi
  `full1346bfd`): expect-serial-selftest, census, mkw 17, mpx1 27,
  mpx2-frames 45, mpx2-paging 27, mpx2-interrupts 35, mpx2-heap 51
  PASS lines; every exit 0, 0 FAIL, 0 SKIP lines; mpx2-heap log
  `214d7540…`.
- hasu under KVM (nix-shell QEMU 11.1.0, the combined OVMF.fd), the
  head images built on kasumi (`images-1346bfd.tar` `cb0c42a9…`, 42
  ISOs), `--images`, three rounds of all six suites: **252/252 boots
  under KVM**, every run rc 0, 0 FAIL, 0 SKIP lines (`hasu-kvm.log`
  `92b7f432…`); mpx2-heap 60/60 boots, H4 and H10 on every leg.
- CI: red 37522116420 (`0390351`); green 37523293609 (`a78b6c9`),
  37524851354 (`1346bfd`); the plant red 37526582366 (`3b157d1`); the
  revert and the head in the PR.
- Downstream: no hosted code here; the pin moved every kernel's bytes
  (a new compiler), and every suite's assertions hold unchanged.
- wolf-lang#571's strict-evidence env governs wolf-lang's cargo gates;
  pax's suites are shell scripts over QEMU with their exit status read
  bare, so it does not apply here.

## wolf limitations met

- **wolf-lang#600 (filed)**, a release-tier wrong answer: rangeopt
  bounds `u64 >> k` as if signed, so a branch on the top half of the
  result is deleted (`if cr2 >> 39 == 0x1ffff80` never taken; even
  `a >> 63 == 1`). Hosted witness with a measured table; likely cause
  `crates/wolf_wir/src/midend/rangeopt.rs`'s `Lshr` arm. pax compares
  address ranges instead, at `kernel/interrupts` and `heap.contains`,
  each naming the issue. Audited every `>>` in `kernel/`: the rest are
  masked or not branched on (`paging.canonical` returns its compare,
  measured to survive).
- **wolf-lang#598 (the orchestrator's P0, filed by lc01)**: a module
  `var`'s value forwarded across a call that writes it, on native and
  release. Probed on both tiers (freestanding objects, `objdump`): the
  heap's shape — int-cast raw pointers, stored or loaded, a call to a
  writer, loaded again — answers right on both (native reloads through
  a real call, release keeps the store and returns 99); the module-var
  shape answers stale on both. The heap's books are therefore in its own
  page, not module `var`s; its one `var` (`up`) is written only by
  `start` and never read across a writing call: no reload site is
  needed, so no `// #598` site exists to retire. H10 reads `up` and the
  books on either side of a writing call: a guard at the module
  boundary (each module is its own object on both tiers today, so the
  forward cannot cross it now). Other pax module vars audited:
  `frames.state` (written once in `init`, read by callees),
  `apic.lint0_before`, `interrupts.breakpoint_count` (one read after
  the `int3`), `timer.tick_count` (`kmain_timer`'s loop reloads it
  through a cross-module call each iteration; I5 green on both tiers):
  none has the hazard's shape.
- Not filed, by design: module state only in `unsafe` (E1301); a `pub
  const` across modules (wolf-lang#579, open) — `interrupts` keeps its
  own copy of the heap's range.

## What the scheduler (px07) and user-mode lanes inherit

- **The lock.** `heap.alloc`/`heap.free` and wolf's runtime take no
  lock. Before a second CPU runs wolf code, or a preempted task can be
  inside the allocator, take a spinlock around both (kw11's
  `atomic_cas` acquire / `atomic_store` release). No interrupt handler
  may allocate (a handler that interpolates would re-enter the heap).
- **The runtime's root never frees.** A `List`, `Map` or string built
  outside every `region` is a root allocation, kept forever. Long-lived
  kernel loops run each iteration in a `region` (as `kmain_heap`);
  per-task scratch belongs in a task's region.
- **The runtime's ambient-region slot is one word**, not per-task: a
  context switch inside a `region` changes what the next task allocates
  into. The scheduler must save and restore it per task (wolf's runtime
  exposes no API for it today; a wolf-lang issue when px07 meets it).
- **Kernel stacks are not heap**: the heap never unmaps, and a guard
  page needs an unmapped page below each stack. Stacks belong in their
  own slot.
- **Virtual layout so far**: PML4 256 HHDM, 320 paging's test scratch,
  352 the APIC, 384 the heap (books, runs at +256 GiB, classes at +320
  GiB), 511 the image. The heap never shrinks or returns frames; memory
  pressure is a later lane's.
- **User mode**: nothing user-accessible is in slot 384 (supervisor,
  NX); user address spaces need their own lower-half tables, and
  `copy_from_user`-style reads must not be served from the kernel heap.
- **wolf-lang#600**: compare addresses by range, never by a shifted top
  half, until it is fixed. **wolf-lang#598**: keep mutable kernel state
  out of module `var`s that a callee writes, or reload after the call.
