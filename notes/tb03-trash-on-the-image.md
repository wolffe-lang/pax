# tb03: trash on the image (T3, the second part)

trash's five commands (`trash`, `trash-list`, `trash-restore`, `trash-rm` and
`trash-empty`, wolffe-lang/trash) go onto PAX's image as sniff's hook would
put sniff there: a pin (`user/trash.pin`), a builder (`tools/mktrash`), the
distribution's root (`tools/distribution-root`) and its check
(`tests/distribution`), and a session typed at the console
(`tests/mpx5-trash`), held to the same binaries in a Linux container. The
first part (trash#4, merged at trash `90169ed`) hardened the commands; this
part ships them.

## Prediction (written before any change)

Sources for this section: sniff's hook as its own lane wrote it (its
`tools/mksniff`, `user/sniff.pin` and the distribution and CI lines that go
with them; not yet in this tree), PAX's
own `tools/mkburrow`, `tools/mkscent`, `tools/distribution-root`,
`tests/distribution`, `tests/mpx5-scent` and `tools/ci-tiers.map`, and
trash's `tools/build.py`, `wolf-toolchain.toml` and its PAX rows (19, green
at `90169ed` on PAX trunk `db516c69`'s console kernel). Nothing below has
been run.

### The pieces

- **`user/trash.pin`**: `TRASH_REPO`, `TRASH_REV` (trash `90169ed`, a full
  sha), the codeload source archive's sha256 at that commit (read twice),
  and the five binaries' digests and sizes as trash's own gate built them
  (its `trash-static` step: wolf 0.2.38, the default tier, through a `cc`
  that adds `-static`, then stripped).
- **`tools/mktrash OUTDIR`**: `tools/mkburrow`'s twin. trash at the pin,
  through `tools/fetch-retry`, in two checkouts; the wolf release archive
  its `wolf-toolchain.toml` pins, by digest, read twice, cached in
  `PAX_CACHE` (the standard library is the archive's own); trash's own
  `tools/build.py --static` in each checkout; the stripped binaries of the
  two must agree, each checked static (ET_EXEC, no `PT_INTERP`, no dynamic
  section); `OUTDIR/sums.txt` gets `NAME <sha256> <bytes>` for the five;
  whether each is the pin's digest is printed (the binary depends on the
  `libc.a` it links); `trash --version` must answer.
- **The image**: the five as `/bin/trash`, `/bin/trash-list`,
  `/bin/trash-restore`, `/bin/trash-rm` and `/bin/trash-empty`, 0755,
  root's, byte for byte as `tools/mktrash` built them (already stripped by
  trash's own build, so not stripped again).
- **`tests/distribution`**: a row that each of the five is on the image,
  0755, root's, its bytes the builder's and its sha256 and size the ones
  `user/trash.pin` names.
