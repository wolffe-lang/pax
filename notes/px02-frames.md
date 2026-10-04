# px02 — physical frames (M-PX2's first piece)

Contract: `sprints/pax/02-frames/px02-frames.md` in wolffe-lang/wolf
(planning trunk `347e1c7`). Branch `px02` off pax `1b8945d`, rebased onto
`053d12f` (px04 landed meanwhile; one conflict in `ci.yml`, both jobs
kept); PR pax#5. The five sections are committed whole in `ec56ad3` (an
empty commit, before the first change; first pushed as `92d1eb1` before
the rebase); this note carries §2's drift, §3 against what was measured,
and §4.

## 1. Forbidden

As committed in `ec56ad3`. Kept: no Linux or glibc source read (the refs
clone was not opened); nothing installed on any host; no build on
nomad-1 (it edited, pushed and read CI); kasumi under `~/lanes/px02/`
only; hasu touched only under `~/lanes/px02/` through `nix-shell -p qemu
nasm` (plus `nix-build '<nixpkgs>' -A OVMF.fd` for the combined
firmware, as px01 did); the lupin pin not moved.

## 2. Inputs, verified (drift)

Re-derived 2026-10-04 and stated in `ec56ad3`. Drift: the track index's
px00 row says kasumi is not a QEMU host; it has been since the
2026-10-02 upgrade (QEMU 11.1.1, OVMF, clang 23.1.1). wolf-lang#527
(F3, volatile) is still open although kw07 merged. `tools/fetch-wolf`
at `1b8945d` could only stage a release archive; kw05's source mode was
in history only, so it came back beside the archive mode (below). A
source build of wolf-lang reports `0.2.22+dev.unknown` with no pin
clause unless `WOLF_COMMIT` is set at build time (wolf's dist build sets
it); `fetch-wolf` now sets it, so `--version` names the commit.

