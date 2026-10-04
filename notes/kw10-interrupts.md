# kw10 — interrupts (KWC F7, ruling #31 K7 = B; M-PX2's interrupt and timer pieces)

Contract: `sprints/compiler/91-freestanding/kw10-interrupts.md` in
wolffe-lang/wolf (planning trunk `d3d5e2d`). Branch `kw10` off pax
`ad34a40`; PR pax#7. The wolf-lang half, `[abi.interrupt]` and its
QEMU-booted witness, is wolf-lang#578 (branch `kw10`). The five sections
are committed whole in `8b71a8a` (an empty commit, before the first
change); this note carries §2's drift, §3 against what was measured,
and §4.

## 1. Forbidden

As committed in `8b71a8a`. Kept: no Linux, glibc or other kernel source
read (the trampolines, the tables and the handlers are from the Intel
SDM vol. 3A ch. 3, 6, 7 and 11 and the AMD64 APM vol. 2 ch. 4, 8 and
12, the timer from Intel's 8259A and 8254 data sheets, by section, in
`docs/SOURCES.md`); nothing installed on any host; no build on nomad-1
(it edited, pushed and read CI); kasumi under `~/lanes/kw10/` only;
hasu under `~/lanes/kw10/` through `nix-shell -p qemu nasm`, plus
`nix-build '<nixpkgs>' -A OVMF.fd` for the combined firmware, as
px01–px03 did; jobs started with `setsid` and waited on by done-file;
no issue closed.

## 2. Inputs, verified (drift)

Re-derived 2026-10-04 and stated in `8b71a8a`. Drift against the
contract's §2: none in the shas (pax trunk `ad34a40`, wolf-lang trunk
`6a4e6151`). Found while working:

- `boot/kernel.ld` keeps `.got` in the writable group, and kw09's lesson
  says to move it beside the read-only data once `extern "c" let` is
  used. Measured unnecessary here: pax's script names its PT_LOADs with
  `PHDRS`, so ld.lld makes no RELRO segment and no `.bss` page covers
  the GOT; every kernel reads its tables' link-time addresses
  correctly (I6: the monitor's GDT, IDT and TR bases equal the ELF's
  `pax_gdt`, `pax_idt` and `pax_tss`). The script is unchanged.
- **Limine leaves the local APIC enabled with LINT0 masked** (QEMU's
  `info lapic`: LVT0 `0x00018700` under SeaBIOS, `0x00010700` under
  OVMF). With the 8259 remapped and line 0 unmasked, the master's IRR
  held line 0 and no tick ever arrived (`info pic`: `irr=01 imr=fe`).
  The contract's "masked 8259, then the PIT" needed a third piece:
  `kernel/apic` maps the APIC's page and sets LINT0 to ExtINT, unmasked.
- Every kernel of the package links `boot/isr.S` (the `asm` list is
  per package), so every kernel must define `pax_interrupt`: every
  kernel now calls `interrupts.start()` first.
- `tools/build-kernel` refused any import outside the hooks and the asm
  roster; `extern "c" let` names symbols `boot/start.S` and
  `boot/kernel.ld` define, so it now admits exactly those two sets.
