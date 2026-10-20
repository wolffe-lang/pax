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
| lobo | release v0.1.1 (archive `6e21e151…`), trunk `f79418d1181d…` for lobo's live site (the directory `tools/census/inside/stage.sh` fetches) | GPL-3.0 (the project's own) | read: the live site's four shell scripts and its configs; run: lobo | `workloads/lobo.sh` |
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

## px08 — the tour of the kernel (2026-10-06)

**Linux: nothing.** No Linux file of any kind was read, and no glibc,
musl or other libc or kernel source. Permissively licensed kernels:
none consulted. The tour adds no capability: its stages call the
subsystems px01-px07 wrote, whose sources are cited above.

| source | version | licence | how | used for |
|---|---|---|---|---|
| Limine's `CONFIG.md` (`timeout`, `quiet`, `serial`, `default_entry`, `interface_branding`, entry syntax) | v12.9.1 (the pinned release) | BSD-2-Clause | read, the bootloader's user documentation | `boot/limine-tour.conf`: a menu with two entries, mirrored to the serial console |
| Intel 8254 programmable interval timer data sheet: the counter-latch command (control word with RW bits 00), mode 2's count from N down to 1 and reload | — | — | the author's own knowledge | `kernel/pax_tour`'s early pause (`pit_count`, `pause_early`) |
| Intel SDM vol. 3A §4.5 (the four-level entry formats: P, R/W, PS, XD, the address bits) | — | — | the author's own knowledge, as kernel/paging cites | `kernel/pax_tour`'s read-only walk (`leaf`), the permissions stage 3 prints |

## px10 — the loader (2026-10-07)

