# px80 — the linker respin: the dev ISO's lld at 18 (pax#172)

Crawl 54, Claude Opus 5.5, ruling #128. kasumi CPUs 0–3 under
`~/lanes/kasumi-cores-0-3.lock` (shared with wl68's batches: taken per
build, per suite and per boot, released between). Branch `px80` from trunk
`8d631040` (px79's merge), rebased before the PR onto `edbd385c` (px69's
merge: the disk tools, `tools/mkdisk`, mpx6-root, CI's disktools job), which
touches nothing this lane built or booted (`kernel/`, `boot/`,
`tools/build-kernel`, `mkdev`, `mkimage`, `mkinitramfs`, the pins and sums,
the four suites), so the evidence taken at `d3772923` holds at the head.
The runs name their pre-rebase commits, whose trees are the rebased ones
less px69's paths: `d3772923` is `1ac0bec1`, `72e1b69a` is `8cd7dccd`,
`72df815b` is `e0c49028`.
The kernel is unchanged: no file under `kernel/` or `boot/` moves.

clef's as01 found that the dev ISO's static lld 17.0.6 (px60's build,
`user/wolf-link.sums` `1217ca75…`) cannot link PAX's release-tier kernel;
the Ubuntu lld 18.1.3 CI uses can. This lane rebuilt the ISO's lld at
18.1.8 from LLVM's release tarball, by px60's recipe with zlib and zstd
added, proved it on the kernel, re-summed the record, respun the dev ISO,
ran hello on PAX with it, and staged the bundle for a release. The
publication itself is not a lane's.

## 1. Forbidden, and what was read

- No kernel source, no libc source, no shell, grep, filesystem-tool or
  bootloader source was read. The kernel's sources are PAX's own and do
  not change here.
- LLVM's tarball was compiled, never read (ligature's rule binds the org):
  the lane's contact with its tree was `tar` extracting `cmake`, `llvm`,
  `lld`, `libunwind` and `third-party`, then `cmake` and `ninja`, and
  copying the licence files the bundle carries. lld was observed only as a
  black box: its argv, its exit status, its messages, its output bytes.
- The configure step's own log (`CMakeConfigureLog.yaml`) was read once, to
  see why a check failed (`/usr/lib/libz.a` absent: Alpine's static zlib is
  `/lib/libz.a`). No LLVM CMake module was read.
- musl's, zlib's and zstd's release tarballs: only the licence member of
  each was extracted (`tar -O … COPYRIGHT` / `LICENSE`); no source member
  was opened.
- Everything ran on kasumi in containers (Alpine 3.20 and px65's Ubuntu
  24.04, both by digest; px57-rust), QEMU on the kasumi host under
  `taskset -c 0-3`, `ulimit -c 0`. No package was installed on any host.
  The playground's `pax-dev.iso` was read (copied, extracted), never
  written; the new ISO goes beside it.
- No merge, tag, label, release, issue filed or closed, and no attribution
  trailer on any commit. Sources consulted: `docs/SOURCES.md` § px80.

## 2. Inputs, verified

