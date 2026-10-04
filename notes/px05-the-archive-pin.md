# px05 — the archive pin, and the workarounds retired

Contract: `sprints/pax/05-the-archive-pin/px05-the-archive-pin.md`
(planning trunk `bd1dfa2`); its five sections are the empty commit
`b2b739c`, committed before the first change. Branch `px05` off
`29d21c0` (kw10), PR pax#8.

## What changed

- **The pin.** `kernel/wolf.pin` is the wolf 0.2.23 release archive by
  digest (`WOLF_VERSION`, `WOLF_URL`, `WOLF_SHA256` `6f505eb5…`,
  `WOLF_PIN_COMMIT` `8edac3ee…`), no source pin. CI's five wolf cache
  steps are gone: every job fetches the archive and checks its digest.
  lupin stays at 0.1.44 (see Drift 2). `tools/fetch-wolf` keeps its
  source shape, dormant, for the next feature a release does not carry.
- **The workarounds, by file.**
  - `kernel/serial/serial.lu`: COM1's base, the register offsets (THR,
    IER, FCR, LCR, MCR, LSR, SCR, DLL, DLM), the LCR/FCR/MCR values, the
    LSR bits, the scratch and loopback patterns and the poll bound are
    module `const`s (px01's commented literals, wolf-lang#560). `put`
    reads LSR through `inp` instead of a hand-added `1021`. No state,
    no struct offsets.
  - `kernel/frames/frames.lu`: the state's address is the module `var
    state`, set once by `init`, read through one unsafe accessor `st()`
    (px02 returned it from `init` and every function took it,
    wolf-lang#529). The header is `#[repr(c)] struct FrameState` (eight
    `u64`s), each field read and written as a scalar at its
    `offset_of` (`[abi.layout.query]`; px02's `st + 0` … `st + 56`), the
    bitmaps at `size_of(FrameState)`. 4096, 1 MiB, 256, 64, 8, the magic
    and the usable type are `const`s. The API lost `st`: `alloc()`,
    `free(pa)`, `report()`, `hhdm()`, `free_count()`, …; `start()` still
    returns the state's address, which no caller needs to keep.
  - `kernel/paging/paging.lu`: P, RW, PS, NX, the two address masks,
    4 KiB, 2 MiB, 512, the entry size, the shifts, the canonical top,
    EFER.NXE, CR0.WP, CR4.PGE and the five memory-map types are
    `const`s (px03's literals). `st` left every signature: tables come
    from `frames.alloc()`, the HHDM from `frames.hhdm()`. The PML4 stays
    an argument (`build` fills structures that are not live).
    `present`/`writable`/`no_exec` stay `pub fn`s (wolf-lang#579).
    Paging lays out no struct at fixed offsets, so it has no `offset_of`
    site.
  - Callers: `kernel/apic` (`start(pml4)`), and every `kmain*.lu` that
    allocates or maps (eight kernels).

## Drift (re-deriving §2)

1. The contract said 0.2.23 is newer than `6a4e6151` "only by s208 and
   kw10". s208 (`9bf6a5d5`) is already an ancestor of `6a4e6151`. The
   difference is kw10 (`6aaf7f25..07a4a784`) and r28's release commits
   (`641f0400..8edac3ee`), and no file under `crates/*/src` changed.
2. lupin. The pin held 0.1.44 for wolf-interp#182, which 0.1.46 fixes
   (#182 CLOSED). Moving it changes `tests/mkw` step 6's `lupin-target`
   row, which asserts 0.1.44's clap error. Measured on kasumi, 0.1.46
   (`d13a0379…`) answers `{"verdict":"unsupported","x-unsupported":"the
   freestanding target x86_64-unknown-none"}`. A changed assertion is
   outside this contract, so lupin stays 0.1.44 and the move is a later
   lane's.

**CI time.** Each kernel job now takes 1–2 minutes, against about 7 on
trunk's run 37191531201. That run compiled wolf from source in every
job (`Compiling proc-macro2…` in its log: the source pin's cache missed);
the archive is a download and a digest check.

## Prediction against measurement

| predicted (b2b739c) | measured | verdict |
|---|---|---|
| pin: every lane ELF byte-identical to trunk's run 37191531201 | 16 release ELFs byte-identical; 16 native ELFs (mkw's 3 included) identical in `.text`, `.rodata`, `.data`, differing only in the DWARF producer string (`wolfgang 0.2.22` → `0.2.23`, one byte per compile unit, 1–12 bytes): the source build at `6a4e6151` still carried 0.2.22's version | right in substance, wrong in letter |
| pin: no transcript line moves; PASS counts unchanged | kasumi 17/27/45/27/35 PASS, 0 FAIL, 0 SKIP = run 37191531201's counts; CI 37228806932 green | right |
| sizes: no section start moves; native `.text` ±2%; release ±2%; `.rodata` ±64 B; `.bss` +8 | native `.text` −2.0% to −5.3% (`kmain` 35526 → 33740; −2.0% even in `kmain_panic`, `kmain_int3`, `kmain_ud2`, which link no frames: serial's change alone), release −9.8% to +6.2% (`kmain_frames` 28767 → 25935, `kmain_double_free` 11647 → 12368); section starts moved a page in 6 kernels (native double_fault, text_write, paging; release double_free, frames, double_fault); `.rodata` within 34 B; `.bss` +8 where frames links; native `.data` +8 too | wrong: the dropped parameter saved more than the accessor cost on native, and LLVM inlined differently on release |
| so no transcript line moves | 43 of 64 CI transcripts identical, 21 moved, every moved line an address or a count (below) | wrong, explained |
| S stays 5; pax cr3 and table-frame counts unchanged | S 5 / 4, pax cr3 `0x105000` / `0x104000`, P 8 / 9 everywhere | right |

## Every transcript line that moved, and why

Compared: CI run 37191531201 (trunk `29d21c0`) against 37229667793
(head `7678dc6`), 64 serial logs normalised, firmware banners dropped.
The image and the kernel file changed size by whole pages. Limine loads
both at the top of RAM, so:

- **Counts** (`frames:` T and F; `exhaust`, `touch`, `free`, `again`):
  T moves by −(Δ image pages + Δ ELF file pages) in all 28 transcripts
  with a `frames:` line (0 disagree). For example, release `kmain_frames`:
  image 15 → 14 pages, file 12 → 11, so T +2 and F, touch, free and
  again +2. Native `kmain_double_free`: file 14 → 15, so T −1. L, S and
  P never move.
- **Addresses Limine chose**: `limine cr3`, `image: phys`, `image:
  0x… to 0x…`, `free the image`, `reuse: freed`, and a panic's `rsp` and
  `frame` on Limine's stack all move with the same page delta.
- **Addresses the linker chose**: where native `.text` shrank across a
  page (`kmain_double_fault`, `kmain_text_write`, `kmain_paging`),
  rodata, data and bss start a page lower, so the `gdt:` and `idt:`
  lines, the IST1 bounds, the double fault's frame and `kmain_paging`'s
  section ranges move by 0x1000. `kmain_text_write`'s panic `rip` moves
  because the code moved (`…7b63` → `…7555`). Its vector, error 0x3 and
  CR2 `0xffffffff80000040` do not.

## Assertion table, red then green

The plant `7ccf0b4` makes `frames.own()` read `FrameState`'s `low`
field: the wrong-`offset_of` bug this lane's change could introduce. It
went red in CI run **37230193011**:
- mpx2-frames job 111518058441: F2 `S=44` on both tiers, then F2–F5,
  F6 and F8; 16 PASS, 25 FAIL, 0 SKIP lines.
- mpx2-paging job 111518058592: G2–G6 and G8, because `kmain_paging`'s
  last free panics as withheld; 2 PASS, 13 FAIL, 0 SKIP lines. Log
  `551a60e6…`.

mkw, mpx1 and mpx2-interrupts stayed green: mpx1's A2 matches the
`frames:` line's shape, not its sum. Reverted in `a25d3fc`, whose tree
is `7678dc6`'s.

## Evidence index

- CI runs:
  - `47e3fad` (pin): 37228806932 green.
  - `fcb2396` (serial): 37229273148 green.
  - `524aa90` (frames): 37229368144 green.
  - `7678dc6`: 37229667793 green, for `ef513b1` (paging) and the docs,
    pushed together; the kernel tree is the same.
  - `7ccf0b4` (plant): 37230193011 red.
  - `a25d3fc` (revert): 37231156348 green.
  - `ff7c1e0` (this note's first version): 37231280975 green. Same
    PASS counts as trunk (mkw 17, mpx1 27, mpx2-frames 45, mpx2-paging
    27, mpx2-interrupts 35), 0 FAIL, 0 SKIP; log `cc036d38…`.
  - Trunk baseline: 37191531201.
- kasumi (QEMU 11.1.1), every suite plus census and the selftest, in
  parallel, one tree each, `PAX_REQUIRE_UEFI=1`, full logs under
  `~/lanes/px05/runs/<tag>/`. All rc 0, with 17/27/45/27/35 PASS, 0 FAIL
  and 0 SKIP lines each round. Log digests by round:
  - pin `7a504436…`
  - serial `d11921a7…`
  - frames `76444423…` (tree `086b233`, = `524aa90`)
  - paging `a060d526…`
  - head `fc7165e2…`
- hasu (nix-shell QEMU 11.1.0, KVM, the combined `OVMF.fd`): the head
  images built on kasumi (`images.tar` `143a6a1b…`, 32 ISOs), `--images`,
  three rounds each of mkw, mpx1, mpx2-frames, mpx2-paging and
  mpx2-interrupts. **192/192 boots under KVM**, every run rc 0, 0 FAIL,
  0 SKIP lines (`hasu-kvm.log` `da365e25…`).
- Size table and transcript diff: `sizes.sh` and `tcheck.sh` over the
  two runs' artifacts (method above).

## Inherited by the heap lanes (kw12 + a pax lane) and the scheduler

- `frames` is a module with its own state: `frames.start()` once, then
  `alloc()`/`free(pa)` from anywhere. There is no guard before `start`:
  `st()` is 0, so a call reads near address 0 and panics `page fault` by
  name (kw10). Frames come back unzeroed.
- `paging.map/map_large/unmap/translate(pml4, …)` take no allocator
  state. The live PML4 is what `paging.start()` returned. No module
  `var` holds it yet: a heap that maps on demand either keeps it or adds
  one accessor the same way.
- The pattern for kernel state: a scalar module `var` behind one unsafe
  accessor. Structured state lives in memory the module owns, with a
  `#[repr(c)]` header read and written at `offset_of`, because module
  state holds scalars only (`[mem.static.3]`) and `p[0].f = v` is still
  refused (wolf-lang#577).
- A `pub const` read from another module is still refused
  (wolf-lang#579): export it as a `pub fn`. There is still no `~`
  (#575) and no never-returning fn (#572).
- `kernel/boot_info` still reads Limine's structures word by word at
  fixed offsets. `#[repr(c)]` mirrors at `offset_of` are the same
  retirement for the next lane that touches it.
- Addresses in transcripts move whenever the image crosses a page.
  Every test matches them by pattern, and a lane that adds code will
  see them move again, by the rule above.
- The scheduler inherits kw10's list unchanged (the trampoline must
  return the frame to resume; the TSS has no RSP0; free virtual space
  outside PML4 slots 256/320/352/511).
- lupin 0.1.46: a lane of its own, changing `tests/mkw` step 6's
  `lupin-target` row to the record above.

## Sources

`docs/SOURCES.md`, px05: the wolf spec's `[abi.layout.c]`,
`[abi.layout.query]` and `[mem.static]`, two wolf-lang witnesses, and
the release digests. No Linux, no glibc, no other kernel.