**Linux: only allowed paths, from the refs clone's sparse checkout, never
widened.** No Linux source (`.c`, `.S`, non-uapi headers), no glibc,
musl or other libc or kernel source was read. glibc's behaviour was
observed black-box only: `strace` of a static program on kasumi and the
CI runner, and `objdump -d` of one instruction where PAX killed it (the
static start-up's `_dl_aux_init`, an AVX-512 store). Permissively
licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| Linux `include/uapi/linux/auxvec.h`, `arch/x86/include/uapi/asm/auxvec.h` | the refs clone's sparse checkout | GPL-2.0 WITH Linux-syscall-note | read: the AT_* numbers | `kernel/user`'s auxiliary vector; `user/elf/hello.S` |
| Linux `arch/x86/entry/syscalls/syscall_64.tbl` | the same | facts of the ABI | read: `exit_group` 231, `arch_prctl` 158 | `kernel/user`'s dispatch; the census |
| Linux `Documentation/driver-api/early-userspace/buffer-format.rst` (the initramfs buffer format: `newc`, ALGN(4), NUL padding between archives, `TRAILER!!!`, compression) | the same | GPL-2.0 (prose) | read, allowed by ruling #22 | `kernel/initramfs`, `tools/mkinitramfs` |
| System V gABI, "Object Files" and "Program Loading" (the ELF header, program headers, `PT_LOAD`, `PT_INTERP`, `PT_PHDR`, congruence modulo the page) and `elf(5)` | gABI 4.1 / man-pages 6.x | — | the author's own knowledge, checked against `readelf -lhW` of the built programs | `kernel/elf` |
| System V AMD64 psABI §3.4.1 (the initial process stack: argc, argv, envp, auxv, 16-byte alignment, %rdx), §5 (program loading) | 1.0 | — | the author's own knowledge | `kernel/user.exec`, `user/elf/hello.S` |
| man-pages `execve(2)`, `exit_group(2)`, `getauxval(3)` (AT_RANDOM, AT_EXECFN, AT_PHDR …), `cpio(5)` | 6.x | the man-pages project's licences | the author's own knowledge | the same |
| Intel SDM vol. 1 §10.5 and ch. 13 (FXSAVE's area: FCW at 0, MXCSR at 24; XSAVE's enumeration by CPUID leaf 0DH, enabling with CR4.OSXSAVE and XCR0, the area's header at 512, XSTATE_BV, the standard form, the init state), §8.1.5/§10.2.3 (FNINIT's and the reset values: FCW 0x037f, MXCSR 0x1f80); vol. 2 (CPUID, XGETBV, XSETBV, XSAVE64, XRSTOR64, FXSAVE64, FXRSTOR64, RDRAND, RDTSC); vol. 3A §2.5–§2.6 (CR0.MP/EM/TS, CR4.OSFXSR/OSXMMEXCPT/OSXSAVE, XCR0) | — | — | the author's own knowledge | `kernel/fpu`, `boot/fpu.S` |
| AMD64 APM vol. 2 §11.5 (saving media and x87 state) | — | — | the author's own knowledge, as a cross-check | the same |
| Limine `PROTOCOL.md` (the Module Feature, `struct limine_file`, the x86-64 machine state at entry: every CR0/CR4 bit not named cleared) and `CONFIG.md` (`module_path`) | limine-protocol `3a0526b7`; Limine v12.9.1 | BSD-2-Clause | read | `boot/start.S`'s module request, `kernel/boot_info`, `boot/limine-initramfs.conf`, `kernel/fpu` |
| black-box Linux: `user/elf/hello.S` run natively on kasumi (CachyOS, kernel 7.2.8) and on the CI runner (Ubuntu); `strace` 7.2 of the static wolf program | — | — | measured | `fcw 0x037f mxcsr 0x1f80` at execve; the census's Linux half |

## px12 — Linux programs, M-PX3 (2026-10-07)

**Linux: only allowed paths, from the refs clone's sparse checkout, never
widened.** No Linux source (`.c`, `.S`, non-uapi headers), no glibc,
musl, busybox or other libc, kernel or program source was read. glibc's,
boreutils' and busybox's behaviour was observed black-box only: `strace`
of the binaries under test in an Ubuntu 24.04 container on kasumi and on
the CI runner (`notes/px12/`). No disassembly was needed. Permissively
licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| Linux `arch/x86/entry/syscalls/syscall_64.tbl` | the refs clone's sparse checkout | facts of the ABI | read: the numbers of every call `kernel/user` dispatches | `kernel/user` |
| Linux `arch/x86/include/uapi/asm/stat.h` (`struct stat`, x86-64), `include/uapi/linux/stat.h` (`struct statx`, STATX_*), `include/uapi/asm-generic/fcntl.h` and `include/uapi/linux/fcntl.h` (O_*, AT_FDCWD, AT_SYMLINK_NOFOLLOW, AT_EMPTY_PATH), `include/uapi/asm-generic/mman-common.h` and `include/uapi/linux/mman.h` (PROT_*, MAP_*), `arch/x86/include/uapi/asm/prctl.h` (ARCH_SET_FS …), `include/uapi/linux/prctl.h` (PR_GET_NAME), `include/uapi/asm-generic/ioctls.h` (TCGETS, TIOCGWINSZ), `include/uapi/linux/time.h` (CLOCK_*), `include/uapi/linux/utsname.h` (`struct new_utsname`), `include/uapi/linux/random.h` (GRND_*), `include/uapi/asm-generic/errno-base.h`/`errno.h` | the same | GPL-2.0 WITH Linux-syscall-note | read: layouts and numbers | `kernel/files`, `kernel/vm`, `kernel/user` |
| man-pages `brk(2)`, `mmap(2)`, `munmap(2)`, `mprotect(2)`, `arch_prctl(2)`, `open(2)`, `read(2)`, `pread(2)`, `lseek(2)`, `close(2)`, `stat(2)`, `statx(2)`, `getdents64(2)` (`struct linux_dirent64`), `getcwd(2)`, `readlink(2)`, `ioctl(2)`, `getrandom(2)`, `clock_gettime(2)`, `clock_nanosleep(2)`, `uname(2)`, `prctl(2)`, `getrlimit(2)`, `set_tid_address(2)`, `path_resolution(7)`, `makedev(3)` | 6.x | the man-pages project's licences | the author's own knowledge | the same |
| Intel SDM vol. 4 (IA32_FS_BASE, MSR 0xC0000100), vol. 3A §2.5 (CR4.FSGSBASE left clear) | — | — | the author's own knowledge | `kernel/sched`'s FS base per thread |
| black-box Linux: the boreutils binaries and busybox-static's `ls` under `strace` (Ubuntu 24.04, glibc 2.39, strace 6.8, kasumi's kernel 7.2.8 in a podman container; the CI runner's kernel), chrooted in the initramfs's tree (`tools/linux-run`) | — | — | measured | the call set (`notes/px12/linux-strace-*.txt`), every answer `tests/mpx3-boreutils` compares, and one fact the psABI leaves open: glibc passes `AT_FDCWD` with the register's upper half zero (`0x00000000ffffff9c`), so `int` arguments are read as 32 bits |

## px13 — the console (2026-10-08)

**Linux: nothing from the refs clone this time.** The uapi termios header
(`include/uapi/asm-generic/termbits.h`) was the planned source for
`struct termios` and its bits; its read was refused by this lane's tool
permissions, so every number came black-box instead (below). No Linux
source (`.c`, `.S`, non-uapi headers), no glibc, musl or other libc, no
kernel's source and **no shell's source** (ruling #43) was read: pelt is
built from its own tree at its pin and observed only from outside
(`strace`, a pseudo-terminal). No disassembly. Permissively licensed
kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| PC16550D data sheet: IER bit 0 (received data available), FCR's receive trigger, LSR bit 0, RBR | — | — | the author's own knowledge | `kernel/serial`'s receiver |
| the IBM PC AT keyboard controller (8042): ports 0x60/0x64, status bits 0, 1 and 5, commands 0x20, 0x60 and 0xae, the configuration byte's bits 0, 1, 4 and 6; scancode set 1 for the US layout (make codes, bit 7 on release, the 0xe0 prefix) | — | — | the author's own knowledge | `kernel/console`'s keyboard |
| Intel 8259A data sheet (OCW1, OCW2's non-specific EOI) | — | — | the author's own knowledge | `kernel/timer`'s `unmask` and `eoi` |
| POSIX.1-2024 XBD chapter 11 (General Terminal Interface: canonical and non-canonical input, the special characters, ECHO, ECHOE, ECHOK, ICRNL, VMIN) | 2024 | The Open Group | the author's own knowledge | `kernel/console`'s line discipline |
| man-pages `termios(3)` (ECHOCTL, ECHOKE, IEXTEN, VWERASE), `ioctl_tty(2)` (TCGETS, TCSETS, TCSETSW, TCSETSF, TIOCGWINSZ, TIOCSWINSZ) | 6.x | the man-pages project's licences | the author's own knowledge | the same, and `kernel/console`'s ioctls |
| black-box Linux: `TCGETS` and `TIOCGWINSZ` on a fresh pseudo-terminal (`notes/px13/termios.c`: the 36 bytes TCGETS writes, the 8 TIOCGWINSZ writes), `strace -X verbose` and `strace -v` of that program and of `notes/px13/bits.c` (one flag bit set a call, so strace names each), in the `px13-ubuntu` container on kasumi (Ubuntu 24.04, strace 6.8) | — | — | measured | `struct termios`'s layout (four 32-bit flags, `c_line`, 19 control characters, 36 bytes), every flag bit's value, every `c_cc` index, the pseudo-terminal's defaults, the request numbers (`notes/px13/termios.txt`, `bits.strace`, `termios-v.strace`) |
| black-box Linux: pelt `dd22a86` (static, `tools/mkpelt`) under `strace -f` on a pseudo-terminal, a session typed (`notes/px13/ptysess.py`) | — | — | measured | what pelt asks of the terminal (nothing: no ioctl), how it reads (`/dev/stdin`, one byte a call) and writes its prompt (`write(2, "$ ", 2)`) (`notes/px13/pelt-session.strace`, `pelt-eof.strace`) |
| black-box Linux: every session `tests/mpx3-console` types, typed into the same binaries on a Linux pseudo-terminal with ISIG and IXON cleared (`tools/linux-tty`) | — | — | measured | the reference every PAX transcript is compared with, byte for byte: the echo of erase (`\b \b`, twice for a `^X`), kill and word-erase, `^C` as a byte, VEOF on a non-empty line |
| QEMU's monitor `sendkey` and the `file` character device's `input-path` | QEMU 8.2 (CI), 11.1 (kasumi, hasu) | — | the QEMU documentation | `tools/qemu-halt --type`, `tools/qemu-run --serial-input` |

## px14 — processes (2026-10-08)

**Linux: the uapi headers and the syscall table only**, from the refs
clone's sparse checkout (never widened): `include/uapi/linux/sched.h`
(CLONE_*, `struct clone_args` and its three published sizes),
`include/uapi/linux/wait.h` (WNOHANG, WEXITED, WNOWAIT, the `__W*` bits,
P_ALL/P_PID/P_PGID), `include/uapi/asm-generic/siginfo.h` (the SIGCHLD
member of `__sifields`: `_pid`, `_uid`, `_status`; SI_MAX_SIZE 128;
CLD_*), `arch/x86/include/uapi/asm/signal.h` (signal numbers,
SA_RESTORER), `include/uapi/asm-generic/signal-defs.h` (SA_*), and
`arch/x86/entry/syscalls/syscall_64.tbl` (rt_sigaction 13,
rt_sigprocmask 14, dup 32, dup2 33, getpid 39, clone 56, fork 57, vfork
58, execve 59, wait4 61, kill 62, getppid 110, _sysctl 156 =
sys_ni_syscall, tkill 200, tgkill 234, waitid 247, dup3 292, clone3
435). No Linux source (`.c`, `.S`, non-uapi headers), no glibc, musl or
other libc, no kernel's source and **no shell's source** (ruling #43):
pelt is built from its own tree at its pin and observed only from
outside. No disassembly. Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| the uapi headers and `syscall_64.tbl` above | the refs clone | GPL-2.0 WITH Linux-syscall-note | read | `kernel/process`'s numbers, flags and layouts |
| man-pages `clone(2)` (CLONE_VM, CLONE_VFORK, CLONE_CLEAR_SIGHAND, the raw x86-64 argument order, clone3), `vfork(2)`, `execve(2)` (what is kept and reset: descriptors without close-on-exec, the signal mask, handled signals to SIG_DFL, ignored ones kept; EACCES, ENOEXEC, E2BIG, a NULL argv), `wait4(2)`, `wait(2)`/`waitid(2)` (the status word, WNOHANG, ECHILD, the siginfo it fills), `getpid(2)` (init's parent 0), `gettid(2)`, `sigprocmask(2)`/`rt_sigprocmask`, `sigaction(2)` (the kernel's `struct sigaction` on x86-64), `kill(2)`, `dup(2)` (dup3's EINVAL), `signal(7)`, `credentials(7)`, `pid_namespaces(7)` | 6.x | the man-pages project's licences | the author's own knowledge | `kernel/process`, `kernel/sched`'s process table, `kernel/files`' dup and close-on-exec, `user/elf/procs.c` |
| black-box Linux: pelt `dd22a86` (static) under `strace -f -tt` on a pseudo-terminal, chrooted in the shell's tree, with and without PATH (`notes/px14/strace-spawn.sh`, in a privileged rootless `px13-ubuntu` container on kasumi: Ubuntu 24.04, glibc 2.39, strace 6.8, kernel 7.2.8) | — | — | measured | the spawn PAX answers (`notes/px14/pelt-spawn-path.strace`): `rt_sigprocmask(SIG_BLOCK, ~[])`, `clone3({CLONE_VM\|CLONE_VFORK\|CLONE_CLEAR_SIGHAND, SIGCHLD, stack, 0x9000})`, the child's mask query, `rt_sigaction(SIGPIPE, SIG_DFL)`, `dup2(5, 0)` (/dev/null as standard input), `execve`; the parent's `munmap`, `close(5)`, `wait4(pid, …, 0, NULL)`; and that with no PATH pelt searches the working directory (`statx("./cat")`) |
| black-box Linux: `user/elf/procs.c` as pid 1 of a fresh pid namespace (`unshare --pid`), chrooted in procs' tree | — | — | measured | every line `tests/mpx3-shell` compares procs' with: pids from 1, the status words, orphans to pid 1, waitid's siginfo, execve's errnos, the mask and actions across execve; and that the core-dump bit (0x80) depends on the host's core_pattern, not RLIMIT_CORE (set under a piped pattern), so procs masks it |

## px15 — boreutils' `ls`, and `quiet` on the kernel command line (2026-10-08)

No Linux source, no glibc, musl or other libc, no kernel's source and
no shell's source (rulings #22, #43); pelt and boreutils are built from
their own trees at their pins and observed only from outside. No
disassembly. Permissively licensed kernels: none consulted. Linux: no
header or table read (nothing here needed a number or a layout of
Linux's).

| source | version | licence | how | used for |
|---|---|---|---|---|
| The Limine Boot Protocol, `PROTOCOL.md` | limine-protocol `3a0526b700e356f0eac1b71a77697b3fd1c707a3` (fetched from its repository, as px00–px10) | 0BSD | read: Executable Command Line Feature (id words `0x4b161536e598651e, 0xb390ad4a2f1f303a`, the response `{revision, cmdline}`, a NUL-terminated ASCII string, the same memory as the executable file's `string`) | `boot/start.S`'s eighth request, `kernel/boot_info`'s `cmdline_has` |
| Limine `CONFIG.md` | Limine `v12.9.1` | BSD-2-Clause | read: the entry key `cmdline` (alias `kernel_cmdline`) | `boot/limine-initramfs-quiet.conf` |
| boreutils' `notes/bu18-ls.md` and `notes/bu18/pax-mpx3-with-ls.patch` | boreutils `50d8907` | GPL-3.0 | read | `ls`'s options as built (one name a line without a terminal; `-l` refused by name), the twelve `ls` lines on `user/mpx3-boreutils.run` |
| pelt's `README.md` | pelt `dd22a86` | GPL-3.0 | read for what it claims (functions, every expansion) | `user/console/shell-howl.keys` |
| black-box Linux: `user/console/shell-howl.keys` typed into the same binaries on a Linux pseudo-terminal (`tools/linux-tty --root --pid1`, a privileged rootless `px13-ubuntu` container on kasumi: Ubuntu 24.04, kernel 7.2.8; the CI runner) | — | — | measured | `user/console/shell-howl.expect`, the reference the howl session is held to; and, under `strace -f` of the harness, that boreutils opens `/dev/stdout`, which Linux resolves through `/proc/self/fd`, so the chroot keeps its `/proc` (px15's `4c39733`, reverted) |

## px17 — pipes, redirection and `cd` (2026-10-09)

**Linux: the uapi headers and the syscall table only**, from the refs
clone's sparse checkout (never widened): `include/uapi/asm-generic/errno.h`
(ENOTSOCK 88, EPROTONOSUPPORT 93, ESOCKTNOSUPPORT 94, EAFNOSUPPORT 97,
EISCONN 106), `include/uapi/asm-generic/fcntl.h` (F_DUPFD 0 to F_SETFL 4,
F_LINUX_SPECIFIC_BASE 1024, O_APPEND, O_NONBLOCK, O_DIRECT),
`include/uapi/linux/fcntl.h` (F_DUPFD_CLOEXEC = base + 6, F_GETPIPE_SZ =
base + 8), and `arch/x86/entry/syscalls/syscall_64.tbl` (pipe 22, sendto
44, recvfrom 45, socketpair 53, fcntl 72, getcwd 79, chdir 80, fchdir 81,
pipe2 293). No Linux source, no glibc, musl or other libc, no kernel's
source and no shell's source (rulings #22, #43): pelt and boreutils are
built from their own trees at their pins and observed only from outside.
No disassembly. Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| the uapi headers and `syscall_64.tbl` above | the refs clone | GPL-2.0 WITH Linux-syscall-note | read | `kernel/files`' and `kernel/user`'s numbers, flags and errnos |
| man-pages `pipe(2)`, `pipe(7)` (capacity 65536, PIPE_BUF 4096 and atomic writes, a read of an empty pipe with and without writers, EPIPE and SIGPIPE, O_NONBLOCK's EAGAIN), `dup(2)` and `open(2)` (open file descriptions: duplicates and a fork's child share the offset and status flags; close-on-exec is the descriptor's), `fcntl(2)`, `chdir(2)`, `getcwd(3)` (ERANGE), `socketpair(2)`, `unix(7)`, `recv(2)`, `send(2)` (MSG_DONTWAIT, MSG_NOSIGNAL, EISCONN), `clone(2)` (a clone without CLONE_VM copies the address space; CLONE_CHILD_SETTID, CLONE_PARENT_SETTID, CLONE_CHILD_CLEARTID), `fork(2)`, `kill(2)` (init receives only the signals it has a handler for), `signal(7)` (SIGPIPE's default action) | 6.x | the man-pages project's licences | the author's own knowledge | `kernel/files`, `kernel/process`'s fork and `sigpipe_kills`, `kernel/user`, `user/elf/procs.c`; MSG_DONTWAIT (0x40) and MSG_NOSIGNAL (0x4000) are not in the uapi headers and are the author's own knowledge, unexercised by any test here |
| black-box Linux: pelt `3e7516c` (static, built in `px13-ubuntu` by `tools/mkpelt`, `692007c3…`) under `strace -f -tt` on a pseudo-terminal, chrooted in the shell's tree with `/etc/words` (`notes/px17/strace-plumb.sh`; Ubuntu 24.04, glibc 2.39, strace 6.8, kernel 7.2.8 on kasumi) | — | — | measured | the plumbing PAX answers (`notes/px17/pelt-plumb.strace`): wolf 0.2.26's spawn forks (`clone(CLONE_CHILD_CLEARTID\|CLONE_CHILD_SETTID\|SIGCHLD)`), `socketpair(AF_UNIX, SOCK_SEQPACKET\|SOCK_CLOEXEC)` and the parent's `recvfrom` until `execve` closes the child's end, `fcntl(F_DUPFD_CLOEXEC, 3)` ×3 and `dup2` onto 0-2 in the child; `pipe2(O_CLOEXEC)`; `openat("/dev/null", O_WRONLY\|O_CREAT\|O_TRUNC\|O_CLOEXEC)`; `chdir` then `getcwd`; boreutils reopening `/dev/stdin` and `/dev/stdout` and moving fd 0's shared offset with `lseek`; a pipe end's `statx` S_IFIFO\|0600 |
| black-box Linux: `user/elf/procs.c` as pid 1 of a fresh pid namespace (`tools/linux-tty --root --pid1`) | — | — | measured | every new line procs' transcript holds PAX to: the fork, the pipe modes (0x1180), a waiting read and writer EOF, SIGPIPE's status 0xd, -32 for a child ignoring SIGPIPE and for pid 1 with SIGPIPE at SIG_DFL, the shared offset, getcwd/chdir/fchdir and their errnos, the socket mode (0xc1ff), F_GETFL of a pipe's ends (0 and 1) |

## px19 — the screen (2026-10-09)

No Linux source, no glibc, musl or other libc, no kernel's source
(ruling #22). No disassembly. Linux: no header or table read (`struct
winsize`'s four 16-bit words are px13's, measured). Permissively
licensed kernels and terminal emulators: none consulted; the terminal
is written from ECMA-48's description, not from any implementation.

| source | version | licence | how | used for |
|---|---|---|---|---|
| The Limine Boot Protocol, `PROTOCOL.md` | limine-protocol `3a0526b700e356f0eac1b71a77697b3fd1c707a3` (fetched from its repository, as px00–px15) | 0BSD | read: the Framebuffer Feature (id words `0x9d5827dcd881dd75, 0xa3148604f6fab11b`; the response and `struct limine_framebuffer`'s fields and offsets); "Caching", x86-64 (the framebuffer mapped WC through PAT[5]; Limine's PAT layout WB WT UC- UC WP WC); the HHDM's regions per base revision; the memory map's framebuffer type | `boot/start.S`'s ninth request, `kernel/boot_info`'s `fb_*`, `kernel/fb` |
| Intel 64 and IA-32 SDM vol. 3A §4.5 (the 4 KiB PTE's PWT, PCD and PAT bits), §11.12 (the PAT: IA32_PAT 0x277, its eight entries, the memory-type encodings, the entry a PTE selects, the power-on default); vol. 2 (CPUID leaf 01H EDX bit 16; RDMSR; MOVS, STOS and the REP prefix) | the current edition | Intel's terms | read | `kernel/fb`'s caching choice; `boot/screen.S` |
| ECMA-48, *Control Functions for Coded Character Sets*, 5th edition: the C0 set (BS, HT, LF, CR, ESC), CSI's syntax (parameter bytes 0x30–0x3f, intermediate bytes 0x20–0x2f, final bytes 0x40–0x7e) and SGR's parameters (0, 1, 7, 22, 30–37, 39, 40–47, 49; 90–97 as the common aixterm extension) | 1991 | freely available standard | read | `kernel/screen`'s parser and `tools/screen-ref`'s |
| the VT100 user guide's description of the last-column (deferred) wrap | DEC EK-VT100-UG | — | the author's own knowledge | `kernel/screen`'s pending wrap |
| the PC's 16-colour text-mode palette (00/aa/55/ff levels, brown for colour 3) as the VGA documentation gives it | — | facts | the author's own knowledge | `kernel/screen`'s and `tools/screen-ref`'s palette |
| **Spleen 8x16**, `spleen-8x16.bdf`, by Frederic Cambus | 2.2.0 (release tarball `ec42925c…`) | **BSD-2-Clause** (`font/LICENSE.spleen`), GPL-3.0 compatible | vendored unmodified (`font/`) | `boot/font.S` (generated by `tools/mkfont`), `tools/screen-ref`'s glyphs |
| the BDF format (Adobe's Glyph Bitmap Distribution Format 2.1: `ENCODING`, `BBX`, `BITMAP` rows in hex, most significant bit leftmost) | 2.1 | Adobe's specification | the author's own knowledge | `tools/mkfont`, `tools/screen-ref` |
| QEMU's documented behaviour: `-display` backends (`none`, `cocoa`, `curses`, `dbus` on nomad-1's 11.1.1), `-vga none`, the monitor's `screendump` (a PPM of the display surface), `sendkey` | 8.2.2 (CI), 11.1.1 (kasumi, nomad-1) | — | read (`-display help`, the monitor's `help`) and black-box runs | `tools/qemu-run --no-screen`, `tests/mpx3-screen` |

## px18 — the speaker, `/bin/play`, the tunes (2026-10-09)

No Linux source, no glibc, musl or other libc, no kernel's source
(ruling #22); the refs clone's sparse checkout was not widened. No
disassembly. Permissively licensed kernels: none consulted. QEMU's
source was not read either: its speaker was observed only from outside
(its options, `info qtree`, and what its `wav` backend wrote).

| source | version | licence | how | used for |
|---|---|---|---|---|
| uapi `include/uapi/linux/kd.h` | the refs clone | GPL-2.0 WITH Linux-syscall-note | read: two lines, `KIOCSOUND 0x4B2F`, `KDMKTONE 0x4B30` | `kernel/speaker`'s request numbers, `user/play`, `user/elf/hold.S` |
| man-pages `ioctl_kd(2)` (KIOCSOUND: the low 16 bits the period in clock cycles, 1193180 / frequency, 0 off; KDMKTONE: the low 16 bits the period, the high 16 the duration in ms, 0 off, returns at once) | man7.org, 2026-10-09 | the man-pages project's licences | read | `kernel/speaker`'s two requests |
| Intel 8254 programmable interval timer data sheet (the control word: channel, access low-then-high, mode 3 square wave, binary; the count's load) and the PC's wiring of channel 2 to the speaker through port 0x61 (bit 0 the gate, bit 1 the speaker data enable, bits 2-3 the parity and channel-check enables, bits 4-7 status), as the IBM PC/AT technical reference describes it | — | — | the author's own knowledge | `kernel/speaker`'s `on`/`off`, `boot/io.S`'s `pax_halt` |
| the x86-64 psABI (the argument registers, the `syscall` convention) and `syscall_64.tbl` (ioctl 16, write 1, exit_group 231) | the refs clone | — | read (the numbers), the author's own knowledge (the convention) | `user/play/kd.S`, `user/elf/hold.S` |
| black-box Linux: Ubuntu 24.04's `beep` 1.4.9 under `strace` (`notes/px18/beep-strace.sh`, a disposable `ubuntu:24.04` container on kasumi, kernel 7.2.8) | — | — | measured | `notes/px18/beep.strace`: the console driver opens its device `O_WRONLY` (`/dev/tty0`, then `/dev/vc/0`) and asks `ioctl(fd, KIOCSOUND, 0)`; the evdev driver asks `EVIOCGSND` — the interface PAX answers |
| QEMU's documented options (`-audiodev wav,id=…,path=…`, `-audiodev coreaudio,id=…`, the pc machines' `pcspk-audiodev`, `-audio`) and black-box runs of 11.1.1 on nomad-1 and kasumi | 11.1.1; Ubuntu's apt build (CI) | GPL-2.0 (a program we run) | the author's own knowledge, then measured: `info qtree` shows `isa-pcspk` at 0x61 bound by `pcspk-audiodev` and not by `-audio` (`notes/px18/qemu-pcspk-qtree.txt`); the `wav` backend writes samples only while the speaker sounds, and left the RIFF and `data` sizes 0 in every capture here, QEMU ended by the monitor's `quit` or by SIGTERM (measured on the captures `tests/mpx3-speaker` and the preflight write) | `tests/mpx3-speaker`, `tools/wav-notes`, `tools/qemu-halt --qemu` |
| Scott Joplin, "The Entertainer: A Rag Time Two Step" (St. Louis: John Stark & Son, 1902; plate 10-4); public domain (published 1902, before 1929; Joplin died in 1917); IMSLP's page "The Entertainer (Joplin, Scott)" for the first edition's facts | 1902 | public domain | the melody of the opening strain, written one voice by this lane from Joplin's 1902 melody as the author knows it; no later arrangement used (not Marvin Hamlisch's 1973 adaptation) | `user/tunes/entertainer` |
| none: "Paxito", an original tune by this lane (2026-10-09), written from style alone (a piano montuno's syncopated figure over i-iv-V7-i, a 2-3 clave feel, a brass-like hook of off-beat stabs); not a transcription, arrangement or paraphrase of any existing work, and nothing from the "Mambo" of *West Side Story* | 2026 | GPL-3.0 with the repository | written | `user/tunes/mambo` |
| none: the C major scale, C4 to C5, with the equal-tempered table (A4 = 440 Hz; each note 440 x 2^(n/12)) | — | — | the author's own knowledge | `user/tunes/scale`, `user/play`'s table, `tests/mpx3-speaker` K2 |

## px20 — virtio-net: PCI, the virtio transport, the frame interface, ARP (2026-10-10)

No Linux source, no BSD's, no network stack's (lwIP, picoTCP, smoltcp),
no firmware's (SeaBIOS, OVMF, iPXE) and no virtual machine monitor's
(QEMU) source; **no virtio or PCI driver from anywhere** (ruling #22);
the refs clone's sparse checkout was not widened; no web search for
code. No disassembly. Permissively licensed kernels: none consulted.
The device was learned from its specification and from outside: QEMU's
monitor, the kernel's own log, and the frames QEMU's `filter-dump`
wrote.

| source | version | licence | how | used for |
|---|---|---|---|---|
| OASIS *Virtual I/O Device (VIRTIO)* specification: §2.1 device status, §2.2 feature bits, §2.6 (1.1; §2.7 in 1.2) split virtqueues and the alignment table, §3.1.1 device initialization, §4.1.2 PCI device discovery (vendor 0x1af4; 0x1000 transitional network, 0x1040 + device type for 1.x), §4.1.4 the PCI capabilities (`virtio_pci_cap`, the common configuration, the notification capability and its multiplier, the ISR status), §4.1.5 PCI-specific initialization and notification, §5.1 the network device (queues, feature bits, `virtio_net_config`, `virtio_net_hdr`, the receive buffer's least size) | 1.1 (csprd01, fetched 2026-10-10 from docs.oasis-open.org to confirm the status bits, the ring structures, the descriptor flags, the alignment table and the initialization order) and 1.2 | OASIS's (a specification) | the author's own knowledge of the specification, confirmed in part by the fetch and in whole black-box (a wrong offset or order does not bring the device up) | `kernel/virtio`, `kernel/net` |
| PCI Local Bus specification: configuration mechanism #1 (ports 0xCF8 and 0xCFC), the type 0 and type 1 headers, the command register, base address registers, the capability list (status bit 4, the pointer at 0x34), Interrupt Line and Pin; the PCI-to-PCI bridge architecture specification (the secondary bus number) | 3.0; 1.2 | PCI-SIG's (specifications) | the author's own knowledge, each fact confirmed against QEMU's monitor (`info pci`, `notes/px20/infopci.*.txt`) and the census the kernel prints | `kernel/pci`, `boot/io.S` (`pax_outl`, `pax_inl`) |
| Intel I/O Controller Hub 9 (ICH9) family data sheet: the edge/level control registers ELCR1/ELCR2 (I/O ports 0x4d0, 0x4d1), PIRQ routing to the 8259's lines; Intel 8259A data sheet (OCW1 masks, the cascade on line 2) | — | Intel's (data sheets) | the author's own knowledge; ELCR read back on both firmwares (`0c00` under SeaBIOS, `0000` under OVMF: the driver sets its line's bit itself) | `kernel/timer` (`unmask_line`, `elcr`, `level`), `kernel/net`'s interrupt |
| RFC 826, *An Ethernet Address Resolution Protocol* (the packet, the reception algorithm) | 1982 | — | read as the author knows it; held by the capture, byte by byte | `kernel/arp`, `tools/pcap-net` |
| RFC 894, *A Standard for the Transmission of IP Datagrams over Ethernet Networks* (the frame: addresses, the type field, 0x0800 and 0x0806; the 46-byte minimum data field) | 1984 | — | the author's own knowledge | `kernel/net`, `kernel/netd` |
| IEEE 802 (the Local Experimental EtherTypes 0x88b5 and 0x88b6) | — | facts | the author's own knowledge | `kernel/kmain_net.lu`'s burst frames |
| RFC 791 and RFC 768 (the IPv4 and UDP headers' fixed fields: version/IHL, protocol 17, the addresses, the destination port) | — | — | the author's own knowledge | `tools/pcap-net` recognising the test's own datagrams; nothing in the kernel |
| the pcap capture file format (`pcap-savefile(5)`: the 24-byte header, magic 0xa1b2c3d4, link type 1, 16-byte record headers) | libpcap's documentation | BSD-3-Clause (documentation) | the author's own knowledge | `tools/pcap-net` |
| QEMU's documented options and behaviour: `-device virtio-net-pci` (`netdev`, `mac`, `disable-legacy`, `disable-modern`), `-netdev user` (`ipv6=off`, `hostfwd=udp:…`; the guest's address 10.0.2.15, the gateway 10.0.2.2), `-object filter-dump` (`netdev`, `file`), the monitor's `info pci` | 8.2.2 (CI), 11.1.0 (hasu), 11.1.1 (kasumi, nomad-1) | GPL-2.0 (a program we run) | the author's own knowledge of the documentation; run | `tests/mpx4-net`, `notes/px20/` |
| black-box, QEMU's user-mode network: the gateway's hardware address is 52:55:0a:00:02:02; a datagram for a guest whose address it has not learned makes it broadcast an ARP request (60 bytes on 11.1, 42 unpadded on 8.2.2) and deliver the datagram after the reply (unpadded too on 8.2.2: 45 bytes); its ARP replies are 64 bytes, zero-padded; with `ipv6=off` it sends nothing unasked | 8.2.2, 11.1.x | — | measured (the captures) | `tests/mpx4-net`, `tools/pcap-net` |
| black-box, the firmware: OVMF's own driver sends one or two IPv6 frames (an MLD report, a neighbour solicitation) from the device's address on some boots, before the kernel starts; SeaBIOS's option ROM sends nothing when the CD boots | kasumi's and CI's OVMF | — | measured (the captures) | `tools/pcap-net`'s "before the kernel" frames |

## px21 — IP and ICMP: IPv4, the ARP cache, echo (2026-10-10)

No Linux source, no BSD's, no network stack's (lwIP, picoTCP, smoltcp,
iPXE), no firmware's and no virtual machine monitor's (QEMU, or the
user-mode network library it links); none found by a search, and no
search for code was made; the refs clone's sparse checkout was not
widened. No disassembly. Permissively licensed kernels: none
consulted. What QEMU's user-mode network does was learned from outside:
frames written to a netdev and the frames that came back.

| source | version | licence | how | used for |
|---|---|---|---|---|
| RFC 791, *Internet Protocol*: the header's fields and their order, the flags and fragment offset, §3.1's option encoding (end of list, no operation, type-length-data; loose and strict source route are types 131 and 137) | 1981 | — | the author's own knowledge; held from outside by `tools/net-peer`'s 31 malformed datagrams and the capture | `kernel/ip`, `tools/paxnet.py` |
| RFC 792, *Internet Control Message Protocol*: echo and echo reply (types 8 and 0: identifier, sequence number, data), destination unreachable (type 3; code 2 protocol unreachable; the offending header and 64 bits of its data) | 1981 | — | the author's own knowledge | `kernel/icmp`, `tools/paxnet.py` |
| RFC 1071, *Computing the Internet Checksum*: the one's-complement sum of 16-bit words, the end-around carry, an odd byte padded on the right | 1988 | — | the author's own knowledge; `tools/pcap-net` recomputes every one in every capture | `kernel/ip`'s `sum`, `tools/paxnet.py`'s `csum` |
| RFC 1122, *Requirements for Internet Hosts — Communication Layers*: §2.3.2.1 (the ARP cache: a timeout on the order of a minute; no more than one request a second per destination), §2.3.2.2 (save at least the latest packet for an unresolved address), §3.2.1.2 (verify the header checksum), §3.2.1.3 (addresses that are never a valid source), §3.2.1.7 (never send a time to live of 0; never drop a datagram for a time to live under 2), §3.2.1.8 (options a host does not implement are ignored; a source route), §3.2.2 (when no ICMP error may be sent: a broadcast destination, a link-layer broadcast, a fragment, a source that is no single host), §3.2.2.1 (protocol unreachable), §3.2.2.6 (echo: the data returned entire; a request to a broadcast address MAY be discarded) | 1989 | — | the author's own knowledge | `kernel/arp`, `kernel/ip`, `kernel/icmp`: each choice is stated where it is made |
| RFC 1812, *Requirements for IP Version 4 Routers*: §4.3.2.8 (why ICMP errors are rate-limited), §5.3.7 (sources never valid): read for the reasons, PAX is a host | 1995 | — | the author's own knowledge | `kernel/icmp`'s limit, `kernel/ip`'s `source` rule |
| RFC 826 and RFC 894 (as px20) | — | — | as px20 | `kernel/arp`'s reception algorithm, kept; the frame |
| RFC 5227, *IPv4 Address Conflict Detection* (an address probe is an ARP request whose sender protocol address is 0.0.0.0): only the probe's shape, so that one is answered and teaches nothing | 2008 | — | the author's own knowledge | `kernel/arp`, `tools/net-peer` B1 |
| RFC 5737 (192.0.2.0/24 is TEST-NET-1, for documentation and never routed) | 2010 | facts | the author's own knowledge | the off-link host `tools/net-peer` plays |
| QEMU's documented options: `-netdev socket,udp=…,localaddr=…` (each frame one UDP datagram), `-netdev hubport`, `-machine none`, `-netdev user`'s `hostfwd` (TCP and UDP only) | 8.2.2 (CI), 11.1.0 (hasu), 11.1.1 (kasumi, nomad-1) | GPL-2.0 (a program we run) | the author's own knowledge of the documentation; `-netdev help` on each pool host; run | `tests/mpx4-net`'s `peer` way, `tools/net-peer`, `tools/gateway-probe` |
| black-box, QEMU's user-mode network and ICMP (`tools/gateway-probe`: frames written to a socket netdev on one hub with the user netdev, no guest): the gateway answers an echo request for 10.0.2.2 and for 10.0.2.3 itself (time to live 255, DF, an identification counted from 0, the data intact, 0 to 1472 data bytes); an echo request for an address outside is answered with that address as the source where the host admits unprivileged ICMP; one for an unused address on 10.0.2.0/24 is not answered | 11.1.1 (kasumi, nomad-1), 11.1.0 (hasu); CI's 8.2.2 by the same tool in the `mpx4-net` job | — | measured (`notes/px21-ip-and-icmp.md` §2, §4) | `kmain_net`'s echo soak; the choice of the `peer` mechanism |
| black-box, QEMU's virtio network device on a socket netdev: a frame of 26 bytes reaches the guest as 26 bytes (the kernel counts it `short`), and frames for a group address and for the device's own are delivered | 11.1.1 (kasumi) | — | measured (the `peer` way's counters against its capture) | `tools/net-peer` B6, `tools/pcap-net` |


## px22 — UDP and the socket system calls (2026-10-10)

No Linux source, no BSD's, no libc's (glibc's included: the witnesses
link it, nobody read it), no network stack's (lwIP, picoTCP, smoltcp,
iPXE), no firmware's and no virtual machine monitor's (QEMU, or the
user-mode network library it links); none found by a search, and no
search for code was made; the refs clone's sparse checkout was not
widened. No disassembly. Permissively licensed kernels: none
consulted. What Linux answers a socket call was learned from outside:
the witnesses run on it under strace.

| source | version | licence | how consulted | for what |
|---|---|---|---|---|
| RFC 768 (User Datagram Protocol: the header, the pseudo-header, a checksum of zero meaning none and a computed zero sent as all ones) | 1980 | IETF | the author's own knowledge of the RFC | `kernel/udp`; `tools/paxnet.py`'s `udp`, `udp_sum`, `judge_udp` |
| RFC 1122 §4.1 (what a host does with UDP: the checksum verified and a failure silent, port unreachable for no listener; §3.2.2 for when no error is sent) | 1989 | IETF | the author's own knowledge of the RFC | `udp.input`'s order and causes; the port unreachable through px21's limiter |
| RFC 792 (destination unreachable, code 3) | 1981 | IETF | as px21 | `icmp.unreachable`'s code |
| RFC 862 (the echo service on port 7) | 1983 | IETF | the author's own knowledge of the RFC | `user/net/udpecho`; `tools/pcap-net`'s rule for a datagram from port 7 |
| RFC 1035 §4.1 (the DNS message: the header, a question, a resource record, name compression) | 1987 | IETF | the author's own knowledge of the RFC | `user/net/resolve` (the witness only: the kernel knows no DNS); `tools/paxnet.py`'s `dns_question`, `dns_answer`; `tools/gateway-probe --dns` |
| RFC 6761 (`.test` is reserved and never delegated) and RFC 5737 (192.0.2.0/24) | 2013, 2010 | facts | the author's own knowledge | the name and the address `tools/net-peer`'s DNS server answers with |
| Linux man-pages: `socket(2)`, `bind(2)`, `connect(2)`, `sendto(2)`/`send(2)`, `recvfrom(2)`/`recv(2)`, `getsockname(2)`, `getpeername(2)`, `getsockopt(2)`, `listen(2)`, `accept(2)`, `udp(7)`, `ip(7)` (the default local port range, 32768-60999; `EADDRINUSE`, `EADDRNOTAVAIL`), `socket(7)` (`SO_RCVTIMEO`: a `timeval`, `EAGAIN` at its end; `SO_TYPE`, `SO_ERROR`; `SO_BROADCAST`), `netdevice(7)` (the SIOC* ioctls `tools/linux-net` makes) | 6.x | GPL-2.0+ / BSD / man-pages' own (prose and constants) | the author's own knowledge of the pages | `kernel/socket`, `kernel/udp`'s port rules; `tools/linux-net` |
| uapi headers in the refs clone: `linux/in.h` (`struct sockaddr_in`, `IPPROTO_UDP`), `linux/socket.h`, `linux/net.h` (the SOCK_* types), `asm-generic/socket.h` (`SOL_SOCKET`, `SO_TYPE` 3, `SO_ERROR` 4, `SO_RCVTIMEO_OLD` 20), `asm-generic/errno.h`, `asm-generic/fcntl.h` (SOCK_CLOEXEC and SOCK_NONBLOCK are O_CLOEXEC and O_NONBLOCK); and, for the reference side only, `linux/if_tun.h` (`TUNSETIFF`, `IFF_TAP`, `IFF_NO_PI`), `linux/sockios.h`, `linux/if.h`, `linux/route.h` (`struct rtentry`) | the refs clone's | GPL-2.0 WITH Linux-syscall-note | read (the constants) | `kernel/socket`'s numbers; `tools/linux-net`'s ioctls |
| `arch/x86/entry/syscalls/syscall_64.tbl` (41 socket … 55 getsockopt, 288 accept4) | the refs clone's | GPL-2.0 (facts of the ABI) | read | `kernel/user`'s dispatch |
| `Documentation/networking/tuntap.rst` (a tap device from `/dev/net/tun`) and `Documentation/networking/ip-sysctl.rst` (`ip_local_port_range`) | the refs clone's | GPL-2.0 (prose) | read | `tools/linux-net`; the ephemeral range |
| black-box, Linux 7.2.8 (kasumi, in the `px13-ubuntu` container: Ubuntu 24.04, glibc 2.39-0ubuntu8.9) and the CI runner's: the eight witnesses under `strace -f` — which system calls glibc's `send`, `recv`, `sendto`, `recvfrom`, `fork` make; every errno `user/net/sockerr` prints; what `getsockname` answers before and after a first send and after `connect`; the source address of a datagram over loopback; 92 of 200 datagrams of 1000 bytes kept by an unread socket; a datagram with bytes after its end, with no checksum, with no data, to the subnet's broadcast: each delivered | 2026-10-10 | — | measured (`notes/px22/`) | every refusal in `kernel/socket`; `kernel/udp`'s source-address and length rules; the witnesses' expected output is Linux's own |
| black-box, QEMU's user-mode network and UDP: a datagram the host sends to a `hostfwd=udp` port reaches the guest's port from 10.0.2.2; one the guest sends to 10.0.2.2 reaches the host's 127.0.0.1 at the same port; 10.0.2.3 answers ARP as 52:55:0a:00:02:03 and hands a DNS query to the host's resolver (`tools/gateway-probe --dns`) | 11.1.1 (kasumi, nomad-1), 11.1.0 (hasu), 8.2.2 (CI) | GPL-2.0 (a program we run) | QEMU's documentation of `hostfwd` and the user network's addresses; measured | `tests/mpx4-udp`'s `user` way, `tools/udp-host` |

## px21a — the pin at 0.2.27, the ambient slot, `/dev/tty0` and `/dev/console` (2026-10-11)

No kernel's source, no libc's and no network stack's was read (ruling
#22); the refs clone's sparse checkout was not widened. No disassembly
of anything but pax's own kernels. Permissively licensed kernels: none
consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| wolf's CHANGELOG at `v0.2.27` ("Read this before you bump the pin", the `ffi` capability, the ambient pair) and wolf-lang PR #646's text | wolf-lang `0ddda6b7` | wolf's own | read | the pin, the three `capabilities: [ffi]` lines, `kernel/heap`'s `ambient`/`set_ambient`, `kernel/sched`'s save and restore |
| black-box Linux 7.2.8 (kasumi): `stat` of `/dev/tty0` (character, 4:0), `/dev/console` (5:1), `/dev/ttyS0`, `/dev/null` | — | — | measured | `kernel/files`' device numbers for the two nodes (their mode there is udev's policy, 0660 and 0600; PAX gives both the console's 0620) |
| black-box Linux: Ubuntu 24.04's packaged `beep` 1.4.9-1.1ubuntu2 (`/usr/bin/beep`, `81b9a8d1…`) in the `px13-ubuntu` container: `readelf -h -l` (type DYN, a `PT_INTERP` naming `/lib64/ld-linux-x86-64.so.2`), and `strace` of `beep -f 440 -l 100` and `beep -e /dev/console …` (`notes/px21a/beep-default.strace`, `beep-console.strace`): it looks for `/dev/tty0`, then `/dev/vc/0`, then the evdev speaker's path | — | — | measured | why the packaged file cannot run on PAX; which device nodes a beep program opens |
| Ubuntu's `beep` source package, 1.4.9-1.1ubuntu2 (`beep_1.4.9.orig.tar.gz` `3b6b03c2…`, `beep_1.4.9-1.1ubuntu2.debian.tar.xz` `6fe840cb…`, from Launchpad's archive of the package) | 1.4.9-1.1ubuntu2 | GPL-2+ (its `COPYING` and `debian/copyright`); a user program, not a kernel, a libc or a network stack | built, not committed: `tools/mkbeep` runs its own GNUmakefile with `-static` added to the link. Read: `debian/rules` and the GNUmakefile's compiler variables, to build it as the package does. Its C was not read | `/bin/beep` in `tests/mpx3-speaker`'s image |
| black-box Linux 7.2.8 (kasumi), python3 on a pty: `ioctl(fd, 0x8000451a)` (the request beep's evdev driver asks, as `notes/px18/beep.strace` prints it raw) answers `ENOTTY` on a terminal | — | — | measured | `kernel/console`: a request of type 'E' is plain `-ENOTTY`, not a refusal PAX reports |
| QEMU's documentation of `-icount shift=N` (one instruction every 2^N ns of virtual time) and a black-box check (two RDTSC reads in a row are 9 ticks apart on the native tier, 7 on release; two runs give one number) | 11.1.1 | GPL-2.0 (a program we run) | read, then measured | the cost of the save and restore per switch (`notes/px21a-the-pin-0227.md`) |

## px23 — TCP (2026-10-11)

No Linux source, no BSD's, no libc's (glibc's included: the witnesses
link it, nobody read it), no network stack's (lwIP, picoTCP, smoltcp,
iPXE), no firmware's and no virtual machine monitor's (QEMU, or the
user-mode network library it links, whose TCP is the other end of one
of the test's three ways and was only ever spoken to); none found by a
search, and no search for code was made; the refs clone's sparse
checkout was not widened. No disassembly. Permissively licensed
kernels: none consulted. What Linux answers a stream socket's calls,
and what it puts on a wire under the faults the tests inject, was
learned from outside: the witnesses run on it under strace, a script's
own TCP at the other end of a tap device.

| source | version | licence | how consulted | for what |
|---|---|---|---|---|
| RFC 9293 (TCP: the header, the states and their transitions, §3.10.7's processing of a segment by state, the acceptability test, resets and RFC 5961's challenge ACKs as §3.10.7.4 takes them in, the MSS option and its default of 536, zero-window probing, the silly-window rules it restates) and RFC 793 where 9293 defers to it | 2022, 1981 | IETF | the author's own knowledge of the RFCs | `kernel/tcp`; `tools/paxtcp.py`; `tools/paxnet.py`'s `tcp`, `judge_tcp`; `tools/pcap-net`'s TCP rules |
| RFC 1122 §4.2 (a host's TCP: §4.2.2.13 a close with data unread resets and a SYN may reopen from TIME-WAIT, §4.2.2.20 out-of-order segments queued, §4.2.3.2 the delayed ACK is a SHOULD, §4.2.3.3–4 the two silly-window rules and Nagle's algorithm, §4.2.3.5 R1 and R2, §4.2.3.9 ICMP errors, §4.2.3.10 no SYN for a broadcast address) | 1989 | IETF | the author's own knowledge of the RFC | `kernel/tcp`'s choices, each named in its header |
| RFC 6298 (the retransmission timer: the first RTO, SRTT and RTTVAR, Karn's algorithm, the backoff, the 60 s ceiling; §2.4's 1 s floor, from which `RTO_MIN` departs) | 2011 | IETF | the author's own knowledge of the RFC | `tcp.rtt_sample`, `tcp.timeout` |
| RFC 5681 (slow start, congestion avoidance, the initial window, fast retransmit and fast recovery, the window after a timeout, what a duplicate ACK is) | 2009 | IETF | the author's own knowledge of the RFC | `tcp.ack_in`, `tcp.fast_retransmit`, `tcp.establish` |
| RFC 6528 (initial sequence numbers: a clock plus a keyed function of the four addresses and ports) | 2012 | IETF | the author's own knowledge of the RFC | `tcp.isn` |
| RFC 1337 (a reset in TIME-WAIT is better ignored), RFC 5461 §4 (stacks that end a connection not yet synchronized on a soft ICMP error), RFC 7323 and RFC 2018 (only the kinds of the options skipped: 3, 8; 4, 5), RFC 7413 (kind 34) | 1992–2014 | IETF | the author's own knowledge | `tcp.time_wait_in`, `tcp.unreached`, `tcp.options`' counters |
| J.-P. Aumasson and D. J. Bernstein, "SipHash: a fast short-input PRF" (2012), and its 32-bit sibling HalfSipHash as its authors describe it | the paper | public domain (the algorithm) | the author's own knowledge; **not checked against a test vector** | the shape of `tcp.keyed`'s rounds; nothing depends on its being that function exactly (RFC 6528 asks that F be hard to predict without the key) |
| ISO 3309's CRC-32 (the reflected polynomial 0xedb88320) | a fact | — | the author's own knowledge | `user/net/say.h`'s `crc32_of`; the tools use Python's `zlib.crc32`, which agrees with it on every transfer |
| Linux man-pages: `tcp(7)` (`TCP_NODELAY`, `TCP_SYNCNT`, `TCP_USER_TIMEOUT`; the defaults `tcp_syn_retries` 6, `tcp_synack_retries` 5, `tcp_retries2` 15, `tcp_fin_timeout` 60), `ip(7)`, `socket(7)` (`SO_REUSEADDR`, `SO_ERROR`), `listen(2)` (the backlog), `accept(2)` (`accept4`'s flags), `connect(2)`, `shutdown(2)`, `send(2)`, `recv(2)`, `bind(2)`, `getsockopt(2)`, `ioctl(2)` | man-pages 6.x | various free licences | the author's own knowledge of the pages | `kernel/socket`'s stream calls; `kernel/tcp`'s give-up bounds |
| uapi headers in the refs clone: `linux/tcp.h` (`TCP_NODELAY` 1, `TCP_SYNCNT` 7, `TCP_USER_TIMEOUT` 18), `asm-generic/socket.h` (`SO_REUSEADDR` 2), `asm-generic/ioctls.h` (`FIONBIO` 0x5421), `asm-generic/errno.h` (`ECONNRESET` 104, `ETIMEDOUT` 110, `ECONNREFUSED` 111, `EHOSTUNREACH` 113, `EINPROGRESS` 115), `linux/in.h` | the refs clone's | GPL-2.0 WITH Linux-syscall-note | read | the numbers in `kernel/socket`, `kernel/tcp`, `kernel/files` |
| `arch/x86/entry/syscalls/syscall_64.tbl` (43 accept, 48 shutdown, 50 listen, 288 accept4) | the refs clone's | GPL-2.0 (facts of the ABI) | read | `kernel/user`'s dispatch |
| `Documentation/networking/ip-sysctl.rst` (`tcp_max_tw_buckets`: past its bound Linux destroys a time-wait socket at once) | the refs clone's | GPL-2.0 (prose) | read | the argument for a bounded time-wait table that gives up an entry when full |
| wolf's `spec/11-os.md` at v0.2.26 (the `net_*` builtins) and `corpus/net/echo_roundtrip.lu` (their use) | wolf-lang `89dc1394` | wolf's | read | `user/net/tcpwolf.lu`, `tcpwolfd.lu` |
| black-box, Linux 7.2.8 (kasumi, in the `px13-ubuntu` container) and the CI runner's: the ten witnesses under `strace -f` — which system calls they and wolf's runtime make (`ioctl(FIONBIO)`, `accept4` with `SOCK_CLOEXEC\|SOCK_NONBLOCK`; `epoll`, `eventfd2`, `clone3` and `futex` once a call finds nothing ready); every errno `user/net/tcperr` prints; that a reset after the peer's FIN leaves `EPIPE` and one before it `ECONNRESET`; that a `shutdown` refused with `ENOTCONN` still marks the socket; that a backlog of 2 lets 3 connections in and drops the next SYN; that `bind` to a port in time-wait is `EADDRINUSE` unless `SO_REUSEADDR`; that an ICMP host unreachable for a SYN ends the connect at once with `EHOSTUNREACH` and a port unreachable with `ECONNREFUSED`; that `TCP_USER_TIMEOUT` ends a read with `ETIMEDOUT`; and, on a tap device with `tools/net-peer --tcp` at its other end, that every transfer stays exact under the same faults | 2026-10-11 | — | run and observed (`notes/px23/`) | `kernel/socket`, `kernel/tcp`; `tests/mpx4-tcp`'s reference side |
| black-box, QEMU's user-mode network and TCP (QEMU 11.1.1, 11.1.0, 8.2.2): a connection the host makes to a `hostfwd=tcp` port reaches the guest's port from 10.0.2.2 once the guest's listener answers; one the guest makes to 10.0.2.2 reaches the host's 127.0.0.1 at the same port, and is reset when nothing listens there; a half-closed connection stays open the other way | documented (`hostfwd`), then run | — | observed with `tools/tcp-host` | `tests/mpx4-tcp`'s `user` way |

## px26: threads, futexes and signals

No kernel's, libc's or threading library's source was read or searched
for. pelt and boreutils are used as built from their own repositories
at their pins; their source was not read for how they work.
Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `clone(2)` (clone3's `struct clone_args`, the flag rules), `set_tid_address(2)`, `set_robust_list(2)`, `futex(2)`, `futex(7)`, `signal(7)`, `sigaction(2)`, `sigprocmask(2)`, `sigpending(2)`, `sigreturn(2)`, `sigaltstack(2)`, `kill(2)`, `tgkill(2)`, `execve(2)`, `madvise(2)`, `prctl(2)`, `termios(3)`, `sendfile(2)`, `splice(2)`, `copy_file_range(2)`, `readlink(2)`, `proc(5)` | man-pages 6.x | their own (mostly the Linux man-pages copyleft, some BSD) | read | `kernel/sched`, `kernel/process`, `kernel/futex`, `kernel/signal`, `kernel/vm`, `kernel/files`, `kernel/console` |
| uapi headers in the sparse checkout: `linux/sched.h` (CLONE_*), `linux/futex.h` (the operations, FUTEX_PRIVATE_FLAG, FUTEX_CLOCK_REALTIME), `arch/x86/include/uapi/asm/signal.h` (numbers, SA_*), `asm/sigcontext.h` (`struct sigcontext_64`, the extended state's software bytes, the two magics), `asm/ucontext.h` and `asm-generic/ucontext.h`, `asm-generic/siginfo.h` (the layout, SI_*, CLD_*, SEGV_*, ILL_*, FPE_*), `asm-generic/mman-common.h` (MADV_*) | the checkout's | GPL-2.0 WITH Linux-syscall-note | read | the numbers and layouts above |
| the x86-64 psABI (the red zone, the stack's alignment at a function's entry) and the Intel SDM vol. 1 §13 (XSAVE's area and header), vol. 2 (IRET, SYSRET) | — | their own | read | the signal frame and `rt_sigreturn` |
| Motorola's MC146818 data sheet (the registers, UIP, the data-mode and 24/12 bits) and the IBM PC/AT technical reference (ports 0x70 and 0x71); QEMU's documentation of `-rtc` | — | their own | read | `kernel/rtc` |
| RFC 8536 (the TZif format) | — | IETF | read | `tools/mkzone` (the UTC zone file, written from the RFC; the same bytes as tzdata's, measured) |
| black-box Linux 7.2.8 (kasumi, the `px13-ubuntu` container, glibc 2.39, strace 6.8): `strace -f` of pax's own builds of pelt `b32bebc` and boreutils `870815c` on a pseudo-terminal (`notes/px26/*.strace`, the keys and the script beside them) | — | — | measured | which calls the two make and with what arguments; which thread takes the terminal's SIGINT; what `ls -l` reads |
| black-box Linux: `user/elf/threads.c`, a static glibc program written for this lane, run on Linux 7.2.8 and on the CI runner's kernel | — | pax's own | measured | every answer `kernel/futex` and `kernel/signal` give that the man pages leave open: a private wait is not reached by a wake without the flag; pending signals run highest-numbered first; the handler starts with a fresh x87/SSE state; `uc_flags` 7 and a zero stack triple; the ucontext 8 bytes and the siginfo 312 above the handler's RSP; which calls run again under SA_RESTART; the exit status of a process whose leader exits first; a fault with its signal blocked or ignored still ends the process |

## px27: the writable tree

No kernel's, libc's or file system's source was read or searched for
(not Linux's, a BSD's, any tmpfs or ramfs). boreutils, pelt and lobo
are used as built from their own repositories at their pins; their
source was not read for how they work (bu21's `tools/roottest` was
read as a tool, for how a root guard is tested in a container). No GNU,
busybox, uutils or toybox source. Permissively licensed kernels: none
consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `open(2)`/`openat(2)` (the flags, O_CREAT's mode and umask, the errors), `write(2)`, `pwrite(2)` (and its BUGS: O_APPEND), `lseek(2)`, `truncate(2)`, `mkdir(2)`, `rmdir(2)`, `unlink(2)`, `rename(2)`, `link(2)`, `symlink(2)`, `mknod(2)` (EPERM for a file system that makes none), `chmod(2)`, `chown(2)`, `utimensat(2)`, `stat(2)`, `statx(2)`, `getdents(2)`, `fsync(2)`, `umask(2)`, `access(2)`, `copy_file_range(2)`, `sendfile(2)`, `splice(2)`, `getcwd(3)`, `path_resolution(7)`, `inode(7)`, `tmpfs(5)` | man-pages 6.x | their own | read | every call's arguments and errors; what is refused and with which errno |
| POSIX.1-2024 (`rename`, `unlink`, `rmdir`, `readdir`: what a reading of a directory may return while it changes) | 2024 | IEEE/The Open Group | read | `kernel/tree`'s `rename` and `entry_at` |
| uapi headers in the sparse checkout: `asm-generic/fcntl.h` and `linux/fcntl.h` (O_*, AT_REMOVEDIR, AT_EACCESS, RENAME_*), `linux/stat.h` (`struct statx`, STATX_BTIME), `arch/x86/include/uapi/asm/stat.h`, `asm-generic/errno-base.h`, `asm-generic/errno.h`, `arch/x86/entry/syscalls/syscall_64.tbl` (the numbers) | the sparse checkout's | GPL-2.0 WITH Linux-syscall-note | read | the constants and the layouts |
| the Intel SDM vol. 2 (MOVS, STOS, REP) and the x86-64 psABI | — | their own | read | `boot/tree.S` |
| black-box Linux 7.2.8 (kasumi, a throwaway `px13-ubuntu` container, strace 6.8, every program on a tmpfs): `strace -f` of pax's own builds of boreutils `abc59f5` (`mkdir`, `rmdir`, `rm`, `mv`, `cp`, `ls`, `stat`, `cat`) and pelt `b32bebc` (`>`, `>>`, `<>`, a here-document), and of lobo `b256d2e` serving, reloading, reopening its logs and stopping (`notes/px27/straces/`) | — | — | measured | which calls and flags a program in an image, and lobo, make on files: the list this lane implements, and what it leaves refused |
| black-box Linux: `user/elf/tree.c`, a static glibc program written for this lane, pid 1 with its root a tmpfs in a throwaway container (`tools/linux-tree`), on Linux 7.2.8 and on the CI runner's kernel | — | pax's own | measured | every answer the man pages leave open or this lane had predicted: a directory's size (40 and 20 an entry) and link count; `O_RDONLY\|O_TRUNC` truncates; `pwrite` on an O_APPEND descriptor appends; a hole's blocks; what `rmdir` and `rename` answer for `.`, `..`, `/` and a mount point; a removed working directory (`getcwd` -ENOENT, 0 links, a reading of it -ENOENT, nothing made in it); `copy_file_range`, `sendfile` and `splice` between files and onto O_APPEND; which times a write, a read, a rename, a truncation and an unlink move |
| black-box Linux: `user/console/shell-tree.keys` typed into the same binaries (`tools/linux-tree`: `tools/linux-tty` inside the container) | — | — | measured | the session's reference transcript, taken afresh at every run |

## px24: readiness (poll, epoll, eventfd and the rest lobo's runtime asks for)

No kernel's, libc's, event library's or network stack's source was read
or searched for, and wolf's runtime was not read for behaviour PAX
must match: lobo and the wolf witness are used as built and observed
under `strace`. Permissively licensed kernels: none consulted. No
`ptrace` launcher and no vDSO trick: which clocks a program reads was
not taken from Linux at all.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `poll(2)`, `epoll(7)`, `epoll_create1(2)`, `epoll_ctl(2)`, `epoll_wait(2)`, `eventfd(2)`, `fcntl(2)`, `readv(2)`, `send(2)`, `recv(2)`, `connect(2)`, `socket(7)`, `tcp(7)`, `pipe(7)`, `getrandom(2)`, `prctl(2)`, `sigaltstack(2)`, `sched_setaffinity(2)`, `signal(7)` | man-pages 6.x | their own (verbatim-copying and GPL, prose) | read | `kernel/ready`, `kernel/event`, `writev`, `sigaltstack`, `sched_getaffinity`, `getrandom`'s flags |
| uapi headers in the sparse checkout: `asm-generic/poll.h` (POLL*), `linux/eventpoll.h` (EPOLL*, `struct epoll_event` packed on x86-64), `linux/eventfd.h`, `linux/uio.h` (UIO_MAXIOV), `linux/random.h` (GRND_*), `asm-generic/signal-defs.h` and `asm/signal.h` (SS_*, MINSIGSTKSZ, SA_ONSTACK), `asm-generic/socket.h` (SO_ACCEPTCONN) | the refs clone's | GPL-2.0 WITH Linux-syscall-note | read | the numbers |
| wolf's `spec/11-os.md` at v0.2.27 (`net_listen`, `net_accept`, `net_connect`, `net_read`, `net_write`, `net_close`, `net_port`; `scope`, `spawn`, channels) | wolf-lang `0ddda6b7` | wolf's | read | `user/net/waitwolf.lu` (what the builtins promise a program, not how the runtime keeps the promise) |
| black-box Linux 7.2.8 (kasumi, the `px13-ubuntu` container, glibc 2.39, strace 6.8): lobo `b256d2e` built static by wolf 0.2.27 and `user/net/waitwolf.lu`, each under `strace -f` with a request set (`notes/px24/linux/`) | — | — | measured | which calls wolf's runtime and lobo make once a call must wait, with every flag: `epoll` level-triggered with EPOLLONESHOT and EPOLLRDHUP, an `eventfd`, `poll(POLLIN)`, `writev`, `sigaltstack`, `sched_getaffinity`; and what they never ask (`EPOLLET`, `epoll_pwait`, `sendmsg`, `sendfile`) |
| black-box Linux 7.2.8 and the CI runner's: the five probes (`user/net/nbprobe.c`, `pollprobe.c`, `epollprobe.c`, `evprobe.c`, `restprobe.c`), written for this lane | — | pax's own | measured | every answer the man pages leave open: what `poll` says of each kind of descriptor in each state (a stream socket never connected is POLLOUT\|POLLHUP; SHUT_WR leaves POLLOUT set; a reset is all five bits and POLLERR goes when the error is taken; a full pipe is writable again after 4096 bytes are read, not 4095); that a reset keeps the bytes already received; epoll's errnos; that EPOLL_CTL_MOD arms a registration again; that `lseek` on an epoll descriptor and on an eventfd answers 0; an anonymous inode's mode 0600; that `writev` to a pipe is one write for PIPE_BUF's rule and reads every part before it writes; `sigaltstack`'s answers and the context's stack triple |
| black-box, QEMU's user-mode network (11.1.1): of 64 connections begun at once to a `hostfwd=tcp` port, some never reach the guest (one capture: 52 SYNs of 65, each answered) | — | — | measured | `tools/ready-host` makes its connections one after another |

## px30: the sound card

No kernel's, libc's, sound server's, sound library's or driver's source
was read or searched for (not Linux's sound core, its OSS emulation or
virtio-snd driver, ALSA's library, OSS, SDL, PulseAudio, PipeWire), and
no QEMU device or audio source. Linux and QEMU were run, never read.

| source | version | licence | how | used for |
|---|---|---|---|---|
| OASIS Virtual I/O Device (VIRTIO) specification §5.14 (the sound device: configuration, queues, request codes and structures, the PCM format and rate enumerations, the stream's states) and §4.1 (the PCI transport) | 1.2, 1.3 | OASIS (a specification) | the author's own knowledge of it, then measured against QEMU's answers (the PCM_INFO response, the device's features, each request's status) | `kernel/sound`, `kernel/virtio` |
| uapi `linux/soundcard.h` (request numbers, AFMT_*, DSP_CAP_*, `audio_buf_info`, `count_info`, SOUND_VERSION) and `sound/asound.h` (only to size ALSA's PCM interface for the prediction) | the sparse checkout | GPL-2.0 WITH Linux-syscall-note | read | `kernel/sound`, `user/sound`, `user/play/kd.S` |
| the OSS programmer's guide (the order SETFMT, CHANNELS, SPEED; that a request answers what was set) and man-pages `open(2)`, `ioctl(2)`, `close(2)`, `poll(2)` | — | their own | read | `kernel/sound`'s answers |
| black-box Linux 7.2.8 (kasumi's own kernel image and modules, run under QEMU 11.1.1 by `tools/linux-sound` with each candidate device; busybox-static and strace 6.8 from `px13-ubuntu`) | 7.2.8-1-cachyos | GPL-2.0 (programs we run) | measured | the device survey, the witnesses' straces, what Linux answers at the edges (`notes/px30/linux-*.serial.log`), its close's drain, its version answer 0x030810 |
| QEMU's documentation (`-audiodev` and its `out.frequency`, `wav`, `coreaudio`, `none`; `-device virtio-sound-pci`) and black-box runs of 11.1.1 (kasumi, nomad-1), 11.1.0 (hasu) and the CI runner's | — | GPL-2.0 (a program we run) | measured: `info pci`/`info qtree` of the device; the `wav` backend writes only while the stream has data (an underrun's gap is not in the file, Linux's alike) | `tests/mpx3-sound`, `tools/wav-notes` |

## px32: the orchestra (the part format, synthesised timbres)

No synthesiser's, tracker's, sound library's or music engine's source
was read or searched for (no SoundFont player, MIDI synthesiser,
tracker or audio DSP library). No recorded sample, sound font or sample
set is used: every timbre is computed in wolf from arithmetic at
start-up.

| source | version | licence | how | used for |
|---|---|---|---|---|
| the textbook methods: additive synthesis (a periodic wave as a sum of sine partials), wavetable lookup by a phase accumulator, ADSR envelopes, the linear-congruential generator, one-pole low-pass filters, vowel formants as a fixed spectral envelope, constant-power panning, a look-ahead peak limiter, the Goertzel algorithm (one DFT bin) | — | general knowledge | the author's own knowledge, no text copied | `user/play/orch.lu`, `tools/orch-check` |
| the published partial series of church and tubular bells (hum 0.5, prime 1, tierce 1.2, quint 1.5, nominal 2) and of a kettledrum's membrane modes (about 1 : 1.50 : 1.74 : 2.00 : 2.24 : 2.49); the vowel "ah"'s first formants (about 750, 1150, 2800 Hz) | — | general knowledge (acoustics) | the author's own knowledge | `orch.lu`'s bells, timpani and choir |
| QEMU 11.1.1's `wav` backend (kasumi, nomad-1) and the CI runner's | — | GPL-2.0 (a program we run) | measured: its data size is left 0 when QEMU ends (as px30's `wav-notes` found) | `tools/orch-check` |

## px36: the file changes (modes, times and links; the pin to 0.2.28)

No kernel's, libc's or file system's source was read or searched for
(not Linux's, a BSD's, any tmpfs). boreutils and pelt are used as built
from their own repositories at their pins; their source was not read.
No GNU, busybox, uutils or toybox source. Permissively licensed
kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `chmod(2)`/`fchmodat(2)`, `chown(2)` (root since Linux 2.2.13 "treated like other users": the set-ID bits), `utimensat(2)` (UTIME_NOW, UTIME_OMIT, ctime "even if the other timestamps don't change", AT_SYMLINK_NOFOLLOW, "the greatest value supported … not greater than the specified time"), `link(2)`/`linkat(2)` (Linux does not dereference `oldpath`; AT_SYMLINK_FOLLOW, AT_EMPTY_PATH), `symlink(2)`, `readlink(2)`, `open(2)` (O_NOFOLLOW), `path_resolution(7)` (a link before the last component, the final link, trailing slashes, 40 links), `symlink(7)` (a link's permissions are always 0777), `capabilities(7)` (CAP_FSETID) | man-pages 6.x on kasumi | their own | read | every new call's arguments and errors; which calls follow a last link |
| POSIX.1-2024 `chown` (EINVAL for an owner or group ID the implementation does not support) | 2024 | IEEE/The Open Group | read | the refusal of an owner that is not root |
| uapi headers in the sparse checkout: `linux/fcntl.h` (AT_SYMLINK_FOLLOW, AT_SYMLINK_NOFOLLOW, AT_EMPTY_PATH), `linux/stat.h` (UTIME_NOW, UTIME_OMIT, S_IFLNK), `arch/x86/entry/syscalls/syscall_64.tbl` (the numbers) | the sparse checkout's | GPL-2.0 WITH Linux-syscall-note | read | the constants |
| wolf's CHANGELOG at `v0.2.28` ("Read this before you bump the pin") | wolf-lang `f71ece8e` | wolf's own | read | the pin |
| black-box Linux 7.2.8 (kasumi, a throwaway `px13-ubuntu` container as root, strace 6.8, every program on a tmpfs): `strace -f` of pax's own builds of boreutils `2ab3651` (`chmod`, `touch`, `ln`, `mkdir -m`, `cp -p`, and `ls -l`, `stat`, `readlink`, `cat`, `rm`, `mv` meeting links; `notes/px36/straces/`) | — | — | measured | the calls and flags bu22's binaries make: `chmod`, `utimensat` (UTIME_NOW, UTIME_OMIT, AT_SYMLINK_NOFOLLOW), `linkat`, `symlink`, `readlink`, `rename` over a temporary name |
| black-box Linux: `user/elf/tree.c`'s px36 sections, pid 1 with its root a tmpfs in a throwaway container (`tools/linux-tree`) | — | pax's own | measured | what the man pages leave open: a link's `st_blocks` (none below a 128-byte target, eight from it), a link's atime moved by a walk through it and by `readlink`, root's `chown` clearing set-ID bits whatever ids were asked, -1 included, a new name with a trailing slash -ENOENT, O_NOFOLLOW with O_DIRECTORY -ENOTDIR, `fchmodat2`'s AT_SYMLINK_NOFOLLOW on a link -EOPNOTSUPP, both UTIME_OMIT leaving ctime, times before 1970 and past 2262 |
| black-box Linux: `user/console/shell-changes.keys` typed into the same binaries (`tools/linux-tree`) | — | — | measured | the session's reference transcript, taken afresh at every run |

## px39: the credentials (a process's ids and groups)

No kernel's, libc's or file system's source was read or searched for,
nor that of `su`, `login`, shadow-utils or util-linux. The rules are
px38's model (`notes/px38/check-cred.py`, written from the man pages
and held to px38's recorded rows) and black-box runs this lane took.
Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `credentials(7)`, `setuid(2)`, `setreuid(2)`, `setresuid(2)`, `setfsuid(2)`, `getresuid(2)`, `getgroups(2)` (NGROUPS_MAX "32 before Linux 2.6.4"), `execve(2)` (the saved set-user-ID copied from the effective), `capabilities(7)` ("Effect of user ID changes on capabilities"), `prctl(2)` and `PR_SET_DUMPABLE(2const)` (when the attribute is reset), `PR_GET_NO_NEW_PRIVS(2const)`, `getauxval(3)` (AT_SECURE), `proc_pid_status(5)` (`Uid`, `Gid`, `Groups`, the `Cap*` lines), `user_namespaces(7)` (`/proc/<pid>/setgroups`), `nptl(7)` (ids are per thread in the kernel) | man-pages 6.x | various free licences | read | the rules of `kernel/cred`; what to measure |
| uapi headers in the sparse checkout: `arch/x86/entry/syscalls/syscall_64.tbl` (105, 106, 113 to 120, 122, 123), `linux/prctl.h` (PR_GET_DUMPABLE 3, PR_GET_KEEPCAPS 7, PR_GET_SECUREBITS 27, PR_GET_NO_NEW_PRIVS 39), `linux/auxvec.h` (AT_UID to AT_SECURE) | the sparse checkout's | GPL-2.0 WITH Linux-syscall-note | read | the numbers |
| px38's recorded answers: `notes/px38/linux/vm.txt` (the `cred` section, 2,684 lines, real root of Linux 7.2.8 under QEMU) and `notes/px38/check-cred.py` | pax `fe7c05b` | pax's own | read; the recording is `tests/mpx5-users.d/linux/cred.txt` to the byte | the reference `kernel/cred` is held to |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image booted under QEMU 11.1.1 with `notes/px39/vminit.c` as pid 1: root of the initial user namespace, every capability; `notes/px39/linux-vm.sh`): `user/elf/cred.c` again (byte-identical to px38's recording), the same after `as 1000 1000`, `user/elf/ident.c` as root and as 1000:1000, `user/elf/ids.c`, the soak | — | pax's own programs | measured (`tests/mpx5-users.d/linux/`, `vm.meta`) | what the man pages leave open: which call clears dumpable, dumpable and AT_SECURE at `execve` (the file-system ids and the group list enter into both), `CapPrm`, the `Groups:` line with no group, the order `getresuid` writes in, the order `setgroups` and `getgroups` check in, 32-bit ids, `prctl`'s other arguments, the mode of `/proc/self/setgroups` |
| black-box Linux 7.2.8: the same programs as uid 1000 of a rootless podman container (`px13-ubuntu`; `notes/px39/linux-ct.sh`) | — | pax's own programs | measured (`notes/px39/linux/ct/`) | a second witness for a user's rows only; never a reference for root |


## px41: the runner flakes (play's sleep, lobo-session's ports)

| source | where | licence | how | used for |
|---|---|---|---|---|
| man-pages `clock_nanosleep(2)` (TIMER_ABSTIME; the raw call answers a negative errno; EINTR on an absolute sleep is answered by calling again), `clock_gettime(2)`, `nanosleep(2)` (a sleep is never shorter than asked) | the man-pages project | as the man pages | read | `user/play/kd.S`'s `play_now_ms` and `play_sleep_until_ms`; why PAX's sleep ends the tick after its target |
| `syscall_64.tbl` (clock_gettime 228, clock_nanosleep 230) and the uapi `linux/time.h` (CLOCK_MONOTONIC 1, TIMER_ABSTIME 1) | the sparse checkout | GPL-2.0 WITH Linux-syscall-note | read | the numbers |
| pax's own `kernel/user` (`sleep_until`), `kernel/timer`, `kernel/speaker` | this repository | pax's own | read | the arithmetic of a late tick (`notes/px41-the-runner-flakes.md`) |
| man-pages `ip(7)` (`ip_local_port_range`, a port of 0 at `bind`), `bind(2)`; QEMU's documentation of `-serial tcp:` (a connection made by QEMU when `server` is not given) and of `-nic user,hostfwd=` | the man-pages project; QEMU's manual | as each | read | `tools/lobo-session`'s ports and its console |
| black-box Linux 7.2.8 (kasumi) and QEMU 11.1.1: a million rounds of bind to port 0, read, close; a QEMU given one host port for two forwards | — | — | measured | how often one port is answered twice; what QEMU does then (`notes/px41/kasumi/`) |

## px42: the owners (a file's owner and group)

No kernel's, libc's or file system's source was read or searched for,
nor that of `su`, `login`, shadow-utils, util-linux or coreutils. The
rules are px38's recorded rows and black-box runs this lane took; where
the man pages and the measurement part, the measurement is what PAX
does and the note says so. Permissively licensed kernels: none
consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `chown(2)` (the owner may change the group to one he is in; the set-ID bits on a change by an unprivileged user, and by root "Linux-specific"), `fchownat(2)` (AT_EMPTY_PATH, AT_SYMLINK_NOFOLLOW), `stat(2)` and `statx(2)` (`st_uid`, `st_gid`; `stx_uid`, `stx_gid`, STATX_UID, STATX_GID), `inode(7)`, `mkdir(2)` and `open(2)` (the group of a new file; the set-group-ID directory), `symlink(2)`, `unix(7)` (a socket's name), `credentials(7)` (the file-system ids), `proc(5)` (who owns `/proc/<pid>`), `cpio(5)` | the pages px36 and px38 cite | their own (GPL-2.0-or-later, BSD, verbatim) | recalled, not opened again in this lane (`px13-ubuntu` holds no man pages); no row rests on them: each is measured | what to ask |
| uapi headers in the sparse checkout: `arch/x86/include/uapi/asm/stat.h` (`struct stat`: `st_uid` at 28, `st_gid` at 32), `include/uapi/linux/stat.h` (`struct statx`: `stx_uid` at 20, `stx_gid` at 24; STATX_UID 8, STATX_GID 16), `linux/fcntl.h`, `arch/x86/entry/syscalls/syscall_64.tbl` (92, 93, 94, 260: all answered since px36) | the sparse checkout's | GPL-2.0 WITH Linux-syscall-note | read | offsets and numbers; no number added |
| `Documentation/driver-api/early-userspace/buffer-format.rst` | the sparse checkout's | GPL-2.0 | read | the header's uid and gid fields |
| px38's recorded answers: `notes/px38/linux/vm.txt` (the `perm` section, 382 lines, real root of Linux 7.2.8 under QEMU) | pax `fe7c05b` | pax's own | read; `tests/mpx5-users.d/linux/perm.txt` to the byte | sections E (`chown`, 71 rows) and H (who owns what is made, 13 rows): the rule and the stamps |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image booted under QEMU 11.1.1 with `notes/px42/vminit.c` as pid 1: root of the initial user namespace, every capability; `notes/px42/linux-vm.sh`): `user/elf/own.c` as root and after `as 1000 1000`, `user/elf/perm.c` again (byte-identical to px38's recording), the soak | — | pax's own programs | measured (`tests/mpx5-users.d/linux/`, `vm-own.meta`) | what px38 did not ask: a link's and a socket's stamp, S_ISGID and the sticky bit at creation, `fchown`, `lchown`, `fchownat`, a `chown` that asks for nothing, which group decides the set-group-ID bit, the file-system ids against the effective ones, 32-bit ids, `/proc/<pid>`'s owner and when its files are root's |
| black-box Linux 7.2.8, the same boot with PAX's image archive as its initramfs (a second archive after it holds `/init`): boreutils' `ls -ln` and `ls -l` | boreutils `2ab3651` | pax's build of boreutils' own | measured (`ls.txt`, `ls-names.txt`, `vm-image.meta`) | an image's owners as Linux reads the same bytes |
| black-box Linux in a container (`tools/linux-tree`): `user/elf/tree.c`'s `owner:` line | — | pax's own | measured afresh at every run of `tests/mpx3-tree` | `chown` to 1000:1000 by root |


## px43: the file checks (open, truncate, access, execve, the walk)

No kernel's, libc's or file system's source was read or searched for,
nor that of `su`, `login`, shadow-utils, util-linux or coreutils. Every
rule the kernel follows is a row Linux answered (px38's recording, or
this lane's probe on the same kind of boot); where a man page and a
measurement could part, the measurement decides and the note says so.
Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `path_resolution(7)` (search permission on each directory of the lookup, EACCES), `inode(7)` and `credentials(7)` (the class; the file-system ids), `open(2)` (O_TRUNC, O_CREAT, EISDIR), `truncate(2)`, `access(2)` and `faccessat2` (the real ids; AT_EACCESS), `execve(2)` (EACCES for no execute permission), `chdir(2)` and `fchdir`, `getcwd(3)`, `unix(7)`; POSIX.1-2024 XBD 4.5 (file access permissions) and 4.16 (pathname resolution) | the pages px38 cites | their own | recalled, not opened in this lane; no row rests on them: each is measured | what to ask |
| uapi constants already in pax's source (`kernel/files`: AT_EACCESS 0x200, AT_EMPTY_PATH, O_TRUNC, O_CREAT, O_DIRECTORY; `kernel/user`: 21, 76, 80, 81, 269, 439, all answered before this lane), taken from the sparse checkout by earlier lanes | the sparse checkout's | GPL-2.0 WITH Linux-syscall-note | not opened again | flags; no number added |
| px38's recorded answers: `notes/px38/linux/vm.txt`'s `perm` section (sections A, B, G: 221 rows, real root of Linux 7.2.8 under QEMU) | pax `fe7c05b` | pax's own | read; `tests/mpx5-users.d/linux/perm.txt` to the byte | the class, root's three rules, real against file-system ids |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image under QEMU 11.1.1, `notes/px43/vminit.c` as pid 1: root of the initial user namespace, every capability; the initramfs PAX's own `chk` archive with `/init` after it; `notes/px43/linux-vm.sh`): `user/elf/chk.c` as root dropping to px38's five actors, and after `as 1000 1000`; the soaks | — | pax's own programs | measured (`tests/mpx5-users.d/linux/chk*.txt`, `vm-chk.meta`) | what px38 did not ask: `.`, `..`, a trailing `/`, a missing or too-long name under a directory one may not search, a working directory and a directory descriptor that lost search, links through such a directory, O_TRUNC with O_RDONLY, O_CREAT and O_EXCL where the directory refuses, `truncate` and O_WRONLY of a directory, a socket's name, `access` with real, effective and file-system ids apart (AT_EACCESS is the file-system ids), `execve` by class of an archive file, a descriptor held across a `chmod` |

## px44: names and metadata (directory write, sticky, the protected settings, chmod, utimensat, set-ID bits, connect)

No kernel's, libc's or file system's source was read or searched for,
nor that of `su`, `login`, shadow-utils, util-linux or coreutils. Every
rule the kernel follows is a row Linux answered (px38's recordings, or
this lane's rows of `chk` on the same kind of boot with the protected
settings at 1); where the prediction and the measurement parted, the
measurement decided and the note says so. Permissively licensed
kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `proc_sys_fs(5)` (the four protected settings), `inode(7)` (the sticky bit), `unlink(2)`, `rmdir(2)`, `rename(2)` (both directories; a directory's `..`; two names of one file), `link(2)`, `symlink(7)`, `chmod(2)`, `utimensat(2)`, `write(2)`, `truncate(2)`, `fallocate(2)` (its errors), `unix(7)` (write permission on the socket's name); POSIX.1-2024 XBD 4.5, XSH `rename()`, `unlink()`, `chmod()`, `futimens()` | the pages px38 cites | their own | recalled, not opened in this lane; no row rests on them alone: each is measured | what to ask |
| uapi constants already in pax's source (`kernel/files`: S_ISVTX, S_ISUID, S_ISGID, S_IXGRP, UTIME_NOW, AT_REMOVEDIR; `kernel/user`: the call numbers), and `fallocate`'s number 285 from `tools/census/syscall_64.csv` (the syscall table px04 took from the sparse checkout) | the sparse checkout's | GPL-2.0 WITH Linux-syscall-note | not opened again | one number added (285) |
| px38's recorded answers: `notes/px38/linux/vm-protected.txt`'s `perm` and `setid` sections (real root of Linux 7.2.8 under QEMU, the four settings at 1) | pax `fe7c05b` | pax's own | read; `tests/mpx5-users.d/linux/perm.txt` and `setid.txt` to the byte | directory write, the sticky bit, `chmod`, `utimensat`, `connect`, the protected rows, what takes the set-ID bits |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image under QEMU 11.1.1, `notes/px44/vminit.c` as pid 1: root of the initial user namespace, every capability, the four settings written to 1 before the probe; the initramfs PAX's own `chk` archive with `/init` after it; `notes/px44/linux-vm.sh`): `user/elf/chk.c` as root dropping to px38's five actors and to two id states, and after `as 1000 1000`; the soaks | — | pax's own programs | measured (`tests/mpx5-users.d/linux/chk*.txt`, `vm-chk.meta`) | what px38 did not ask: what is answered first (an existing name, a missing one, the kind of name, two names of one file, `link`'s EPERM before EACCES, a bound socket's `bind`), a directory moved between parents, sticky directories of root and not world-writable, links of four owners followed at the end and in the middle of a path, O_CREAT of four owners' files, hard links to eleven kinds of file, the settings' files, `chmod` by every actor, `futimens` against the descriptor's mode, ten writes to set-ID files and the writer's ids against the opener's, `connect` to closed names and regular files, root after `setfsuid(1002)` and as (0 1000 0) |

## px45: processes and root's things (who may signal whom, root's calls, /dev's modes, /proc/<pid> by owner, SO_PEERCRED)

No kernel's, libc's, file system's or ALSA's source was read or searched
for, nor that of `su`, `login`, shadow-utils, util-linux or coreutils.
Every rule the kernel follows is a row Linux answered (px38's
recordings, or this lane's `rights` and `devs` on the same kind of
boot); where the prediction and the measurement parted, the
measurement decided and the note says so. Permissively licensed
kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `kill(2)` (the permission rule, SIGCONT within a session, a zombie is a process), `tgkill(2)`, `signal(7)`, `sigaction(2)`'s siginfo, `setpriority(2)`, `sched_setscheduler(2)`, `chroot(2)`, `reboot(2)`, `ioctl_console(2)` and `KIOCSOUND(2const)`, `proc_pid_environ(5)`, `ptrace(2)`'s access mode, `unix(7)` and `socket(7)`'s SO_PEERCRED; POSIX.1-2024 XSH `kill()` | kasumi's man-pages (the pages of `kill(2)` and `ioctl_console(2)` opened; the rest recalled) | their own | read, where opened; no row rests on them alone: each is measured | what to ask |
| uapi `linux/reboot.h` (LINUX_REBOOT_MAGIC1, 2, 2A, 2B, 2C), `linux/resource.h` (PRIO_PROCESS, PRIO_PGRP, PRIO_USER), `linux/sched.h` (SCHED_*, SCHED_RESET_ON_FORK), `asm-generic/socket.h` (SO_PEERCRED 17), `linux/kd.h` and `linux/soundcard.h` (already pax's), and the call numbers 140, 141, 144, 145, 161, 164 to 166, 169 to 171, 227 from `tools/census/syscall_64.csv` (px04's, from the sparse checkout) | the sparse checkout's | GPL-2.0 WITH Linux-syscall-note | opened for these constants | the numbers and constants |
| px38's recorded answers: `notes/px38/linux/vm-protected.txt`'s `sig` and `priv` sections (real root of Linux 7.2.8 under QEMU) | pax `fe7c05b` | pax's own | read; `tests/mpx5-users.d/linux/sig.txt` and `priv.txt` to the byte (this lane's own boot of the same binaries reproduced both) | who may signal whom (102 rows), `/proc/<pid>` by reader, what only root may do |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image under QEMU 11.1.1, `notes/px45/vminit.c` as pid 1: root of the initial user namespace, every capability, the four protected settings written to 1; the initramfs PAX's own `rights` archive with `/init` after it; `notes/px45/linux-vm.sh`): `user/elf/rights.c` as root dropping to its sender and reader states, after `as 1000 1000`, and its soaks | — | pax's own programs | measured (`tests/mpx5-users.d/linux/rights*.txt`, `vm-rights.meta`) | `tkill`; a zombie signalled (by the rule, never -ESRCH); `kill(-1)` and `kill(0)` answers; `si_uid` the real id; SIGCHLD whatever the ids; a held port's -EACCES first; setpriority's and sched_setscheduler's rules for oneself and others, a zombie's; chroot's, umount2's and clock_settime's argument errors before -EPERM, reboot's and sethostname's after it; devtmpfs's modes; `/proc/<pid>`'s owners, `cmdline` and `environ` texts, ptrace's read mode with the file-system ids, a zombie's files; SO_PEERCRED (socketpair, listener, connected ends, unconnected, AF_INET, a short length, the effective ids) |
| black-box Linux 7.2.8-1-cachyos with its own modules (`virtio_snd`, `snd-pcm-oss`, decompressed and loaded as `tools/linux-sound` does, px30's) and QEMU's `virtio-sound-pci`: `notes/px45/devs.c` as root and as 1000:1000 | — | pax's own program | measured (`notes/px45/linux-devs.serial.log`) | `/dev/dsp` and `/dev/snd/*` 0600 root's on devtmpfs (a user's own open -EACCES), OSS ioctls on a descriptor root opened not gated; KIOCSOUND and KDMKTONE refused (-EPERM) to a user on a virtual terminal that is not its controlling terminal, owned or not, and allowed on its controlling terminal |

## px48: job control (groups, sessions, the controlling terminal, stops, the foreground group's keys, hangup)

No kernel's, libc's, shell's or terminal driver's source was read or
searched for, nor that of `su`, `login`, util-linux or procps (ruling
#22). BusyBox (the witness shell) was run, never read. Every rule the
kernel follows is a row Linux answered on real root's guest (this lane's
`jobs` probe and the shell session), or s240's recorded rows; where the
prediction and the measurement parted, the measurement decided and the
note says so. Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `setpgid(2)`, `setsid(2)`, `getsid(2)`, `credentials(7)`, `wait4(2)`, `waitid(2)`, `wait(2)`, `kill(2)`, `signal(7)`, `sigaction(2)` (SA_NOCLDSTOP, CLD_STOPPED, CLD_CONTINUED), `sigsuspend(2)`, `ioctl_tty(2)` and `TIOCSCTTY(2const)`, `TIOCSPGRP(2const)`, `termios(3)` (ISIG, TOSTOP, VMIN, VTIME), `tty(4)`, `proc_pid_stat(5)` | man-pages 6.x, the author's own knowledge | GPL-compatible documentation | the rules, as documentation | `kernel/sched`, `kernel/signal`, `kernel/process`, `kernel/console`, `kernel/files`, `kernel/procfs` |
| POSIX.1-2024: XBD 3 (process group, session, orphaned process group, controlling terminal), XBD 11.1.2 to 11.1.4 and 11.1.9 (the controlling terminal, terminal access control, the special characters), XSH `setpgid`, `setsid`, `tcsetpgrp`, `tcgetpgrp`, `tcgetsid`, `waitpid`, `waitid`, `kill`, `_exit` (the hangup and the orphaned group), the job-control rationale | 2024 | The Open Group | read (the author's own knowledge of it) | the same |
| uapi values: the TIOC* requests (TIOCSCTTY 0x540e, TIOCGPGRP 0x540f, TIOCSPGRP 0x5410, TIOCNOTTY 0x5422, TIOCGSID 0x5429), WUNTRACED 2, WCONTINUED 8, CLD_STOPPED 5, CLD_CONTINUED 6, TOSTOP 0x100, `rt_sigsuspend` 130 | — | GPL-2.0 WITH Linux-syscall-note | the author's own knowledge, confirmed black-box: the probe, built against glibc 2.39's headers in `px13-ubuntu`, asked the same numbers of Linux and PAX and got the same answers | the constants |
| wolf-lang `211d28cb`'s s240 note, `grp.c`, `sess.c`, `run-linux.log` and its strace of dash and GNU timeout | wolf-lang `211d28cb` | the org's own | read | §2's inputs, §3's predictions, the probe's shapes (`user/elf/jobs.c` is this lane's own) |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image `f4c00d5d…` under QEMU 11.1.1, `notes/px48/vmjob.c` as pid 1, the program on a fresh pseudo-terminal as its session leader; the initramfs the suite's own archives) | — | GPL-2.0 (a program we run) | run, never read: `jobs` as root and as 1000:1000, the shell as root and as `pax` | `tests/mpx5-jobs.d/linux/` |
| Ubuntu 24.04 `busybox-static` `1:1.36.1-6ubuntu3.1`, the .deb `944b2728…`, `usr/bin/busybox` `dbac288c…` | Ubuntu archive | GPL-2.0 (a program we run) | fetched by digest and run, never read (`tools/fetch-busybox`, `user/busybox.pin`) | the witness shell (`sh -i`), and `sleep` |
| rootless podman 6.1.3 on kasumi, `px13-ubuntu`; CI's Docker with `python:3.12-slim` by digest | — | — | run: the user's sessions in a throwaway container (`tools/linux-tree --rdev --nsproc`) | J0, J3 |

## px49: the small gaps (pause, rt_sigsuspend, TIOCSTI/TCFLSH/TCSBRK, sendfile and splice under TOSTOP, socket owners, faccessat2's flags, fallocate's modes, unlink of /dev)

No kernel's, libc's, shell's or terminal driver's source was read or
searched for (ruling #22). Every rule the kernel follows is a row Linux
answered on real root's guest (this lane's `gaps` probe, as root and as
1000:1000) or in a container (a user's `unlink` of `/dev` and `/proc`,
`tests/mpx3-tree`); where the prediction and the measurement parted, the
measurement decided and the note says so. Permissively licensed kernels:
none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `pause(2)`, `sigsuspend(2)`, `signal(7)`, `ioctl_tty(2)` (TIOCSTI, TCFLSH, TCSBRK), `termios(3)` (`tcflush`, `tcdrain`, `tcsendbreak`, TOSTOP), `sendfile(2)`, `splice(2)`, `fallocate(2)`, `access(2)` (`faccessat2`), `unlink(2)`, `stat(2)`, `socket(7)`, `eventfd(2)`, `epoll_create(2)`, `accept(2)`, `setfsuid(2)`, `credentials(7)` | man-pages 6.x, the author's own knowledge | GPL-compatible documentation | the rules, as documentation | `kernel/user`, `kernel/sched`, `kernel/signal`, `kernel/console`, `kernel/files`, `kernel/tree` |
| POSIX.1-2024: XSH `pause`, `sigsuspend`, `tcflush`, `tcdrain`, `tcsendbreak`, `faccessat`, `unlink`; XBD 11.1.4 (terminal access control) | 2024 | The Open Group | read (the author's own knowledge of it) | the same |
| uapi values: TCSBRK 0x5409, TCFLSH 0x540b, TIOCSTI 0x5412, TCIFLUSH 0, TCOFLUSH 1, TCIOFLUSH 2; FALLOC_FL_KEEP_SIZE 1, PUNCH_HOLE 2, COLLAPSE_RANGE 8, ZERO_RANGE 0x10, INSERT_RANGE 0x20, UNSHARE_RANGE 0x40; AT_SYMLINK_NOFOLLOW 0x100, AT_EMPTY_PATH 0x1000; `pause` 34 | — | GPL-2.0 WITH Linux-syscall-note | the author's own knowledge, confirmed black-box: the probe, built against glibc 2.39's headers in `px13-ubuntu`, asked the same numbers of Linux and PAX | the constants |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image `f4c00d5d…` under QEMU 11.1.1, `notes/px49/vmjob.c` as pid 1 — px48's with the loopback up and `/sys` mounted — the program on a fresh pseudo-terminal as its session leader; the initramfs the suite's own archive; `dev.tty.legacy_tiocsti` 0) | — | GPL-2.0 (a program we run) | run, never read: `gaps` as root and as 1000:1000, recorded twice, the same bytes | `tests/mpx5-jobs.d/linux/gaps*.tty` |
| rootless podman on kasumi (`px13-ubuntu`), CI's Docker (`python:3.12-slim` by digest) | — | — | run: `gaps` as 1000:1000 (`tools/linux-tree --owners --rdev --nsproc`); `tree` as root and as 1000:1000 (`tests/mpx3-tree`); boreutils' `cat f >> f` (`notes/px49/cat-dark-linux.txt`) | J0, J3; mpx3-tree's T1; the record of `cat`'s refusal |
| boreutils `8f0bbb1` (bu25) and pelt `1102498` (sh17), built from their own trees by `tools/mkboreutils` and `tools/mkpelt` | the org's own | the org's own | built and run, as before | the pins |

## px50: the descriptor table in /proc (`/proc/<pid>/fd`, `fdinfo`), rmdir and rename of /proc and /sys, nbprobe's race

No kernel's source was read or searched for, its procfs above all, nor
any libc's, shell's or terminal driver's (ruling #22). Every rule the
kernel follows is a row Linux answered on real root's guest (this lane's
`fdtab` probe, as root and as 1000:1000) or in a container (the same
probe as 1000:1000; boreutils' `cat` with its input its output, as root
and as `pax`); where the prediction and the measurement parted, the
measurement decided and the note says so. Permissively licensed
kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `proc(5)`, `proc_pid_fd(5)`, `proc_pid_fdinfo(5)`, `readlink(2)`, `open(2)`, `stat(2)`, `statx(2)`, `getdents64(2)`, `ptrace(2)` (PTRACE_MODE_READ_FSCREDS), `prctl(2)` and `PR_SET_DUMPABLE(2const)`, `pipe(7)`, `socket(7)`, `unix(7)`, `eventfd(2)`, `epoll_create(2)`, `rmdir(2)`, `rename(2)`, `tcp(7)` (SIOCOUTQ, SIOCINQ), `poll(2)`, `send(2)` | man-pages 6.19 (kasumi) | GPL-compatible documentation | read | `kernel/files`, `kernel/procfs`, `kernel/cred`, `kernel/user`; `notes/px50/nbrace.c` |
| uapi values: O_LARGEFILE 0100000, O_DIRECTORY 0200000, O_NOFOLLOW 0400000, O_CLOEXEC 02000000; PR_SET_DUMPABLE 4; SIOCINQ, SIOCOUTQ (`linux/sockios.h`) | — | GPL-2.0 WITH Linux-syscall-note | the author's own knowledge, confirmed black-box: fdinfo's `flags` line read on Linux | the constants |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image `f4c00d5d…` under QEMU 11.1.1, `notes/px50/vmjob.c` as pid 1 — px49's with `/` made 0755 — the program on a fresh pseudo-terminal as its session leader; the initramfs the suite's own archive) | — | GPL-2.0 (a program we run) | run, never read: `fdtab` as root and as 1000:1000, recorded twice, the same bytes | `tests/mpx5-jobs.d/linux/fds*.tty` |
| rootless podman on kasumi (`px13-ubuntu`), CI's Docker | — | — | run: `fdtab` as 1000:1000 (`tools/linux-tree --owners --rdev --nsproc --sys`); boreutils' `cat` in the shell-inout sessions (`tests/mpx3-tree`); `notes/px50/nbrace` over the container's loopback under `taskset -c 0-3` | J0, J3; mpx3-tree's T1; pax#79's evidence |
| boreutils `8f0bbb1` (bu25): `src/bore/inout.lu` (the org's own source: which `/proc` lines `cat` reads) and `tests/inout/cases.toml` (its shapes) | the org's own | the org's own | read, as the org's own code | the witness |

## px51: the pins at 0.2.32 (wolf, lupin, pelt's job control, boreutils' kill and timeout)

No kernel's source was read or searched for, nor any libc's, shell's,
terminal driver's, `kill`'s or `timeout`'s (ruling #22). No kernel code
changed: the lane moves pins and measures. Every session is the org's
own binaries typed at PAX's console and at real Linux under QEMU (and,
for `pax`'s rows, in a container); where a session raced on the Linux
side it was reshaped, never loosened (notes/px51-the-pins-0232.md).
Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| wolf 0.2.32 (`v0.2.32` at `72de141f`, release 416327027) and lupin 0.1.54 (`v0.1.54` at `0e536e8`, release 415937354), the linux x86-64 archives `4c37f9c5…` and `175df238…`; wolf-std `d37c911` | the org's own | the org's own | fetched by digest, read twice (the release API, then `sha256sum` of the download on kasumi) | `kernel/wolf.pin`, `user/su/wolf-toolchain.toml` |
| pelt `2676879` (sh18): `notes/sh18-job-control.md`, `tests/session/c_jc_*.keys` | the org's own | the org's own | read, as the org's own code and tests; the keys rewritten in `tools/qemu-halt`'s notation (`user/console/pjobs/`), five as named variants | the pjobs sessions |
| boreutils `43ee185` (bu27): `notes/bu27-the-groups.md`, `notes/bu27/ev/straces.log` and its strace transcripts (kasumi) | the org's own | the org's own | read, as recorded runs of the org's own binaries | which calls `kill` and `timeout` make; the groups session |
| man-pages `kill(1)`, `kill(2)`, `timeout(1)`, `setpgid(2)`, `socketpair(2)`, `unix(7)`, `vfork(2)`, `clone(2)`, `proc_pid_stat(5)`, `proc_pid_status(5)`; POSIX.1-2024 XCU 2.11, `kill`, `jobs`, `fg`, `bg`, `wait` | man-pages 6.19 (kasumi); POSIX.1-2024 | GPL-compatible documentation; IEEE/The Open Group | read | what each row should answer |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image `f4c00d5d…` under QEMU 11.1.1, `notes/px50/vmjob.c` as pid 1, the shell on a fresh pseudo-terminal as its session leader; the suite's own pjobs archive) | — | GPL-2.0 (a program we run) | run, never read: each of the 26 pjobs sessions and the groups session as root and as 1000:1000, recorded twice, the same bytes | `tests/mpx5-jobs.d/linux/pjobs-*`, `groups*` |
| rootless podman on kasumi (`px13-ubuntu`), CI's Docker | — | — | run: the user sessions (`tools/linux-tree --owners --rdev --nsproc`) | J0, J3 |

## px52: the small fixes (EFD_SEMAPHORE, /dev/std* as links, a later image's red in CI, the silent UEFI boot)

No kernel's source was read or searched for, Linux's above all, nor any
libc's, shell's, container runtime's, init system's, device manager's or
QEMU's (ruling #22). Every rule the kernel follows is a row Linux
answered: `evprobe` in a rootless container on kasumi's 7.2.8 and on CI's
runner (`tests/mpx4-ready`'s live Linux side); `fdtab` on real root's
guest and in a container (`tests/mpx5-jobs` J8); the shell-inout
sessions in a container (`tests/mpx3-tree`). Where the prediction and
the measurement parted, the measurement decided and the note says so.
Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `eventfd(2)`, `read(2)`, `poll(2)`, `epoll(7)`, `proc_pid_fdinfo(5)`, `proc_pid_fd(5)`, `symlink(7)`, `path_resolution(7)`, `readlink(2)`, `lstat(2)`, `statx(2)`, `open(2)`, `readdir(3)`, `ip(7)` (`ip_local_port_range`), `udp(7)`, `unshare(1)` | man-pages 6.x | GPL-compatible documentation | the author's own knowledge (no page opened in this lane); no row rests on them alone: each is measured | `kernel/event`, `kernel/ready`, `kernel/files`, `kernel/procfs`; the port pickers; the loop's namespace |
| uapi `linux/eventfd.h`: EFD_SEMAPHORE 1 (EFD_CLOEXEC and EFD_NONBLOCK are O_CLOEXEC and O_NONBLOCK) | — | GPL-2.0 WITH Linux-syscall-note | the author's own knowledge, confirmed black-box (F_GETFL and fdinfo's `flags` show no bit for it) | the flag |
| black-box Linux 7.2.8-1-cachyos: `user/net/evprobe.c` (static, built in `px13-ubuntu`) in a rootless podman container on kasumi, as root and as 1000:1000, twice each, one digest | — | (a program we run) | run | §B (pax#82) |
| black-box Linux 7.2.8-1-cachyos under QEMU 11.1.1 (kasumi's own kernel image `f4c00d5d…`, `notes/px52/vmjob.c` as pid 1: px50's, with what devtmpfs has at `/dev/fd`, `stdin`, `stdout`, `stderr` printed and then the four links made; the suite's own fds archive) | — | GPL-2.0 (a program we run) | run, never read: `fdtab` as root and as 1000:1000, recorded twice, the same bytes | `tests/mpx5-jobs.d/linux/fds*.tty` |
| kasumi's own `/dev` (CachyOS, systemd's boot) and a rootless podman container's (`px13-ubuntu`): `ls -l`, `stat -c`, `readlink` of `/dev/stdin`, `stdout`, `stderr`, `fd` | — | (programs we run) | read, black-box | which links a Linux system has (§C) |
| QEMU's documentation of `-netdev user` (`hostfwd`); QEMU 8.2.2's own line in CI's artifact 12120719249 (push run 39086412018) | — | GPL-2.0 (a program we run) | read; black-box | §D (pax#86) |
| GitHub Actions' `workflow_dispatch` inputs (documentation) | — | — | the author's own knowledge | ci.yml's `jobs_boots` (pax#85) |

## px53: the pins at 0.2.33 (wolf, boreutils' retired refusals, pelt's leak and `cd`; the new calls)

No kernel's source was read or searched for, Linux's above all, nor any
libc's, shell's, `kill`'s or `timeout`'s, nor `systemd-coredump`'s
(ruling #22). No kernel code changed: the lane moves pins and measures.
Every row is the org's own binaries at PAX's console and at real Linux
under QEMU (and, for `pax`'s rows, in a container); what a host's
`core_pattern` decides is named as the host's, never loosened into the
comparison (notes/px53-the-pins-0233.md). Permissively licensed
kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| wolf 0.2.33 (`v0.2.33` at `85dab5d7`, release 417610226) and lupin 0.1.54 (`v0.1.54` at `0e536e8`, release 415937354), the linux x86-64 archives `4f955e8d…` and `175df238…`; wolf-std `cceda63` | the org's own | the org's own | fetched by digest, read twice (the release API, then `sha256sum` of the download on kasumi) | `kernel/wolf.pin`, `user/su/wolf-toolchain.toml`, `user/sigwolf/wolf-toolchain.toml` |
| wolf-lang `v0.2.33`: `CHANGELOG.md`, spec `11-os.md` (`[os.signal.disp.one]`, `[os.signal.exit]`, `[os.proc.status]`, `[os.proc.poll]`, `[os.signal.text]`, `[os.signal.gaps.note]`), `crates/wolf_rt/src/task/stack.rs` (the stack guard: a SENT SEGV by `si_code` ≤ 0), s246's fixtures `crates/wolf_driver/tests/fixtures/signal_gaps/` | the org's own | the org's own | read, as the org's own code and specification | what the five calls ask of a kernel; `user/sigwolf/sigwolf.lu`'s modes (s246's `exit_by.lu`, `group_fault.lu`, `core.lu` in the probe's own shape) |
| boreutils `cc64f68` (bu28): `notes/bu28-the-retired-refusals.md`, `notes/bu28/ev/static-digests.txt`, `notes/bu28/ev/straces.log` | the org's own | the org's own | read, as recorded runs of the org's own binaries | which calls `timeout` and `kill` now make; the groups session's rows; the digests held |
| pelt `be1a75d` (sh19, tl28): `notes/sh19-the-leak-and-the-ci.md` | the org's own | the org's own | read | the static digest held; which sessions `cd`'s join could move (none) |
| man-pages `signal(7)`, `sigaction(2)`, `kill(2)`, `tgkill(2)`, `sigprocmask(2)`, `wait4(2)`, `core(5)`, `getrlimit(2)`, `proc_pid_stat(5)`, `proc_pid_status(5)`, `timeout(1)`, `kill(1)` | man-pages 6.19 (kasumi) | GPL-compatible documentation | read | what each row should answer; `core(5)`: a pattern that pipes is given a core whatever `RLIMIT_CORE` says |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image `f4c00d5d…` under QEMU 11.1.1, `notes/px50/vmjob.c` as pid 1, the shell or the probe on a fresh pseudo-terminal as its session leader; the suite's own pjobs and sigs archives) | — | GPL-2.0 (a program we run) | run, never read: the 26 pjobs sessions (the same bytes as px51's), groups with bu28's rows, sigs, each as root and as 1000:1000, recorded twice, the same bytes; and `cat /proc/self/limits` and `core_pattern` typed there (`RLIMIT_CORE` soft 0, hard unlimited; `core`) | `tests/mpx5-jobs.d/linux/groups*`, `sigs*`, `notes/px53/linux-limits.txt` |
| rootless podman on kasumi (`px13-ubuntu`, `--ulimit core=0:0`), CI's Docker | — | — | run: the user sessions (`tools/linux-tree`); the host's `systemd-coredump` lists their ends with no core file stored | J0, J3; `notes/px53/kasumi-corestore.txt` |
## px55: the small fixes, two (/dev/fd, the port pickers, mpx4-ready's ways, the core limit, /proc/self/limits and core_pattern)

No kernel's source was read or searched for, Linux's above all, nor any
libc's, shell's, container runtime's, init system's or QEMU's (ruling
#22). Every rule the kernel follows is a row Linux answered: `fdtab`'s
`/dev/fd` rows on real root's guest and in a container (`tests/mpx5-jobs`
J8, J3); the tree probe's `proc:` section in a container
(`tests/mpx3-tree` T1) and on real root's guest (Linux's boot values:
`notes/px55/`). Where the prediction and the measurement parted, the
measurement decided and the note says so. Permissively licensed kernels:
none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `proc(5)` (`/proc/pid/limits`, `/proc/sys/kernel/core_pattern`), `proc_pid_fd(5)`, `core(5)`, `getrlimit(2)`/`prlimit(2)`, `symlink(7)`, `path_resolution(7)`, `readlink(2)`, `lstat(2)`, `open(2)`, `getdents64(2)`, `ip(7)` (`ip_local_port_range`), `bind(2)` | man-pages 6.x | GPL-compatible documentation | the author's own knowledge (no page opened in this lane); no row rests on them alone: each is measured | `kernel/files`, `kernel/procfs`, `kernel/user`; the port pickers |
| uapi `asm-generic/resource.h`: the sixteen `RLIMIT_*` numbers (`RLIMIT_STACK` 3, `RLIMIT_CORE` 4, `RLIMIT_NOFILE` 7, `RLIM_NLIMITS` 16) and `RLIM_INFINITY` | — | GPL-2.0 WITH Linux-syscall-note | the author's own knowledge, confirmed black-box (the limits file's rows in that order, each `getrlimit`'s) | `procfs.rlimit` |
| black-box Linux 7.2.8-1-cachyos under QEMU 11.1.1 (kasumi's own kernel image `f4c00d5d…`, `notes/px52/vmjob.c` as pid 1: devtmpfs, then `/dev/fd` and the three `/dev/std*` made; the suite's own archives) | — | GPL-2.0 (a program we run) | run, never read: `fdtab` as root and as 1000:1000, recorded twice, the same bytes; the tree probe as root and as 1000:1000 for its `proc:` section | `tests/mpx5-jobs.d/linux/fds*.tty`; `notes/px55/` (the boot's limits and core pattern) |
| rootless podman on kasumi (`px13-ubuntu`), CI's Docker | — | — | run: `fdtab` as a user (`tools/linux-tree --rdev --nsproc --sys`), the tree probe as root and a user, the port pickers' loop (`--network none`) | J0, J3; mpx3-tree T1; #89's loop |
| GitHub Actions' `workflow_dispatch` inputs (documentation) | — | — | the author's own knowledge | ci.yml's `ways` (pax#91) |
