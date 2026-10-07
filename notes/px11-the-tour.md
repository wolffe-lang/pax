# px11 — the tour

Contract: `sprints/pax/11-the-tour/px11-the-tour.md` in wolffe-lang/wolf
(planning trunk at the lane's start). Branch `px11` off pax `7c42f5b`.
One deliverable: nothing in pax's source, names, menus, tests, tools or
docs says or implies that anything is filmed or made for viewers. px08's
boot reel becomes a tour of the kernel, with identical behaviour.

## 1. Forbidden, absolutely

- No Linux, glibc, musl or other kernel's or libc's source is read.
  This lane reads pax's own tree and nothing else.
- Behaviour identical: every stage, its serial output, its timing and
  both endings stay as they are, except on-screen words that imply
  filming (listed in §3, line by line).
- `~/scratch/wolf/pax-demo/` keeps its name; it is the one place the
  filming words stay.
- px10's files are not touched beyond the renames (px10 rebases after).
- No `rm` outside `~/lanes/px11/`, this lane's worktrees and the renamed
  files; no `git add -A`; nothing under `~/.claude`; no merge; no build
  on nomad-1 (kasumi builds; nomad-1 runs QEMU for the rehearsal only).
- No issue closed.

## 2. Inputs, verified

- pax `origin/trunk` = `7c42f5b` (px08 merged), as the contract says.
- px10 (`origin/px10`) carries one commit, its note; it plans edits to
  `.github/workflows/ci.yml`, `docs/SOURCES.md`, `kernel/README.md`,
  `README.md` (appended sections) and uses `tools/mkimage` as written.
  This lane edits the first three where they name the reel; px10 rebases.
- `git grep -niE "reel|film|viewer|camera|video|finale|scene|shot|audience|maintainer"`
  at `7c42f5b`: **341 lines in 30 files** (`~/lanes/px11/grep-before.txt`
  on nomad-1, sha256 `8ebfcf53…`). By group:
  - px08's code: `kernel/reel/reel.lu` 19, `kernel/kmain_reel.lu` 24,
    `kernel/kmain_reel_text.lu` 20, `boot/limine-reel.conf` 6,
    `tools/reel` 18, `tests/reel` 38, `tools/mkimage` 1, the CI job 16.
  - px08's filming material: `demo/reel/{README.md,SHOTLIST.md,preflight.sh}` 61.
  - docs: `kernel/README.md` 5, `docs/SOURCES.md` 7, `docs/CENSUS.md` 3.
  - px04's census, naming lobo's demo site (lobo's `demo/reel` tree):
    `tools/census/inside/{pins,probe,stage}.sh` 7, `workloads/lobo.sh` 5.
  - `CLAUDE.md` 1: "private until the maintainer says otherwise" (a
    publication rule, not filming; and stale: pax is public since
    2026-10-06).
  - lane history: `notes/px08-the-reel.md` 62, `notes/px08/*` 47,
    `notes/px04-the-census.md` 1.
- Drift: none in the contract's inputs. Found: the census reads lobo's
  `demo/reel` directory by path at lobo `f79418d1…`; that path is lobo's
  and stays (§3).
- How the history notes are treated: `notes/px08-the-reel.md` and
  `notes/px08/*` record px08's lane, and they do mention filming (the
  title, "the viewer", the SHOTLIST's scenes, `rehearsal-scene*.times`).
  **Kept as history, unedited**: the serial logs and timings there are
  measured artifacts cited by sha256 in the note and in pax#11's body;
  rewording them would make those citations false. `notes/px04` line 64
  is history too and stays.

## 3. Prediction (committed before the first change)

**Renames** (`git mv`; contents edited after):

| before | after |
|---|---|
| `kernel/reel/reel.lu` (module `reel`) | `kernel/tour/tour.lu` (module `tour`) |
| `kernel/kmain_reel.lu` | `kernel/kmain_tour.lu` |
| `kernel/kmain_reel_text.lu` | `kernel/kmain_tour_text.lu` |
| `export fn pax_reel_worker` (wolf; no assembly names it) | `pax_tour_worker` |
| `boot/limine-reel.conf` | `boot/limine-tour.conf` |
| `tools/reel` | `tools/tour` |
| `tests/reel` | `tests/tour` |
| CI job `reel`, artifact `pax-reel-linux`, `build/reel*` | `tour`, `pax-tour-linux`, `build/tour*` |
| ISOs `pax-reel.iso`, `pax-reel-b.iso` | `pax-tour.iso`, `pax-tour-b.iso` |
| `demo/reel/` | removed (it lives in the folder only) |
| the census's staging dir `/stage/reel`, `/work/reel` | `/stage/lobo-site`, `/work/lobo-site` |

**On-screen lines that change** (every other line byte-identical):

| where | before | after |
|---|---|---|
| Limine menu title | `PAX, the boot reel` | `PAX, a tour of the kernel` |
| menu entry 1 | `PAX reel, finale a: a thread overruns its stack` | `PAX tour, ending a: a thread overruns its stack` |
| menu entry 2 | `PAX reel, finale b: the kernel writes to its own text` | `PAX tour, ending b: the kernel writes to its own text` |
| serial, both ISOs | `finale in 3... 2... 1...` | `ending in 3... 2... 1...` |
| serial, ending a | `finale: a thread recurses until it runs off its stack` | `ending: a thread recurses until it runs off its stack` |
| serial, ending b | `finale: the kernel writes to its own text, which paging mapped r-x` | `ending: the kernel writes to its own text, which paging mapped r-x` |
| failure paths only (never printed by a passing run) | `reel: no frame for the round trip`, `reel: no frame for the finale's page` | `tour: no frame for the round trip`, `tour: no frame for the ending's page` |

Every replacement is the same length as the word it replaces (`finale`
and `ending`, `reel` and `tour`, `pax_reel_worker` and
`pax_tour_worker`, `kmain_reel` and `kmain_tour`), so:

- **ISO bytes change beyond the menu text**: yes. The kernels' rodata
  (the three lines above), their symbol and string tables and the
  menu file differ. But no section changes size, so **every address,
  count and `rip` the kernels print is unchanged**: the BIOS serial log
  of each ISO, before and after, differs in exactly the lines above
  (two per ISO: the countdown and the ending's first line), and
  `diff` shows nothing else. Falsified by any other differing line (an
  address, `image: … KiB`, a frame count, ending b's `rip …bd53`).
- The ISOs' size stays 4,610,048 bytes; their shas change.
- Timings: the run is paced by the virtual PIT, so the headings land at
  the same stamps as px08's (5.1/8.1/11.1/14.1/19.1 s, PANIC 28.5 s
  under nomad-1 TCG BIOS) within 0.1 s.
- **tests/tour on kasumi** (QEMU 11.1.1 TCG, `PAX_REQUIRE_UEFI=1`, both
  tiers, BIOS and UEFI): **44 PASS, 0 FAIL, 0 SKIP**, as tests/reel's
  44 at px08's head.
- Final grep: zero hits outside `notes/` lane history, except two,
  argued: lobo's directory name `demo/reel` in
  `tools/census/inside/stage.sh` (a path in another repository at a
  pinned commit; renaming it is lobo's), and `CLAUDE.md`'s "maintainer"
  (not a filming word; the line's publication rule is the
  orchestrator's to correct).

## 3, against measurement

| predicted (`e1f19c7`) | measured | verdict |
|---|---|---|
| module `kernel/tour` (`use tour`) | built that way first (`d674f8c`, `da798c2`): ending a's serial log differed only in the predicted words, but **ending b's moved** (image 104 -> 108 KiB, frame counts -2, text/rodata/data bounds +4 KiB, gdt/idt +4 KiB, `rip …bd53` -> `…90da`). Cause: `tools/build-kernel` links `NAME.<module>.o` in glob order; `tour.o` links after `timer.o` where `reel.o` linked between `panic.o` and `root.o`, and in `kmain_tour_text` the new order adds 8 bytes of padding (`.text` 0x11000 -> 0x11008), one page more. **Fixed by naming the module `pax_tour`** (`eb86e33`), which sorts where `reel` did: `kernel/pax_tour/pax_tour.lu`, `use pax_tour`. Drift from the contract's `kernel/reel` -> `kernel/tour`, taken because "behaviour identical" is the non-negotiable rule | **wrong** (the name), corrected |
| every address, count and `rip` unchanged; BIOS serial logs differ only in the countdown and the ending's first line (plus the menu) | at `bbaa22b`, kasumi TCG, BIOS and UEFI, both ISOs: exactly those lines (`notes/px11/serial-before-after.diff`); `rip 0xffffffff8000bd53`, `image … 104 KiB`, `65096 usable` as before | right (after the fix) |
| ISO bytes change beyond the menu text | yes: the kernels' rodata, symbol and debug sections; the loaded segments' sizes are unchanged | right |
| ISO size 4,610,048 bytes, shas change | 4,610,048; native `a1a888ff…`, `cc9ed5b0…`; release `fe60d16c…`, `2f89d1b3…` | right |
| headings at 5.1/8.1/11.1/14.1/19.1 s, PANIC 28.5 s, within 0.1 s | kasumi BIOS a: 5.13/8.13/11.14/14.14/19.15, PANIC 28.47 (before: 5.14/8.14/11.16/14.15/19.15, 28.48); nomad-1 rehearsal: 5.14/8.14/11.15/14.15/19.15, 28.47 | right |
| tests/tour 44 PASS, 0 FAIL, 0 SKIP on kasumi | 44 / 0 / 0 at `c4347f3` (`~/lanes/px11/tour1.out` on kasumi, `97ae071b…`) and at `bbaa22b` (`tour2.out`, `3939f10e…`) | right |
| final grep: hits only in lane history, plus lobo's `demo/reel` path and `CLAUDE.md`'s "maintainer" | as predicted (§4) | right |

One input found while working: a kernel's native-tier ELF records the
source directory in its debug sections (`/home/…/lanes/px08/wt/kernel`),
so px08's folder ISO `25232dbf…` is reproducible only from that
directory; the loaded segments do not depend on it (the release tier
does not record it: `af1d7b26…` rebuilt here byte for byte).

## The on-screen lines that changed

Every other line, of both ISOs, under BIOS and UEFI, is byte-identical
(`notes/px11/serial-before-after.diff`):

1. Limine's menu title: `PAX, the boot reel` -> `PAX, a tour of the kernel`
2. entry 1: `PAX reel, finale a: a thread overruns its stack` -> `PAX tour, ending a: a thread overruns its stack`
3. entry 2: `PAX reel, finale b: the kernel writes to its own text` -> `PAX tour, ending b: the kernel writes to its own text`
4. `finale in 3... 2... 1...` -> `ending in 3... 2... 1...` (both ISOs)
5. ending a: `finale: a thread recurses until it runs off its stack` -> `ending: …`
6. ending b: `finale: the kernel writes to its own text, which paging mapped r-x` -> `ending: …`
7. never printed by a passing run: the two `panic.fail` texts `reel: …` -> `tour: …` (`finale's page` -> `ending's page`)

## 4. Evidence index

- **Grep before** (`7c42f5b`): 341 lines, 30 files (`~/lanes/px11/grep-before.txt` on nomad-1,
  `8ebfcf53…`). **After**: in the PR body (the grep of the head that
  carries this note); outside `notes/`, two lines: `CLAUDE.md:33`
  ("the maintainer says otherwise", the publication rule) and
  `tools/census/inside/stage.sh:40` (`demo/reel`, lobo's directory at
  lobo `f79418d1…`; staged here as `lobo-site`).
- **Serial logs** (kasumi, QEMU 11.1.1 TCG, BIOS, `tools/tour time` /
  px08's `tools/reel time`): before `notes/px11/kasumi-tcg-bios-before-pax-reel.serial.log`
  `805af30f…` (the same sha as px08's committed log of its head) and
  `…-before-pax-reel-b.serial.log` `764dbdfb…`; after
  `notes/px11/kasumi-tcg-bios-pax-tour.serial.log` `8183fa71…`,
  `…-pax-tour-b.serial.log` `5168d0c4…`; the diff
  `notes/px11/serial-before-after.diff`; timings beside each (`*.times`).
  UEFI before/after (`~/lanes/px11/boot-before`, `boot-head` on kasumi): the same lines differ, nothing else.
- **ISO shas** (kasumi, `tests/tour`'s R0 build in `~/lanes/px11/head`, no `.git`):
  native `pax-tour.iso` `a1a888ff…`, `pax-tour-b.iso` `cc9ed5b0…` (the
  same at `c4347f3` and `bbaa22b`); release `fe60d16c…`, `2f89d1b3…`.
  Before (`7c42f5b` in `~/lanes/px11/before`): native `0697824d…`,
  `a4fcd9d7…`; release `af1d7b26…`, `1b5427ce…` (px08's release shas).
- **tests/tour, kasumi**, `PAX_REQUIRE_UEFI=1`, both tiers and
  firmwares: 44 PASS, 0 FAIL, 0 SKIP (`~/lanes/px11/tour2.out`
  `3939f10e…`, at `bbaa22b`).
- **Planted red**: `6874d8d` puts `finale in 3...` back. CI run
  37703732162, job `tour` 113073058032: R1 FAIL on all eight legs
  (`line 40 not found after log line 82: ending in 3\.\.\. 2\.\.\. 1\.\.\.`),
  R0 and R2-R7 PASS; every other job green. Reverted in `bbaa22b`
  (CI run 37704386581 green).
- **tests/census** (C1-C3) PASS on nomad-1 after the census edits; the
  census itself was not re-run (a container run on kasumi); its next run
  must re-stage (`tools/census/census stage`), since the staging
  directory is now `lobo-site`.
- **Rehearsal** (nomad-1, the folder's SHOTLIST typed into fish by
  `~/lanes/px11/rehearse.py`, a copy of px08's): preflight GO, its boot
  29.40 s; boot a: menu 0.21 s, headings 5.14, 8.14, 11.15, 14.15,
  19.15 s, `join` 21.48 s, PANIC 28.47 s; boot b: Enter at 2.75 s,
  PANIC 26.17 s (23.4 s after Enter), `rip …bd53`
  (`notes/px11/nomad1-rehearsal-boot-{a,b}.times`).

## 5. Done-when

See the PR body (pax#14). Closes nothing.
