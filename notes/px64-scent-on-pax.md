# px64 — scent on PAX: `/bin/grep` is scent

Crawl 54, Opus 5.5. Contract `sprints/pax/64-scent-on-pax` (ct02's
drafted px contract, adopted). Branch `px64` from trunk `e5dfad45`
(px63's merge). The prediction was committed first, `ed82cfe`
(`notes/px64/prediction.txt`). Every build, boot and test ran on kasumi's
CPUs 12-15 under `flock ~/lanes/scent-cores-12-15.lock`, in the lane's
own Ubuntu 24.04 container (`notes/px64/Containerfile`,
`localhost/px64-ubuntu`), the Linux sides in their own throwaway
containers; nothing on nomad-1 but git and gh.

## 1. Forbidden, and what was read

No Linux kernel source, no other kernel's, no glibc's, musl's or shell's
source, and no grep implementation's: not GNU grep's, gnulib's or
busybox's, and not scent's own `src/`. GNU grep 3.12 was built by scent's
`tools/fetch-oracle` from its signature-verified tarball and run as a
black box (nothing of its tree opened, no build log printed). What was
read is in `docs/SOURCES.md` (px64): scent's build and test tooling and
README at `b6f63a4` (the org's own), cpio(5)'s link entry, symlink(2)
and (7), execve(2)'s `#!` line, and PAX's own tree.

## 2. Inputs, re-derived

| input | found |
|---|---|
| pax trunk | `e5dfad45` (px63's note on its merge) |
| scent | trunk `b6f63a4892cca631475cd0b87a0b648ce9b532a9` (ct02, scent#6, M1); `wolf-toolchain.toml`: wolf 0.2.35 (`4cc4045b…`, `wolf 0.2.35 (wolfgang, pin cf0c13d)`), lupin 0.1.56, std `2386522e`, the std the wolf archive bundles |
| scent's wrappers | `wrappers/egrep`, `wrappers/fgrep`: 240 bytes each, 100755 blobs, `#!/bin/sh`, a warning on standard error, then `exec grep -E` / `-F` after putting `${0%/*}` first on PATH |
| the image writer | `tools/mkinitramfs` wrote files and directories only; kernel/tree's `adopt` left an archive's links out (the prediction's item 3, right) |
| `/bin/sh` | pelt in every image that carries the wrappers (the suite's, the dev ISO's); `#!` is px56's |
| the dev builder | px60's recipe as px62 made it lane-local (`notes/px62/dev-iso/`; px62's `pax-dev.iso` `393249a4…` is the last), px60's retained wolf, runtime and link stack on kasumi |
| pins at the head | wolf 0.2.34 (kernel), pelt `57ffef96`, boreutils `12de639`, lope `bc38867`, aspen `476edee`, yew `77c1083`, lupin 0.1.55: none moved (px65's) |

## 3. Prediction, scored

| predicted | measured | score |
|---|---|---|
| 14,846,984 bytes, ET_EXEC, no PT_INTERP, ct02's digest `bd860457…` twice; stripped 1,362,232 | `bd860457f2ff97591b7525da5f46c186feee4b8266d3f51b121866b001135d89`, 14,846,984 bytes, two builds in two checkouts at two paths; stripped 1,362,232 (`19140490…`); CI's runner built the same digest (the plant runs' logs) | right |
| no ABI gap: -ENOSYS only for 273 and 334, no `refused:` line | so, on every boot of the suite and the dev ISO; 27 calls by name on Linux (§6) | right |
| the abort rows the same on PAX but perhaps the core bit | the same: status 134, the runtime's panic text to the byte but its thread id, pelt's `pelt: ended by signal 6 (ABRT)` on both; no core wording anywhere. One thing not predicted: under `quiet` the kernel's own fault line shows on the console (§9) | right, with one surprise |
| the link needs the writer and the tree, about 40 lines | `tools/mkinitramfs` +32, kernel/tree +19 (8 of them code, the rest its comments) | right |
| about 90 s from the first prompt to the last typed grep command a session under TCG on kasumi; 180 s on CI; under 5 minutes for the boot | 56.2 s (root) and 57.1 s (pax) on kasumi (`notes/px64/kasumi-timing.out`); the boot with both sessions 118 s; on CI's runner the boot with both sessions 130 s (the plant run 40005207994: 18:45:05 to 18:47:15) | wrong: 1.6 times too slow for kasumi, about 2.8 times for CI |
| the dev ISO about 239 MB | 238,931,968 bytes | right |

## 4. What was built

**`user/scent.pin`** names `https://github.com/wolffe-lang/scent` at the
full merged sha. **`tools/mkscent`** (mkaspen's twin, with scent's own
mkscent's two builds): fetches exactly `SCENT_REV` (from
`PAX_SCENT_REPO` when set), reads scent's toolchain file, takes the
whole wolf archive by its digest read twice, refuses a `--version` that
is not the pin's and a bundled `std/STD-REV` that is not the pin's std,
keeps `libwolf_rt.a` beside `wolf`, builds by scent's static flags
(`wolf build --release --no-cache --deny-warnings src/scent.lu -o
target/static/scent` through a `cc -static`) twice, in two checkouts,
and refuses two digests; checks ET_EXEC and no PT_INTERP, copies the
wrappers byte for byte (git's blob hash) at 0755, writes `sums.txt`.

**The archive's links.** `tools/mkinitramfs` takes `/PATH->TARGET[:UID:GID]`
and writes cpio's link entry (mode 0120777, one link, the target as its
data); kernel/tree's `adopt` makes such an entry a link of the tree as
`symlink` makes one (R-px64-1). `/bin/grep -> scent` in every image that
carries scent.

**`tests/mpx5-scent`** (mpx5-aspen's shape): one kmain_console image
with pelt as `/bin/pelt` and `/bin/sh`, `/bin/scent`, the link, the
wrappers, boreutils' `cat env head id ls mkdir readlink tr`, `as`, `/tmp`,
`/home/pax`, an empty `/usr/lib` and the generated fixture
(`tests/mpx5-scent.d/fixture.py`) at `/usr/share/scent`;
`user/console/scent.keys` typed twice, as root and as `pax` (`as 1000
1000`). The keys define `s`, which runs a command with its streams to two
files and prints `status N`, the output (NUL as `@`), `[stderr]`, the
error, so a row's status and its two streams are held apart. A0 the
build (scent twice, static, the wrappers, `/bin/sh` in the root, the
archive's `bin/grep` read back by the suite's own reader as `120777 1 5
scent`); A1 each session byte-identical to the container's (the
runtime's thread id in a panic line typed `{pid}`, R-ct02-6); A2 49 rows
(`tests/mpx5-scent.d/rows.py`); A3 -ENOSYS 273 and 334 only, nothing
refused, init ended 0, halted. CI job `mpx5-scent`, mapped in
`tools/ci-tiers.map` (its own files; `@user`, since it is the suite whose
archive holds a link; `@asuser`), proven in `tests/ci-plan`.

## 5. Rulings asked (recommended, implemented, not decided)

- **R-px64-1: how an image carries `/bin/grep -> scent`.** Options: (a)
  cpio's own link entry, written by `tools/mkinitramfs`
  (`/PATH->TARGET`) and adopted by kernel/tree at boot as `symlink(2)`
  would make it; (b) a second copy of scent at `/bin/grep` (the contract
  forbids it: "rather than silently copying"); (c) the console's
  start-up making the link (`ln -s scent /bin/grep` in `/etc/pax-run` or
  `/etc/shrc`): every image's start-up file would have to do it, the
  link would carry the boot's time and the shell's owner, and the Linux
  side's root would need the same step. **Recommendation (a)**,
  implemented: the archive is where every other file of the image is
  said, the container's copy (`cp -R`) keeps the link as a link, and a
  link costs the tree one frame. Reversible: revert `0db14d8` and
  `8dac9af` (the plant branch `px64-plant-link` is exactly that revert,
  and turns the suite red).
- **R-px64-2: the dev ISO's scent is not stripped.** The dev recipe
  strips every program it carries (a tinkering image); contract item 3
  says `/bin/scent` is installed unmodified, so the dev ISO carries the
  14,846,984-byte binary (stripping would save 13.5 MB of 239 MB).
  **Recommendation: keep it unmodified**, implemented
  (`notes/px64/dev-iso/assemble.sh`); one line to strip it instead.

## 6. Witnesses and measurements

**The suite on kasumi** (native BIOS; `notes/px64/kasumi-suite.out`):
A0, A1 224 lines for each session (`ef86fa0a5dc6…`, root's and pax's the
same bytes: nothing the session prints depends on who typed it), A2 49
of 49 for both, A3 (serial 138,041 bytes). The gate runs all four legs
at the final head (the PR names its run).

**The rows' GNU half, held to GNU itself.** `notes/px64/gnu-rows.py`
runs the 25 rows whose lines are GNU 3.12's answers through bash with the
same `s` helper and the pinned GNU binary (`92b211f7…`, in scent's oracle
image) as `grep`: 25 of 25 (`notes/px64/kasumi-gnu-rows.out`). The other
24 rows are scent's by ruling (#115-#117), the upstream rows' shapes,
scent's own prose (help's usage line, `--version`, `-r`'s refusal), and
PAX's or pelt's (the link, the wrappers, PATH, the locale, pelt's words).

**The Linux-side prerequisite.** scent's whole byte suite
(`tools/pax-posture`: plain ubuntu:24.04, `LANG` unset, no locale data)
against the binary pax's `tools/mkscent` built: 6,078 agree, 0 differ,
12 not-yet, 117 reviewed (109 published + 8 upstream-blocked), exit 0
(`notes/px64/kasumi-posture.out`); ct02's counts exactly.

**The C locale in the guest.** `env` has no `LANG` and no `LC_*`
(`grep -c` 0, status 1); `/usr/lib/locale` does not exist; `^..$`
matches each two-byte line (2), and `-i` with é matches é alone (1): the
C locale's bytes and ASCII-only folding, as GNU in the C locale.

**The calls** (`notes/px64/census.sh`, `census.out`: strace 6.8 over
14 kinds of run): 27 by name: arch_prctl, brk, close, execve,
exit_group, fstat, futex, getpid, getrandom, gettid, lseek, mmap,
mprotect, openat, prlimit64, read, readlinkat, rseq, rt_sigaction,
rt_sigprocmask, sched_getaffinity, set_robust_list, set_tid_address,
sigaltstack, statx, tgkill, write; failures only `lseek` ESPIPE (a pipe
on standard input) and `openat` ENOENT (the missing file). PAX serves
every one but set_robust_list and rseq (-ENOSYS, which glibc's start-up
takes, as for every glibc program on PAX).

## 7. The dev ISO

`notes/px64/dev-iso/` (px62's recipe, lane-local: `verify.sh`,
`build.sh`, `assemble.sh`, `boot.sh`, driven by `notes/px64/dev-all.sh`
at one tree commit): the base userspace at the head's pins plus scent
(built twice by `tools/mkscent`), px60's wolf, worker, runtime and link
stack verified twice against `user/wolf.sums` and `user/wolf-link.sums`,
the musl lupin in px57's Rust image; booted with 2 GiB under TCG and
typed `dev.keys`: mpx5-scent's session as root, `su pax`, the session
as pax, then px62's dev session from its `cd`.

| | |
|---|---|
| tree | `b2937346` (`SOURCE_DATE_EPOCH` 1792781037, its commit time); the gate rebuilds it at the final head, named in the PR |
| kmain_console.elf | `c9b2bb74753e96e627e3a94c9af3bf18c4dc0270a195a5b99319f7bc70f8baa2` |
| `pax-dev.iso` | `c89aafa70f30bb246d3a2db9f51638bc0c53df563f5258b03bb1ff4c201a3977`, 238,931,968 bytes, read twice (`kasumi:~/lanes/px64/dev/out/`) |
| `pax-dev-smoke.iso` | `dea0b574b1e2826ad5f40560c09deb0b8ba411a517a6c0e6955eb1c7f6b09d35` |
| the archive | `9e66243d…`, 231,958,532 bytes: `link 120777 5 bin/grep -> scent`, `bin/scent` 14,846,984 (unmodified), `bin/egrep`, `bin/fgrep` 240 (`kasumi-dev.initramfs.out`) |
| the boot | 153 s; HALTED (`kasumi-dev.verdict`); px62's `check-dev-session.py` PASS; `check-scent-session.py` PASS, 49 rows as root and as pax (`kasumi-dev.out`, the serial log `kasumi-dev.serial.log`) |

The scent check's first run failed on a correct session: under `quiet`
the kernel still prints a fault, and its `user: ff-arg pid 136 killed:
SIGABRT after 2 runs` line stood between the command and pelt's line;
the checker leaves the kernel's lines out now, as the suite does
(`618b7b9`), and was rerun on the same serial log. The ISO was not
copied to nomad-1 (the contract names no copy; the orchestrator's to
place).

## 8. CI

Plants, each a branch never merged, dispatched `-f tier=pr -f
suites=mpx5-scent` (extracts in `notes/px64/`):

- `px64-plant-wrapper` (`6600c84`, the image without `/bin/egrep`): run
  40005203655, job 120591511678: A0 green (the root holds the wrapper),
  A1 red for both sessions (`ls: cannot access '/bin/egrep': No such
  file or directory`, the container's lines missing), A2 red (the
  wrappers' rows), A3 green (`ci-40005203655-plant-wrapper.log`).
- `px64-plant-link` (`f0ec682`, the tree adopts no archive link: a revert
  of `8dac9af`): run 40005207994, job 120591642506: A0 green (the archive
  holds the link; the kernel ignores it), A1 red (`ls: cannot access
  '/bin/grep'`), A2 red (every row through `grep`), A3 green
  (`ci-40005207994-plant-link.log`).

Restored: the control, `px64` at `c0e89478` (the plants' base) with the
same dispatch, run 40007204477, job 120598360201: green, A0 to A3, both
sessions `ef86fa0a5dc6…` as on kasumi (`ci-40007204477-control.log`).
The final head's `tier pr` is named in the PR.

## 9. What a PAX user sees (the gaps, by whose)

- **scent's, by design:** `--help` and `--version` are scent's prose
  (`Usage: scent [OPTION]...`, `scent 0.1.0`); `-r` and colour are M2,
  refused by name (`scent: not yet implemented: r (M2)`); C-locale
  semantics only (M3); rulings #115-#117's answers.
- **upstream (wolf-lang#899, #904): the argv0 seam.** A diagnostic says
  `grep:` whatever name ran it: `/bin/grep --bad` says `grep:
  unrecognized option '--bad'` where GNU says `/bin/grep: …`; another
  link name would still say `grep`.
- **upstream (wolf-lang#406, #904): an argument that is not UTF-8 aborts.**
  On PAX exactly as on Linux: status 134, the runtime's panic text,
  pelt's `pelt: ended by signal 6 (ABRT)`; under `quiet` the kernel adds
  its fault line, `user: ff-arg pid N killed: SIGABRT after K runs`, on
  the console. A PAX user can reach it only through a `#!` line or a
  program that is not a wolf one: pelt cannot pass the byte (next).
- **pelt's:** `$'\377'` is `?` (0x3f), not byte 0xff: a wolf string holds
  only UTF-8, so pelt cannot pass a byte argument that is not (the
  session's row; to list for pelt).
- **PAX's:** none. No call missing, no refusal, nothing differs from the
  container but the thread id the runtime prints.

## 10. Limits named

- An archive's hard links stay separate files; devices and FIFOs are
  still left out.
- A link's target is 1 to 4095 bytes; another length is left out
  without a word (the writer refuses one).
- The suite's image carries unmodified boreutils (14 MB each): the
  archive is 162,653,968 bytes and the suite boots with 1 GiB.

## 11. Issues and what to prune

To close: none. To file (listed, not filed):

- pelt: `$'\ooo'` and `$'\xHH'` of a byte that is not UTF-8 become `?`;
  POSIX.1-2024's dollar-single-quote yields the byte (§9).
- scent: the help's usage line says `scent` where the error's usage
  says `grep`, and `-r`'s refusal is prefixed `scent:` where every other
  diagnostic says `grep:` (a question for scent: by design or not).
- wolf-lang#406, #899 and #904 are the upstream rows' own (not
  duplicated).

Prune (the lane's own) once the PR merges: kasumi `~/lanes/px64/`
(`build/`, `dev/`, `w/`, `exp/`, `scent-out/`, `scent/` with its
`.oracle/`, `cache/`, `tmp/`, the pax clone) and the images
`localhost/px64-ubuntu`, `localhost/px64-scent-oracle`; the plant
branches `px64-plant-wrapper` and `px64-plant-link` stay on origin as
evidence (never merged).
