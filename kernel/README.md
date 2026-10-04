# kernel/

The wolf kernel: first light (px01, M-PX1), physical frames (px02) and paging (px03). `kmain.lu` brings up COM1,
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
own text after the switch, which must fault (`tests/mpx2-paging`).

| module | what |
|---|---|
| `serial/` | the 16550 driver on COM1: `init` (no interrupts, 115200 8N1, FIFOs; scratch and loopback checks), `put` (LSR-polled) |
| `log/` | a line writer over `serial`: `put`, `line`, `end` (CR LF), `put_byte`, `dec`, `hex`, all without allocation |
| `boot_info/` | Limine's responses (bootloader name and version, firmware type, memory map, HHDM, the image's physical base) read in wolf with `read_volatile` through `N as *T`; `boot/limine.S` supplies only each request's address and the image's link-time bounds |
| `frames/` | the physical page-frame allocator (px02): two bitmaps (free, ever-usable) over the memory map, its state in frames it takes for itself above 1 MiB, reached through the HHDM; `init`/`start`, `alloc` (row `out_of_memory`), `free` (named panics), the totals |
| `paging/` | x86-64 four-level paging (px03): `build` (a zeroed PML4; the image W^X per section from `boot/kernel.ld`'s bounds; the HHDM over usable, bootloader-reclaimable, ACPI and reserved-mapped memory, 2 MiB pages where they fit, without the image or the framebuffer), `switch_to` (EFER.NXE, CR0.WP and CR4.PGE checked, the stack mapped, MOV to CR3), `start` (both), `map`/`map_large`/`unmap` (INVLPG on the live structures)/`translate` (rows: `out_of_memory`, `misaligned`, `not_canonical`, `already_mapped`, `large_page`, `not_mapped`), `report` |
| `panic/` | `wolf_trap`, the freestanding trap hook, in wolf; `fail(what, v)`, a fault the kernel detects, by name; `halt` |

- `wolf.pkg` lists `../boot/io.S` (port I/O, the halt),
  `../boot/limine.S` (the requests' addresses, the image's and each
  section's bounds) and `../boot/cpu.S` (px03: CR0, CR3, CR4, EFER,
  INVLPG, CPUID's NX bit) under `asm`: wolf
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
  call, through an address cast to a pointer (kw06). Struct layouts are
  read word by word at fixed offsets until kw08's `offset_of`. What wolf
  still cannot spell is a symbol's address (wolf-lang#529), so
  `boot/limine.S` keeps that and nothing else (px02; px01 read every
  response there).
- The frame allocator keeps its state in memory it owns, not in module
  state (wolf-lang#529, KWC kw09): `frames.start()` returns the state's
  HHDM address and every call takes it. `paging` takes the same `st`
  (its tables come from it, reached through its HHDM offset) and the
  PML4's physical address.
- wolf has no bitwise complement (wolf-lang#575): alignment is written
  `x - x % 4096`, masks as literals.
- Constants are written as literals, each named where it is used:
  wolf 0.2.22 refuses a module-level `const` (wolf-lang#560).
- `wolf.pin` names wolf: since px02 a wolf-lang commit (`eb955c3b`)
  built from source by `tools/fetch-wolf` (kw06/kw07 are in no release
  yet; back to a release archive by digest at 0.2.23), and lupin's
  release and digest (`tools/fetch-lupin`).

`tests/mpx2-frames` builds kmain and the three frames kernels on both
tiers, boots them under SeaBIOS and OVMF, and checks the totals against
the map, the exhaust, the touch, the reuse, the two named panics and
every halt. `tests/mpx1` builds kmain and kmain_panic on both tiers, boots them under SeaBIOS
and OVMF, asserts the transcript and the panic line, and proves each halt
through QEMU's monitor (`tools/qemu-halt`). M-KW's kernels (`KWC`,
`TRAP 1`) are frozen in `tests/mkw.d` and still booted by `tests/mkw`.
`docs/BOOT.md` says what the boot protocol asks of the object.
