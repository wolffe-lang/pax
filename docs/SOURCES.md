# SOURCES — what each change was written from

The clean-room rule (`CLAUDE.md`) requires this log. Every lane adds its
entries: what it consulted, at which version, for which file, and how
(read, black-box run, or the author's own knowledge with no text copied).
**Linux kernel source is never an entry**: the allowed Linux material is the
uapi headers, the syscall tables, `Documentation/`, and black-box behaviour.

## px00 — the harness (2026-10-02)

**Linux: nothing.** `wolf/refs/repos/linux` was not opened; no Linux file of
any kind was read. Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| The Limine Boot Protocol, `PROTOCOL.md` | limine-protocol `3a0526b700e356f0eac1b71a77697b3fd1c707a3` | 0BSD | read: General Notes, Requests Delimiters, Base Revisions and their summary, Memory Layout at Entry, x86-64 Machine State at Entry, Features (request/response), Firmware Type Feature | `boot/stub/pax-stub.s` (marker, tag and request words), `boot/stub/linker.ld`, `docs/BOOT.md` |
| Limine `CONFIG.md`, `USAGE.md` | Limine `v12.9.1` | BSD-2-Clause | read: config file location and syntax, global `timeout`/`quiet`, the `limine` protocol entry; hybrid ISO creation and `bios-install` | `boot/limine.conf`, `tools/mkimage` |
| Limine release binary `limine-binary.tar.gz` | `v12.9.1`, sha256 `5cdebc51…` | BSD-2-Clause | fetched by digest and run, never vendored; its `Makefile` read to build the host tool | `tools/fetch-limine`, the image |
| QEMU (`isa-debug-exit`, `-gdb`/`-S`, `-no-reboot`, pflash firmware, `-serial file:`) | 11.1.1 (macOS), Ubuntu's apt build (CI) | GPL-2.0 (a program we run) | the author's own knowledge of the documented options, then black-box: status 33 for `0x10` measured on both hosts | `tools/qemu-run`, `tools/qemu-gdb` |
| Intel 64 and IA-32 SDM, vol. 2 and 3 | — | — | the author's own knowledge: `IN`/`OUT`/`HLT`/`CLI`; `CR4.OSFXSR` and #UD for SSE | the stub; `docs/BOOT.md` clause 3 |
| PC16550D UART register map (base+0 THR, base+5 LSR, bit 5 THR empty) | — | — | the author's own knowledge | the stub's `puts` |
| multiboot2 specification; UEFI specification 2.10 (PE32+, boot services, `ExitBootServices`) | — | GNU FDL; UEFI Forum | the author's own knowledge, for the comparison only | `docs/BOOT.md` |
| xorriso, `as`/`ld` (GNU binutils), gdb | distro builds | GPL-3.0 (programs we run) | run | `tools/mkimage`, `tools/build-stub`, `tools/qemu-gdb` |

## kw05 — the first boot, M-KW (2026-10-03)

**Linux: nothing.** No Linux file of any kind was read, and no glibc source.
Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| The Limine Boot Protocol, `PROTOCOL.md` | limine-protocol `3a0526b7…` (as px00) | 0BSD | px00's reading, through `docs/BOOT.md` and `boot/stub/pax-stub.s`: the request markers, base revision 6 and its third word, entry state (64 KiB stack, a zero return address, long mode, higher half) | `boot/start.S`, `boot/kernel.ld` |
| System V AMD64 psABI | 1.0 | — | the author's own knowledge: argument registers (`%edi`, `%esi`, …), `%rax` result, 16-byte stack alignment at a call, the red zone | `boot/io.S`, `boot/start.S`, `tools/build-kernel`'s red-zone check |
| Intel 64 and IA-32 SDM, vol. 2 | — | — | the author's own knowledge: `IN`/`OUT`/`CLI`/`HLT`/`DIV` | `boot/io.S`, `boot/start.S` |
| PC16550D UART register map | — | — | the author's own knowledge, as px00 | `boot/io.S`'s `puts` |
| QEMU `isa-debug-exit` | as px00 | GPL-2.0 (a program we run) | black-box: status `(v << 1) | 1` (33 for `0x10`, 3 for `0x01`) measured | `boot/io.S`, `tests/mkw` |
| the wolf spec (`spec/04-abi.md` §5–§6, `spec/08-package.md`) and wolf-lang's kw04 gate stubs | wolf-lang kw05 | the project's own | read | `kernel/*.lu`, `kernel/wolf.pkg`, `boot/io.S` (`wolf_trap`'s signature) |
| GNU binutils (`nm`, `objdump`, `as`), LLVM `clang`/`ld.lld` | distro builds | programs we run | run | `tools/build-kernel` |

## px01 — first light, M-PX1 (2026-10-03)

**Linux: nothing.** No Linux file of any kind was read, and no glibc
source. Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| The Limine Boot Protocol, `PROTOCOL.md` | limine-protocol `3a0526b700e356f0eac1b71a77697b3fd1c707a3` (fetched from its repository, as px00) | 0BSD | read: Features (request/response layout), Bootloader Info, Firmware Type, HHDM, Memory Map (types, sorting, alignment), Paging Mode (the x86-64 default), Memory Layout at Entry (the HHDM may vary between boots), Base Revision 6 | `boot/start.S` (the four requests), `boot/limine.S`, `kernel/boot_info`, `tests/mpx1`'s A2 shapes |
| PC16550D UART register map | public datasheet facts | — | the author's own knowledge: register offsets (THR/RBR, IER, FCR, LCR, MCR, LSR, SCR), LCR's DLAB, the divisor latch, 8N1, FCR's enable/clear/trigger bits, MCR's loopback/OUT2, LSR's data-ready and THR-empty bits, the 1.8432 MHz clock (divisor 1 = 115200) | `kernel/serial` |
| System V AMD64 psABI | 1.0 | — | the author's own knowledge, as kw05 | `boot/limine.S`, `boot/io.S` |
| Intel 64 and IA-32 SDM, vol. 2 and 3 | — | — | the author's own knowledge: `IN`/`OUT`/`CLI`/`HLT`; `RFLAGS.IF` (bit 9) | `boot/io.S`, `tools/qemu-halt` |
| QEMU human monitor (`-monitor pipe:`, `info registers`, `quit`) | 11.1.1 (kasumi, hasu), Ubuntu's apt build (CI) | GPL-2.0 (a program we run) | the author's own knowledge of the documented options, then black-box: the `RIP=… RFL=… HLT=` line measured under TCG and KVM | `tools/qemu-halt` |
| the wolf spec (`spec/04-abi.md` §5–§6, `spec/05-conformance.md` `[conf.trap.set]`, `spec/01-grammar.md` §2) and wolf-lang's `crates/wolf_rt/src/native.rs` `trap_code` / `crates/wolf_driver/src/main.rs` (`--emit=obj`) | wolf-lang `8e36bc1a` (v0.2.22) | the project's own | read | `kernel/panic` (the hook's signature, kind numbers), `tools/build-kernel` (the multi-object output) |
| GNU binutils (`nm -S`), LLVM `clang`/`ld.lld`, xorriso | distro builds | programs we run | run | `tools/build-kernel`, `tools/qemu-halt` |


## px04 — the census (2026-10-04)

**Linux: the syscall table only.** From the planning repo's sparse refs
clone (`wolf/refs/repos/linux` at `3b7cab693`), exactly one file was
opened: `arch/x86/entry/syscalls/syscall_64.tbl`, for numbers and names
(`tools/census/syscall_64.csv`). No uapi header was needed; no other
Linux file of any kind was read, and no glibc source. Everything else
about Linux and glibc in `docs/CENSUS.md` is black-box behaviour of
programs run in a container on kasumi (host kernel 7.2.3-1-cachyos).
Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| `arch/x86/entry/syscalls/syscall_64.tbl` | refs clone `3b7cab693` | GPL-2.0 WITH Linux-syscall-note | read: numbers, ABI column, names (facts of the ABI) | `tools/census/syscall_64.csv` |
| strace | 7.2 (Arch `strace 7.2-1`) | LGPL-2.1+ (a program we run) | run: `-ff -o`, `-f -c`, `-y`, `-s`, `-e inject=…:error=ENOSYS`, `--kill-on-exit`, `--argv0` (from `strace -h`); its decoded output is the census's only input | `tools/census/inside/trace.sh`, `tally.py`, `inject-wrap.c` |
| GNU gdb | 18.1 | GPL-3.0 (a program we run) | run: `starti`, `info auxv`, `catch syscall`, access watchpoints, the Python API (the author's own knowledge of the documented interface) | `tools/census/inside/auxv.py` |
| System V AMD64 psABI | 1.0 | — | the author's own knowledge: the initial process stack (argc, argv, NULL, envp, NULL, auxv pairs to `AT_NULL`), `AT_IGNORE` = 1, `AT_SYSINFO_EHDR` = 33 | `tools/census/inside/auxv.py` |
| ptrace on x86-64 | — | — | the author's own knowledge, confirmed black-box (counts agree with strace's): at a syscall-entry stop `rax` holds `-ENOSYS` and `orig_rax` the number | `auxv.py`'s vDSO count |
| podman | 6.1.3 (kasumi) | Apache-2.0 (a program we run) | run, rootless, a lane-private store | `tools/census/census` |
| Arch Linux `archlinux:base-devel` | digest `sha256:8185e444…`, then `pacman -Syu` on 2026-10-04 (`out/image-pacman-Q.txt`) | various (programs we run) | run: the traced userspace (glibc 2.44, bash 5.3.20, dash 0.5.13.4, pacman 7.1.0, gcc 16.2.1, make 4.4.1, OpenSSH 10.5p1, curl 8.22.0) | every workload |
| boreutils | `010f3144a9ba…` | GPL-3.0 (the project's own) | read: `tools/difftest` (its CLI, `--bin`, the case-result lines), `tools/build` (the link), `wolf-toolchain.toml` (the std pin); run: the suite | `workloads/boreutils-*.sh`, `inject.sh`, `stage.sh` |
| lobo | release v0.1.1 (archive `6e21e151…`), trunk `f79418d1181d…` for `demo/reel` | GPL-3.0 (the project's own) | read: the reel's scripts (`lib.sh`, `preflight.sh`, `scene4.sh`, `teardown.sh`) and configs; run: lobo | `workloads/lobo.sh` |
| wolf | release v0.2.22 (archive `df0f2fea…`) | the project's own | run: `wolf build --release` (the link line read from `--verbose`), `wolf run` | `stage.sh` |

## px02 — physical frames (2026-10-04)

**Linux: nothing.** No Linux file of any kind was read, and no glibc
source. Permissively licensed kernels: none consulted (the bitmap
allocator is the author's own knowledge of a textbook structure).

| source | version | licence | how | used for |
|---|---|---|---|---|
| The Limine Boot Protocol, `PROTOCOL.md` | limine-protocol `3a0526b700e356f0eac1b71a77697b3fd1c707a3` (fetched from its repository, as px00/px01) | 0BSD | read: Memory Layout at Entry (what the HHDM maps at base revision 3 and later; the image physically contiguous at one offset), Memory Map Feature (the types, sorted entries, usable and bootloader-reclaimable entries 4 KiB aligned and never overlapping, executable/module entries illustrative only), Executable Address Feature (id words, `physical_base`, `virtual_base`), HHDM Feature | `boot/start.S` (the sixth request), `kernel/boot_info` (every layout offset), `kernel/frames` |
| the wolf spec (`spec/02-memory-model.md` `[mem.unsafe.volatile]`, `[mem.prov.expose]`, `[mem.prov.device]`, `[mem.unsafe.sig]`) and wolf-lang's kw06/kw07 fixtures (`crates/wolf_driver/tests/fixtures/freestanding_device/kmain_device.lu`, `fixtures/volatile/vol.lu`) | wolf-lang `eb955c3b` | the project's own | read | `kernel/boot_info`, `kernel/frames`, `kernel/kmain_frames.lu` (the spellings `N as *T`, `*p`, `with_addr`, `read_volatile`/`write_volatile`; `*T` only in private signatures) |
| wolf-lang `crates/wolf_driver/src/main.rs` (`version_identity`, `WOLF_COMMIT`) | wolf-lang `eb955c3b` | the project's own | read | `tools/fetch-wolf` (stamping a source build so `--version` names its commit) |
| System V AMD64 psABI | 1.0 | — | the author's own knowledge, as kw05 | `boot/limine.S` |
| GNU `ld` / LLVM `ld.lld` linker-script symbol assignment | distro builds | programs we run | the author's own knowledge | `boot/kernel.ld` (`__pax_image_start`, `__pax_image_end`) |

## px03 — paging (2026-10-04)

**Linux: nothing.** No Linux file of any kind was read, and no glibc
source. Permissively licensed kernels: none consulted (the paging
structure is the architecture manuals'; the code is the author's own).

| source | version | licence | how | used for |
|---|---|---|---|---|
| Intel 64 and IA-32 Architectures SDM, vol. 3A, ch. 4 "Paging": §4.1.3 (paging-mode modifiers: CR0.WP, IA32_EFER.NXE), §4.5 (4-level paging and its entry-format tables: PML4E, PDPTE referencing a PD, PDE mapping a 2 MiB page, PDE referencing a PT, PTE), §4.6 (access rights: the combination over levels, supervisor writes under CR0.WP, execute-disable), §4.10.4 (invalidation: MOV to CR3, INVLPG, CR4.PGE) | — | — | the author's own knowledge of the named sections; no text copied | `kernel/paging` (entry bits, indices, the walk, W^X, the switch), `boot/cpu.S` |
| Intel SDM vol. 2 (MOV to/from control registers, RDMSR, WRMSR, INVLPG, CPUID leaf 0x80000001 EDX bit 20); vol. 3A §2.2.1 (IA32_EFER bits), §2.5 (CR0, CR3, CR4), §6.15 (#DF; a fault while delivering #DF is a triple fault) | — | — | the author's own knowledge | `boot/cpu.S`, `tools/qemu-fault`, `kmain_text_write.lu`'s argument |
| AMD64 Architecture Programmer's Manual, vol. 2: §3.1.7 (EFER), §5.3 (long-mode page translation), §5.4 (page-translation-table entry fields), §5.5 (TLB invalidation), §5.6 (page protection: NX, WP) | — | — | the author's own knowledge, as a cross-check of the Intel sections | `kernel/paging`, `boot/cpu.S` |
| The Limine Boot Protocol, `PROTOCOL.md` | limine-protocol `3a0526b700e356f0eac1b71a77697b3fd1c707a3` (as px00–px02) | 0BSD | read: Base Revision Changes Summary (what the HHDM maps at revisions 3 and 4; no identity map since revision 1), Memory Layout at Entry (PT_LOAD permissions, one uniform virtual-to-physical offset, bootloader page tables in bootloader-reclaimable memory), Caching (x86-64: WB through PAT0), x86-64 Machine State at Entry (CR0.WP, EFER.NXE when available, every other CR0/CR4/EFER bit clear and IDTR limit 0 at revision 5 and later; GDT and stack in bootloader-reclaimable memory) | `kernel/paging` (what the HHDM keeps, what it leaves out), `kmain_text_write.lu` |
| QEMU human monitor (`info registers`, `info tlb`, `info mem`, `xp /Ngx`, `print`, `info status`) and options `-no-shutdown`, `-d int,cpu_reset`, `-D` | 11.1.1 (kasumi, hasu), Ubuntu's 8.2 (CI) | GPL-2.0 (a program we run) | the author's own knowledge of the documented commands, then black-box: `info tlb`'s nine flag columns (X G P D A C T U W) measured on a kernel with known mappings; `$cr3` in an expression works on 11.1.1 and is "unknown register" on 8.2 (CI run 37180318852); a triple fault under `-no-reboot -no-shutdown` pauses the machine ("paused (shutdown)") with CR2 intact, on TCG and KVM | `tools/qemu-halt --cmd`, `tools/qemu-fault`, `lib.sh`'s `mon_cmd`, `tests/mpx2-paging` |
| GNU binutils `readelf -lW`, `nm` | distro builds | programs we run | run | `tests/mpx2-paging` G1 |


## kw10 — interrupts (2026-10-04)

**Linux: nothing.** No Linux file of any kind was read, and no glibc
source. Permissively licensed kernels: none consulted (the trampoline,
the tables and the handlers are the architecture manuals' structures;
the code is the author's own).

| source | version | licence | how | used for |
|---|---|---|---|---|
| Intel 64 and IA-32 Architectures SDM, vol. 3A, ch. 6 "Interrupt and Exception Handling": §6.10 (IDTR), §6.12.1 (interrupt vs trap gates and IF), §6.13 (error code), §6.14.1 (64-bit mode IDT: the 16-byte gate, Figure 6-8), §6.14.2 (the 64-bit stack frame: SS, RSP, RFLAGS, CS, RIP pushed unconditionally, the stack aligned to 16 first), §6.14.3 (IRET in IA-32e mode), §6.14.5 (the interrupt stack table), §6.15 (exception and interrupt reference: interrupts 0-31, #PF's error code and CR2, #DF and Table 6-5's contributory/page-fault classes), Table 6-1 (vectors, names, which push an error code) | — | — | the author's own knowledge of the named sections; no text copied | `boot/isr.S`, `kernel/idt`, `kernel/interrupts` (the names), `kmain_double_fault.lu`'s argument |
| Intel SDM vol. 3A §3.4.5 (segment descriptors, Figure 3-8), §3.5.1 (descriptor tables), §7.2.3 (the TSS descriptor in 64-bit mode), §7.7 (task management in 64-bit mode: the 64-bit TSS, Figure 7-11, IST1-7, the I/O map base); §4.7 (#PF error code bits); §11.4.1, §11.4.4, §11.5.1, §11.5.4, §11.12.3 and Table 11-1 (the local APIC: its MMIO page and IA32_APIC_BASE, the LVT and ExtINT, the APIC timer, the register offsets); §4.9.2 (PCD/PWT and the PAT's power-on entries) | — | — | the author's own knowledge | `kernel/gdt`, `kernel/apic`, `kmain_text_write.lu` |
| Intel SDM vol. 2 (LGDT, LIDT, LTR, IRETQ, RET far, STI's one-instruction interrupt shadow, HLT, MOV from CR2, RDMSR) | — | — | the author's own knowledge | `boot/isr.S`, `boot/cpu.S` |
| AMD64 Architecture Programmer's Manual, vol. 2: §4.8 (long-mode segment descriptors, the system-segment and gate formats), §8.2 and Table 8-1 (vectors; #VC 29 and #SX 30 push an error code; 28 the hypervisor injection exception), §8.4 (error codes), §8.9 (long-mode interrupt control transfers: gates, the stack frame, IST), §12.2.5 (the 64-bit TSS) | — | — | the author's own knowledge, as a cross-check of the Intel sections and for vectors 28-30 | `boot/isr.S` (the error-code set), `kernel/interrupts` (the names), `kernel/gdt` |
| Intel 8259A programmable interrupt controller data sheet (ICW1-ICW4, OCW1-OCW3, the in-service register, the spurious IR7 request) and Intel 8254 programmable interval timer data sheet (the control word, mode 2, the counter's 1.193182 MHz input as the PC wires it); the PC's port assignments (0x20/0x21, 0xa0/0xa1, 0x40-0x43) | — | — | the author's own knowledge | `kernel/timer` |
| System V AMD64 psABI | 1.0 | — | the author's own knowledge: %rdi, the callee-saved registers, %rsp 16-aligned at a call, DF clear at entry | `boot/isr.S`'s common path |
| the wolf spec (`spec/04-abi.md` `[abi.interrupt]`, `[abi.layout.packed]`, `[abi.layout.query]`, `[abi.link.extern]`; `spec/02-memory-model.md` `[mem.static]`) and the kw10 witness (`crates/wolf_driver/tests/fixtures/freestanding_interrupt/`) | wolf-lang `kw10` branch over `6a4e6151` (PR wolf-lang#578) | the project's own | written by this lane | the frame, the tables in assembly-reserved .bss, the handler's shape |
| QEMU human monitor (`info registers` — CR2, RSP, CS/SS/TR, GDT=, IDT=; `info pic`; `info lapic`) | 11.1.1 (kasumi), Ubuntu's 8.2 (CI) | GPL-2.0 (a program we run) | black-box: Limine leaves the local APIC enabled with LINT0 masked (LVT0 `0x00018700` under SeaBIOS, `0x00010700` under OVMF) and the 8259's IRR holding line 0 — measured, not read | `kernel/apic`, `tests/mpx2-interrupts` I1, I4, I6 |

## px05 — the archive pin, the workarounds retired (2026-10-04)

**Linux: nothing.** No Linux file of any kind was read, and no glibc
source. Permissively licensed kernels: none consulted. No new hardware
fact: every register, bit and layout `serial`, `frames` and `paging`
name was already cited by px01-px03; px05 only gave them names.

| source | version | licence | how | used for |
|---|---|---|---|---|
| the wolf spec (`spec/04-abi.md` `[abi.layout.c]`, `[abi.layout.query]`; `spec/02-memory-model.md` `[mem.static]` .1-.3) and wolf-lang's witnesses `corpus/comptime/offset_of_layout.lu`, `corpus/memory/packed_fields_at_offset_of.lu` | wolf-lang `v0.2.23` (`8edac3ee`) | the project's own | read | `frames`' `FrameState` (a field read or written as a scalar at its `offset_of` is an ordinary raw access on every machine), the module `var` and its accessor, `const` initializers naming other `const`s |
| wolf-lang release v0.2.23 (403069562) and wolf-interp release v0.1.46 (403040421): asset digests from the release API | — | — | read | `kernel/wolf.pin` (the x86_64-unknown-linux-gnu archive, `6f505eb5…`) |
| wolf-lang `git log`/`git diff 6a4e6151..v0.2.23` | — | the project's own | read | that no compiler source moved between the source pin and the tag |

## px07 — the scheduler (2026-10-06)

**Linux: nothing.** No Linux file of any kind was read, and no glibc or
other libc source. Permissively licensed kernels: none consulted. The
design — a frame saved on the interrupted thread's own stack and
resumed by `iretq`, a hand-built frame for a voluntary switch, a FIFO
run queue, an idle thread that halts, reaping a dead thread's stack from
another thread, a test-and-test-and-set lock with interrupts off — is
textbook operating-systems material, written from the manuals' mechanics
below; no kernel's code was looked at.

| source | version | licence | how | used for |
|---|---|---|---|---|
| Intel SDM vol. 3A ch. 6: §6.8.1 (masking maskable interrupts: IF, CLI, STI), §6.12.1 (a call through an interrupt gate: no stack switch without a privilege change, IF cleared), §6.14.2 (the 64-bit mode frame: RSP aligned to 16, SS, RSP, RFLAGS, CS, RIP pushed unconditionally), §6.14.3 (IRET in IA-32e mode pops all five at the same privilege), §6.15 interrupt 8 and Table 6-5 (a page fault while delivering a page fault is a double fault; #DF's saved CS:RIP undefined), interrupt 14 and §4.7 (CR2 holds the faulting linear address) | — | — | the author's own knowledge of the named sections; no text copied | `boot/isr.S` (the resumed frame), `boot/sched.S` (`pax_switch`'s frame, `pax_irq_save`/`restore`), `kernel/sched` (the guard), `kernel/interrupts` (the stack-overflow panic from #DF's CR2) |
| Intel SDM vol. 3A §9.1.2 (bus locking: a LOCK-prefixed read-modify-write is atomic against every processor) and vol. 2 (CMPXCHG, PAUSE, PUSHF/POPF, HLT, IRET) | — | — | the author's own knowledge | `kernel/sync`, `boot/sched.S` |
| AMD64 APM vol. 2 §8.9.3 (the long-mode interrupt stack frame), §8.9.5 (IRET in long mode) | — | — | the author's own knowledge, as a cross-check of the Intel sections | `boot/sched.S` |
| Intel 8259A data sheet (a request stays in the IRR while masked by IF, so a tick deferred by a held lock is taken at the STI) | — | — | the author's own knowledge | `kernel/sync`'s argument |
| System V AMD64 psABI | 1.0 | — | the author's own knowledge: callee-saved registers survive `pax_switch`, %rsp 8 mod 16 at a function's entry, %rdi the first argument | `boot/sched.S` |
| the wolf spec at v0.2.24: `spec/03-concurrency.md` §1 `[conc.mm.atomic]` (`.order`, `.raw` .1-.5, `[conc.mm.fence]`), `spec/04-abi.md` `[abi.interrupt]`, `[abi.c.export]`, `[abi.link.extern]`, `spec/02-memory-model.md` (`read_volatile`/`write_volatile`), `spec/01-grammar.md` `[gram.inv.kw]` (`spawn` is reserved) | wolf-lang `v0.2.24` (`294d626d`) | the project's own | read | the lock's orders, a thread body named by `extern "c" let`, the record's words read volatile |
| wolf-lang release v0.2.24 (404332628) and wolf-interp release v0.1.47 (404283632): asset digests from the release API | — | — | read | `kernel/wolf.pin` (the x86_64-unknown-linux-gnu archive, `501d6d3f…`) |

## px06 — the kernel heap (2026-10-06)

**Linux: nothing.** No Linux file of any kind was read, and no glibc or
other libc source. Permissively licensed kernels: none consulted. The
allocator (address-ordered first-fit page runs with boundary tags,
power-of-two size classes with an allocated map per page) is the
author's own design from general knowledge of allocators; no allocator's
source was read.

| source | version | licence | how | used for |
|---|---|---|---|---|
| the wolf spec, `spec/04-abi.md` `[abi.target.none]`, `[abi.target.none.hooks]`, `[abi.target.none.alloc]`; `spec/02-memory-model.md` `[mem.static]`, `[mem.region.account.2]` | wolf-lang `v0.2.24` (`294d626d`) | the project's own | read | the hook pair's contract (align 16, sizes multiples of 16, a null traps `alloc-contract`, free once with its own size, root grants never freed, no lock), `live_region_bytes`, module state only in `unsafe` |
| wolf-lang `crates/wolf_rt_none/src/{lib,native,str}.rs`, `crates/wolf_rt/src/{list,map}.rs` (doc comments and the sizes they ask) | `v0.2.24` | the project's own | read | the region chunk ladder (1 KiB doubling to 1 MiB, +16-byte link), the 64-byte region header, the strbuf (32-byte header, 64-byte first buffer), List and Map doubling from 8, Map's linear scan: the size classes and §3's numbers |
| wolf-lang's kw12 witness `crates/wolf_driver/tests/fixtures/freestanding_alloc/` and `tests/freestanding_alloc.rs` | `v0.2.24` | the project's own | read | the hook's shape in wolf, the archive's name beside the object (`K.rt-none.a`) and its place in the link |
| wolf-lang `crates/wolf_wir/src/midend/rangeopt.rs` (the `Lshr` arm) | `v0.2.24` | the project's own | read, to point wolf-lang#600 at its likely cause | the issue only |
| wolf-lang release v0.2.24 (404332628) and wolf-interp release v0.1.47 (404283632): asset digests from the release API, the x86-64 archive re-hashed on kasumi | — | — | read | `kernel/wolf.pin` (`501d6d3f…`) |
| Intel SDM vol. 3A ch. 4 (§4.5 the paging structures, §4.10.4 TLB invalidation) and AMD64 APM vol. 2 ch. 5 (§5.3, §5.4) | — | — | the author's own knowledge, as px03 cited them | the heap's slot, its pages mapped RW+NX, never unmapped (no INVLPG to get wrong) |

## px09 — user mode (2026-10-07)

**Linux: the syscall table and the uapi errno headers, nothing else.**
`arch/x86/entry/syscalls/syscall_64.tbl` (lines for `write` 1, `getpid`
39, `exit` 60, `exit_group` 231) and `include/uapi/asm-generic/errno-base.h`
/ `errno.h` (EBADF 9, EFAULT 14, ENOSYS 38), read in the sparse refs
clone; no other Linux file, and no glibc or other libc source.
Permissively licensed kernels: none consulted. The design (a frame
built by the SYSCALL entry in the shape an interrupt from ring 3 would
push, a return by SYSRETQ guarded against a non-canonical RIP, a
per-process PML4 sharing the kernel half's tables, a thread body that
enters ring 3 by IRETQ, faults in ring 3 ending the thread) is written
from the manuals' mechanics below.

| source | version | licence | how | used for |
|---|---|---|---|---|
| Intel SDM vol. 3A §5.8.8 (SYSCALL and SYSRET in 64-bit mode: STAR's selector fields, LSTAR, FMASK, no stack switch), §6.12.1 (a change to CPL 0 loads RSP from the TSS's RSP0), §6.14.2-§6.14.3 (the frame, IRET to an outer level pops SS:RSP), §4.6.1 (U/S at every level, SMEP, SMAP, EFLAGS.AC), §4.7 (page-fault error codes: P, W/R, U/S, I/D), §2.5 (CR4.SMEP bit 20, CR4.SMAP bit 21), §6.15 (interrupts 13, 14) | — | — | the author's own knowledge of the named sections; no text copied | `boot/user.S`, `boot/isr.S`'s `pax_sysret`, `kernel/user`, `kernel/paging`'s user half, `kernel/gdt`'s RSP0, `tests/mpx3-user`'s expected error codes |
| Intel SDM vol. 2 (SYSCALL, SYSRET and its #GP on a non-canonical RCX, IRET, STAC, CLAC, HLT at CPL > 0, MOV from a segment register, CPUID leaf 07H EBX bits 7 and 20, RDMSR, WRMSR) and vol. 4 (IA32_STAR C0000081H, IA32_LSTAR C0000082H, IA32_FMASK C0000084H, IA32_EFER.SCE) | — | — | the author's own knowledge | `boot/cpu.S`, `boot/user.S`, `boot/isr.S`, `user/programs.S`, `kernel/user` |
| AMD64 APM vol. 2 §6.1.1 (SYSCALL and SYSRET), §3.1.7 (EFER.SCE), §8.9.3 (the long-mode frame) | — | — | the author's own knowledge, as a cross-check of the Intel sections | the same |
| System V AMD64 psABI, A.2.1 (the Linux kernel calling convention: number in %rax; %rdi, %rsi, %rdx, %r10, %r8, %r9; %rcx and %r11 destroyed; result in %rax, -4095..-1 an error) | 1.0 | — | the author's own knowledge | `kernel/user`'s dispatch, `user/programs.S` |
| Linux `arch/x86/entry/syscalls/syscall_64.tbl`; `include/uapi/asm-generic/errno-base.h`, `errno.h` | the refs clone's sparse checkout (allowed paths only) | GPL-2.0 WITH Linux-syscall-note (uapi); the table's numbers are facts of the ABI | read: the four lines and three defines named above | `kernel/user`'s numbers and -errno values, `user/programs.S` |
| man-pages: `write(2)` (EFAULT: "buf is outside your accessible address space"), `_exit(2)`, `syscall(2)` (x86-64: `syscall`, %rax, the argument registers, %rcx and %r11 clobbered) | man-pages 6.x | the man-pages project's licences | the author's own knowledge | `write`'s -EFAULT instead of a kill (notes/px09-user-mode.md §2), the register convention |
| the wolf spec at v0.2.24: `[gram.inv.kw]` (`shared` and `spawn` are reserved: `paging.kernel_half`, `sched.start_thread`), `[abi.asm.roster]`, `[abi.link.extern]`; and the target's limit that `str` comparison needs the hosted runtime (a refusal met while building, so programs go by number) | wolf-lang `v0.2.24` (`294d626d`) | the project's own | read (and the compiler's refusals) | the names, the roster, the numbering |
| QEMU (`-cpu max`: TCG 8.2 in CI and 11.1.1 on kasumi, KVM on hasu passing the host's i7-12700KF features) | — | GPL-2.0 (a program we run) | black-box: SMEP and SMAP present on all three, as `kernel/user`'s CPUID read and the two witnesses show | `tests/mpx3-user` U1, U7, U8 |
