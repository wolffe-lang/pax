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

**Forbidden, kept.** Written from the Intel SDM (vol. 3A ch. 2, 4, 6, 7, 11, 15; vol. 2), the UEFI and ACPI
specifications as px76 cites them, and Limine's protocol as `docs/BOOT.md` records it. QEMU, OVMF, SeaBIOS and Limine
were run as black boxes; clef's own source (the org's assembler, `user/clef.pin` at `b71b43f4`) was read for its
mnemonic table only. No kernel's, firmware's, bootloader's, emulator's or driver's source. kasumi was never touched
(the maintainer booted it); hasu's :9364 server and the maintainer's data were not touched; no label, no merge, no
issue filed or closed; no attribution trailers.

**Inputs.** Base pax trunk `56b9f554` (px78's head; the branch rebased once onto `3958c5a0`, px77c's notes and `docs/INSTALL-METAL.md` only: every branch sha this note cites is the pre-rebase one, paired with its rebased twin in `notes/px77d/rebase-map.txt`), wolf 0.2.35 (`4cc4045b…`, read twice: `notes/px77d/archive-reads.txt`),
Limine 12.9.1 (`5cdebc51…`, `limine-read-{1,2}.sha256`). hasu block A (CPUs 0-5) under
`flock /home/mfwolffe/lanes/hasu-block-A.lock`, `localhost/px75-ubuntu:2`, `/dev/kvm` passed in; every job's
script is under `notes/px77d/hasu/` (`session.sh` holds the lock). One deviation: the first session's wrapper
returned early, so one kernel rebuild (`kout2`, about 5 minutes) ran on CPUs 0-5 after the lock was released;
px77c was idle then (its last log line 02:31Z). Every later job held the lock.

**Prediction** (`notes/px77d/prediction.txt`, `d7af9a7f`). It was committed after the triage code's commits and
before the first triage boot, not before the first change (RULES §5): stated in the file. Scored:

| predicted | measured |
|---|---|
| P1 entry 1 boots to `login:` under OVMF/KVM with boxes 01-26 and the band intact | **right** (`screens/02-entry1-login-with-band.png`) |
| P2 `stop=6`: the green banner, boxes 01-06 | **right** (`screens/03-entry3-stop-at-6.png`) |
| P3 `fault=3`: FAULT 00, STEP 03, VEC 06, RIP in `pax_ud2`, halted, no reset; `fault=12` FAULT 01 and PAX's PANIC line | **right**: RIP `0xffffffff8000047c` = `pax_ud2`, halted in `t_halt` (`HLT=1`), no reset event; `fault=12`: `tg_f_src` 1 and `PANIC invalid opcode vector 6` (T6) |
| P4 entry 11 boots as the px77b stick does | **right** in QEMU (no band, the same transcript) |
| K1 (most likely) on kasumi a machine check, drawn as VEC 12 | **wrong**: kasumi booted entry 1 to `login:`, no fault, `MC BANKS CLEAN` |
| "x2APIC: KVM's x2APIC-ID run reached login" (as evidence the x2APIC path works) | **wrong as evidence**: the panel there reads APIC `FEE00900`, OVMF did not hand over x2APIC mode. The path was then run under KVM by px76's own hand leg: `PAX_METAL_X2APIC=1 tests/mpx6-metal` on UEFI, `apic: x2APIC mode (IA32_APIC_BASE EXTD set at the handover): its registers by MSR`, `PASS METAL LAPIC tick rate 20 ticks in 150..300ms`, `PASS METAL firmware uefi x2apic` (R-px76-7's first witness) |

**The metal result** (the maintainer, 2026-10-30 ~00:35 EDT, relayed): the triage stick's entry 1 boots kasumi to
`login:` with boxes 01-1A; the 101e7761 stick reset at once. The panel, from the photo:

    APIC 00000000FEE00900  CR0 80010011  CR4 00000020
    EFER 00000D00  PAT 0000010500070406
    CPUID 000A0671  MTRR 0C06  MMAP 0093
    FB 0000004000000000 0A00X05A0 PITCH 4000
    MCG 00000C0F STATUS 0000
    MC BANKS CLEAN

