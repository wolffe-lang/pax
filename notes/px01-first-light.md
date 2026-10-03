# px01 — first light (M-PX1)

Contract: `sprints/pax/01-first-light/px01-first-light.md` in wolffe-lang/wolf
(planning trunk `d34de28`). Branch `px01` off pax `7840d79`; PR pax#3.
The five sections are committed whole in `505ecbf` (an empty commit,
before the first change); this note carries §2's drift, §3 against what
was measured, and §4.

## 1. Forbidden

As committed in `505ecbf`. Kept: no Linux or glibc source read (the
refs clone was not opened); nothing installed on any host; no build on
nomad-1 (it edited, pushed and ran the expect-serial selftest, which runs
no compiler); hasu touched only under `~/lanes/px01/` through
`nix-shell -p qemu nasm` (plus `nix-build '<nixpkgs>' -A OVMF.fd` for the
combined firmware, as px00 and kw05 did); the lupin pin not moved.

## 2. Inputs, verified (drift)

Re-derived on 2026-10-03 and stated in `505ecbf`: wolf v0.2.22 is
wolf-lang `8e36bc1a`, published 2026-10-03T21:37Z, and carries kw05's
`af397195`; its linux x86-64 archive is sha256 `df0f2fea…`. Drift from
the contract:

1. kw05's campaign line expected the pin to move "to 0.2.23+"; 0.2.22
   already carries `asm`, so it moved now (`1b20aba`).
2. lupin stays at 0.1.44 (0.2.22 pairs with 0.1.45): M-KW's step 6
   records lupin's `--target` clap error, wolf-interp#182, open on both.
3. A multi-module kernel under `--emit=obj -o K.o` gets no `K.o`: one
   object per module on native (`K.root.o`, `K.serial.o`, …), one per
   cluster on release (`K.c00.o`, `K.c01.o`). Filed wolf-lang#562;
   `tools/build-kernel` links the set (`80535ee`).
4. Imports are file-scoped and an unused one is an error (E0305): the
   kernel names `panic` (for `panic.halt()`); a module reached only for
   its `export fn` would not be compiled in.
