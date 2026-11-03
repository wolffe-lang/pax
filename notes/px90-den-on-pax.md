# px90 — den on PAX (`/bin/den`, and `git` beside it)

den, the org's version control in wolf, is on PAX's images and on the disk `pax-install` writes: `/bin/den`, the
binary den's own builder made, unmodified, and `/bin/git` a symbolic link to it. This is den's milestone M6 pulled
ahead of the wire: every local verb at den's pin, typed at PAX's console in repositories on an ext2 `/home`, held
byte for byte to the same den on Linux, as root and as `pax`, and a repository committed on an installed disk
before a reboot reads back clean after it.

## 1. Forbidden, and what was read

- **Clean room.** No kernel, firmware or driver source (PAX's rule), and no Git source (den's). Git ran only as a
  program: the container's and the runner's `git` read the repositories PAX wrote (`fsck --full`, `rev-list`).
  den runs on PAX only as itself; there is no Git on PAX.
- **den unchanged.** den is built from its pin by its own `tools/mkden`, installed byte for byte (never stripped),
  and nothing in this lane hides a PAX defect inside den. Two of den's own limits surfaced; both are reported
  (section 4, the gaps), neither is worked around in den.
- **Read** (`docs/SOURCES.md`, px90): den's README, `docs/MAP.md`, `wolf-toolchain.toml`, `tools/mkden`,
  `tools/build`, `tools/lib-toolchain.sh`, `tools/fetch-toolchain` and `tools/environment.py` at `13bc2caa`, and a
  census of the OS calls den's `src/` makes (no `std.process`: no editor, pager or hook is ever run); PAX's README,
  `user/scent.pin`, `tools/mkscent`, `tools/mklope`, `tests/mpx5-scent`, `tools/mkdev`, `tools/mkdistribution`,
  `tools/distribution-root`, `tests/distribution*`, `user/install/` (the snapshot that copies the live root,
  links included) and `tests/mpx6-install.d/` (the rig `den.py` joins); RFC 8536 for the zone file, as px26's
  `tools/mkzone`.
- **Hosts.** hasu block A (CPUs 0-5) and, for the program inputs, block B (6-11), each run under both lock names
  (outer then inner, one `flock -w 21600` each), taskset inside the baseline Ubuntu 24.04 container
  (`localhost/px75-ubuntu:2`: `ubuntu:24.04` plus clang, lld 18, QEMU 8.2.2, OVMF, xorriso, e2fsprogs; glibc
  2.39-0ubuntu8.9), `--memory 12g`, stdin closed, KVM. Never kasumi; never the Mac for a build or a boot. TMPDIR
  under `~/lanes/px90/` on hasu. No package installed, no maintainer data touched, no `rm` outside the lane.
