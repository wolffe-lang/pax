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

**P6, by row** (added after the first boot, before either plant ran;
the rows are tests/mpx5-lope's L2 and L3). **A**: L2 red at `etc`, `g -`,
`g`, `gi`'s menu and the second shell's `bin`; green at `ls` (the
built-in `cd /bin` still moved the shell), `true` and `zzqqxx`; L3 red
at both store rows; L4 green. The menu's digit becomes a command line
of its own (`2: not found`), so every later step is typed a prompt
early: L1 may then part from the container's on type-ahead echo, a
plant's noise. **B**: L2 red at `etc` (not found: the store cannot be
read), `g -` (the jump never moved the shell, so `cd -` goes back to
`/etc` and prints it), `ls` (it lists `/etc`), `g` (lope's I/O error
between `g` and `pwd`), `gi`'s menu and `bin`; green at `true` and
`zzqqxx`; L3 red at both; L4 green; L1 as A's. (Corrected before
either plant ran: the first text had B's `g -` and `ls` green.)

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | the pins and the hook, each its own commit; the kernel unchanged | `user/lope.pin` `85b7778` (with `tools/mklope` `6bcb188`), `user/pelt.pin` `93b65ca`, the hook `user/shrc` `3ad15ae`; `git diff c8b48cb HEAD -- kernel boot` is empty | right |
| P2 | lope `f9a2f064…` and pelt `5448cb27…` in `px13-ubuntu`, twice each | lope **`f9a2f064…`** (14,426,728) and pelt **`5448cb27…`** (15,201,640), each in two builds, the same bytes (§B); pelt at trunk's pin first gave sh19's `7be05ec0…` twice; every suite build since gave the same two | right |
| P3 | the hook through `env ENV=/etc/shrc`, no kernel change; `ENV` inherited by `exec sh` and `su pax` | so: the second shell (`exec sh -i -m`) and the playground's `su pax` both run the hook (§D, §I) | right |
| P4 | the session byte-identical to the container's as root and `pax` at the first boot, every row's witness; the menu's pause a race to size | **byte-identical at the first boot** (36 lines each, root and `pax`), L2's first text wrong in two of its own lines (`ls` prints columns on a terminal; pelt's not-found carries the line number 98, the hook's text counted), fixed in the suite before any commit of it; every row as predicted. The pause is no race: the same bytes with the digit 0.2 s after `gi` (§D) | right on PAX and Linux; wrong on the pause (in the safe direction) |
| P5 | the census's names; every one served but 273 and 334 | **23 calls by name** (§E): no `mmap`, no signal call, no `sigaltstack`, no `clock_gettime` on Linux (the vDSO's); every one is in PAX's table; L4 on every boot: -ENOSYS 273 and 334 only, no `refused:` | right in the verdict, the list longer than lope asks |
| P6 | plants A and B red at L2 and L3 by row, L1 noise | A and B red at exactly the rows predicted, on kasumi and in CI (runs 39650231203, 39650235303; §F) | right |
| P7 | the pelt pin moves no recording; the pelt suites green on kasumi | mpx5-jobs' pelt images (52 pjobs runs, groups as root and `pax`) and gaps, fds, sigs: every J PASS; mpx3-shell, mpx3-tree, mpx5-accounts, mpx3-console, mpx3-screen, mpx3-speaker PASS (§G) | right |
| P8 | the playground refreshed with lope, a new digest, on nomad-1 | **`cc15c60224f910f671bbc08df344c50d04aad455fb7dcd0f3dbb9bd2bdc27214`** (71,751,680 bytes), smoke-booted, on nomad-1, hashed twice (§I) | right |
| P9 | the token: unknown | **absent for pax** at first: `Input required and not supplied: token` (run 39488153518), then said by name in its own step; ruling px54-R1 (a): the maintainer set a read token as pax's `WOLF_CI_TOKEN` (§H) | asked, ruled |

## A. The pins and the hook (item 1)

- `user/lope.pin` (`85b7778`): lope's repository and `5ac37df`, the
  digest and the image it was built in. lope is private, so
  `tools/mklope` (`6bcb188`) takes the tree from `PAX_LOPE_REPO` when it
  is set; it is `tools/mkpelt` with lope's names, a fetch that says why
  it fails, and a `lope --version` run after the link.