- `--images` on a fresh tree (hasu, from `git archive`) has no `build/`;
  `tests/mpx2-interrupts` makes it (px01–px03's tests still assume it).

## 3. Prediction against measurement

| predicted (`8b71a8a`) | measured |
|---|---|
| GDT: null, 0x08 kernel code, 0x10 data, 0x18/0x20 user, 0x28 TSS; limit 55 | as predicted: the monitor reads `GDT= ffffffff80006000 00000037`, `CS =0008 … CS64`, `SS =0010` (int3 kernel, CI) |
| TSS 104 bytes, IST1 = top of a 16 KiB .bss stack, I/O map base 104 | as predicted: `TR =0028 ffffffff80006040 00000067`; IST1 `[0xffffffff800060d0, 0xffffffff8000a0d0)` |
| IDT 256 gates, limit 4095, 0-47 routed, #DF on IST1 | as predicted: `IDT= ffffffff80005000 00000fff` |
| frame 22 u64, size_of 176 | as predicted: the #DF frame sits at `pax_ist1_top - 176` exactly |
| error-code vectors 8, 10-14, 17, 21, 29, 30 | as predicted (I0: `objdump` of all 48 trampolines); #PF's error code reads `0x3` |
| I1 `PANIC page fault vector 14 error 0x…3 … cr2 0xffffffff80000040` | as predicted; the monitor's CR2 agrees |
| I2 `PANIC invalid opcode vector 6 … rip <pax_ud2>` | as predicted (a fault saves the ud2's own RIP) |
| I3 `int3: breakpoint vector 3, rip <past the int3>`, `int3: returned`, `halt` | as predicted: rip = `pax_int3 + 1` |
| I4 #DF from a push at %rsp = 0x1000, frame on IST1 | as predicted: `rsp 0x0000000000001000`, frame `pax_ist1_top - 176`, the halted machine's RSP on IST1 |
| I5 8259 at 32/40, PIT divisor 11932 (99.998 Hz), 20 ticks | **wrong as first written**: no tick at all until LINT0 was unmasked (§2); with `kernel/apic`, 20 ticks on vector 32, 0 spurious, on both firmwares and tiers. The rate is the divisor's; it was not measured against another clock |
| every I red at the pre-change head | as predicted: 30 FAIL, 0 PASS (below) |
| plant: #PF's trampoline pushes a dummy → I0, I1 red | as predicted: I0 x10, I1 x4; I2–I6 PASS |
| wolf limitations: #572, #575, none new; a memcpy import filed if seen | #572 and #575 met (commented); **two new**: wolf-lang#577 (a store to a field of a raw element) and #579 (a `pub const` read from another module); no memcpy/memset import on either tier (build-kernel's import lists) |

## 4. Evidence index

### Assertions, red then green

`tests/mpx2-interrupts`, CI job `mpx2-interrupts`, per tier (native,
release) and firmware (bios, uefi). Red at `1493dbe` (the test and its
job, before any kernel change): run **37188522479** (job 111395597490,
log `d6347245…`), 30 FAIL, 0 PASS, 0 SKIP lines; the other seven jobs
green. Green at `7730112`: run **37188919348** (job 111396779525, log
`dd09bcb6…`), 34 PASS, 0 FAIL, 0 SKIP lines; mpx1 26, mpx2-frames 44,
mpx2-paging 26 PASS; every job success. Strict mode: the one skip path,
the UEFI leg without OVMF, is a failure under `PAX_REQUIRE_UEFI=1` (CI
and every run below); SKIP counted in each job's full log.

| | red at `1493dbe` (37188522479) | green at `7730112` (37188919348) |
|---|---|---|
| I0 build: 48 trampolines' shapes, iretq, `pax_interrupt` T | FAIL x10: `no symbol pax_isr_common` (text_write), no `kernel/<k>.lu` (the rest) | PASS x10 |
| I1 page fault: error 0x3, CR2 = text + 0x40 = the monitor's CR2, halted | FAIL x4: `QEMU ended (qemu-run status 0)` — the triple fault | PASS x4 |
| I2 invalid opcode at `pax_ud2`, halted | FAIL x4: no image | PASS x4 |
| I3 int3 returns, rip = `pax_int3 + 1`, halted | FAIL x4: no image | PASS x4 |
| I4 #DF on IST1, frame = top - 176, halted | FAIL x4: no image | PASS x4 |
| I5 20 ticks on vector 32, halted with IF clear | FAIL x4: no image | PASS x4 |
| I6 the monitor's GDT/IDT/TR/CS/SS = the ELF's tables | red as I3: no int3 kernel to read (`7730112` makes the script print I6's own FAIL line too) | PASS x4 |

### The planted break

`46bbeb9` (pushed alone): `ISR_NOERR 14`, so #PF's trampoline pushes a
zero over the CPU's error code and the frame is off by eight. Run
**37189785902**, job 111399385479 (log `264f6c0a…`), red: I0 x10
(`pax_isr14 (error code) begins 'push $0x0', not 'push $0xe'`), I1 x4
(the panic reads `error 0x0000000000000000`); I2–I6 PASS; 20 PASS, 14
FAIL, 0 SKIP lines. Reverted in `7cba18e`, green in run
**37190151463** (every job success; mpx2-interrupts job 111400450296,
34 PASS, log `1c2e3ef1…`).

### Runs

- CI (ubuntu-latest, QEMU 8.2, TCG): the runs above.
- kasumi (QEMU 11.1.1, TCG): all four kernel suites on the working
  tree before the green push (`~/lanes/kw10/evidence/try3-*.out`):
  mpx1 26, mpx2-frames 44, mpx2-paging 26, mpx2-interrupts 34 PASS.
- hasu (nix-shell QEMU 11.1.0, **KVM**, the combined `OVMF.fd`): the
  images built on kasumi at `7730112` (`images.tar` `9ce47d87…`, the
  tree `git archive`d at that commit `e62f2eea…`), `--images`: three
  rounds of `mpx2-interrupts` and one each of `mpx1`, `mpx2-frames`,
  `mpx2-paging`: **92/92 boots under KVM** (60 + 12 + 16 + 4), 24 PASS
  a round + 20 + 36 + 24, 0 FAIL, 0 SKIP lines (`hasu-kvm.log`
  `f33e46d9…`).

### Serial transcripts (normalised, CI run 37188919348, native BIOS)

kmain_text_write (`02a6d4a9…`):

    PAX paging: write to text
    paging: limine cr3 0x000000000ff67000, pax cr3 0x0000000000105000, 8 table frames
    write: text at 0xffffffff80000040
    PANIC page fault vector 14 error 0x0000000000000003 rip 0xffffffff80007b63 rsp 0xffff80000ff5ff70 frame 0xffff80000ff5fec0 cr2 0xffffffff80000040

kmain_ud2 (`c904048e…`):

    PAX interrupts: ud2
    PANIC invalid opcode vector 6 error 0x0000000000000000 rip 0xffffffff800002cc rsp 0xffff80000ff6efb8 frame 0xffff80000ff6ef00

kmain_int3 (`027eea4a…`):

    PAX interrupts: int3
    gdt: 0xffffffff80006000, 7 descriptors, tss 0x28 at 0xffffffff80006040, ist1 0xffffffff800060d0 to 0xffffffff8000a0d0
    idt: 0xffffffff80005000, 256 gates, 48 routed, #DF on ist1
    int3: breakpoint vector 3, rip 0xffffffff800002cb
    int3: returned, 1 breakpoint
    halt

kmain_double_fault (`6b77fe52…`):

    PAX interrupts: double fault
    paging: limine cr3 0x000000000ff67000, pax cr3 0x0000000000105000, 8 table frames
    gdt: 0xffffffff8000c000, 7 descriptors, tss 0x28 at 0xffffffff8000c040, ist1 0xffffffff8000c0d0 to 0xffffffff800100d0
    idt: 0xffffffff8000b000, 256 gates, 48 routed, #DF on ist1
    PANIC double fault vector 8 error 0x0000000000000000 rip 0xffffffff800002d6 rsp 0x0000000000001000 frame 0xffffffff80010020

kmain_timer (`53c52349…`; release UEFI `072f84f5…` reads `lint0
0x0000000000010700 -> …`):

    PAX interrupts: timer
    paging: limine cr3 0x000000000ff66000, pax cr3 0x0000000000105000, 8 table frames
    apic: 0x00000000fee00000 at 0xffffb00000000000, id 0, svr 0x00000000000001ff, lint0 0x0000000000018700 -> 0x0000000000008700
    timer: pit divisor 11932 (99.998 Hz), 8259 at 32 and 40, line 0 unmasked
    timer: 20 ticks on vector 32, 0 spurious
    halt

### Monitor transcripts (the same run, native BIOS)

kmain_int3 halted, `info registers` (`.cmd1`):

    CS =0008 0000000000000000 ffffffff 00af9a00 DPL=0 CS64 [-R-]
    SS =0010 0000000000000000 ffffffff 00cf9300 DPL=0 DS   [-WA]
    TR =0028 ffffffff80006040 00000067 00008900 DPL=0 TSS64-avl
    GDT=     ffffffff80006000 00000037
    IDT=     ffffffff80005000 00000fff

kmain_text_write halted: `CR0=80010011 CR2=ffffffff80000040
CR3=0000000000105000 CR4=00000020`. kmain_double_fault halted:
`RSP=ffffffff8000feb8` (on IST1). Every file is in the run's
`pax-mpx2-interrupts-linux` artifact, with `mpx2-interrupts-runs.txt`
(each log's and ISO's sha256).

### Filed

- **wolf-lang#577** (new): a store to a field of a raw element (`f[0].rip
  = v`) is "assignment through this place shape" on native, release and
  checked. `kernel/interrupts` only reads the frame; the wolf-lang
  witness writes RIP through `f as *u64` at `offset_of(Frame, rip) / 8`.
- **wolf-lang#579** (new): a `pub const` read from another module
  (`timer.MASTER_BASE`) is refused on native, release and checked;
  lupin runs it. `kernel/timer` exports `master_base()`, `slave_base()`,
  `divisor()` instead.
- **wolf-lang#572**, **#575** (commented): `kernel/apic`'s dead returns
  after `panic.fail`; IA32_APIC_BASE's bits 51:12 and LINT0 without a
  bitwise complement.

## px01–px03 workarounds retired

- **`boot/limine.S`, both routines**: `kernel/boot_info` names the six
  Limine requests and `kernel/paging` the section bounds with `extern
  "c" let` (wolf-lang kw09); the file is gone from the tree and from
  `wolf.pkg`.
- **#560 (literals for constants)** and **#529 (state threaded)**:
  retired in this lane's code — `kernel/gdt`, `idt`, `timer`, `apic` and
  `interrupts` use module `const`s and keep their counters in module
  `var`s. px01–px03's modules (`serial`, `frames`, `paging`) still
  spell literals and thread `st`; refactoring them was not this lane's.

## What the scheduler and heap lanes inherit

- **Every kernel loads its own GDT, TSS and IDT first**
  (`interrupts.start()`); any exception in kernel code panics by name
  with its vector, error code, RIP, RSP and frame (CR2 for #PF) and
  halts with interrupts off. The kernel runs with IF clear except
  inside `timer.wait()` (`STI; HLT; CLI`).
- **The trampoline** (`boot/isr.S`): one macro per vector 0-47, the
  176-byte frame (`[abi.interrupt]`), `pax_interrupt(f: *Frame)` in
  `kernel/interrupts`. It restores from the frame it built. A
  preemptive switch needs the handler to name the frame to resume:
  `pax_interrupt` returning a `*Frame` and the common path moving it to
  `%rsp` before the pops is the one-instruction change; each task then
  needs its own kernel stack holding a frame.
- **The timer**: the PIT at 99.998 Hz on vector 32 through the 8259 and
  the APIC's LINT0 (virtual wire); `timer.tick()` counts and EOIs.
  **The local APIC is mapped** uncached at `0xffffb00000000000` (PML4
  slot 352, `kernel/apic`: `read(offset)`, LINT0 already ExtINT): the
  scheduler's per-CPU timer is the APIC's LVT timer (0x320, divide
  0x3e0, initial count 0x380, EOI 0xb0), calibrated against this PIT.
  Masking the 8259's line 0 hands the tick over.
- **The GDT** has user data 0x18 and user code 0x20 in SYSRET's order
  and a TSS with no RSP0 yet: the ring-3 lane sets `rsp0` (kernel/gdt's
  `Tss`, written whole: wolf-lang#577 forbids a field store through the
  pointer) and the STAR/LSTAR MSRs.
- **The heap**: PML4 slot 352 is now taken (devices). Free virtual
  space is everything but 256 (HHDM), 320 (the paging test's scratch),
  352 (devices) and 511 (the image). A demand-paging heap hooks vector
  14 in `pax_interrupt` (today it panics); the IST1 stack is 16 KiB in
  `.bss`, for #DF only.
- `tools/qemu-fault` (px03) is no longer used by CI (G7 moved to I1);
  it remains the harness for any test that must stop on a triple
  fault.