xAPIC mode at the handover (no x2APIC), machine checks off at the handover (CR4 = PAE only), Limine's PAT layout,
Rocket Lake (`0xA0671`), the MTRR default type **write-back** with MTRRs enabled, **147** memory-map entries, the
framebuffer at **256 GiB** (ReBAR and Above 4G on), 2560x1440 with a 16384-byte pitch (4096 pixels a row), 15 banks,
none holding an error.

**What triage changed, and so what can have saved kasumi.** In the triage boot nothing faulted and no machine check
was signalled: both would have been drawn and halted (T4, T6, the CR4.MCE plant). So triage's IDT and CR4.MCE caught
nothing; they cannot be what let kasumi boot. What else differs from the plain boot: (1) the band, drawn at every
step by switching CR3 to Limine's tables and back (a TLB flush each time) with interrupts off for a few milliseconds;
(2) the console 70 rows high at 2560x1440 instead of 90; (3) the time all that takes (about 0.1 s before box 9, a few
ms a box after); (4) Limine's conf: the triage stick has `timeout: 15`, `verbose: yes` and `cmdline: triage`, the
101e7761 stick `timeout: 3`, one entry, no command line; (5) the kernel itself: 101e7761 against 56b9f554, whose
kernel diff is all after box 9 (`kernel/{xhci,usb_storage,block,ahci,vblk,files,procfs}`, `io.S`'s `pax_call5`,
kmain_console's `block.attach_usb`), none of it reset-shaped. Entry 11 of the triage stick (56b9f554's kernel plus
the inert hooks, the triage stick's Limine conf, no `cmdline:`) separates (1)-(3) from (4)-(5): if it boots, the
reset was the old stick's kernel, its conf, or a one-off (one boot each so far); if it resets, the bisection stick
(below) names which of triage's effects kasumi needs. Entry 11's result was not in at this hand-back.

## Reproduction

Every boot of the px77b stick (`598d3439…`) under OVMF reached `login:` (`runs/` on hasu, `notes/px77d/hasu/repro.py`):
KVM `-cpu host` (i7-12700KF), 32 GiB, `-smp 16`, `pit=off`, two MSI-only `nec-usb-xhci`, `X-PciMmio64Mb=262144`
(the xHCI BARs at `0x40_0000_0000`), `-serial none` and `-serial file`; with VGA, bochs-display and virtio-vga; and an
APIC-ID-256 machine (intel-iommu `eim=on`, `kernel-irqchip=split`). The triage stick likewise (entry 1 at 32 GiB and
16 CPUs, on the x2APIC-ID machine, entries 3, 10 and 11).

Not reproducible here, by measurement: **a GOP framebuffer above 4 GiB.** Every QEMU display device OVMF drives puts
its framebuffer in a 32-bit BAR (`info pci`: VGA, bochs-display, virtio-vga's VGA BAR all `32 bit prefetchable` at
`0x80000000`); `-device VGA,help` and the others offer no BAR-width property; `ramfb` lands in RAM below 4 GiB
(`0x7EA3F000`); `virtio-gpu-pci`'s GOP has no scanout after ExitBootServices ("Display output is not active").
Nor AVX-512 (hasu is Alder Lake), nor 147 map entries (OVMF gives 32 to 42), nor a write-back MTRR default (OVMF's
is `0C06` too, so that one is reproduced). The map's walkers (kernel/frames, kernel/paging, kernel/acpi's `mapped`
and its `memory:` line) have no fixed bound.

Limine's answer to a missing `cmdline:` was read (`notes/px77d/hasu/cmdprobe.py`): a pointer to a NUL inside Limine's
own image (`00 65 6c 66 3a …`), in a bootloader-reclaimable entry under OVMF (`0xe710752`, entry 16) and SeaBIOS
(`0x5185e`, entry 0), which PAX's HHDM maps; with `cmdline: triage`, a string in bootloader-reclaimable memory. Both are
read after PAX's page-table switch and before its IDT (`fstab.root_asked`, box 8), so a mapping gap there would be a
silent reset on the plain boot only; QEMU shows none.