- `user/pelt.pin` (`93b65ca`): `90d7c64` (sh21), its paragraph beside
  px53's.
- The hook (`3ad15ae`): `user/shrc`, which the image installs as
  `/etc/shrc`: `eval "$(lope init pelt)"`. The console shell's line is
  `/bin/env ENV=/etc/shrc /bin/sh -i -m`: boreutils' `env` puts `ENV` in
  the environment, the kernel's fixed `HOME=/ TERM=linux PAX=1
  PATH=/bin` (`kernel/kmain_console.lu:56`) is kept, and pelt runs the
  file before its first prompt (`src/sh/interact.lu:262`). pelt reads no
  other start-up file, and a kernel that set `ENV` would have been a
  kernel change; `env` needs none. `HOME=/` and no XDG variable: root's
  store is `/.local/share/lope/store` (the container's tree after the
  session lists `./.local/share/lope/store` and `./.sh_history`,
  `notes/px54/linux-lope.after.txt`).
- **The kernel unchanged**: no file under `kernel/` or `boot/` moved.

## B. The binaries (item 1)

| program | built by | digest | where |
|---|---|---|---|
| lope (`5ac37df`, its own 0.2.33 / `cceda63`) | `tools/mklope` | `f9a2f064077f6bb33ede9219608b6fe72d4a45a66c84f61f3f9d9e5e94f5066c`, 14,426,728 | `localhost/px13-ubuntu` (`ad8964505189`), two builds the same bytes (`notes/px54/kasumi-bins-lope-twice-pelt-trunk.out`); lp00's `tools/mkstatic` digest, so `tools/mklope` builds what lope's own tool builds |
| pelt (`90d7c64`, its own 0.2.32 / `d37c911`) | `tools/mkpelt` | `5448cb27d882553bccba66dbde2c4aaba417a7501ae1c6bf3944af0d00a93c5d`, 15,201,640 | two builds the same bytes (`kasumi-bins-pelt-90d7c64-twice.out`); sh21's digest; at `be1a75d` (trunk's pin) the same tool gave `7be05ec0…` twice first |
| `env`, `ls`, `true` (boreutils `cc64f68`) | `tools/mkboreutils` | `88faec90…`, `1e34a02a…`, `a3bf0296…` (bu28's) | unchanged pin |

CI's runner builds the **same** lope, `f9a2f064…` 14,426,728 bytes, and
the same pelt, `5448cb27…` (the plants' runs, §F): lp00 saw CI's lope
differ at `ee83f5d` (`08741bfa…`, its runner's `libc.a` then); today's
`ubuntu-latest` links the bytes `px13-ubuntu` links.

## C. Where the session lives

`tests/mpx5-lope`, a suite of its own (§3 P4 argued it): one image
(kmain_console), two runs, the same keys
(`user/console/lope.keys`), the container of the same tree as L1's
reference for root's run and `pax`'s, L2 and L3 each run's own witness
(a plant that breaks both sides alike is caught there), L4 as mpx5-jobs'
J6. Wired as every suite is: its job in `ci.yml`, the `tier` job's
needs, `tools/ci-tiers.map` (`user/lope.pin`, `tools/mklope`,
`user/shrc`, `user/console/lope.keys`; and `mpx5-lope` among `as`'s
users), `tests/ci-plan` (156 PASS on kasumi, two new cases, two moved).

## D. The typed session (item 2)

The container's transcript and PAX's, the same 36 lines as root
(`notes/px54/linux-lope.txt`, `pax-native-bios-lope.txt`, sha256
`b8f4e24c…`):

```
$ cd /etc
$ cd /bin
$ lope list
/bin
/etc
$ etc
$ pwd
/etc
$ g -
/bin
$ ls
as  env  lope  ls  pelt  sh  true
$ g
$ pwd
/
$ gi
1) /bin
2) /etc
3) /
lope: which? 2
$ pwd
/etc
$ true; echo st=$?
st=0
$ zzqqxx; echo st=$?
pelt: line 98: zzqqxx: not found
st=127
$ exec sh -i -m
$ lope list
/etc
/bin
/
$ bin
$ pwd
/bin
$ exit
```

and as `pax` the same with `/home/pax` for `/` (`c7df6c42…`). Held on
kasumi on all four legs (native and release, BIOS and UEFI, TCG,
`taskset -c 0-3`): L1 to L4 PASS, 8 sessions (`kasumi-mpx5-lope.out`),
at the first boot of the image and at every boot since. pelt's line
number 98 counts the lines the hook's text took (the same on both
sides). `lope list`'s first answer is a tie (one visit each) broken by
byte order, as lope's rule says. The menu's digit (`^~2`) was typed 0.2,
0.5, 1, 1.5, 2 and 3 s after `gi` under kasumi's load (12 to 13): the
same bytes each time (`kasumi-first-boot-and-pause-sweep.out`; the
sweep ran the suite's first text, whose `PAX_LOPE_PAUSE` set
`PAX_TYPE_PAUSE`, since removed), so the default pause stands. A whole
boot, two sessions, 44 s under TCG.

## E. What lope asks of PAX (item 3)

`strace -f -n` of lope's own runs on Linux 7.2.8 in `px13-ubuntu`
(`notes/px54/census.sh`; `notes/px54/census/`: each run's calls, their
failures, the union), the runs the hook makes: `--version`, `init pelt`,
`list` with no store, `add -- DIR` making the store and adding to it,
`list`, `query --cwd -- WORD` (a miss and a hit), `query -- WORD`,
`query --all --`, a query with no match, `add` with a file where
`~/.local` is. **23 calls by name**:

| call | nr | runs | on PAX |
|---|---|---|---|
| `execve`, `arch_prctl`, `set_tid_address`, `prlimit64` (RLIMIT_STACK), `readlinkat` (`/proc/self/exe`), `getrandom`, `mprotect`, `brk`, `exit_group` | 59, 158, 218, 302, 267, 318, 10, 12, 231 | every one (glibc's start and end; the runtime allocates by `brk` alone, no `mmap`) | served (px10, px12) |
| `set_robust_list`, `rseq` | 273, 334 | every one | **-ENOSYS**, as for every static glibc program PAX runs (glibc copes); L4's only two |
| `openat`, `read`, `close`, `statx`, `readlink` | 257, 0, 3, 332, 89 | the store read; a path made canonical | served |
| `mkdir`, `getpid`, `rename`, `write` | 83, 39, 82, 1 | `add`: `~/.local/share/lope` made, `store.tmp.PID` written, renamed over | served (px27's tree) |
| `getcwd`, `fstat`, `getdents64` | 79, 5, 217 | `query --cwd`: the working directory's names | served |

No signal call (lope installs no handler and starts no thread), no
`fsync` (wolf 0.2.33 has none: ruling #96 D9), no `mmap`. Not seen on
Linux and made on PAX: `clock_gettime` (228) for lope's clock, which
Linux answers from the vDSO and PAX, which gives no vDSO, as a call
(served since px12; inferred, PAX has no tracer). The failures lope
meets and answers: `openat` ENOENT (no store yet), `mkdir` ENOENT and
EEXIST (`create_dir_all`), and with a file at `~/.local` `openat`
ENOTDIR, which lope reports as `lope: I/O error: Not a directory (os
error 20)` — on PAX too, the same bytes (plant B's lines before its
type-ahead). **Served: all but 273 and 334; refused: none. No kernel
change.**

## F. Plants (item 4)

Branches never merged, one commit each, cut from `dc4c09f` (the suite and the CI as at
that head, before the rebase; `1cabdbc` after it):

| plant | branch, commit | change | kasumi (native BIOS) |
|---|---|---|---|
| A | `px54-plant-a` `e89f87f` | the image without the hook: no `/etc/shrc` (the run lines unchanged: pelt passes over an `ENV` file it cannot read) | **red** on kasumi (`kasumi-plant-a.out`) and in CI, run **39650231203**, mpx5-lope job 119396526045 (`ci-39650231203-plant-a.txt`), the same rows: L2 at `etc`, `g -`, `g`, `gi`'s menu, `bin`, as root and as `pax`; `ls`, `true`, `zzqqxx` green; L3 at both store rows; L4 green; L1 apart on type-ahead (the menu's `2` became a command, every later step typed a prompt early), as predicted |
| B | `px54-plant-b` `2225338` | lope's store path unwritable: a regular file at `/.local` and `/home/pax/.local`, in the tree and the archive | **red** on kasumi (`kasumi-plant-b.out`) and in CI, run **39650235303**, mpx5-lope job 119396590537 (`ci-39650235303-plant-b.txt`), the same rows: L2 at `etc`, `g -`, `ls`, `g`, `gi`'s menu, `bin`; `true`, `zzqqxx` green; L3 at both; L4 green; L1 on type-ahead only: root's first 30 lines, lope's ENOTDIR line among them, are the container's bytes, and `pax`'s run parts at its first line (the root run's early keys spill into it) |

Both dispatched by the orchestrator once the token was set (`gh
workflow run ci -r px54-plant-a -f tier=pr -f suites=mpx5-lope`, and
`-plant-b`), each red in CI at its planted rows, past `WOLF_CI_TOKEN
present` and lope's build: L2 and L3 as on kasumi, L4 green, L1 on
type-ahead.

## G. The suites that build pelt (P7)

kasumi, native BIOS, `taskset -c 0-3`, builds in `px13-ubuntu` at
`dc4c09f`, before the rebase (the code as at the head), every one with pelt `5448cb27…`:
`mpx5-lope` both tiers and both firmwares PASS; `mpx5-jobs`: the 52
pjobs runs and groups as root and `pax` byte-identical to real root's
recordings (J9, J10, 54 PASS), gaps, fds and sigs PASS, 187 PASS lines;
its four busybox images (probe, probe over PS/2, shell, shell-user) were
not built (the lane's cache had no busybox: `tools/fetch-busybox` needs
`zstd`, which `px13-ubuntu` lacks; run on the host after) and are no
pelt image; `mpx3-shell`, `mpx3-tree`, `mpx5-accounts`, `mpx3-console`,
`mpx3-screen`, `mpx3-speaker` PASS (`kasumi-*.out`, `kasumi-chain1.out`,
`kasumi-chain2.out`; every build log names pelt `5448cb27…`). No fixed
reference moved (the console's `.expect` files, the speaker's, the
accounts' recording, the pjobs and groups recordings). CI's
pull-request run runs every suite on the PR leg (the change touches
`ci.yml`): §H.

## H. CI, and lope's privacy (P9)

lope is private and pax public. The job checks lope out at the pin with
`secrets.WOLF_CI_TOKEN`, the org's grant to read private siblings
(lobo's `acquire-toolchain`). **That secret does not reach pax**: the
first dispatch, run 39488153518 (`-f tier=pr -f suites=mpx5-lope`, at
`6e95404`, before the rebase), was red at the checkout, `Input required and not supplied:
token`; since `dc4c09f` (`1cabdbc` rebased) the job says so by name in a step of its own
(`::error title=No WOLF_CI_TOKEN for lope::…`), never a skip. So in CI
the suite cannot build lope, its plants cannot be seen red at their rows,
and no `tier full` could be green. Listing the org's secrets to learn
more was refused by the harness; nothing was routed around. The pull
request's first run, 39497071109 at `840728c` (before the rebase), was every suite green on
the PR leg but `mpx5-lope`, red at the token step. **Ruling px54-R1,
asked**: (a) grant pax `WOLF_CI_TOKEN` (an org secret
visible to pax, with read on `wolffe-lang/lope`) — the smallest change,
lope stays private; nothing of lope's is uploaded, the artifact keeps
its sums and the transcripts — or (b) make lope public (the maintainer's
step), when `tools/mklope` fetches it as `tools/mkpelt` fetches pelt and
the token steps go. Recommended: (a) now, (b) when the maintainer
publishes lope. **Ruled (a)** (2026-10-21): the maintainer made a
fine-grained token with read on lope (and aspen) and set it as pax's
repository secret `WOLF_CI_TOKEN`. The plants then ran (§F) and the
branch was rebased (§L).

## L. The rebase onto `241b322`

pax trunk moved while the ruling was asked: px55 (`/dev/fd`, the limits,
`RLIMIT_CORE` soft 0, mpx4-ready's ways) and tl29 (the one-leg merge
gate: `tier full` is every suite on native BIOS, `tier all` every leg).
`px54` rebased onto `241b322` (the pre-rebase head kept on nomad-1 as
`px54-prerebase`, `840728c`): three conflicts, each two lanes'
paragraphs at one place (`docs/SOURCES.md`, README, CHANGELOG), kept
both, px54's first where the file is newest-first; ci.yml, the tiers
map and `tests/ci-plan` applied clean, and `tests/ci-plan` passes at the
new head (190 PASS); the job's step is named as tl29 names the tiers.
The shas in §4 are the rebased ones (`git log` on the branch). px55's
kernel changes touch nothing lope or pelt calls in the session (no
`/dev/fd`, no limit but `RLIMIT_STACK` read, no core): the pull
request's run at the new head is the measurement.

Then px56 (exec from the tree and `#!`: `kernel/elf`, `kernel/files`,
`kernel/sched`) merged first, and `px54` rebased again, onto `f83d627`
(the head before it kept as `px54-prerebase2`, `b61683a`, whose `tier
pr` run 39651106921 was green and whose labelled full run, superseded,
was cancelled): the same three prose conflicts, kept both (px54's
section after px56's in `docs/SOURCES.md`, px54's paragraph first in
README and CHANGELOG); `tests/ci-plan` 190 PASS. lope and pelt are
archive files, which PAX ran before px56 as after; the session's
measurement at this base is the pull request's run.

