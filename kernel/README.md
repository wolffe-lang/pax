# kernel/

The wolf kernel: first light (px01, M-PX1), physical frames (px02), paging (px03), interrupts (kw10), preemptive kernel threads (px07), the heap (px06) and user mode (px09, below), on the wolf 0.2.28 release archive (px05 moved pax to the archive at 0.2.23; px07 to 0.2.24 for kw11's atomics; px10 to 0.2.25; px16 to 0.2.26; px21a to 0.2.27 for the ambient pair; px36 to 0.2.28). `kmain.lu` brings up COM1,
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
thread off its stack into its guard (`tests/mpx2-sched`). Since px08
`kmain_tour.lu` and `kmain_tour_text.lu` are a tour of the kernel: px01-px07's
stages in one boot (not the heap or user mode), each under a heading with a pause
between them so it can be read (`kernel/pax_tour`), ending in a stack overflow or a write to
text (`tests/tour`, `tools/tour`).

| module | what |
|---|---|
| `serial/` | the 16550 driver on COM1: `init` (no interrupts, 115200 8N1, FIFOs; scratch and loopback checks), `put` (LSR-polled); px13: `receive_on` (a one-byte receive trigger, IER's received-data interrupt), `ready`, `receive` |
| `log/` | a line writer over `serial`: `put`, `line`, `end` (CR LF), `put_byte`, `dec`, `hex`, all without allocation |
| `boot_info/` | Limine's responses (bootloader name and version, firmware type, memory map, HHDM, the image's physical base) read in wolf with `read_volatile` through `N as *T`; each request named with `extern "c" let` (kw10; `boot/limine.S` supplied the addresses before) |
| `frames/` | the physical page-frame allocator (px02): two bitmaps (free, ever-usable) over the memory map, its state in frames it takes for itself above 1 MiB, reached through the HHDM; `init`/`start`, `alloc` (row `out_of_memory`), `free` (named panics), the totals |
| `paging/` | x86-64 four-level paging (px03): `build` (a zeroed PML4; the image W^X per section from `boot/kernel.ld`'s bounds; the HHDM over usable, bootloader-reclaimable, ACPI and reserved-mapped memory, 2 MiB pages where they fit, without the image or the framebuffer), `switch_to` (EFER.NXE, CR0.WP and CR4.PGE checked, the stack mapped, MOV to CR3), `start` (both), `map`/`map_large`/`unmap` (INVLPG on the live structures)/`translate` (rows: `out_of_memory`, `misaligned`, `not_canonical`, `already_mapped`, `large_page`, `not_mapped`), `report` |
| `gdt/` | the kernel's GDT (null, kernel code 0x08 and data 0x10, user data 0x18 and code 0x20, the TSS at 0x28) and the 64-bit TSS with IST1 (a 16 KiB .bss stack), built in wolf in storage `boot/isr.S` reserves, loaded (LGDT, the segment reloads, LTR) (kw10) |
| `idt/` | 256 gates: 0-31 and 32-47 interrupt gates through `boot/isr.S`'s trampolines, #DF on IST1, the rest not present; LIDT (kw10) |
| `interrupts/` | `pax_interrupt`, the `export fn` every trampoline calls with its frame (`[abi.interrupt]`): a breakpoint prints and returns, vector 32 ticks the timer, a spurious 8259 request returns, every other vector panics `PANIC <name> vector <v> error … rip … rsp … frame …[ cr2 …[ (heap)]]` (` (heap)` for an address in the heap's slot, px06); `start`/`report` for the tables (kw10) |
| `apic/` | the local APIC's page mapped uncached at PML4 slot 352 (`0xffffb00000000000`) and LINT0 set to ExtINT, unmasked: Limine leaves it masked, and an 8259 request would never arrive (kw10) |
| `timer/` | the 8259s remapped to 32/40 and masked; the PIT's channel 0 at divisor 11932 (99.998 Hz) with line 0 alone unmasked; `tick` (EOI), `ticks`, `wait` (STI; HLT; CLI), `spurious`, `stop` (kw10; the PIT argued against the local APIC timer in the module's header) |
| `heap/` | the kernel heap and wolf's allocator hook (px06): `wolf_alloc`/`wolf_free` as `export fn`s over `alloc`/`free`; PML4 slot 384 (`0xffffc00000000000`): a state page and 64-byte page descriptors, then the heap's pages from `0xffffc04000000000`, each a `frames.alloc()` frame mapped RW+NX by `paging.map` as the heap grows, never unmapped; address-ordered first-fit page runs with boundary tags for sizes above 2048, eight power-of-two size classes (16-2048) in their own zone (`0xffffc05000000000`) with a per-page allocated map; limit 32768 pages (128 MiB); named panics (`PANIC heap: double free …`, `free outside the heap`, `free with the wrong size`, `out of memory`, …); `report`, `pages`, `live_blocks`, `frames_taken`, …; `alloc`/`free` under `sync.heap()` (px07's threads are preempted); `ambient`/`set_ambient`, the runtime's ambient-region slot, which `sched` saves and restores per thread at every switch (px21a): a `region` may stay open across a yield, a preemption or a wait |
| `panic/` | `wolf_trap`, the freestanding trap hook, in wolf; `fail(what, v)`, a fault the kernel detects, by name; `halt` |
| `sync/` | the spinlock (px07): a lock is an 8-byte word's address; `acquire` saves RFLAGS and clears IF, then test-and-test-and-set (`atomic_load` relaxed, `atomic_cas` acquire/relaxed, kw11), `release` is a release store and IF as saved; `irq_save`/`irq_restore`/`enable`, `relax` (PAUSE), `console()` (the lock threads write whole lines under) |
| `sched/` | (px26: a process is a group of slots sharing a leader's area and address space — `clone_thread`, `end_thread`, `end_with` for the whole group, a leader held while its threads live, `exec_alone`; futex waiters (`futex_wait`, `futex_wake`); the pending signal sets, the thread that takes a process's signal, and `poke`, which readies a waiting thread a signal will reach) kernel threads on one CPU (px07): 16 records in `boot/sched.S`'s `.bss` (`#[repr(c)] Thread`, its words at `offset_of`), slot 0 the kernel's own context, slot 1 the idle thread (`pax_idle`, HLT with IF set); each stack four frames mapped RW NX at the top of its slot's 64 KiB in PML4 slot 416 (`0xffffd00000000000`), the 48 KiB below never mapped (the guard); a FIFO run queue; `preempt` (the tick: wake sleepers, rotate after a two-tick quantum, idle gives way at once), `switched` (after `pax_switch`), `create(body, arg)`, `yield`, `sleep(n) -> (from, woke)`, `wait_all`, `exit` (the stack reaped by the next `create` or `wait_all`), `guard_of` (for the overflow panic), `report` |
| `process/` | processes (px14): a program's image and psABI stack (moved from `user/`), `clone`/`clone3`/`vfork` (CLONE_VM\|CLONE_VFORK: the child borrows the parent's space, the parent waits until it execs or ends), `execve` (path, argv, envp copied out first; close-on-exec, handled signals reset, the old space given back or handed back to the vfork parent), `wait4`/`waitid` (zombies reaped, Linux's status words, WNOHANG, a blocked wait re-runs when a child ends), px26: a thread by `clone`/`clone3` with CLONE_THREAD (`sched.clone_thread`), a census line every 2500th; `execve` ends a process's other threads first; `who`, the `user: <name> pid <n>` prefix; the signal calls moved to `signal/` |
| `signal/` | signals delivered (px26): `rt_sigaction`, `rt_sigprocmask` (a mask a thread), `rt_sigpending`, `kill`, `tgkill`, `tkill`; `on_return`, which every frame about to resume in ring 3 passes through (`interrupts`) and which takes the thread's pending signals — ignore, terminate (the process ends, its wait status the signal), stop refused by name, or a handler on a frame laid on the thread's stack: the extended state as XSAVE wrote it with its two magics, siginfo, ucontext with every register, the restorer's address; `rt_sigreturn` puts it all back and leaves by IRETQ; a waiting system call is run again or answers -EINTR by what it was (`sched`'s `W_*`) and SA_RESTART; `fault` gives an exception in ring 3 to a handler; `tty` raises the console's signals for every process |
| `futex/` | the `futex` call (px26): wait, wake, their bitset forms, FUTEX_PRIVATE_FLAG (a key bit: a private wait is not reached by a wake without it), relative and absolute timeouts; the key is the word's physical address; waiters are threads in `sched`'s FUTEX state, woken longest-waiting first; other operations refused by name |
| `rtc/` | the CMOS real-time clock read once at `user.start` (px26): seconds since the epoch for CLOCK_REALTIME, `time` and `gettimeofday` |
| `tree/` | the writable file tree, in memory (px27): inodes, files in frames, directories of records, the initramfs as its first contents, a cap and `ENOSPC` (below, "The writable tree") |
| `schedtest/` | the thread bodies `tests/mpx2-sched` runs, as `export fn`s the kernels name with `extern "c" let` (px07) |
| `pax_tour/` | the tour's stages (px08): each calls the subsystems above as their test kernels do and prints their reports under a heading; `leaf`, a read-only walk of the live page tables for the permissions stage 3 prints; `pax_tour_worker`, stage 5's named thread body; the pauses between stages (the PIT's count polled before the timer interrupt is live, `timer.wait`, then `sched.sleep`) |

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
  `#[repr(c)] struct FrameState` whose fields are read and written in
  place through a `*FrameState` (`hdr()[0].free -= 1`, wolf 0.2.26,
  wolf-lang#577; px05 to px15 wrote them as `u64`s at their
  `offset_of`), the bitmaps at `size_of(FrameState)`. `heap`'s books
  keep the `offset_of` words through one unsafe site, `rd`/`wr`. `paging` asks `frames` for table frames and the
  HHDM offset and takes only the PML4's physical address.
- Alignment is `x & !(PAGE - 1)` and a bit is cleared with `x & !BIT`
  (`!` on an integer, wolf 0.2.26, wolf-lang#575; until px16 `x - x %
  PAGE` and `0xffffffffffffffff ^ BIT`); the address masks stay spelled
  whole (`paging`'s `ADDR`, `ADDR_2M`). A 32-bit flags test keeps
  `0xffffffff ^ KNOWN` (a 64-bit `!` would test the high half too).
- Constants are module `const`s in every module (px05 retired
  px01-px03's commented literals in `serial`, `frames` and `paging`;
  wolf 0.2.22 refused a module-level `const`, wolf-lang#560, closed by
  kw09). Another module reads a `pub const` as `timer.MASTER_BASE`,
  `paging.RW` (wolf 0.2.26, wolf-lang#579; until px16 the constants
  were exported as `pub fn`s).
- Module state: kw10's modules keep scalars in module `var`s (the tick
  and breakpoint counters, kw09); tables live in `.bss` that
  `boot/isr.S` reserves, because module state holds scalars only
  (`[mem.static.3]`). A handler resuming past a fault would write the
  frame's RIP as `f[0].rip = v` (wolf 0.2.26, wolf-lang#577). A kernel
  that cannot go on calls `panic.fail` or `panic.halt`, both `-> never`
  (wolf 0.2.26, wolf-lang#572): no value follows the call.
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
- `wolf.pin` names wolf: the 0.2.28 release archive by digest (px36;
  0.2.27 from px21a, 0.2.26 from px16, 0.2.25 from px10, 0.2.24 from px07, 0.2.23 from px05;
  `tools/fetch-wolf` stages it and never builds; px02 and kw10 built
  wolf-lang `eb955c3b` and `6a4e6151` from source while no release
  carried kw06-kw09), and lupin's release and digest
  (`tools/fetch-lupin`; 0.1.51, 0.2.28's pairing, since px36; 0.1.50 from px21a; 0.1.49 from px16; 0.1.48
  from px10: it had
  been held at 0.1.44 for `tests/mkw` step 6's recorded clap error,
  which 0.1.48 replaces with an `unsupported` verdict naming the
  target).

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
| `../user/programs.S` | the first user programs, flat position-independent blobs in the kernel's `.rodata` (never executable in ring 0): hello, the five fault cases, badptr, spin1 and spin2 (each checking a mark of its own in a register and on its stack); `pax_uprogs` their bounds |

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
- Every word of a frame is read and written at its index, volatile
  (wolf 0.2.26's `f[0].rax = v`, wolf-lang#577, is an ordinary access the
  compiler may merge or move); the state handlers
  write lives in `pax_syscall_state` and the thread records, read
  volatile, never in module `var`s (wolf-lang#598, not fixed in 0.2.24);
  no `region` is left open where a system call gives up its kernel
  stack (a wait that runs the call again, an exit, `execve`): the code
  after it never runs (`sched`'s "Regions"; a return to ring 3 itself
  switches no thread and needs nothing saved).
- Not yet: FXSAVE/XSAVE per thread (no program here touches x87 or
  SSE, and the kernel uses neither; px10's static binaries will),
  `exit_group` (231), an ELF loader, argv/envp/auxv on the stack (px10),
  SWAPGS and per-CPU state (SMP), an IST for NMI (the window between
  `pax_sysret`'s stack load and `sysretq`).

## The loader (px10)

| module or file | what |
|---|---|
| `initramfs/` | a read-only view of the `newc` archive Limine hands over as the first module (Documentation's initramfs buffer format, `cpio(5)`): `check`/`problem` walk it once (NUL padding between archives skipped, `TRAILER!!!` ends one; a compressed archive, a bad magic, a field that is not hex or a size past the end refused by name), `lookup(path)` finds a regular file (one leading `/` dropped from the query, `./` or `/` from the entry), `data`/`size`/`name_*` read it in place, `report` lists it |
| `elf/` | the ELF64 loader for a static `ET_EXEC` x86-64 file: `refusal` checks the header and every `PT_LOAD` before anything is mapped (`ET_DYN`, `PT_INTERP`, a 32-bit, big-endian or non-x86-64 file, segments misaligned, past the file, below 64 KiB, past `0x7f0000000000`, overlapping or sharing a page with different permissions, each refused by name), `load` maps each segment's pages with its permissions (W → RW, no X → NX) in a fresh user half and copies `p_filesz` bytes, the rest zero; `aux` gives AT_PHDR (`PT_PHDR`, else where the headers land), AT_PHNUM, AT_PHENT, AT_ENTRY |
| `fpu/` and `../boot/fpu.S` | CR0 (EM and TS clear, MP set), CR4 (OSFXSR, OSXMMEXCPT, and OSXSAVE with XCR0 = x87 \| SSE \| AVX when CPUID has XSAVE and AVX), one area per thread slot from a frame each, a template (FCW 0x037f, MXCSR 0x1f80: Linux's state at execve) copied into a new thread's area, and at every switch XSAVE64 (or FXSAVE64) of the outgoing thread, XRSTOR64 (or FXRSTOR64) of the incoming one; nothing before `fpu.start` |
| `user/` (px10 additions) | `exec(body, path, argv, envp)`: the file from the initramfs, `elf.refusal`, a fresh space, `elf.load`, a 32-page stack below `0x7ffffffff000` holding the psABI's initial block (argc, argv, envp, the auxiliary vector AT_PHDR … AT_EXECFN, AT_RANDOM's 16 bytes, the strings), and a process thread; `exit_group` (231) |
| `sched/` (px10 additions) | the record grows to 120 bytes (an ELF process's entry, user stack pointer and name); `create_process`; `run_next` calls `fpu.switch` when the slot changes; a new thread's area is reset to the template |
| `paging/` (px10 addition) | `map_modules`: each Limine module's own pages, read-only no-execute in the HHDM (memory-map type 6 is left out of the HHDM with the image) |
| `boot_info/`, `../boot/start.S` (px10) | the module request; `module_count`, `module_addr`, `module_size`, `module_path_byte` |
| `kmain_loader.lu` | lists the initramfs, runs `/bin/hello one two`, two `hello spin` at once, six refusals and `/bin/wolf-hello` when present, checks every frame came back, halts (`tests/mpx3-loader`) |
| `../user/elf/hello.S`, `../user/elf/wolf_hello.lu` | the test program (no libc; checks what execve hands it and prints it the same way on Linux) and the gap census's wolf program |

- The programs are built on the host: `tools/mkuser` (hello and its
  refused variants), `tools/mkwolf-hello` (the wolf program, linked
  static through a `cc -static` wrapper), `tools/mkinitramfs` (a
  reproducible archive), `tools/mkimage --conf
  boot/limine-initramfs.conf --add … initramfs.cpio` (the module).
- No `region`, no heap: the archive is read in place, a process's pages
  and stack are frames written through the HHDM before its space is
  live, and the FPU areas are frames.
- Not yet (the gap to M-PX3, `notes/px10-the-loader.md` §4): `brk`,
  `arch_prctl(ARCH_SET_FS)` and FS per thread, `mprotect`, anonymous
  `mmap`, `getrandom`, `readlinkat` of `/proc/self/exe`, the files
  lane's calls; PIE (a load bias); `PT_INTERP` (M-PX4); AVX-512 state
  (XCR0 bits 5–7: no PAX host offers it, and a glibc built for
  x86-64-v4 needs it before its first system call).

## Linux programs (px12, M-PX3)

| module or file | what |
|---|---|
| `vm/` | a process's memory past its image: `brk` (from the page above the image's highest byte, up to 64 MiB, zeroed frames; the old break answered on a refusal, as Linux does), `mmap` (anonymous private only, top-down from `0x7f0000000000`, frames zeroed at the call, `MAP_FIXED` replaces, `MAP_FIXED_NOREPLACE` -EEXIST; a file mapping -ENODEV and `MAP_SHARED` -EINVAL, each a `refused:` line), `munmap`, `mprotect` (leaves rewritten, INVLPG; `PROT_NONE` takes U/S away) |
| `files/` | 32 descriptors a process in its area (zero is a fresh process: 0-2 the console); the read-only tree is the initramfs plus a synthetic `/dev` (`stdin`, `stdout`, `stderr` reopen descriptor 0, 1, 2 as Linux's links do; `null`); paths made canonical as strings, then looked up whole (-ENOENT, -ENOTDIR, -EISDIR, -EROFS for any write, `refused:` named); `openat`, `read`, `pread64`, `lseek`, `close`, `fstat`/`newfstatat` (`struct stat`, 144 bytes), `statx` (256 bytes), `getdents64` (`.` and `..` first, then the archive's order), `ioctl` (-ENOTTY), `getcwd` (`/`), `readlinkat` (nothing is a link) |
| `uaccess/` | every user buffer of the new calls: the process's own tables walked first (`paging.user_ok`, `user_ok_write`), then the frame through the HHDM (SMAP never relaxed); checked whole, so all or nothing; `string_in` for paths |
| `user/` (px12 additions) | the dispatch (`dispatch`): the calls above, `arch_prctl` SET_FS/GET_FS, `getrandom`, `clock_gettime`/`time`/`gettimeofday` (the PIT's ticks; no vDSO, no wall clock), `clock_nanosleep`/`nanosleep` (the thread sleeps to the tick after the deadline), `uname`, `prctl(PR_GET_NAME)`, `prlimit64` (read only), `set_tid_address`/`gettid`, the four ids (0); `int` arguments read as 32 bits; every other call -ENOSYS, logged once per process; `exec_span`/`exec_line` take a path and words as kernel bytes |
| `sched/` (px12 additions) | the record grows to 128 bytes (`fs`, written to IA32_FS_BASE at every switch in); a 2048-byte process area per slot in `../boot/sched.S`'s `pax_procs`, zeroed with the slot; `sleep_current` for a system call that sleeps |
| `paging/` (px12 additions) | `user_ok_write`; `protect_user` (a user leaf's flags rewritten, its frame kept) |
| `initramfs/` (px12 additions) | `ino`, `nlink`, `is_dir`, `is_file`; `find_span`/`lookup_span` for a path given as kernel bytes |
| `kmain_boreutils.lu` | runs the initramfs's `/etc/pax-run` (`../user/mpx3-boreutils.run`), one command at a time, each waited for, every frame checked back (`tests/mpx3-boreutils`) |

- The programs are boreutils' own (`../user/boreutils.pin`, built by
  `tools/mkboreutils` with the toolchain boreutils pins, `-static`
  through a `cc` wrapper: wolf has no `--static`), `ls` among them since
  px15 (px12 ran busybox-static's), unmodified; `tools/linux-run` runs
  the same list chrooted on Linux, the reference side.
- No `region`, no heap: a process's state is words in its area and
  frames; a path goes through `../boot/user.S`'s `pax_kbuf` (one CPU,
  IF clear for the whole call).
- Not yet: `fork`/`execve`/`wait4` (px14), console input (px13, below:
  kmain_boreutils never starts it, so `read` on its console is
  end-of-file), signals, threads (`clone`, futexes,
  `set_robust_list` and `rseq` -ENOSYS), a writable file system, a wall
  clock, the vDSO, demand paging, PIE and `PT_INTERP`.


## The console (px13)

`kmain_console.lu` starts the console's input and runs the
initramfs's `/etc/pax-run` as kmain_boreutils does, one command at a
time, but with descriptors 0-2 a terminal: the first command is init
(PID 1 in role; PAX's ids number kernel threads first, so the log says
`pid 2`), and when the list is done the kernel says how init ended
(`PAX: init /bin/pelt ended with status 0; nothing left to run`) and
halts (`tests/mpx3-console`).

| module or file | what |
|---|---|
| `console/` | COM1's receiver (vector 36, the 8259 master's line 4) and the i8042's keyboard (vector 33, line 1; the configuration byte set to interrupt and translate to scancode set 1; set 1 decoded for a US layout: shifts, controls, Caps Lock, Ctrl with a letter) into one input queue and one line discipline: canonical mode (echo, erase, kill, word erase, Enter, Ctrl-D at an empty line for end of file, Ctrl-D on a non-empty one to hand it over) and non-canonical (VMIN 0 or at least 1); the settings a Linux pseudo-terminal starts with, measured, less ISIG and IXON (no signals yet: Ctrl-C is the byte 0x03); `read` (one line a call in canonical mode, `RESTART` when nothing is ready), the terminal ioctls (TCGETS, TCSETS, TCSETSW, TCSETSF, TIOCGWINSZ 0x0, TIOCSWINSZ; anything else refused by name), `report`, `summary`. Before `start` it is px12's console: reads end of file, every ioctl -ENOTTY |
| `../boot/console.S` | the console's storage: 64 state words and a 4096-byte input ring in `.bss` |
| `sched/` (px13 additions) | a wait state for console input: `block_input` (from a system call), `wake_input` (from the console's interrupt), `kick` (switch to a woken thread at once when the CPU was idle) |
| `user/` (px13 additions) | a console `read` with nothing ready rewinds its frame to the `syscall` instruction (RIP − 2, RAX the call's number) and waits for input, so the read runs afresh in its own address space when woken; a refused tty ioctl is a `refused: tty ioctl 0x…` line and -ENOTTY; a `write` to the console turns NL into CR NL only under OPOST and ONLCR; `last_exit` |
| `timer/` (px13 additions) | `unmask` (a master line), `master_mask`, `eoi` (any 8259 vector) |
| `files/` (px13 change) | a console descriptor's `read` and `ioctl` go to `console/` |
| `../user/elf/ask.S` | the console's test program: prompts, makes one read, says what it read; `ask tty` asks the terminal first, reads a line with echo off and bytes in non-canonical mode |

- Both lines stay masked until `console.start()`, so every earlier
  kernel (the tour, kmain_boreutils) behaves as before: a batch
  program's descriptors are not a terminal there, as Linux's pipe is
  not, and `tests/mpx3-boreutils` still compares with Linux's pipe.
- No `region`, no heap: the queue is bytes in `.bss`, read and
  written volatile (the interrupt writes them behind every thread's
  back), every entry with IF clear.
- Not yet: signals (Ctrl-C, Ctrl-\, Ctrl-Z deliver their bytes; ISIG
  is clear), output flow control (IXON clear), VTIME, VREPRINT,
  VLNEXT, arrows and function keys (no escape sequences), line
  editing beyond the discipline's, more than one reader's fairness, a
  framebuffer console (the echo and every write go to COM1), process
  groups and a controlling terminal (TIOCGPGRP and friends are refused
  by name), process creation (`clone`/`execve`/`wait4`, px14).

## Processes (px14)

pelt, as pid 1 on kmain_console, runs the programs in the initramfs:
it starts each child as it does on Linux (measured: `clone3` with
CLONE_VM | CLONE_VFORK | CLONE_CLEAR_SIGHAND on a stack of its own, the
child's `dup2` of /dev/null onto 0 and `execve`, the parent's `wait4`),
and every typed session is byte-identical to the same binaries' on a
Linux pseudo-terminal (`tests/mpx3-shell`).

| module or file | what |
|---|---|
| `process/` | see the table above: the image builder and the process calls |
| `sched/` (px14 additions) | the record grows to 184 bytes in a 256-byte slot (`pid`, `ppid`, `status`, `owns`, `vparent`, `zombie`, `sigmask`); the process area to 4096 bytes (the signal records); states ZOMBIE, VFORK, WAITING; `clone_current`, `vfork_wait`, `exec_current`, `child_ended`, `zombie`, `wait_child`, `end_with` (the status word), `self_pid`, `self_ppid`, `pid_of`; `finish` resumes a vfork parent, reparents to pid 1, keeps a zombie for a parent and wakes it; `reap` keeps a zombie's slot and never frees a borrowed space |
| `files/` (px14 additions) | `dup` (dup, dup2, dup3: the copy without close-on-exec unless asked; a position per descriptor, not per open file, named), `exec_close` (O_CLOEXEC), `exec_lookup` (execve's file: -ENOENT, -EACCES for a directory, a device or no execute bit) |
| `fpu/` (px14 additions) | `fork` (a child's x87/SSE state is its parent's), `exec` (the template, loaded at once) |
| `user/` (px14 changes) | a `who` line's `pid` is the Linux pid; `exit`/`exit_group` leave `code << 8`, a fault the signal (`process.fault_signal`); `getpid`, `getppid`, `gettid`, `set_tid_address` the pid; the process calls routed to `process/`; `last_exit` only for a program the kernel started |
| `kmain_console.lu` (px14 change) | init's environment gains `PATH=/bin` |
| `../boot/user.S` (px14 addition) | `pax_argbuf`, 69632 bytes where a new program's strings are staged |
| `../user/elf/procs.c` | the process calls' witness, C with no libc: run as pid 1 on PAX and as pid 1 of a fresh pid namespace on Linux, the same lines on both |

- Not yet: threads (CLONE_VM without CLONE_VFORK, CLONE_THREAD),
  signal delivery (masks and actions are recorded; `kill` is refused by
  name; px17 adds SIGPIPE's default only), process groups and sessions
  (wait4's 0 and -pgid mean any child), rusage (zeroed), `execveat`,
  `#!` scripts (-ENOEXEC). px17 did `fork` and the shared offset.

## Pipes, redirection and `cd` (px17)

pelt `3e7516c` (H2) runs pipelines, redirections and `cd` on PAX as on
Linux. Its spawn (wolf 0.2.26's, measured: `notes/px17/pelt-plumb.strace`)
is not px14's: a **fork** (`clone(CLONE_CHILD_SETTID|CLONE_CHILD_CLEARTID|
SIGCHLD)`), a `socketpair(AF_UNIX, SOCK_SEQPACKET|SOCK_CLOEXEC)` whose
close at `execve` tells the parent's `recvfrom` the child ran, three
`fcntl(F_DUPFD_CLOEXEC, 3)` and `dup2`s onto 0-2 in the child; pipelines
`pipe2(O_CLOEXEC)`; `cd` `chdir` then `getcwd`. Every typed session,
`shell-plumb` among them, is byte-identical to Linux's
(`tests/mpx3-shell`).

| module or file | what |
|---|---|
| `files/` (px17) | **open files** (`pax_ofiles`, 64): what a descriptor and its duplicates (dup, dup2, dup3, F_DUPFD, a child's copy of the table) share, an offset among them; freed with the last reference. **pipes** (`pax_pipes`, 16 records; 65536 bytes in 16 frames, freed with the last end): a read waits while empty with a writer open (`WAIT`), 0 with none; a write waits while full, a write of at most 4096 bytes whole; -EPIPE with no reader. **socketpairs** (AF_UNIX stream and seqpacket): two one-frame buffers. `fcntl` (F_DUPFD, F_DUPFD_CLOEXEC, F_GETFD, F_SETFD, F_GETFL, F_SETFL, F_GETPIPE_SZ), `pipe2`, `socketpair`, `recvfrom`, `sendto`, `chdir`, `fchdir`, `getcwd` the real directory; relative paths from the process's working directory (area word 12, inherited, kept across `execve`); `inherit` (a child's references), `close_all` (a process's end) |
| `process/` (px17) | `fork`: a clone without CLONE_VM on a copy of the caller's space (`paging.copy_user`), both running; CLONE_CHILD_SETTID, CLONE_PARENT_SETTID; `sigpipe_kills` (SIG_DFL, not blocked, not pid 1) |
| `paging/` (px17) | `copy_user`: every present user page copied into a fresh frame, mapped with the same permissions |
| `sched/` (px17) | state PIPE, `block_pipe`, `wake_pipes`; `clone_current` takes a fork's own space |
| `user/` (px17) | the eight numbers routed; a `WAIT` rewinds the call and parks the thread; `killed: SIGPIPE …` and status 13; every end of a process closes its descriptors |
| `pax_tour/` (px17) | the closing line: "All in wolf. Linux programs run on it unmodified: a shell, its pipes, its tools." |
| `../boot/user.S` (px17) | `pax_ofiles`, `pax_pipes` |
| `../user/elf/procs.c` (px17) | fork, pipes (a waiting reader, writer EOF, SIGPIPE, -EPIPE), a shared offset, the working directory, a socketpair, fcntl |

- Named drift: a SOCK_SEQPACKET's record boundaries are not kept; O_NONBLOCK
  on the console's never-opened 0-2 is the descriptor's; a SIGPIPE handler
  is not run (the write answers -EPIPE); CLONE_CHILD_CLEARTID is not kept
  (no futex, no threads); a fork copies every page (no copy-on-write).

## The command line, and `quiet` (px15)

`../boot/start.S` asks Limine for the executable command line (the
configuration's `cmdline`); `boot_info.cmdline_has(w)` says whether it
holds `w` as a word. `user.start` reads `quiet` there once into
`log`'s one word (`pax_log_quiet`, `../boot/console.S`), and with it on:

| line | with `quiet` |
|---|---|
| `user: exec pid …` (`process/`), `user: <name> pid <n> exit_group <s> after <r> runs` and `… syscall <n>: -ENOSYS` (`user/`), `user: frames free …` (`kmain_console.lu`) | not printed |
| `user: quiet (the kernel command line): …` (`user.report`) | printed once, at start-up |
| refusals (`refused:`), `killed:`, `-EBADF`/`-EFAULT` on a write, the tty ioctl refusal, panics, every boot line | printed |

Every test kernel boots without it; `tests/mpx3-shell` boots the shell's
initramfs with `../boot/limine-initramfs-quiet.conf` beside the
narrating legs and holds both to the same Linux transcript.

## The screen (px19)

| module or file | what |
|---|---|
| `screen/` | the console drawn on the framebuffer: `put` (every byte `serial.put` writes; before `attach`, kept in a 16 KiB early buffer), `attach(va, w, h, pitch, rs, gs, bs)` (clears the screen, replays the early buffer, draws the cursor), `on`, `cols`, `rows`, `scrolls`, `replayed`, `lost`, `bytes`. A grid of 8×16 cells (at most 256×128); ASCII and UTF-8 drawn from `../boot/font.S` (a code point the font lacks, or at or above 256, as `?`); deferred wrap; LF, CR, BS (a pending wrap only cleared), TAB; CSI read whole, SGR 0 1 7 30–37 39 40–47 49 90–97 honoured, everything else ignored; the PC's 16-colour palette; a steady inverse cursor; scrolling by `pax_fb_copy`/`pax_fb_fill`. IF clear while it draws, and a re-entered `put` (a fault while drawing) does nothing |
| `fb/` | Limine's first framebuffer mapped in PAX's HHDM at the address Limine gave, 4 KiB pages RW NX, write-combining through PAT entry 5 (PWT and PAT on the leaf) when CPUID has the PAT and IA32_PAT's entry 5 is WC, else uncached (PCD and PWT, entry 3); a 32-bit RGB 8:8:8 framebuffer only, anything else refused by name; `start(pml4)` (after `paging.start`, before any process), `report` (`screen: …`, kmain_screen only), `write_combining` |
| `serial/` (px19 change) | `put` hands each byte to `screen.put` after the UART |
| `console/` (px19 change) | `start` sets the window size (`TIOCGWINSZ`) to the screen's rows and columns when the screen is attached; 0 by 0 otherwise, as px13 |
| `boot_info/`, `../boot/start.S` (px19) | the framebuffer request; `fb_count`, `fb_address`, `fb_width`, `fb_height`, `fb_pitch`, `fb_bpp`, `fb_model`, `fb_mask` |
| `../boot/screen.S` | `pax_screen_state` (64 words), `pax_screen_cells` (256×128 cells), `pax_screen_early` (16 KiB); `pax_fb_copy` (REP MOVSQ, then MOVSB), `pax_fb_fill` (REP STOSQ) |
| `../boot/font.S` | `pax_font`: 256 glyphs of 16 bytes, generated by `../tools/mkfont` from `../font/spleen-8x16.bdf` (Spleen 2.2.0, BSD-2-Clause) |
| `kmain_screen.lu` | the screen's test kernel: the scroll's cost by the PIT, the terminal's pattern, halt |
| `kmain_console.lu`, `kmain_tour.lu`, `kmain_tour_text.lu` (px19 change) | `fb.start(pml4)` after paging, with no line of their own: the serial console is what it was |

- The screen is the console when Limine hands over a framebuffer; a
  machine with no display device (`tools/qemu-run --no-screen`, QEMU's
  `-vga none`) gets no framebuffer response, and the console is serial
  only, with px13's window size of 0 by 0.
- The serial log is the screen's source of truth: `../tools/screen-ref`
  draws the screen's picture from it (from the kernel's first line on;
  the firmware's own serial output never reached the screen), and
  `tests/mpx3-screen` compares that with QEMU's `screendump` of the
  halted machine, pixel for pixel.
- Not yet: other SGR parameters (underline, 256 colours), cursor
  movement and erase sequences (read and ignored), a back buffer (a
  scroll reads the framebuffer, which is slow through WC on real
  hardware), the cursor's blink, more than one framebuffer.

## The speaker (px18)

`kmain_console`'s programs can sound the PC speaker: Linux's console
ioctls on a console descriptor, which a Linux beep program asks
(`notes/px18/beep.strace`). `/bin/play` (`../user/play`, wolf) sounds
note files with them; `tests/mpx3-speaker` captures QEMU's speaker to
a WAV file (`-audiodev wav,id=snd0,path=… -machine
pcspk-audiodev=snd0`) and measures it.

| module or file | what |
|---|---|
| `speaker/` | the 8254's channel 2 in mode 3 (control word 0xB6 to 0x43, the count to 0x42) gated to the speaker by port 0x61 bits 0 and 1 (read-modify-write, bits 2-3 kept); KIOCSOUND (0x4B2F: the count, 0 silence) and KDMKTONE (0x4B30: the count and a duration in ms, ended by the tick); `own` (the process that started the tone), `ended` (that process's end stops it: `user: speaker off at the end of pid <n>, port 0x61 0x<v>`, unless quiet), `tick`, `summary` (`speaker: <t> tones, <e> stopped at their process's end, sounding <c>, port 0x61 0x<v>`, when a tone was started); every change logged with its tick in a 1024-word ring a test reads through QEMU's monitor |
| `console/` (px18) | KIOCSOUND and KDMKTONE answered (kernel/speaker) once the console is started |
| `interrupts/` (px18) | vector 32 also calls `speaker.tick` |
| `sched/` (px18) | `end_with` calls `speaker.ended` with the ending process's pid: exit, `exit_group`, a fault's kill |
| `user/` (px18) | a speaker request answered 0 makes the caller the tone's owner (`speaker.own`) |
| `../boot/speaker.S` | `pax_spk_state` (8 words) and `pax_spk_ring` (1024 words), storage only |
| `../boot/io.S` (px18) | `pax_halt` clears port 0x61 bits 0 and 1 before its `hlt` loop: no halt, a panic's included, leaves a tone sounding |

- Where PAX differs from Linux, on purpose: a tone stops when the
  process that started it ends (Linux leaves it sounding), and a halt
  silences it.
- `/dev/tty0` and `/dev/console` (px21a, `files/`) open the console
  whatever descriptors 0-2 have become, and answer its ioctls, these
  two among them. Ubuntu's `beep` (1.4.9, its source package built
  with `-static` by `../tools/mkbeep`, nothing of it committed) runs
  unmodified on them: `beep -f 440 -l 300` opens `/dev/tty0`,
  `beep -e /dev/console …` the other, and `tests/mpx3-speaker` K7
  holds both tones to 1% of the pitch asked. The package's own binary
  is a PIE that loads libc through `ld.so`, which `elf/` refuses by
  name: PAX has no dynamic loader yet. An input-device request on the
  console (`EVIOCGSND`, which beep also tries) is plain `-ENOTTY`, as
  on a Linux terminal.
- Not yet: the evdev speaker; a dynamic loader (so the packaged
  `beep` itself).

## Sampled sound (px30)

`kmain_console` starts QEMU's virtio sound device when the machine has
one (silently when it has none) and programs reach it through Linux's
OSS interface, `/dev/dsp` (`notes/px30-the-sound-card.md`).

| module or file | what |
|---|---|
| `sound/` | the device (`1af4:1059`): VERSION_1 only; queues 0 control (synchronous), 1 event, 2 transmit; `PCM_INFO`, the first output stream; eight periods of 4096 bytes (frames taken once), a transmit message being the stream id, the period, the status; `SET_PARAMS`/`PREPARE` before the first period, `START` at two, `STOP` after a drain, `RELEASE` at the last close; an underrun counted; OSS's open, write (WAIT when full), ioctl, drain and release; `summary` (`sound: <counters>`, when /dev/dsp was opened) |
| `virtio/` (px30) | `use_words`: a transport record per device (net keeps px20's in `pax_net_state`); `attach_at`: the device slot's windows from a given one (sound 4-7) |
| `files/` (px30) | `/dev/dsp` (14:3, mode 020666, listed in `/dev` only while the device is up): a descriptor kind whose writes, ioctls and last close go to `sound/`; `lseek` ESPIPE, `read` EBADF |
| `user/` (px30) | `write` to /dev/dsp, and its last `close`, which drains first (WAIT until the device is done) |
| `interrupts/` (px30) | the sound vector: `sound.irq`, net's handler too when the line is shared, one EOI, every pipe-waiter woken |
| `kmain_console.lu` (px30) | `pci.scan` and `sound.start` after the console |
| `../boot/sound.S` | `pax_snd_state` (128 words) and `pax_snd_stats` (64), storage only |

- Where PAX differs from Linux, on purpose or for now: no capture
  (`O_RDONLY` is ENXIO); formats other than U8 and S16_LE are answered
  S16_LE, more than two channels two, an unlisted rate the nearest
  listed (Linux converts and resamples); a process that ends with the
  device open is silenced at once (Linux plays the queue out); the
  period stays 4096 bytes whatever SETFRAGMENT asks; no `mmap`, no
  TRIGGER; `poll` waits for px24.

## The network (px20, px21)

`kmain_net.lu` finds QEMU's virtio network device, brings it up and
speaks ARP, IPv4 and ICMP echo with the user-mode gateway or, with
`peer` on the command line, with `tools/net-peer` at the other end of
a socket netdev (`tests/mpx4-net`): two steps toward M-PX4. Nothing
user-visible: the surface is kernel-internal (`net.send`, `ip.send`,
`icmp.ping`).

| module or file | what |
|---|---|
| `pci/` | configuration mechanism #1 (ports 0xCF8/0xCFC, `../boot/io.S`'s `pax_outl`/`pax_inl`): `scan` (bus 0, every function, and the bus behind any bridge) into `pax_pci_table`; `find`, `bar` (I/O, 32-bit or 64-bit memory), `next_cap` (the capability list), `command`/`set_command`, `line`, `pin`; `report`, the census (one line a function, its BARs, its capabilities), printed by kmain_net when the kernel command line holds `pci` (`../boot/limine-net.conf`) |
| `virtio/` | the virtio 1.x PCI transport: `attach` finds the vendor capabilities (common configuration, notification, ISR status, device configuration) and maps each in a window of the device slot (PML4 slot 352, above the local APIC's page), uncached; `reset`, `add_status`, `device_features`/`set_features` (64 bits through the select registers), `isr`, `device8`. The split virtqueue: `layout` (descriptors, avail, used in one frame), `aligned` (the specification's 16/2/4), `queue_setup`, `set_desc`, `offer`, `notify` (honouring the device's NO_NOTIFY), `returned`, `collect`, `quiet` (the driver's NO_INTERRUPT) |
| `net/` | the network device and the frame interface: `start` (the device found, reset, VERSION_1 and MAC taken and required, two 64-entry queues with a 2048-byte buffer a descriptor, its 8259 line made level-triggered and unmasked; one `net:` line and no network when there is no device or it is refused by name), `irq` (the cause read, the 8259 acknowledged), `wait`, `rx_take`/`rx_give`, `send` (rows `down`, `size`, `full`; padded to 60 bytes), `tx_free`, `mac_byte`, `count` (frames and bytes each way; drops by cause: runt, long, other station, a type nothing speaks, down, size, full), `report`, `counters` |
| `arp/` | RFC 826 for IPv4 over Ethernet and the cache `ip` sends through (px21): `input` (the reception algorithm: validate, merge, add, answer a request for this station; a sender of 0.0.0.0 or the broadcast teaches nothing, one claiming this station's address is a `conflict`), `send` (the next hop's hardware address written into the frame, or the frame queued and a request sent), `query`, `lookup`, `tick`; eight entries, each free, incomplete, resolved or stale; a resolved one is good for a minute from the last ARP packet from its address (`start`'s `age`), then stale: still used, and asked for again by the first frame sent to it, three times a second apart, then freed (px35, pax#32); an incomplete one is asked for three times a second apart and then given up (`unresolved`), two frames wait per address and a third pushes out the oldest (`pushed out`), a new address evicts the resolved or stale entry stamped longest ago and never an incomplete one (`table full`); `report`, counters |
| `ip/` (px21) | IPv4: `start` (address, netmask, gateway, given once at boot), `input` (the one place a header is judged, in order: `short`, `version`, `ihl`, `checksum`, `length`, `ttl`, `fragment`, `source`, `option`, `source-route`, `other`, `protocol`, each a counter; it answers what the datagram is and `netd` makes the call), `send` (version 4, IHL 5, DF, TTL 64, an identification counted from boot; on-link or by way of the gateway; the broadcasts to ff:ff:ff:ff:ff:ff; a payload over 1480 bytes refused, `size`), `sum` (RFC 1071), `next_hop`, `is_broadcast`; the MTU is 1500 and nothing is fragmented or reassembled |
| `icmp/` (px21) | `input` (an echo request answered in place: type 0, the checksum made again, to the request's source; an echo reply matched to the one echo the kernel waits for, else `stray`; `short`, `checksum`, `broadcast`, `type`), `ping` and `answer` (the kernel's own echo request, identifier 0x5058, and its round trip by the time-stamp counter), `unreachable` (type 3 code 2 for a protocol nothing speaks, quoting the header and 8 bytes; one a second, the rest `limited`; none for a broadcast, `silent`) |
| `netd/` | `pax_netd`, the network thread's body: waits for the device's interrupt, takes each frame, hands 0x0806 to `arp` and 0x0800 to `ip` and then `icmp` (px21), counts and drops anything else, gives the buffer back; `pax_net_clock` (px21), a second thread: `arp.tick` every ten ticks |
| `sched/` (px20) | state NET, `block_net`, `wake_net` |
| `timer/` (px20) | `unmask_line` (a slave line and the cascade), `elcr`, `level` |
| `sync/` (px20, px21) | lock words 2 (`net`), 3 (`arp`, taken before it), 4 (`ip`, taken before both) and 5 (`icmp`, never held across a call into `ip`) |
| `interrupts/` (px20) | the device's vector: `net.irq`, `sched.wake_net`, `sched.kick` |
| `log/` (px20) | `hex_n` |
| `../boot/net.S` | `pax_pci_table`, `pax_pci_count`, `pax_net_state`, `pax_net_stats`, `pax_arp_state`, `pax_ip_state`, `pax_icmp_state`: storage only |
| `../boot/io.S` (px20) | `pax_outl`, `pax_inl` |

- The interface is the 1.x one only: a transitional device's legacy
  I/O BAR is never touched, and a legacy-only device is refused by
  name. The interrupt is INTx on the 8259 line the firmware wrote in
  Interrupt Line (11 on q35 under SeaBIOS and OVMF); OVMF leaves that
  line edge-triggered in ELCR, so the driver sets it level itself.
- No frame is touched with an interrupt in service, and nothing on
  the frame path allocates: the rings and buffers are 66 frames taken
  once, the state words in `.bss` read and written volatile under
  `sync.net()` (no `region`: the device's interrupt allocates nothing).
- A module `const` cannot be initialised from another module's on
  wolf 0.2.26 or 0.2.27 (wolf-lang#653, re-tested at px21a's pin): `net`'s feature mask spells
  `virtio.F_VERSION_1` out.
- Every kernel links `net`, `virtio` and `pci` (kernel/interrupts
  names the vector), as every kernel links the console and the
  speaker; none but kmain_net starts them, and the vector is 0 until
  then.
- The protocols allocate nothing either (px21): `arp`, `ip` and `icmp`
  take eleven frames once (one to compose in each, eight for the
  cache's queues) and keep words in `.bss`; an echo reply is made in
  the receive buffer and copied once into `ip`'s frame.
- What PAX sends is one datagram a frame, at most 1500 bytes, DF set;
  a fragment that arrives is dropped by name (`fragment`), and IP
  options are skipped on the way in (a source route is refused,
  `source-route`) and never sent.
- Not yet: TCP (px23); fragmentation and reassembly; ICMP errors
  other than protocol and port unreachable, and any use of the ones
  received; an address from anywhere but a kernel's constants
  (no DHCP); more than one echo waited for at a time; MSI-X; merged
  receive buffers, checksum and segmentation offload, the control
  queue (so the device's receive filter is whatever it starts as;
  `net` drops frames for other stations itself); link status; more
  than one device; a device removed.

## UDP and sockets (px22)

`kmain_sockets.lu` starts what `kmain_boreutils` and `kmain_net` start
between them and runs a run list of static Linux programs that open
AF_INET datagram sockets (`tests/mpx4-udp`, `user/net/`): the third
step toward M-PX4.

| module or file | what |
|---|---|
| `udp/` | RFC 768: `input` (from `netd`, for protocol 17: `short`, `length`, `checksum` — zero is "none made" — `port-zero`, then the socket that takes the datagram or `no-port`, or `full` when its queue has no room), the pseudo-header checksum, `send` (the caller's bytes behind a header in the module's frame, then `ip.send`), loopback (a datagram for the station's own address or 127/8 goes to the receiving side in the same call), 16 sockets in `boot/net.S`'s `pax_udp_socks` — local address and port, peer, receive timeout, a 65,536-byte ring in 16 frames taken at `open` and freed at `close` — which are the port table too (`bind`: `EADDRINUSE` for the same port on the same address or on every address; ephemeral ports 32768-60999, sequential from a start the time-stamp counter picks), counters by cause |
| `socket/` | the calls: `socket`, `bind`, `connect` (and AF_UNSPEC), `sendto`, `recvfrom` (`MSG_DONTWAIT`, `MSG_PEEK`, `MSG_TRUNC`), `getname` (both), `setsockopt` and `getsockopt` (`SO_RCVTIMEO_OLD`; `SO_TYPE`, `SO_ERROR`), `no_connections` (`listen`, `accept`, `accept4`: -EOPNOTSUPP); `struct sockaddr_in` read and written through `uaccess`; each refusal's errno as Linux gave the witness, and the ones PAX names logged once a process (`why`, `detail`) |
| `files/` | kind `K_INET`: a descriptor on an open file whose node is `udp`'s socket number; the last close calls `udp.close`; `sock_kind`, `inet_open`, `inet_sock`, `nonblocking`; `open_files`, `pipes_held` for the books |
| `user/` | the dispatch (41-45, 49-52, 54, 55, 288); `read` and `write` on a socket; a waiting receive parks through `sched.block_pipe_until` when the socket has a timeout |
| `sched/` | `block_pipe_until(f, tick)`: a pipe wait the timer ends too; `wait_down_to(n)`: `wait_all` for a kernel whose own threads never exit |
| `icmp/`, `ip/`, `netd/` | `unreachable` takes the code and says what it did; `TO_UDP`; protocol 17 to `udp.input`, and a port unreachable when it answers `NO_PORT` |
| `kmain_sockets.lu` | the run list, each command waited for with the processes it made, then its frames, its time by the time-stamp counter and the books (heap, frames, open files, pipes, sockets, datagrams waiting); the counters; halt |

- The layering is one-way because wolf refuses an import cycle (E0303,
  tested by px22): `socket` → `files` → `udp` → `ip` → `arp` → `net`,
  and `netd` above them all makes the calls between siblings (`udp`'s
  answer, then `icmp`).
- Locks: `sync.udp()` before `sync.ip()` before `sync.arp()` before
  `sync.net()`. A system call runs with IF clear and calls `udp.send`,
  which reaches `net.send`, on its own kernel stack; nothing on that
  path switches.
- A socket's queue is the only place a received datagram is kept: it
  is copied out of `netd`'s receive buffer (or the sender's bytes, over
  loopback) into the ring, 8 bytes of head and the data rounded up to
  8; one that does not fit is dropped whole (`full`). Nothing here
  allocates from the heap or opens a region.
- A receive with nothing queued answers `files.WAIT` and is run again
  when any pipe or socket changes (`sched.wake_pipes`, from `udp`'s
  `push`) or its deadline comes. No close can reach a socket a receive
  is parked on: a process has one thread, and its own reference keeps
  the socket.
- Not yet: `sendmsg`, `recvmsg`, `shutdown`; `poll`, `select`, `epoll`;
  any option but the three; a datagram over 1472 bytes (nothing
  fragments) or to a broadcast address; an ICMP error delivered to a
  socket (a connected socket never sees ECONNREFUSED); loopback below
  UDP (`icmp.ping` to the station's own address, and TCP's); a socket
  of any other family or type.

## TCP (px23)

`kmain_sockets.lu` also starts `kernel/tcp` and runs static Linux
programs that open AF_INET stream sockets (`tests/mpx4-tcp`,
`user/net/tcp*`): the fourth step toward M-PX4.

| module or file | what |
|---|---|
| `tcp/` | RFC 9293. 64 control blocks of 128 words (`pax_tcp_conns`): a socket, a connection a listener holds, a connection its process closed that is still finishing. `input` (from `netd`, protocol 6): `short`, `header`, `checksum`, `broadcast`, `port-zero`, `option`, then the block, the time-wait entry or the listener the segment names, else a reset; §3.10.7.4's order for a connection (the window, a reset, a SYN, the acknowledgement, the data, the FIN). `output`: what the peer's window, the congestion window, Nagle and the silly-window rule allow. `tick` (from the clock, every 10 ms): the retransmission, persist and user timers, a closed block's end. The calls: `open`, `bind`, `listen`, `accept`, `connect`, `send`, `recv`, `shutdown`, `close`, the options. A time-wait table of 32,768 entries in 256 frames; the counters, eight lines |
| `ip/` | **loopback** (`send_from`, `loop_peek`, `loop_done`): a datagram for this station or 127/8 waits on 64 frames; `input` takes `looped`; `speak_tcp` (protocol 6 is `protocol` until `tcp.start`) |
| `netd/` | `deliver` (one datagram to its protocol) and `drain` (the loopback queue, IF clear a datagram); the clock turns every tick: `tcp.tick`, `arp.tick` every tenth, `drain` |
| `icmp/` | looped messages counted apart; a destination unreachable handed back (`ERROR`, `quoted`) for `tcp.unreached` |
| `udp/` | its own loopback gone: `send` always goes through `ip.send_from`; `input` takes `looped` |
| `socket/` | the stream forms of every call, `listen`, `accept` (and `accept4`'s two flags), `shutdown`, `stream_send` (a write waits until every byte is queued); `SO_REUSEADDR`, `TCP_NODELAY`, `TCP_SYNCNT`, `TCP_USER_TIMEOUT` |
| `files/` | kind `K_TCP`: a descriptor on an open file whose node is `tcp`'s block; the last close calls `tcp.close`; `tcp_open`; `ioctl(FIONBIO)` on a socket |
| `user/` | 43, 48, 50, 288; `netd.drain` after every call (and the call run again when it had answered "wait" and the drain delivered something); `EPIPE` on a stream socket to SIGPIPE |
| `sync/` | word 7, `tcp()`: the last of the eight |
| `kmain_sockets.lu` | `tcp.start` with a key from `process.random_word`; the kernel's echo to 127.0.0.1 and to its own address; after each command up to 30 s for closed connections to finish; `tcp blocks` and `time-wait` in the books |

- Layering: `socket` → `files` → `tcp` → `ip` → `arp` → `net`, beside
  `udp`; `netd` above them makes the calls between `ip`, `icmp`, `udp`
  and `tcp`. A module that sends to this machine never calls the
  receiving side: it returns, and whoever called it (`kernel/user`
  after a system call, the clock, `netd` after a frame) drains the
  loopback queue.
- Locks: `sync.tcp()` before `sync.ip()` before `sync.arp()` before
  `sync.net()`; never with `sync.udp()`. One lock for all of TCP. The
  eight lock words are all taken now.
- A connection's two rings are its only buffers: 16 frames each, taken
  at `establish` (or at `connect`) and given back by `free_block` (or
  when a block a descriptor still names has nothing left to read).
  Out-of-order bytes go straight into the receive ring where they
  belong; four intervals say which are there.
- Waiting is px17's: a call answers `files.WAIT`, `kernel/tcp` calls
  `sched.wake_pipes` on every change, and the call runs again. A
  `connect` in flight is marked on its block (`F_CONNECTING`) so the
  call run again finds its handshake and not a second one.
- Not yet (px23; `poll`, `epoll` and `eventfd` are px24's, below, and
  threads and `futex` px26's): `select`; `sendmsg`,
  `recvmsg`; `SO_LINGER`, `SO_KEEPALIVE`, `SO_RCVBUF`/`SO_SNDBUF`,
  `SO_RCVTIMEO` on a stream, `TCP_CORK`, `MSG_WAITALL`, `MSG_OOB`;
  window scaling, SACK, timestamps and PAWS, NewReno's partial-ACK
  rule, a delayed ACK, path MTU discovery, keep-alives; an ICMP error
  delivered to a UDP socket; more than 256 control blocks or a listen
  queue past 129 (64 and 33 before px24); a closed connection whose peer acknowledges and never
  opens its window stays until the peer goes.
## Who a process is (px39)

The first lane of the users campaign (`notes/px39-the-credentials.md`,
ruling #75 in the planning repository). A process has an identity;
**nothing yet checks it** — no `open`, path walk, `kill`, `bind` or
`ioctl` asks who the caller is. `tests/mpx5-users` holds the ids and
the id calls to a real Linux's recorded answers, as root and as a user.

| module or file | what |
|---|---|
| `cred/` | the record, 42 words of the process area (words 160 to 201): four user ids and four group ids (real, effective, saved, file-system), the count and the sorted list of supplementary groups (32 at most, ruling R4), one word for "not dumpable"; all zero is root with no group, so no start path changes. `setid`, `setre`, `setres`, `setfs` (the rules of `setuid`, `setreuid`, `setresuid`, `setfsuid` and their group twins, privilege the effective USER id), `getres`, `getgroups`, `setgroups` (more than 32 refused by name, -EINVAL), `at_secure` (AT_SECURE), `exec` (saved and file-system ids become the effective ids; nothing raised), `dumpable`, `cap` (the masks `/proc/<pid>/status` prints) |
| `user/` | the dispatch's `id_calls` (102, 104 to 108, 113 to 120, 122, 123); `prctl`'s PR_GET_DUMPABLE, PR_GET_KEEPCAPS, PR_GET_SECUREBITS, PR_GET_NO_NEW_PRIVS |
| `process/` | `build_stack` writes AT_UID, AT_EUID, AT_GID, AT_EGID and AT_SECURE from the caller's record; `execve` calls `cred.exec` at its point of no return |
| `procfs/` | `status`'s `Uid`, `Gid`, `Groups` and five `Cap*` lines from the record; `/proc/self/setgroups` and `/proc/<pid>/setgroups` (`allow`) |

- kernel/sched is not touched: it already copies the process area
  whole for a fork's and a vfork's child, keeps it over `execve` and
  gives a process's threads their leader's. So ids are a process's on
  PAX; Linux keeps them per thread (a named difference).
- What is not there: any permission check; set-ID execution (ruling
  R5); `capget` and `capset` (-ENOSYS, R9); more than 32 groups;
  `PR_SET_DUMPABLE`; per-thread ids.

## Who a file belongs to (px42)

The second lane of the users campaign (`notes/px42-the-owners.md`).
A file has an owner and a group, stored, stamped, changed, reported
and carried by an image. **Still nothing checks them** on `open`,
`execve`, a path walk, a signal or a device: the one rule about who
asks is `chown`'s own. The campaign's ruled claim, when its checks
exist, is "enforced for honest programs; not a boundary against an
attacker"; this lane enforces nothing but that one rule.

| module or file | what |
|---|---|
| `tree/` | an inode's sixteenth word is its owner's user id (low 32 bits) and its group's id (high 32): `uid`, `gid`. The inode is the 128 bytes it was (32 a frame, 16,384 at most): the free list's link, the only use the sixteenth word had, lives in a free record's birth-time word. `create`, `mkdir`, `symlink`, `mksock` take the ids to stamp; `chown` (px36's `owned`) sets them, moves ctime and takes a regular file's set-user-ID bit, and its set-group-ID bit when the file is group-executable or the caller is outside its group; `adopt` gives an inode the archive entry's uid and gid |
| `files/` | `stamp`: a new name is its maker's **file-system** user id and group id, or the directory's group under a set-group-ID directory (which a new directory there inherits; `file_perm`: a file made group-executable with S_ISGID there by one outside the group loses the bit). `mkdirat` keeps a sticky bit and never takes S_ISGID from its caller. `fchownat` (92, 93, 94, 260): any id for file-system user id 0; for anyone else Linux's rule, measured (its doc comment). `put_stat`/`put_statx` write uid and gid (`n_owner`): an inode's own, a `/proc` node's by `procfs.owner`, 0 for `/dev`, a pipe and a socket |
| `procfs/` | `owner`: `/proc/<pid>` is its process's effective ids; its files too while the process is dumpable, root's once it is not |
| `cred/` | `in_list` is public |
| `initramfs/` | `uid`, `gid` (the header's third and fourth fields) |
| `tools/mkinitramfs` | `/PATH=FILE:MODE:UID:GID` and a directory entry `/PATH/:MODE:UID:GID`; without an owner the archive is the bytes it was |

- What is not there: every check but `chown`'s (px43 adds the file
  checks); an owner for a pipe or a socket (`fstat` says 0:0; Linux says the
  maker's ids; px43 gives pipes, socketpairs and AF_UNIX sockets theirs); a `chown` of `/dev` or `/proc` (refused by name,
  -EROFS); `O_TMPFILE`.

## Who may signal whom, and what only root may do (px45)

The fifth lane of the users campaign (`notes/px45-the-processes.md`):
the rules on **processes and root's things**. Root for signals and
privilege is effective user id 0 (`cred.privileged`, ruling #75 R9);
root for files stays file-system user id 0 (`files.may`). The ruled
claim stands: **enforced for honest programs; not a boundary against
an attacker**.

| module or file | what |
|---|---|
| `signal/` | `may_signal`, the one rule: privileged, or the sender's real or effective user id is the target's real or saved one, or SIGCONT (PAX's one session held every process; px48: within the sender's session); else -EPERM. `kill` of a pid, `tgkill` and `tkill` of the thread's process, and each process `kill(-1)`, `kill(0)` and a group reach ask it (`kill(-1)` answers 0 when any other process exists, a group 0 when one was signalled). A zombie answers by the rule and takes nothing. siginfo's `si_uid` is the sender's real user id (a child's for SIGCHLD); what the kernel raises asks nothing |
| `sched/` | an origin word carries the real user id (`sig_info`, `info_parts`; the pid in 21 bits); a process that has ended for its parent is a zombie from its end (`ended`), not from the next `reap` |
| `cred/` | `privileged` is public: the one test for root's things |
| `socket/` | `bind` of a port from 1 to 1023 by the unprivileged: -EACCES, before whether it is taken; a raw socket -EPERM to a user; SO_PEERCRED on every socket (`files.peercred`) |
| `files/` | `/dev`'s devices with devtmpfs's modes and owners (0:0; `null`, `zero`, `full`, `random`, `urandom`, `tty` 0666; `console`, `tty0`, `ttyS0`, `dsp` 0600), checked by `may` on `open` and `access` (`checked`); `/dev/zero` and `/dev/full` read zeros, `/dev/full` takes no write (-ENOSPC), `/dev/random` and `/dev/urandom` are `getrandom`'s; `/proc/<pid>/environ` and `fd/` guarded as `ptrace(2)`'s read mode (`may_read_of`: the mode, then the process itself, the privileged, or the file-system ids equal to all of the target's while it is dumpable); `fd/` lists the descriptors (its links are not followed: named); `peercred` (a socketpair's maker, a listener's own at `listen`, a connected end's peer, else pid 0 and ids -1); `chroot_dir`, `path_found` |
| `unix/` | 34 words a socket (32 before): SO_PEERCRED's pid and ids (`cred`, `set_cred`, `copy_cred`) |
| `procfs/` | `/proc/<pid>/cmdline` and `environ` (the program's strings as they are now in its memory, at most a page), `fd/`; `/proc/self/cmdline`, `environ`; `/proc/sys/net/ipv4/ip_unprivileged_port_start` `1024`; a zombie's files root's, its `cmdline` empty, its `environ` -ESRCH to read |
| `process/` | `setpriority`, `getpriority` (PRIO_PROCESS; a nice value lowered only by the privileged, another's changed by its real or effective user id); `sched_setscheduler`, `sched_getscheduler` (real-time policies the privileged's); both kept and reported, the scheduler unchanged (named drift); `root_call`: `chroot`, `reboot`, `sethostname`, `setdomainname`, `settimeofday`, `clock_settime`, `mount`, `umount2` refused to a user as Linux refuses (-EPERM, after the path where Linux asks it first), refused by name for root (PAX keeps no such state), `chroot("/")` 0 |
| `console/` | `controlling`: the console is every process's controlling terminal (one session), so the speaker's ioctls, Linux's for the privileged and a terminal's own session, are anyone's on a console descriptor (px48: the caller's own controlling terminal, by sessions) |
| `user/` | the dispatch of 140, 141, 144, 145, 161, 164 to 166, 169 to 171, 227; `mknod` of a device -EPERM to a user (root's still refused by name) |

- What is not there: job control, sessions and process groups (every
  process is in PAX's one session and one group: `kill(0)` and a
  negative group are every process, each by the rule; px48 adds them);
  a raw socket,
  `mknod` of any node, a FIFO; limits (`prlimit64` as before);
  capabilities (root is effective user id 0 and nothing finer); a root
  directory that is not the tree's; the time, the host name and file
  systems set by root (refused by name); `/proc/<pid>`'s `stat`,
  `maps`, `mem`, `auxv`, `io`, `limits` and its `exe`, `cwd`, `root`
  links; `/dev/mem`, `/dev/kmsg`, `/dev/ptmx`; what `/dev/std*`
  reopens keeps its answer; a priority or a policy that changes how
  PAX schedules.

## Job control (px48)

Process groups, sessions and the controlling terminal, as Linux keeps
them, measured black-box (`notes/px48-job-control.md`): by px48's probe
(`user/elf/jobs.c`) and a typed job-control session in Ubuntu's static
busybox `sh -i`, each as root and as a user, against real root's
recordings (kasumi's kernel under QEMU, the program on a pseudo-terminal
as its session leader) and a container's for the user's.

| module or file | what |
|---|---|
| `sched/` | a leader's `pgid`, `sid`, `ctty`, `execd`, `stopped`, `wstop`, `wcont` (a fork's child takes the first three, `execve` sets `execd`); the console's session and foreground group (`S_TTY_SID`, `S_TTY_PGRP`); a process the kernel starts leads a session and a group and takes the console when it is a terminal and free (named: Linux's init is in session 0 with none); `setpgid`, `setsid`, `group_exists`, `member_after`, `take_tty` (TIOCSCTTY: a session leader with none, or a steal by the privileged with arg 1: the old foreground group hears SIGHUP and SIGCONT), `drop_tty` (TIOCNOTTY), `open_tty`; **stops**: a stop signal at its default stops the process when it is sent (`job_signal`; a blocked one when it is taken), a STOPPED thread is parked when dequeued or on its way to ring 3 (`park_current`), SIGCONT continues whatever its action and discards a pending stop, a stop discards a pending SIGCONT, SIGKILL readies a stopped process; the parent is told (SIGCHLD with CLD_STOPPED or CLD_CONTINUED unless SA_NOCLDSTOP, `wait_find`'s W_STOPPED and W_CONTINUED); SIGTSTP, SIGTTIN and SIGTTOU to an orphaned group are discarded; **hangup**: a controlling process's end sends its terminal's foreground group SIGHUP and frees the console; an end that orphans a group with a stopped member sends it SIGHUP and SIGCONT (`orphaned_but`); `rt_sigsuspend` (`suspend_current`, SUSPEND, W_SUSPEND); the origin word's kind four bits, its pid twenty |
| `signal/` | `kill(0)` the caller's group, `kill(-g)` group g's members (a zombie one), -ESRCH with none, each by `may_signal`; SIGCONT within a session to anyone, across sessions by the rule; the console's keys for its foreground group only; a stop taken (`stop_self`) and parking in `on_return`; CLD_STOPPED and CLD_CONTINUED in siginfo; a handler run from `rt_sigsuspend` restores its mask at `rt_sigreturn` |
| `process/` | `setpgid` (109), `getpgrp` (111), `setsid` (112), `getpgid` (121), `getsid` (124); `wait4` by pid, -1, 0 and -pgid with WUNTRACED (`(sig << 8) \| 0x7f`) and WCONTINUED (`0xffff`); `waitid` P_PGID (0 the caller's), WSTOPPED, WCONTINUED, WNOWAIT |
| `console/` | TIOCSCTTY, TIOCNOTTY, TIOCGPGRP, TIOCSPGRP, TIOCGSID; `job`: a background reader is sent SIGTTIN (or told -EIO when it blocks or ignores it or its group is orphaned), a background writer under TOSTOP SIGTTOU (one that blocks or ignores it writes), a background setting (TCSETS*, TIOCSPGRP) SIGTTOU; `JOB_STOP` runs the call again once continued; SIGWINCH for the foreground group on a new size; `controlling` is the caller's own; VMIN above 0 waits for its bytes and VTIME then times the gap after the last byte (pax#66) |
| `files/` | `/dev/tty` -ENXIO to a process with no controlling terminal; a session leader with none that opens the console (no O_NOCTTY) takes it; a read of the console asks `console.job` first |
| `user/` | the five group calls, `rt_sigsuspend` (130), the console's background write rule, `JOB_STOP`'s rewind |
| `procfs/` | `/proc/<pid>/stat` and `/proc/self/stat` (`proc_pid_stat(5)`'s 52 fields: the state, parent, group, session, the console's number 0x440 and its foreground group, threads, sizes, signal sets; what PAX does not keep, 0); `status`'s State `T (stopped)`, NSpgid and NSsid the process's |
| `../boot/sched.S` | 400 bytes of the 512-byte thread record; `pax_sched_state` 32 words |

- What is not there: a second terminal (no pseudo-terminal: the
  console is PAX's one tty); the hangup of a terminal's open files
  (Linux's own `vhangup`; a controlling process's end only frees the
  terminal and sends SIGHUP, which is what Linux was measured to do
  there); `pause` (34) stays -ENOSYS; TIOCSTI, TIOCCONS, TIOCEXCL,
  TIOCOUTQ; `tcflush` and `tcdrain` (refused by name); the background
  rules for a console written by `sendfile` or `splice`; PRIO_PGRP and
  PRIO_USER (refused by name, as before).

## Who may name, change and keep (px44)

The fourth lane of the users campaign (`notes/px44-the-names.md`). The
rules on **names and metadata**, each by px43's one class rule (`may`)
and px42's group test (`member`), with two ownership tests beside them.
The ruled claim stands: **enforced for honest programs; not a boundary
against an attacker**.

| module | what |
|---|---|
| `files/` | **Directory write**: `may_make` (write and search of the directory: `mkdirat`, `symlinkat`, `linkat`'s new directory, `unix_bind`) and `unname` (the same, then the sticky rule: `unlinkat` for a file and AT_REMOVEDIR, `renameat` for the name moved and a name replaced); `renameat` asks both directories, and write on a directory that changes parent; an existing name answers -EEXIST (-EADDRINUSE for `bind`) first, a missing one -ENOENT, and the permission comes before what the name is (-EISDIR, -ENOTDIR, -ENOTEMPTY); two names of one file are renamed with nothing asked. **Sticky** (`sticky_ok`): in an S_ISVTX directory a name goes only for its owner, the directory's owner or file-system user id 0 (-EPERM). **The protected settings** (R7, on, fixed): `may_follow` (a path's last component that is a link in a sticky world-writable directory is followed only by its owner or when the directory's owner owns it, root included; one in the middle of a path by anyone), `may_creat_open` (O_CREAT of an existing regular file there: the opener's or the directory owner's, else -EACCES, root included), `may_hardlink` (a non-owner links only a regular file without S_ISUID or S_ISGID with group execute that it may read and write, else -EPERM, before the directory's -EACCES). **`chmod`** (`chmod_as`, `owns`): the owner or file-system user id 0, else -EPERM; S_ISGID asked by one outside the group is dropped. **`utimensat`**: the owner or file-system user id 0 sets any times; anyone else both to now when the class gives write (of the file, not the descriptor), else -EACCES; other times -EPERM. **Set-ID bits** (`wrote`): a write of a byte or more (`write`, `writev`, `pwrite`, `sendfile`, `splice`, `copy_file_range`), O_TRUNC, `ftruncate`, `truncate` and `fallocate` by one whose file-system user id is not 0 take S_ISUID, and S_ISGID when the file is group-executable or the writer is outside its group — the writer's ids at the call. **`connect`** asks write of an AF_UNIX name before whether anything listens. `fallocate` (285), mode 0: the file grows by a hole; other modes refused by name |
| `procfs/` | `/proc/sys/fs/protected_hardlinks`, `_symlinks`, `_regular`, `_fifos`: `1`, mode 0644, root's |

- What is not there: signals, ports, the speaker, `/dev` modes (U5, px45: above); a
  FIFO (`mknod` is refused by name, so `protected_fifos` has nothing
  to act on); `/dev`'s and `/proc`'s directories keep their answers to
  making and removing names (-EROFS, -ENOENT); `fallocate`'s other
  modes; space set aside by `fallocate` (a hole, like `ftruncate`).

## Who may open, run and walk (px43)

The third lane of the users campaign (`notes/px43-the-file-checks.md`).
**The class rule now decides** `open`, `truncate`, the `access` family,
`execve`, `chdir`, `fchdir` and the search of every directory a path
walk passes. The campaign's ruled claim: these checks are **enforced
for honest programs; not a boundary against an attacker** — the
kernel has not been fuzzed or audited and loads programs at fixed
addresses.

| module | what |
|---|---|
| `files/` | `may(a, who, n, want)`: the one function every check calls. `who` is `cred.FS` (every call but the access family) or `cred.REAL` (`access`, `faccessat`, `faccessat2` without AT_EACCESS). That user id 0 reads and writes anything and searches every directory, and executes a non-directory only where some execute bit is set (R9). Anyone else gets one class, chosen once: the owner's bits for the owner, else the group's for a member (`member_as`: that group id or a supplementary group), else the others'. `walk_as` (`walk`, `walk_k`, `walk_who`) asks MAY_X of every directory a component is looked up in — `.`, `..` and the last component's included — before the component's length or existence; `openat` asks read, write or both by the access mode, write for O_TRUNC of a file, write and search of the directory for a name O_CREAT makes (a file the call made is exempt), and asks a socket's name before its -ENXIO; `truncate` write; `faccessat` the mode, with the real ids or (AT_EACCESS) the file-system ones, walking with the same ids; `exec_lookup` execute; `chdir` and `fchdir` search of the directory itself |

- pax#58: a pipe, a socketpair and an AF_UNIX socket are their maker's
  file-system ids to `fstat` (`files`' `P_OWNER`, `unix`'s `owned`),
  as on Linux; an AF_INET socket, an eventfd, an epoll object and an
  end `accept` made still say 0:0 (not measured).
- A descriptor keeps what it was opened with: no check runs on `read`,
  `write`, `ftruncate` (which asks only that the descriptor was opened
  for writing), `getdents64` or `fstat`.
- Files that are not the tree's — `/dev`'s devices, `/proc`'s and
  `/sys`'s files, what `/dev/std*` reopens — keep their answers (U5
  gives `/dev` modes that count); their directories are searched by the
  rule like any other (0755 and 0555: anyone may).
- What is not there: write on a directory to remove or rename a name,
  the sticky rule, the protected settings, `chmod` and `utimensat`
  ownership, set-ID clearing on a write (U4, px44: above); signals,
  ports, the speaker, `/dev` (U5); set-ID execution (R5). `execve` still runs only
  an archive file whole (px27): a program written since boot is refused
  whatever its mode.

## The writable tree (px27)

Every kernel that links `kernel/user` makes the file tree at
`user.start` (`tree.start`): the initramfs's entries are its first
inodes, and from then on it is written, grown and emptied by the
programs. `tests/mpx3-tree` holds it to Linux's tmpfs.

| module or file | what |
|---|---|
| `tree/` | **inodes** (16 words; a table that grows a frame at a time, 32 a frame, at most 16,384; a freed inode is the next one made): mode, link count, size, holders (`hold`, `release`: open files, working directories, a removed directory's hold on its parent), four times, where the bytes are. **a file's bytes**: frames under an index of depth 0 (the frame alone), 1 (512 pointers) or 2 (1 GiB, the largest file); a page never written has no frame (`span` answers the page of zeros); `cut` gives back every frame past a size. **the initramfs under it** (`start`, `adopt`): an archive file's inode reads the archive in place (`I_BACK`, `I_BACKLEN`) until a page is written, which copies that page; `archive_entry` says whether a file is still the archive's whole (what `execve` can load). **directories**: records (inode + 1, lengths, name), none across a page, a removed one free again and joined to the free ones after it; `lookup`, `entry_at` (the first live record at or after a position, found from its page's start), `name_of`; a directory with no entry holds no frame. **the changes**: `create`, `mkdir`, `unlink`, `rmdir`, `rename` (every refusal and the room for the new name before the first change), `truncate`, `read`, `write` (from a user buffer or kernel bytes). **the cap**: half the frames free at `start`, and never below `RESERVE` (2,048) free in the machine (`grab`); `held`, `live`, `table_frames`, `base` for the books; `census_due`, `full_news` for kernel/user's lines; `refuse` counts a refusal by name |
| `../boot/tree.S` | `pax_tree_state` (32 words), `pax_tree_copy` and `pax_tree_zero` (REP MOVS, REP STOS on kernel addresses) |
| `files/` | a node may be an inode (`T_INO`); `walk` resolves a path a directory at a time (`.`, `..`, -ENOTDIR, -ENOENT, -ENAMETOOLONG for a component past 255 bytes; the directory and name of the last component for the calls that make or remove one); `openat` with `O_CREAT`, `O_EXCL`, `O_TRUNC`, `O_APPEND`, `O_WRONLY`/`O_RDWR`, `O_NOFOLLOW`, the mode and `umask`; `file_write`, `pwrite`, `ftruncate`, `truncate`, `fsync`, `mkdirat`, `unlinkat`, `renameat`, `faccessat`, `umask`, `refused`; `copy_file_range` and `sendfile` between files, `splice` from a pipe into one; an open file and a working directory hold their inode (`of_new`, `of_drop`, `set_cwd`, `inherit`, `close_all`); `getcwd` walks up; `put_stat`/`put_statx` with times, blocks and two device numbers (the tree 0:1, `/dev` 0:5; px36: signed times, `tsec`/`tnsec`); `getdents` from the records (px36: `DT_LNK`), `dev` last in the root; `exec_lookup` asks `tree.archive_entry` |
| `initramfs/` | `mtime` |
| `user/` | `tree.start` in `start`; the dispatch (18, 21, 74-77, 82-84, 87, 95, 258, 263, 264, 269, 316, 439; px36's `change_calls`: 86, 88, 90-94, 260, 265, 266, 268, 280, 452; refused by name 132, 133, 235, 259); `write` to a file; `tree_lines` (every 2500th file removed: the books; the tree at its cap) and `tree_report` (after a kernel's frames line) |
| `kmain_console.lu` | `user.tree_report()` after the frames line |

- Layering: `user` → `files` → `tree` → `frames`, `initramfs`, `paging`.
  `tree` knows no descriptor, path or process; `files` keeps those and
  holds inodes by number.
- px36 (`notes/px36-the-file-changes.md`): `tree`'s `link`, `symlink`
  (S_IFLNK|0777, the target held as a file's bytes; `target`),
  `set_mode`, `set_times` (signed nanoseconds), `owned` (root's chown; px42: `chown`);
  `files`' `walk` follows a symbolic link before the last component and,
  as the call says, at it (the path rewritten in pax_kbuf, 40 at most),
  and `linkat`, `symlinkat`, `readlinkat`, `fchmodat`, `fchmod`,
  `fchownat`, `utimensat`; `changeable` refuses a change to what PAX
  keeps fixed (-EROFS). (px42: `owned` is `chown` and keeps any id;
  `root_or_none` and its -EINVAL are gone.)
- What is not there: `utime` and `utimes`
  (refused by name), `mmap` of a file, a second writable file system (`/dev` is
  fixed), `/proc` and `/sys` beyond `/proc/self/exe`, file locks,
  `fallocate`, `statfs`. `execve` runs a file only while it is still
  the archive's own bytes.

## Readiness (px24)

`poll`, `epoll` and `eventfd`: what wolf's hosted runtime and lobo ask
of Linux the moment a call must wait (`notes/px24-readiness.md`).

| module | what |
|---|---|
| `event/` | new: 64 eventfd counters and 16 epoll objects (256 registrations each, in four frames an object holds while it lives); a registration is the open file and descriptor number it was added by, its events, its data, the two counts it last answered at; `forget` drops an open file's registrations at its last close |
| `ready/` | new: `poll`, `epoll_create1`, `epoll_ctl`, `epoll_wait`, `eventfd2`, `sched_getaffinity`; the refusals by name; the books' line |
| `files/` | kinds `K_EVENT` and `K_EPOLL`; `poll` and `poll_of`: what each kind of descriptor says (a pipe's two ends, a socketpair, a datagram socket, a stream socket through `tcp.poll`, an eventfd, the console, a file); `watch`; an eventfd's `read` and `write`; 128 descriptors in the area's second half, 512 open files, 64 pipes; the console's status flags |
| `tcp/` | `poll`: a block's bits by its state, and two counts (arrivals; room come back after a send found none); 256 blocks, a listen queue of 128; a reset keeps what was received |
| `udp/` | `poll` |
| `sched/` | 64 slots; a thread's deadline word (`self_until`), alternate signal stack, `block_pipe_eintr`; console input wakes the threads in `poll` too |
| `signal/` | `sigaltstack`; a handler with SA_ONSTACK starts at the alternate stack's top |
| `socket/` | a waiting send's progress and a receive's deadline are the thread's; `SO_ACCEPTCONN`; -EALREADY |
| `user/` | 7, 20, 131, 204, 232, 233, 290, 291; `writev`; `getrandom`'s flags; a wait in `poll` or `epoll_wait` is never restarted |

- Layering: `user` → `ready` → `files` → `event`, and `files` → `tcp`,
  `udp`, `console` as before. `event` imports nothing but `frames`: it
  is storage and bookkeeping, so `files` can free an eventfd or an
  epoll object at a last close without a cycle.
- **Readiness is computed at the wait.** Nothing keeps a queue of
  waiters and there is no ready list. A call that finds nothing
  answers `files.WAIT`; the thread parks as a pipe's reader does, and
  every change anywhere (`sched.wake_pipes`, sixteen call sites, and
  `epoll_ctl`) makes every waiter ready to run its call again. No lock
  is needed for it (a system call runs with IF clear on one CPU; the
  eight lock words are all taken), and the one wake that could fall
  between a look and a wait — the call's own traffic still on the
  loopback queue — is px23's drain, after which the call runs again.
  The cost is a call run for nothing: the books count them (`user:
  ready: … waits <w>, empty <m> …`).
- Level-triggered: an event is answered while it holds. Edge-triggered:
  when it holds and a count has moved since the registration last
  answered. The counts are each kind's own: a pipe's bytes written and
  the times a read gave a writer room; a stream socket's RCV.NXT with
  its state, and the times an acknowledgement made room after a send
  had found none; a listener's connections become ready to accept; an
  eventfd's adds and takes.
- A registration is keyed by (open file, descriptor number), as
  Linux's: a duplicate descriptor keeps it alive after the first is
  closed, and it goes with the open file's last descriptor.
- Not yet: `ppoll`, `select`, `pselect6`, `epoll_pwait`,
  `epoll_pwait2`, `readv`, `sendmsg`, `recvmsg`, `timerfd`, `signalfd`
  (no strace of lobo or of a wolf program shows one);
  `EPOLLEXCLUSIVE`, `EPOLLWAKEUP`, nested epoll objects,
  `EFD_SEMAPHORE`, `SS_AUTODISARM` (refused by name); the console or
  `/dev/null` in an epoll object; wait queues an object (past about a
  hundred waiting threads the wake-everyone rule would cost); memory
  taken when a page is first touched (a wolf task's 8 MiB stack costs
  2,072 frames at its `mmap`); AF_UNIX path sockets.
