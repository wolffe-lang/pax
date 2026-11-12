# px128 — ligature on the dev image, beside lld

PAX's dev image links every program `wolf build` makes on the machine with lld: `wolf build` prints
`wolf build: note: linking through /usr/bin/ld.lld found on PATH (LLD 18.1.8 …); WOLF_LD=cc (or --linker cc)
links with the system linker instead`, and `/etc/pax-release` has no ligature line. This lane traces why,
puts ligature on the dev image, built from a pinned commit as the image's other wolf tools are, and holds it to
rows on the machine beside lld. lld stays the default for builds on the machine, and ligature is the opt-in
(`export WOLF_LD=/usr/bin/ligature`, which also silences the note). The reason was memory: on the 2 GiB guest the
dev image is tested with, ligature `32ec7f43` could not link a pelt-sized program (ligature#35). Its pin is now
`8594073c` (ligature#36), which links pelt and den there in under 3 s. The default stays lld until it is decided
again (§6, decision 1; §11).

Footprint: cross-cutting (the dev image's contents and a new pin, `user/ligature.pin`; `tools/mkligature`,
`tools/distribution-root`; `tests/distribution`, the new `tests/distribution-ligature`; `tools/ci-tiers.map` and
`tests/ci-plan`).

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

## 4. What was done

The first branch was based on trunk `48ea81ba` (pax#369). §4 to §10 cite its commits, which stay on
`px128-before-rebase`; `notes/px128/r2-shamap.txt` gives each one's commit on this branch, `px128-r2`, rebased
onto the 0.2.39 pins (§11). Commits in order:

- `053d5d86`: this note: the trace, the measurements and the prediction, before any change.
- `cb6a4f27`, `fb6cccb8`: `user/ligature.pin` at ligature `32ec7f43`, and later the digest the builder made.
- `6be3b40a`: `tools/mkligature`, the clef and trash builders' twin. It builds from the tree's own
  `wolf-toolchain.toml` (the wolf 0.2.38 gnu archive, read twice, its bundled std checked against the pin)
  through a `cc` that adds `-static -Wl,--build-id=none` and ends with `-fuse-ld=bfd`. It builds in two
  checkouts at paths of different lengths, compares the stripped binaries, checks the result is static and
  runs `--version`. Its output is `ligature 625caa40…, 2,073,816 bytes`, the same from both checkouts.
- `adef7a9a`, red first: `tests/distribution` requires `/usr/bin/ligature` in the dev image (0755, root's,
  the builder's sums, the pin's digest), none in the release image, and a `ligature` line in
  `/etc/pax-release`. It also requires that no image's `/etc/shrc` exports `WOLF_LD`.
- `ef62d5a9` … `2ddaf553`, red first: the new suite `tests/distribution-ligature` (§5). Its rows came before
  the change that installs ligature.
- `aef2bcd7`: `tools/distribution-root` puts `/usr/bin/ligature` in the dev image, held to its sums and
  the pin's digest.
- `551cf80c`: `tests/fetch-retry-selftest` counts mkligature among the source fetches that go through
  `tools/fetch-retry`.
- `5f5ded46`, then `d05a8f63`: the planner's expectation, then `tools/ci-tiers.map`. The pin and the
  builder reach `census` and `mpx6-install`, as trash's and the distribution's paths do. The suite falls under
  `tests/distribution*`.
- `6f825d2a`, `646b7a91`, `72c57eee`, `803f05be`: the README (the dev image's tables, the opt-in, why lld
  stays the default), the CHANGELOG, and `docs/SOURCES.md`.
- `19a445ca`, `02151eff`, `f5b3ffa1`: `notes/px128/rig/`, this lane's record rig (px123's shape): the quick
  checks, the rows seen red, the rows on an image with ligature, and the plant.
- `503d99e5`, `77931d18`, `dea161f0`, then `fdf1b20c` and the two before it: den beside pelt in the suite, and
  yew out of it, after the first red take showed yew's compile fits neither guest.

## 5. The rows

`tests/distribution-ligature IMAGE_DIRECTORY` takes `tools/mkdistribution`'s output and boots the dev
archive as it is, plus one addition under paths the image does not have:

- the session;
- `ldtime`, a measuring `WOLF_LD` built on the host with `cc -static`, never shipped. It runs the named
  linker as its one child and logs wall time, plus CPU time and peak memory from the kernel's `wait4` usage;
- the programs' sources: hello and netproc, which are the suite's own, and pelt, den and ligature at the
  commits the image's own `/etc/pax-release` names.

It boots the image's own console kernel once, at 2048 MiB, and types one session as root, with the console's
environment. Until ligature `8594073c` it booted twice: pelt's link by ligature stopped at 2048 MiB, so a second
boot at 3072 linked pelt and den (§11).

| row | holds |
|---|---|
| L0 | `/usr/bin/ligature` runs (`ligature 0.0.2 …`), and `/etc/pax-release` names it |
| L1 | the default is lld: no `WOLF_LD` in the console's environment; a plain `wolf build`'s program is byte-identical to lld's link and not ligature's; from wolf 0.2.39 the note names `/usr/bin/ld.lld` |
| L2 | the opt-in: `WOLF_LD=/usr/bin/ligature wolf build` prints no note, and its program runs |
| L3 | hello by both linkers, the same output; two ligature links byte-identical |
| L4 | netproc (`std.net`, `std.process`) by both, the same output |
| L5 | ligature compiled and linked by itself on PAX runs (`--version`), and links hello to the shipped ligature's bytes |
| L6 | a refusal (`LIGATURE_SYSROOT` naming an empty directory): ligature's named error, a non-zero `wolf build`, no output, no fallback |
| L7 | pelt by both linkers at 2048 MiB, the same output. Until `8594073c` it was an expected refusal tied to ligature#35, which failed, saying so, the day ligature linked pelt there (§11) |
| L8 | den by both at 2048 MiB, the same output (until `8594073c`: pelt and den by both on a larger guest, den by lld at 2048) |
| L9 | every link above measured (wall, CPU, peak), each with a non-zero peak |
| L10 | the boot clean: the session's end, init's status 0, no panic, the halt proven by `tools/qemu-halt` |

yew is the largest of the image's wolf programs, about 150,000 lines. The first red take showed its compile does
not fit the live image at either 2048 or 4096 MiB: `user: wolf pid N killed: SIGABRT` both times, before any link,
with lld as with ligature. So den, about 38,000 lines, is the largest of the image's programs that its compiler
builds there. On Linux, with the image's own compiler, ligature links yew in 20.8 s at a 1.54 GiB peak, and lld in
0.13 s at 341 MiB.

## 6. Decisions (each open to review)

1. **What the default is on the 2 GiB guest.** The options were:
   - (A) flip it now, with pelt-sized programs at 2 GiB a named red row that `WOLF_LD=cc` gets past;
   - (B) ship ligature and its rows now, and keep lld the default until a pelt-sized link fits that guest;
   - (C) flip it, and run the rows at a larger guest.

   **B, decided before the first change.** A default that fails pelt-sized builds on the configuration the dev
   image is tested with would be a regression for anyone at the machine. The memory is ligature#35.
   ligature#36 fixed it: at `8594073c` ligature links pelt and den at 2048 MiB (§11). B stands until the
   default is decided again. What is left between the two linkers is time, 2.2 to 2.8 s against under 0.1 s,
   and the flip is one line (decision 3).
2. **How the image's ligature is built.** The options were:
   - (A) as clef and trash are: the tree's own pinned wolf release, `cc -static`, two checkouts, stripped;
   - (B) linked by ligature itself against the image's musl inputs;
   - (C) a published binary.

   **A.** It is the image's one way of building a wolf tool, it is reproducible from the pin alone, and it
   needs no publication. B is a good later step toward an image whose linker is linked by itself. The rows
   already hold the self-link on PAX (L5).
3. **Where an opt-in or a later default lives.** The options were:
   - (A) `/etc/shrc`, through `tools/system-env`, which reaches ssh through burrowd's `SetEnv`;
   - (B) a wolf-lang change, so that `wolf build` finds ligature by itself or reads a configuration file;
   - (C) replacing the image's `cc` with ligature's front end.

   **A when the default flips**, which is one line. Today the README documents the opt-in for a person's own
   shell. B needs no change now, because wolf already reads `WOLF_LD`. C would leave wolf's note naming lld
   while lld no longer links. One caveat, for the flip: an upgrade keeps an `/etc/shrc` its owner changed (the
   new one is written as `/etc/shrc.pax-new`), so a changed `/etc/shrc` would not get the default.
4. **Where the rows live.** The options were:
   - (A) a new image-directory suite beside `tests/distribution-boot`, on the actual dev image;
   - (B) `tests/mpx5-wolf` in CI;
   - (C) more lines in `user/console/distribution.keys`.

   **A.** The rows need the real dev image, a 2 GiB guest and minutes of compiling, and CI's `mpx5-wolf`
   leaves out the musl link inputs on purpose. ligature's licensed link bundle carries the same five musl
   inputs byte for byte, so a later CI row could fetch them from it.
5. **The largest program.** yew's compile fits neither the 2048 nor the 4096 MiB live image. The rows use den,
   the largest of the image's programs its compiler builds there, and record yew's links on Linux.
6. **The plant.** The options were:
   - (A) `tools/mkligature` keeping the build-id, so the two checkouts differ;
   - (B) `tools/distribution-root` leaving ligature out.

   **A.** It is red by name at this head with no image to build. B needs a dev image assembled from inputs
   built at this branch's pins. The rows' red take on the machine's image (§8) shows what B would show:
   `L0-package` and every ligature row FAIL by name.
7. **When the 0.2.39 pin lands on trunk** (the terminal-over-ssh work's second pull request), `--latest` builds
   need ligature among their inputs: `ligature` in `tools/mkdistribution`'s `INPUTS_ALL`, and
   `tools/mkligature` in `tools/latest-resolve`'s `BUILDER_PATHS`. That is two lines, tried on this lane's
   integration image (§8) and to be carried by this branch's rebase onto that pin, as a new branch and pull
   request. Nothing else here depends on the compiler's version. Before 0.2.39, wolf 0.2.36 prints no note at
   all, so `L1` holds the default by bytes alone.

8. **The larger guest, once ligature links pelt and den at 2048 MiB.** The options were:
   - (A) drop it: one boot at 2048 MiB, pelt and den first, by both linkers;
   - (B) keep a second boot at 3072 MiB as a margin.

   **A.** 2048 MiB is the size the dev image is tested with, so a regression there fails L7 or L8 by name. The
   take is shorter: 213 s against 353 s for the two boots (§11).
9. **ligature under `--latest`.** The options were:
   - (A) at its pin, as the compiler is: `tools/latest-resolve` does not resolve it, and a `--latest` build
     builds `user/ligature.pin`'s commit;
   - (B) at ligature's trunk head, as trash and the other org trees are.

   **A.** The image holds ligature to the digest its pin records (`tools/distribution-root`,
   `tests/distribution`), and a moving head would fail that check by design. B needs the check to follow the
   resolution.

## 7. For the person at the machine

On an image built with this branch:

```sh
ligature --version                     # ligature 0.0.2 (static ELF; x86-64, AArch64 subset)
grep '^ligature ' /etc/pax-release
wolf build hello.lu                    # as before: lld, and wolf's note naming /usr/bin/ld.lld
export WOLF_LD=/usr/bin/ligature
wolf build hello.lu && ./hello         # no note; the link takes about 2 s
WOLF_LD=cc wolf build hello.lu         # lld again, for this one build
```

The real machine has far more memory than the 2 GiB guest, and its root is on a disk, not in memory. So
`export WOLF_LD=/usr/bin/ligature` should link pelt-sized programs there too. That is a prediction, not a
measurement: this lane never touched a real machine.

## 8. Evidence index

Records are taken by the steps recorder through `notes/px128/rig/` (light takes on the Linux build host,
both-lock takes on the second Linux host). Each is cited by sha256. The integration image is lane-local and
never pushed: it is px117's image branch (`bf1e38db`, the 0.2.39 pins and `--latest`) with this branch's image
commits, ligature among the `--latest` inputs, and the pin-parse fix. It was built at `87137d71`, from a fresh
resolution at `928b2be9`. Every input whose resolved revision equalled the machine's image's was copied by value
from that build; the std moved to `be1d10fa` and was fetched.

| what | where | result |
|---|---|---|
| quick checks at `19a445ca` (ci-plan, census, fetch-retry, mkligature) | `quick-19a445caf147.record`, sha256 `4c4d4bc748b5fd4bbb01c042c6daa88ef7089e780403d47b885e816976ba0f67` | worst=0, steps=4; mkligature `625caa40…`, the pin's |
| the rows seen red on the machine's image (65d972ac, no ligature), at `19a445ca` | `red-19a445caf147.record`, sha256 `514e9ae108c24e0280582e23d24b522bdaf094a7cb1fb025d5cd86478c4e7d85` | `FAIL L0-package`, L2 to L9 FAIL by name; L1 and L10 PASS; yew's compile `killed: SIGABRT` at 2048 and 4096 MiB |
| the same at `fdf1b20c` (pelt and den) | `red-fdf1b20ccf0d.record`, sha256 `4057436f9a073d4e6cd335944b6f36b711d0ee680ddd84057551b4dd2efdd2c2` | `FAIL L0-package`, L2 to L9 FAIL by name; L1, L8 (den by lld at 2048) and L10 PASS. Found: the image has no `sed`, so the session's `why` and `ldtime` lines were lost (fixed in `092acbe7`, the row tightened to ligature's own error) |
| the integration image's assembly at `928b2be9` | the build's log | `tools/distribution-root` refused its own input: `ligature is not the digest user/ligature.pin records`. The pin parse read the pin's prose lines that start with "ligature" too (fixed in `16d5eac6`, `30d4d005`) |
| the integration image at `87137d71` | `pax-dev-87137d71.cpio`, sha256 `ea0d394a0af22b8b61d165e0cc42d82c40973058f9175ab894c83b9c1caeb9c0` | `tests/distribution` I0 and I1 PASS for both variants; `/etc/pax-release`: `ligature 32ec7f43… aa5e6f35…` |
| the rows on it at `87d46c9f` | `green-87d46c9fff07.record`, sha256 `76323d340c45ecd97fa7189b82f09339bea30eca00b55a5a66b904c37ce4bdb6` | every row PASS but `L8-den-at-big`: ligature's link of den stopped for memory at 2560 MiB (peak 819 MiB). The larger guest moved to 3072 (`a8d97cdb`) |
| the rows on it at `a8d97cdb` (the larger guest at 3072 MiB) | `green-a8d97cdbda51.record`, sha256 `44dd366c15095509e0cf3d2af1efd98185f3112d2650fbb43581f9ad6e63bf61` | worst=0, steps=1: L0 to L10 PASS, 13 links measured |
| the upgrade from the machine's image | px117's over-ssh leg (copied by value, `fac31ec0…`) and this lane's `upgrade-rows.py` (`f6b365e8…`), log sha256 `da3693523aff87409e9386363de83acab220a8026f71b514061d8ab30be96931` | a disk shaped like the machine's, running 65d972ac (`25a93538…`), is sent the integration archive over ssh, armed, and upgraded by the staged boot (S1 PASS: 642,754,220 bytes received in 78 s). On the upgraded disk: `/usr/bin/ligature` 0755 and `/etc/pax-release` the archive's, with its ligature line (U1); no `WOLF_LD`, so a plain `wolf build` names lld and runs (U2); `WOLF_LD=/usr/bin/ligature` builds with no note and the program prints the same line (U3); the two outputs differ and `ligature verify` reads ligature's back (U4) |

**Link time and peak memory on PAX**, from the kernel's `wait4` usage (`ldtime`). The record is
`green-a8d97cdbda51.record`, under KVM on one vCPU. PAX's `ru_maxrss` is the peak of the process's mapped
pages, so it reads above Linux's resident peak.

| guest | program | ligature: wall, CPU, peak | lld (the image's cc): wall, CPU, peak |
|---|---|---|---|
| 2048 MiB | hello | 12.73 s, 12.73 s, 793 MiB | 0.07 s, 0.09 s, 123 MiB |
| 2048 MiB | netproc | 13.45 s, 13.44 s, 825 MiB | 0.08 s, 0.09 s, 125 MiB |
| 2048 MiB | ligature | 13.38 s, 13.38 s, 828 MiB | 0.08 s, 0.09 s, 126 MiB |
| 2048 MiB | pelt | stopped at 12.08 s, peak 888 MiB, status 134 (ligature#35) | 0.09 s, 0.10 s, 143 MiB |
| 2048 MiB | den | not run (larger than pelt) | 0.09 s, 0.11 s, 144 MiB |
| 3072 MiB | pelt | 16.48 s, 16.50 s, 944 MiB | 0.08 s, 0.10 s, 143 MiB |
| 3072 MiB | den | 16.40 s, 16.38 s, 925 MiB | 0.09 s, 0.10 s, 144 MiB |

At 2560 MiB, pelt's link took 16.40 s at a peak of 944 MiB, and den's stopped at a peak of 819 MiB
(`green-87d46c9fff07.record`). On Linux, with the image's compiler and the same inputs, the linker's resident
peaks were ligature 640 to 773 MiB (yew 1.54 GiB) and lld 110 to 341 MiB (§2; yew, den and lobo measured too:
ligature 20.8 s, 10.2 s and 9.5 s; lld 0.06 to 0.13 s).

## 9. Prediction, scored

1. The package: **as predicted.** The two checkouts give one stripped digest, `625caa40…` (2,073,816 bytes),
   in every take.
2. The image: **as predicted, after one fix.** The first assembly refused its own input: the pin parse also read
   the pin's prose lines that start with "ligature". That was fixed in both readers (`16d5eac6`, `30d4d005`).
   The release image carries no ligature, and `/etc/pax-release` has the line.
3. The default: as decided. `L1` and `U2` hold it on the live image and on an upgraded disk.
4. The rows:
   - The suite is `tests/distribution-ligature`, not the `tests/mpx5-ligature` predicted. It sits beside the other
     image-directory suites and under their plan rule.
   - **Missed: the largest program.** yew's compile fits neither a 2048 nor a 4096 MiB live image, so den stands
     in for the largest. ligature's den link needs 3072 MiB, not the 2560 that pelt needs.
   - **Missed: the times and peaks on PAX.** 12.7 to 16.5 s, against the 10 to 12 s predicted; 793 to 944 MiB,
     against the 640 to 750 predicted. The predicted ranges were Linux's; PAX counts mapped pages, on one vCPU.
     lld was 0.07 to 0.09 s and 123 to 144 MiB, not about 1 s.
   - **Found on the way:** the image has no `sed`. The session prefixes lines with the shell's own loop.
5. The upgrade: **as predicted** (U1 to U4).
6. The plant: **changed.** It is mkligature keeping the build-id (§6, decision 6), not `distribution-root`
   leaving ligature out. The red take on the machine's image shows what that one would.

## 10. Bounds, and what is not done

- **Not shipped by this lane:** no image, release, tag or asset. The integration image of §8 is lane-local and
  never pushed; it shows the branch is fit for an image. ligature's link bundle is not needed for that.
- **lld and the link-only `cc` stay on the image,** and lld stays the default. ligature#35 no longer stands
  in the way (§11); removing them, or flipping the default, is a decision of its own. The flip is one line in
  `tools/system-env` (§6, decision 3).
- **The 0.2.39 line.** The first branch was based on trunk, whose dev compiler was 0.2.36, and its rows ran on
  a lane-local 0.2.39 integration image. This branch is based on the 0.2.39 pins and adds ligature to
  `--latest` (§6, decision 7); its rows ran on a dev image built from those pins (§11).
- **yew** cannot be compiled on the live dev image at 2 or 4 GiB. The compiler stops for memory before any link,
  with either linker. That is a finding about the compiler on a live image, not about either linker.
- **The real machine** was never touched. §7's commands are what a person there would try.
- **The plant** is in the hand-back with its record. It is pushed without a pull request, never merged.

## 11. The rebase, and ligature `8594073c`

**The rebase.** This branch, `px128-r2` (pax#373), carries the first branch's 42 commits, cherry-picked onto
`e87b480b`. That is the head of the terminal-over-ssh work's second pull request (pax#372, stacked on pax#366 and
pax#367), which brings wolf 0.2.39, the pins the images carry and `--latest`. Two commits met the base's new
entries in `CHANGELOG.md` and `docs/SOURCES.md`; both entries were kept. pax#369 is closed with a pointer here.
`notes/px128/r2-shamap.txt` maps each old commit to its new one. Then:

- `4cd03d75`: ligature among a `--latest` build's inputs (`INPUTS_ALL`) and builder paths (`BUILDER_PATHS`), the
  two lines tried on the integration image (§6, decision 7).
- `36cc5d94`: `user/ligature.pin` at ligature `8594073c` (ligature#36, for ligature#35). Its toolchain pin is
  `32ec7f43`'s (wolf 0.2.38, std `d4a4d4ca`), so `tools/mkligature` builds it unchanged. Two checkouts give
  `b6772781…`, 2,225,368 bytes, on both Linux hosts.
- `642e4b72`: the README's pin row. The image below is built at this commit.
- `2a4a603b`: `notes/px128/rig/pin.manifest`, the rows as they stood at the move.
- `29948bbe`, `78bb5f41`, `99922d16`: the flip. One session at 2048 MiB, pelt and den by both linkers first;
  L7 and L8 plain link rows; one boot (§6, decision 8).
- `f8da8c15`: `notes/px128/rig/flip.manifest`, the rows after the flip.
- `72c934f7`, `610ce5f1`, `9080b3e6`, `ed4a43fe`, `35dadcb3`: `docs/SOURCES.md`, the sha map, the README, the
  CHANGELOG, and `final.manifest` on the new image.

**The image.** A pinned build at `642e4b72`, `tools/mkdistribution BASE INPUTS OUT`, the form CI and lane records
use. The base payload is `098b918e…`, read twice. Every input is at the head's pins:

- Fifteen inputs were copied by value from the integration image's build (§8). Each was at the same revision as
  the head's pin, and no builder path differs between `928b2be9` and the head but `user/ligature.pin`. They are
  pelt, scent, lope, aspen, lobo, boreutils, burrow, sniff, trash, lupin (its binary `c96021ad…`, the pin's), the
  dev compiler (every file `user/wolf.sums`'), the games, auth, roots and wolf-std.
- Four were built at the head: den `291011dd` (`f9a8cde9…`), yew `3a9983ee` (`339b688d…`), the base std
  `77cf3210`, and ligature (`b6772781…`).

`tests/distribution`'s I0 and I1 pass in the assembly, for both variants. The archive is `pax-dev-642e4b72.cpio`,
641,921,820 bytes, sha256 `cae674a512e54b67c5366cf28b83183894c25f92f1dd05c6f061beb2327a4c47`. Its
`/etc/pax-release` has `ligature 8594073c… 62ea3b89…`. Nothing the image is built from moved after `642e4b72`:
later commits touch the suite, the notes, the README, the CHANGELOG and `docs/SOURCES.md` only.

**Prediction**, written in pax#373's body before either take: with `8594073c`, ligature links pelt and den on the
2 GiB guest, so L7 goes red at the pin move, and after the flip it is a plain passing row.

| what | record (sha256) | result |
|---|---|---|
| the rows as at the move, `pin.manifest` at `2a4a603b` | `pin-2a4a603b6a8e.record`, `05044779a174ea9b972473574edb33432aee989198c28702d1277fea115b41a3` | worst=1, `END rows-ligature exit=1 secs=353`: `FAIL L7-pelt-at-small — ligature linked pelt at 2048 MiB: ligature#35 looks fixed, so this expected refusal must become a link row`. Every other row passes, pelt and den by both at 3072 among them |
| the rows after the flip, `flip.manifest` at `f8da8c15` | `flip-f8da8c15149a.record`, `efa51665f64297d537defacf09cfc42f9d788fbd9a1f5d32405ca3ceb786259d` | worst=0, `END rows-ligature exit=0 secs=213`: L0 to L10 pass; `L7-pelt` and `L8-den`, by both at 2048 MiB, the same output |

**Scored: as predicted.** The red row named itself, and the flip turned it green with den beside it.

**Link time and peak memory on PAX**, wall and `wait4`'s peak, under KVM on one vCPU (ligature's CPU time is
its wall time to within 1%). The first column is `green-a8d97cdbda51.record` (§8). The others are the flip
record at 2048 MiB and the pin record at 3072.

| guest | program | ligature `32ec7f43` | ligature `8594073c` | lld |
|---|---|---|---|---|
| 2048 MiB | hello | 12.73 s, 793 MiB | 2.20 s, 174 MiB | 0.07 s, 123 MiB |
| 2048 MiB | netproc | 13.45 s, 825 MiB | 2.33 s, 186 MiB | 0.07 s, 125 MiB |
| 2048 MiB | ligature | 13.38 s, 828 MiB | 2.31 s, 183 MiB | 0.08 s, 127 MiB |
| 2048 MiB | pelt | stopped at 12.08 s, 888 MiB, status 134 | 2.61 s, 223 MiB | 0.09 s, 143 MiB |
| 2048 MiB | den | not run | 2.76 s, 234 MiB | 0.08 s, 143 MiB |
| 3072 MiB | pelt | 16.48 s, 944 MiB | 2.62 s, 223 MiB | 0.08 s, 143 MiB |
| 3072 MiB | den | 16.40 s, 925 MiB | 2.78 s, 234 MiB | 0.08 s, 143 MiB |

The peaks fell four to five times and the times about six. A link by ligature still takes 29 to 34 times lld's
time, and peaks at 1.4 to 1.6 times lld's memory. Two links of hello by ligature are byte-identical, and the
ligature compiled and linked on PAX links hello to the same bytes as the shipped one (L3, L5).