## I. The playground (item 5)

The orchestrator's two scripts on kasumi, changed as the contract says
(`notes/px54/playground.sh`, which applies the changes and runs them;
their sha256 before and after in `notes/px54/kasumi-playground.txt`):
`build.sh` gains `tools/mklope` (lope from a clone of its pin inside the
playground's directory, `-e PAX_LOPE_REPO=$L/lope`, since lope is
private); `assemble.sh` gains a stripped `/bin/lope` (as its other
binaries), `/etc/shrc` from `user/shrc`, the hook line
(`/etc/pax-run` `/bin/env ENV=/etc/shrc /bin/sh -i -m`), and two motd
lines naming lope and saying its store is in memory; the first motd line
names `pax px54 39f8597` (the code as at the head then, before the
rebase, `48e5f8c` after it; only notes and prose followed), pelt `90d7c64`. Both rc 0; lope `f9a2f064…`, pelt
`5448cb27…`. **`pax-playground.iso`
`cc15c60224f910f671bbc08df344c50d04aad455fb7dcd0f3dbb9bd2bdc27214`**
(71,751,680 bytes; px53's was `2336718e…`), `pax-smoke.iso`
`11228dcb…`. Smoke-booted once (native BIOS, TCG,
`notes/px54/playground.keys`): root's `cd`s, `lope list`, `etc` alone,
`g -`, `gi` and `1`, `zzqqxx` 127, then `su pax` (HOME `/home/pax`,
`ENV` kept: the hook runs in `pax`'s shell, its own store), `cd /tmp`,
`cd /etc`, `g`, `lope list`, back to root's list, halt. Copied to
nomad-1 `~/pax-playground/pax-playground.iso` over px53's, hashed there
twice.

## J. The kernel's cost

None: no file under `kernel/` or `boot/` changed (`git diff c8b48cb HEAD
-- kernel boot` is empty), so every kernel is px53's.

## K. lope's README (item 6)

Not written here (lope's lane): lope's README gains a PAX line — lope is
preinstalled on PAX as `/bin/lope` at pax's `user/lope.pin`, its hook in
`/etc/shrc` through pelt's `$ENV`, the store in PAX's in-memory tree
until PAX has storage, `gi`'s menu the PAX path.

## 4. Evidence index

Shas are this branch's (`px54`). kasumi paths are under `~/lanes/px54/`.

### What was written

- The prediction: `0049059` (§1 to §3, before any change or
  measurement); the plants' rows `1245f48`, corrected `48e5f8c`, both
  before either plant ran.
- The pins and the hook: `6bcb188` (`tools/mklope`), `85b7778`
  (`user/lope.pin`), `93b65ca` (`user/pelt.pin`), `3ad15ae`
  (`user/shrc`).
- The session and the suite: `cb2e18e` (`user/console/lope.keys`),
  `6a72990` (`tests/mpx5-lope`), `93c4a67` and `1cabdbc` (ci.yml's job,
  the token said by name), `6e9db04` (`tools/ci-tiers.map`), `1fb8aa4`
  (`tests/ci-plan`).
- The words: `079cecc` (`docs/SOURCES.md`), `316db4b` (README),
  `5f3d736` (CHANGELOG), and this note.
- The scripts: `6710809`, `57407d6` (`notes/px54/*.sh`, the
  playground's keys).
- The plants: `px54-plant-a` `e89f87f`, `px54-plant-b` `2225338` (on
  origin, never to be merged).

### What was measured, and where it is

- **The archives**: wolf 0.2.33 `4f955e8d…` and 0.2.32 `4c37f9c5…`, the
  release API read twice (§1); `tools/mklope` and `tools/mkpelt` check
  each download against them.
- **The binaries**: `notes/px54/kasumi-bins-lope-twice-pelt-trunk.out`,
  `kasumi-bins-pelt-90d7c64-twice.out`; every suite's build log.
- **The session**: `notes/px54/linux-lope.txt`, `linux-lope-user.txt`
  (the container), `pax-native-bios-lope.txt`,
  `pax-native-bios-lope-user.txt` (PAX), the same bytes;
  `linux-lope*.after.txt` (the store's files); `kasumi-mpx5-lope.out`
  (four legs), `kasumi-first-boot-and-pause-sweep.out`.
- **The census**: `notes/px54/census/` (`census.sh`).
- **The plants**: `notes/px54/kasumi-plant-a.out`, `kasumi-plant-b.out`.
- **The suites that build pelt**: `notes/px54/kasumi-mpx5-jobs.out`,
  `kasumi-mpx3-*.out`, `kasumi-mpx5-accounts.out`, `kasumi-chain1.out`,
  `kasumi-chain2.out`.
- **The playground**: `notes/px54/kasumi-playground.txt`.
- **CI**: run 39488153518 (the token absent); 39497071109 (the pull
  request at `840728c`, before the rebase, every suite green but `mpx5-lope`); the plants
  39650231203 and 39650235303 (`notes/px54/ci-*.txt`); the run at the
  final head, in the pull request.

### Measured, inferred, not verified

**Measured**: everything in §A to §I but what follows.

**Inferred**:
- That lope's clock is a `clock_gettime` call on PAX (PAX gives no vDSO;
  Linux answers from it, so strace shows none there). PAX has no tracer;
  no -ENOSYS for it in any boot.
- Why the menu's digit may come early: not traced; measured only that
  the transcript does not move (§D).

**Not verified**:
- The labelled full run (the orchestrator's, ruling #92).
- hasu under KVM; more than one CPU.
- A lope store across a reboot: PAX has no storage (said in the README).

### Issues

- **To close at merge**: none (the contract names no pax issue).
- **Would file (none filed)**:
  1. (none for CI: px54-R1 ruled (a), the secret set.)
  2. lope: README's PAX line (§K), for lope's lane; and lope#3's pelt
     rows (already filed by the orchestrator) go live at pelt `90d7c64`.
  3. pax (small, the harness): `tools/fetch-busybox` needs `zstd`, which
     `px13-ubuntu` lacks, so a suite built entirely in that container has
     no busybox (px53 found it; again here); a lane fetches it on the
     host first.
- Nothing to file for the kernel, pelt or wolf: every call lope makes is
  served.

## 5. Done-when

- Branch `px54` on origin; the pax pull request (number in the
  hand-back), open, unmerged.
- The five sections §1 to §5; the items §A to §K.
- The test checklist:
  - [x] the pins and the hook, each its own commit; the kernel unchanged
  - [x] lope `f9a2f064…` and pelt `5448cb27…`, two builds each, the same
        bytes
  - [x] the session byte-identical to the container's as root and as
        `pax` at the first boot, every row's witness (L1 to L4), four
        legs on kasumi
  - [x] the census: 23 calls, all served but 273 and 334
  - [x] plants A and B red at the predicted rows on kasumi
  - [x] plants A and B red in CI at the same rows (39650231203,
        39650235303)
  - [x] the suites that build pelt green on kasumi at `90d7c64`
  - [x] `tests/ci-plan` 156 PASS
  - [x] the playground refreshed, smoke-booted, on nomad-1, hashed twice
  - [ ] the pull request's `tier pr` run green at the final head,
        `mpx5-lope` included (the run ids in the pull request)
  - [ ] `full-matrix` at the final head; its `tier full` held by the
        orchestrator (ruling #92)
- `wolf/tools/lane-audit.sh pax px54 <PR>`: named in the hand-back.
