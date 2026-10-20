# px54 — lope on PAX (ruling #91 R4; the pelt hook)

Contract: px54's, `sprints/pax/54-lope-on-pax/px54-lope-on-pax.md` in
wolffe-lang/wolf (planning trunk `c2bf9b3`, read 2026-10-20 from
`origin/trunk`), px51's shape, under `sprints/RULES.md`. Branch `px54`
in pax, cut from pax trunk `c8b48cb` (px53). §1 to §3 are committed
before the first change to a pin, the kernel, a tool, a probe or a test,
and before the first measurement.

One deliverable: **lope preinstalled in PAX's image** (`/bin/lope`, the
static binary by digest) and the no-prefix jump working at the console:
the pins (`user/lope.pin`, `user/pelt.pin` to sh21's `90d7c64`), the
console shell running lope's hook before its first prompt, a typed
session held byte for byte to the same binaries in a Linux container as
root and as `pax`, what lope asks of PAX, plants, the playground image
refreshed for the maintainer.

## 1. Forbidden, absolutely

- No kernel's source is read or searched for, Linux's above all, nor any
  libc's, shell's, terminal driver's, container runtime's or init
  system's (ruling #22; RULES.md §1). No jumper's or matcher's source:
  nucleo, fzf, skim, zoxide, autojump, z, fasd (ruling #91 R3); lope and
  pelt are the maintainer's and are read and cited as such (lope
  `5ac37df`: `src/cmd/init.lu`, `src/db/paths.lu`, `src/db/store.lu`,
  `shell/pelt/*.sh`, `shell/posix/menu.sh`, `tools/mkstatic`,
  `notes/lp00-the-port.md`; pelt `90d7c64`: `src/sh/interact.lu`'s
  `$ENV`, `notes/sh21-the-hook.md`). Facts about Linux come from the man
  pages (`strace(1)` as documentation, `environ(7)`, `execve(2)`), POSIX
  .1-2024 (XCU 2.5.3 `ENV`, 2.9.1 command search, `cd`, `read`), the
  allowed uapi headers and syscall table, pax's own source and notes,
  and black-box runs: the same static binaries on a pseudo-terminal in a
  throwaway container (`tools/linux-tree`), and `strace -f` of lope's
  own runs in `px13-ubuntu`. `wolf/refs/repos/linux` stays sparse and is
  not opened. No word implying filming.
- Every check gets a user row: the session as root and as `pax`
  (1000:1000). Signals and id changes only inside QEMU or a container.
- Probe and test binaries static, built in `px13-ubuntu` on kasumi,
  never with kasumi's CachyOS glibc (AVX-512). No build on nomad-1.
  kasumi under `bash`, long jobs `setsid -f` with a pid file, ended by
  that pid only; work under `~/lanes/px54/`, pruned (kasumi `/home` 23
  GB free at the start); never `/tmp`. Boots under `taskset -c 0-3`.
  Ports 8080 and 8088 unused; nothing installed on any host.
  `~/lanes/orch-paxplay/` is touched only as item 5 says (its two
  scripts gain lope); every other lane's directory untouched.
- Toolchains from release archives by digest, each read twice: pelt's
  own wolf 0.2.32 (`4c37f9c5…`, release 416327027, 80,092,071 bytes),
  lope's own wolf 0.2.33 (`4f955e8d…`, release 417610226, 80,128,936
  bytes); the kernel's pin (wolf 0.2.33 / lupin 0.1.54) unmoved.
- No `rm` outside `~/lanes/px54/` and this worktree; no `git add -A`;
  nothing under `~/.claude`; no merge, no tag; no issue filed or closed
  (listed); no `2>/dev/null` on a checkout; no trailer on a commit or the
  PR. No other lane's run cancelled (px55 and tl29 run beside); a plant
  by dispatch, `-f tier=pr` with its suite; the PR opened without the
  label, `full-matrix` added at the final head. "Seen red" cites a run.
  No assertion deleted or weakened, no timeout or retry as a fix.
  **lope is private and pax public**: nothing of lope's source enters
  this repository, and no lope binary is uploaded as a CI artifact (the
  sums only). If the harness refuses an action I stop and report.

## 2. Inputs, verified (2026-10-20)

