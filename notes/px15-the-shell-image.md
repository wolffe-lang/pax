# px15 — The shell image (all wolf, quiet)

Contract: px15's, under `sprints/pax/` in wolffe-lang/wolf (planning
trunk, read 2026-10-08). Branch `px15` in
pax, cut from pax trunk `396c5fb` (px14 merged). §1–§3 are committed
before the first change to the kernel, the tests or the image.

## 1. Forbidden, absolutely

- No Linux kernel, glibc, musl or any other kernel's or libc's source
  is read (ruling #22), and no shell's source (ruling #43): pelt is
  used as built from its own repository (`user/pelt.pin`,
  `tools/mkpelt`), its README read for what it claims. Allowed: the
  uapi headers and the syscall `.tbl` in the refs clone's sparse
  checkout (never widened), the ELF/psABI specs, the Intel/AMD manuals,
  man-pages sections 2, 4 and 7, Limine's `PROTOCOL.md` (0BSD) and
  `CONFIG.md`, black-box runs of Linux.
- No `region` held open across a yield, a switch or a return to user
  mode (wolf-lang#611): the new setting is one `.bss` word, written
  once at start-up and read volatile.
- Test binaries for PAX (pelt, boreutils) are built in an Ubuntu 24.04
  container on kasumi and on the CI runner, **never with kasumi's
  CachyOS glibc**.
- No `rm` outside `~/lanes/px15/` and this lane's worktrees; no `git
  add -A`; nothing under `~/.claude`; no merge; no attribution
  trailers; no "seen red" without a run id, sha, path or digest.
- The tour (`kernel/pax_tour`, `kmain_tour*`, `tools/tour`,
  `tests/tour`) keeps passing; if its ISOs change, the tour's folder
  outside this repository is refreshed and its preflight run to GO.
- The setting is named for what it does (`quiet`, a word on the kernel
  command line); nothing in this repository names any use of it beyond
  that.
- No `ls -l`, and no option boreutils' `ls` refuses (#625, #536,
  #626), in the howl session; every command typed on the image is in a
  session `tests/mpx3-shell` diffs against Linux.

## 2. Inputs, verified (2026-10-08, from origin)

| input | found |
|---|---|
| pax trunk | `396c5fb` (px14 merged, PR #17), as the contract says; trunk CI green at `396c5fb` (run 37738756822, every job) |
| the shell image | `~/scratch/wolf/pax-shell/pax-shell.iso` `379b737d…`, `shasum -c SHA256SUMS` OK; its `/bin`: `cat echo false head ls pelt sleep true wc`, `ls` busybox-static's (px14's boot log on nomad-1: `initramfs: file 2124608 bin/ls`) |
| `user/boreutils.pin` | `2f15585` (boreutils' own pin then: wolf 0.2.23 / lupin 0.1.46), as the contract says |
| boreutils trunk | `50d8907` (bu18 merged: `src/ls.lu`; `wolf-toolchain.toml` at wolf 0.2.25 `6710f9e0`, lupin 0.1.48, wolf-std `0f74ec5`). bu18 ran its `ls` on PAX at `d90f90a` under px12's harness (`notes/bu18/pax-mpx3-with-ls.patch`: twelve `ls` lines, B1–B5 PASS on four legs) |
| boreutils' `ls` without a terminal | one name a line by default (terminal detection waits for wolf 0.2.26's `os_isatty`, bu18 note); `-l`, `-i`, `-s`, `-U`, `-f` and the rest of bu18's deferred list refused by name, status 2 |
| `ls /` against Linux | **differs under the Linux harnesses as they are**: `tools/linux-run` and `tools/linux-tty --root` mount `/proc` in the chroot (`linux-tty` lines 120-128 create `DIR/dev` and `DIR/proc`), PAX has no `/proc`; bu18 measured `bin dev etc` on PAX against `bin dev etc proc` on Linux |
| busybox in pax | `tests/mpx3-shell` (`/bin/ls`), `tests/mpx3-boreutils` (`/bin/busybox`, three run-list lines), CI's apt lists in the `mpx3-boreutils` and `mpx3-shell` jobs, `PAX_BUSYBOX`; nothing else runs it |
| the `user:` narration | `kernel/process` `describe_elf` (`user: exec pid …`), `kernel/user` the exit line (`… exit_group <s> after <r> runs`), the once-per-call `-ENOSYS` line, refusals, `-EBADF`/`-EFAULT` on a bad write, the tty ioctl refusal, `killed:`; `kmain_console`'s `user: frames free …` after each run-list line. No setting turns any of them off |
| a kernel command line | none: `boot/start.S` asks Limine for bootloader info, firmware type, memory map, HHDM, executable address and modules; `boot/limine-initramfs.conf` gives no `cmdline`. Limine's `PROTOCOL.md` (`3a0526b7`) has the Executable Command Line feature (id `0x4b161536e598651e, 0xb390ad4a2f1f303a`; response `{revision, cmdline}`); `CONFIG.md` (v12.9.1) the entry key `cmdline` |
| pelt | trunk `dd22a86`, the pin; its README claims functions and every expansion (arithmetic included); pipelines, redirections, `cd` refused by name |
| kasumi | `px13-ubuntu` podman image (Ubuntu 24.04, glibc 2.39); `/home` 96% (47 GB free); QEMU 11.1.1, TCG |
| nomad-1 | QEMU 11.1.1 (Homebrew) |

## 3. Prediction (committed before the first change)

### P1. The image's `/bin` after the swap

`cat echo false head ls pelt sleep tail true wc` — ten programs, all
built by wolf: pelt `dd22a86`, and boreutils `50d8907`'s nine (`tail`
added for the session's `head`/`tail`). No busybox anywhere in the
image, the tests or CI's apt lists.

### P2. The session diffs

- Against Linux (the same binaries, `tools/linux-tty --root --pid1`):
  **empty, every session, every leg** (both tiers, BIOS and UEFI),
  after `linux-tty` stops mounting `/proc` in the chroot (the one
  harness asymmetry `ls /` sees). Nothing pelt, boreutils or procs runs
  reads `/proc`, so the three px14 sessions' Linux transcripts do not
  move when the mount goes (a named guess).
- Against px14's PAX transcripts: `shell-serial` and `shell-ps2`
  differ **only in `ls /bin`'s output**: busybox's one row (`cat    echo
  false  head   ls     pelt   sleep  true   wc`) becomes ten lines, one
  name each (boreutils' `ls` has no terminal detection at 0.2.25), with
  `tail` among them. Every other line is unchanged, `pelt: line 7:
  nosuch: not found` included. `procs` is unchanged.
- `mpx3-boreutils`: its three busybox lines become boreutils' `ls`
  (`ls /bin /etc`, `ls /etc` beside the sleeper, `ls -a /etc`) plus
  bu18's twelve; byte-identical to Linux; no system call outside
  -ENOSYS 273/334 (bu18 measured none).

### P3. The quiet setting

`quiet` on the kernel command line (Limine's `cmdline`): the console
prints no `user: exec`, exit, `-ENOSYS` or `frames free` line; one
boot line says the setting is on; refusals, faults and bad buffers
still print. Every test kernel boots without it and narrates as today.
The quiet leg's session (everything pelt and its children print) is
byte-identical to Linux's, as the narrating legs' is. Seen red first:
the test lands before the kernel change, and CI fails on exactly the
quiet legs.

### P4. Boot to the prompt on nomad-1

The quiet image, BIOS, TCG, QEMU 11.1.1: **2.0 s ± 0.4** from the
command to pelt's `$ ` (px14's image: 1.6 s), the initramfs about 20
MB larger (`ls` 2.1 → ~11.9 MB, `tail` ~11.9 MB added) and loaded by
Limine before the kernel starts. Falsified outside 1.6–2.4 s.

### P5. The brief's session (added 2026-10-08, the orchestrator's brief, before any of it ran)

The brief replaces item 3's command list. A new typed session,
`shell-howl` (`user/console/shell-howl.keys`), types exactly:
`cat /etc/motd`, `ls /bin`, `echo $((6 * 7))`, `howl() { echo
"a${1}ooo!"; }`, `howl wwwww`, `wc /etc/motd`, `teleport`, `echo $?`,
then Ctrl-D at the empty prompt. The shell image's `/etc/motd` becomes
`PAX. Kernel: wolf. Shell: wolf. Tools: wolf. Nothing here existed last
year.` and a newline (77 bytes, 12 words). Predicted, on Linux and on
PAX alike (the session diff empty on every leg, quiet and narrating):

- `cat /etc/motd`: that line;
- `ls /bin`: `cat echo false head ls pelt sleep tail true wc`, one a
  line;
- `echo $((6 * 7))`: `42`;
- the definition prints nothing; `howl wwwww`: `awwwwwooo!`;
- `wc /etc/motd`: ` 1 12 77 /etc/motd` (the widths px14's ` 1 15 81`
  had);
- `teleport`: `pelt: line 7: teleport: not found` (the seventh line
  pelt read), then `echo $?`: `127`;
- Ctrl-D: pelt ends with status 0; `PAX: init /bin/pelt ended with
  status 0; nothing left to run`, `halt`.

Falsified by any line of it differing between PAX and Linux, or by
pelt answering any of it otherwise (then reported, not changed).

The Linux side run beside PAX: the same tree under `podman run -it
--rootfs` (pelt pid 1, a pseudo-terminal, the same environment) on
kasumi, reached from nomad-1 by `ssh -t`: nomad-1 has podman but no
podman machine and 20 GiB free, and no lane installs on it. Its
transcript, carriage returns removed, from the first prompt to the
last, equals PAX's (a named guess: the two terminals differ in ISIG
and IXON only, which nothing typed here reaches).
