# kernel/

The wolf kernel: first light (px01, M-PX1). `kmain.lu` brings up COM1,
reads what Limine handed it and prints one line each — the banner, the
UART, the bootloader and base revision, the firmware, a memory-map
summary, the HHDM offset — then `halt` and halts. `kmain_panic.lu` is a
second kernel whose overflow reaches the trap hook, which prints
`PANIC <kind> <file>:<line>` and halts.

| module | what |
|---|---|
| `serial/` | the 16550 driver on COM1: `init` (no interrupts, 115200 8N1, FIFOs; scratch and loopback checks), `put` (LSR-polled) |
| `log/` | a line writer over `serial`: `put`, `line`, `end` (CR LF), `put_byte`, `dec`, `hex`, all without allocation |
| `boot_info/` | Limine's responses (bootloader name and version, firmware type, memory map, HHDM) in the kernel's vocabulary, from `boot/limine.S` |
| `panic/` | `wolf_trap`, the freestanding trap hook, in wolf; `halt` |

- `wolf.pkg` lists `../boot/io.S` (port I/O, the halt) and
  `../boot/limine.S` (the responses, read in assembly) under `asm`: wolf
  assembles them for the kernel's target and refuses a call into anything
  off their roster (`[abi.asm.roster]`, E1306). The target is passed by
  `tools/build-kernel` (`--target x86_64-unknown-none`), not set here.
- Each kernel file is a standalone entry (`//! member: false`): a
  directory is one wolf module, and two `kmain`s would collide. The
  modules are child directories, imported by name (`use log`); imports
  are file-scoped and an unused one is an error (E0305), so a kernel
  names `panic` (for `panic.halt()`) even though the link would want
  only its `wolf_trap`.
- Limine's response pointers are bootloader-written, so wolf never reads
  them: `boot/limine.S` does, a fresh load per call, and returns
  integers, until wolf has volatile access (KWC kw07) and
  integer-to-pointer lowering (kw06).
- Constants are written as literals, each named where it is used:
  wolf 0.2.22 refuses a module-level `const` (wolf-lang#560).
- `wolf.pin` names wolf's release archive and its digest
  (`tools/fetch-wolf`, which also checks the binary's `--version` against
  the release's wolf-lang commit) and lupin's release and digest
  (`tools/fetch-lupin`).

`tests/mpx1` builds both kernels on both tiers, boots them under SeaBIOS
and OVMF, asserts the transcript and the panic line, and proves each halt
through QEMU's monitor (`tools/qemu-halt`). M-KW's kernels (`KWC`,
`TRAP 1`) are frozen in `tests/mkw.d` and still booted by `tests/mkw`.
`docs/BOOT.md` says what the boot protocol asks of the object.
