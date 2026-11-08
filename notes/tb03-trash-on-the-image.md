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

Sources for this section: sniff's unmerged hook (its `tools/mksniff`,
`user/sniff.pin` and the distribution and CI lines that go with them), PAX's
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
