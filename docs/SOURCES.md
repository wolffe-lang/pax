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
| lobo | release v0.1.1 (archive `6e21e151…`), trunk `f79418d1181d…` for its demo site (the directory `tools/census/inside/stage.sh` fetches) | GPL-3.0 (the project's own) | read: the demo site's four shell scripts and its configs; run: lobo | `workloads/lobo.sh` |
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
| black-box, QEMU's user-mode network: the gateway's hardware address is 52:55:0a:00:02:02; a datagram for a guest whose address it has not learned makes it broadcast an ARP request (60 bytes) and deliver the datagram after the reply; its ARP replies are 64 bytes, zero-padded; with `ipv6=off` it sends nothing unasked | 8.2.2, 11.1.x | — | measured (the captures) | `tests/mpx4-net`, `tools/pcap-net` |
| black-box, the firmware: OVMF's own driver sends one or two IPv6 frames (an MLD report, a neighbour solicitation) from the device's address on some boots, before the kernel starts; SeaBIOS's option ROM sends nothing when the CD boots | kasumi's and CI's OVMF | — | measured (the captures) | `tools/pcap-net`'s "before the kernel" frames |