- **The tarball.** `llvm-project-18.1.8.src.tar.xz` from LLVM's GitHub
  release `llvmorg-18.1.8`: 132,067,260 bytes (the release asset's size),
  sha256 `0b58557a6d32ceee97c8d533a59b9212d87e0fc4d2833924eb6c611247db2f2a`,
  read twice on kasumi. llvm.org's release page publishes no sha256 for it
  (R-px80-3): the same digest is Homebrew's published one for `llvm@18`
  (formulae.brew.sh), and the tarball's `.sig` verifies, in a scratch
  keyring, against LLVM's `release-keys.asc`: `Good signature from "Tom
  Stellard <tstellar@redhat.com>"`, key `474E 2231 6ABF 4785 A88C 6E8E A2C7
  94A9 8641 9D8A`, made 2024-06-21 (the key has since expired; it was valid
  when it signed).
- **The bundle before px80.** The playground's `pax-dev.iso` (px65's,
  `02f979be…`, read on nomad) holds the seven files of
  `user/wolf-link.sums` at `/usr/bin/{ld.lld,cc}` and
  `/usr/lib/wolf-musl/*`; each was held to its line twice on nomad and
  twice again on kasumi (`ld.lld` 17.0.6 `1217ca75…`). The dev compiler's
  three files from the same image match `user/wolf.sums` twice (its lines
  have not moved since `fd9827bd`). So the respin rebuilds only `ld.lld`.
- **The kernel's objects.** At `8d631040`'s tree, in px65's container
  (`notes/px65/Containerfile`, built as `localhost/px80-ubuntu`: Ubuntu
  24.04 `@sha256:534baea6…`, `lld-18` 1:18.1.3-1ubuntu1, clang 18.1.3,
  binutils 2.42), `tools/build-kernel` built each tier's kmain_console
  objects once; every input was hashed twice (`notes/px80/control/*/
  inputs.sha256`: 26 for the release tier, 70 for the native). Against
  as01's: `start.o`, the 16 assembly objects and `kmain_console.rt-none.a`
  are the same bytes; the eight release codegen units (`c00`…`c07`) differ,
  because the tree moved from as01's `105d0d1f` to `8d631040` (px79's
  kernel changes).
- **CI's own kernels.** Run 40170169823 (the tier-all pull-request run at
  `8d631040`, green on every leg) uploads mpx5-wolf's two kmain_console
  ELFs; they are this lane's comparison for the bytes CI booted.

## 3. Prediction, scored

Committed first: `2f140466` (`notes/px80/prediction.txt`).

| | predicted | measured | score |
|---|---|---|---|
| P1 | the build misses px60's hour on four cores: ~100 min | 2,006 s, 33 min 26 s (1,729 ninja steps, `-j 4`) | wrong: inside the hour, a third of the estimate |
| P2 | zlib + zstd under 1 MiB (under 1.5 %); the binary 66–71 MB, point 68.5 MB; ET_EXEC, no PT_INTERP, no dynamic section | 68,594,984 bytes (+2,347,976, +3.5 %); zstd's code ~540 KB (its 522 global symbols 246,633 B), zlib's globals 31,945 B: under 0.9 % together; ET_EXEC, no PT_INTERP, no dynamic section | right |
| P3 | (a) red with as01's error word for word, on `c04.o`; (b) and (c) link | (a) red with as01's error — the same function `_Wpaging.build$00fa5c99b8525ce4`, the same `-2147483652`, the same `__pax_image_start` at `kernel.ld:29` — but in `c00.o` at `.text+0xfcd` (the codegen units moved with the tree); (b), (c) link | right but the unit's name |
| P4 | (b) and (c) byte-identical on both tiers and on every kernel the suites link | identical on both tiers (release `265b2f3d…`, native `dd72c3ec…`), and on all 83 kernel links compared (§9); hosted programs differ in the `.comment` that names the linker (§9) | right for kernels |
| P5 | lld 17 links the native kernel, byte for byte as 18 | yes: all four rows `dd72c3ec…` | right |
| P6 | the new lld reads zlib and zstd compressed sections; hello links against the packaged sysroot | both formats read, each output byte for byte the uncompressed input's; hello, loop and signal link against Alpine's and Rust's files as they ship, the same bytes as against the bundle's (§7) | right |
| P7 | every suite green on the lld-18 kernels at the first boot but for pax#174 | mpx1, mpx2-paging and mpx5-wolf green on all four legs at the first boot; mkw's first run failed in my runner (no lupin: `missing tool`), green at the second; pax#174's suite was not in the batch (§9) | right but mkw's runner |
| P8 | only the `ld.lld` line moves | right: `4ba77b28` changes one line | right |
| P9 | hello, loop and signal on PAX at the first boot; the ISO +2–6 MB | hello built, linked and run on PAX as uid 1000 at the first boot (the dev session builds hello alone; loop and signal ran on Linux, §7); the ISO is 266,698,752 bytes, +2,553,856 on px65's | right on what ran |

## 4. What was built

- `notes/px80/build-lld.sh` and `Containerfile.lld` (`8d7cdb98`): Alpine
  3.20 by digest (`@sha256:d9e853e8…`), clang 17.0.6-r1 with libc++,
  libc++abi, llvm-libunwind and compiler-rt 17.0.6-r1, musl 1.2.5-r4,
  zlib-static 1.3.2-r0, zstd-static 1.5.6-r0, cmake 3.29.3, every package's
  version in `notes/px80/apk-info.txt`. The cmake line is px60's with three
  changes: `-DLLVM_ENABLE_ZLIB=FORCE_ON -DZLIB_USE_STATIC_LIBS=ON
  -DZLIB_LIBRARY=/lib/libz.a` and `-DLLVM_ENABLE_ZSTD=FORCE_ON
  -DLLVM_USE_STATIC_ZSTD=ON` (R-px80-2 A; FORCE_ON so a missing library is
  an error, never a silent build without it), and `ninja -j 4`. The exact
  line, as cmake ran it, is the `set -x` output in
  `notes/px80/lld-configure.log`; the build's log is `lld-build.log`
  (the compiler's unused-argument warnings removed). The result:
  `LLD 18.1.8 (compatible with GNU linkers)`, 68,594,984 bytes, sha256
  `9fa7191f0e22887486cd52bbc95f261ad0be71a6ab29f1c1cc13322a34d4ca4a`, read
  twice; ET_EXEC, no PT_INTERP, no dynamic section (its debug sections are
  the static libraries' own, as px60's were).
- `user/wolf-link.sums` (`4ba77b28`): the `ld.lld` line, and only it.
- `tests/mpx5-wolf.d/verify-link` and CI's mpx5-wolf step (`6a4d6f95`):
  **W0 link**, the record's first check in CI. Until now only
  `tools/mkdev` read `user/wolf-link.sums`, and only where a bundle is (CI
  stages the checked dev root without one), so no CI row could see a wrong
  line. `--shape` holds the record to mkdev's seven names in order, each
  with a sha256 and a size; `--cc RUST` rebuilds the one member CI can
  build in seconds, the `cc` front end, from `notes/px60/cc.rs` by
  `notes/px60/build-m2.sh`'s line with the pinned Rust, and holds its bytes
  to the `cc` line (GitHub's runner rebuilt `3161aea2…`, the recorded
  bytes, in the plant's run); `DIR` holds a staged bundle's seven files to
  their lines (what mkdev does). `ld.lld` (a 33-minute build) and the
  sysroot are held where the bundle is.
- `notes/px80/control.sh`, `elfcmp.py`, `lld-wrap/ld.lld` (`07813e07`):
  the control (§6). `lld-wrap/ld.lld` is the `ld.lld` first on PATH
  while the suites build (`tools/build-kernel` calls `ld.lld` by name, and
  wolf's hosted links reach it through `gcc -fuse-ld=lld`): it links with
  the bundle's lld 18.1.8, links the same argv again with the container's
  Ubuntu lld 18.1.3 and compares the two files; one line per link.
- `notes/px80/dev-iso/` (`82076b95`): px65's dev ISO recipe at this lane's
  inputs (§8); `dev.keys` is px64's with `ld.lld --version` after `wolf
  --version`, and `check-linker.py` holds the answer to LLD 18.1.8.
- `notes/px80/{run-suite,batch,kernels,m2-linux,chain}.sh` (`80172674`,
  `1ac0bec1`): the boots, every kernel's links, the Linux rows, the order;
  after the first batch (`aea66510`, `8cd7dccd`) the runner fetches lupin
  for mkw and counts only failing lines, and the compressed objects are
  made by Ubuntu's lld and counted by their headers (`chdr.py`);
  `rerun.sh` is the kasumi driver of that rerun.
- `notes/px80/stage.sh`, `bundle-README.md` (`fd3f6736`), `restage.sh`
  (`e0c49028`): the staged bundle (§10).

## 5. Rulings (recommended and implemented, not decided)

- **R-px80-1, the version: (A) 18.1.8**, the line's last release, as
  recommended. Byte-equality with Ubuntu's 18.1.3 was not expected either
  way; it came anyway (§6).
- **R-px80-2, compression: (A) zlib and zstd built in.** Measured in §7:
  the new lld links the packaged (compressed) sysroot, so `decompress.sh`
  is no longer needed to make a bundle. See R-px80-4 for the bytes this
  bundle keeps.
- **R-px80-3 (new), the tarball's digest.** The contract asks for the
  sha256 from llvm.org's release page; LLVM publishes none (the GitHub
  release lists the tarball and its `.sig`, no digest; llvm.org links
  there). Options: (A) the signature by LLVM's release key, the digest read
  twice from the download, and two independent records of it (the release
  asset's byte size; Homebrew's published sha256 for `llvm@18`); (B) stop
  until a first-party digest exists. **Recommend (A)**, implemented.
- **R-px80-4 (new), the sysroot's bytes.** With lld 18 reading compressed
  sections, the bundle could carry Alpine's and Rust's files as they ship.
  (A) keep px60's decompressed files: one line of the record moves, the
  contract's "unchanged sysroot"; their provenance is now measured (§7:
  Alpine 3.20's musl-dev 1.2.5-r4 and Rust 1.97.1's `libunwind.a`,
  decompressed by `llvm-objcopy` 17, are the recorded bytes). (B) ship the
  packaged files at this respin (five more lines move, the ISO's bytes with
  them). **Recommend (A)**, implemented; the packaged files go in at the
  next musl move, with `decompress.sh` retired then.
- **R-px80-5 (new), the boots' scope.** The contract asks for every suite
  on every leg, as CI's tier all; CI's last tier all was 1,233 job-minutes,
  ~20 hours of a four-core block another lane shares. (A) run all of it
  locally; (B) prove the links byte-identical to the distro lld's that CI
  links with, on every kernel the tree builds, both tiers, and hold the
  bytes to CI's own (the tier-all run 40170169823, green on every leg at
  this trunk, booted the same release kernel file and the same native
  loaded image); then boot directly, on all four legs, the suites that test
  the link itself (mpx1: first light and the halt, mkw: M-KW's kernels,
  mpx2-paging: the image's PT_LOADs held to `boot/kernel.ld`'s symbols,
  mpx5-wolf: the release kmain_console lld 17 cannot link, under the dev
  compiler's sessions) and the dev ISO's session; any link that differs
  sends its suites to (A). **Recommend (B)**, implemented: 83 kernel links,
  83 identical, so no suite went to (A).

## 6. The control on the kernel

kmain_console at `8d631040`, objects built once per tier, linked with
`tools/build-kernel`'s argv (`-nostdlib -static -z max-page-size=0x1000 -T
boot/kernel.ld -o OUT start.o <16 asm objects> <wolf objects>
kmain_console.rt-none.a`); `notes/px80/control/`.

| row | linker | release tier | native tier |
|---|---|---|---|
| (a) | the ISO's lld 17.0.6 (`1217ca75…`) | **status 1**: `ld.lld: error: …/kmain_console.c00.o:(function _Wpaging.build$00fa5c99b8525ce4: .text+0xfcd): relocation R_X86_64_REX_GOTPCRELX out of range: -2147483652 is not in [-2147483648, 2147483647]; references '__pax_image_start'` `>>> referenced by wolf` `>>> defined in …/boot/kernel.ld:29` | status 0, `dd72c3ec…` |
| (b) | the new lld 18.1.8 (`9fa7191f…`) | **status 0**, `265b2f3d…`, 2,273,328 bytes | status 0, `dd72c3ec…`, 2,915,248 bytes |
| (c) | Ubuntu lld 18.1.3 (px65's container) | **status 0**, `265b2f3d…` | status 0, `dd72c3ec…` |
| (a′) | lld 17.0.6 `--no-relax` (as01's control, never the fix) | status 0, `d5353fc7…`, 2,274,128 bytes | status 0, `dd72c3ec…` |

- **The byte difference between (b) and (c): none.** Both tiers'
  kernels are the same file (`elfcmp.py`: every PT_LOAD, every section,
  the whole file). `boot/kernel.ld` discards `.comment`, the one place lld
  writes its version, and nothing else between 18.1.3 with Ubuntu's
  patches and 18.1.8 reaches this link. (c) equals build-kernel's own link
  (c-bk) too.
- **Against CI's.** The release kernel is byte for byte the one CI's
  tier-all run 40170169823 built and booted green on every leg
  (`265b2f3d…`, its mpx5-wolf artifact). The native kernel's loaded image
  is the same as CI's, every PT_LOAD and every allocated section; the
  files differ only in `.debug_info` and `.debug_aranges`, where
  Cranelift's DWARF names the build directory (`notes/px80/control/
  ci-artifacts.txt`).
- (a′) differs from (b) as `--no-relax` should: `.data`, where
  `boot/kernel.ld` puts `.got`, is 800 bytes longer (2,176 against 1,376)
  and `.text` is the same length with other bytes. On the native tier lld
  17's output is 18's, byte for byte, with or without `--no-relax`.

## 7. Compressed sections and hello on Linux (R-px80-2)

`notes/px80/m2-linux.sh` (px60's M2 recipe), kasumi, in px65's container;
the static musl wolf 0.2.35 (`user/wolf.sums`' bytes) builds hello, loop and
signal through the bundle's `cc` (`PAX_LLD`, `PAX_CC_SYSROOT`); log
`notes/px80/m2-linux.log` (the first run's, `m2-linux-first.log`, had a
vacuous zstd row: clang 17 on Alpine has no zstd, so its `-gz=zstd` object
was not compressed and the counter read readelf's legend; the rerun makes
the compressed objects with Ubuntu's lld 18.1.3, `ld.lld -r
--compress-debug-sections=zlib|zstd`, and counts them by their section
headers, `notes/px80/chdr.py`).

| row | linker | sysroot | hello, loop, signal |
|---|---|---|---|
| new-bundle | 18.1.8 | the bundle's (decompressed) | build 0, run 0: `hello, wolf`, `1 squared is 1`, `INTERRUPT is signal 2 here`; ET_EXEC, no PT_INTERP, no dynamic section |
| new-packed | 18.1.8 | as shipped: Alpine 3.20 musl-dev 1.2.5-r4 (`crt1.o` 6, `crti.o` 2, `crtn.o` 2, `libc.a` 8,911 zlib sections), Rust 1.97.1's `libunwind.a` (none) | the same three, **byte for byte new-bundle's** |
| old-packed | 17.0.6 | as shipped | build 2: `ld.lld: error: …/crt1.o:(.debug_info) is compressed with ELFCOMPRESS_ZLIB, but lld is not built with zlib support` (px60's packaging error, again) |
| old-bundle | 17.0.6 | the bundle's | build 0, run 0; differs from new-bundle in `.comment` (`Linker: LLD 17.0.6`), lld 18's `.relro_padding` and what moves with it |

| object | compressed sections | lld 18.1.8 | lld 17.0.6 |
|---|---|---|---|
| `z-zlib.o` | 7, ELFCOMPRESS_ZLIB | links, runs 0; the executable is byte for byte the uncompressed object's | **refused** (control): `is compressed with ELFCOMPRESS_ZLIB, but lld is not built with zlib support` |
| `z-zstd.o` | 7, ELFCOMPRESS_ZSTD | links, runs 0; byte for byte the uncompressed object's | **refused** (control): `is compressed with ELFCOMPRESS_ZSTD, but lld is not built with zstd support` |

lld 17's two refusals are facts about px60's build (no zlib, no zstd),
recorded as the control, not a defect of the respin. The bundle's sysroot
is accounted for: the packaged files decompressed by Alpine's `llvm-objcopy`
17 (`decompress.sh`'s command) are the five recorded files, read twice;
`libunwind.a` had no compressed section, and the command's rewrite of the
archive is the recorded bytes (R-px80-4).

## 8. The dev ISO and hello on PAX

`notes/px80/dev-iso/dev-all.sh d3772923` on kasumi (`notes/px80/dev-iso/
kasumi/`): verify 81 s, build, assemble and boot, 1,182 s in all.

- **verify**: the dev compiler's three files and the new bundle's seven,
  each read twice against `user/wolf.sums` and `user/wolf-link.sums`
  (`4ba77b28`), copied, read again; the std tree fetched at the pin;
  `verify-bins` W0 PASS.
- **build**: the base userspace at the tree's pins (unchanged since px65);
  the console kernel linked by the bundle's lld 18.1.8 through the wrapper,
  `identical` to Ubuntu's link (`457f1973…`, 2,915,456 bytes: the native
  kernel, its DWARF naming this build's directory).
- **assemble**: `tools/mkdev` held the seven files to the record, then
  `tools/mkimage`. **`pax-dev.iso` is 266,698,752 bytes, sha256
  `893ae1b90446a05e8e4d607d56a7eca956d15f8848d7495ce433e798041a50de`**,
  read twice after assembly, twice at the boot, twice in the stage on
  kasumi, and twice on nomad at `~/pax-playground/pax-dev-lld18.iso`
  (beside the maintainer's `pax-dev.iso`, px65's `02f979be…`, which was not
  written). Built from `d3772923`: trunk `8d631040`'s kernel and pins, the
  new record. The smoke image beside it is `3a98d1cd…`.
- **boot**: 2 GiB, TCG, BIOS, the kasumi host's QEMU 11.1.2 under
  `taskset -c 0-3`, 156 s, `qemu-halt: HALTED in pax_halt`. As `pax` (uid
  1000) the session wrote `hello.lu`, formatted and typechecked it, ran the
  checked machine, emitted an object, and **`wolf build hello.lu`
  (`build=0`) and `./hello` (`native=0`, `written on PAX, checked by
  wolf`)**: px60's M1 row on PAX with the ISO's own toolchain; the
  release tier's named clang wall (`release=2`); no mapping refused; clean
  exit (`check-dev-session.py` PASS). mpx5-scent's 49 rows held as root and
  as pax (PASS). **`ld.lld --version` at the PAX console: `LLD 18.1.8
  (compatible with GNU linkers)`** (`check-linker.py` PASS): the new
  static binary starts on PAX.
- The console banner still prints no kernel commit (pax#176, filed by
  ld01); the contract allows no kernel change, so this ISO is told apart by
  its sha256 and the MOTD's first line (`pax px80 (the lld 18 respin;
  kernel of trunk 8d63104)`).

## 9. The boots

R-px80-5 (B). `notes/px80/run-suite.sh` (px79's, on CPUs 0-3): each suite
built in px65's container with `lld-wrap/ld.lld` first on PATH, its Linux
side on the host, then every leg booted on the host (both tiers, both
firmwares, `PAX_REQUIRE_UEFI=1`), each suite under the block's lock.
Batch b1 at `d3772923`, b2 (mkw again) at `72e1b69a`; logs in
`notes/px80/boots/`.

| suite | legs | rows | links compared | first run |
|---|---|---|---|---|
| mpx1 | 4 | 21 PASS lines, 0 failing (the four `PASS A6 … spin` lines quote the halt refusal the spin kernel must earn: `qemu-halt: NOT HALTED`) | 6, 6 identical (kmain, kmain_panic, spin; both tiers) | green; b1's summary said `fail 4`: my counter matched `NOT HALTED` inside PASS lines (fixed, `aea66510`) |
| mkw | 4 | 13 PASS, 0 failing | 6, 6 identical (mkw.d's kmain, kmain_trap, kwd) | b1 `build rc=2`: `mkw: missing tool: lupin`, my runner had not fetched lupin as CI does (`tools/fetch-lupin`; fixed, `aea66510`); green in b2 |
| mpx2-paging | 4 | 25 PASS, 0 failing | 2, 2 identical | green |
| mpx5-wolf | 4 | 17 PASS (W1 byte-identical sessions, root and pax, on each leg; W2; W3), 0 failing; the Linux side rc 0 | 5: the two kernels identical (release `265b2f3d…`, the control's and CI's file); `pelt`, `cat` and `env` DIFFER | green |

The three mpx5-wolf DIFFER lines are not kernels: they are hosted programs
wolf links through `gcc -fuse-ld=lld`, so the PATH wrapper links them too.
Against Ubuntu's link the files differ in `.comment` alone (`Linker: LLD
18.1.8` against `Linker: Ubuntu LLD 18.1.3`, 109 against 116 bytes) and the
`.note.gnu.build-id` that hashes the file (the only change inside
PT_LOAD[0]). The sessions on them were byte-identical to Linux's.

**Every kernel the tree builds** (`notes/px80/kernels.sh`, `kernels/`): the
33 `kernel/kmain*.lu` on both tiers through `tools/build-kernel` and the
wrapper: 66 built, 66 links, **66 identical** (13,433 s; the release tier
~6.7 minutes a kernel). With the batch's 16, the dev ISO's one and the
control's two, **83 kernel links, 83 byte-identical** between lld 18.1.8 and
Ubuntu's 18.1.3 — the linker CI links every kernel with and booted, at this
trunk, on every leg (run 40170169823). pax#174 (mpx5-jobs) was not in the
batch, so neither seen nor rerun.

## 10. The bundle staged (the publication)

`notes/px80/stage.sh`, then `restage.sh` after a README correction (the
staged `README.md` said Rust's `libunwind.a` was decompressed; it has no
compressed section). On kasumi `~/lanes/px80/stage/`, copied to nomad
`~/lanes/px80/stage/` and read twice there:

| file | bytes | sha256 |
|---|---:|---|
| `pax-wolf-link-18.1.8.tar.xz` | 17,950,184 | `d2046648837637ac741e39d739e01d44e6d0958b607d3a1c1d726ed80d39dfc9` |
| `pax-dev.iso` | 266,698,752 | `893ae1b90446a05e8e4d607d56a7eca956d15f8848d7495ce433e798041a50de` |

- The archive (`tar --sort=name`, mtime the tree commit `72df815b`'s,
  owner 0, `xz -9`) holds `pax-wolf-link-18.1.8/`: `ld.lld`, `cc`,
  `sysroot/` (five files), `wolf-link.sums` (the record, byte for byte),
  `README.md` (`notes/px80/bundle-README.md`) and `LICENSES/`; its 33
  files' sums are `pax-wolf-link-18.1.8.contents.sha256`, checked against
  an extraction of the archive. The seven bundle files were read against
  the record twice when staged and twice when restaged.
- The licences, each its project's own file, only the licence member
  extracted: LLVM's `llvm/`, `lld/` and `libunwind/LICENSE.TXT` and the
  Support library's three third-party notices (from the verified tarball);
  musl's `COPYRIGHT` (musl-1.2.5.tar.gz `a9a118bb…`, its `.asc` a good
  signature by `8364 8929 0BB6 B70F 99FF DA05 56BC DB59 3020 450F`, the key
  musl.libc.org serves); zlib's `LICENSE` (zlib-1.3.2.tar.gz `bb329a0a…`,
  held to Alpine 3.20's APKBUILD sha512); zstd's `LICENSE` (its release's
  `.sha256`, OK); Rust 1.97.1's `share/doc/rust` licences; PAX's `LICENSE`
  and `LICENSE-TRAINING-DATA` (for `cc`'s source).
- The README, in plain prose, names the versions (lld 18.1.8 from the
  tarball's sha256 and signing key, clang 17.0.6, musl 1.2.5-r4, zlib
  1.3.2, zstd 1.5.6, Rust 1.97.1), every file's size and sha256, where each
  comes from, what links with it, and the licence table.
- The publication (a GitHub release) is the maintainer's, after this
  lane; the contract names it pax#167, but pax#167 is host.lu's E0802
  warning: the release has no issue (§12).

## 11. CI and seen red

- **The plant, `px80-plant-sums`** (`7dcfd30f`, draft pax#177 based on
  `px80`, so its plan was mpx5-wolf alone on native BIOS): the `cc` line of
  `user/wolf-link.sums` with one hex digit changed (`3161aea2…` →
  `3161aea3…`). Run 40183720349, job 121140186689 (mpx5-wolf), red at the
  W0 link step: `verify-link: FAIL W0 link: cc rebuilt from
  notes/px60/cc.rs is 3161aea27abb…5b11 (499760 bytes);
  …/user/wolf-link.sums records 3161aea37abb…5b11 (499760 bytes)`; the
  shape row before it passed. Read once.
- **The `ld.lld` line, locally** (kasumi, `notes/px80/plant-ld-local.log`):
  the record with `9fa7191f` → `9fa7191e`, against the staged bundle:
  `verify-link` FAIL naming `ld.lld` (status 1) and `tools/mkdev`, the dev
  ISO's stager, `native link input differs from pin: ld.lld` (status 2);
  at the true record both pass.
- The W0 link row's control is the PR's own run (mpx5-wolf runs there:
  the PR changes `.github/workflows/ci.yml`, so its `tier pr` is every
  suite on native BIOS); its run ids are in the PR and the hand-back.

## 12. Issues and what to prune

Filed here: none. Closed here: none; **pax#172 closes at the merge**, by
hand.

To file:
- **pax**: CI links every kernel with Ubuntu's lld, not the ISO's. Once the
  bundle is published, fetch it by digest (as `tools/fetch-wolf` fetches
  wolf's archive) and link CI's kernels with its `ld.lld`, so CI tests the
  linker the ISO ships; W0 link can then hold the `ld.lld` and sysroot lines
  in CI too (today only the `cc` line and the shape).
- **pax** (the maintainer's step): the release that publishes
  `pax-wolf-link-18.1.8.tar.xz` (`d2046648…`) and `pax-dev.iso`
  (`893ae1b9…`), staged in `~/lanes/px80/stage/` on kasumi and nomad. No
  issue tracks it: the contract's "pax#167" is `user/wolf/host.lu`'s E0802
  warning (open, unrelated); the item is the crawl's of 2026-10-24 23:50.
- Already filed, not refiled: pax#176 (the banner names no commit; this
  ISO is told apart by its sha256 and its MOTD's first line).
- For ligature (ld01/ld02, ligature#4): on PAX's kernel lld 18.1.8 and
  Ubuntu's 18.1.3 give the same bytes (83 links), so either can be the 18.x
  oracle; ligature's own lld 17 is unchanged by this lane. wolf-lang#938
  (the code model) is unaffected.

Pruned already: the LLVM build tree and its extracted source, the
tarball, `kernels/` (2.9 GB), `m2/`, every suite build directory, the
snapshots and the playground extraction on nomad. To prune (by the
orchestrator, literal paths):
- kasumi `~/lanes/px80/` (1.8 GB): `cache/`, `dev/` (the built ISO, the std
  tree, the clone), `link-old/`, `link-new/`, `wolf-bin/`, `lope/`,
  `lope.bundle`, `pax/`, `build/`, `runs/`, `logs/`, `gnupg/`,
  `gnupg-musl/`, `dl/`; then `lld-out/` and `stage/` once the release is
  made; the images `localhost/px80-lld` (1.18 GB) and
  `localhost/px80-ubuntu` (831 MB).
- nomad `~/lanes/px80/`: `stage/` (once the release is made) and the
  worktree `pax/`.
- The plant: branch `px80-plant-sums`, draft pax#177.
- The playground: `~/pax-playground/pax-dev-lld18.iso` stays until the
  maintainer swaps it for `pax-dev.iso`.

README read against the pass: the dev-image paragraphs moved (lld 17 →
18.1.8; W0 link; the mapping sentence px62 made stale) and a newest-part
paragraph names px80; refreshed in a README-only commit.
