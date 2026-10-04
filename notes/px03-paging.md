# px03 — paging (M-PX2's second piece)

Contract: `sprints/pax/03-paging/px03-paging.md` in wolffe-lang/wolf
(planning trunk `22eeece`). Branch `px03` off pax `531ae59`; PR pax#6.
The five sections are committed whole in `98704e2` (an empty commit,
before the first change); this note carries §2's drift, §3 against what
was measured, and §4.

## 1. Forbidden

As committed in `98704e2`. Kept: no Linux, glibc or other kernel source
read (the refs clone was not opened; the paging structure is from the
Intel SDM vol. 3A ch. 4 and the AMD64 APM vol. 2 ch. 5, by section, in
`docs/SOURCES.md`); nothing installed on any host; no build on nomad-1
(it edited, pushed and read CI); kasumi under `~/lanes/px03/` only; hasu
under `~/lanes/px03/` through `nix-shell -p qemu nasm` (plus
`nix-build '<nixpkgs>' -A OVMF.fd` for the combined firmware, as px01
and px02 did); jobs started with `setsid` and waited on by done-file;
no issue closed.

## 2. Inputs, verified (drift)

Re-derived 2026-10-04 and stated in `98704e2`. Drift against the
contract's §2: wolf-lang trunk has moved to `9bf6a5d5` (the pin stays
`eb955c3b`); kw08 is an open PR (wolf-lang#573), kw09 has none, so the
section bounds come from assembly (`boot/limine.S`'s `pax_image_bounds`
over `boot/kernel.ld`'s symbols) and the state is threaded. px02's
staged wolf on kasumi had been pruned; px03 built `eb955c3b` again in
`~/lanes/px03/cache`. Found while working: CI's QEMU (Ubuntu's 8.2) has
no `$cr3` in monitor expressions ("unknown register", run
37180318852), which 11.1 has; `tools/qemu-halt` substitutes `{cr3}`
from the monitor's own `info registers` instead.

## 3. Prediction against measurement

| predicted (`98704e2`) | measured |
|---|---|
| frames the tables cost: BIOS P = 8..11 | **8** (kasumi, CI, hasu): PML4, image PDPT/PD/PT, HHDM PDPT/PD, 2 HHDM PTs (the first 2 MiB and the image's 2 MiB) |
| UEFI P = 11..18 | **9** on CI's OVMF, **10** on kasumi's and hasu's: wrong, OVMF's runs leave only 3–4 partly covered 2 MiB chunks, not 5–12 |
| round trip adds 3 tables, uses 2 frames | as predicted (`map: …, 3 table frames`) |
| text R-X, rodata R--, data RW-, US 0, PWT/PCD 0 | as predicted: `info tlb` `----A----` text, `X---A----` rodata, `X---A---W` data (D never set: the kernel writes no `.data`/`.bss`, it has no module state) |
| HHDM: 2 MiB where whole, 4 KiB edges, RW NX, no image alias, no framebuffer | as predicted: 126 2 MiB entries on BIOS, 4 KiB at the edges (about 1010 entries in all on BIOS, 1430–1940 on UEFI: CI's OVMF and kasumi's differ), every one `X…W`, none on an image frame |
| CR3 = a usable frame >= 1 MiB from px02's allocator, != Limine's | as predicted: `0x105000` BIOS, `0x104000` UEFI (the first frame after the allocator's state); Limine's `0xff71000`/`0xff7a000` (BIOS), `0xbf9b000`/`0xa5fe000` (UEFI, CI). That Limine's frame is bootloader-reclaimable was not checked |
| CR0 WP+PG, EFER = 0xd00 already (kernel sets nothing), CR4 = 0x20 | as predicted: CR0 `0x80010011`, EFER `0xd00`, CR4 `0x20` (monitor and kernel agree) |
| `info tlb` nothing below 0xffff800000000000; `xp /256gx` of CR3 all zero | as predicted |
| the write: #PF e=0003, CR2 = the address, #GP/#DF, triple fault; `-no-reboot -no-shutdown` pauses; CR2 readable under TCG and KVM | as predicted: `-d int` (TCG) `v=0e e=0003 … CR2=ffffffff80000040`, `check_exception old: 0xe new 0xd`, `v=08`, `check_exception old: 0x8 new 0xd`, `Triple fault` (the last line needs `cpu_reset` in `-d`); `info status` `paused (shutdown)`; CR2 from the monitor under KVM on hasu too |
| every G assertion red at the pre-change head; plant: text writable → G3, G7 red | as predicted (below) |
| wolf limitations: #529, #560, #572; maybe a bit-63 literal, no bitwise NOT | #529, #560, #572 met (commented); the bit-63 literal is accepted (no gap; `no_exec()` uses `1 << 63` anyway); **no bitwise complement** (filed wolf-lang#575) |

## 4. Evidence index

### Assertions, red then green

`tests/mpx2-paging`, CI job `mpx2-paging`, each per tier (native,
release) and firmware (bios, uefi). Red at `9605361` (the test and its
job, before any kernel change): run **37179735101** (job 111369687753),
0 SKIP lines. Green at `e72ddcd`: run **37180541517** (job
111372059959), 32 PASS, 0 FAIL, 0 SKIP lines (mpx2-frames 44 PASS, mpx1
26 PASS, every job success). Strict mode: the pax tests have one skip
path, the UEFI leg without OVMF, which `PAX_REQUIRE_UEFI=1` (set in CI
and in every run below) turns into a failure; no lupin pairing is
involved; SKIP counted in each job's full log.

| | red at `9605361` (37179735101) | green at `e72ddcd` (37180541517) |
|---|---|---|
| G1 build, both kernels, 3 PT_LOADs in bounds | FAIL x4: no kernel/<k>.lu | PASS x4 |
| G2 switch: CR3 = the kernel's, != Limine's; WP, NXE | FAIL x4: no image | PASS x4 |
| G3 sections W^X in `info tlb` | FAIL x4: no image | PASS x4 |
| G4 HHDM direct, RW NX, no image alias, no lower half | FAIL x4: no image | PASS x4 (`info tlb`) + x4 (`xp /256gx` at CR3) |
| G6 map/unmap round trip, kernel and monitor | FAIL x4: no image | PASS x4 |
| G7 write to text: stop, CR2, `-d int` #PF 0003 | FAIL x4: no image | PASS x4 |
| G8 halted | FAIL x4: no image | PASS x4 |
| G5 frames on PAX's structures (tests/mpx2-frames F2–F5) | FAIL x8 on kasumi: head's tests on `9605361`'s kernels (`pre-mpx2-frames.log` `fc4ca3fd…`: F2 kmain x4 no paging line, F2–F5 kmain_frames x4; 0 SKIP); mpx1 A2 FAIL x4 the same way (`pre-mpx1.log` `b1c7358e…`) | PASS: mpx2-frames job 111372060098, 44 PASS (kmain_frames: `65085 = F - P frames` on BIOS) |

The first green attempt, `0bd332d` (run 37180318852), was red on G4's
`xp` only: `$cr3` is unknown to QEMU 8.2's monitor; fixed in `5459797`
(run 37180469105 green).

### The planted break

`288a0de` (commit of its own, pushed alone): `paging.build` maps text
with RW. Run **37180803045**, job 111372807983, red: G3 x4 (text pages
`----A---W`), G7 x4 (no fault stop 120 s after the write; the kernel
printed `write: returned`); G1, G2, G4, G6, G8 PASS; 24 PASS, 8 FAIL,
0 SKIP lines. Reverted in `dc000e3`, green in run 37181356324 (every
job success).

### Runs

- CI (ubuntu-latest, QEMU 8.2, TCG): the runs above.
- kasumi (QEMU 11.1.1, TCG): `tests/mpx2-paging` 32 PASS, `mpx2-frames`
  PASS, `mpx1` PASS on the working tree before the commits; G5's red
  above.
- hasu (nix-shell QEMU 11.1.0, **KVM**, the combined `OVMF.fd`): the
  images built on kasumi at `e72ddcd` (tar sha256 `a532d2f7…`),
  `--images`, three rounds of `mpx2-paging`, `mpx2-frames`, `mpx1`:
  **108/108 boots under KVM** (24 + 48 + 36), 28 + 36 + 20 PASS a
  round, 0 FAIL, 0 SKIP lines. G7 under KVM: CR2 `0xffffffff80000040`
  from the stopped machine's monitor (QEMU logs no exceptions there).

### Serial transcripts (normalised, CI run 37180541517)

kmain_paging, native, BIOS (`f08415aa…`):

    PAX paging test
    frames: 65142 usable, 44 below 1 MiB, 5 allocator, 65093 free
    hhdm: 0xffff800000000000
    paging: limine cr3 0x000000000ff71000, pax cr3 0x0000000000105000, 8 table frames
    image: phys 0x000000000ff7a000, virt 0xffffffff80000000, text 0xffffffff80000000 to 0xffffffff80008000, rodata 0xffffffff80008000 to 0xffffffff80009000, data 0xffffffff80009000 to 0xffffffff8000a000
    cpu: cr0 0x0000000080010011, cr4 0x0000000000000020, efer 0x0000000000000d00
    map: 0xffffa00000000000 to 0x000000000010d000, 3 table frames, read 0x5a5a5a5a5a4a8a5a, write seen at 0x0123456789abcdef
    translate: 0xffffa00000000000 is 0x000000000010d000
    unmap: 0xffffa00000000000 was 0x000000000010d000, then not_mapped
    remap: 0xffffa00000000000 to 0x000000000010e000, read 0x5a5a5a5a5a4aba5a
    gone: 0xffffa00000001000 mapped to 0x000000000010d000 and unmapped, then not_mapped
    halt

kmain_paging, release, UEFI (`2b03e21b…`): the same shape with
`frames: 54796 usable, 159 below 1 MiB, 4 allocator, 54633 free`,
`paging: limine cr3 0x000000000bf9b000, pax cr3 0x0000000000104000, 9
table frames`, image at `0x000000000e729000` (text 6 pages).

kmain_text_write, native, BIOS (`c5953870…`):

    PAX paging: write to text
    paging: limine cr3 0x000000000ff87000, pax cr3 0x0000000000105000, 8 table frames
    write: text at 0xffffffff80000040

### Monitor transcripts (the same run, native BIOS)

kmain_paging halted: `info registers` (`.cmd1`, `d9f8235d…`)

    CR0=80010011 CR2=0000000000000000 CR3=0000000000105000 CR4=00000020
    EFER=0000000000000d00

`info tlb` (`.cmd2`, `0f80ec99…`, 1024 lines), excerpts:

    ffff800000001000: 0000000000001000 X-------W
    ffff800000200000: 0000000000200000 X-P-----W
    ffff80000ff79000: 000000000ff79000 X-------W
    ffff80000ff84000: 000000000ff84000 X-------W      (ff7a000..ff83000, the image, absent)
    ffffa00000000000: 000000000010e000 X---A---W      (the remap; nothing at ffffa00000001000)
    ffffffff80000000: 000000000ff7a000 ----A----      (text, 8 pages)
    ffffffff80008000: 000000000ff82000 X---A----      (rodata)
    ffffffff80009000: 000000000ff83000 X---A---W      (data, bss)

`xp /256gx 0x0000000000105000` (`.cmd3`, `b47108e8…`): 128 lines of
`0x0000000000000000` pairs.

kmain_text_write stopped (`.regs` `f559b91e…`, `.int` `6c46e24f…`):

    RIP=ffffffff800063f5 … HLT=0
    CR0=80010011 CR2=ffffffff80000040 CR3=0000000000105000 CR4=00000020
         0: v=0e e=0003 i=0 cpl=0 IP=0028:ffffffff800063f5 pc=ffffffff800063f5 SP=0030:ffff80000ff7ff70 CR2=ffffffff80000040
    check_exception old: 0xe new 0xd
         1: v=08 e=0000 i=0 cpl=0 IP=0028:ffffffff800063f5 …
    check_exception old: 0x8 new 0xd
    Triple fault
    qemu-fault: STOPPED (paused (shutdown)) after the marker; CR2=ffffffff80000040 RIP=ffffffff800063f5; serial still at 226 bytes; accel tcg; quit -> 0

Every file is in the run's `pax-mpx2-paging-linux` artifact, with
`mpx2-paging-runs.txt` (each log's and ISO's sha256).

### Filed

- **wolf-lang#575** (new): no bitwise complement (`!` is bool-only,
  E0409; no `~`); `kernel/paging` aligns with `x - x % 4096` and spells
  masks as literals. Witness in the issue.
- **wolf-lang#529** (commented): section bounds from `limine.S`'s
  `pax_image_bounds` over linker symbols; `st` and the PML4 threaded.
- **wolf-lang#560** (commented): flag values as zero-argument fns and
  literals.
- **wolf-lang#572** (commented): dead `return`s after `panic.fail` in
  `paging.build`/`switch_to`; "map or panic" spelled `else 9` and a
  sentinel test.

## What the heap and interrupt lanes inherit

- `paging.start(st)` returns the PML4's physical address; the kernel
  runs on it from `kmain` on. `paging.map(st, pml4, va, pa, flags)`
  (4 KiB; flags `paging.writable()`, `paging.no_exec()`, P added),
  `map_large`, `unmap` (INVLPG when `pml4` is live; returns the frame,
  the caller's to free; empty tables are kept), `translate`. Rows
  `out_of_memory`, `misaligned`, `not_canonical`, `already_mapped`,
  `large_page`, `not_mapped`.
- **The heap**: free virtual space is everything not the HHDM
  (PML4 256), the scratch slot the test uses (PML4 320,
  `0xffffa00000000000`) and the image (PML4 511). A heap region in its
  own PML4 slot (e.g. 384) grows by `frames.alloc` + `paging.map`; HHDM
  frames need no mapping at all. 2 MiB pages are never split by
  `unmap` (`large_page`).
- **Interrupts**: Limine's IDTR is limit 0, so any exception is a triple
  fault today; `tools/qemu-fault` reads such a stop (CR2, RIP) under TCG
  and KVM, and is the harness for the first IDT's tests (a #PF handler
  should turn `kmain_text_write`'s stop into a named panic). The GDT is
  still Limine's, in bootloader-reclaimable memory mapped by PAX's HHDM;
  an IDT and TSS of the kernel's own go in `.data` or allocated frames.
  The stack is Limine's (HHDM); `switch_to` refuses to switch if it is
  unmapped.
- Still Limine's and still mapped: bootloader-reclaimable memory (its
  page tables, the GDT, the stack, the responses). Reclaiming it waits
  until a kernel stack and GDT of PAX's own exist.
- Not mapped by PAX: the framebuffer (it wants WC: a PAT choice) and
  the image's HHDM alias (W^X). No user pages, no G bit, CR4.PGE clear.
