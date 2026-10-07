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
