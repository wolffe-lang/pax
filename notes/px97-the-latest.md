# px97 — the latest pins: every component at its trunk head, gated

Contract: px97's (2026-11-04), under the lane rules of 2026-10-31 and their additions. Every component pin moves to
its repository's trunk head as read on 2026-11-04, one commit per component, with the component's rows run red first
where a row can be red. A head that breaks on PAX stays at its old pin and its break is written up for its own
repository.

Footprint: cross-cutting (user pins; `tools/census/inside/pins.sh`; a row's expectation). Tests:
`tests/mpx5-scent.d/rows.py`. Docs: README (README-only commits), `docs/SOURCES.md`. The rest is notes.

The other half of the contract, `tools/mkdistribution --latest`, is a separate branch. It rides on the upgrade path
of a branch not yet merged, and is not part of this change.

## 1. Forbidden, and what was read

No kernel's, firmware's, bootloader's or driver's source was read. The org's own trees were read where a pin needs
them, as `docs/SOURCES.md` lists: each `wolf-toolchain.toml` at the old pin and at the head, the log between them,
the `src/` paths the log names, and the release notes and mirror pin of the new lupin. Every release archive and
every source archive was read by digest, twice. The published lupin binary was checked by its ELF header, never run
outside a container.

The machines, by the names this note and `notes/px97/` give them:

| name here | the machine |
|---|---|
| the lane host | an x86-64 Linux workstation with KVM: a heavy slot of eight CPUs behind two lock names, and a light slot beside it. Every build, boot and record |
| the build Mac | git, and the Python-only rows (census, `tests/ci-plan`, `tests/pax-release`), behind its build lock |

Builds and boots ran on the lane host under both of its locks, inside the heavy slot's CPUs, in the baseline Ubuntu
24.04 container (`localhost/px75-ubuntu:2`) with KVM. Each step took the locks for itself, and the Linux side of each
row ran in throwaway containers through the lane's own podman. Two lines of `notes/px97/prediction.txt` named the lane
host by its own name when committed; they were reworded to these names before the merge, and nothing else in it. No package was installed, and no disk but a QEMU image
the rows made was written. No label, merge, tag, release or issue.

## 2. Inputs, verified

Base: trunk `a9f5b6f1`. The pins were first moved on `9c88ec8a`, where the probe ran, and rebased onto trunk before
the final gauntlet; the one conflict on the way was `docs/SOURCES.md`, where px89's section and this one both end
the file (both kept, px89's first).

| component | pin before | pin now | commits | toolchain at the head | read |
|---|---|---|---:|---|---|
| boreutils | `0f7a57b6` | `ff5396ad` | 7 | wolf 0.2.36 / lupin 0.1.58 / std `78b9d3cb` | source archive `30d5ccc0…`, twice |
| lope | `e6f623c7` | `d65bb03c` | 7 | the same | |
| lobo | `49ed870e` | `64e7339d` | 25 | the same | wolf 0.2.36's archive `d383c74c…`, from the release API twice |
| scent | `81d761d6` | `eb888dfc` | 35 | the same | source archive `c6c0daeb…`, twice |
| aspen | `3692cf5d` | `096245c8` | 37 | the same | |
| den | `13bc2caa` | `584b18a3` | 139 | the same (unchanged) | |
| yew | `0ccb2c67` | `1218169e` | 213 | the same | source archive `fdf3cb07…`, twice |
| lupin | v0.1.58 `6240efe5` | v0.1.59 `668fb752` | 38 | Rust 1.97.1 | musl archive `29ee2c30…` (the API twice, two downloads); binary `9de724f5…` (two extractions): ET_EXEC, no PT_INTERP, no PT_DYNAMIC; `lupin 0.1.59 (wolf-interp, reference interpreter at pin b16353e)` |
| wolf-std | `78b9d3cb` | `3111d39f` | 78 | wolf 0.2.36 / lupin 0.1.58 | |

Every head's toolchain is wolf 0.2.36 (pin `5adf3d9`). den was there already; every other component moves from 0.2.35.
wolf-std moves after lupin, never before: its `std.env` wraps `env_arg0` and `env_args_bytes`, which lupin resolves
from 0.1.59.

Left where they were:
- **pelt** stays `4683b3f5` (head `301e25e0` at the probe, `b514e14a` since): R-px97-7.
- **clef** stays `b71b43f4` (head `900bdf0a`): R-px97-6.
- **wolf**: `user/wolf.pin` has been v0.2.36 since px92. `kernel/wolf.pin`, the kernel's own compiler, stays 0.2.35:
  R-px97-1.
- **The games' catalog** keeps its pins: R-px97-5.

Moved since the read (2026-11-04), for the next pass:
- **den**'s trunk is `ef0bb0ca` (57 commits). It now draws history decorations at a terminal, which
  `tests/mpx5-den.d/rows.py`'s terminal row holds as `den: not yet implemented: history decorations`; that row moves
  first, red at `584b18a3`, as scent's A2 did.
- **lobo**'s trunk is `6b8b9ee7` (9 commits: tests and notes, nothing under `src/`).
- **wolf** 0.2.37 was released on 2026-11-05. Every head above still pins 0.2.36.

## 3. Prediction, scored

Committed first (`notes/px97/prediction.txt`).

- **Census red first:** held. C5 for boreutils, scent and yew, and C4 for pelt, were each red by name at the commit
  that moved the snapshot and green at the pin's own commit. The pelt pair left with pelt.
- **Green at the new pins:** held for boreutils, lope, lobo (its build), aspen, den, yew (and the screen row), lupin
  with wolf-std, and mpx4-unix. yew's stack did not outgrow the 1 MiB policy.
- **scent:** predicted green; A2 was red. The row held the runtime's panic for an argument that is not UTF-8, the
  answer of wolf 0.2.35. scent's head is built by 0.2.36, whose runtime traps it by name (`wolf-trap:
  argument-utf8`, `argument 1 is not UTF-8; read it with env_args_bytes()`, status 134). PAX and Linux print the same
  bytes (A1: 221 lines identical). That is a fix: the row was updated first, red at the old pin, then the pin moved.
- **clef:** predicted green; Q0 was red. `tools/mkclef` holds clef's toolchain to `kernel/wolf.pin`'s release, which
  is 0.2.35, and clef's head pins 0.2.36. PAX's own pairing rule refused it, so clef was not broken (R-px97-6).
- **pelt:** predicted green; red three ways (R-px97-7).
- **The images:** at the probe's head, every input built (`inputs`, 7657 s), `tools/mkdistribution` assembled both
  variants (4605 s), and `tests/distribution-boot` booted both ISOs on BIOS and UEFI (825 s), all green. That was
  with pelt and clef at their heads; the final gauntlet builds the images again at the pins here.
- **The probe's record:** 45 steps, worst 1. The red steps are the ones named above: scent's A2, clef's Q0, pelt's
  replay and friendly rows, and mpx3-shell (pelt's prompt).
- **Wall time:** far over the estimate. Under one slot running hot, the builds alone took 35 to 72 minutes a row
  (boreutils 35, yew 38, pelt 64, lobo's two builds 72).
- **mpx6-part, found by CI's labelled full tier** (run 42105296028, at the first head `4d07bf3b`): not predicted.
  Its console disks hold the kernel and the whole initramfs on a 64 MiB ESP, and at trunk that ESP was already 98%
  full (126,658 of 129,022 clusters on the native tier). boreutils' `cat`, `ls` and `stat` at `ff5396ad`, built by
  wolf 0.2.36, are about 15 MB each unstripped (15,191,560, 15,339,584 and 15,201,912 bytes), and copying the
  initramfs failed: `mkdisk: mcopy ::/boot/initramfs.cpio: exit 1: Disk full`. With no boot disk, P0, P6, P7, P8
  and P10 were red; the GPT fixtures' rows (P1 to P5) held. P0 named the transcript's last line, a progress line
  mkdisk had buffered, not the refusal. Two commits: P0 now names mkdisk's own refusal (`7d44562d`, red by name at
  the new pin), then the initramfs carries the wolf programs stripped, as `tools/distribution-root` ships them
  (`d6915414`). That commit's comments named `tools/distribution-root`, and `tests/ci-plan` reads a path a suite
  names as an input: at `353fee7a` CI's plan job was red on six P2 rows (den's, lope's, the games table's and the
  compiler pin's paths reached mpx6-part). mpx6-part reads none of those, so the comments now name no path, and the
  planner's table is unchanged. The follow-on is pax#303: an ESP sized with stated headroom, and mkdisk flushing its
  progress so a failed run's last line names the failure. The local gauntlet had left mpx6-part to the labelled full tier with the other suites the
  boreutils pin reaches (R-px97-4), so neither the probe nor the first final run had it; the final gauntlet now
  runs every mpx6-part row on the PR leg, and the other suites stay the full tier's (all green in that run).

## 4. Evidence index

The commits, each a component or a row:

**The final gauntlet and the plant:** their records and every `END` line are in the pull request's body.
- The gauntlet runs at the final head, in stop mode: ci-plan, census, red-first (the census pairs), the A2 row at its
  red commit, every mpx6-part row, then each moved component's rows on native BIOS under KVM, then the inputs (the
  dev compiler among them, `tools/mkwolf`'s bytes held to `user/wolf.sums`), `tools/mkdistribution` and
  `tests/distribution-boot`.
- The plant, `px97-plant-den`, is one hunk of `user/den.pin`: a revision that does not exist, red by name as
  `FAIL D0 (build)`.

**Rulings.**
- **R-px97-1:** `kernel/wolf.pin` stays 0.2.35 here. It is the kernel's compiler, a change that runs every suite on
  every leg and moves the kernel-as seam pin, so it gets its own pass.
- **R-px97-2:** red first, for a pin. The census snapshots are red first by name. Every mpx5 row holds PAX to the
  same binary on Linux, so it cannot be red before the pin moves, and it is run green after. A row whose expectation
  the head changes is updated first, red at the old pin (scent's A2).
- **R-px97-3:** pelt's new friendly default. The choice was to be (a), adapt the rows, if they held; or (b), start
  PAX's test shells with `+o friendly`, if they did not, keeping the live console's behaviour. They did not hold.
  (b) cannot keep the console either: a shell invoked as `sh` now refuses friendly mode outright. So neither applies,
  and pelt stays (R-px97-7).
- **R-px97-4:** the rows a lane container cannot run here go to the labelled full tier: mpx4-lobo's sessions (its
  build ran), mpx4-session, kernel-as, and the other suites the boreutils pin reaches.
- **R-px97-5:** the games' catalog keeps its pins; a later pass.
- **R-px97-6:** clef stays `b71b43f4` and moves when `kernel/wolf.pin` moves.
- **R-px97-7:** pelt stays `4683b3f5`. Its head changes PAX's consoles and breaks rows:
  1. A shell invoked as `sh` can no longer turn friendly mode on, and PAX's console is `/bin/sh`. mpx5-pelt's
     friendly rows fail: no shadow, no abbreviation, no history events, no identity.
  2. Every interactive `/bin/pelt` now starts friendly: the stick's live console, the installed console, and the
     rows' images. mpx3-shell's prompts never came (`?@? ~# ` where the rows wait for `$ `).
  3. The Linux side of mpx5-pelt's replay hung at `wait` after eight `true &`; the same binary on PAX did not hang.
  All three are written up for pelt with their witnesses. The prompt's `?@?` is pelt's own fallback (its Linux side
  shows the same), not something PAX lacks.

## 5. Done-when

- [x] The prediction, committed first.
- [x] One commit per component, at its trunk head, with every digest read twice.
- [x] Red first: the census pairs; scent's A2 at the old pin.
- [x] A head that breaks on PAX stays where it was (pelt, clef), its break written up.
- [x] README and `docs/SOURCES.md` (README-only commits).
- [ ] The final gauntlet, green at the head (its record in the pull request's body).
- [ ] The plant, red by name (its record in the pull request's body).
- [ ] The labelled full tier: the coordinator's.