| input | found |
|---|---|
| pax trunk | `c8b48cb` (px53, PR #92 merged); its push run 39483165678 queued at the time of reading; px55's plant dispatches and tl29's PR #97 (the merge gate) running beside; open issues #55, #56, #62, #67, #88–#91, #93–#96 (none this lane's) |
| planning repo | `c2bf9b3` (the contract), `ee935be` after it (crawl 54: px53 merged, px54 launched); ruling #91 R4, ruling #96 (lp00's disagreements kept), ruling #98 (`command NAME` calls no handler) |
| lope | private (`gh repo view`: PRIVATE). Trunk `5ac37df22866…` (lp00's merge); `git diff ee97741 5ac37df -- src` empty, so the source is lp00's final. Its own toolchain: wolf 0.2.33 `4f955e8d…`, version line `wolf 0.2.33 (wolfgang, pin 85dab5d)`, wolf-std `cceda631…`. lp00's static, `tools/mkstatic` in `localhost/px13-ubuntu` (Ubuntu 24.04.5, libc6-dev 2.39-0ubuntu8.9) twice: **`f9a2f064077f6bb33ede9219608b6fe72d4a45a66c84f61f3f9d9e5e94f5066c`, 14,426,728 bytes**, ET_EXEC, no PT_INTERP; CI's runner builds another (its `libc.a`). Build: `wolf build --release --no-cache --deny-warnings src/lope.lu` with a `cc` that adds `-static` first on `PATH` (`tools/build --static`): `tools/mkpelt`'s shape exactly |
| lope's pelt text | `lope init pelt` (`src/cmd/init.lu`, `--hook pwd` the default): `__lope_hook` (`command lope add -- "$PWD"`), a `cd` function that records, `g` (alone: `cd ~`; `-`: `cd -`; a directory; else `lope query --cwd`, then `lope query`), `gi` (fzf when `command -v fzf` finds it, else `__lope_menu`: at most nine `N) PATH` lines and `lope: which? ` on standard error, one digit read), `command_not_found_handle` (a directory, then the cwd's match, then the store's; 127 when none) |
| lope's store | `$LOPE_DATA_DIR`, else `$XDG_DATA_HOME/lope` (an absolute one), else `$HOME/.local/share/lope`, `/` for an unset or empty `HOME` (`src/db/paths.lu`); written whole to `FILE.tmp.PID`, then renamed over (`src/db/store.lu:126`; no fsync at 0.2.33, ruling #96 D9); `lope list` prints the paths most frecent first, ties by frecency, then the shorter path, then byte order |
| pelt | trunk `90d7c64` (sh21 merged, pelt#43); `git diff 6bf7d2a 90d7c64 -- src` empty; its own toolchain wolf **0.2.32** `4c37f9c5…` / lupin 0.1.54 / wolf-std `d37c911` (as `be1a75d`'s). sh21's static with pax `d733bf4`'s `tools/mkpelt` (the same file at `c8b48cb`) in `ubuntu:24.04` with `ld.lld`: **`5448cb27d882553bccba66dbde2c4aaba417a7501ae1c6bf3944af0d00a93c5d`, 15,201,640 bytes**; 49 calls by name, all in sh19's 50. `command_not_found_handle` in the current environment, interactive only, never re-entered, 127 said as pelt's own `NAME: not found` |
| how pelt reads a start-up file | `$ENV` (XCU 2.5.3): an interactive shell expands it and runs the file before its first prompt, a file that cannot be read passed over silently (`src/sh/interact.lu:262`, `run_env_file`). pelt reads no `/etc/profile` and no rc file of its own |
| PAX's console shell | `kmain_console` runs `/etc/pax-run`, one command a line, words split at single spaces, the environment fixed in the kernel: `HOME=/ TERM=linux PAX=1 PATH=/bin` (`kernel/kmain_console.lu:56`). No `ENV`. The playground's `/etc/pax-run` is `/bin/sh -i -m` (`~/lanes/orch-paxplay/assemble.sh`), root's home `/`, `pax`'s `/home/pax` (1000:1000, 0755) in its `/etc/passwd`; `su pax` keeps the environment but sets `HOME`, `SHELL`, `USER`, `LOGNAME` (`user/su/su.lu:27`) |
| `as` | `user/elf/as.c`: the ids, then `execve` with the caller's environment (`HOME=/` kept) |
| boreutils | `cc64f68` (pinned since px53); `env`, `ls`, `true` among its 47 |
| the harness | `tools/linux-tree` (one program on a pseudo-terminal as pid 1 of a fresh pid namespace in a throwaway container, the tree a tmpfs, `--owners`); `tools/linux-tty` and `tools/qemu-halt` type the same keys format (a step waits for the k-th prompt; `^~` a step typed a pause after the one before, 1.5 s on Linux, `PAX_TYPE_PAUSE` default 2 s on PAX) |
| pax CI and lope | pax is public, lope private: the default token cannot read lope. lobo (public) reads the org's private siblings with `secrets.WOLF_CI_TOKEN` (its `acquire-toolchain` action: absence is failure); whether that secret reaches pax and lope is not known before a run (listing the secrets was refused by the harness, reported) |
| kasumi | Linux 7.2.8-1-cachyos, 16 cpus, load 7.6 (other lanes), QEMU 11.1.1, `/home` 23 GB free, `px13-ubuntu` `ad8964505189` (strace, ld.lld, clang, gcc, git); no git access to lope (a bundle of `5ac37df` copied from nomad-1, sha256 `f0e7390a…`) |

## 3. Prediction (committed before the first change and measurement)

**P1. The pins**, each its own commit: `user/lope.pin` (new: lope's
repository and `5ac37df`, the digest and the image it was built in
beside it) and `tools/mklope` (new, `tools/mkpelt`'s shape: lope's tree
at the pin, its own `wolf-toolchain.toml`'s archive by digest and std by
commit, `wolf build --release --no-cache --deny-warnings src/lope.lu`
through a `cc` that adds `-static`, ET_EXEC and no PT_INTERP checked,
`lope <sha256> <bytes>` in `sums.txt`; the tree from `PAX_LOPE_REPO`
when set, a local clone, since lope is private); `user/pelt.pin` to
`90d7c64`. **The kernel unchanged**: no file under `kernel/` or `boot/`
moves.

**P2. The binaries**, in `px13-ubuntu` on kasumi, each built twice:
lope by `tools/mklope` **`f9a2f064…` (14,426,728 bytes), lp00's** (the
same source, toolchain, flags, linker wrapper and image as
`tools/mkstatic`; weak: `-o`'s path, which lope's tool gives relative);
pelt by `tools/mkpelt` **`5448cb27…` (15,201,640 bytes), sh21's**. CI's
runner builds its own of each (its `libc.a`), the same in every CI run.

**P3. The hook, with no kernel change.** `/etc/pax-run`'s console shell
becomes `/bin/env ENV=/etc/shrc /bin/sh -i -m` (boreutils' `env` puts
`ENV` in the shell's environment; the kernel's `HOME=/` and no XDG
variable stay), and `/etc/shrc` is `eval "$(lope init pelt)"`: pelt runs
it before its first prompt, so `cd`, `g`, `gi` and
`command_not_found_handle` are defined there, and `ENV` is inherited by
a shell started from it (`exec sh`, `su pax`). The store is
`/.local/share/lope/store` for root, in PAX's in-memory tree.

**P4. The typed session** (`user/console/lope.keys`), in a new suite
**`tests/mpx5-lope`**, not a new mpx5-jobs image. Argued: its reference
is a live container of the same binaries for root's rows and the user's
(the contract's), where mpx5-jobs holds root's rows to real root's
recordings under QEMU; its one dependency that needs a credential (lope
is private) then reds one job by name, never job control's; mpx5-jobs
is the longest job of a full run (65 of 120 minutes) and a lope change
need not run it; a plant needs `-f suites=mpx5-lope` only. One image
`lope` (kmain_console; `/bin/pelt` and `/bin/sh` pelt, `/bin/lope`,
boreutils' `env`, `ls`, `true`, `/bin/as`, `/etc/shrc`, `/home/pax`
1000:1000), two runs: root's `/bin/env ENV=/etc/shrc /bin/sh -i -m`, and
`pax`'s `/bin/as 1000 1000 /bin/env HOME=/home/pax ENV=/etc/shrc /bin/sh
-i -m` (`as` keeps `HOME=/`, under which a user cannot make
`/.local`; `pax`'s home is the one `su pax` gives). The keys, the same
for both: `cd /etc`, `cd /bin`, `lope list`; `etc` alone, `pwd`; `g -`;
`ls` (bare); `g` alone, `pwd`; `gi`, then `2` at the menu, `pwd`;
`true; echo st=$?`; `zzqqxx; echo st=$?`; `exec sh -i -m` (a second
shell, the first gone); `lope list`; `bin`, `pwd`; `exit`. Predicted on
both sides: `lope list` prints `/bin` then `/etc` (a tie at one visit
each, broken by byte order); `etc` lands in `/etc`; `g -` prints `/bin`
(POSIX `cd -`); `ls` lists `/bin`; `g` lands in `$HOME` (`/`, or
`/home/pax`); the menu is `1) /bin`, `2) /etc`, `3) $HOME` and `lope:
which? `, `2` lands in `/etc`; `st=0`; `zzqqxx: not found` in pelt's
words and `st=127`; the second shell's `lope list` is `/etc`, `/bin`,
`$HOME` (the store written by the first shell, read by the second);
`bin` lands in `/bin`. **Byte-identical on PAX to the container's, as
root and as `pax`, at the first boot, with no kernel change**, each
row's witness present. Weak: the menu's digit is typed a pause after
`gi` (no prompt to wait for): on PAX under TCG the pause must outlast
two `lope query` runs, so the suite sets `PAX_TYPE_PAUSE` from a
measurement, with a wide margin.

**P5. What lope asks of PAX.** `strace -f` of lope's own runs on Linux
(`init pelt`, `add`, `query --cwd`, `query`, `query --all`, `list`, the
store missing and present) names, as a static glibc wolf program:
`execve`, `brk`, `arch_prctl`, `set_tid_address`, `set_robust_list`,
`rseq`, `prlimit64`, `mprotect`, `mmap`, `munmap`, `getrandom`,
`readlinkat` or not, `rt_sigaction`, `rt_sigprocmask`, `sigaltstack`
(the runtime's stack guard), `openat`, `read`, `write`, `close`,
`fstat`/`newfstatat`/`statx`, `getdents64`, `getcwd`, `readlink`,
`mkdir`, `rename`, `unlink` or not, `clock_gettime`, `getpid`,
`exit_group`, perhaps `ioctl`, `futex`, `madvise`. **Every one served by
PAX but `set_robust_list` (273) and `rseq` (334)**, which glibc's start
copes with: no new system-call number, no `refused:` line, in any boot.
No kernel change.

**P6. Plants**, each a branch never merged, one commit, by dispatch
`-f tier=pr -f suites=mpx5-lope`: **A, the image without the hook** (the
run lines' `ENV=/etc/shrc` gone): red at the jump rows as root and as
`pax` (`etc`, `g`, `gi`, `bin`: `NAME: not found`, 127; the shell stays
put), and at the store rows (`cd` is the built-in, nothing is recorded:
both `lope list`s print nothing); the container agrees with PAX (both
lose the hook), so the byte comparison stays green and the witnesses
are what go red. **B, the store's path unwritable** (`/.local` and
`/home/pax/.local` regular files in the tree): every `cd` prints lope's
I/O error, both `lope list`s print nothing (red at the store rows), and
the jumps that need the store (`etc`, the menu, `bin`) are not found;
weak: whether PAX's error for a `mkdir` under a file is Linux's
(ENOTDIR), which the comparison would then also show.

**P7. The pelt pin moves no recording**: sh21's hook runs only where
`command_not_found_handle` is defined, which no existing session does,
and its static makes no call sh19's did not. On kasumi (native BIOS,
`taskset -c 0-3`) every suite that builds pelt is green at `90d7c64`:
mpx5-jobs (the 52 pjobs runs and groups as recorded), mpx3-shell,
mpx3-tree, mpx5-accounts, mpx3-console, mpx3-screen, mpx3-speaker; no
fixed reference moves.

**P8. The playground**: the orchestrator's `build.sh` gains
`tools/mklope` and `assemble.sh` `/bin/lope`, `/etc/shrc` and the hook
line (`/etc/pax-run` `/bin/env ENV=/etc/shrc /bin/sh -i -m`), its motd
naming lope; a new `pax-playground.iso` digest, smoke-booted, copied to
nomad-1 `~/pax-playground/` and hashed twice there.

**P9. CI.** The new job checks lope out at the pin with the org's
`WOLF_CI_TOKEN` (lobo's shape: absent or refused is a red job with the
reason, never a skip). Not known before the first run: whether that
secret reaches pax and reads lope. If it does not, `mpx5-lope` is red by
name and a ruling is asked (the secret granted to pax, or lope made
public); nothing is routed around.