- **`tests/mpx5-trash`** (`mpx5-scent`'s shape): one image, pelt as
  `/bin/sh`, the five commands, boreutils' `printf` and `mkdir`, `as`; two
  sessions typed at the console (`user/console/trash.keys`), as root
  (`HOME=/`, so the trash is `/Trash`) and as `pax` (`HOME=/home/pax`):
  files and a tree made, trashed, listed (the paths, the dates left out,
  since PAX's clock and the container's differ), a missing operand refused,
  a directory restored by its path with its contents back, a pattern
  removed, the trash emptied through `-i` with its question answered, the
  trash's directories empty after it, and `--version`.
  - A0: the build (every program static, the five twice to one digest).
  - A1: each session byte for byte the same binaries' in a throwaway Linux
    container (`tools/linux-tree`).
  - A2: the session's own witness (`tests/mpx5-trash.d/rows.py`): the
    statuses, the listings, the restored bytes, the question's words, an
    empty trash at the end.
  - A3: `-ENOSYS` only for `set_robust_list` (273) and `rseq` (334), as for
    every static glibc program here; nothing refused by name; init ends
    with status 0; halted.
- **CI**: a `mpx5-trash` job, the map's lines for the pin, the builder and
  the keys (`mpx5-trash`, and the pin `census mpx6-install` too, as
  burrow's), `mpx5-trash` in `@user` and `@asuser` (its second session runs
  through `as`), the planner's cases, and `tools/mktrash` among
  `tests/fetch-retry-selftest`'s source fetches (18 of them).
- **Prose**: the README's component table, `docs/SOURCES.md`, the
  CHANGELOG.

### Predicted results

- `tools/mktrash` builds the five twice to one digest each; in an Ubuntu
  24.04 container with the same glibc as trash's oracle image the digests
  are trash's gate's.
- `tests/mpx5-trash`: A0 to A3 hold on the native and release tiers, BIOS
  and UEFI. The sessions are the same on PAX as in the container: the
  commands' only host differences (`flock`, which PAX implements; the clock)
  do not reach the transcript.
- `tests/distribution` holds the five on both variants.
- The footprint is **cross-cutting**: a pin, the CI map and a CI job change.

### Red first, and the plant

- `tests/mpx5-trash` and the distribution row are committed before the
  hook (the pin, the builder, the root's lines): A0 is red by name (no
  `tools/mktrash`), and `tests/distribution` is red at `image-trash-missing`.
- The plant (one hunk on the green head): `tools/mktrash` ships
  `trash-rm`'s bytes as `trash-empty`. `tests/mpx5-trash` goes red by name
  at A2 (the empty's question never asked, the trash not emptied), and the
  distribution row at `image-trash-pin-trash-empty`.

## Since the prediction: the pin at trash `c027df8`

Re-reading the first predicted result above (the builder's digests are
trash's gate's) before any run: at `90169ed` it could not have held. Each
binary named its modules by their absolute paths, and the link's build-id
hashed them, so tools/mktrash's two checkouts would have refused each
other. In PAX's build image, which has an `ld.lld` on `PATH`, wolf 0.2.38
links through lld, whose bytes are not the system linker's that trash's
oracle image uses.

trash#5 (merged at `c027df8`) makes the five depend on the commit alone. It
builds from the tree's root by relative paths, with no build-id, and forces
the system linker after wolf's own arguments. trash's gate holds this: its
`repro` row builds the five at two paths and again with an `ld.lld` on
`PATH` that refuses to link. wolf's silent choice of lld is filed as
wolf-lang#1082.

- **`user/trash.pin`**:
  - `TRASH_REV` is now `c027df8`.
  - The codeload source archive's sha256 is `2bc57c82…`, read twice from
    two downloads.
  - The five digests and sizes are the ones trash's own gate printed at
    `c027df8` (its record's `repro` step).
- **`tools/mktrash`**: its two-checkout agreement check stays.
- **Measured:** the builder's digests are trash's gate's. In PAX's build
  image (Ubuntu 24.04, `ld.lld` on `PATH`), `tools/mktrash` builds the five
  twice and both checkouts agree. Each of the five is the digest
  `user/trash.pin` quotes from trash's gate (`trash` `f7c2cb3b…`, 1853976
  bytes, and the other four), all five byte for byte.

## Dev runs, and what they changed

The dev runs used PAX trunk `db516c69`'s native console kernel and the
staged pelt; boreutils came from `tools/mkboreutils` at its pin. They held:
- A0, the build and the Linux side;
- A1, each session byte for byte the container's, 72 lines each;
- A2, the 17 rows;
- A3, on the native tier, BIOS and UEFI, both sessions.

The release tier and `tests/distribution` are left to CI: the release
tier needs a release console kernel, and the distribution check needs the
whole distribution built. Three things the prediction did not foresee:

- **`trash-rm` is never run by the builder.** As trash-cli's does, it takes
  its first word as the pattern to remove from the trash, so
  `trash-rm --version` is a pattern, not a question. It printed nothing and
  the builder refused it. `tools/mktrash` now asks `--version` of the other
  four only.
- **boreutils' `env` and `id` are on the console image.** The user's run
  line execs `/bin/env`: without it, `as` answered `execve /bin/env: -2`.
  The keys' `$(id -u)` names each session's scratch directory: without
  `id`, both sessions shared `/tmp/w`. Root's run made it, and the user's
  run on PAX could not write in it, where the container, a fresh root for
  each session, could.
- **The PATH row holds the loop's answers, not its line.** The line is
  longer than the console's 80 columns and wraps where the terminal puts
  it, on PAX and in the container alike.

## Rulings

- **R-tb03-12, ruled A:** trash's build was made reproducible as a trash
  follow-up, before this pin moved (trash#5).
- **R-tb03-13, ruled A:** this hook's footprint is cross-cutting. Its PR
  opens against the trunk named after px106, px107 and px108.
- **R-tb03-14 and R-tb03-15:** not ruled on their own. The coordinator
  decided them inside R-tb03-12's ruling, whose outcome is that every
  checkout and trash's own gate give the same bytes.
  - R-tb03-14 is A: the system linker forced, held by `repro-linker`.
  - R-tb03-15 is B: wolf's silent lld filed as a documentation issue
    (wolf-lang#1082).

## The rebase onto `4d899ea4`

PAX trunk moved from `db516c69` to `4d899ea4` (px106's passwords, px107's
clock, px108's block copies). Five of this branch's files met trunk's
changes, and each keeps both sides:
- `tests/distribution`'s I0 line;
- `tools/distribution-root`'s inputs, `auth/` beside `trash/`;
- `tools/ci-tiers.map`'s `@user` and `tools/mkas` lines;
- `tests/ci-plan`'s `ASUSER`;
- `tests/fetch-retry-selftest`'s sites, `tools/mkauth` beside
  `tools/mktrash`, still 18.

The account programs px106 added (`su`, `sudo`, `passwd`, `login`) go into
the distribution's root beside trash's five, never over them. Each of
trash's five is refused if its name is already in the root (`trash would
replace bin/NAME`), and none of the names meet. The metal leg's live tree
(`tests/mpx6-install.d/metal.py`) is built from its own list, which trash
is not on.

More rulings, both decided by the coordinator inside the contract:

- **R-tb03-16 is A: the image holds the pinned digests.** A drift turns
  `image-trash-pin-*` red by name, and that is what a pin is for.
  - Where the check runs: `tests/distribution` runs inside
    `tools/mkdistribution`, where the distribution is built, not in a CI
    job. CI's `mpx5-trash` builds the five on its runner, and
    `tools/mktrash` prints whether each is the pin's digest.
  - The match is proven on two images, both Ubuntu 24.04 with
    libc6-dev 2.39-0ubuntu8.9, binutils 2.42-4ubuntu2.10 and gcc-13
    13.3.0-6ubuntu2~24.04.1:
    - trash's gate image, from the apt snapshot of 2026-11-07;
    - PAX's build image, the same three with LLD 18.1.3 on `PATH`.
  - The runner image `ubuntu24/20261101.360` lists the same binutils
    and gcc 13.3.0. glibc 2.39-0ubuntu8.9 was published on 2026-09-10,
    before that image.
  - A build container pinned to a snapshot, for PAX CI's component
    builds, is later hardening and not part of this change.
- **R-tb03-17 is A: the plant is one hunk at the end of
  `tools/mktrash`, after the checks.** It ships `trash-rm`'s bytes as
  `trash-empty`.
  - It writes their digest into `sums.txt` as `trash-empty`'s.
    `tools/distribution-root` refuses a built input that its sums do not
    name (`built input mismatch`) before `tests/distribution` reads the
    image. A builder whose sums disagree with its bytes therefore stops
    there, and `image-trash-sums-trash-empty` cannot be reached from the
    builder.
  - Predicted: red by name at A2 (`trash-empty -i asks, and takes y`,
    since `trash-rm` reads `-i` as a pattern) and at
    `image-trash-pin-trash-empty`. A1 stays green, since both sides run
    the same planted binary.
