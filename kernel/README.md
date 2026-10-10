# kernel/

The wolf kernel: first light (px01, M-PX1), physical frames (px02), paging (px03), interrupts (kw10), preemptive kernel threads (px07), the heap (px06) and user mode (px09, below), on the wolf 0.2.26 release archive (px05 moved pax to the archive at 0.2.23; px07 to 0.2.24 for kw11's atomics; px10 to 0.2.25; px16 to 0.2.26). `kmain.lu` brings up COM1,
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
| `heap/` | the kernel heap and wolf's allocator hook (px06): `wolf_alloc`/`wolf_free` as `export fn`s over `alloc`/`free`; PML4 slot 384 (`0xffffc00000000000`): a state page and 64-byte page descriptors, then the heap's pages from `0xffffc04000000000`, each a `frames.alloc()` frame mapped RW+NX by `paging.map` as the heap grows, never unmapped; address-ordered first-fit page runs with boundary tags for sizes above 2048, eight power-of-two size classes (16-2048) in their own zone (`0xffffc05000000000`) with a per-page allocated map; limit 32768 pages (128 MiB); named panics (`PANIC heap: double free …`, `free outside the heap`, `free with the wrong size`, `out of memory`, …); `report`, `pages`, `live_blocks`, `frames_taken`, …; `alloc`/`free` under `sync.heap()` (px07's threads are preempted); no `region` across a thread switch until wolf-lang#611 |
| `panic/` | `wolf_trap`, the freestanding trap hook, in wolf; `fail(what, v)`, a fault the kernel detects, by name; `halt` |
| `sync/` | the spinlock (px07): a lock is an 8-byte word's address; `acquire` saves RFLAGS and clears IF, then test-and-test-and-set (`atomic_load` relaxed, `atomic_cas` acquire/relaxed, kw11), `release` is a release store and IF as saved; `irq_save`/`irq_restore`/`enable`, `relax` (PAUSE), `console()` (the lock threads write whole lines under) |
| `sched/` | kernel threads on one CPU (px07): 16 records in `boot/sched.S`'s `.bss` (`#[repr(c)] Thread`, its words at `offset_of`), slot 0 the kernel's own context, slot 1 the idle thread (`pax_idle`, HLT with IF set); each stack four frames mapped RW NX at the top of its slot's 64 KiB in PML4 slot 416 (`0xffffd00000000000`), the 48 KiB below never mapped (the guard); a FIFO run queue; `preempt` (the tick: wake sleepers, rotate after a two-tick quantum, idle gives way at once), `switched` (after `pax_switch`), `create(body, arg)`, `yield`, `sleep(n) -> (from, woke)`, `wait_all`, `exit` (the stack reaped by the next `create` or `wait_all`), `guard_of` (for the overflow panic), `report` |
| `process/` | processes (px14): a program's image and psABI stack (moved from `user/`), `clone`/`clone3`/`vfork` (CLONE_VM\|CLONE_VFORK: the child borrows the parent's space, the parent waits until it execs or ends), `execve` (path, argv, envp copied out first; close-on-exec, handled signals reset, the old space given back or handed back to the vfork parent), `wait4`/`waitid` (zombies reaped, Linux's status words, WNOHANG, a blocked wait re-runs when a child ends), `rt_sigprocmask`/`rt_sigaction` recorded, `kill` refused by name |
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
- `wolf.pin` names wolf: the 0.2.26 release archive by digest (px16;
  0.2.25 from px10, 0.2.24 from px07, 0.2.23 from px05;
  `tools/fetch-wolf` stages it and never builds; px02 and kw10 built
  wolf-lang `eb955c3b` and `6a4e6151` from source while no release
  carried kw06-kw09), and lupin's release and digest
  (`tools/fetch-lupin`; 0.1.49, 0.2.26's pairing, since px16; 0.1.48
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
  no `region` anywhere near a return to ring 3 (wolf-lang#611).
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
  live, and the FPU areas are frames (wolf-lang#611's rule holds).
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