## The triage stick

`boot/triage.S` (the assembly, on every kernel's roster), `kernel/triage` (the words, the steps), hooks in
`kernel/{screen,fpu,frames,apic,panic,interrupts}` and `kernel/kmain_console` (the steps; `paging.start`'s three calls
spelled out so boxes 5 and 6 sit between them). Without `triage` every hook returns at once: T1/T2 compare the plain
and triage transcripts line for line (but the `screen:` line and the numbers Limine or a clock decides) on both
firmwares.

| word | effect |
|---|---|
| `triage` | its own GDT (PAX's layout), a TSS with IST1, 32 exception gates on IST1, CR4.MCE; the handover's facts and a numbered box per step in a band under the console; any fault drawn in large hex and halted; kernel/panic's halt marks its step |
| `slow`, `stop=N`, `fault=N` | each box held a second; a green banner and a halt at step N; an `ud2` at step N |
| `nofb`, `fxsave`, `low4g`, `keeplint0`, `noxhci`, `noblock`, `nosound` | one suspect each turned off (the console's screen, XSAVE, frames above 4 GiB, LINT0, the xHCI, the disks, the sound device) |
| `noidt`, `nomce`, `nodraw`, `fullh` | the bisection words (after kasumi's result): triage's own effects off one at a time |

**The stick** `~/pax-smoke/pax-triage-fedb6f5f.img`, 794,820,608 bytes, sha256
`f7c5f7529ac131d88002aff0e7150271a76d167caa51a372dabc74ead8cbf76a` (read twice on hasu, twice on nomad), px77b's
recipe at `fedb6f5f` (`notes/px77d/hasu/build-inside.sh`, `stick.sh`; `stick-final.log`: U1/U2 pass), the banner
`PAX: kernel fedb6f5f…; release 52bcf747`. `TRIAGE.txt` (copied to `notes/px77d/TRIAGE.txt`) is what the maintainer
followed.

**The bisection stick** `~/pax-smoke/pax-bisect-089896db.img`, 794,820,608 bytes, sha256
`9cc54e8463b17fd019a38d6d75a8159733b4dec6029fbc40094663bcc8f1332b` (two reads on hasu, two on nomad), px77b's recipe at
`089896db`, `boot/limine-bisect.conf`: 1 `triage` (the control), 2 `nodraw`, 3 `fullh`, 4 `nomce`, 5 `noidt`, 6 all
four, 7 `nodraw fullh`, 8 no triage; `BISECT.txt` (`notes/px77d/BISECT.txt`) says the order. Under KVM entries 1, 2,
6 and 8 reach `login:`. Only needed if entry 11 resets.

**Tests** (`tests/mpx6-triage`, run by `tests/mpx6-firmware` as F10; rows T0-T8 in its header): on hasu under KVM,
native tier, both firmwares, every row passes at `1ced6284` (`PASS mpx6-triage native`, 19 s; `logs/mpx6-triage-kvm.log`); the planted break (triage without
CR4.MCE) red by name: `FAIL TRIAGE triage: triage sets CR4.MCE {… "tg_e_cr4": "0x20", "cr4": "0x340620" …}`. T5
witnesses the triage IDT itself: `noidt fault=3` is a reset (QEMU ends under `-no-reboot`) where `fault=3` is a
picture.

## Done-when

- [x] Item 1: the hazard table (H1-H14), first.
- [x] Item 2: reproduction attempted on hasu block A with KVM, 32 GiB, 16 CPUs, OVMF, no serial, the 64-bit window,
  an x2APIC-ID machine: no reset. A GOP framebuffer above 4 GiB and AVX-512 cannot be made here (above).
- [x] Item 3: the triage stick staged with TRIAGE.txt, four reads agreeing; it booted kasumi.
- [ ] Item 4: the fix, when the cause is named (below).
- [x] Item 5: the suite (T0-T8) and its plant; the note; the PR and the audit (the hand-back).
