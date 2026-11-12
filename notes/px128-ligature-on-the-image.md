# px128 — ligature on the dev image, beside lld

PAX's dev image links every program `wolf build` makes on the machine with lld: `wolf build` prints
`wolf build: note: linking through /usr/bin/ld.lld found on PATH (LLD 18.1.8 …); WOLF_LD=cc (or --linker cc)
links with the system linker instead`, and `/etc/pax-release` has no ligature line. This lane traces why,
puts ligature on the dev image, built from a pinned commit as the image's other wolf tools are, and holds it to
rows on the machine beside lld. lld stays the default for builds on the machine, and ligature is the opt-in
(`export WOLF_LD=/usr/bin/ligature`, which also silences the note). The reason is memory: on the 2 GiB guest the
dev image is tested with, ligature cannot yet link a pelt-sized program (ligature#35).

Footprint: to be stated with the PR (the image's contents, `tools/`, `tests/`).

## 1. The trace

**What the image's half of the linker's milestone delivered: nothing, because it never ran.** ligature's campaign
put "the dev ISO drops lld and the `cc` front end" in its second milestone, as PAX's half beside ligature's own
work and the `--linker` seam in wolf-lang. The PAX half was scheduled after the lld 18 respin (px80) and the
assembler seam (as02b). Both of those merged. This tree has no branch, commit, note or pull request for the PAX
half. "ligature" appears here only in the future tense: px80's and as02b's notes name the linker's package as
ligature's milestone, and px88's note credits ligature with finding pax#175. Nothing was merged and then
reverted. Two things overtook it instead:

- When ligature's milestone work merged, its note said no milestone was claimed past one blocker: a
  musl-linked program read `argc=0` (wolf-lang#962). That blocked the self-link and blocked running ligature
  on PAX. wolf 0.2.36 fixed it. ligature then moved its pin to 0.2.36 and later to 0.2.38, but the PAX half
  was never queued again.
- ligature's own README still says "Running that newly self-linked linker inside PAX is not established by the
  Linux gate".

**The pins today.**

| | ligature trunk `32ec7f43` | the dev image as the machine runs it (`65d972ac`) | pax trunk `48ea81ba` |
|---|---|---|---|
| wolf | 0.2.38 (`95ae0827`), its gnu release archive `8447a579…`, to build ligature itself | 0.2.39 (`3fc86f77`), static musl from `tools/mkwolf`, `55e196a4…` | 0.2.36 (`5adf3d91`), `user/wolf.pin` |
| runtime | wolf-rt 0.2.38 musl, `libwolf_rt.a` `37252e1d…` (its CI's) | `/usr/bin/libwolf_rt.a` `db50108f…`, 47,693,716 bytes | `6892dac8…`, 46,700,882 bytes (`user/wolf.sums`) |
| std | `d4a4d4ca` | compiler std `2411d868`, lupin's std `77cf3210` | compiler std `78b9d3cb`, lupin's `3111d39f` |
| musl inputs | the link bundle's `sysroot/` | `/usr/lib/wolf-musl`, `user/wolf-link.sums` | the same |
| linker | — | `ld.lld` 18.1.8 and the link-only `cc` | the same |

The five musl inputs, `crt1.o`, `crti.o`, `crtn.o`, `libc.a` and `libunwind.a`, are byte-identical in
ligature's link bundle and in `user/wolf-link.sums`, and so is the link-only `cc`. Only `ld.lld` differs:
the bundle carries lld 17 as ligature's oracle, the image lld 18.1.8. The 0.2.39 compiler reaches pax trunk with
the pin move that follows the terminal-over-ssh work. The machine's image was built ahead of it, from every tree's
newest head.

**wolf-lang already has what the image needs.**

- `--linker PATH` and `WOLF_LD` select a cc-shaped linker (wolf-lang#961, merged 2026-10-25, in 0.2.36 and
  later).
- A selected linker gets `-o OUT OBJECTS RUNTIME -lpthread -ldl -lm -Wl,--gc-sections`. Its failure is final:
  there is no fallback.
- With neither set, the Linux link is `cc`, plus `-fuse-ld=lld` whenever an `ld.lld` is on `PATH`. The note
  above names that lld. It comes from wolf-lang#1082, released in 0.2.39, and it prints on every build of a
  binary that selects no linker.
- A nonempty `WOLF_LD` prints no note.
- ligature's cc front end takes exactly that argument line. It reads the musl inputs from
  `/usr/lib/wolf-musl`, the directory the image already uses, unless `LIGATURE_SYSROOT` names another. It
  accepts and ignores `-fuse-ld=lld`.
- So the image can make ligature the default by itself: one `export WOLF_LD=/usr/bin/ligature` line among
  `tools/system-env`'s dev lines. That reaches the console through `/etc/shrc` and ssh through burrowd's
  `SetEnv`. lld would stay one word away: `WOLF_LD=cc`, the image's link-only `cc`, runs `/usr/bin/ld.lld`.
- One limit belongs to the upgrade, not to wolf. An upgrade keeps an `/etc/shrc` its owner changed and writes
  the new one beside it as `/etc/shrc.pax-new`, so a changed `/etc/shrc` would not get the default.

**The link bundle.** ligature's `link-bundle-wolf-0.2.38` release is the licensed, digest-pinned set of binary
inputs that ligature's own CI and oracles need:

- PAX's lld 17 control;
- the link-only `cc`;
- the five musl inputs;
- the 0.2.38 musl runtime;
- the licence texts of each.

The image does not need it. It already carries the five musl inputs byte for byte. The runtime it links is its
own compiler's, not the bundle's 0.2.38. ligature builds from its pinned commit exactly as clef and trash do: its
own `wolf-toolchain.toml`'s release archive, and a `cc` that adds `-static`.

## 2. Measured before any change

ligature `32ec7f43` was built static with its own pinned wolf 0.2.38 and `cc -static`, as the image builds
clef and trash. It took 0.7 s and produced 16,476,856 bytes, `561afeaa…`, printing
`ligature 0.0.2 (static ELF; x86-64, AArch64 subset)`.

**On Linux, with the image's own compiler.** The machine's dev archive supplied wolf 0.2.39, its compiler std,
its runtime and its musl inputs, all run on Linux. Four programs:

- hello;
- `netproc`, which uses `std.net` (a loopback listener, connect, accept, an exchange each way) and
  `std.process` (it starts `/bin/echo` and waits for its status);
- pelt at `b80d6570`, about 30,000 lines;
- ligature itself.

Each was linked by ligature and by the image's `cc` and lld 18.1.8, through a `WOLF_LD` wrapper that times the
linker as its one child and reads its `ru_maxrss`.

| program | ligature: wall, peak resident | lld: wall, peak resident | output bytes, ligature / lld | behaviour |
|---|---|---|---|---|
| hello | 7.64 s, 640 MiB | 0.050 s, 110 MiB | 46,004,568 / 15,356,824 | identical |
| netproc | 7.96 s, 670 MiB | 0.046 s, 111 MiB | 48,327,136 / 15,929,912 | identical |
| pelt | 9.04 s, 750 MiB | 0.055 s, 129 MiB | 58,901,920 / 24,776,760 | identical |
| ligature | 7.92 s, 670 MiB | 0.046 s, 113 MiB | 48,545,936 / 16,552,608 | identical |

**On PAX.** The setup:

- the machine's dev archive, unchanged but for `/usr/bin/ligature` and the four programs' sources;
- its own console kernel, under QEMU with KVM, 2 GiB of RAM, BIOS;
- two boots.

Times come from `date +%s`, because the shell's `times` reads 0 there. Each build of a program ran four
times: the default, which compiles and links with lld; ligature, which reuses the compiled objects; the
default again; ligature again. So each link time is a warm build's.

- **hello and netproc** link with both linkers, and each pair behaves identically. ligature's links take 9 to
  12 s, lld's 1 s or less. ligature's output is deterministic on the machine: two links of hello are
  byte-identical, `ac7a13c7…`.
- **ligature on PAX, compiled and linked by itself there,** runs. It is `2dbd95bb…` in both boots. It links
  hello to the same bytes as the shipped ligature, `ac7a13c7…`.
- **pelt does not link with ligature at 2 GiB.** PAX logs `user: ligature pid N killed: SIGABRT`, after
  `memory allocation of 1048576 bytes failed` (in the second boot, of 9071888 bytes). `wolf build` prints
  `selected linker: "/usr/bin/ligature" … failed linking /tmp/w/pelt.lig` and exits 2. Nothing falls back to
  lld. lld links the same pelt in both boots, `bfcf2dfd…`, and it runs.
- The 2 GiB guest reports 1,478,762,496 usable bytes. The live image's files, about 650 MB, sit in memory, and
  the `wolf build` process stays resident while its linker runs.
- With more memory, ligature links pelt and the result runs as lld's does (`pelt-ok`, status 3):

| guest | usable bytes | ligature links pelt | the link |
|---|---|---|---|
| 2048 MiB | 1,478,762,496 | no (both boots) | — |
| 2560 MiB | 2,015,633,408 | yes | 30 s |
| 3072 MiB | 2,552,504,320 | yes | 26 s |
| 4096 MiB | 3,626,246,144 | yes | 26 s |

The memory and the output size are filed against ligature as ligature#35.

## 3. Prediction (written before the first change)

1. **The package.** `tools/mkligature` builds ligature at `user/ligature.pin`'s commit. It uses that tree's own
   pinned toolchain and a `cc` that adds `-static -Wl,--build-id=none` and links with GNU ld, as trash's
   reproducible build does. It builds in two checkouts at different paths, and their stripped binaries are
   byte-identical. Without the build-id and the strip they are not: two paths gave two digests in this lane's
   first test.
2. **The image.** The dev image carries `/usr/bin/ligature`, root's and 0755, at the digest the pin records;
   the release image carries none. `/etc/pax-release` gains a `ligature` line from the pin, as every
   `user/*.pin` does. `tests/distribution` holds both: red on the base, green after.
3. **The default stays lld, decided before the first change.** `tools/system-env` is unchanged: no
   `WOLF_LD` in the image's environment, so a plain `wolf build` still links through lld and prints the
   note. The README documents the opt-in, `export WOLF_LD=/usr/bin/ligature`, which also silences the note,
   and the measured floor: a pelt-sized link needs a 2560 MiB guest today (ligature#35). Flipping the default
   later is one line in `tools/system-env`.
4. **The rows on the machine** (a new suite, `tests/mpx5-ligature`, on a dev image directory). Each one is red on
   an image without ligature, by name:
   - hello, netproc and the self-link are linked by ligature and by lld on the 2 GiB guest, and each pair
     behaves identically;
   - with no `WOLF_LD`, a build links through lld and prints the note (the default this image keeps);
   - at 2 GiB, pelt's link by ligature is an expected refusal tied to ligature#35: a non-zero `wolf build`
     naming the selected linker, with no output and no fallback. The row turns red the day ligature links
     pelt there, so it flips with the issue. lld links pelt at 2 GiB, and at 2560 MiB ligature links pelt and
     the largest program the machine builds, each behaving as lld's link does;
   - a refusal (a missing musl input) is a named error from ligature and a non-zero `wolf build` with no
     output file;
   - link time and peak memory for both linkers, read from the kernel's own `wait4` usage. I predict ligature at
     about 10 to 12 s and 640 to 750 MiB, and lld at about 1 s and 110 to 130 MiB.
5. **The upgrade.** `pax-upgrade` from the machine's `65d972ac` brings `/usr/bin/ligature` and its
   `/etc/pax-release` line. A row on the upgraded disk links hello with ligature, and the program runs.
6. **One plant**, on the final head: the image without ligature (`distribution-root` skipping it), red by
   name in `tests/distribution` and in the suite's first row.
