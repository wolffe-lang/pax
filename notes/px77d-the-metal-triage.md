# px77d — the metal triage: why kasumi reboots the moment PAX starts

Contract: `wolf/sprints/pax/77d-the-metal-triage/px77d-the-metal-triage.md` (P6, crawl 54), from the
maintainer's first metal boot (px77): Limine's menu drew and took the USB keyboard; picking PAX rebooted
kasumi at once, nothing on the screen. The stick was px77b's `pax-stick-101e7761.img`. PAX's panic path
halts (`kernel/panic`, `io.S` `cli; hlt`), so a reboot is a triple fault, or a machine check while
CR4.MCE is clear (the SDM's shutdown), or a deliberate reset (none is reachable at boot: only reboot(2)
calls `kernel/power`). Footprint: cross-cutting (the kernel's core: `kernel/{panic,frames,interrupts,
apic,fpu}`, `boot/triage.S` on the kernel's roster).

## The hazard table (item 1)

From Limine's handoff to PAX's first pixel and to a live IDT, then to the login. "Escapes" says whether a
fault there became a reboot before this lane (trunk `56b9f554`), and what the triage stick does with it.

| # | step (box) | what PAX does | what kasumi may hand over | escapes to a reboot? |
|---|---|---|---|---|
| H1 | the handover (01) | runs on Limine's GDT and an IDT Limine leaves empty (`docs/BOOT.md` clause 7) until `interrupts.start` (box 09) | — | **yes, every exception in boxes 01-08** (an empty IDT: #GP, #DF, shutdown). Triage: its own GDT, TSS and 32 gates on an IST before anything else |
| H2 | CR4 (01) | never sets CR4.MCE; Limine at base revision 5+ clears every CR4 bit beyond PAE | Rocket Lake's machine-check banks; any uncorrected error, or one the firmware logged | **yes, at any step: a machine check with CR4.MCE clear is a shutdown** (SDM vol. 3A ch. 15). Triage sets MCE and draws vector 0x12 with the banks; the panel shows the banks at entry (a previous boot's error survives a warm reset) |
| H3 | the early screen (03) | `screen.early_start` attaches to Limine's framebuffer mapping and fills `pitch * height` through it | the RTX 4090's GOP framebuffer, perhaps above 4 GiB (ReBAR, Above 4G), at the firmware's mode | a page fault there escapes (H1). QEMU's GOP framebuffers are all 32-bit BARs below 4 GiB (VGA, bochs-display, virtio-vga): the high framebuffer is untested |
| H4 | frames (04) | a bitmap over the span of usable memory, its state in the first usable run above 1 MiB | 32 GiB, many entries, RAM above 4 GiB | escapes (H1) only through a bad memory map; KVM 32 GiB reached the login |
| H5 | PAX's page tables (05, 06) | the image W^X; an HHDM over types 0, 2, 3, 5, 8 in merged runs, 2 MiB pages where a whole aligned 2 MiB lies inside a run (WB through the PAT); modules read-only; then NXE, WP, PGE-clear and the stack checked, CR3 switched | real firmware's map: runtime regions, ACPI NVS, MMIO listed as reserved; MTRRs set by the firmware | a fault escapes (H1). A 2 MiB page over two MTRR memory types is undefined (SDM vol. 3A §11.11.9): a machine check there escapes (H2). Between the switch and box 09 the CPU still holds Limine's GDTR, which PAX's tables may not map |
| H6 | kernel/fb (07) | maps the framebuffer 4 KiB by 4 KiB at Limine's HHDM address, WC (PAT entry 5) | a framebuffer anywhere below MAXPHYADDR (39 bits on Rocket Lake) | a refusal is named (`screen: off`); a fault escapes (H1) |
| H7 | the initramfs (08) | reads the cpio in place through its read-only mapping | the 385 MB module Limine loaded from the stick | escapes (H1) |
| H8 | PAX's IDT (09) | its GDT, TSS (IST1 for #DF) and 48 gates; every kernel exception a named panic on the screen | — | no: from here an exception is printed, unless the handler itself faults (#DF on IST1, then shutdown) |
| H9 | the local APIC (10) | follows IA32_APIC_BASE's EXTD (x2APIC by MSR, px76's R-px76-7), never switches modes; LINT0 to ExtINT, unmasked | x2APIC mode if the firmware enabled it (VT-d with interrupt remapping commonly does) | a #GP from a wrong MSR is printed (H8). The SDM's rule (x2APIC to xAPIC needs a disable first) is never exercised: PAX never changes the mode |
| H10 | the timer (11), the clock (16) | the LAPIC timer calibrated by the HPET, else the PM timer, else the PIT | an HPET, a PM timer, a gated 8254 (no `pit` clock source under Linux) | printed (H8) |
| H11 | the FPU (12) | x87, SSE and AVX only (XCR0 = 7 at most), the area CPUID.0DH:EBX after XSETBV, a page per area | AVX-512 (XCR0 bits 5-7 supported, never enabled by PAX) | no: AVX-512's state is never enabled, so its larger area never applies |
| H12 | xHCI (19), USB (24, 25) | USBLEGSUP's BIOS/OS semaphores (500 ms), MSI, BARs above 4 GiB | the firmware's SMM keyboard emulation owns the controller until handed off | printed; an SMM fault is the firmware's (it would reset, invisibly to any OS) |
| H13 | AHCI, NVMe (20) | BOHC's handoff; polled | the SATA target alone | printed |
| H14 | an NMI (any) | — | a firmware watchdog, SERR | before box 09 it escapes (H1); triage draws vector 02 |

## Evidence index

## Reproduction

## The triage stick

## Done-when
