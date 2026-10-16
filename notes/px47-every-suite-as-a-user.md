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
