# BOOT — how PAX is loaded, and why Limine

**Ruled by px00 (2026-10-02): PAX boots through the Limine boot protocol,
base revision 6, from one hybrid ISO that boots under BIOS and UEFI alike.**
The bootloader is Limine's own release binary, fetched by digest
(`boot/limine.pin`, `tools/fetch-limine`); it is not PAX code and nothing of
it is copied into this repository.

## The three candidates

The question for each: how much C or assembly does the kernel itself have to
carry before wolf code can run, under what licence, and what does the kernel
get handed?

| | Limine protocol | multiboot2 | direct UEFI stub |
|---|---|---|---|
| CPU mode at entry | **64-bit long mode**, paging on | 32-bit protected mode, paging **off** | 64-bit long mode, firmware's identity map |
| higher half | **yes**: the ELF's `PT_LOAD` segments mapped at their addresses (≥ `0xffffffff80000000`), plus an HHDM of usable memory | no: the kernel builds its own page tables and jumps up | no: the kernel builds its own page tables |
| kernel-side glue before wolf runs | **none**: entry is a SysV-ABI function on a 64 KiB stack | page tables, PAE, `EFER.LME`, a 64-bit GDT, a far jump: 32-bit assembly (wolf's backend emits none) | PE32+ output, Microsoft x64 calls into boot services, `GetMemoryMap` / `ExitBootServices`, page tables |
| what it hands over | memory map, HHDM offset, framebuffer, RSDP, SMBIOS, EFI system table, modules (initramfs), command line, firmware type, MP start-up of every CPU, paging-mode choice — each a static request in the kernel image | memory map, framebuffer, modules, command line, ACPI and EFI tags (as tags in a 32-bit-addressed blob) | whatever the kernel asks boot services for, before it exits them |
| BIOS and UEFI | **both, one kernel binary, one ISO** | both through GRUB (or Limine), with the same 32-bit entry | UEFI only |
| licence of what we depend on | bootloader BSD-2-Clause, protocol text 0BSD; fetched, never vendored | GRUB GPL-3.0 (compatible, but a GPL-3 binary on every image); spec GNU FDL | UEFI spec (no third-party code) |
| QEMU test path | ISO on a cdrom, SeaBIOS or OVMF | QEMU's `-kernel` speaks multiboot **1** only, so tests need a GRUB image anyway (`grub-mkrescue`: xorriso plus GRUB's BIOS and EFI module trees) | OVMF plus a FAT image |

Limine is the only candidate under which the first instruction of PAX can be
wolf. multiboot2 forces a 32-bit trampoline that wolf cannot write and this
project would carry as assembly forever. A UEFI stub needs nothing third-party
but asks the most of the compiler (a PE32+ target and the Microsoft calling
convention beside SysV) and gives up BIOS machines. It stays a possible second
entry for P6, not the first.

The cost of Limine, named: a third-party binary on every image (BSD-2,
fetched by digest); a protocol that is Limine's own rather than a multi-vendor
standard (its text is 0BSD, so a second loader could implement it); and the
P6 installer must run Limine's `bios-install` step or copy
`BOOTX64.EFI`, as it would GRUB's.

## What the kernel must do under it (the clauses for kw00)

From PROTOCOL.md (limine-protocol `3a0526b7`), base revision 6, x86-64. Each
is a requirement on wolf's freestanding output, so each is a clause for the
KWC design note to rule on:

1. **An ELF64 executable linked in the top 2 GiB** (or relocatable; Limine
   slides a lower-half PIE up), entry at `e_entry`, one `PT_LOAD` per
   permission (Limine honours `PF_W` and `PF_X`; NX is on).
2. **The entry is a SysV-ABI function that never returns**, called on a
   bootloader stack of at least 64 KiB with a 0 return address pushed.
