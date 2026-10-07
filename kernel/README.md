# kernel/

The wolf kernel: first light (px01, M-PX1), physical frames (px02), paging (px03), interrupts (kw10), preemptive kernel threads (px07) and the heap (px06), on the wolf 0.2.24 release archive (px05 moved pax to the archive at 0.2.23; px07 to 0.2.24 for kw11's atomics). `kmain.lu` brings up COM1,
reads what Limine handed it and prints one line each — the banner, the
UART, the bootloader and base revision, the firmware, a memory-map
summary, the HHDM offset, the frame allocator's totals — switches to its own
paging structures (one `paging:` line), then prints `halt` and halts. `kmain_panic.lu` is a
second kernel whose overflow reaches the trap hook, which prints
`PANIC <kind> <file>:<line>` and halts. `kmain_frames.lu` exercises the
frame allocator; `kmain_double_free.lu` and `kmain_free_unusable.lu`
end in its named panics (`tests/mpx2-frames`); since px03 `kmain_frames`
runs its exercise on PAX's paging structures. `kmain_paging.lu` switches
and makes a map/unmap round trip; `kmain_text_write.lu` writes to its
own text after the switch, which must fault and, since kw10, panics
`page fault` with CR2 (`tests/mpx2-interrupts` I1). Since kw10 every
kernel loads its own GDT, TSS and IDT first (`interrupts.start()`), so
any exception panics by name; `kmain_int3.lu` takes a breakpoint and
goes on, `kmain_ud2.lu` panics `invalid opcode`, `kmain_double_fault.lu`
double-faults onto IST1, and `kmain_timer.lu` counts 20 PIT ticks
(`tests/mpx2-interrupts`). Since px07 `kmain_sched.lu` starts the
scheduler and runs rounds of threads (three that only spin and are
switched by the timer alone, three sleepers, two counting under the
spinlock and two without it), and `kmain_sched_overflow.lu` runs a
thread off its stack into its guard (`tests/mpx2-sched`).

| module | what |
|---|---|
| `serial/` | the 16550 driver on COM1: `init` (no interrupts, 115200 8N1, FIFOs; scratch and loopback checks), `put` (LSR-polled) |
| `log/` | a line writer over `serial`: `put`, `line`, `end` (CR LF), `put_byte`, `dec`, `hex`, all without allocation |
| `boot_info/` | Limine's responses (bootloader name and version, firmware type, memory map, HHDM, the image's physical base) read in wolf with `read_volatile` through `N as *T`; each request named with `extern "c" let` (kw10; `boot/limine.S` supplied the addresses before) |
| `frames/` | the physical page-frame allocator (px02): two bitmaps (free, ever-usable) over the memory map, its state in frames it takes for itself above 1 MiB, reached through the HHDM; `init`/`start`, `alloc` (row `out_of_memory`), `free` (named panics), the totals |
| `paging/` | x86-64 four-level paging (px03): `build` (a zeroed PML4; the image W^X per section from `boot/kernel.ld`'s bounds; the HHDM over usable, bootloader-reclaimable, ACPI and reserved-mapped memory, 2 MiB pages where they fit, without the image or the framebuffer), `switch_to` (EFER.NXE, CR0.WP and CR4.PGE checked, the stack mapped, MOV to CR3), `start` (both), `map`/`map_large`/`unmap` (INVLPG on the live structures)/`translate` (rows: `out_of_memory`, `misaligned`, `not_canonical`, `already_mapped`, `large_page`, `not_mapped`), `report` |
| `gdt/` | the kernel's GDT (null, kernel code 0x08 and data 0x10, user data 0x18 and code 0x20, the TSS at 0x28) and the 64-bit TSS with IST1 (a 16 KiB .bss stack), built in wolf in storage `boot/isr.S` reserves, loaded (LGDT, the segment reloads, LTR) (kw10) |
| `idt/` | 256 gates: 0-31 and 32-47 interrupt gates through `boot/isr.S`'s trampolines, #DF on IST1, the rest not present; LIDT (kw10) |
| `interrupts/` | `pax_interrupt`, the `export fn` every trampoline calls with its frame (`[abi.interrupt]`): a breakpoint prints and returns, vector 32 ticks the timer, a spurious 8259 request returns, every other vector panics `PANIC <name> vector <v> error … rip … rsp … frame …[ cr2 …[ (heap)]]` (` (heap)` for an address in the heap's slot, px06); `start`/`report` for the tables (kw10) |
| `apic/` | the local APIC's page mapped uncached at PML4 slot 352 (`0xffffb00000000000`) and LINT0 set to ExtINT, unmasked: Limine leaves it masked, and an 8259 request would never arrive (kw10) |
| `timer/` | the 8259s remapped to 32/40 and masked; the PIT's channel 0 at divisor 11932 (99.998 Hz) with line 0 alone unmasked; `tick` (EOI), `ticks`, `wait` (STI; HLT; CLI), `spurious`, `stop` (kw10; the PIT argued against the local APIC timer in the module's header) |
| `heap/` | the kernel heap and wolf's allocator hook (px06): `wolf_alloc`/`wolf_free` as `export fn`s over `alloc`/`free`; PML4 slot 384 (`0xffffc00000000000`): a state page and 64-byte page descriptors, then the heap's pages from `0xffffc04000000000`, each a `frames.alloc()` frame mapped RW+NX by `paging.map` as the heap grows, never unmapped; address-ordered first-fit page runs with boundary tags for sizes above 2048, eight power-of-two size classes (16-2048) in their own zone (`0xffffc05000000000`) with a per-page allocated map; limit 32768 pages (128 MiB); named panics (`PANIC heap: double free …`, `free outside the heap`, `free with the wrong size`, `out of memory`, …); `report`, `pages`, `live_blocks`, `frames_taken`, …; `alloc`/`free` under `sync.heap()` (px07's threads are preempted); no `region` across a thread switch until wolf-lang#611 |
| `panic/` | `wolf_trap`, the freestanding trap hook, in wolf; `fail(what, v)`, a fault the kernel detects, by name; `halt` |
| `sync/` | the spinlock (px07): a lock is an 8-byte word's address; `acquire` saves RFLAGS and clears IF, then test-and-test-and-set (`atomic_load` relaxed, `atomic_cas` acquire/relaxed, kw11), `release` is a release store and IF as saved; `irq_save`/`irq_restore`/`enable`, `relax` (PAUSE), `console()` (the lock threads write whole lines under) |
| `sched/` | kernel threads on one CPU (px07): 16 records in `boot/sched.S`'s `.bss` (`#[repr(c)] Thread`, its words at `offset_of`), slot 0 the kernel's own context, slot 1 the idle thread (`pax_idle`, HLT with IF set); each stack four frames mapped RW NX at the top of its slot's 64 KiB in PML4 slot 416 (`0xffffd00000000000`), the 48 KiB below never mapped (the guard); a FIFO run queue; `preempt` (the tick: wake sleepers, rotate after a two-tick quantum, idle gives way at once), `switched` (after `pax_switch`), `create(body, arg)`, `yield`, `sleep(n) -> (from, woke)`, `wait_all`, `exit` (the stack reaped by the next `create` or `wait_all`), `guard_of` (for the overflow panic), `report` |
| `schedtest/` | the thread bodies `tests/mpx2-sched` runs, as `export fn`s the kernels name with `extern "c" let` (px07) |

- `wolf.pkg` lists `../boot/io.S` (port I/O, the halt),
  `../boot/cpu.S` (px03: CR0, CR3, CR4, EFER, INVLPG, CPUID's NX bit;
  kw10: CR2, IA32_APIC_BASE), `../boot/isr.S` (kw10: the 48
  trampolines, the GDT/TSS/IDT/IST1 storage, LGDT/LTR/LIDT, STI-HLT-CLI;
  px07: the common path resumes the frame `pax_interrupt` returns) and
  `../boot/sched.S` (px07: `pax_switch`, `pax_thread_entry`, `pax_idle`,
  PAUSE, the IF routines, the thread table and lock words)
  under `asm`: wolf
  assembles them for the kernel's target and refuses a call into anything
  off their roster (`[abi.asm.roster]`, E1306). The target is passed by
  `tools/build-kernel` (`--target x86_64-unknown-none`), not set here.
- Each kernel file is a standalone entry (`//! member: false`): a
  directory is one wolf module, and two `kmain`s would collide. The
  modules are child directories, imported by name (`use log`); imports
  are file-scoped and an unused one is an error (E0305), so a kernel
  names `panic` (for `panic.halt()`) even though the link would want
  only its `wolf_trap`.
- Limine's response pointers are bootloader-written, so every read of
  one is a `read_volatile` (KWC kw07, wolf-lang `eb955c3b`), afresh per
  call, through an address cast to a pointer (kw06). Limine's struct
  layouts are still read word by word at fixed offsets (`boot_info`;
  kw08's `offset_of` on `#[repr(c)]` mirrors is open to a later lane). A
  symbol's address (each request in `boot/start.S`, `boot/kernel.ld`'s
  bounds, `boot/isr.S`'s tables) is named with `extern "c" let` since
  kw10 (wolf-lang kw09); `boot/limine.S`, which returned those
  addresses while wolf could not spell them (wolf-lang#529), is
  retired.
- The frame allocator keeps its state in memory it owns (module state
  holds scalars only, `[mem.static.3]`), and that memory's HHDM address
  in a module `var`, read through one unsafe accessor (`st()`, px05;
  px02 and px03 threaded it through every call of `frames` and `paging`
  while wolf had no module state, wolf-lang#529). Its header is a
  `#[repr(c)] struct FrameState` whose fields are read and written as
  `u64`s at their `offset_of` (`[abi.layout.query]`), the bitmaps at
  `size_of(FrameState)`. `paging` asks `frames` for table frames and the
  HHDM offset and takes only the PML4's physical address.
- wolf has no bitwise complement (wolf-lang#575): alignment is written
  `x - x % PAGE`, masks spelled whole (`paging`'s `ADDR`, `ADDR_2M`).
- Constants are module `const`s in every module (px05 retired
  px01-px03's commented literals in `serial`, `frames` and `paging`;
  wolf 0.2.22 refused a module-level `const`, wolf-lang#560, closed by
  kw09). A `pub const` read from another module is still refused
  (wolf-lang#579), so `kernel/timer` exports its constants, and
  `kernel/paging` its flags, as functions.
- Module state: kw10's modules keep scalars in module `var`s (the tick
  and breakpoint counters, kw09); tables live in `.bss` that
  `boot/isr.S` reserves, because module state holds scalars only
  (`[mem.static.3]`). A handler resuming past a fault would write the
  frame's RIP through `f as *u64` at `offset_of(Frame, rip) / 8`: a
  store to a field of a raw element is refused (wolf-lang#577).
- A context switch (px07) is the trampoline returning another
  thread's frame: `pax_interrupt` returns `*Frame`, the common path
  moves it into %rsp before the pops, and since a kernel thread is
  interrupted at CPL 0 its frame is on its own stack, so `iretq`
  restores that thread's RSP with its RIP. A voluntary switch builds
  the same frame by hand (`boot/sched.S`'s `pax_switch`, vector 0x81).
  A thread body is an `export fn` in a module other than the one
  naming it with `extern "c" let NAME: *u8`: wolf has no C
  function-pointer value (wolf-lang#520) and the `extern` in the
  export's own module is E0302. A lock word lives in assembly-reserved
  `.bss` because a module `var` has no address (wolf-lang#597).
- `wolf.pin` names wolf: the 0.2.24 release archive by digest (px07;
  0.2.23 from px05;
  `tools/fetch-wolf` stages it and never builds; px02 and kw10 built
  wolf-lang `eb955c3b` and `6a4e6151` from source while no release
  carried kw06-kw09), and lupin's release and digest
  (`tools/fetch-lupin`; held at 0.1.44 for `tests/mkw` step 6's
  recorded refusal).

`tests/mpx2-sched` (px07) builds kmain_sched and
kmain_sched_overflow on both tiers, boots them under SeaBIOS and OVMF,
and checks the trampoline's shape (S0), three threads alternating by
preemption alone (S1), sleep waking on the tick (S2), exit reclaiming
the stacks (S3), the locked counter exact where the unlocked control
loses updates (S4), the overflow into the guard panicking by name (S5)
and the halt (S6).

- A kernel that uses `List`, `Map`, interpolation, a capturing closure
  or `region` calls into wolf's freestanding runtime (wolf-lang kw12):
  wolf writes `libwolf_rt_none.a` beside the object as
  `NAME.rt-none.a`, `tools/build-kernel` links it after the kernel's
  objects, and the kernel supplies `wolf_alloc`/`wolf_free` by `use
  heap` (and calls `heap.start()` after `paging.start()`). A block made
  outside every `region` is never freed (the runtime's process root),
  so long-running kernel code allocates inside a `region` (px06's
  `kmain_heap` runs each round in one). Module `var`s are read only
  inside `unsafe` (E1301), so the heap's books are a `#[repr(c)] struct
  HeapState` in its own state page at `offset_of`, as `frames` keeps
  its own. The release tier deletes a branch on the top half of a
  `u64 >> k` (wolf-lang#600): address checks are written as ranges.

`tests/mpx2-heap` builds kmain_heap and the four heap fault kernels on
both tiers, boots them under SeaBIOS and OVMF, and checks the runtime
linked, eight rounds of allocating kernel code, no leak (live blocks
back to zero, the heap's pages and the free frames unchanged after
every round, every frame the heap holds accounted for), and the double
free, wild free, out-of-memory and heap page-fault panics by name.

`tests/mpx2-frames` builds kmain and the three frames kernels on both
tiers, boots them under SeaBIOS and OVMF, and checks the totals against
the map, the exhaust, the touch, the reuse, the two named panics and
every halt. `tests/mpx1` builds kmain and kmain_panic on both tiers, boots them under SeaBIOS
and OVMF, asserts the transcript and the panic line, and proves each halt
through QEMU's monitor (`tools/qemu-halt`). M-KW's kernels (`KWC`,
`TRAP 1`) are frozen in `tests/mkw.d` and still booted by `tests/mkw`.
`docs/BOOT.md` says what the boot protocol asks of the object.

## User mode (px09)

`kmain_user.lu` runs programs in ring 3, each in an address space of
its own, on a kernel thread of its own that enters ring 3 by `iretq`;
`kmain_user_smap.lu` and `kmain_user_smep.lu` are the SMAP and SMEP
witnesses (`tests/mpx3-user`).

| module or file | what |
|---|---|
| `user/` | the SYSCALL MSRs (EFER.SCE, STAR `0x0010_0008 << 32`, LSTAR, FMASK `0x44700`), SMEP and SMAP when CPUID has them; `load(prog)` (a process's PML4 from `paging.new_space`, its program's bytes at `0x400000` read-execute user, a 16 KiB stack below `0x7ffffffff000` read-write no-execute user, the page below it never mapped), `describe`, `pax_user_thread` (the thread body that enters ring 3); `syscall` (Linux's numbers: `write` 1 to the serial console with every page of the buffer checked present and user first, else `-EFAULT`; `exit` 60; anything else `-ENOSYS`), `kill` (an exception in ring 3 ends the program by name), `from_user`, the ring-3 tick count |
| `paging/` (px09 additions) | `new_space` (entries 256-511 copied from the kernel's PML4: the kernel half's tables shared), `map_user` (U/S at every level), `user_ok` (the walk a user read takes), `free_user` (the user half's pages, tables and the PML4 back to `frames`), `live`, `load` (MOV to CR3), `kernel_half` |
| `gdt/` (px09 additions) | `set_rsp0`/`rsp0`: the TSS's RSP0 as two aligned 32-bit halves (offset 4; a misaligned 8-byte store is a UB row, ruling #36) |
| `sched/` (px09 additions) | a thread's `cr3` and `prog` (the record is 88 bytes); `run_next` makes the switched-in thread's space live and points RSP0 and SYSCALL's stack word at its kernel stack's top; `create_user(body, prog, cr3)`; `end_current(f)` ends the running thread from a handler and returns the next thread's frame; `reap` frees a dead thread's address space with its stack |
| `../boot/user.S` | `pax_syscall_entry` (LSTAR: onto the thread's kernel stack, the interrupt-shaped frame, vector 0x100, into `pax_isr_common`), `pax_enter_user` (`iretq` to CPL 3, registers zeroed), `pax_peek_user` (a user byte, STAC/CLAC under SMAP), `pax_jump`, `pax_syscall_state` |
| `../boot/isr.S` (px09 addition) | `pax_sysret`: a resumed frame with vector 0x100, CS 0x23 and a RIP below `0x7ffffffff000` leaves by `sysretq`; every other by `iretq` |
| `../user/programs.S` | the first user programs, flat position-independent blobs in the kernel's `.rodata` (never executable in ring 0): hello, the five fault cases, badptr, spin; `pax_uprogs` their bounds |

- The way in: `user.load` and `sched.create_user` (thread context, IF
  clear); `run_next` loads the thread's CR3; the body
  `pax_user_thread` calls `pax_enter_user`, whose `iretq` drops to CPL
  3. Interrupts and exceptions from ring 3 arrive on RSP0, system calls
  on the same stack top through `pax_syscall_state` word 0: SYSCALL
  switches no stack.
- The way out: `exit` and a fault both end the thread in the handler
  (`sched.end_current`): `sched.exit` switches by `pax_switch`, which
  is for thread context. The address space is freed by `reap`, in
  thread context, as stacks are (px07).
- Every word of a frame is read and written at its index (a store to a
  field of a raw element is refused, wolf-lang#577); the state handlers
  write lives in `pax_syscall_state` and the thread records, read
  volatile, never in module `var`s (wolf-lang#598, not fixed in 0.2.24);
  no `region` anywhere near a return to ring 3 (wolf-lang#611).
- Not yet: FXSAVE/XSAVE per thread (no program here touches x87 or
  SSE, and the kernel uses neither; px10's static binaries will),
  `exit_group` (231), an ELF loader, argv/envp/auxv on the stack (px10),
  SWAPGS and per-CPU state (SMP), an IST for NMI (the window between
  `pax_sysret`'s stack load and `sysretq`).
