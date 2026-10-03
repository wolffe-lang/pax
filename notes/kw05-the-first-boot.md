# kw05 — the first boot (M-KW)

Lane note. **Class:** large (wolf-lang + pax), Opus. **Contract:**
`sprints/compiler/91-freestanding/kw05-the-first-boot.md` in the planning
repo (trunk `59aa2ec`). Two PRs that name each other: wolf-lang#557 (`asm`
in `wolf.pkg`, K2 = C's linked half) and pax#2 (this branch, M-KW). The
five sections were committed before any change, as the empty commits
`8123e1c` (pax) and `e89526c1` (wolf-lang); this note is §4.

## Forbidden (summary of §1)

No Linux kernel or glibc source read (none was; `docs/SOURCES.md`). QEMU on
hasu only through `nix-shell -p qemu nasm` under `~/lanes/kw05`; nothing
installed anywhere. No build on nomad-1. No seen-red without a run id, path or
digest; a red with SKIP lines is not red.

## M-KW, step by step (kw00 §3e), red then green

Trunk is wolf-lang `a2e16bf8`; head is wolf-lang `af397195` (kernel/wolf.pin).
Both tiers are wolf's native (Cranelift) and release (LLVM) tiers.

| step | trunk, native / release | head, native / release |
|---|---|---|
| 1 inputs | `kernel/wolf.pkg`'s `asm` is `error[E1502]: unknown manifest key` | `kernel/{kmain,kmain_trap}.lu`, `wolf.pkg`, `boot/{io.S,start.S,kernel.ld}` |
| 2 object | exit 2 (E1502) / exit 2: no object | exit 0 / 0; `kmain.asm-io.o` beside each object; `nm -u` {pax_exit, pax_outb, wolf_trap} / {pax_exit, pax_outb} (the trap kernel adds pax_big, and wolf_trap on both); `kmain` T; no `main`; no xmm/ymm; nothing below %rsp; release IR noredzone + no-SSE on every define |
| 3 link | nothing to link | `ld.lld -T boot/kernel.ld start.o kmain.asm-io.o kmain.o`: three PT_LOADs at 0xffffffff80000000 (r-x, r--, rw-) |
| 4 run | no image | SeaBIOS and OVMF: status 33, the serial log ends `KWC` / the same |
| 5 trap | no image | status 3, the serial log ends `TRAP 1` / the same |
| 6 machines | `wolf conform-run --checked`: unsupported `checked execution without a \`main\` entry`; with `--target`: unsupported `the freestanding target x86_64-unknown-none`; lupin 0.1.44: unsupported `the program has no \`main\` …`; lupin `--target`: clap `unexpected argument`, exit 2 (wolf-interp#182) | unchanged, asserted as records in `tests/mkw` |
| 7 seen red | (the build is already red) | in every run: no `--target` → refused for want of a `main` (exit 4); `KWD` boots with status 33 and fails `expect-serial --tail KWC` |

## Evidence index

**CI (pax).**
- Red at the trunk pin: run 37144295614 (head `a312b8d`, pin `a2e16bf8`):
  the mkw job fails every build at step 2 with E1502 on both tiers; 0 SKIP
  lines in its log (sha256 `a40c4890…` of the job's lines).
- Green at the kw05 pin: run 37144773740 (head `2839130`, pin `8ca0771f`),
  mkw job 111266336135: every step PASS, both tiers, BIOS and UEFI, TCG on
  QEMU 8.2.2; 0 SKIP lines (log `0f006cc7…`); wolf built from source in 4m08s.
- Planted break: `2f67e71` (kmain prints KWD), run 37145535842, mkw job
  111268565831: step 4 FAIL on both tiers and both firmwares, the log ends
  `KWD`; 0 SKIP lines (`390c06b9…`). Reverted in `96a280c`; run 37145641994
  green (proof, mkw, macos-run).
- Green at the head pin `af397195`: run 37146439751 (head `84a71ff`).

**kasumi** (`~/lanes/kw05/evidence/`).
- `rederive-trunk-a2e16bf8.log` `dc41ddf6…`: kw00 §3e's inputs at trunk.
- `pax-mkw-trunk-a2e16bf8.log` `8940b77f…`: `tests/mkw --no-boot` with
  trunk's wolf, rc 1, E1502 at step 2 on both tiers, 0 SKIP lines.
- `pax-mkw-build-84a71ff.log` `38147bc6…`: the same at the head (wolf
  `af397195`, `SOURCE_DATE_EPOCH` the head's commit time), rc 0; the ISOs
  (`mkw-images.tar` `04d732b5…`) are the ones hasu booted.

**hasu** (`~/lanes/kw05/`, KVM, QEMU 11.1.0, nixpkgs' combined `OVMF.fd`).
- `run-final.log` `c73c0bb7…`: `tests/mkw --images`, 12 boots, all PASS
  (BIOS 0.21–0.32 s, UEFI 0.51 s), `MKW rc=0`; serial logs and their
  `.meta` under `logs-final/` (`mkw-runs.txt` `adfe462e…`). The serial logs'
  digests: kmain BIOS `d84d2cbb…`, kmain UEFI `f356302e…`, trap BIOS
  `b8bda15a…` (release) and `48a31dad…` (native: Limine wrote one extra
  `ESC [01;01H` before the kernel's line — normalised away; the kernel's
  bytes are the same), trap UEFI `42a50d1d…`, KWD BIOS `b4a1cbf6…`, KWD UEFI
  `d73dbee4…`.
- `run-wip1.log`: the same 12 boots on the pre-commit tree, all PASS.

**Images and objects** (kasumi, head): kmain.elf native `a503f4b8…`, release
`9f2f3233…`; kmain_trap.elf native `4dbb8bce…`, release `da978473…`. ISOs
are reproducible per toolchain, not across (px00's finding), so CI's digests
differ from kasumi's.

## Found on the way

- `expect-serial` matched lines anywhere; "serial exactly KWC" needs the
  log's tail, because SeaBIOS and OVMF write to COM1 before Limine hands
  over. `--tail` added, with selftest rows that must fail.
- `tools/build-kernel --hosted` first accepted any refusal; at the trunk pin
  E1502 passed it (run 37144295614). It now requires the refusal for want of
  a `main` (`6a748ad`).
- Two kernels in one directory are one module (D32): both carry
  `//! member: false`.
- kasumi has QEMU since 2026-10-02; this lane still booted on hasu and CI.

## What px01 inherits

A wolf `kmain` that Limine enters through `boot/start.S`, with port I/O and
the trap hook in `boot/io.S` (listed under `asm`, so every routine the kernel
calls is on the roster, E1306 otherwise); `tools/build-kernel` and
`tests/mkw`; the pin in `kernel/wolf.pin` (one line to move to the merged
wolf-lang commit, and to a release once one carries `asm`). Not yet there:
volatile reads of Limine responses (kw07), section placement (kw09), an IDT
(kw10), allocation (kw12). `pax_outb` does not poll the UART's LSR; real
hardware needs it.
