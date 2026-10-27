# SOURCES — what each change was written from

The clean-room rule (`CLAUDE.md`) requires this log. Every lane adds its
entries: what it consulted, at which version, for which file, and how
(read, black-box run, or the author's own knowledge with no text copied).
**Linux kernel source is never an entry**: the allowed Linux material is the
uapi headers, the syscall tables, `Documentation/`, and black-box behaviour.

## px74 — xHCI and USB keyboards (2026-10-27)

No kernel, firmware, hypervisor or USB driver's implementation source was
read. The Linux guest is an unmodified kernel binary; `modules.builtin`
was read only to confirm built-in xHCI and HID support. The test program
includes the installed Linux uapi `linux/input.h` for `EVIOCGREP` (250 ms
and 33 ms, measured), not a driver header. Existing PAX PCI, virtio,
interrupt, console and px70 keyboard-test code are this project's own.
The release-build follow-up also read the project's own wolf compiler
`crates/wolf_wir/src/midend/rangeopt.rs` and
`crates/wolf_codegen_llvm/src/lib.rs` (range analysis and the documented
`WOLF_CLANG` seam), and px75's `f57d3770` change description. The measured
compiler remains the pinned 0.2.35 archive; the capture wrapper preserves
clang's arguments. `kernel/usb_topology` contains the same specification-
derived helpers extracted from `kernel/xhci`, not a second implementation.

| source | version | consulted for |
|---|---|---|
| [Intel xHCI Requirements Specification](https://www.intel.com/content/dam/www/public/us/en/documents/technical-specifications/extensible-host-controler-interface-usb-xhci.pdf) | 1.2, May 2019 | Read §§4.2–4.3, 4.9, 4.17, 4.20; operational/runtime registers; §6.2 slot and endpoint contexts; §6.4 TRBs; §7.1 legacy ownership. `kernel/xhci`: rings, context sizes, root ports, routing and TT fields, scratchpads, INTx. |
| [USB 2.0 specification bundle](https://www.usb.org/sites/default/files/usb_20_20250603.zip), `usb_20.pdf` | 2.0 | Read chapter 9's device/configuration/interface/endpoint descriptors and requests; chapter 11's hub descriptor, power, reset, status and change acknowledgement. `kernel/xhci`: bounded descriptor walking and USB2 hubs. |
| [USB 3.2 specification bundle](https://usb.org/sites/default/files/usb_32_202206_0.zip), `USB 3.2 Revision 1.1.pdf` | 1.1, June 2022 | Read §8.9 route nibbles, §9.1.2 enumeration and §10.16 hub requests. Hubs are chapter 10 in this revision, not chapter 11. SuperSpeed devices are enumerated but not driven. |
| [Device Class Definition for HID](https://www.usb.org/sites/default/files/documents/hid1_11.pdf) | 1.11 | Read §7.2.4 SET_IDLE, §7.2.6 SET_PROTOCOL, appendices B/C/F: eight-byte boot reports, six unordered usages, rollover, host repeat and lock state. |
| [HID Usage Tables](https://www.usb.org/sites/default/files/hut1_7.pdf) | 1.7, §10 | Read the keyboard/keypad usage table. `kernel/usb_keys` maps usages to PAX's physical-key identifiers, not a second character table. |
| Linux guest, QEMU and the original `user/elf/usbkeys.c` probe | Linux 7.3.0-4-cachyos; QEMU 8.2.2 | Black-box key bytes, repeat settings/timestamps, hot-unplug and replug. Kernel binary digest and raw records in `notes/px74/`; no Linux implementation source read. |

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
| **PAX's own rows**, `font/pax-extra.bdf` (gm01): U+2024 ONE DOT LEADER and U+25AA BLACK SMALL SQUARE, the two code points the wolf games draw that Spleen 2.2.0 lacks | 2026-10-25 | GPL-3.0 with the wolf Training Data Permission (PAX's own; not part of Spleen) | drawn by hand, cell for cell, in Spleen's metrics and stroke weight (a two-pixel dot on the baseline; a filled four-by-four square on the bullet's footprint); no other font consulted | `boot/font.S`'s rows above U+00FF (`tools/mkfont`, `font/extent.txt`), `tools/screen-ref` |
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

## px56: exec from the tree, and `#!` (pax#95, #96)

No kernel's source was read or searched for, Linux's above all, nor any
libc's, shell's, container runtime's, init system's or QEMU's (ruling
#22). Every rule `execve` and `execveat` follow is a row Linux answered:
`user/elf/execs.c` on real root's guest and in a container, as root and
as 1000:1000 (`tests/mpx5-jobs`' execs image, J12, J3), and the typed
pelt session (`user/console/execs.keys`, xsh, xsh-user). Where the
prediction and the measurement parted (the name `execveat(fd, "",
AT_EMPTY_PATH)` gives a program; an empty interpreter in a short file
with no newline; a NUL where a `#!` argument starts), the measurement
decided and the note says so. Permissively licensed kernels: none
consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `execve(2)` (its "Interpreter scripts" paragraph and NOTES: the interpreter, one optional argument with its inner blanks, the script's path appended, argv[0] not passed on, four recursions; ELOOP, ETXTBSY, ENOEXEC, EACCES), `execveat(2)` (AT_EMPTY_PATH, AT_SYMLINK_NOFOLLOW, `/dev/fd/N/P`, the close-on-exec descriptor's ENOENT), `fexecve(3)`, `proc(5)` (`/proc/pid/exe`, `comm`), `prctl(2)` (PR_GET_NAME), `getauxval(3)` (AT_EXECFN), `path_resolution(7)`, `open(2)` and `truncate(2)` (ETXTBSY) | man-pages 6.x | GPL-compatible documentation | read | what each row should answer, the prediction |
| POSIX.1-2024 XCU 2.9.1.4 (a script with no `#!` is the shell's), XSH `exec` | 2024 | the standard | read | ENOEXEC's place: the shell runs such a file itself |
| uapi `linux/fcntl.h` (AT_FDCWD, AT_SYMLINK_NOFOLLOW 0x100, AT_EMPTY_PATH 0x1000), `asm-generic/errno-base.h` (ETXTBSY 26), the syscall table (execveat 322) | — | GPL-2.0 WITH Linux-syscall-note | the author's own knowledge, confirmed black-box | the numbers |
| pelt `be1a75d`: `src/sh/exec.lu` (`is_script`, the `-125` fallback to `os_exe()`) | the org's own | the org's own | read | why the maintainer's `./Script/greet.sh` needs ENOEXEC; the session's rows |
| black-box Linux 7.2.8-1-cachyos under QEMU 11.1.1 (kasumi's own kernel image `f4c00d5d…`, `notes/px52/vmjob.c` as pid 1, unchanged; the suite's own execs archive) | — | GPL-2.0 (a program we run) | run, never read: the probe as root and as 1000:1000 and the typed session as both, recorded twice, the same bytes | `tests/mpx5-jobs.d/linux/execs*.tty`, `xsh*.tty`; `notes/px56/kasumi-recordings-twice.out` |
| rootless podman on kasumi (`px13-ubuntu`), CI's Docker | — | — | run: the user's probe and session (`tools/linux-tree --rdev --nsproc --owners`) | J0, J3 |
| PAX trunk `241b322`'s loader (the archive's contiguous read) | the project's own | — | run: the speed of 780 fork–exec–wait rounds against the tree's | `notes/px56/kasumi-speed.txt`: the fast case not kept |

## px54: lope on PAX (ruling #91 R4; the pelt hook)

No kernel's source was read or searched for, Linux's above all, nor any
libc's or shell's, nor any jumper's or matcher's (nucleo, fzf, skim,
zoxide, autojump, z, fasd; ruling #91 R3). No kernel code changed: the
lane adds a program, a start-up file and a suite, and measures. Every
row is the org's own binaries at PAX's console and in a Linux container
(notes/px54-lope-on-pax.md). Permissively licensed kernels: none
consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| lope `5ac37df` (lp00; the maintainer's, private): `src/cmd/init.lu`, `src/db/paths.lu`, `src/db/store.lu`, `shell/pelt/*.sh`, `shell/posix/menu.sh`, `tools/build`, `tools/mkstatic`, `wolf-toolchain.toml`, `notes/lp00-the-port.md` | the org's own | GPL-3.0 + the wolf Training Data Permission | read and cited, as the maintainer's code; built, never copied into pax | `tools/mklope`, `user/lope.pin`, the hook's shape, where the store is, the session's rows |
| pelt `90d7c64` (sh21): `src/sh/interact.lu`'s `run_env_file` (`$ENV`), `notes/sh21-the-hook.md` | the org's own | the org's own | read | how the console shell runs `/etc/shrc`; what the handler does |
| wolf 0.2.33 (`4f955e8d…`, lope's) and 0.2.32 (`4c37f9c5…`, pelt's), the linux x86-64 release archives; wolf-std `cceda63` and `d37c911` | the org's own | the org's own | fetched by digest, the release API read twice | lope's and pelt's static builds |
| POSIX.1-2024 XCU 2.5.3 (`ENV`), 2.9.1 (command search), `cd` (`cd -` writes the new directory), `read`, `env` | 2024 | (a standard) | the author's own knowledge | the hook line and what each row should show |
| `strace(1)` 6.8 (as documentation and as a black box) in `localhost/px13-ubuntu` on kasumi | — | (a program we run) | run on lope's own runs, never read | lope's 23 calls (notes/px54/census/) |
| black-box Linux 7.2.8-1-cachyos: rootless podman on kasumi (`px13-ubuntu`), CI's Docker | — | (programs we run) | run: the typed session on a pseudo-terminal, root and 1000:1000 (`tools/linux-tree`) | L1's reference |
| lobo's `.github/actions/acquire-toolchain/action.yml` (the org's) | the org's own | the org's own | read | the org's way of reading a private sibling in CI (`WOLF_CI_TOKEN`, absence is failure) |

## px57: the pins at 0.2.34, aspen on PAX, and a lupin that runs there

No kernel's source was read or searched for, Linux's above all, nor any
libc's (glibc's, musl's), shell's or init system's, nor tree's (aspen's
rule 1, ruling #103), nor any interpreter's but lupin's own. No kernel
code changed: the lane moves pins, adds two programs, two probes and two
suites, and measures. Every row is the org's own binaries at PAX's
console against real Linux under QEMU or a Linux container
(notes/px57-the-pins-0234.md). Permissively licensed kernels: none
consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| wolf 0.2.34 (`v0.2.34` at `9da7bdcf`, release 419552903) and lupin 0.1.55 (`v0.1.55` at `e642f26`, release 418932753), the linux x86-64 archives `88a9dd3d…` and `1152abc0…`; wolf-std `3bacc5f` (sc69's merge) | the org's own | the org's own | fetched by digest, read twice (the release API, then `sha256sum` of the download on kasumi) | `kernel/wolf.pin`, `user/su`, `user/sigwolf`, `user/edwolf` |
| wolf-lang `v0.2.34`: `CHANGELOG.md`, spec `11-os.md` (`[os.proc.fork]`, `[os.signal.wait.fds]`, `[os.term.mode]`, `[os.term.restore]`, `[os.fs.open]`, `[os.fs.sync]`, `[os.fs.realpath]`, `[os.clock.ns]`, `[os.proc.spawn]`, `[os.proc.fds]`, `[os.host.sigs]`); wolf-lang#847's branch `s253`, its spec's `[os.uname]`, `[os.proc.core]`, `[os.proc.adopt]` | the org's own | the org's own | read, as the org's own specification | `user/edwolf/edwolf.lu`'s rows; `user/elf/hostq.c`'s (pax#107) |
| aspen `103ba46` (ap00): `tools/mkaspen`, `tools/build`, `wolf-toolchain.toml`, `docs/MAP.md`, `notes/ap00-the-first-light.md`; built from its tree, never copied into pax | the org's own | GPL-3.0-or-later | read as the maintainer's code and records (its `src/` not read) | `tools/mkaspen`, `user/aspen.pin`; the digest held (ap00's) |
| wolf-interp `v0.1.55` / `fcf2fd0`: `Cargo.toml`, `Cargo.lock`, `build.rs` (D57's stamp), `rust-toolchain.toml`, `.github/workflows/release.yml`, `src/main.rs`'s commands, `src/eval/builtin.rs`'s `env_get` (the machine's own overlay), `docs/manual/01-running-programs.md`, its corpus (`vendor/upstream/corpus`) | the org's own | GPL-3.0-or-later | read, as lupin's own code (the one interpreter whose source the lane reads); built at the tag | `tools/mklupin`, `user/lupin.pin`, `user/lupin/*.lu`, the census's programs |
| Rust 1.97.1 and its `x86_64-unknown-linux-musl` target (rustup's prebuilt std with its self-contained musl CRT and libc), rustup-init `5be191e8…` | rust-lang's releases | MIT / Apache-2.0 (and musl's MIT, linked) | run: installed inside a throwaway image (notes/px57/rust/Containerfile) and on CI's runner; nothing of musl read | the static lupin |
| man-pages `fork(2)`, `fsync(2)`, `realpath(3)`, `open(2)` (O_EXCL), `termios(3)`, `poll(2)`, `prctl(2)` (PR_SET_DUMPABLE), `getrlimit(2)` (prlimit64), `fcntl(2)` (F_GETFD, F_SETFD), `uname(2)`, `proc(5)` (`/proc/self/fd`), `strace(1)` | man-pages 6.19 (kasumi) | GPL-compatible documentation | read | what each row should answer |
| `strace(1)` 6.8 in `localhost/px13-ubuntu` on kasumi | — | (a program we run) | run on aspen's and lupin's own runs, never read | the census (notes/px57/census/) |
| black-box Linux 7.2.8-1-cachyos (kasumi's own kernel image `f4c00d5d…` under QEMU 11.1.1, `notes/px52/vmjob.c` as pid 1, unchanged; the suite's own eds archive) | — | GPL-2.0 (a program we run) | run, never read: edwolf and hostq as root and as 1000:1000, recorded twice, the same bytes | `tests/mpx5-jobs.d/linux/eds*.tty`, `hostq*.tty` |
| rootless podman on kasumi (`px13-ubuntu`), CI's Docker | — | — | run: the user's probe rows and the aspen and lupin sessions (`tools/linux-tree`) | J0, J3; A1; U1 |

## px58: yew on PAX, the census

No kernel's source was read or searched for, Linux's above all, nor any
libc's, terminal driver's or terminal emulator's, nor any editor's but
yew's and sagitta's (the maintainer's; Track 12's rule 1). One kernel
change, `kernel/console`'s cursor and editing keys, written from the
measurement below and the set-1 scancode table px13 used. Every row is
the org's own binaries at PAX's console and on a Linux pseudo-terminal
(notes/px58-yew-on-pax.md). Permissively licensed kernels: none
consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| yew `77c1083` (the maintainer's, public): `src/term/tty.lu`, `src/term/input.lu`, `src/term/render.lu`, `src/edit/driver.lu`, `src/edit/cmdline.lu`, `src/edit/message.lu`, `src/yew.lu`, `runtime/init.fl`, `tools/build`, `tools/goldens`, `tools/oracle`, `docs/MAP.md`, `wolf-toolchain.toml` | the org's own | GPL-3.0 + the wolf Training Data Permission | read and cited; built, never copied into pax; no line changed | `tools/mkyew`, `user/yew.pin`, the census's roles, the session's keys, the 4 s message |
| sagitta `9ace98c2` (the maintainer's C yew, the oracle): `tests/pty/registry.c`'s notepad cases; its PTY runner built by yew's `tools/oracle` | the maintainer's | GPL-3.0 | read; built and run | the census's first workload (64 of 64 green under strace) |
| wolf 0.2.33 `spec/11-os.md` (`[os.term.*]`, `[os.signal.wait.fd]`), 0.2.34's (`[os.editor.calls.note]`, `[os.term.restore]`, `[os.signal.wait.fds]`, `[os.fs.sync]`, `[os.fs.realpath]`), 0.2.33's `spec/08-package.md` (`[pkg.caps]`) | the org's own | the org's own | read | termwolf's calls; the 0.2.34 calls listed as coming |
| man-pages `termios(3)`, `ioctl_tty(2)`, `console_codes(4)`, `strace(1)`, `poll(2)`, `reboot(2)`; ECMA-48 (the control functions' names); POSIX.1-2024 XBD 11 | man-pages 6.x; 5th ed. | documentation | read | the rows' names, what each should answer |
| uapi `asm-generic/termbits.h`, `termbits-common.h` (the flag bits' values), `asm-generic/ioctls.h` (TCGETS 0x5401 … TIOCSWINSZ 0x5414), the syscall table (ioctl 16) | — | GPL-2.0 WITH Linux-syscall-note | the author's own knowledge, confirmed black-box (strace's decoding) | termwolf's bit names and requests |
| ncurses' terminfo database, `infocmp linux` on kasumi | — | (data) | read | the `linux` terminal's key strings, beside the measurement |
| `strace(1)` 6.8 in `localhost/px13-ubuntu` on kasumi | — | (a program we run) | run on yew's goldens and the typed session, never read | §B, §C |
| black-box Linux 7.2.8-1-cachyos under QEMU 11.1.1 (kasumi's own kernel image `f4c00d5d…`, a VGA display, the PS/2 keyboard; `notes/px58/vtkeys.c` as pid 1) | — | GPL-2.0 (a program we run) | run, never read: the VT's keys, window and answers, twice, the same rows | §E, `kernel/console`'s keys |
| rootless podman on kasumi (`px13-ubuntu`), CI's Docker | — | — | run: the probe and the session on a pty (`tools/linux-tree`) | Y1, Y4's reference |

## px59: the console for an editor

No kernel's source was read or searched for, Linux's above all, nor any
libc's, terminal driver's or terminal emulator's, nor any editor's but
yew's and pelt's (the maintainer's, read for what they write and ask).
`kernel/screen`, `kernel/console` and `tools/screen-ref` were written
from console_codes(4), ECMA-48 and the measurements below; the VT was a
black box: bytes sent, `/dev/vcsa1` and the input read back.
Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `console_codes(4)`, `vcs(4)`, `console_ioctl(4)` (VT_GETSTATE, VT_ACTIVATE), `termios(3)`, `poll(2)`; ECMA-48 (the control functions' names and syntax) | man-pages 6.x; 5th ed. | documentation | read | the classes' names, what to measure, the probes' calls |
| black-box Linux 7.2.8-1-cachyos under QEMU 11.1.1 (kasumi's own kernel image `f4c00d5d…`, its VGA display and PS/2 keyboard; `notes/px59/vtprobe.c` and `vtprobe2.c` as pid 1, built static in `px13-ubuntu`) | — | GPL-2.0 (a program we run) | run, never read: each case's cells and cursor, the answers, the keys with their modifiers, each probe twice, the same rows | `notes/px59/vt.rows`, `vt2.rows`; every class of `kernel/screen`, the keys of `kernel/console`, `tests/mpx5-screen.d/vtcheck.py` |
| yew `77c1083` (the maintainer's): `src/term/tty.lu` (the probe string, DA1 as its fence, the alternate screen's ESC 7 / ESC 8), `runtime/init.fl` (C-z) | the org's own | GPL-3.0 + the wolf Training Data Permission | read and cited, never changed | what yew asks and how it suspends |
| pelt `90d7c64` (the maintainer's): `src/sh/edit.lu` (`ed_query`: one cursor report before each prompt, 300 ms, never asked again unanswered; the editor's moves) | the org's own | GPL-3.0 + the wolf Training Data Permission | read and cited | R-px59-4, S3 |
| Limine 12.9.1's configuration (`resolution:`) | by digest (`boot/limine.pin`) | BSD-2-Clause | run | `boot/limine-vt.conf` |
| rootless podman on kasumi (`px13-ubuntu`), CI's Docker | — | — | run: the keyboard session on a 50 by 160 pseudo-terminal (`tools/linux-tty --winsize`) | Y6, Y7's reference |


## px60: the dev compiler

No kernel or libc source was read. Wolf's own v0.2.34 source was read
and patched in a separate worktree; the attached patch is the only
compiler source change used by the dev recipe. No upstream trunk was
changed. The kernel is unchanged in this lane.

| source | how used |
|---|---|
| wolf-lang v0.2.34, `9da7bdcf`; driver, runtime, checked machine and backend manifests | owned source: derive the command/link boundaries, prototype the musl portability fixes |
| wolf-std `e036bec318ad81ecd5a025612bc2c2adb17527f3` | owned source: stage the compiler's STD-PIN and run a real `std.str` witness |
| man7 `newlocale(3)`, `pthread_join(3)`, `mremap(2)` | API documentation: a null-base, zero-mask locale uses POSIX/C defaults; joinable thread ownership; the measured allocator resize and its scope boundary |
| Rust 1.97.1 musl target and Rust 1.99.1 musl-host rust-lld | shipped binaries only: compiler/runtime build inputs and alternative-linker ELF inspection |
| Alpine 3.20 musl-dev, lld-dev, LLVM 17 packages | shipped binaries and package inventories only: static libc/CRT link feasibility and the packaged linker's dynamic dependencies |
| LLVM 17.0.6 release source archive | authorized throwaway lld-only build using clang, libc++ and LLVM libunwind; never a source for PAX kernel code |
| strace 6.8, Linux in a container, PAX under QEMU TCG | black-box runs: commands, syscall union, Linux/PAX transcripts and named linker walls |

## px62: mappings, FIFOs and locks (pax#127, #128, #108)

No Linux kernel source, no other kernel's, no musl's or glibc's source
was read. Every rule is a man page's or POSIX's, a number is a uapi
header's or the syscall table's, and every answer the kernel gives was
measured black-box on Linux with the two probes before the kernel was
written (kasumi's 7.2.8 in a `px13-ubuntu` container, then CI's
runner kernel through `tools/linux-tree`). Permissively licensed
kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `mmap(2)` (munmap and its ENOMEM split), `mremap(2)`, `msync(2)`, `mprotect(2)`, `madvise(2)`, `fork(2)`, `execve(2)`, `truncate(2)`, `flock(2)`, `fifo(7)`, `pipe(7)`, `mknod(2)`, `mkfifo(3)`, `open(2)`, `sigaction(2)` (si_code), `tmpfs(5)` | man-pages 6.x | documentation | read | what each call does and answers; what the probes ask |
| POSIX.1-2024: `mmap()`, `msync()`, `munmap()`, `mkfifo()`, `open()` (FIFOs) | 2024 edition | documentation | read | what is specified and what is left to the system (a private page's view of a later write; O_RDWR of a FIFO) |
| uapi `linux/mman.h` (MREMAP_MAYMOVE, MREMAP_FIXED, MREMAP_DONTUNMAP, MAP_SHARED_VALIDATE), `asm-generic/mman-common.h` (MS_ASYNC, MS_INVALIDATE, MS_SYNC, MAP_SYNC), `asm-generic/fcntl.h` (LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN), `linux/stat.h` (S_IFIFO, S_IFSOCK, S_IFBLK), `asm-generic/siginfo.h` (BUS_ADRERR, SEGV_ACCERR), `asm-generic/errno.h` (ENOLCK, EOVERFLOW, EOPNOTSUPP); `syscall_64.tbl` (25 mremap, 26 msync, 73 flock, 133 mknod, 259 mknodat) | the refs clone (`wolf/refs/repos/linux`, sparse to the allowed paths) | GPL-2.0 WITH Linux-syscall-note | read, numbers only | the constants in kernel/vm, kernel/files, kernel/signal, kernel/user |
| Intel SDM vol. 3A §4.5 (table 4-20: a 4 KiB PTE's bits 11:9 ignored), AMD64 APM vol. 2 §5.4.1 (AVL) | current editions | documentation | read | kernel/paging's BORROWED and COW bits |
| black-box Linux: `user/elf/maps.c` and `user/elf/fifos.c` as pid 1, root and 1000:1000, in a container whose root is a tmpfs (kasumi 7.2.8-1-cachyos, podman; CI's runner kernel, Docker) | — | GPL-2.0 (a program we run) | run, never read | every expected line of `tests/mpx3-maps`; the decisions measured, not guessed: a failed LOCK_NB conversion leaves no lock, a truncation unmaps copied private pages too (SIGBUS), a waiting FIFO open counts as its end, mmap of a pipe, a directory and /dev/null -ENODEV |
| pelt `57ffef9` (the maintainer's): `user/console/fork/diff/builtin/c_s_dot_special_file.sh` (pax's copy of pelt's fixture) | the org's own | GPL-3.0 + the wolf Training Data Permission | read and run | the corpus row px61 left at 21/22 |
| wolf-lang `3c7ac0e6` (the maintainer's): `crates/wolf_driver/tests/fixtures/fs_gaps/lock_rows.lu`, `fifo_rows.lu` (s254) | the org's own | GPL-3.0 + the wolf Training Data Permission | read and cited, never changed | the system calls `fifos.c`'s s254 rows make |

## px63: the disk (virtio-blk, the block layer, ext2, the mount table, reboot)

No Linux kernel source, no other kernel's, no musl's, glibc's, QEMU's or
e2fsprogs' source, and no file-system driver from anywhere was read.
The on-disk layout is the kernel's own documentation of it (its
`Documentation/` tree, which the refs clone keeps); every number is a
specification's, a uapi header's or the syscall table's; e2fsprogs and
Linux were run as black boxes (the image made by one, checked by
another, read and written by Linux on QEMU), never read. Permissively
licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| Linux `Documentation/filesystems/ext2.rst` (the layout, the superblock's fields, block groups, the bitmaps, inodes and the 12 direct, single, double and triple indirect blocks, directories, fast and slow symbolic links, the revisions and the feature sets) and `Documentation/filesystems/ext4/` (`super.rst`, `group_descr.rst`, `blockgroup.rst`, `bitmaps.rst`, `inode_table.rst`, `inodes.rst` (`i_extra_isize`, the extra time words' epoch bits and nanoseconds, the high 16 bits of the owner), `blockmap.rst`, `directory.rst` (linear directories, `ext4_dir_entry_2`, the file-type byte, htree's INDEX_FL), `special_inodes.rst`, `dynamic.rst`, `globals.rst`) | the refs clone (`wolf/refs/repos/linux`, sparse to the allowed paths) | GPL-2.0 (documentation) | read | `kernel/ext2`: every structure, field offset and rule it keeps |
| OASIS *Virtual I/O Device (VIRTIO)* §5.2 (the block device: its device ids, feature bits VIRTIO_BLK_F_RO, F_BLK_SIZE, F_SEG_MAX, F_FLUSH, `virtio_blk_config`, the request header, types IN, OUT, FLUSH and GET_ID, the status byte), with §2 and §4.1 as px20 read them | 1.2 | OASIS's (a specification) | the author's own knowledge of it, held black-box (QEMU's device answers every request: a wrong layout returns an error status or nothing) | `kernel/vblk`, `kernel/virtio`'s 32- and 64-bit configuration reads (§4.1.4.3's config_generation) |
| man-pages `fstab(5)`, `mount(8)` (the option names: defaults, ro, rw, sync, async, nofail, relatime, nosuid, nodev, noexec), `statfs(2)`, `fsync(2)`, `sync(2)` and `syncfs(2)`, `reboot(2)`, `msync(2)`, `statvfs(3)`, `mke2fs(8)`, `e2fsck(8)`, `debugfs(8)` (`write`, `mkdir`, `symlink`, `ln`, `sif`, `ls -p`, `stat`, `dump`, `cat`) | man-pages 6.x, e2fsprogs 1.47.0's pages | documentation | read | `kernel/fstab`'s table and options; the calls' answers; how the images are made and checked (`tools/mkdisk`, `tools/e2tree`) |
| uapi `linux/magic.h` (EXT2_SUPER_MAGIC, TMPFS_MAGIC, PROC_SUPER_MAGIC, SYSFS_MAGIC), `asm-generic/statfs.h` (`struct statfs`'s fields), `linux/reboot.h` (the magic numbers, LINUX_REBOOT_CMD_*), `syscall_64.tbl` (74, 75, 137, 138, 162, 169, 306) | the refs clone | GPL-2.0 WITH Linux-syscall-note | read, numbers only | `kernel/files`' statfs, `kernel/user`'s reboot; f_flags' ST_RDONLY, ST_VALID and ST_RELATIME are statvfs(3)'s names for the bits Linux's statfs answered on the fixture (black-box, below) |
| Intel I/O Controller Hub 9 (ICH9) data sheet: the reset control register (I/O port 0xcf9: SYS_RST, RST_CPU, FULL_RST); the 8042 keyboard controller's pulse-reset command (0xfe to port 0x64) | — | Intel's (a data sheet); the 8042's command a de facto standard | the author's own knowledge; measured: QEMU's q35 resets on 0x02 then 0x06 at 0xcf9 under SeaBIOS and OVMF | `kernel/user`'s `reboot` |
| e2fsprogs: `mkfs.ext2`, `e2fsck -fn`, `debugfs` | 1.47.0-2.4~exp1ubuntu4.1 in `docker.io/library/ubuntu@sha256:534baea6…` (mke2fs `07cd24ce…`, e2fsck `c69c6315…`, debugfs `1e83118c…`: `tools/e2fs --version`) | GPL-2.0 (programs we run) | run, never read | the images (`tools/mkdisk`), the oracle that each written image is clean, the trees PAX and Linux leave (`tools/e2tree`); measured: debugfs keeps the low 32 bits of a time (the extra word set by hand), and writes the superblock's write time at its close (E2FSPROGS_FAKE_TIME for one disk's bytes) |
| black-box Linux: kasumi's 7.2.8-1-cachyos on QEMU (q35, TCG), the image as its virtio disk (`tools/linux-blk`), the same programs and sessions as PAX's | — | GPL-2.0 (a program we run) | run, never read: modules.builtin and modules.dep listed to load virtio_blk and ext4 (which mounts ext2) | every expected line of `tests/mpx6-ext2` (recorded in `tests/mpx6-ext2.d/linux/`); the decisions measured, not guessed: the disk's device numbers (254:0), a directory's atime moved by a read (relatime), statfs's f_blocks less the metadata (bsddf), the fsid's two words, new inodes' `i_extra_isize` of 32, the 512-byte block counts, a write session's tree |
| QEMU's documented options: `-drive file=…,if=none,id=…,format=raw[,readonly=on]`, `-device virtio-blk-pci,drive=…` | 8.2.2 (CI), 11.1.1 (kasumi) | GPL-2.0 (a program we run) | the author's own knowledge of the documentation; run | `tests/mpx6-blk`, `tests/mpx6-ext2`, the playground |

## px64: scent on PAX (/bin/grep, the wrappers, the archive's links)

No Linux kernel source, no other kernel's, no glibc's, musl's, shell's
or grep implementation's source was read: not GNU grep's, gnulib's,
busybox's, and not scent's own `src/` (scent's rule: nobody reads GNU
grep's source, and pax has no reason to read scent's). GNU grep 3.12
was built by scent's own tool from its signature-verified tarball and
run as a black box; nothing of its tree was opened, its build logs were
not printed. Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| `cpio(5)`'s "new ASCII" format (a symbolic link's entry: mode 0120000 with its permission bits, the target as the entry's data, no NUL), with Linux's `Documentation/driver-api/early-userspace/buffer-format.rst` as px10 read it | man-pages / the kernel's documentation | documentation | the author's own knowledge of the documentation; checked by the suite's own archive reader (`tests/mpx5-scent` A0) and by the archive booting | `tools/mkinitramfs`' `/PATH->TARGET`, kernel/tree's adoption |
| man-pages `symlink(2)` (the target's length, at most PATH_MAX - 1 bytes), `symlink(7)` (a link's mode 0777, its bits unused), `execve(2)` (the `#!` line's one optional argument, its bytes as written) | man-pages 6.x | documentation | the author's own knowledge; measured (the session's link rows, the `#!` abort row, held to Linux) | the adoption's 1-4095 bytes; the abort row passed by a `#!` line |
| scent `b6f63a4` (the org's own, public): `README.md`, `wolf-toolchain.toml`, `scent-oracle.toml`, `tools/mkscent`, `tools/build`, `tools/lib-toolchain.sh`, `tools/lib-toml.sh`, `tools/fetch-toolchain`, `tools/fetch-oracle`, `tools/fetch-oracle.py`, `tools/oracle.py` (its harness, the head), `tools/pax-posture`, `tools/in-container`, `ci/oracle.Containerfile`, `wrappers/egrep`, `wrappers/fgrep`, `notes/ct02-the-default-syntax.txt`, `notes/ct02-evidence/px-scent-contract.txt`, `static-sums.txt`, `toolchain.txt` | the org's own | GPL-3.0-or-later + the wolf Training Data Permission | read (the build and test tooling, never `src/`), run (its pax-posture suite against pax's build) | `tools/mkscent`'s flags and checks; the wrappers installed byte for byte; the published differences and upstream rows the session witnesses; the Linux-side prerequisite |
| GNU grep 3.12 configured `--disable-perl-regexp`, built by scent's `tools/fetch-oracle` (tarball `2649b27c…` hashed twice, signature `155D3FC5…` verified) to the pinned binary `92b211f7…` in scent's oracle image (Ubuntu 24.04, glibc 2.39-0ubuntu8.9) | 3.12 | GPL-3.0-or-later (a program we run) | built and run, never read (no source file opened, no log printed) | the oracle of scent's full byte suite (`tools/pax-posture`), and of the session's 25 GNU rows (`notes/px64/gnu-rows.py`) |
| wolf 0.2.35, the release archive for x86_64-unknown-linux-gnu (`4cc4045b…`, read twice; its `wolf --version`, its bundled std `2386522e`, its `libwolf_rt.a`) | 0.2.35 | GPL-3.0 + the wolf Training Data Permission (the org's own) | run | building scent, as scent pins |
| Ubuntu 24.04 in the lane's own image (`docker.io/library/ubuntu@sha256:534baea6…`; libc6-dev 2.39-0ubuntu8.9, gcc 13.3.0, clang 18.1.3, binutils 2.42, QEMU 8.2.2, OVMF 2024.02, xorriso 1.5.6; `notes/px64/Containerfile`) | 24.04 | the packages' own (programs we run) | run, never read | every build and boot of the lane; scent's static link (the libc.a) |
| `strace(1)` 6.8 in the lane's image | — | (a program we run) | run on scent's own runs, never read | the census of scent's calls (`notes/px64/census.out`) |
| black-box Linux: the same binaries typed the same keys in a throwaway container (`tools/linux-tree`: kasumi's 7.2.8-1-cachyos under podman; CI's runner kernel under Docker) | — | GPL-2.0 (a program we run) | run, never read | `tests/mpx5-scent` A1 |

## px66: the partition table (GPT and MBR read, partitions as windows, a disk that boots)

No Linux kernel source (none of `block/partitions/`, `efi.c`, `msdos.c`,
nor any kernel's partition, boot or FAT code), and no source of
util-linux (sfdisk, libfdisk, blkid, lsblk), gptfdisk, dosfstools,
mtools, e2fsprogs or Limine was read. The layouts are the UEFI
specification's; Limine's installer and loader, the partitioners, the
FAT tools and Linux were run as black boxes. Limine's binary release
carries the installer's source (`limine.c`), which `tools/fetch-limine`
builds with the host's cc as before; it was not opened. Permissively
licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| UEFI Specification, chapter 5 "GUID Partition Table (GPT) Disk Layout" (§5.1; §5.2.1 the legacy MBR and its partition record, §5.2.2 OS types 0xEE and 0xEF, §5.2.3 the protective MBR, §5.3.1 the overview: LBA 1, the last LBA, the 16 KiB minimum array, the usable range, §5.3.2 the header and its validity tests and the backup's use, §5.3.3 the entry, table 5.7's type GUIDs, table 5.8's attributes) and Appendix A (a GUID's text: three little-endian fields, then eight bytes in order) | 2.10 (uefi.org/specs/UEFI/2.10, the HTML chapter, fetched 2026-10-23) | the UEFI Forum's (a specification) | read | `kernel/block` (every offset, check and order), `tools/mkgpt` (the writer), `kernel/boot_info`'s `struct limine_uuid` reading |
| Limine `USAGE.md` ("UEFI", "BIOS/MBR", "BIOS/GPT": a BIOS boot partition of at least 32 KiB, its number to `limine bios-install`; where `limine-bios.sys` and `limine.conf` may lie), `CONFIG.md` ("Location of the config file", the `boot()` resource), `FAQ.md` (the ESP as `/boot`) | v12.9.1 (the pinned release's tag, fetched from its repository) | BSD-2-Clause | read | `tools/mkdisk --gpt`'s layout, R-px66-2, R-px66-3 |
| Limine `PROTOCOL.md`: `struct limine_file` (`media_type`, `partition_index`, `mbr_disk_id`, `gpt_disk_uuid`, `gpt_part_uuid`, `part_uuid`; LIMINE_MEDIA_TYPE_*) and `struct limine_uuid` | limine-protocol `3a0526b700e356f0eac1b71a77697b3fd1c707a3` (as px00) | 0BSD | read | `kernel/boot_info`'s `module_media`, `module_partition`, `module_guid`; kmain_console's `boot:` line |
| Limine's installer, `limine bios-install IMAGE [N]` and `--help` | v12.9.1 (built by `tools/fetch-limine` from the release) | BSD-2-Clause (a program we run) | run, never read: measured, on a GPT image it refuses with no BIOS boot partition ("no BIOS boot partition specified or detected"), detects one by type when no number is given, and writes the MBR's boot code (bytes 1-422) and stage 2 from the partition's first sector, nothing else | `tools/mkdisk --gpt` (partition 3), R-px66-2 |
| man-pages `sfdisk(8)`, `sgdisk(8)` (`--dump`, `-v`), `mkfs.fat(8)` (`-F`, `-i`, `-n`, `-h`, `--offset`, `--invariant`, `--mbr`, `-S`), `fsck.fat(8)` (`-n`), `mcopy(1)` (`-m`, `-i IMAGE@@OFFSET`), `mmd(1)`, `mtools(1)`, `mtools(5)` (the drive's `offset`), `fstab(5)` (the spec field's `LABEL=`, `UUID=`, `PARTLABEL=`, `PARTUUID=`), `mount(8)`, `blkid(8)` (`-p -o export`, the tag names), `lsblk(8)` (`-b -o NAME,START,SIZE,PARTUUID`), `proc(5)` (`/proc/partitions`), `dumpe2fs(8)` (`-h`) | util-linux 2.39.3, gdisk 1.0.10, dosfstools 4.2, mtools 4.0.43 (the pages in user/disktools.pin's packages); man-pages 6.x | documentation | read | `tools/disktools`, `tools/mkdisk --gpt`, `tools/linux-part`, `kernel/fstab`'s spellings, `tests/mpx6-part`'s oracles |
| sfdisk, sgdisk, mkfs.fat, fsck.fat, mcopy, mmd, mdir (user/disktools.pin's Ubuntu 24.04 packages, by digest, in `docker.io/library/ubuntu@sha256:534baea6…`), blkid and lsblk (that image's util-linux) | as the row above | GPL-2.0 / GPL-3.0 (programs we run) | run, never read: measured, sgdisk reads only 128-byte entries, sfdisk reads 256-byte ones, sfdisk reads a protective MBR with no valid GPT as a DOS table of one type-ee entry, mtools honours SOURCE_DATE_EPOCH for its directory times (two runs give the same bytes) | the fixtures' and the boot disk's oracles, the ESP, the guest's blkid |
| black-box Linux: kasumi's 7.2.8-1-cachyos on QEMU (q35, TCG) with each image as its virtio disk (`tools/linux-part`), and mounting a not-clean ext2 (`tools/linux-blk`) | — | GPL-2.0 (a program we run) | run, never read: modules.builtin listed (virtio_blk) | every expected answer of `tests/mpx6-part` (recorded in `tests/mpx6-part.d/linux/`); measured, not guessed: `/proc/partitions`' layout and its size column (sectors / 2, rounded down), names by slot (vda64), 254:1-15 then 259:0 on in order, PARTUUIDs as blkid prints them (GPT lower case; MBR `ssssssss-nn`), a bad primary header reads as no table unless booted with `gpt` ("Primary GPT is invalid, using alternate GPT"), a bad backup is said ("Alternate GPT is invalid, using primary GPT"), entries of 256 bytes are never read, a 4096-byte-block device finds no table at LBA 1 of 512, lsblk's PARTUUID column is empty without udev, and a not-clean ext2 mounted read-write and unmounted stays not clean |
| QEMU's documented options: `-device virtio-blk-pci,drive=…,bootindex=0`, `logical_block_size=`, `physical_block_size=`, `-bios` | 8.2.2 (CI), 11.1.1 (kasumi), 11.1.2 (the maintainer's Mac) | GPL-2.0 (a program we run) | the author's own knowledge of the documentation; run | `tools/qemu-run --boot-disk`, the fourk row, the maintainer's lines |
| edk2's `edk2-x86_64-code.fd` as Homebrew's QEMU 11.1.2 ships it (sha256 `33090cc0…`), copied to kasumi for the playground's UEFI session | — | BSD-2-Clause-Patent (firmware we run) | run | `notes/px66/play/boot.sh` |
## px65: the pins at 0.2.35, and boreutils' new utilities

No Linux kernel source, no other kernel's, no glibc's, musl's, shell's or
coreutils' or gnulib's source was read; nothing of GNU coreutils was run
(the sessions run boreutils' binaries on both sides). The org's own
repositories were read as the maintainer's code and records; what each
gave is below. Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| wolf-lang `cf0c13d3` (`v0.2.35`, the org's own): `CHANGELOG.md`'s 0.2.35; `crates/wolf_driver/src/main.rs`' version identity (D57: `WOLF_RELEASE` and `WOLF_COMMIT`); `xtask/src/main.rs`' `version_stamp` and `release_stamp`; `rust-toolchain.toml`; `crates/wolf_rt/src/task/stack.rs` (the main thread's guard through `pthread_getattr_np`, `install_overflow_handler`, `overflow_handler`) | 0.2.35 | GPL-3.0 + the wolf Training Data Permission | read | the pin's facts; R-px65-2's stamp (`tools/mkwolf`); why sigwolf's fault-ignore row and every new utility's start read `/proc/self/maps` (R-px65-5) |
| wolf 0.2.35's linux x86-64 release archive (`4cc4045b…`, release 421613621; the API read twice, two downloads hashed twice each on kasumi) and its `libwolf_rt_none.a` (`nm -S`: the new `__wolf_rt_list_reserve`, 76 bytes) | 0.2.35 | the org's own | run | every kernel and wolf program built here; the kernels' 80 bytes |
| wolf-interp `v0.1.56` (`28547b4`, the org's own): `CHANGELOG.md`, `Cargo.toml`, `rust-toolchain.toml`, `.github/workflows/release.yml`'s musl row, `ci/musl-build.sh`, `ci/musl-check.sh`; the release's glibc and musl archives (`ad703550…`, `6303b47a…`, each downloaded and hashed twice; the musl binary `c0ac0888…` read twice) | 0.1.56 | GPL-3.0-or-later + the wolf Training Data Permission | read; run | `user/lupin.pin`, `tools/mklupin`'s release mode (R-px65-1); `tests/mkw`'s lupin |
| wolf-std `78b9d3c` (sc72, the org's own): `CHANGELOG.md`, the log since `2386522e` | sc72 | the org's own | read | `user/std.pin`, the three probes' std |
| boreutils `575dc7b` (the org's own): `README.md` (the readiness table, the building section), `notes/bu30-the-small-file-tools.md`, the log since `12de639`, the names of `src/*.lu` (not their text), `wolf-toolchain.toml` | bu30, bu31 | GPL-3.0-or-later + the wolf Training Data Permission | read | the fourteen new utilities, their refusals by name (bare `sync`, `sync -f`, `truncate -o`, FIFOs, `mkfifo -Z`, `shuf --random-source`) |
| lobo `49ed870` and `v0.1.5` (the org's own): `wolf-toolchain.toml` at both, the log since `v0.1.5`, `src/main.lu`'s master or one process (`master_main`, `serve_main`), `src/config/userconf.lu`'s `hands_drop`, `default_drops`, `drop_host`, `default_ids_host`, `src/config/table.lu`'s `user` directive text | trunk, 0.1.5 | the org's own | read | why lobo serves as a master and a hand in the container and as one process on PAX: the account files (R-px65-4) |
| pelt `70eec14`, lope `e6f623c`, aspen `3692cf5` (the org's own): their `wolf-toolchain.toml`s and logs since the old pins; pelt's `tests/diff/` fixtures compared byte for byte with `user/console/fork/`'s copies (the same at `70eec14`) | trunks | the org's own | read | the pins and what moved |
| the author's own knowledge of the man-pages project and POSIX.1-2024: `mkfifo(1)`, `link(1)`, `unlink(1)` and `(2)`, `truncate(1)`, `sync(1)`, `mktemp(1)`, `realpath(1)`, `tty(1)`, `base64(1)`, `base32(1)`, `comm(1)`, `join(1)`, `tsort(1)`, `shuf(1)` (their GNU diagnostics' shape), `proc(5)`'s `status` and `maps`, `pthread_getattr_np(3)`, `sigaction(2)`, `sigaltstack(2)`; RFC 4648 (base64 and base32) | — | documentation | the author's own knowledge; every row measured (the sessions on both sides, `tests/mpx5-bore.d/rows.py`, the encodings computed by Python's `base64`) | the sessions' keys and their witness rows |
| black-box Linux: the same binaries typed the same keys in a throwaway container (`tools/linux-tree`; kasumi's 7.2.8-1-cachyos under podman, CI's runner under Docker); `strace(1)` 6.8 over the fourteen utilities (`notes/px65/census.sh`) and over sigwolf's start; two static probes (`notes/px65/probes/`) on Linux and PAX; real root's guest (kasumi's own kernel image under QEMU, `notes/px48/linux-vm.sh`, px50's and px52's vmjob) for the recordings | — | GPL-2.0 (programs we run) | run, never read | `tests/mpx5-bore`; the census; the `~X:` finding; the recordings at the new pins |
| Ubuntu 24.04 in the lane's own image (`docker.io/library/ubuntu@sha256:534baea6…`, px64's packages and zstd for `tools/fetch-busybox`; `notes/px65/Containerfile`) and px57-rust (Rust 1.97.1 and the musl target, as px57 made it) | 24.04 | the packages' own (programs we run) | run, never read | every build and boot of the lane; the dev compiler's two builds |
| px66's playground recipe (`notes/px66/play/`: `assemble.sh`, `boot.sh`, `session.py`, the org's own) and edk2's `edk2-x86_64-code.fd` as Homebrew's QEMU 11.1.2 ships it on nomad-1 (sha256 `33090cc0…`, copied to kasumi and read twice) | px66 | the org's own; BSD-2-Clause-Patent (firmware we run) | read; run | `notes/px65/disk/`: the playground disk at the new pins, booted under SeaBIOS and with the code file as a read-only pflash |

## px67: root on the disk (`root=`, the system installed onto ext2, mount(2) and umount2(2), the end)

No Linux kernel source (none of `init/do_mounts*.c`, `fs/namespace.c`,
`fs/ext2`, `fs/ext4`, `block/partitions/`), no other kernel's mount,
boot or file-system code, and no source of any init system or mount
tool (systemd, sysvinit, util-linux's mount and umount, busybox), of
e2fsprogs, dosfstools or Limine was read. Linux, its ext4 driver
mounting ext2, the guest's own mounts, e2fsprogs and Limine were run as
black boxes. Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| man-pages `mount(2)` (the flags: MS_RDONLY, MS_NOSUID, MS_NODEV, MS_NOEXEC, MS_REMOUNT, MS_BIND, MS_MOVE, the propagation flags; the magic number in the top half; the errors), `umount2(2)` (MNT_FORCE, MNT_DETACH, MNT_EXPIRE, UMOUNT_NOFOLLOW; the errors), `mount(8)` (remount, `-o ro`), `fstab(5)` (a line for `/`, the options, `tmpfs`), `proc_pid_mounts(5)` and `proc_pid_mountinfo(5)` (the two tables' fields, the escapes of a space, a tab, a newline and a backslash), `bootparam(7)` (`root=` by name and by number, `rootfstype=`, `ro` and `rw`, `rw` the default), `statfs(2)`, `statvfs(3)` (ST_RDONLY, ST_RELATIME), `reboot(2)`, `pause(2)`, `kill(2)`, `signal(7)` | man-pages 6.x, kasumi's (CachyOS) | documentation | read | `kernel/files`' mount_call, umount_call and mounts_of, `kernel/fstab`'s `root=` and its `/` and `tmpfs` lines, `kernel/user`'s end, `user/elf/mounts.c` |
| `systemd-system.conf(5)` (DefaultTimeoutStopSec= 90 s) and `systemd-shutdown(8)` (what a distribution's last step does: the remaining processes killed, the file systems unmounted or remounted read-only) | systemd 258, kasumi's man pages | documentation (LGPL-2.1 program, read only its pages) | read | R-px67-4, the end's order |
| the uapi headers in the refs clone for numbers only: `linux/mount.h` (MS_*, MNT_*), `asm-generic/signal.h` (SIGTERM 15, SIGKILL 9, SIGCONT 18) | the refs clone's | GPL-2.0 WITH Linux-syscall-note | read, numbers | `kernel/files`, `kernel/user` |
| Limine `CONFIG.md`: `timeout` (0 boots the entry at once and shows no menu; any key during a non-zero timeout reveals it), `quiet`, `serial`, `default_entry`, an entry's `cmdline` and `module_path` | v12.9.1 (the pinned release's tag, fetched from its repository) | BSD-2-Clause | read | R-px67-2 (a rescue entry is reachable only with a timeout), `tools/mkdisk --root`'s configuration |
| the ext2 layout documentation (`Documentation/filesystems/ext2.rst`, `ext4/super.rst`: `s_state`, `s_mnt_count`, `s_mtime`, `s_wtime`) | as px63 | GPL-2.0 (documentation) | read | `kernel/ext2`'s `remount` |
| black-box Linux: kasumi's 7.2.8-1-cachyos on QEMU (q35, TCG, no initramfs) with its root on an ext2 partition of a GPT disk and `user/elf/mounts.c` as its init (`tools/linux-root`), and once with an initramfs as its root (`--initrd`) | — | GPL-2.0 (a program we run) | run, never read | every expected answer of `tests/mpx6-root` (recorded in `tests/mpx6-root.d/linux/`); measured, not guessed: the root's source reads `/dev/root`; the kernel mounts devtmpfs at /dev itself (`rw,nosuid,noexec,relatime`); /proc/mounts is a link to `self/mounts` (11 bytes) and Arch's /etc/mtab `../proc/self/mounts`; a remount read-only refused EBUSY while a file is open for writing, EINVAL on a directory that is no mount's root; a volume's unmount EBUSY with a working directory or an open file in it, then 0, then EINVAL; a target that is a file ENOTDIR, a missing one ENOENT, a source that is no block device ENOTBLK, an unknown type ENODEV; a flag outside umount2's four EINVAL; root's `umount2("/")` answers 0 and remounts `/` read-only; a user's mount, remount and umount2 EPERM, umount2's missing path ENOENT first; a remount read-write counts as a mount; `root=PARTUUID=` in either case, `root=UUID=` refused by the kernel alone (a panic), a root mounted not clean read-write with `warning: mounting unchecked fs, running e2fsck is recommended` and left not clean by its clean unmount; with an initramfs the root reads `rootfs / rootfs rw,size=…,nr_inodes=…`; with neither `ro` nor `rw` on the command line the root is mounted read-only (`VFS: Mounted root (ext2 filesystem) readonly`, `ro,relatime`), where bootparam(7) says `rw` is the default (the kernel's answer is the one served); `root=0xfe02`, `root=fe02` and `root=254:2` each mount vda2 (254:2) |
| kasumi's own `/proc/self/mountinfo` and `/proc/self/mounts` (CachyOS, systemd) | — | — | read (a running system's tables) | the flags a distribution's init gives /proc, /sys, /dev and /tmp |
| e2fsprogs 1.47.0 (`e2fsck -fn`, `dumpe2fs -h`, `debugfs`), from the image tools/e2fs pins | as px63 | GPL-2.0 (programs we run) | run, never read | R4, R5, R7, R8, the crash row's classes |

## px70: framebuffer renditions, editing, palette and keypad

No kernel or terminal-emulator source was read. The references are public
interfaces, this repository's existing probes, and repeated black-box runs.

| source | version | how | used for |
|---|---|---|---|
| `console_codes(4)` on kasumi, read 2026-10-24 | installed man-pages | documentation | CSI capacity, editing controls, SGR/reset names, OSC P/R syntax |
| Linux VT under QEMU, `/dev/tty1` and `/dev/vcsa1`, public `linux/vt.h` and `linux/kd.h` ioctl interfaces | 7.3.0-4-cachyos, image SHA256 `bd5b90c3ba79ce78839b77a0f5b4f798738d62dbc06f8b1be3e0eaf83e1a92fe`; QEMU 11.1.2 | run, never implementation source | two repeats of px59's probes; fresh rendition, editing and 19,683 RGB samples; timed pixels for blink, cursor and all sixteen palette entries; 87 keyboard cases including Alt decimal and AltGr Unicode entry; evidence in `notes/px70/` |
| PAX's own px58/px59 probes, renderer, keyboard and comparison harness | trunk `54570380` | read and extended | unchanged baseline and new differential rows |

VCSA comparisons normalize the font and palette indices; exact pixel
comparisons use the independent `tools/screen-ref` renderer. The measured VGA
VT's 9x16 ROM font and DAC conversion are not PAX's 8x16 framebuffer font and
24-bit pixels. `GIO_CMAP` returned the default global palette even after OSC P;
the per-console change was verified by timed screenshots, not that ioctl.

## px68: the journal for `/` (ext3: has_journal, the log, its commits, revocations, the replay)

No kernel's source: none of Linux's `fs/jbd2`, `fs/ext3`, `fs/ext4` or
`fs/ext2`, no other kernel's journal or file-system code, and no
e2fsprogs source (`lib/ext2fs`, `e2fsck/`, `debugfs/`, `misc/mke2fs`).
`Documentation/filesystems/journalling.rst` (jbd2's in-kernel API) and
`ext3.rst` were not opened: only the on-disk layout's pages below.
e2fsprogs, QEMU and Linux 7.3.0 were run as black boxes. Permissively
licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| `Documentation/filesystems/ext4/journal.rst` (the journal's layout: every field big-endian; the block header and its types; the v1 and v2 superblocks: s_blocksize, s_maxlen, s_first, s_sequence, s_start, the feature words and their bits, s_uuid; descriptor blocks, the 8-byte tag without CSUM_V3 or 64BIT, its flags ESCAPE, SAME_UUID, DELETED and LAST_TAG, the 16-byte UUID after a tag without SAME_UUID; data blocks and the escape rule; revocation blocks, r_count and their 32-bit block numbers, "used to prevent replay of a block in an earlier transaction", and "any block being added to a transaction will cause the removal of all existing revocation records for that block"; the commit block, h_commit_sec and h_commit_nsec; data=ordered, data=journal and data=writeback as prose; the checkpoint) | the refs clone's (`wolf/refs/repos/linux`, a sparse checkout of the allowed paths) | GPL-2.0 (documentation) | read | `kernel/journal`, `tools/mkjournal`, `tools/jorder` |
| `Documentation/filesystems/ext4/super.rst` (COMPAT_HAS_JOURNAL 0x4, INCOMPAT_RECOVER 0x4 and INCOMPAT_JOURNAL_DEV 0x8, s_journal_uuid, s_journal_inum, s_journal_dev, s_last_orphan, s_jnl_blocks; the names of every INCOMPAT and RO_COMPAT bit; the default mount options' journal modes), `special_inodes.rst` (inode 8, the journal), `inodes.rst` and `blockmap.rst` as px63 (inode 8's blocks) | as above | GPL-2.0 (documentation) | read | `kernel/ext2`'s has_journal, needs_recovery and the features' names; `tools/mkjournal`'s reader of inode 8 |
| man pages `mke2fs(8)` (`-t ext3`, `-J size=`, the journal's default size by the volume's), `debugfs(8)` (`logdump`, `ssv`, `ffb`), `e2fsck(8)` (`-fy`, `-fn`, recovering a journal), `dumpe2fs(8)` (`Journal sequence`, `Journal start`, `Total journal blocks`) | e2fsprogs 1.47.0's | documentation | read | `tools/mkdisk --journal`, `notes/px68/oracle.sh`, the suite's rows |
| e2fsprogs 1.47.0 (`mke2fs -t ext3`: has_journal ext_attr resize_inode dir_index filetype sparse_super large_file, a journal of 1024 blocks under 32768 blocks of 4 KiB and 4096 for 448 MiB, a v2 superblock with no journal feature, sequence 1, start 0, the fs UUID as s_uuid, the journal in a few runs with its indirect blocks between; `e2fsck -fy`'s replay of journals tools/mkjournal wrote: a revocation of the tag's own transaction or a later one suppresses it, the revoke feature flag not needed, an escaped block's magic restored, a torn commit and an open transaction dropped, a log that wraps followed, the log left at s_start 0 and s_sequence one past the end's; `debugfs logdump`; `dumpe2fs -h`), from the image tools/e2fs pins | as px63 | GPL-2.0 (programs we run) | run, never read | the replay's rules (`notes/px68/oracle.sh`, `tests/mpx6-journal` J4), J1, J3, the crash row's host repair |
| black-box Linux: kasumi's installed 7.3.0-4-cachyos image (the running 7.2.8's was gone after the 2026-10-24 upgrade) on QEMU (q35, TCG), its root on an ext3 partition (`tools/linux-root --fstype ext3`, `user/elf/mounts.c` its init) | — | GPL-2.0 (a program we run) | run, never read | measured, not guessed (notes/px68/guest.sh, `tests/mpx6-journal.d/linux/`, `tests/mpx6-root.d/linux/`): `mounting ext3 file system using the ext4 subsystem`, `mounted filesystem … r/w with ordered data mode`, `VFS: Mounted root (ext3 filesystem)`; /proc/mounts names it `ext3`, and `ext2` when `rootfstype=ext2` asks (the journal still used); a power cut leaves `clean` with needs_recovery (the state's VALID bit kept while mounted) and the log at a start; the next boot's one line `recovery complete`; a clean unmount clears needs_recovery and empties the log; an incompatible bit it does not know: `Couldn't mount because of unsupported optional features (80000000)`, then `couldn't mount as ext3 due to feature incompatibilities`, mount(2) -EINVAL; e2fsck -fy after its replay fixes the free counts the kernel keeps lazily |
| QEMU's trace events `virtio_blk_handle_write`, `virtio_blk_handle_read`, `virtio_blk_req_complete` (`-trace`, the log backend, `-D`), their names read from `-trace help` | QEMU 11.1.2 (kasumi), 8.2.2 (Ubuntu 24.04's package, the CI runner's; the names found in its binary) | GPL-2.0 (a program we run) | run, never read | `tools/jorder`: the order the journal's writes and FLUSHes reached the disk (J2, J4) |
| the OASIS VIRTIO specification 1.2 §5.2.6 (VIRTIO_BLK_T_FLUSH) | as px63 | OASIS | read | the commit's two FLUSHes and the checkpoint's |

## px79: block device nodes, the block ioctls and a second disk (pax#144)

No kernel's source: none of Linux's `block/` (`ioctl.c`, `partitions/`,
`bdev.c`, `genhd.c`), `drivers/block/virtio_blk.c`, `fs/block_dev.c`,
devtmpfs or sysfs, and no other kernel's block layer; no source of
util-linux (`lsblk`, `blkid`, `sfdisk`, `partx`), of a libc or of any
partitioner. The ioctls' numbers and structures are the uapi headers'
(the refs clone's allowed paths); every answer and width is the Linux
guest's, run as a black box with the lane's probe. Permissively licensed
kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| `include/uapi/linux/fs.h` (BLKROSET to BLKGETDISKSEQ, their `_IO`, `_IOR` numbers), `include/uapi/linux/blkpg.h` (BLKPG, `struct blkpg_ioctl_arg`, `struct blkpg_partition`, BLKPG_ADD_PARTITION, BLKPG_DEL_PARTITION, BLKPG_RESIZE_PARTITION), `include/uapi/linux/hdreg.h` (HDIO_GETGEO, `struct hd_geometry`) | the refs clone's (`wolf/refs/repos/linux`, a sparse checkout of the allowed paths) | GPL-2.0 WITH Linux-syscall-note | read, numbers and layouts only | `kernel/files`' `blk_ioctl`; `user/elf/nodes.c` includes the same headers from the build container's linux-libc-dev |
| man pages `ioctl(2)`, `ioctl_list(2)` (the block requests and who may ask them: CAP_SYS_ADMIN for BLKRRPART, BLKPG, BLKFLSBUF), `sd(4)` (HDIO_GETGEO, BLKGETSIZE, BLKRRPART), `open(2)` (O_EXCL on a block device without O_CREAT: an exclusive open, EBUSY when in use; O_DIRECT), `lseek(2)`, `read(2)`, `write(2)`, `pread(2)`, `fsync(2)`, `sendfile(2)`, `splice(2)`, `copy_file_range(2)`, `mount(2)`, `proc(5)` (/proc/partitions), `sysfs(5)` (/sys/block, /sys/class, /sys/dev), `mknod(2)` | man-pages 6.x on kasumi | documentation | read | the calls' shapes; what the guest was asked |
| the OASIS VIRTIO specification 1.2 §5.2.3 and §5.2.4 (VIRTIO_BLK_F_GEOMETRY, bit 4; `struct virtio_blk_geometry` at 16: le16 cylinders, u8 heads, u8 sectors) and §4.1.2 (PCI discovery: every function with device id 0x1001 or 0x1042, in the bus's order) | as px63 | OASIS | read | kernel/vblk's several disks and the geometry HDIO_GETGEO answers |
| black-box Linux: kasumi's installed 7.3.0-4-cachyos image on QEMU 11.1.2 (q35, TCG), one to three virtio-blk disks (`tools/linux-nodes`, the probe `user/elf/nodes.c` and boreutils' `ls` run unmodified, pelt as the shell) | — | GPL-2.0 (a program we run) | run, never read | every expected answer of `tests/mpx6-nodes` (recorded in `tests/mpx6-nodes.d/linux/`; the lane's measurements in `notes/px79/guest.sh`): the nodes `brw-------` 0:0 with no udev, st_blksize 512, size 0; 254:0, 254:16, 254:32 for three disks in PCI slot order, 254:N to vdX15 and the extended major 259 from 0 for the rest across disks (vdb16 259:113 after vda's 113), the lowest free minor again after a rescan; /proc/partitions' and /sys's values (a disk's `dev`, `size`, `ro`, `removable`; a partition's `dev`, `start`, `size`, `partition`, `ro`; `/sys/block/vda` and `/sys/class/block/<name>` links into /sys/devices); each ioctl's value and the bytes it writes (BLKGETSIZE64 and BLKGETSIZE 8, BLKSSZGET, BLKPBSZGET, BLKIOMIN 512 in 4, BLKIOOPT, BLKALIGNOFF, BLKDISCARDZEROES 0 in 4, BLKROGET 1 on a read-only disk, BLKBSZGET 4096 or 512 (the largest block the size is a whole number of), BLKROTATIONAL 1 in 2, BLKGETDISKSEQ 1, 2, 3, HDIO_GETGEO the device's geometry, QEMU's 16/63 by default and its `cyls=`, `heads=`, `secs=` when set, the start as the unsigned long); TCGETS, FIONREAD, FS_IOC_GETFLAGS ENOTTY; lseek bounded to the size (EINVAL past it and before 0, SEEK_DATA EINVAL); reads short across the end and 0 at it; writes short across the end and ENOSPC at and past it; a read-only disk's writes EPERM even of no bytes, its O_RDWR open allowed; O_DIRECT, O_TRUNC accepted, O_DIRECTORY ENOTDIR; BLKRRPART EBUSY with a partition open or mounted, 0 with the disk open, EINVAL on a partition; O_EXCL against O_EXCL and against a mount, both ways and across the disk and its partitions; BLKPG: an overlapping range and a number in use EBUSY, a range past the end EINVAL, an open or mounted partition's deletion EBUSY; mount(2) from a node, ENOTBLK for /dev/null, ENOENT for a bare name |
| QEMU 11.1.2's virtio-blk-pci device properties `cyls`, `heads`, `secs` | kasumi's | GPL-2.0 (a program we run) | run | the geometry row (the guest answers the device's) |
| e2fsprogs 1.47.0 (`e2fsck -fn`), from the image tools/e2fs pins | as px63 | GPL-2.0 (programs we run) | run, never read | N6, N10, N14 |

## px69 — disk tools

- **UEFI Specification 2.10**, chapter 5, §§5.2–5.3 (protective MBR,
  GPT headers, entry arrays, CRCs and backup-first updates); Appendix A,
  Tables A.1–A.2 (GUID layout and text). `user/disktools/paxgpt` and its
  independent sfdisk/sgdisk differential.
  <https://uefi.org/specs/UEFI/2.10/05_GUID_Partition_Table_Format.html>
  <https://uefi.org/specs/UEFI/2.10/Apx_A_GUID_and_Time_Formats.html>
- **Microsoft FAT Specification, 30 August 2005**, §§3.3–3.6 (FAT32
  BPB, geometry and backup), §4 (allocation table), §5 (FSInfo), §6
  (directories and timestamps), §7.1–7.3 (VFAT order, checksum, UTF-16
  names and padding), pages 11–16 and 17–33. The published specification,
  not filesystem-tool source; retrieved from
  <https://academy.cba.mit.edu/classes/networking_communications/SD/FAT.pdf>.
  `user/disktools/paxfat` preserves UTF-16 surrogate pairs; the test names
  mtools 4.0.49's observed supplementary-character truncation separately.
- **Black-box programs:** e2fsprogs 1.47.4, dosfstools 4.2, mtools 4.0.49,
  util-linux 2.42.4 and GPT fdisk 1.0.10, copied with their binary libraries
  into the lane's Ubuntu build container; their implementation source was
  not opened. Geometry, alias choice and diagnostic behaviour were measured.
  The maintained `tools/mkgpt` is the seed-compatibility reference;
  sfdisk and sgdisk supply the independent partition-table checks.
- **Linux ext4 on-disk documentation**, sparse allowed-documentation checkout
  at `3b7cab693ba2bab63774bf5b988e8a61b2ef0f32`:
  `Documentation/filesystems/ext4/{overview,blocks,super,group_descr,bitmaps,
  inodes,blockmap,directory,special_inodes}.rst`. The ext2-compatible
  superblock and 32-byte group descriptors, 256-byte inode records and
  timestamp epochs, classic directory records, sparse-super placement,
  bitmaps, reserved inodes and direct/single/double-indirect block maps.
  Only documentation was read, never filesystem or kernel implementation.
  `paxext2` leaves `has_journal` clear and does not claim resize-inode,
  indexed-directory, extent or metadata-checksum features.

- **Limine 12.9.1 release**, archive SHA256
  `5cdebc518daa3af30b22c2322ba0dba2e0e2046fa8b087b9e13071b8dbcdcff4`.
  The existing fetch/build recipe consumes the archive unopened. The
  `tools/mklimine-static` cc wrapper adds only `-static -no-pie`; no source
  is opened or patched. On the Ubuntu baseline, the original dynamic
  executable is SHA256 `0b90e40a23889a44b354608259bdbfd1ff14eef7e22643dc331ad931e036a324`,
  the static executable `dad435d4797b51ad41f223e64c1b9d4f7f58800bf06f5576789774909603a700`.
  Both write identical disk bytes on Linux; the latter runs unchanged on
  PAX and writes the same bytes through `/dev/vda`.
- **Linux 7.3.0-4-cachyos and GNU findutils 4.9.0**, binaries only:
  the guest mounts both full installed-tree images read-only and `find
  -printf` returns 238 identical rows. No GNU or kernel implementation
  source was read. Linux strace records the formatters and the static
  Limine installer's calls; evidence is under `notes/px69/`.


## px71 — guided installer

- PAX's own px69 formatter interfaces, fixtures and `notes/px69/report.txt`;
  px79's block-node/ioctl/mount-table evidence; px68's root-journal report;
  `docs/BOOT.md`, `docs/CENSUS.md`, and the maintained `tools/e2tree` oracle.
  The new code orchestrates those formatters and does not rewrite them.
- Wolf 0.2.35 (`cf0c13d3`) `spec/04-abi.md`, `spec/11-os.md` and
  `spec/prelude.json`, plus the Wolf guide. The raw membrane follows the
  x86-64 syscall/structure ABI used by PAX's own probes and play membrane:
  open, close, ioctl, fstat, fsync and getrusage. Third-party kernel, libc,
  shell, formatter, bootloader and installer implementation sources were
  not read.
- Black-box binaries: Ubuntu-baseline static Limine 12.9.1, sgdisk/sfdisk,
  dosfstools/mtools and e2fsprogs; QEMU TCG with SeaBIOS and OVMF. In
  particular, the log-reservation proof is a byte diff before/after
  `bios-install DEVICE 3`, a Linux/PAX equality check, and boots after
  writing the log last, not an inference from Limine source.
- The project's own pack repository, pinned at
  `91d93ac38b1e99933ed15818bedc79d37eb98738`, source archive SHA256
  `7cf8a1ed814ba26889840b16d9004951562a2304c416181f98b3e7bce217b73e`.
  Its build flags (including the existing WOLF_MIDEND=0 setting) were
  followed. The source archive includes pack's original GPL licence and
  training-data policy and is installed beside the optional binary.
  Pack is static glibc on Ubuntu 24.04, not a musl build.

## px80: the linker respin (pax#172)

No kernel source and no libc source was read; the kernel is unchanged in
this lane. LLVM's release tarball was compiled, never read: the lane's
only contact with its tree was `tar` extracting five top-level
directories, `cmake` and `ninja`, and copying out the licence files the
bundle carries. lld's behaviour was observed only as a black box, its
argv and its answers (the control on the kernel, the links of hello,
loop and signal, the compressed-section rows). Permissively licensed
kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| `llvm-project-18.1.8.src.tar.xz` (LLVM's GitHub release `llvmorg-18.1.8`; sha256 `0b58557a…db2f2a`, 132,067,260 bytes, signed by LLVM's release key `474E2231 6ABF4785 A88C6E8E A2C794A9 86419D8A`, the key list at releases.llvm.org) | 18.1.8 | Apache-2.0 WITH LLVM-exception | compiled, never read (`notes/px80/build-lld.sh`); its `LICENSE.TXT` files and the Support library's third-party notices copied into the bundle | the dev ISO's static `ld.lld` |
| Homebrew's `llvm@18` formula (formulae.brew.sh's JSON) | 18.1.8 | BSD-2-Clause (the formula) | read: its published sha256 of the same tarball | a second, independent record of the tarball's digest |
| Alpine 3.20 (`alpine@sha256:d9e853e8…`) packages: clang17 17.0.6-r1, lld 17.0.6-r0, libc++ and compiler-rt 17.0.6-r1, llvm-libunwind 17.0.6-r1, llvm17 17.0.6-r2 (its `llvm-objcopy`), musl-dev 1.2.5-r4, zlib-static 1.3.2-r0, zstd-static 1.5.6-r0, cmake 3.29.3-r0 | as listed | as each package's | run: the build environment (`notes/px80/Containerfile.lld`); musl-dev's CRT and `libc.a` as shipped (zlib-compressed debug sections), decompressed by `llvm-objcopy` | the build; the compressed-sysroot rows; the bundle sysroot's provenance |
| Ubuntu 24.04 `lld-18` 1:18.1.3-1ubuntu1, `clang-18`, binutils 2.42 (px65's container, `notes/px65/Containerfile`) | as listed | Apache-2.0 WITH LLVM-exception; GPL-3.0 | run | row (c) of the control, every link's reference in `notes/px80/lld-wrap`; the zlib and zstd test objects (`ld.lld -r --compress-debug-sections=`) |
| the static lld 17.0.6 and the bundle's `cc` and sysroot, from the playground's `pax-dev.iso` (px65's, `02f979be…`) | 17.0.6 | as px60 | run, each file held to `user/wolf-link.sums` twice | row (a) of the control; the bundle's unchanged members |
| Rust 1.97.1 (px57-rust) | 1.97.1 | MIT OR Apache-2.0 | run: cc rebuilt to its recorded bytes; its musl target's `libunwind.a` as shipped; its `share/doc/rust` licences copied into the bundle | W0 link; the provenance row; the bundle's licences |
| musl 1.2.5's release tarball (musl.libc.org, its `.asc` against `musl.pub`) | 1.2.5 | MIT | its `COPYRIGHT` member alone extracted; no source member opened | the bundle's licence for the sysroot and for the musl inside `ld.lld` and `cc` |
| zlib 1.3.2's and zstd 1.5.6's release tarballs (zlib.net, held to Alpine 3.20's APKBUILD sha512; GitHub's `facebook/zstd` release, its `.sha256`) | 1.3.2, 1.5.6 | Zlib; BSD-3-Clause | the `LICENSE` member alone extracted | the bundle's licences for the compression code inside `ld.lld` |
| GnuPG 2.4.9 (kasumi), in a scratch keyring | 2.4.9 | GPL-3.0 | run | the two signature checks |

## px81: friendly pelt at the consoles

Pelt launch trunk `0b5eaa5394667c485de3a134f771c87024b68a3c` was read
twice with `git ls-remote`. Only its `wolf-toolchain.toml`,
`docs/FRIENDLY.md`, `docs/KEYS.md` and typed session inputs/expectations
were consulted. No shell implementation, kernel, libc, grep, filesystem,
bootloader or installer implementation from another project was read.
Pelt is built unmodified by `tools/mkpelt` with its own wolf 0.2.35 pin.

The typed fixture follows sh28's Alt-dot, sh29's history suffix, sh30's
command/quote/shadow and sh31's Space abbreviation and history events.
Default suggestions use SGR90 and resolving commands the default foreground.
The separate custom palette `command=green:shadow=brblack+dim` exercises
SGR2 explicitly, without changing the shipped defaults. PAX's own px70
console rows are the framebuffer attribute reference. `stty` is the
already-pinned BusyBox binary, used black-box for the explicit resize.
A small original C probe reads TIOCGWINSZ through its public ioctl ABI, since
BusyBox stty prints a diagnostic instead of dimensions at0x0.

`tools/census/inside/pins.sh` now records this pelt launch tree; C4 in
`tests/census` compares it with `user/pelt.pin`. Neither a later upstream
commit nor a network failure changes this deterministic identity check.
## Offline ext2/ext3 checker

- Dave Poirier, *The Second Extended File System: Internal Layout*,
  https://www.nongnu.org/ext2-doc/ext2.html — superblock, group descriptor,
  inode, bitmap and directory-entry layouts (chapters 3–4).
- e2fsck(8), https://man7.org/linux/man-pages/man8/e2fsck.8.html — offline
  operation, report-only/preen/yes modes and exit statuses. e2fsprogs
  1.47.0 binaries are the black-box repair oracle; the corpus retains
  each prompt and finding rather than editing a golden answer.
- The published JBD2 on-disk journal layout, already recorded for the
  kernel journal above; PAX's own `kernel/journal/journal.lu` and the
  unchanged thirteen-case replay corpus are the replay reference.
- open(2)'s Linux `O_EXCL`-without-`O_CREAT` block-device rule, and the
  Linux x86-64 syscall ABI, for exclusive offline access. No libc source.

No Linux kernel, e2fsprogs, util-linux, busybox or other filesystem-tool
implementation source was consulted. Malformed-directory salvage remains
an explicit unsupported row, not an inferred or copied algorithm.

The rescue monitor follow-up uses QEMU's published QMP specification,
https://www.qemu.org/docs/master/interop/qmp-spec.html: greeting,
`qmp_capabilities`, command IDs, responses and asynchronous events. The
fixture acknowledges `quit` and retains its connection until closure;
it does not infer command consumption from a successful socket write.
No QEMU implementation source was read.

## as02b: the kernel's assembler seam and the clef package

No kernel source, no libc source, no shell, grep, filesystem-tool or
bootloader source was read. No assembler's, disassembler's or opcode
database's source was read: GNU as was run as a black box, its objects
compared by clef's own structural rule. The org's own repositories were
read and cited: wolf-lang (the seam: `crates/wolf_driver/src/asm.rs`, the
freestanding runtime's lookup in `crates/wolf_driver/src/main.rs`, `cargo
xtask rt-none` in `xtask/src/main.rs`) and clef (`notes/as01*`, its
`tools/` gates, the `notes/as01/seam/` controls, `tools/elf.py`).
Permissively licensed kernels: none consulted.

| source | version | licence | how | used for |
|---|---|---|---|---|
| clef (`wolffe-lang/clef`, `user/clef.pin`) | `996a3ccd` (as01's merge) | GPL-3.0-only with the wolf Training Data Permission | built (`tools/mkclef`; clef's own line, native tier, static); its census sources copied as the corpus; its `tools/elf.py` run; its as01 driver shims run as controls | the package, the qualification's corpus and oracle comparison, item 3's 0.2.35 control |
| wolf-lang | `9f2cff44` (as02a's merge, wolf-lang#957) | GPL-3.0 with the wolf Training Data Permission | built from source (`tests/kernel-as.d/wolf.pin`, `tools/fetch-wolf`'s source shape), `--version` `wolf 0.2.35+dev.9f2cff44` | the seam wolf: `--assembler` / `WOLF_AS` |
| wolf 0.2.35 release archive (`4cc4045b…`, kernel/wolf.pin) | 0.2.35 | as wolf-lang | run; its `libwolf_rt.a` (`9efc68e1…`) linked into the package, its `libwolf_rt_none.a` (`6b9c4852…`) staged beside the seam wolf | the image's compiler and runtime |
| GNU binutils 2.42 (`as`), Ubuntu 24.04 `2.42-4ubuntu2.10` (clef's `ci/oracle-lock.json`, by sha256); CI: the runner's 2.42 | 2.42 | GPL-3.0 | run (`as --64 -o OUT SRC`) | the GNU-as kernels, the qualification's oracle objects |
| clef's pinned images (`localhost/clef-oracle:bce39162bc0b1e5e`, `localhost/clef-integration:52846d3b65aeafca`: Ubuntu 24.04 by digest, gcc 13.3, libc6-dev 2.39-0ubuntu8.9, clang and lld 18.1.3, QEMU, OVMF; every package by sha256) | as locked | as each package's | run (built by clef's `tools/in-container` and `tools/integration-image` on kasumi) | every local build and boot; glibc's `libc.a` linked into the package, never read |
| rustup-init (static.rust-lang.org, sha256 `5be191e8…` read twice) and Rust 1.97.1 with rustfmt and clippy | 1.97.1 | MIT OR Apache-2.0 | run (`notes/as02b/Containerfile.rust`) | building the seam wolf |

## gm01: the games on PAX — the font row, the games in the payload, the equal-experience proof

No kernel, libc, shell, grep, file-system tool, bootloader or font-engine
source was read; the kernel's change is kernel/screen's own (a glyph
number of up to sixteen bits in a cell, the code point found in
boot/font.S's ranges). Spleen 2.2.0 stays vendored unmodified: its BDF
was read as data (the glyphs, as px19 read them), and it turned out to
carry 159 of the 161 code points the games draw (every braille pattern,
all 32 block elements, the box drawing, U+2248 and U+25C6). The braille
and block-element generators in `tools/mkfont` are written from the
code points' Unicode definitions and are held equal to Spleen's glyphs
bit for bit (285 of 285); the two glyphs Spleen lacks are PAX's own
drawing (`font/pax-extra.bdf`, the row above). The games are the
maintainer's own repositories (RULES §1), read and run, never changed.

| source | version | licence | how | used for |
|---|---|---|---|---|
| The Unicode Standard, the Braille Patterns chart (U+2800–U+28FF: dot k+1 is bit k; dots 1–3 down the left column, 4–6 down the right, 7 and 8 the bottom row) and the Block Elements chart (U+2580–U+259F: halves, eighths, quadrants, the three shades) | 16.0 | Unicode's terms (charts) | read | `tools/mkfont`'s `braille` and `block`, its `--test` rows |
| `wolffe-lang/pack` `e10835f2818ada427bc2d74f1171653af3ffdce1`, `wolffe-lang/cub` `6153d97555b3e1ae7406b9405df0e2cd10033af9`, `wolffe-lang/trail` `6dbe253fad3c73225c547a036aa8ec786abd91dc` (the maintainer's; source archives `b997002b…`, `ba390445…`, `bac96fe5…`) | the pins | GPL-3.0 with the wolf Training Data Permission | read: `docs/GLYPHS.md`, `docs/KEYS.md`, `docs/REPLAY.md`, `lair.pin`, `tests/cases/*.pk`, `tests/goldens/`; built by their own engine's tools (`tools/fetch-lair`, `.lair/tools/fetch-toolchain`, `.lair/tools/build --release`); run headless, live on a pseudo-terminal and on PAX | `user/install/games.txt`, `tools/mkgames`, `font/games-glyphs.txt`, `tests/mpx6-games`; `tests/mpx6-games.d/cases/trail-natural-paused.pk` is trail's `natural-80.pk` with its last line a pause |
| `wolffe-lang/lair` `aa6c4dc0bc5071d3c07121451d913a8837cd2a6a` (pack's and cub's engine) and `57870143ebbb4806b8bee40379e8c6e781f50842` (trail's) (the maintainer's; archives `7507a4cb…`, `191dc626…`) | the pins | GPL-3.0 with the wolf Training Data Permission | read: `docs/REPLAY.md`, `src/tier/tier.lu` (`detect`: plain for `TERM=linux`), `src/grid/grid.lu` (`push_sgr`, the colour words), `src/headless/headless.lu`, `src/probe/probe.lu`, `wolf-toolchain.toml`, `tools/build`, `tools/fetch-toolchain`, `tools/pty`'s description | `tools/mkgames` (the engine's archive by digest, held to the tree `fetch-lair` stages); `tests/mpx6-games.d/compare.py` (a golden frame to bytes); R-gm01-4 |
| wolf 0.2.35 (`cf0c13d`, x86_64 Linux archive `4cc4045b…`), lupin 0.1.56 and wolf-std `2386522e`, as the engine's `wolf-toolchain.toml` pins them | as listed | as each project's | run by the engine's `fetch-toolchain` and `build` | the three games' static binaries |
| Ubuntu 24.04's gcc and glibc (`libc.a`), the lane's `px80-ubuntu` container on kasumi and CI's `ubuntu-24.04` runner | as installed | GPL-3.0; LGPL-2.1 | run (`cc -static` as the link) | the games' static link, as px71's pack |
| QEMU's monitor `sendkey` names (`shift-down`, `shift-right`, `spc`, `ret`, `ctrl-d`) and `screendump` | 8.2.2 (CI), 11.1.1 (kasumi) | — | read (the monitor's `help`) and run | `user/console/games.keys`, `games-withheld.keys` through `tools/ps2-session` |

## px83: deterministic observations and measured CI budgets

No shell, libc or kernel source was read. Pelt and the existing static
probe binaries were run as black boxes in dedicated Linux containers or
QEMU; only PAX's own test/harness source was changed. F0 process-state
snapshots came from the test container's `/proc`, never the host process
table. Host process metadata was read only to identify the shared CPU-block
lock holder. No third-party implementation was used as source for a fix.

| source | version | how | used for |
|---|---|---|---|
| [POSIX exec, DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/functions/exec.html) | POSIX.1-2024 | prose read | ignored dispositions at exec, distinguished from later runtime initialization in `user/sigwolf/sigwolf.lu` |
| [POSIX sigaction, DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/functions/sigaction.html) | POSIX.1-2024 | prose read | subsequent handler installation may replace an inherited ignore |
| PAX tests, workflow and CI logs | base `187aafdf`; run IDs in `tests/ci-budgets.d/` and `notes/px83-evidence/` | own source and recorded output read | ordered J4 witness, K2 clock distinction, bounds and retry policy |
| Pelt binary at `user/pelt.pin` | unchanged pin | built by the existing digest-checked builder; black-box replay only | Linux F0 futex/zombie symptom, pelt#98 |
| ELF symbol table of the lane-built sigwolf | wolf 0.2.35, pinned archive | `readelf -sW`, no disassembly or library source | assert the overflow PC belongs to the current `_Wdeep$…` function |
| QEMU speaker capture and guest event ring | same native-BIOS image before/after | black-box output | separate host capture duration from guest ticks |


## px73: the live USB image

No third-party bootloader, firmware, kernel, driver or disk-tool implementation
source was read. PAX's own sources were read. Limine, firmware, Linux and its modules are binary inputs. The
new host-image path reuses PAX's own `tools/mkdisk` and `tools/mkgpt`;
module staging follows PAX's own `tools/linux-nodes`. The kernel's existing
Limine media report is unchanged. Consulted on 2026-10-27:

| source | version / clauses read | use |
|---|---|---|
| [UEFI GPT disk layout](https://uefi.org/specs/UEFI/2.10/05_GUID_Partition_Table_Format.html) | 2.10, §§5.2.3–5.3: protective partition at LBA 1 with size disk-minus-one, both GPT headers and entry arrays | raw-image layout and independent coverage/CRC checks |
| [UEFI media access](https://uefi.org/specs/UEFI/2.10/13_Protocols_Media_Access.html) | 2.10, §§13.3.1.3, 13.3.2, 13.3.4.1: removable-media directory, GPT discovery and FAT | ESP and removable boot path |
| [Limine usage documentation](https://github.com/Limine-Bootloader/Limine/blob/v12.9.1/USAGE.md) | v12.9.1, UEFI, BIOS/GPT and hybrid ISO sections | BOOTX64.EFI and the explicit BIOS boot partition; existing ISO kept unchanged |
| [Limine boot protocol](https://github.com/Limine-Bootloader/limine-protocol/blob/3a0526b700e356f0eac1b71a77697b3fd1c707a3/PROTOCOL.md) | File Structure: media_type, partition_index, mbr_disk_id, GPT UUIDs | existing `boot:` line; generic media is not evidence of a USB transport |
| [El Torito bootable CD-ROM specification](https://pdos.csail.mit.edu/6.828/2018/readings/boot-cdrom.pdf) | 1.0, §5.3 no-emulation booting | distinguish the unchanged optical ISO path from the raw-disk USB path |
| [Intel xHCI requirements specification](https://www.intel.com/content/dam/www/public/us/en/documents/technical-specifications/extensible-host-controler-interface-usb-xhci.pdf) | 1.2, May 2019, §§1.1–1.2 and §3 architectural overview | host-controller versus class-driver boundary; QEMU xHCI topology, no driver implemented |
| [USB mass-storage bulk-only transport](https://www.usb.org/sites/default/files/usbmassbulk_10.pdf) | 1.0, §1.1 scope, §2 terms | command/data/status transport over bulk endpoints; firmware-owned storage during boot |
| QEMU, SeaBIOS, OVMF; Linux with xHCI, usb-storage and vfat | installed binary versions recorded with the gate | black-box USB boots and Linux ESP file differential |
| `lsblk --json`, `findmnt`, `diskutil` plist inventory shapes | Linux/macOS tool interfaces; synthetic inventories in tests | fail-closed removable-disk plan and dry-run writer policy, no real-device writes |

## px82: yew launch pin

The org-owned yew tree moves from `77c108391242dac8ff3be0087e52bc153a2d75a2` to `0ccb2c67661a2dd789b5ce86180d592370a79c31` (1066 commits).
Launch `git ls-remote` read twice with identical results; the codeload
archive SHA256 `d2ef6674865306bf5bc910b0541814210069c981a70bdbefdbf7a11e6f54ef15` read twice on hasu.
Built unmodified with its own wolf-toolchain.toml; no third-party source
consulted. The image snapshot is separate from px04 historical traces.

## px82: boreutils launch pin

The org-owned boreutils tree moves from `575dc7b94b3aea8cb2c5d92d5263465b4a72c4c2` to `0f7a57b68829765f60c39ced01edb7ea75265eb8` (347 commits).
Launch `git ls-remote` read twice with identical results; the codeload
archive SHA256 `ee30f43a304b7b5029daf1bc4dcb9b24f6183644c95e2436ca4c5fb311a81bd8` read twice on hasu.
Built unmodified with its own wolf-toolchain.toml; no third-party source
consulted. The image snapshot is separate from px04 historical traces.

## px82: scent launch pin

The org-owned scent tree moves from `b6f63a4892cca631475cd0b87a0b648ce9b532a9` to `81d761d6d3b3c32f83a7b54801728088afea245a` (102 commits).
Launch `git ls-remote` read twice with identical results; the codeload
archive SHA256 `15f4b5261a623fe3c7470965483c63c9a30b6f908a6f274da0d0040c450da9fa` read twice on hasu.
Built unmodified with its own wolf-toolchain.toml; no third-party source
consulted. The image snapshot is separate from px04 historical traces.

## px82: pelt launch pin

The org-owned pelt tree moves from `0b5eaa5394667c485de3a134f771c87024b68a3c` to `4683b3f5faf46cd393ec2632f345f8cd483a4f1f` (25 commits).
Launch `git ls-remote` read twice with identical results; the codeload
archive SHA256 `19645879b4401ee8f1d93fdac3b5169ca057afeea179268f6811352cdc96aee8` read twice on hasu.
Built unmodified with its own wolf-toolchain.toml; no third-party source
consulted. The image snapshot is separate from px04 historical traces.
