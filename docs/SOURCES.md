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
