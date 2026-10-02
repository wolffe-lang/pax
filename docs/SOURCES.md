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