5. `p[i]` through `p: *u8` takes an `int` index (E0401 on `i64`).
6. Met while building, not foreseen: a module-level `const` does not
   compile on either tier (wolf-lang#560); a `str`'s `len()` is
   `std.str`'s and the archive has no std (wolf-lang#563).

## 3. Prediction against measurement

| predicted (`505ecbf`) | measured |
|---|---|
| seven lines: banner, serial, `boot: Limine 12.9.1, base revision 6`, firmware, `mem: N entries, U bytes usable`, `hhdm: 0x…`, `halt` | exactly these, on every boot of both tiers and both firmwares (kasumi, CI, hasu) |
| BIOS: N in 6..10, U in 240..256 MiB | N = **18** (wrong: SeaBIOS's e820 plus Limine's own reclaimable and executable regions), U = 266887168 native / 266895360 release (254.5 MiB, in range; the two tiers' images differ in size) |
| UEFI: N in 15..60, U lower than BIOS, 150..250 MiB | N = 33 (kasumi, QEMU 11.1.1), 30 (CI, QEMU 8.2.2), 32 (hasu, nixpkgs' OVMF.fd); U 210–214 MiB. In range |
| HHDM `0xffff800000000000`, asserted by shape only | `0xffff800000000000` on every boot |
| panic: `PANIC overflow kmain_panic.lu:<L>`; release may lose the site (#555) | `PANIC overflow ./kmain_panic.lu:20` on **both** tiers: the path is wolf's display path (the build runs in `kernel/`), and release kept the site because `pax_big` is opaque to it |
| at the trunk pin, tests/mpx1 fails A2 at line 1 (log ends `KWC`) and A3 (QEMU exits 33) | so, with the final harness against trunk's kernel (kasumi, below). In CI at `09c5eb3` (the test before the kernel) A3/A5/A6 were red for a weaker reason — `qemu-halt` refused to boot an ELF without `pax_halt` (exit 2) — fixed in `c0b15d3`, so a missing symbol now boots and is NOT HALTED |

Halt detection, as argued: QEMU's monitor on a pipe, after the kernel's
last line, `info registers` twice a second apart — RIP inside
`pax_halt` (from `nm -S`), IF clear, HLT=1, the serial log not one byte
longer, QEMU still running. Measured HLT=1 on all 48 probes of halted
kernels under KVM (hasu) and every TCG probe; HLT=0 on all 12 probes of
the spinning kernel.

## 4. Evidence index

### Assertions, red then green

| assertion | red (pre-change) | green |
|---|---|---|
| A1 build, `wolf_trap` defined in wolf | CI 37158227275 (mpx1 job 111306003825, head `09c5eb3`): `wolf_trap is not defined` for kmain on both tiers, kmain_panic absent | CI 37159036758 (job 111308388799, head `1550686`) |
| A2 transcript | CI 37158227275: FAIL ×4; kasumi `mpx1-red-trunk-kernel-c0b15d3.log` `b5bf3b13…`: FAIL ×4, the log ends `KWC` (`mpx1-native-kmain-bios.serial.log` `07cec5c4…`) | CI 37159036758: PASS ×4 |
| A3 halted | kasumi, same log: `QEMU ended (qemu-run status 33) before a line matching /halt/` ×4 | CI 37159036758: PASS ×4 |
| A4 panic line | CI 37158227275 and kasumi: no `kernel/kmain_panic.lu` ×4 | CI 37159036758: PASS ×4 |
| A5 panic halted | the same: no panic kernel ×4 | CI 37159036758: PASS ×4 |
| A6 a spin is refused | the same: the spin variant could not be made (no `panic.halt()` line) ×4 | CI 37159036758: PASS ×4 (`NOT HALTED: RIP … is outside pax_halt`) |

Every red log above has 0 SKIP lines.

### The planted break

`71564b0` made `log.hex` stop one digit early. CI run **37158903272**
(mpx1 job 111307988607): A2 FAIL on both tiers and both firmwares (the
log reads `hhdm: 0xffff80000000000`), A1 and A3–A6 PASS, 0 SKIP lines,
the other three jobs green. Reverted in `1550686`; green again in
37159036758.

### Runs

- **CI** (ubuntu, QEMU 8.2.2, TCG): green at the head before this note,
  run 37159036758 — mpx1 26 PASS / 0 FAIL / 0 SKIP, mkw, proof and
  macos-run green. The wolf step is the archive by digest at every run
  since `b773498` (run 37157947115, M-KW green on 0.2.22).
- **kasumi** (`~/lanes/px01/evidence/`, QEMU 11.1.1, TCG):
  `mpx1-kasumi-1550686.log` `fdbb83a8…` (26 PASS, rc 0),
  `mkw-kasumi-1550686.log` `6b244e72…` (rc 0), the serial logs, halt
  records and verdicts under `kasumi-1550686/`. Kernels:
  native `kmain.elf` `f39d5196…`, `kmain_panic.elf` `4d4384e5…`;
  release `kmain.elf` `8d6222ef…`, `kmain_panic.elf` `dfe6902b…`
  (`mpx1-images.tar` `bf5f3ea3…`, the source `pax.tar` `9a2bd807…` —
  `git archive` of `1550686`).
- **hasu** (`~/lanes/px01/`, KVM, nixpkgs' QEMU and combined `OVMF.fd`):
  the kasumi-built images above, `tests/mpx1 --images`, three rounds
  `run-f1.log` `08f3d971…`, `run-f2.log` `dca83bcb…`, `run-f3.log`
  `38514a41…`: 20 boot assertions PASS each (36 boots), 0 FAIL, 0 SKIP;
  `logs-f1/mpx1-runs.txt` `501d528c…`. Three earlier rounds (`r1`–`r3`)
  on `46eb8a7`'s images, also all PASS, are where HLT=1 under KVM was
  measured before it was asserted.

### Serial transcripts (normalised tail)

BIOS, native (kasumi `b1ddc495…`):

    PAX first light
    serial: 16550 at 0x3f8, 115200 8N1, scratch ok, loopback ok
    boot: Limine 12.9.1, base revision 6
    boot: firmware bios
    mem: 18 entries, 266887168 bytes usable
    hhdm: 0xffff800000000000
    halt

UEFI, native (kasumi `532a255a…`): the same but `boot: firmware uefi64`
and `mem: 33 entries, 220344320 bytes usable`. Panic kernel (UEFI,
release, kasumi `ef85e71d…`):

    PAX first light (panic kernel)
    PANIC overflow ./kmain_panic.lu:20

### Filed

- wolf-lang#560 — a module-level `const` is refused on native and release
  (item-initializer lowering), unsupported on checked; lupin runs it.
  PAX writes the literals inline with a comment naming each.
- wolf-lang#562 — `--emit=obj -o K.o` writes no `K.o` for a multi-module
  build (`K.<module>.o` native, `K.cNN.o` release), undocumented.
  `tools/build-kernel` links the set by glob.
- wolf-lang#563 — on `x86_64-unknown-none` a `str`'s length has no
  spelling (`len()` is `std.str`'s; the archive has no std). Nothing in
  the kernel needs it yet.

Already open and lived with, not re-filed: #527 (KWC F3, volatile) and
#531 (F9, int-to-pointer) — Limine's responses are read in
`boot/limine.S`; #529 (F6, module-level state) — no recursion guard in
`wolf_trap`; #555 — not met (release kept the site).

## What P2 inherits

- `kernel/serial`, `kernel/log`, `kernel/boot_info`, `kernel/panic`; the
  console is polled, interrupts are off, the IDT is empty.
- The memory map and HHDM offset as integers through `boot/limine.S`.
  Physical frames (P2's first need) can be built on `boot_info.memmap_*`
  today; walking or writing memory through the HHDM needs kw06
  (int-to-pointer) and kw07 (volatile), or more assembly.
- `tools/qemu-halt` for any test whose kernel ends in a halt, and
  `expect-serial --regex` for transcripts with machine-dependent numbers.
- `tools/build-kernel` links whatever set of objects wolf writes; if
  wolf-lang#562 is ruled toward one object, the glob can go.
- `boot/stub/` and `tests/proof` (px00's assembly proof) are still in the
  tree and in CI; CLAUDE.md says px01 retires the stub, but the contract's
  items did not ask it, so the retirement is left to a later lane.