- **Not done:** no label, merge, tag, release, deploy, package or issue; no metal session; no attribution trailer.
  The plant branch is pushed without a PR (the local merge gate).

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `5da8daaf` (px87's #272 and px88's #275 still open: nothing to rebase onto) | `git log` |
| den | `13bc2caa46efa152ea7709da0b84180a9f350d85` (den trunk, r41p's pin to wolf 0.2.36), `user/den.pin` | `tools/mkden` refuses any other HEAD |
| den's wolf | 0.2.36, `wolf 0.2.36 (wolfgang, pin 5adf3d9)`, archive `d383c74c8cd123b9d9dfaa268271d4f004294f85c2b230237d0ef07027d9500d`, its bundled std `78b9d3cb` (the pin's) | the archive read twice, the version line and STD-REV checked |
| den's lupin | 0.1.58, `lupin 0.1.58 (wolf-interp, reference interpreter at pin a5378e3)`, archive `34f52792bb59bc7565e0edc1235cd47d9a6ad13d5e6528993627f2e699b62193` | read twice (den's `tools/lib-toolchain.sh` wants it beside wolf; the static build never runs it) |
| den, static | `d4d3d6b85009be7dbbb7a759307261d18b3703e5c758d085a2e4d752d7858439`, 16,698,144 bytes; stripped `a25593f2…`, 2,590,744 bytes (not installed) | four builds (two checkouts, den's `tools/mkden` twice in each), one digest; ET_EXEC, no PT_INTERP; `den 0.0.0 (built with wolf 0.2.36)` |
| the base dev payload | `098b918e…` (px82's, `tools/distribution-root`'s `BASE_SHA`), copied from px82's lane | sha256 |
| the other programs | user/*.pin at trunk, rebuilt at the head by their own builders (`tools/mk*`) | each builder's own checks |

## 3. Prediction, scored

The prediction is `notes/px90/prediction.txt`, committed first (`5f6c8e15`).

| predicted | measured | verdict |
|---|---|---|
| den static 16.3 MB (15.5-17.5), stripped 2-4 MB | 16,698,144 bytes; stripped 2,590,744 | held (+2.4%) |
| two checkouts through den's own `tools/mkden`, one digest | four builds, `d4d3d6b8…` each, at 8181588b and again in every later build | held |
| no fork, exec, pipe or wait from den | none needed and none seen: den's source uses no `std.process`, no editor or pager ran (`GIT_EDITOR=yew` is refused by name, `not yet implemented: commit editor yew`), and every verb's status matched Linux's | held |
| -ENOSYS only 273 and 334, no `refused:` | exactly that, from den and from every program of the session, on both firmwares | held |
| every file call served on ext2 (O_EXCL locks, link, rename, fsync of files and directories, getdents64) | 198 den runs a boot exit 0, 4 exit 1 and 10 exit 2, each the same status on Linux; the disk e2fsck-clean after the boot; git reads both repositories whole | held |
| `config` read-only, `gc` refused, every other verb inside den's measured surface | `den config user.name Other`: `den: not yet implemented: config (only --get <key> is supported) (M2, vc03)`, status 2; `den gc`: `den: not yet implemented: gc expiry, reflog, ref-packing and commit-graph policy (M4, vc13)`, status 2; every other verb as Git's porcelain words | held |
| `git --version` is den's line | `den 0.0.0 (built with wolf 0.2.36)` from both | held |
| about 110 typed lines and 600 transcript lines a session | 138 typed lines, 859 transcript lines | wrong (more rows than sketched) |
| 4-6 minutes a boot under KVM | about 7 minutes (the typing at 20 ms a character and the prompt waits) | wrong, by a minute |
| byte-identical to Linux at the first try of a correct rig | yes, once the rig was correct: the first run's two differences were the rig's (a typed `$ ` the prompt counter took for a prompt, and an ISO variable reused across modes), never PAX's | held |
| nothing in the images changes but den | **wrong**: den prints a date only from the zone database (`$TZDIR/$TZ`), which PAX's images did not carry; every dated verb said `fatal: invalid`, on PAX and in the container alike. R-px90-2: `/usr/share/zoneinfo/UTC` now ships, the bytes `/etc/localtime` already had | wrong; fixed in the image, reported for den |
| (not predicted) | at a terminal, `den log` asks for decorations den does not draw: `den: not yet implemented: history decorations`; `--no-decorate` or `log.decorate = false` gives the plain log | a den limit, reported; README says so |

## 4. Evidence index

### The pin, the build, the install

- `user/den.pin` (`51a09f20`): den at `13bc2caa`, a header in `user/scent.pin`'s style (what den is, its clean
  room, what the pin carries and lacks). `/etc/pax-release` gains its `den` row from it (`tools/mkpax-release`
  reads every pin; `tests/census` C6 and R0 green).
- `tools/mkden` (`8181588b`, `278d8a04`, `b631daec`): `PAX_DEN_REPO` for a local cache, exactly the pin through
  `tools/fetch-retry` (its seventeenth site, `55fcb7eb`), den's `wolf-toolchain.toml` read, the wolf and lupin
  archives by den's digests read twice, the std the archive bundles checked against the pin's, den's own
  `tools/mkden` in two checkouts (each builds twice and refuses two digests), the two checkouts' binaries
  compared, ET_EXEC and no PT_INTERP, `sums.txt`. Four builds, `d4d3d6b8…` every time (first at `8181588b`,
  again in every later build of this lane).
- `tools/install-den` (`b94ddeb7`): `/bin/den` byte for byte (checked against `sums.txt`), 0755, and `/bin/git`
  a symbolic link to `den`; one helper for both image builders. `tools/distribution-root` (`e9ecfbf7`) puts both
  in the dev and the release roots, den unstripped; `pax-install` copies the live root whole, links included
  (`user/install/snapshot.lu`), so the installed disk carries them with no installer change.
- `tests/distribution` (`5e62f233`, `914fd794`): the packed den is mkden's bytes and size, 0755, root's; `bin/git`
  an entry of mode 0120777 whose data is `den`; the zone file is `/etc/localtime`'s bytes. `tests/distribution-boot`
  (`a68bbb6b`): on both ISOs and both firmwares `den --version` and `git --version` print
  `den 0.0.0 (built with wolf 0.2.36)` and `readlink /bin/git` prints `den` (I2, four boots).

### The typed session (`tests/mpx5-den`, `user/console/den.keys`)

The keys (`238015ff`, `6c39ddb4`, `d74b7be6`, `b2ffe960`) set den's pinned environment themselves (den's
`tools/environment.py`: `LC_ALL=C`, `TZ=UTC`, a scratch HOME and XDG home, a global config of a fixed identity
with no system config, colour off, pager cat, empty hooks and template, `GIT_EDITOR=false`, `GIT_PAGER=cat`, and
author and committer dates a minute apart a step), then type 138 lines between `den-session-begin` and
`den-session-end`. Every verb runs through `s`, so its status, its standard output and its standard error are
three separate blocks of the transcript.

| verbs | what the session holds |
|---|---|
| `init`, `config` | `init repo`; `config --get` of `core.bare`, `core.filemode`, `user.name`, `init.defaultBranch` and of a `core.autocrlf` the keys append to `.git/config`; `config user.name Other` refused by den (no writer at the pin) |
| `add`, `status`, `commit` | `status` human (4) and `--porcelain` v1 (10, through untracked, staged, modified, conflicted, clean); `commit -m` and `commit -a` (14 commits) |
| `log`, `diff` | `log` default, `--oneline`, `-p -n 1`, `-n 3`; `diff` of the worktree, `--cached`, `HEAD~2 HEAD`, `HEAD~1 HEAD` |
| `branch`, `switch`, `merge` | `branch`, `switch`, `switch -c`; a fast-forward `merge`, then a three-way `merge` that stops on a conflict (status 1, `CONFLICT (content)`, Git's markers in the file, `UU`), resolved by `add` and `commit -m` |
| `rebase`, `cherry-pick`, `revert` | a linear `rebase main` of a feature branch, its fast-forward merge; `cherry-pick` of a branch's commit; `revert --no-edit HEAD` |
| `tag`, `cat-file`, `blame` | a lightweight and an annotated tag (`-a -m`), the list, `cat-file -t` and `-p` of the tag object; `blame` across the merge |
| `stash`, `notes`, `reset` | `stash push -m`, `list`, `pop`; `notes add -m`, `show`, `list`, and the note in `log -n 1`; `reset --soft HEAD~1`, `--mixed HEAD`, `--hard HEAD~1` |
| the editor | `commit --allow-empty` with `GIT_EDITOR=false`: `error: there was a problem with the editor 'false'`, status 1, as Git; with `GIT_EDITOR=yew`: `den: not yet implemented: commit editor yew`, status 2: den never runs an editor |
| through `git` | `--version`, `status`, `log --oneline -n 3`, `branch`, `tag`, `diff HEAD~1 HEAD`, `cat-file -p HEAD`, `init ../made-by-git`, `fsck --full --no-dangling`: nine verbs, each block byte-identical to den's |
| packs | every loose object file's sha256; `fsck --full --no-dangling`; `gc` refused by den; `repack -a -n -q -d`, `prune-packed`, the pack's sha256s, `verify-pack -v`, `fsck` and `log` again from the pack |
| the terminal | `den log --oneline -n 2` written to the console: `den: not yet implemented: history decorations`; with `--no-decorate`, the two lines |

Assertions (per tier, firmware and session): D0 the build (every program static, den one digest, `bin/git` an
archive link read back by a reader of the suite's own, the home disk the bytes `tests/mpx6-ext2.d/disks.sha256`
records); D1 the session byte-identical to the container's; D2 the 39 witness rows of `tests/mpx5-den.d/rows.py`
(den's answers fixed by Git's formats and den's README, and every `git` block equal to the `den` block before
it); D3 the disk after the boot: `e2fsck -fn` clean, both repositories read back by debugfs, the pack files the
session's bytes, and Linux's own `git` finds them whole (`fsck --full`) with the commits den's log printed; D4
-ENOSYS only for 273 and 334, nothing refused, init ended with status 0, halted.

| image | firmware | den-root | den-user | D3 | D4 |
|---|---|---|---|---|---|
| mpx5-den's own, native kernel | BIOS, UEFI | 859 lines = Linux (`b83e3ec8…`), 39 rows | 859 lines = Linux (`3cd734d7…`), 39 rows | clean; git 2.43.0 reads both | 273, 334 only |
| mpx5-den's own, release kernel | BIOS | the same `b83e3ec8…` | the same `3cd734d7…` | clean | 273, 334 only |
| the rebuilt dev ISO (`/home` in memory) | BIOS, UEFI | the same `b83e3ec8…` | the same `3cd734d7…` (`su pax`) | not run: no disk | quiet kernel: no lines |
| the disk installed from the rebuilt release ISO (`/` and `/home` its ext2 root) | BIOS, UEFI | the same `b83e3ec8…` | the same `3cd734d7…` (`su pax`) | clean; git reads both | quiet kernel: no lines |

The session digests are the same on every image, tier and firmware: one den, one transcript. A boot's two
sessions run 212 den processes and 18 through `git` (198 exit 0, 4 exit 1, 10 exit 2: each the same status in
the container); the native boot under KVM took about seven minutes, nearly all of it the typing.

### The installed disk across a reboot (`tests/distribution-den`, `tests/mpx6-install.d/den.py`)

`tests/distribution-install` installs from the rebuilt release ISO onto a fresh 1 GiB virtio disk (px82's test;
`1843d7d5` gives it px78's install allow-list, without which `pax-install` now refuses every target of a live
ISO: `refused: no usable install allow-list`), then boots the disk alone under BIOS and UEFI (I3). `den.py`
(`eaeeeb66`, `1abc642c`) boots a copy of it alone, as `session.py` does: boot 1 at the installed root shell,
den's pinned environment, `den init`, `add`, `commit`, `reboot`; boot 2 `den log`, `den fsck --full`, `git log
--oneline`, `den status --porcelain`, `exit`. Then, on the host: the root partition `e2fsck -fn`; `/bin/den` and
the repository read back by debugfs; the same steps on Linux with that den.

| row | BIOS | UEFI |
|---|---|---|
| P1 `den init`, `add`, `commit` exit 0 on the installed root; `reboot` marks `/` clean and restarts | PASS | PASS |
| P2 after the reboot `den log --no-decorate` is Linux's byte for byte, `den fsck --full` exits 0 with nothing on either stream, `git log --oneline --no-decorate` is den's on Linux, the worktree clean | PASS | PASS |
| P3 the root `e2fsck -fn` clean; the three object files on the disk (`.git/objects/6e/cec20e…`, `78/80b89c…`, `ef/f7d832…`) byte-identical to Linux's; HEAD and `refs/heads/main` Linux's | PASS | PASS |

The pre-run (hasu, `~/lanes/px90/jobs/dist2/` and `persist2/`) installed from the release ISO built at
`660a8871`; the gauntlet repeats every step at the final head.

### The images

`tools/mkdistribution` at a clean checkout, with every program input rebuilt at the head by its own builder
(pelt, scent, den, lupin, lope, aspen, lobo, the games, yew, the base std, boreutils' 107: about 48 minutes on
six CPUs) and px82's base payload. The pre-run at `660a8871` (`~/lanes/px90/jobs/dist1/out/`):

| artifact | bytes | sha256 |
|---|---:|---|
| release ISO `pax-660a8871.iso` | 408,389,632 | `9395cbd47dc6a276f3dfb8ceee937b8535af7ffd743c30f0e14c92a171345702` |
| dev ISO `pax-dev-660a8871.iso` | 552,022,016 | `59f1c197339938cb378db045db59183d62f58d28e6ce4b78cdef8f81465105c2` |
| release initramfs (335 entries) | 401,615,828 | `b7c7da9b270857681eefdf988ea748d571e3ced13fd5a3f61ded45e4f62f77db` |
| dev initramfs (463 entries) | 545,240,884 | `235fa34d154cb1e4ef559ce2f0f93801f797d81fc2049a5ab30fb7410f198256` |
| kernel (release tier) | | `99d81c528077811dfe814523730671d2fc80c3b0c16cb8bae83770d62ee31a0b` |

Both ISOs are 16,939,008 bytes larger than px82's (391,450,624 and 535,083,008), den's 16,698,147 and the
zone's 114 among them, with the installer changes since px82 (px84-px86). `tests/distribution` I0/I1 (252
release and 319 dev file digests, den's bytes, the link, the zone), `tests/distribution-boot` I2 (four boots,
`den` and `git` answering the same line), `tests/distribution-install` I3 (the install, the target alone under
BIOS and UEFI), then the den rows above. Boot logs: `release-{bios,uefi}.serial.log`,
`dev-{bios,uefi}.serial.log`, `install.serial.log`, `installed-{bios,uefi}.serial.log` beside the images; the
final head's images and logs are the gauntlet's, named in the PR.

### The gaps found, by whose

- **den: a date needs the zone database.** den prints a date (`log`, `show`, `blame`, `cherry-pick`'s kept author
  date) only from `$TZDIR/$TZ`, default `/usr/share/zoneinfo/$TZ`, with TZ set or unset; with no such file every
  dated verb answers `fatal: invalid` (`cherry-pick`: `fatal: invalid_date`), where Git prints UTC. Measured as a
  black box on Linux (`TZDIR=/nonexistent` with `TZ=UTC`, `UTC0`, `:UTC`, unset: all `fatal: invalid`; one file
  `UTC` in `TZDIR`: the date). PAX's images had `/etc/localtime` and no zone database, so on PAX every dated verb
  failed, in the container's chroot too. Not a kernel defect; R-px90-2 ships the file; an issue for den to file.
- **den: `log` at a terminal.** Written to a terminal, `den log` asks for decorations and says `den: not yet
  implemented: history decorations`; `--no-decorate`, or `log.decorate = false` in `~/.gitconfig` (measured at a
  pseudo-terminal), gives the plain log. A den limit, the same on Linux; the README says so.
- **pax: `tests/distribution-install` was stale** since px78's allow-list (local-only, never in CI); fixed here.
- **pelt** answers `command -v` for its first name only (POSIX's synopsis names one); the keys ask one at a time.
- No PAX defect was found: every byte the two sessions print, on every image, is Linux's.

### R-px90-1: what stays on the base image (a proposal, not decided)

Measured in the rebuilt roots (`hasu/sizes.py` over the packed cpio: the bytes as installed, stripped where
`tools/distribution-root` strips; den, scent and lupin unmodified):

| program | files | bytes in the release root | note |
|---|---:|---:|---|
| pelt (`/bin/pelt`, `/bin/sh`) | 2 | 5,123,248 | PID 1 and every script's shell |
| boreutils | 107 | 141,209,704 | 1.32 MB a utility, each its own static binary |
| scent (and `grep`, `egrep`, `fgrep`) | 4 | 15,047,837 | unstripped; 1,553,112 stripped (mkscent's measure) |
| den (and `git`) | 2 | 16,698,147 | unstripped; 2,590,744 stripped |
| lupin, and wolf-std beside it | 1 + 56 | 7,747,424 + 1,358,618 | |
| yew | 1 | 7,601,144 | PAX's only editor |
| lope | 1 | 1,722,552 | `/etc/shrc` runs `lope init pelt` in every console shell |
| aspen | 1 | 1,931,224 | |
| lobo | 1 | 2,959,256 | |
| su, as, play, reboot, pax-release | 5 | 3,473,532 | |
| the installer (pax-install, paxgpt, paxfat, paxext2, limine) | 5 | 61,315,856 | the live image's; an installed system can keep or drop them |
| the three games, live (`/home/pax/Games`) | 9 | 66,016,423 | |
| the three games, the installer's payload | 12 | 66,018,067 | the same games again |
| the dev toolchain (dev image only) | 67 | 143,598,471 | |
| clef (dev, opt-in) | 1 | — | not in either default root |
| boot assets, `/etc`, `/usr/share` fixtures, the zone | | 3,348,157 | |

The release root's file data is 401,571,189 bytes; the dev root's 545,176,940.

- **A (the orchestrator's sketch):** on the disk pelt, boreutils, scent, den, lupin (and its std), the installer
  tools and the accounts' tools; to the package manager's repository, once it installs (pm00's design), yew,
  lope, aspen, lobo, clef and the games. The base is about 255 MB; 146 MB moves (yew 7.6, lope 1.7, aspen 1.9,
  lobo 3.0, the games 132).
- **B (recommended): A, with yew kept on the base.** yew is PAX's only editor and den never runs one: without it
  a fresh install edits files and writes commit messages only through `printf` and `cat >`. It is 7.6 MB, 1.9%
  of the release root. Moving lope also means `/etc/shrc` guards its `lope init pelt` (`command -v lope`).
- **C:** everything stays until the package manager installs (today's roots).

Two facts for whichever is ruled: the games are packed twice in the live image (66 MB live and 66 MB as the
installer's payload), the largest single saving; and den and scent are installed unstripped as their contracts
say (31.7 MB; 4.1 MB stripped), which is a separate choice from the base set.

### R-px90-2: the zone file (recommended and implemented)

- **A (implemented, `49fa017b`, `b39cbdcd`):** both distribution roots and mpx5-den's image carry
  `/usr/share/zoneinfo/UTC`, 114 bytes, the bytes `/etc/localtime` already has (`tools/mkzone`, RFC 8536);
  `tools/distribution-root` builds it with `tools/mkzone` and refuses if it is not the base's `/etc/localtime`.
  den's dates then work with `TZ=UTC` and with TZ unset.
- **B:** no image change; document `TZDIR`. Every dated den verb fails out of the box.
- **C:** den falls back to UTC for `TZ=UTC` or no TZ when the database is absent, as Git does: den's change, not
  PAX's; to file as a den issue whatever is ruled here.

### The plant

The plant is one commit on the final head, `px90-plant-git-copy`, pushed with no PR (the local merge gate): it
changes one hunk of `tools/install-den` so that `/bin/git` is a small script that is not den, a copy where the link
was. Its red is shown by name in its own gauntlet record (`hasu/gauntlet.sh` with `PLANT=1`: mpx5-den on native
BIOS): the `link`, `git-version`, `git-status` and `git-log` rows of `tests/mpx5-den.d/rows.py`, and D0's archive
row. The record and its FAIL lines are in the PR body.

### CI

`mpx5-den` is a CI job (`feac14de`): it builds den, the image and the home disk, runs the Linux side in a
throwaway container and boots the plan's legs; the tier job needs it. `tools/ci-tiers.map` (`4f1c3464`) and
`tests/ci-plan` (`81fb98bf`, 319 rows green locally) route den's pin, builder, installer and keys to it, and
kernel/ext2, kernel/fstab, kernel/vblk, kernel/block and `as` reach it as they reach the other user and disk
suites. The image builders, a pin and CI itself make this PR `cross-cutting`. The distribution's tests are
local, as px82 left them (their base payload is a lane input, not in the repository).

## 5. Done-when

- [x] 1. The prediction, committed first (`5f6c8e15`), scored above.
- [x] 2. The pin: `user/den.pin` at the full sha, with its header.
- [x] 3. `tools/mkden`: `PAX_DEN_REPO`, exactly the pin, den's toolchain read, the archives read twice, den's own
  builder in two checkouts, one digest, ET_EXEC and no PT_INTERP, the sums; built only in the Ubuntu 24.04
  container.
- [x] 4. Installed unmodified as `/bin/den` 0755 with `/bin/git` a link to it, in the dev and release roots and so
  on the disk `pax-install` writes; the README says `git` is den and quotes den's own usage text.
- [x] 5. `tests/mpx5-den`: as root and as `pax`, on the ext2 `/home`, every verb of the contract, stdout, stderr
  and status apart, object ids and object bytes equal, nine verbs through `git`, `GIT_EDITOR=false` and
  `GIT_PAGER=cat` set and the editor's refusal shown.
- [x] 6. Persistence on the installed disk, from the rebuilt medium, with the mpx6-install rig (`den.py`).
- [x] 7. The dev ISO and the install medium rebuilt through the current builders, their commits, digests and
  boot logs recorded, booted for items 5 and 6; README's shipped programs and pins table.
- [x] 8. R-px90-1 proposed with the sizes; not decided.
- [x] 9. The plant, local, pushed without a PR, red by name in its own record.
- [x] 10. This note; the PR with its Footprint line; the gauntlet at the final head; the audit once.

Issues for the orchestrator to file (none filed by this lane): den, the zone database (dates need
`$TZDIR/$TZ`; Git prints UTC without it); den, `log` at a terminal (`history decorations`). Nothing to close.