**How `tools/fetch-wolf` handles a source pin.** `kernel/wolf.pin` takes
one of two shapes (`tools/lib.sh`, `load_wolf_pin`, which refuses both
or neither): `WOLF_LANG_COMMIT` (a full sha: fetch exactly that commit,
refuse any other HEAD, `cargo build --release -p wolf_driver --locked`
with `WOLF_COMMIT` set, check `--version`'s `pin` clause) or px01's four
release lines (the archive by digest, never built). CI caches the staged
`wolf-*` directory by the pin's hash, without a source pin's `src/`.
Moving to 0.2.23 is deleting `WOLF_LANG_COMMIT` and writing the four
release lines.

## 3. Prediction against measurement

| predicted (`ec56ad3`) | measured |
|---|---|
| BIOS T = 65150..65170 usable frames | **65147–65157** (kasumi, CI, hasu; the four kernels' images differ in size): the low end of the band was 3 frames too high — the exercise kernel's image is the largest |
| UEFI T = 51000..54000 | 53784–53794 on kasumi's OVMF, **54792–54804 on CI's** and 54860–54863 on hasu's: inside the band on kasumi only; OVMF builds differ by ~1000 frames |
| L = 100..160 below 1 MiB, both firmwares | UEFI **159** (in); BIOS **44** (wrong: Limine keeps most of the low 640 KiB as bootloader-reclaimable under SeaBIOS) |
| span <= 65536 frames on both | yes: the highest usable byte is below `0x10000000` on both |
| S = 5 frames on both (64 + 2 x 8192 bytes) | BIOS **5**; UEFI **4** (wrong: OVMF's highest usable frame is lower, so the span needs <= 1020 words a bitmap) |
| bitmap, next-fit | as predicted |
| every assertion red at the pre-change head | F1 for the three new kernels, F2–F7 all red; F1 and F8 for `kmain` green there (kmain existed and halted) |
| wolf limitations: #529, #560, linker symbols, maybe error rows | #529 (both halves) and #560 met; error rows compile on the freestanding target on both tiers (no gap); new: no diverging fn (wolf-lang#572) |

## 4. Evidence index

### Assertions, red then green

`tests/mpx2-frames`, CI job `mpx2-frames`, each per tier (native,
release) and firmware (bios, uefi). Red at `e220549` (the test and its
job, before any kernel change): run **37174671928** (job 111354709419),
0 SKIP lines. Green at `4197947`: run **37175103966** (job
111355992584), 44 PASS, 0 FAIL, 0 SKIP; again at the revert `46a2529`:
run **37176013007**, 44 PASS (mpx1 26 PASS in the same run).

| | red at `e220549` (37174671928) | green at `4197947` (37175103966) |
|---|---|---|
| F1 build, kmain_frames / double_free / free_unusable | FAIL x6: no kernel/<k>.lu | PASS x6 |
| F1 build, kmain | PASS x2 (existing kernel) | PASS x2 |
| F2 totals, kmain | FAIL x4: the transcript does not end hhdm, frames, halt | PASS x4: BIOS T=65150 (x4096 = 266854400, the mem line) L=44 S=5 F=65101; UEFI T=54795 L=159 S=4 F=54632 |
| F2–F5, kmain_frames | FAIL x4: the transcript | PASS x4 each: exhaust = F then `out_of_memory`; every check 0; touch F, 0 mismatches; reuse returns the freed frame; free-all restores F; again F |
| F6 double free | FAIL x4 | PASS x4: `PANIC frames: double free 0x0000000000105000` (BIOS), `…104000` (UEFI), halted |
| F7 never usable | FAIL x4 | PASS x4: `PANIC frames: free of a frame never usable 0x<image base>`, halted |
| F8 halted, kmain | PASS x4 | PASS x4 |
| F8 halted, kmain_frames | FAIL x4: no image | PASS x4 |

### The planted break

`2017c5c` (commit of its own, pushed alone): `frames.init` withholds
only frame 0, not the first MiB. Run **37175243641**, job
111356402344, red: F3 `checks: … below 1 MiB 44` on BIOS (the 44 low
frames handed out), F6 red (the first frame allocated is now below
1 MiB, so its first free panics `free of a withheld frame`, not the
double free), F8 red for kmain_frames (the free-all panics on a low
frame); F1, F2 for kmain and F7 PASS; 0 SKIP lines. Reverted in
`46a2529`, green in run 37176013007.

### Runs

- CI: the four runs above (ubuntu-latest, QEMU 8.2, TCG).
- kasumi (QEMU 11.1.1, TCG): `tests/mpx2-frames` 44 PASS on the working
  tree before the commits; `tests/mpx1` 26 PASS and `tests/mkw` PASS with
  wolf `eb955c3b` and the retired readers.
- hasu (nix-shell QEMU 11.1.0, **KVM**, the combined `OVMF.fd`): the
  images built on kasumi at `4197947` (tar sha256 `2b83ffc5…`),
  `tests/mpx2-frames --images`, three rounds: **48/48 boots under KVM**,
  36 PASS a round, 0 FAIL, 0 SKIP.

### Serial transcripts (normalised tail, CI run 37175103966)

kmain, native, BIOS (`778f83ff…`):

    PAX first light
    serial: 16550 at 0x3f8, 115200 8N1, scratch ok, loopback ok
    boot: Limine 12.9.1, base revision 6
    boot: firmware bios
    mem: 18 entries, 266854400 bytes usable
    hhdm: 0xffff800000000000
    frames: 65150 usable, 44 below 1 MiB, 5 allocator, 65101 free
    halt

kmain_frames, native, BIOS (`9ac5ff39…`):

    PAX frames test
    frames: 65147 usable, 44 below 1 MiB, 5 allocator, 65098 free
    image: 0x000000000ff7f000 to 0x000000000ff86428, allocator 0x0000000000100000 to 0x0000000000105000
    exhaust: 65098 frames, then out_of_memory
    checks: misaligned 0, outside usable 0, below 1 MiB 0, in image 0, in allocator 0
    touch: 65098 frames written and read back, 0 mismatches
    reuse: freed 0x000000000ff4e000, alloc returned 0x000000000ff4e000
    free: 65098 frames freed, 65098 free
    again: 65098 frames, then out_of_memory
    halt

kmain_frames, release, UEFI (`d4f83a83…`):

    PAX frames test
    frames: 54798 usable, 159 below 1 MiB, 4 allocator, 54635 free
    image: 0x000000000e72b000 to 0x000000000e731138, allocator 0x0000000000100000 to 0x0000000000104000
    exhaust: 54635 frames, then out_of_memory
    checks: misaligned 0, outside usable 0, below 1 MiB 0, in image 0, in allocator 0
    touch: 54635 frames written and read back, 0 mismatches
    reuse: freed 0x000000000e6b7000, alloc returned 0x000000000e6b7000
    free: 54635 frames freed, 54635 free
    again: 54635 frames, then out_of_memory
    halt

kmain_double_free, native, BIOS (`c5ae5cc4…`):

    PAX frames: double free
    frames: 65150 usable, 44 below 1 MiB, 5 allocator, 65101 free
    free twice: 0x0000000000105000
    PANIC frames: double free 0x0000000000105000

kmain_free_unusable, release, UEFI (`1ae4cb40…`):

    PAX frames: free of a frame never usable
    frames: 54804 usable, 159 below 1 MiB, 4 allocator, 54641 free
    free the image: 0x000000000e731000
    PANIC frames: free of a frame never usable 0x000000000e731000

The other eleven digests are in the run's `mpx2-runs.txt` and the
`pax-mpx2-frames-linux` artifact.

### Filed

- **wolf-lang#572** (new): no way to declare a fn that never returns; a
  kernel panic in a handler arm is E0401, so `frames.start`'s arms write
  a dead `0` after `panic.fail` and `frames.free` a dead `return`.
  Witness in the issue (hosted and freestanding alike).
- **wolf-lang#529** (commented with px02's witness): no symbol address,
  so `boot/limine.S` keeps two address-only routines; no module state,
  so the allocator's state lives in frames it takes and its address is
  passed to every call.
- **wolf-lang#560** (commented; re-measured at `eb955c3b`: a module
  `const` is still "cannot compile this yet — item-initializer
  lowering"): the allocator's constants are literals.
- Lived with, not filed: layouts read at fixed offsets until kw08's
  `offset_of`; `p.addr()` is `uint`, so a `u64` offset is cast
  (`(k * 8) as uint`), which is the spec's typing, not a gap.

## What paging (px03) inherits

- `frames.start()` / `alloc(st)` / `free(st, pa)`: physical frames for
  page tables, zeroing them is the caller's (a frame comes back with
  whatever it held). `st` must be threaded to whoever allocates until
  kw09 gives module state.
- The HHDM is Limine's: usable memory is mapped there now, so a fresh
  page-table frame is reachable at `hhdm + pa` before px03 builds its
  own map. When px03 replaces Limine's tables, it must map the HHDM
  range the allocator's state and every handed-out frame live in, and
  the state's own frames (`frames.state_phys`, `frames.own`) stay
  withheld.
- Bootloader-reclaimable memory (Limine's page tables, its stack, the
  responses `boot_info` still reads) is never handed out; reclaiming it
  is a later lane's, after px03 stops using Limine's tables and copies
  what it needs out of the responses.
- `boot_info.image_phys()`, `image_virt()`, `image_bytes()`: the
  kernel's physical and virtual extent, which px03 maps.
- `panic.fail(what, v)` for named faults; wolf-lang#572 for its callers.
