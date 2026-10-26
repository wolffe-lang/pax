# as02b — the image seam and the package

Crawl 54, Claude Opus 5.5, contract `wolf/sprints/clef/02-the-package-path/as02-the-package-path.md`
(as02b's half; as02a, wolf-lang#957, merged at `9f2cff44`). kasumi CPUs 0–3 under
`~/lanes/kasumi-cores-0-3.lock`, taken per job; every build and boot in clef's pinned integration
image (`localhost/clef-integration:52846d3b65aeafca`, built on kasumi by clef's own
`tools/in-container` and `tools/integration-image` at `996a3ccd`), the Linux sides on the kasumi host
(rootless podman). Branch `as02b` from trunk `77d7b00c` (px80's note). The kernel's sources are
unchanged: nothing under `kernel/` or `boot/` moves.

Footprint: cross-cutting

## Prediction

Committed first: `a62b1cdf` (`notes/as02b/prediction.txt`). Measured before it and not predicted:
wolf 0.2.35 answers `--assembler` with "unknown flag", status 2; clef's own build line makes a
14,213,232-byte dynamic binary with three DT_NEEDED entries.

| | predicted | measured | score |
|---|---|---|---|
| P1 | the package ET_EXEC, no PT_INTERP, no dynamic section, 0 DT_NEEDED; 14.6–16.5 MB, point 15.2 MB; three build inputs by digest, no std | 15,370,648 bytes (stripped 1,819,608, not installed), 0 DT_NEEDED (the host clef: 3); inputs the wolf archive `4cc4045b…`, its `libwolf_rt.a` `9efc68e1…`, Ubuntu 24.04's glibc `libc.a` (libc6-dev 2.39-0ubuntu8.9); no std | right |
| P2 | two builds at one path one digest; at two paths only the debug sections differ | right at one path; at two paths `.debug_info`, `.debug_aranges` **and the build-id note** differ (measured on kasumi before `d2cbceee`, two checkouts at two paths). Not predicted: with mktemp's path every run was a new digest (`6f171db0…`, then `29cd889d…`), so `d2cbceee` builds at one fixed path per pin; since then **one digest on kasumi's container and on CI's runner**: `a90a4ca8efc93c6e6d3343ea36d70d7003cd5c30e91ff1345b07c3febcdd3161` | right, but the build-id note and the fixed path |
| P3 | one branch for `boot/start.S`, one argument for wolf's object build; absent or empty, every command trunk's | right (`1c73e8db`; plus the one-time resolution and the ELF check the branch needs); K1 holds 18 native and 36 release traced calls to trunk's build-kernel's, K2 the empty value to the same calls and bytes | right |
| P4 | 17 assembly calls per tier through a selected assembler (16 + 1), 0 through cc or clang, the release tier's code generation unchanged | right on both tiers (K4, K5; the release tier's 8 `clang -x ir` and 9 `clang --version` calls K1's) | right |
| P5 | wolf 0.2.35 with WOLF_AS set refused by name before any object | right (K3: no kernel, no assembly call) | right |
| P6 | clef kernel = GNU-as kernel through the seam, both tiers, identical non-assembly objects; 9f2cff44's non-assembly objects = 0.2.35's (60 %), so the seam kernels = the 0.2.35 GNU-as baseline through as01's shims | right on every count: 53 of 53 native and 9 of 9 release non-assembly inputs identical between the two compilers; six kernels per tier in two classes (below) | right |
| P7 | the stock kernel's first difference from the GNU-as one near byte 96, both tiers | offset 96 on both tiers (`kernels.json`). The K4 line in `logs/e1.log` says "byte 9797": a display bug, cmp's 1-based 97 printed twice; `620923d0` prints the offset once (rerun at `7ae9ca72` on kasumi: "their first difference at offset 96") | right |
| P8 | on PAX, at the first boot: 43/43 objects, the expansion and every refusal identical to the host clef's and to the same package on Linux; 43/43 GNU as's by clef's rule; nothing unserved but 273 and 334 | right at the first boot (`logs/jobB.log`, native BIOS), then on every leg | right |
| P9 | every leg of mpx5-wolf and the muzzle witness green at the first boot on the clef kernels | right (`logs/e3c.log`) | right |
| P10 | the plants red by name: the wrong assembler at kernel-as, the runtime at Q0 naming both digests | right (below), though the runtime plant is not wolf 0.2.34's runtime: that one does not link (`__wolf_rt_stack_start` undefined) | right but its form |

## Forbidden

- No kernel, libc, shell, grep, filesystem-tool or bootloader source was read. No assembler's,
  disassembler's or opcode database's source was read; GNU as 2.42 was run as a black box and its
  objects compared by clef's own `tools/elf.py`.
- The org's own repositories were read and cited: wolf-lang (`crates/wolf_driver/src/asm.rs`, the
  rt-none lookup in `crates/wolf_driver/src/main.rs`, `xtask`'s `rt_none`), clef (`notes/as01*`, its
  `tools/` gates and images, the `notes/as01/seam/` controls), and pax's own builders and suites.
  Permissively licensed kernels: none. `docs/SOURCES.md` § as02b lists every source.
- as01's shims (`notes/as01/seam/gas-driver`, `clef-driver`) ran only as the 0.2.35 control
  (`notes/as02b/kernels.sh`); nothing lane-local became a default. No default moved: no image carries
  clef unless `tools/mkdev --clef` is asked, and no kernel is assembled by clef unless `WOLF_AS` names
  it (R-as02-3 A).
- No package was installed on any host; Rust 1.97.1 went into a throwaway image
  (`notes/as02b/Containerfile.rust`). No QEMU outside a container; no `--pid=host`; `ulimit -c 0`.
  Nothing of `~/pax-playground` was read or written. No merge, tag, release, label, issue filed or
  closed; no attribution trailer on any commit.

## Inputs, verified

- pax trunk `77d7b00c`; the kernel's tree is px80's `8d631040`'s (px80 §2), whose release kernel CI's
  run 40170169823 booted (`265b2f3d…`).
- clef `996a3ccd` (user/clef.pin): `wolf-toolchain.toml` pins wolf 0.2.35 by `4cc4045b…`, the same
  digest as `kernel/wolf.pin` and as boreutils', pelt's and scent's pins; read twice by clef's
  `tools/fetch-toolchain` and twice again by `tools/mkclef` on every run.
- wolf-lang `9f2cff44` (as02a's merge), built from source by `tools/fetch-wolf`'s source shape at
  `tests/kernel-as.d/wolf.pin`: `wolf 0.2.35+dev.9f2cff44 (wolfgang, pin 9f2cff44)`, 2 min 22 s on four
  cores (`logs/seam-wolf.log`). `crates/wolf_rt_none` is the same tree at v0.2.35 and at `9f2cff44`
  (`git diff` empty), so the release archive's `libwolf_rt_none.a` (`6b9c4852…`, the bytes every
  kernel links) is staged beside it (K0).
- The dev compiler's three files for mpx5-wolf: px80's staged copies, each held to `user/wolf.sums`
  twice on kasumi and again by the suite's W0.
- GNU as: binutils 2.42-4ubuntu2.10 from clef's `ci/oracle-lock.json` (by sha256); CI's runner has
  its own 2.42.
- rustup-init `5be191e8…`, the digest static.rust-lang.org names, read twice.

## What was built

**The seam** (`1c73e8db`). `tools/build-kernel` reads `WOLF_AS` once: unset or empty, nothing moves.
Set, it is resolved to an absolute path (a bare name through PATH, a path from the caller's
directory) and refused by name unless it is an executable file; wolf gets it as `--assembler PATH`
for the object build (CLI over environment, the same value, R-as02-1 A), so wolf 0.2.35 refuses the
flag and the script says "this wolf has no assembler seam"; `boot/start.S` is assembled by the call
wolf's seam makes, `PATH --64 -o start.o boot/start.S`, after any old `start.o` is removed, and a
nonzero status, no output or output that is not an ELF64 little-endian x86-64 relocatable object
fails the build naming the assembler, with no second try. One variable for both seams (R-as02-2 A).
`PAX_WOLF_PIN` (`84d66154`) lets a suite name another wolf pin.

**The suite** (`tests/kernel-as`, `4c8d34bf`, `b619f656`, `620923d0`; its tools `7975d8af`,
`c35a9ded`; the records `f8b46f98`, `8a9290ed`; the seam wolf `92dd32cc`). kmain_console built with
every C-driver and assembler call traced. Rows K0–K9 (the script's header); the release tier runs
K1, K4 and K5.

**The package** (`b65d461d`, `52fbbdb2`, `d2cbceee`). `tools/mkclef`: clef at the pin, the toolchain
its tree pins held to the image's (archive digest and version line of `kernel/wolf.pin`), no std, its
own build line (`wolf build --no-cache --deny-warnings src/clef.lu`, the native tier clef's gates
measure: R-as02-6 A) through the user tools' static `cc`, twice from fresh checkouts at
`/tmp/pax-clef-996a3ccdf160` (R-as02-7 A), checked ET_EXEC with no PT_INTERP and no dynamic section,
its `sums.txt` naming the package, the runtime it linked and the archive. `tools/mkdev --clef DIR`
(`b60b3c6d`) adds it to a dev image, opt-in.

**The qualification** (`tests/mpx5-clef`, `16eaaf0d`, `82356b99`, `23b80bc5`). One image: pelt as
`/bin/sh` and init, boreutils' base64, cat and mkdir, the package at `/usr/bin/clef`, clef's census
sources copied to `/usr/share/clef/corpus`, and `qualify.sh` from qualify.py's one case list: 
`--version`, the 43 sources (`--64 -o`), the ISR's `--expand` and `--provenance`, the C-driver form,
nine refusals. Each case prints its status, its output and its output file in base64. Rows Q0 (the
package static, its runtime the image's by digest), QT (the transcript byte for byte the same
package's in a throwaway container), Q1–Q3 (every case byte for byte the host clef's), Q4 (the 43
objects GNU as's by clef's structural rule), Q5 (nothing unserved but 273 and 334, init's status 0,
halted).

**CI** (`2b4cc337`, `ce0374ea`, `f10d0974`): jobs `kernel-as` (the seam wolf's binary cached by its
pin) and `mpx5-clef`; `boot/*.S` and `user/programs.S` run `kernel-as` too; three planner rows.

**Docs** (`dfba01eb`, `ce55ca29`), CHANGELOG (`05cb8855`), README (`7ae9ca72`, README only).

## Measured

**The kernels** (`notes/as02b/kernels.json`; native bytes are the kasumi checkout's, its DWARF
naming the build directory):

| tier | stock (clang/cc) | GNU as | clef | which compilers |
|---|---|---|---|---|
| native | `e9f36a3e…`, 2,915,304 | `ca5d0e25…`, 2,915,304 | `ca5d0e25…` | 0.2.35 and the seam wolf alike, all three |
| release | `265b2f3d…`, 2,273,328 (CI's, px80's) | `76f6e210…`, 2,273,328 | `76f6e210…` | the same |

- **Through the explicit seam the clef kernel is byte for byte the GNU-as kernel on both tiers**,
  and so is every non-assembly input (53 native, 9 release); through as01's shims wolf 0.2.35 makes
  the same two kernels; the stock kernels differ from them first at offset 96, both tiers.
- The same clef kernels are the ones mpx5-clef (`logs/e3b.log`) and mpx5-wolf (sha256 of its two
  `kmain_console.elf`, read on kasumi before the prune) built through the seam on their own: the
  seam is not a property of one suite's build.

**The package.** 15,370,648 bytes, `a90a4ca8…`, ET_EXEC, no PT_INTERP, no dynamic section, 0
dynamic dependencies (the host clef: `libgcc_s.so.1`, `libc.so.6`, `ld-linux-x86-64.so.2`); links
`libwolf_rt.a` `9efc68e1…` (45,370,722 bytes) from archive `4cc4045b…`; two runs, one digest
(`logs/jobB.log`), and the same digest on CI's runner (dispatch 40247580343).

**The qualification**, every leg (native and release, BIOS and UEFI; the kernels the clef ones):
the 2,870-line transcript `132ece83…` on PAX and in the container; 43 of 43 sources status 0 and
every object the host clef's; the ISR's expansion 37,737 bytes, the provenance object and the
C-driver form the host clef's; nine refusals (statuses 2, 2, 2, 2, 2, 2, 2, 1, 1) and every byte
they print the host clef's, the existing output left as it was; 43 of 43 GNU as's by clef's
structural rule (0 byte-identical files: the symbol and string tables are serialized differently,
as01's boundary); -ENOSYS only for 273 and 334 (`notes/as02b/qualify/`, `logs/e3c.log`).

**Every boot leg** on the clef kernels: mpx5-clef 4 of 4; mpx5-wolf 4 of 4 (W1 root `57cf42de…`
and pax `36f1903a…` byte-identical to Linux on each leg, W2, W3: halted, unserved 273 334, 8 wolf
processes, 12 mremap calls served); the fresh muzzle CRT witness (crt0.S, sys.S and as01's
muzzle-user.S by the package, `aed5c41c…`, byte for byte the GNU-as program) prints `clef muzzle
CRT: pass` and exits 7 on Linux and on all four legs (`notes/as02b/muzzle/`).

## Plants

Both draft PRs are based on `as02b`; the orchestrator ends them (`notes/as02b/plants.txt`).

- pax#203 (`as02b-plant-as`, head `5000c047`): kernel-as K5 selects clang, a C driver and not
  as-shaped, as WOLF_AS. Seen red in run 40252371836, job 121347095161 (kernel-as): `FAIL K5 native:
  the clef build failed (build-kernel: FAIL wolf build --target x86_64-unknown-none --emit=obj
  --assembler …/build/kernel-as/bin/sel exited 2 (kmain_console, native))`; every other row passed.
- pax#204 (`as02b-plant-runtime`, head `3d3db1d1`): mkclef rewrites the runtime member clef's argument
  call links with one extra section, so the package links a `libwolf_rt.a` (`dd8bddc0…`) that is not
  the image's. Seen red in run 40252374744, job 121347147153 (mpx5-clef): `FAIL Q0: the package's
  runtime is libwolf_rt.a dd8bddc0… from archive 4cc4045b…; the image's is 9efc68e1… from
  4cc4045b…`; QT and Q1–Q5 passed, and kernel-as was green in the same run.

## Rulings (recommended and implemented, not decided)

- **R-as02-1 (A)** CLI over `WOLF_AS` over the legacy driver, no fallback: build-kernel passes the
  choice on the command line.
- **R-as02-2 (A)** one `WOLF_AS` for `boot/start.S` and wolf's manifest seam.
- **R-as02-3 (A)** qualified and opt-in: `tools/mkdev --clef`; the default flip (an image that carries
  clef unasked, a kernel assembled by clef by default) is the maintainer's.
- **R-as02-5 (new): the seam's compiler.** No release carries #957. (A) `tests/kernel-as` builds
  wolf-lang `9f2cff44` from source by its own pin file while `kernel/wolf.pin` stays the 0.2.35
  release, and build-kernel refuses WOLF_AS with a wolf that lacks the seam; `kernel/wolf.pin` moves
  at the first release with #957 and the suite's pin goes. (B) a source pin for every kernel now.
  (C) wait. **Recommend A**, implemented.
- **R-as02-6 (new): the package's tier.** (A) clef's own build line, the native tier its 33 gates
  measure; (B) the release tier, as pelt, boreutils and scent build. **Recommend A**, implemented.
- **R-as02-7 (new): the build path.** The native tier's DWARF names the build directory, so a path
  of mktemp's makes every run a new digest. (A) one fixed path per pin, `/tmp/pax-clef-<12 hex>`,
  refused if it exists; (B) accept a new digest a run. **Recommend A**, implemented: one digest on two
  hosts.

## The claim's limits

clef assembling the kernel's `.S` files does not take the C toolchain out of the kernel's build or
off the image. The kernel still links with `ld.lld` (Ubuntu's 18.1.3 in CI, the dev image's 18.1.8:
the same bytes, px80); the release tier's code generation is still wolf's `clang -x ir` through LLVM;
a hosted wolf program, clef included, still links through `cc` and a C library. The linker's own
package is ligature's milestone (ld02). The package is clef's measured census dialect, not a complete
GNU as: what it does not know it refuses by name.

## Evidence index

- `a62b1cdf` the prediction.
- `84d66154`, `92dd32cc` the seam wolf's pin.
- `1c73e8db` the seam in build-kernel.
- `7975d8af`, `c35a9ded`, `4c8d34bf`, `f8b46f98`, `b619f656`, `8a9290ed`, `620923d0` tests/kernel-as.
- `b65d461d`, `52fbbdb2`, `d2cbceee` the package; `b60b3c6d` mkdev's opt-in.
- `16eaaf0d`, `82356b99`, `23b80bc5` tests/mpx5-clef.
- `2b4cc337`, `ce0374ea`, `f10d0974` CI, the map, the planner's rows.
- `aa8ca43f`, `c3693a4d` the 0.2.35 control and the six kernels per tier.
- `28c6f352` the muzzle witness, the legs' runner, the Rust image.
- `6f66d889`, `e55b3c7d`, `2334c10b` the runs' logs, the qualification's cases, the muzzle legs.
- `dfba01eb`, `ce55ca29`, `05cb8855`, `7ae9ca72` BOOT.md, SOURCES.md, CHANGELOG, README.
- Runs: dispatch 40247580343 (`tier partial`, kernel-as and mpx5-clef, native BIOS, green at
  `f10d0974`); the plants' 40252371836 and 40252374744; the PR's own run, read once, in the PR.
- kasumi `~/lanes/as02b/logs/` (every job's pid, log and exit marker).

## Done-when

- [x] The seam: absence, emptiness, presence (GNU as, clef), failure, a missing tool, a non-object,
  a stale object, a wolf without the seam; 17 assembly calls per tier counted (tests/kernel-as).
- [x] The package static on the image's toolchain and runtime by digest, reproducible on two hosts.
- [x] The package qualified on the image over the copied corpus, the expansion and the refusals,
  on every leg (tests/mpx5-clef).
- [x] The kernel through the explicit seam byte for byte the GNU-as kernel, both tiers; the
  stock-clang differences recorded separately.
- [x] mpx5-wolf and the muzzle CRT witness on all four legs with the clef kernels.
- [x] Plants red by name in their own runs (pax#203, pax#204).
- [x] docs, CHANGELOG, README (read against the pass and refreshed; `docs/CENSUS.md` read, current:
  clef needs no call PAX does not serve).
- [ ] The orchestrator: the full-matrix label at the final head, the green tier full, the merge.

## Issues to file (not filed here)

- **pax**: move `kernel/wolf.pin` to the first wolf release carrying wolf-lang#957 and retire
  `tests/kernel-as.d/wolf.pin` and its CI build (R-as02-5).
- **wolf-lang**: a release with #957, so PAX's seam runs on its pinned compiler.
- **clef**: `clef` with no operand exits 2 and prints nothing (every other usage error prints the
  usage line); `clef nosuch.S` prints the usage line and then `cannot read nosuch.S` (status 1).
  Both measured on PAX and Linux alike (Q3); neither is PAX's.
- **pax** (the maintainer's ruling): the default flips R-as02-3 leaves open.

## To prune (the orchestrator, literal paths)

- kasumi `~/lanes/as02b/` (2.8 GB): `build/e1` (the K1/K4/K5 kernels), `build/e3` (the qualification
  images per tier, the muzzle witness), `build/pkg1` (the package), `cache/` (the seam wolf's binary,
  the 0.2.35 staging, cargo's registry, clef's integration debs), `clef/` (the clone, its debs under
  `target/container`), `pax/`, `plant-runtime/`, `dev-wolf/`, `ev/`, `scripts/`, `logs/`, `tmp/`.
  Files written by root inside a container need `podman unshare rm -rf`.
- kasumi images: `localhost/as02b-rust` (1.69 GB), `localhost/clef-integration:52846d3b65aeafca`
  (1.02 GB), `localhost/clef-oracle:bce39162bc0b1e5e` (787 MB).
- The plants: branches `as02b-plant-as`, `as02b-plant-runtime`; draft pax#203, pax#204.
- The Mac: the worktrees are removed at the hand-back.