3. **No FP/SIMD before the kernel enables it.** Base revision 5 and later
   clear every `cr0`/`cr4` bit beyond PE, ET, WP, PG and PAE, so
   `CR4.OSFXSR` is off and the first SSE instruction faults (#UD). wolf's
   kernel code must either be compiled without SSE (as soft-float kernels
   are) or enable it in its first lines — and the protocol's own
   boundary is "System V ABI without FP/SIMD" either way.
4. **Requests are static, 8-byte-aligned data** with exact layout (four
   64-bit id words, a revision, a response pointer), between the start and
   end markers, and must survive the linker (no section GC drops them).
5. **The response pointers are written by the bootloader after the image is
   built**: the compiler must treat them as volatile (a zero-initialised
   static the optimiser folds to null reads as "no response" forever).
6. **The base revision tag is read back**: Limine zeroes its third word when
   it honours the revision; the kernel checks it (the stub does: status 35
   and a message when it is not).
7. Interrupts are off, the IDT is empty, the PICs and I/O APIC entries are
   masked, the local APIC is in a defined state: the kernel loads its own IDT
   before enabling anything. Kernel code that takes interrupts must not use
   the SysV red zone (a P2 clause, named here so kw00 sees it).

The stub `boot/stub/pax-stub.s` exercises 1, 2, 4, 6 and the firmware-type
request, in assembly, so the harness has something to boot. px01 replaces it
with wolf.

**The wolf kernel's boot path (kw05, M-KW).** `boot/start.S` holds the
request markers and the base-revision tag, checks the tag's third word and
calls wolf's `kmain` (an `export fn`) with the stack aligned to 16 bytes:
clauses 1, 2, 4 and 6. Clause 3 is the compiler's: `wolf build --target
x86_64-unknown-none` emits no SSE and no red zone on either tier, and
`tools/build-kernel` checks every object for it. Clause 5 is met by not
needing it yet: the one bootloader-written word M-KW reads (the base
revision) is read in assembly, so no wolf code reads a response pointer
before wolf has volatile access (KWC kw07). `boot/io.S` holds the port I/O,
the exit and the trap hook (`wolf_trap`), listed under `asm` in
`kernel/wolf.pkg` so wolf assembles it for the kernel's target.
`boot/kernel.ld` is the stub's layout plus what a compiled object brings
(`.rodata.*`, `.data.rel.ro`, the small-PIC GOT, `.bss`).

**First light (px01, M-PX1).** `boot/start.S` carries four more requests
between the markers — bootloader info, firmware type, memory map and
HHDM — each with its PROTOCOL.md id words, revision 0 and a null response
pointer. Clause 5 is still met by not needing it in wolf: `boot/limine.S`
(listed under `asm`, so on wolf's roster) loads each response pointer
afresh on every call, follows it, and returns plain integers (a string
byte by byte; a memory-map field by entry and index), so wolf code never
holds a pointer the bootloader wrote. When wolf has volatile access (kw07)
and integer-to-pointer lowering (kw06) the readers can move into wolf;
the requests stay in `start.S`. Measured on QEMU (q35, 256 MiB, Limine
12.9.1): SeaBIOS gives 18 memory-map entries and ~254.5 MiB usable, OVMF
30–33 entries and ~210–214 MiB usable (boot-services memory is reported
bootloader-reclaimable), and the HHDM offset was `0xffff800000000000` on
every boot (4-level paging) — which the test asserts only by shape, since
the protocol lets it vary. The kernel ends in `cli; hlt` (`boot/io.S`'s
`pax_halt`), not `isa-debug-exit`; `tools/qemu-halt` proves the halt
through QEMU's monitor.

**Physical frames (px02).** `boot/start.S` carries a sixth request,
the executable address (id `0x71ba76863cc55f63, 0xb2644a48c516a487`):
Limine answers with the image's physical and virtual base, which the
frame allocator's test needs, because executable-and-modules entries in
the memory map are "illustrative only" (PROTOCOL.md). With wolf-lang
`eb955c3b` (kw06's `N as *T`, kw07's `read_volatile`) the readers moved
into wolf: `kernel/boot_info` follows each response pointer with one
volatile load per word, afresh per call, which is clause 5 met in wolf
itself. `boot/limine.S` keeps only what wolf cannot spell: a symbol's
address (each request's, and `boot/kernel.ld`'s `__pax_image_start` /
`__pax_image_end`; wolf-lang#529) — until kw10, which retired it:
with wolf-lang kw09's `extern "c" let`, `kernel/boot_info` and
`kernel/paging` name those symbols themselves. Measured on QEMU (q35, 256 MiB,
Limine 12.9.1): SeaBIOS 65147–65157 usable frames, 44 of them below
1 MiB, the highest usable byte below `0x10000000`; OVMF 53784–54863
usable frames (the count moves by about a thousand between the OVMF
builds of kasumi, CI and hasu), 159 below 1 MiB; the image near the top
of RAM (`0xff7f000` under SeaBIOS; `0xbfb1000` or `0xe72b000` under
OVMF, by build). Usable memory is mapped in the
HHDM at this base revision, so the allocator reaches every frame it
hands out through it.

## The image

`tools/mkimage KERNEL.elf OUT.iso` lays out:

    /boot/pax                         the kernel ELF
    /boot/limine/limine.conf          boot/limine.conf: timeout 0, quiet, one entry
    /boot/limine/limine-bios.sys      Limine's BIOS stage 2
    /boot/limine/limine-bios-cd.bin   El Torito BIOS boot image
    /boot/limine/limine-uefi-cd.bin   El Torito EFI system partition image
    /EFI/BOOT/BOOTX64.EFI             Limine for UEFI

then runs `xorriso -as mkisofs` with Limine's documented hybrid flags and
`limine bios-install` on the result, so the same file boots from a cdrom
under SeaBIOS, from a cdrom under OVMF, and (later) written raw to a USB
stick.

## Measured

The proof's runs, both firmwares, the same ISO on linux and macOS: see
`notes/px00-the-harness.md` §4. Exit status 33 is the stub's `0x10` through
`isa-debug-exit` (QEMU reports `(value << 1) | 1`).
