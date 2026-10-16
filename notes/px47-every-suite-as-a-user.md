# px47 — Every suite as a user (P5 lane U7: the user runs, the pelt pin, the words)

Contract: px47's, `sprints/pax/47-every-suite-as-a-user/` in
wolffe-lang/wolf (planning commit `be08902`, read 2026-10-16), under
`sprints/pax/p5-the-users-campaign.md` (ruling #75, R1 to R9) and the
rules of `sprints/crawl-54.md` and `sprints/wave-53.md` down to
`wave-45.md`. Branch `px47` in pax, cut from pax trunk `654c9ec`. §1 to
§3 are committed before the first change to a pin, the kernel, a tool, a
program or a test, and before the first measurement.

Until now every suite ran as root, so a permission bug only a user would
meet stayed green. Three deliverables: **a non-root run** of the tree,
shell, boreutils, unix, tcp, udp, speaker and lobo suites, each beside
its root run (which stays), each driven through `su pax -c …`/`su pax`
(px46) or `as` (px39), each with a Linux side run as a user too; **pax's
pelt pin** moved to `06223a8` (sh16, tab completion), built by pax's own
`tools/mkpelt`; and **the docs' words** for multi-user PAX, R6's:
**enforced for honest programs; not a boundary against an attacker**.

## 1. Forbidden, absolutely

- No source of any kernel, libc, file system, shell, `su`/`login`,
  shadow-utils, util-linux or coreutils is read (ruling #22). Facts come
  from the man pages, POSIX.1-2024, the allowed uapi headers, pax's own
  source, and px38's to px46's recorded Linux answers. A Linux answer
  nobody recorded is measured black-box: a user's rows in a throwaway
  container (`tools/linux-tree --owners`, the image's owners and modes;
  a rootless container is a sound reference for a user's rows and is
  never used for what root may do); real root's rows under QEMU (kasumi's
  own kernel image as a guest, px46's `vmtty.c` and `linux-vm.sh`).
- No account is made on any host and nothing uses `sudo`. Accounts exist
  in PAX's images and inside throwaway containers and guests only; a
  test becomes a user through `su` (in an image that has `/etc/passwd`)
  or `as`. Refusal cases are built into the image with owners and modes
  (`tools/mkinitramfs`'s `:MODE:UID:GID`), not by `chown` at run time.
- Set-ID execution is not honoured (R5). The `execve` rows that need a
  program written since boot stay unmatched (the px27 loader limit) and
  are named; the loader limit is not lifted here.
- Nothing calls PAX secure; R6's two halves always together; no word
  implying filming.
- Static binaries are built in the Ubuntu 24.04 container on kasumi
  (`px13-ubuntu`), never against kasumi's own glibc. No build on this
  Mac (nomad-1). kasumi and hasu: commands under `bash` (hasu: `env
  bash`), long jobs under `setsid` with a pid file, killed by that pid
  only (never by name, pattern or process group); work under
  `~/lanes/px47/`, pruned as I go; never `/tmp`. hasu: BIOS only, write
  only under `~/lanes/px47/`, port 9308's server untouched. Host ports
  8080 and 8088 are not used. Nothing is installed anywhere.
- No `rm` outside `~/lanes/px47/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer on a commit or the PR. No run
  of another lane is cancelled. "Seen red" cites a run. If the harness
  refuses an action I stop and report.

## 2. Inputs, verified (2026-10-16)

| input | found |
|---|---|
| pax trunk | `654c9ec` (px46 merged, PR #65), the contract's; `origin/trunk` the same at the start |
| planning repo | `be08902`: the contract, the campaign (R1 to R9), crawl 54 |
| pelt | pin `7dd3304` (sh15) → `06223a8` (sh16, PR #30, merged): 22 commits, `src/` +800 −3, `wolf-toolchain.toml` unchanged (wolf 0.2.30 `4e55b39e…`, wolf-std `fd6bcdc`); sh16's last code commit is `d8d420c`, `06223a8` adds notes only (`git diff d8d420c 06223a8 -- src` empty) |
| sh16's static pelt | `6774441b…`, 14,765,328 bytes, built from `d8d420c` by pax `b7fb8d1`'s `tools/mkpelt` in a plain Ubuntu 24.04 container; its log says `wolf build: note: ld.lld not found on PATH — linking with the system linker` (pelt `notes/sh16-evidence/logs/mkpelt.log`) |
| `px13-ubuntu` | `ad896450…` on kasumi, has `/usr/bin/ld.lld` (Ubuntu LLD 18.1.3), clang 18.1.3; CI installs `lld` in every job (`.github/workflows/ci.yml`) |
| `su`, `as` | `user/su/su.lu` (`tools/mksu`, px46), `user/elf/as.c` (`tools/mkcred`, px39) |
| the Linux side of a user | `tools/linux-tree --owners` (px46), typing `su pax` or running `as` in the container; `notes/px46/vmtty.c`, `linux-vm.sh` for real root |
| suites | `mpx3-tree` (`tree` probe as pid 1 and two typed sessions, Linux side in containers), `mpx3-shell` (typed sessions and `procs`, Linux side `tools/linux-tty` as root on the host), `mpx3-boreutils` (a run list under `kmain_boreutils`, Linux side `tools/linux-run` as root on the host), `mpx4-unix` (probes, soak, ctl as pid 1, containers), `mpx4-tcp` and `mpx4-udp` (run lists under `kmain_sockets`, three ways; Linux `tools/linux-net` as root on the host), `mpx3-speaker` (typed sessions held to `.expect` files and to the tones), `mpx4-lobo` (steps typed at pelt, Linux side in a container) |
| lobo#52 | closed (ws54): lobo at pax's pin `944edc1` reads its effective uid from `/proc/self/status`; with a `user` directive it warns and loads when unprivileged and refuses by name as root (it cannot drop privileges at that pin). It applies: PAX has `/proc/self/status` (px39), so lobo run as `lobo` (990) is told its uid |
| CI | tiered (px37, px40); `user/pelt.pin` is no line of `tools/ci-tiers.map`: by derivation it runs the suites whose scripts name `tools/mkpelt` |
| open issues | pax#55, #56, #58, #60, #62, #63, #66, #67, #68 |
| kasumi | `/home` 34 GB free; Linux 7.2.8-1-cachyos |

## 3. Prediction (committed before the first change and measurement)

**P1. The pin.** `tools/mkpelt` at `06223a8` in `px13-ubuntu` builds a
static pelt (ET_EXEC, no PT_INTERP) whose digest is **not** sh16's
`6774441b…`: wolf links through `ld.lld` when it is on PATH and through
the system linker (GNU ld) when not (the note in sh16's log), and
`px13-ubuntu` has it. The same build twice gives the same digest, and
the build in CI (which installs `lld`) gives that digest too. Hiding
`ld.lld` from `px13-ubuntu` reproduces sh16's `6774441b…` byte for
byte. **No expected text moves**: no suite types a Tab. Every suite
that stages pelt stays green on the pin alone. **Falsified by** CI's
digest differing from kasumi's, by the no-lld build differing from
`6774441b…`, or by any suite's text moving.

**P2. The user runs.** Each suite gains user sessions beside its root
ones (which do not change), held byte for byte to the same binaries run
as the same user on Linux (`tools/linux-tree --owners` for every user
side, so no new Linux side needs root on a host):

| suite | user run | how | Linux user side |
|---|---|---|---|
| `mpx3-tree` | the `tree` probe and its soak as 1000:1000; `shell-tree` and `shell-changes` typed after `su pax`, in `/home/pax` | `as`, `su` | container, `as` and `su` |
| `mpx3-shell` | a session after `su pax` (listing, a pipeline, redirections in the home, a write to `/etc` refused, `ls -l`, a trap and Ctrl-C, `env`); `procs` as 1000:1000 | `su`, `as` | container |
| `mpx3-boreutils` | the run list with every line under `as 1000 1000`, and a 0600 file and a 0700 directory of root's refused | `as` | `tools/linux-run` inside a container |
| `mpx4-unix` | the probes and `ctl` as 1000:1000 | `as` | container (`--sys`) |
| `mpx4-tcp`, `mpx4-udp` | the `none` way's run list as 1000:1000, and a port below 1024 refused | `as` | `tools/linux-run` inside a container with no network, `ip_unprivileged_port_start` 1024 |
| `mpx3-speaker` | `play` and `beep` after `su pax` | `su` | the tones' rows: px45's measured Linux answer (KIOCSOUND 0 on the caller's controlling VT); `beep`'s `/dev/tty0` refused: real root's guest |
| `mpx4-lobo` | `serve` as `lobo` (990) through `su -s /bin/pelt lobo`, on a port above 1023, and port 80 refused | `su` | container |

What I expect them to find (each a finding: fixed if small, else listed):
- **Most user rows are already Linux's**: px43 to px46 held the class
  rule, names, signals and privileges to Linux with probes run as users.
  I expect **between one and four** user-only findings across the eight
  suites, none in `mpx3-boreutils` (it reads only) and none in the
  net `none` runs beyond the low port (which px45 measured).
- **A harness finding before a kernel one**: Docker and podman set
  `net.ipv4.ip_unprivileged_port_start` to 0 inside a container's
  network namespace, so a container's user may bind port 7: a user
  side that does not set it back to 1024 is not Linux's default, and
  would make PAX's (correct) refusal look like a red.
- **The tree probe as a user** differs from root's in its `~` lines
  (what PAX answers by name, held to PAX's own text) and its `/dev`
  rows: I expect PAX to answer `-EROFS` (its fixed `/dev`) where Linux
  answers a user `-EACCES` (the search or write check first) for a name
  made or removed in `/dev`: one finding, small (the order of two
  checks), fixed.
- **A user's history file**: each `su pax` shell leaves
  `/home/pax/.sh_history`, root's `/.sh_history` (px46): the tree
  counts move by one inode and one page per shell.
- `mpx4-lobo`: lobo as `lobo` with `user lobo;` in its config prints
  nginx's warning and serves (lobo#52 applies); as root on PAX it
  refuses the directive by name, as on Linux.

**Falsified by** a user run red against its Linux side for a reason I
did not name above, more than four findings, or a root run that moves.

**P3. Linux's two references agree.** For each typed `su` session the
container's transcript is byte-identical to real root's guest's (user
rows are user rules: a rootless container is sound for them). Falsified
by any difference.

**P4. Cost.** Each suite's CI job grows by its user boots: about one
fifth more boot time on `mpx3-tree`, `mpx3-shell` and `mpx4-unix`, one
boot a leg more on `mpx3-boreutils`, `mpx4-tcp`, `mpx4-udp`,
`mpx3-speaker` and `mpx4-lobo`. No job passes 60 minutes on a leg.

**P5. Plants**, each in a CI run of its own with one suite: A, the
kernel's class rule (`kernel/files`' `may`) treats every caller as root
— every root session stays green and the user runs go red (that is what
the lane exists to show); B, `as` keeps root's uid (it skips
`setresuid`) — the container agrees with PAX (same binary) and the user
run is red only where a check names the uid it expects.

**P6. The words.** README gains a paragraph on multi-user PAX (the
accounts, `su`, the checks, which suites run as a user), with R6's
sentence whole; CHANGELOG gains px47's entry. Nothing says "secure".

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | mkpelt in `px13-ubuntu` builds a digest that is not sh16's, the same twice and in CI; hiding `ld.lld` gives sh16's `6774441b…`; no expected text moves | `af7351d1…`, 15,002,424 bytes, twice; with `ld.lld` hidden `6774441b…`, 14,765,328 bytes, sh16's to the byte (`notes/px47/kasumi-pins.out`); CI: §A; no root session's text moved on any suite run here (§B) | right |
| P2 | user runs held to Linux's users; one to four user-only findings, none in boreutils or the net runs beyond the low port; Docker and podman give a container port start 0; the tree probe's `/dev` rows -EROFS where Linux says -EACCES; lobo warns as lobo, refuses as root | **two kernel findings** (§C 1, 2: `/dev` and `/proc`/`/sys`), both fixed, plus **three harness findings** (§C 3–5) none of which I predicted; the `/dev` one was predicted for names made in `/dev` and was also `rmdir`/`rename` of `/dev` (-EBUSY); rootless podman already gave 1024 (CI's Docker: §E); boreutils and the net runs found nothing of the kernel's; lobo as predicted | right on the count (two of the kernel's), wrong on the harness |
| P3 | each typed `su` session's container transcript is real root's guest's, byte for byte | `shell-changes-user` 136 lines the same after the dates; `shell-tree-user` differs in two lines, both about `/` itself: the guest's `/` is the initramfs root, **1777** (measured, `notes/px47/linux/px47-root-mode.tty`), where PAX's and the container's are 0755, so a user's `mkdir /t` succeeds there and `rmdir /bin` is -EPERM (sticky) for -EACCES (§G) | wrong (2 lines, the guest's `/`, not a user rule) |
| P4 | about a fifth more boot time on the typed suites; no job past 60 minutes a leg | §E | §E |
| P5 | plant A red in the user runs only; plant B agrees with itself in the container, red only where a check names the uid | §F | §F |
| P6 | README and CHANGELOG in R6's words; nothing says secure | so (§D) | right |

## A. The pelt pin (item 1)

`user/pelt.pin` → `06223a8` (sh16, pelt PR #30), its own commit
`f29ba05`. The toolchain is `7dd3304`'s (`wolf-toolchain.toml` does not
move); sh16's last code commit is `d8d420c` (`06223a8` adds notes only).

**Why sh16's static pelt differed.** sh16 built `d8d420c` with pax
`b7fb8d1`'s `tools/mkpelt` in a plain Ubuntu 24.04 container that has
clang but no `ld.lld`; wolf 0.2.30 says so and links with the system
linker (`wolf build: note: ld.lld not found on PATH — linking with the
system linker`, pelt `notes/sh16-evidence/logs/mkpelt.log`). pax's own
build host (`px13-ubuntu`) and CI's runners (`apt-get install … lld`
in every job of `ci.yml`) have `ld.lld`, so wolf links with it. Measured
in `px13-ubuntu` on kasumi (`notes/px47/kasumi-pins.out`):

| build | sha256 | bytes |
|---|---|---|
| `tools/mkpelt` at `06223a8`, `ld.lld` present | `af7351d1eee039dd0a3320e733d7b5cf755776c222cba89a821479fe57180ab3` | 15,002,424 |
| the same, again | `af7351d1…` | 15,002,424 |
| the same with `/usr/bin/ld.lld` moved aside in the throwaway container | `6774441ba446250e05065fd4dfa384d80bde593c2f4f612db073488b10c0a997` (sh16's) | 14,765,328 |

So the source is the same and the linker is the difference; the pin is
what pax's own tool builds, and the binary every suite boots is
`af7351d1…` (CI's digest: §E). No expected text moved: no suite types a
Tab.

## B. Each suite's user run and its Linux side (item 2)

Every suite keeps its root sessions unchanged and gains sessions run as
a user. A user is made one of two ways, never by an account on a host:
**`as`** (px39's `user/elf/as.c`, built alone by the new `tools/mkas`:
no supplementary group, the three group ids, the three user ids, then
`execve`), as pid 1 or as a run-list line; **`su`** (px46's, in wolf)
typed at root's pelt, in an image that carries px46's `/etc/passwd`,
`/etc/group` and `/etc/login.defs` (R3: `pax` 1000, `lobo` 990), with
the user's home and every refusal built into the image by
`tools/mkinitramfs`'s owners and modes. The Linux side of a user is the
same binaries as the same user in a throwaway container (rootless podman
on kasumi, Docker in CI): `tools/linux-tree --owners` (the image's
owners and modes applied after the copy), typing `su pax` or running
`as` there, `--runlist` (px47) for the run lists, `--net` (px47) where
the run list needs PAX's addressing; lobo's through
`tools/lobo-session --linux --owners` (px47). Real root's guest
(`notes/px47/linux-vm.sh`, px46's `vmtty.c`) records what a container
cannot have: `beep`'s `/dev/tty0` and `/dev/console` (devtmpfs's modes),
and P3's cross-check.

Measured on kasumi, native BIOS, at the code of `5f17292`
(`notes/px47/kasumi-*.out`); every leg in CI (§E).

| suite | user session | how | its checks | the Linux row each is held to | kasumi |
|---|---|---|---|---|---|
| `mpx3-tree` | `probes-user` | pid 1 `/bin/as 1000 1000 /bin/tree`; `/t` the user's (0755) | T1 every line but `~`; T2 the `~` and refusal lines; T3; T4; T8 | T1: the container as 1000:1000; T2: PAX's own recording `tests/mpx3-tree.d/probes-user.pax` (10 lines: the loader limit, the time past 2262, the flags and sizes PAX refuses by name — root's named rows, a user's values) | T1 154 lines, T2 10 lines, T3, T4 (4 refusals by name), T8 |
| | `soak-user` | `as … /bin/tree soak` | T1, T3, T4, T5, T8 | the container as 1000:1000 | 5 lines; census flat; both fills |
| | `shell-tree-user` | `su pax`, the tree session in `/home/pax`, then root's things refused: a write to `/etc/motd`, `mkdir /t`, a copy into `/etc`, a move into `/bin`, `rm /etc/motd`, `rmdir /bin`, `rm -rf /` | T1, T3, T4, T6, T8 | the container (`--owners`); real root's guest: §G | 85 lines; T6 36 names and the two history files |
| | `shell-changes-user` | `su pax`, the changes session in the home, then `chmod`, `touch`, `touch -t`, `ln` of root's `/etc/motd`, `chown` to root, `chgrp` to root refused, a symbolic link to it read | T1, T3, T4, T6, T8 | the container; real root's guest: 136 lines the same (§G) | 136 lines |
| `mpx3-shell` | `shell-user` | `su pax`: listings, a pipeline, a group read from a file, `cd`, a file made and read in the home, `/etc/secret` (0600) and a name in `/etc` refused, `ls -l /etc`, `stat` of owners, `/proc/self/exe`, `env`, a trap, Ctrl-C on `sleep`, SIGPIPE | S1 (and the tree: two history pages, the home's page, the inode table), S2, S3, S4, S5 | the container (`--owners --rdev`) | 92 lines, exit 130 |
| | `procs-user` | pid 1 `/bin/as 1000 1000 /bin/procs` | S1, S2, S3, S4, S5 | the container | 45 lines, as root's (procs asks nothing a user is refused) |
| `mpx3-boreutils` | the user run list | `user/mpx3-boreutils-user.run`: root's 29 lines under `as 1000 1000`, then 0600 `/etc/secret` and 0700 `/etc/private` read by the user (refused) and by root | B1 to B5 as root's; B6 (new) | the same list in the container (`--runlist --owners`); B6 each side's own `Permission denied` | 38 commands; B6 7 refusals both sides, root's read |
| `mpx4-unix` | `probes-user`, `soak-user`, `ctl-user` | pid 1 `as 1000 1000 /bin/unixprobe` (`soak`), `/bin/ctl`; `/u` and `/logs` the user's | U1, U2 (root's checks; and the user's `/proc/self/cgroup` open to write EACCES on both sides), U3–U7 | the container (`--sys --owners`) | U1 259, 6 and 20 lines; U2 the cgroup row; U5 census flat; U6 lobo's client |
| `mpx4-tcp` | `none-user` | `user/mpx4-tcp-none-user.run`: the six `none` lines under `as`, then ports 7 and 1023 | T1–T4, T7–T9 as `none`; T2 also: 7 and 1023 EACCES on both sides | the same list in the container, addressed as PAX (`--runlist --net 10.0.2.15/24,10.0.2.2`) | 8 commands; loopback 16 MiB, 10,000 connections |
| `mpx4-udp` | `none-user` | `user/mpx4-udp-none-user.run`: the three `none` lines under `as`, then ports 7 and 1023 | U1–U4, U7, U9 as `none` (14 sockets made and freed: the two refused binds); U2 also the low ports | the same, in the container addressed as PAX; `udpfill` to its file as root's | 5 commands |
| `mpx3-speaker` | `speaker-user` | `su pax`: `id`, `play`, a refused file, `hold`, `play scale` | K1 `user/console/speaker-user.expect`; K2 the scale (Hz and the kernel's ticks); K3 hold's tone stopped; K4 9 tones; K5 | px45's measured row: KIOCSOUND answers 0 on the caller's controlling VT, whoever it is (PAX's console is every process's); a pseudo-terminal has no speaker, so no container is a reference | 24 lines; worst 0.065% |
| | `beep-user` | `su pax`: `beep` (`/dev/tty0`), `beep -e /dev/console`, pelt's `>` to each | K1, K4 (no tone), K5 | real root's guest, recorded: `tests/mpx3-speaker.d/linux/beep-user.tty` | 19 lines |
| `mpx4-lobo` | `serve-user` | root: `lobo -t` of `/srv/lobo/conf/lobo.conf` (`user lobo;`); `su -s /bin/pelt lobo`; port 80 refused; port 8000 served as lobo, the `user` directive warned of; a file lobo writes, served; stop | L1, L2, L3 (R1 replies, R3 page, R4 written, R9 lobo's lines), L4 | the container: bash dropped to 990 by an `exec` (`lobo-session --linux --owners`), `--network host` (the host's port start, 1024 on kasumi and the runner) | 34 steps; R1 15 replies; R3; R4; R9 7 lines (read from `lobo: [` on since `309ffe5`: one run's first lobo line landed on pelt's echo of the line typed before it, `notes/px47/kasumi-mpx4-lobo.out`) |

lobo#52 applies, as P2 said: lobo at pax's pin reads its effective uid
from `/proc/self/status`, which PAX has (px39). As root, `lobo -t` of a
config with `user lobo;` is refused by name (`[emerg] … lobo cannot
drop privileges at this pin …`, status 1) on PAX and on Linux; as
`lobo` it prints nginx's warning (`[warn] the "user" directive makes
sense only if the master process runs with super-user privileges,
ignored in ./conf/lobo.conf:7`) and serves. Port 80: `[emerg] bind()
to <address>:80 failed`, status 1, both sides.

`logname` is left out of every session (px46: a container inherits the
host's login uid).

## C. What a user run found that root's never did (item 3)

1. **Kernel: a user's write to `/dev` was answered `/dev`'s fixed
   answer before Linux's permission check** (`mpx3-tree` probes-user,
   T1 and the `~` lines). `rmdir /dev` and `rename` of or onto `/dev`
   were -EBUSY for a user, a file, a directory or a symbolic link made
   in `/dev` -EROFS (refused by name), an `unlink` in `/dev` -EROFS;
   Linux tells a user -EACCES for all of them (devtmpfs's `/dev` is
   root's 0755; the write check on the directory comes first) and root
   -EBUSY or success. Fixed in `kernel/files` (`5e49a18`): `may_make`
   asks `/dev` too, before the fixed answer, in `openat`'s O_CREAT,
   `mkdirat`, `symlinkat` and `bind`; `unlinkat` asks `/dev`'s write
   and search; `rmdir` and `rename` of `/dev` ask `/`'s before -EBUSY,
   and a name in or out of `/dev` stays -EXDEV, which Linux answers
   first. Root's answers do not move (`probes` T1, T2: the nine
   refusals as before); the user's probe went from 7 refusals by name
   to 4 and its 154 lines became Linux's.
2. **Kernel: `/proc` and `/sys` files did not ask their mode on
   `open`** (`mpx4-unix` probes-user, U1). Only the guarded files
   (`environ`, `fd/`, px45) asked the class rule; a user opened its own
   0444 `/proc/self/cgroup` to write, where Linux answers -EACCES (root
   0, then -EINVAL on the write). Fixed (`cacf66a`): every `/proc` and
   `/sys` node asks its mode by the class rule on `open`, with
   kernel/procfs's owners (px42); the guarded ones then ask ptrace's
   rule as before (before: `notes/px47/kasumi-mpx4-unix-before-proc-fix.out`).
3. **Harness: a rootless container's `/dev/null`** (`mpx3-shell`
   shell-user, S2 on kasumi). `tools/linux-tty` binds `/dev` into the
   chroot with a plain bind; under rootless podman `/dev/null` is the
   host's node bound onto a file of the container's `/dev`, so the
   plain bind showed the file under it, and the user was refused it
   (`cannot create /dev/null: Permission denied`) — and root, all along,
   wrote into that file rather than into the null device
   (`notes/px47/kasumi-mpx3-shell-before-rdev.out`). `--rdev`
   (`a35bfd1`, made an option of `tools/linux-tree` in `7465906`) binds
   `/dev` whole, made private. It is not the default: with it,
   `/dev/null` is on the host's devtmpfs, another file system than the
   container's `/dev`, which `mpx3-tree`'s root probe reports
   (`paths: … /dev/null is on it 0` on kasumi:
   `notes/px47/kasumi-mpx3-tree-rdev-on-root-probes.out`);
   CI's rootful Docker makes the nodes in the container's `/dev` and
   is right either way. Only the user sessions that write `/dev/null`
   ask for it.
4. **Harness: `tools/linux-run` left SIGPIPE ignored** (`mpx4-tcp`
   none-user, T2 on kasumi): Python ignores SIGPIPE and SIGXFSZ, and an
   ignored signal stays ignored across `execve`, so `tcperr`'s child
   wrote "EPIPE: not killed" on Linux where PAX kills it (px46 found the
   same in `linux-tty`, px23 in `linux-net`). `linux-run` gives the
   program both at their defaults (`f6620d3`;
   `notes/px47/kasumi-mpx4-tcp-before-linux-run-fix.out` before it);
   `mpx3-boreutils`' root
   list writes no broken pipe, so nothing it held moves.
5. **Prediction and harness: the container's port start.** Rootless
   podman's `--network none` namespace already had
   `ip_unprivileged_port_start` 1024 (every `linux-tree` line in the
   logs; P2 said 0 for both engines); CI's Docker: §E. `linux-tree`
   writes 1024 there anyway and prints what it found.

Not findings but what the user sides needed (setup): run lists in a
container (`--runlist`, `57df9d4`), more than 64 MiB for them
(`b160e4b`), PAX's addressing without a device (`--net`, `7465906`,
`ca3940f`: a tap held open, 10.0.2.15/24, a default route through
10.0.2.2; without it `udploop` and `tcploop` waited on 10.0.2.15 for
ever and `sockerr`'s broadcast and bound-source rows were the
container's, not PAX's), a kernel line after `beep`'s BEL cut out of
the transcript (`deea149`), `as` and its program counted as one pid
(`b160e4b`).

**Each user run's own witness that it was a user's.** A differential
check holds PAX to a Linux side that runs the same `as` or `su`, so a
broken one agrees with itself (px46's plant A, and plant B here, §F).
So each user run also asks something of each side's own answer: the
tree probe's T2 (PAX's recorded user answers), `mpx3-boreutils` B6
(seven refusals told `Permission denied` on both sides, root's read
allowed), `mpx4-unix` U2 (the user's `/proc/self/cgroup` open to write
EACCES on both sides), the net runs' low ports (EACCES on both sides),
the typed sessions' `id` and the speaker's `.expect`, lobo's R9.
`procs-user` has none: procs asks nothing a user is refused, and its 45
lines are root's.

## D. The docs' words (item 4)

`README.md` (`8e6afb2`) gains a paragraph, "Users (P5, px38 to px47)":
the accounts, no passwords, the root shell at boot, `su` as root
becoming a user, set-ID not honoured, the ids and the checks measured
against Linux, the suites now run as a user, and R6's sentence whole:
"These checks are enforced for honest programs; not a boundary against
an attacker: the kernel has never been fuzzed or audited, and it loads
programs at fixed addresses." `CHANGELOG.md` (`5001d79`) gains px47's
entry, ending with the same claim. Nothing in either says "secure"
(checked: `grep -i secur README.md CHANGELOG.md` finds only px39's
`AT_SECURE`).

## G. P3: the container against real root's guest

`notes/px47/linux/`: real root's recordings of `shell-tree-user` and
`shell-changes-user` (kasumi's 7.2.8-1-cachyos `f4c00d5d…` under QEMU
11.1.1, `vmtty` `f00f5189…`, the suite's own `shell-user` archive
`2ec73247…`, 3 GiB: the 336 MB archive did not unpack in px46's 1 GiB),
beside the container's (`ct-*.tty`). After serial normalisation and the
dates of files made in the session masked: `shell-changes-user` 136
lines identical; `shell-tree-user` 84 against 85 lines:

    59d58
    < mkdir: cannot create directory '/t': Permission denied
    67c66
    < rmdir: failed to remove '/bin': Permission denied
    ---
    > rmdir: failed to remove '/bin': Operation not permitted

Both are about `/` itself. The archive names no entry for `/`; the
guest's `/` is the initramfs root, measured **1777 root's**
(`px47-root-mode.tty`: `stat -c %a:%u:%g /` typed in the same guest,
keys `stat -c %a:%u:%g /` and `exit`), so a user may make `/t` there
and `rmdir /bin` meets the sticky rule (-EPERM); PAX's `/` and the
container's (`mount -t tmpfs -o mode=755`) are 0755 root's. Not a user
rule: the recording is not committed as a reference, and the container
stays the user runs' Linux side.
