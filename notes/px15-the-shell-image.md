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

### §3 against what was measured

| predicted | measured |
|---|---|
| P1: `/bin` = `cat echo false head ls pelt sleep tail true wc`, all wolf-built, no busybox in the image, tests or CI | **right** (`notes/px15/session-shell-howl.pax.txt` lines 3-12; boreutils `50d8907` built in `px13-ubuntu`: `ls` `e177ec39…`, bu18's sha; pelt `1e2535d7…`, px13's; `grep -i busybox` finds it only in history comments) |
| P2: after `linux-tty` stops mounting `/proc`, the px14 sessions' Linux transcripts do not move (nothing reads /proc) | **wrong**: without `/proc` every boreutils child failed `cat: standard output: Bad file descriptor`: boreutils opens `/dev/stdout`, which on Linux is a link into `/proc/self/fd` (strace of the harness, `openat("/dev/stdout") = -ENOENT`). `4c39733` reverted by `fc60a70`; the chroot keeps `/proc`, so `ls /` stays out of every session (the brief dropped it anyway) |
| P2: every session's diff against Linux empty, every leg | **right**: all six sessions, both tiers, BIOS and UEFI (kasumi a3 at `4053a40`, 129 PASS; CI run 37950564695 at `bad40dc`, 129 PASS); `notes/px15/session-*.{pax,linux}.txt` `cmp` equal (the quiet sessions against their namesakes' Linux transcripts) |
| P2: against px14, shell-serial and shell-ps2 differ only in `ls /bin` | **wrong by the brief**: also the motd line and `wc /etc/motd` (` 1 12 77`), because the brief changed `/etc/motd` after P2 was written (P5 named it). `ls /bin`: busybox's one row became ten lines with `tail`, as predicted. procs unchanged (`cmp` with `notes/px14/session-procs.pax.txt`) |
| P2: mpx3-boreutils byte-identical with boreutils' `ls`, no new -ENOSYS | **right**: 29 commands, B1-B5 PASS on four legs (CI job 113887937920, 21 PASS) |
| P3: `quiet` on the command line silences exec, exit, -ENOSYS, frames; one boot line; refusals and faults still print; test red first on exactly the quiet legs | **right**: CI run 37778469142 at `172f470` red on S1, S2, S4 of the four `shell-howl-quiet` legs only (`notes/px15/ci-37778469142-mpx3-shell-172f470.txt`); green after `eee6e7b`..`ee36b29`. **Not predicted**: `tools/qemu-halt --type` counted prompts only after the first `user: exec pid` line, so a quiet kernel's prompt never counted (CI runs 37779372777, 37779583637 red: `prompt 1 ('$ ') did not come`); fixed in `4053a40` (count from `run 1:` too) |
| P4: boot to the prompt on nomad-1 2.0 s ± 0.4 | **right: 2.0 s** (2.02, 2.05, 2.08, 2.1 s in four boots; the preflight 2.1 s). A fresh interactive fish in a pseudo-terminal that answers no terminal queries waits 10 s before its first command; a real terminal answers, so the timings start after a first command |
| P5: every line of the brief's session as written, on Linux and PAX alike | **right, every line**: `user/console/shell-howl.expect` (Linux, kasumi `px13-ubuntu`) is P5's text; `pelt: line 7: teleport: not found`, `127`, `awwwwwooo!`, `42`, ` 1 12 77 /etc/motd` |
| P5: the Linux side under `podman run -it --rootfs` on kasumi over `ssh -t` equals PAX's, ISIG/IXON never reached | **right**: from nomad-1, its transcript cut from the first `$ cat` to `127` equals PAX's (`1934ecd0…`, 24 lines each) and equals the expect file's first 24 lines |

## 4. Evidence index

- **The quiet test red then green**: red, CI run **37778469142** (job 113315250529) at `172f470` (the test before the kernel change): 12 FAIL lines, all `shell-howl-quiet` S1/S2/S4 (`notes/px15/ci-37778469142-mpx3-shell-172f470.txt`); kasumi a1 the same. Green: kasumi a3 at `4053a40` (129 PASS, 0 FAIL, 24 boots, TCG), CI run 37948767105 at `4053a40` and **37950564695 at the head `bad40dc`**, every job green (mpx3-shell 129 PASS, mpx3-boreutils 21, mpx3-console 101, tour 44; no SKIP).
- **Planted break**: `3a414ea` (quiet hides a system call's refusal too), predicted red on exactly procs-quiet S4, four legs: CI run **37949636654** (job 113884754004), red on exactly those four (`notes/px15/ci-37949636654-mpx3-shell-plant-3a414ea.txt`, 125 PASS, 4 FAIL); reverted `3244f79`. The code at the head is `4053a40`'s: `git diff 4053a40 bad40dc -- kernel boot user tools tests .github` is empty.
- **Session diffs** (empty): `notes/px15/session-{shell-serial,shell-ps2,shell-howl,procs}.{pax,linux}.txt`, `session-{shell-howl,procs}-quiet.pax.txt` (kasumi a3, native BIOS); every leg in CI's S2.
- **The tour**: `tests/tour` on kasumi at `8dde82d` (kernel code as the head): 45 PASS, rc 0; the ISOs changed (`ad646ec1…`, `3ddf288b…`; px14's `dd2e76e6…`, `788471df…`): the image 404 → 408 KiB, frames −3, ending b's `rip` `0xffffffff80022eb2`. The tour's folder refreshed and its preflight GO (the PANIC line in 29 s).
- **The shell image**: `console-shell-quiet.iso` (native) of kasumi a3 at `4053a40`, sha256 `6903ece11464543546217418fea252e78af6e084ded6700c683beb7add62fb55`; boots to pelt's prompt in 2.0 s on nomad-1 (QEMU 11.1.1, TCG).
- Sources consulted: `docs/SOURCES.md` § px15.

### Drift from the contract, reported

1. The orchestrator's brief (2026-10-08) replaced item 3's command list: `ls /`, `head`/`tail`, `false; echo $?`, `sleep 1` and `exit` are not in the session; the howl session is. `head`, `tail` and `false` stay in `/bin` and in mpx3-boreutils' and shell-serial's sessions.
2. The session ends with Ctrl-D, not `exit` (the brief's beat 9).
3. `ls /` is in no session: Linux's chroot needs `/proc` for boreutils' `/dev/stdout`, and PAX has no `/proc`, so `ls /` cannot agree under the harness (bu18 measured the same).
4. The note was first committed under its contract's name, with words this repository does not use; renamed and reworded in `b54b93a`/`9766071` (history keeps the first wording).

## 5. Done-when

- Branch `px15` on origin; PR wolffe-lang/pax#18, open, unmerged; CI green at the head (run 37950564695).
- `/bin` all wolf (boreutils' `ls`), busybox gone from the image, the tests and CI's apt lists; `user/boreutils.pin` at `50d8907` in its own commit (`7b4bf70`).
- `quiet` on the kernel command line, off in every test kernel, on in the shell image; `tests/mpx3-shell` proves both (narrating legs: no `user: quiet`, every exec/exit line; quiet legs: one `user: quiet`, none of them, refusals and the fault still printed).
- Close nothing. To close: none (no pax issue names this work).
