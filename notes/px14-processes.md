# px14 — Processes (the shell runs programs)

Contract: `sprints/pax/14-processes/px14-processes.md` in
wolffe-lang/wolf (planning trunk, read 2026-10-08). Branch `px14` in
pax, cut from pax trunk `644ef64` (px13, the console). §1–§3 are
committed before the first change to the kernel and before the first
strace of a spawn; §4 and §5 fill in as the evidence lands.

## 1. Forbidden, absolutely

- No Linux kernel, glibc, musl or any other kernel's or libc's source
  is read (ruling #22), and no shell's source (ruling #43): pelt is
  used as built from its own repository (`user/pelt.pin`,
  `tools/mkpelt`), never read for how it works; its README is read
  for what it claims. Allowed: the uapi headers and the syscall `.tbl`
  in the refs clone's sparse checkout (never widened), the ELF/psABI
  specs, the Intel/AMD manuals, man-pages sections 2, 4 and 7, and
  black-box runs of Linux (strace of a binary). Disassembling a libc
  binary only to identify a faulting instruction, disclosed.
- No `region` held open across a yield, a switch or a return to user
  mode (wolf-lang#611): the process table, the signal records and the
  exec staging are `.bss` words reserved in assembly and read
  volatile; nothing here allocates from wolf's heap.
- Test binaries for PAX (pelt, boreutils, busybox) are built or taken
  in an Ubuntu 24.04 container on kasumi and on the CI runner, **never
  with kasumi's CachyOS glibc**.
- No `rm` outside `~/lanes/px14/` and this lane's worktrees; no `git
  add -A`; nothing under `~/.claude`; no merge; no attribution
  trailers; no "seen red" without a run id, sha, path or digest.
- The tour (`kernel/pax_tour`, `kmain_tour*`, `tools/tour`,
  `tests/tour`) keeps passing; if its ISOs change,
  `~/scratch/wolf/pax-demo/` is refreshed and its preflight run to GO.
  No word implying filming anywhere in pax.

## 2. Inputs, verified (2026-10-08, from origin)

| input | found |
|---|---|
| pax trunk | `644ef64` (px13 merged, PR #16), as the contract says; trunk CI at `644ef64` in progress at the time of reading (run 37728781448), `0b805dd`'s predecessor runs green |
| process ids today | `kernel/sched`: ids are thread ids — 0 main, 1 idle, then 2, 3, … in spawn order, never reused; slots (16, 2-15 spawnable) are. A user program's `who` line says `pid <thread id>`; `set_tid_address` and `gettid` answer the thread id; **`getpid` (39) is -ENOSYS on purpose**: px09's `hello` (`user/programs.S`) calls it and tests/mpx3-user U2 requires `syscall 39: -ENOSYS` |
| the process model today | one thread a process; a thread record holds `cr3` (its PML4, owned: `reap` frees it with the stack), `prog`, the ELF entry/usp/name, the FS base; a 2048-byte process area per slot (kernel/vm's break and mmap cursor words 0-2, the refusal word 3, kernel/user's logged-calls bitmap 4-11, kernel/files' 32 descriptors × 4 words from word 16: kind, node, position, flags). **No parent link, no exit status kept, no wait**: `exit`/`exit_group`/a fault mark the thread DEAD and the next `create` or `wait_all` reaps it; kmain's `wait_all` blocks until the live count is 0. **No close-on-exec bit** is kept (openat's flags word holds whatever was passed) |
| how programs start | only from the kernel: `user.exec_line` / `exec_span` with argv and envp as space-separated kernel bytes (`/etc/pax-run`'s lines), environment `HOME=/ TERM=linux PAX=1` (kmain_console's `ENV`). **No PATH** in it |
| the initramfs px12 built | tests/mpx3-boreutils: `/bin/` the boreutils utilities by name (static, `tools/mkboreutils`) and `/bin/busybox` (busybox-static 1.36.1, the runner's); `/etc/motd`, `/etc/words`, `/etc/pax-run`. px13's pelt initramfs: `/bin/pelt` and `/etc/pax-run` only |
| boreutils' `ls` | **not merged**: boreutils trunk is still `2f15585` (no `src/ls.lu`); the queued boreutils `ls` lane has not landed. So `ls` is busybox-static's, installed as `/bin/ls` (busybox picks the applet from argv[0]'s base name) |
| boreutils built for this lane | `tools/mkboreutils` at the pin `2f15585` in the `px13-ubuntu` container on kasumi (image id `ad896450…`, Ubuntu 24.04, glibc 2.39): echo, cat, wc, head, tail, pwd, sleep, true, false, each 11.8 MB, ET_EXEC, no PT_INTERP (`~/lanes/px14/bore/sums.txt`; `false` `bd6861d6…`, `true` `769e71d1…`) |
| pelt | trunk **`dd22a86`**, the pin px13 used (`user/pelt.pin`): no newer pelt. Its README: "run simple commands … Pipelines, redirections, `&`, `cd` and command substitutions that run another program are refused by name"; Ctrl-C ends pelt; no job control. The static binary `1e2535d7…` (12,362,688 bytes, px13's, `~/lanes/px13/pelt-bin/pelt`) |
| what pelt calls to start a child | **not taken yet**: the strace on Linux (the same static pelt, a pseudo-terminal, black-box) is the measurement §3 P1 predicts, run after this commit |
| kasumi | QEMU 11.1.1, podman (`px13-ubuntu`), no `/dev/kvm` (TCG only); `/home` 95% (54 GB free) |
| hasu | `/dev/kvm` present (crw-rw-rw-), 395 GB free; KVM boots through `nix-shell -p qemu` |
| CI | pax `.github/workflows/ci.yml`: one job per suite; `mpx3-console` builds pelt on the runner (tools/mkpelt), types the sessions on Linux with `tools/linux-tty` (a pseudo-terminal, no chroot) and on PAX with `tools/qemu-halt --type` |

## 3. Prediction (committed before the first change and the first strace)

### P1. One spawn on Linux (strace -f of pelt, a pseudo-terminal, `cat /etc/motd` typed)

- pelt starts a child through glibc's `posix_spawn` shape, not `fork`:
  in the parent `rt_sigprocmask(SIG_BLOCK, ~[], [], 8)`, then
  **`clone3({flags=CLONE_VM|CLONE_VFORK|CLONE_CLEAR_SIGHAND,
  exit_signal=SIGCHLD, stack=…, stack_size=…}, 88)`**; in the child
  `rt_sigprocmask(SIG_SETMASK, [], NULL, 8)` and `execve("/bin/cat",
  ["cat", "/etc/motd"], envp)`; in the parent, once the child has
  exec'd, `rt_sigprocmask(SIG_SETMASK, [], NULL, 8)` and then
  **`wait4(pid, …, 0, NULL)`**. Falsified by a `clone` without
  `CLONE_VM` (a fork), by `waitid` instead of `wait4`, or by a `pipe2`
  around the spawn (pelt capturing the child's output).
- No `dup2`/`close` in the child (pelt passes its descriptors 0-2
  through as they are: no redirection at its pin), no `getpid`, no
  `rt_sigaction` in the child (CLONE_CLEAR_SIGHAND makes it
  unnecessary). Falsified by any of them.
- pelt finds the program itself before spawning, by a stat-family call
  (`newfstatat` or `access`/`faccessat2`) per PATH directory; **with
  PAX's environment (no PATH) pelt searches a default path or finds
  nothing**, a named guess: PAX's environment then needs `PATH=/bin`.
- An unknown name: `pelt: nosuch: not found` on standard error,
  status 127, **no clone at all** (the search fails first).
- `false; echo $?` and `echo hi`: `echo` is a built-in (no spawn);
  `false` is a regular built-in too (no spawn), a guess.
- The spawn adds **5 ± 2** distinct calls to px13's 16
  (rt_sigprocmask, clone3, execve, wait4, the search's stat call),
  falsified outside 3..7.

### P2. The process model PAX takes

- **Process ids** are Linux's, separate from the kernel's thread ids:
  the first program is **pid 1**, the next 2, 3, … never reused in a
  boot. `getpid` answers it, `getppid` the parent's (0 for pid 1, as
  Linux gives init), `gettid` and `set_tid_address` the pid (one
  thread a process). The log's `pid <n>` becomes the Linux pid.
- **`clone`/`clone3` with `CLONE_VM|CLONE_VFORK`**: a new process (a
  new slot and kernel stack, a new pid, the caller its parent) that
  **shares the caller's address space** (the same CR3, not owned:
  nothing frees a space a process only borrows), starts at the
  instruction after the `syscall` with %rax 0, %rsp the stack the
  call names (clone3: stack + stack_size; clone: child_stack), every
  other register and the FS base the caller's; a **copy** of the
  descriptor table (no CLONE_FILES) and of the signal mask. The
  parent waits (a new thread state) until the child **execs or
  exits**, then resumes with %rax the child's pid. Plain `fork`
  (no CLONE_VM) only if the strace shows it; otherwise refused by name.
- **`execve`**: path, argv and envp copied out of the caller's memory
  into kernel staging first (the caller's space may be borrowed); a
  fresh space from the initramfs (kernel/elf, px10's stack layout);
  on success the old space is let go (freed when owned, handed back
  to the vfork parent and the parent woken when borrowed); descriptors
  with close-on-exec closed; FS 0; the FPU template; the pid and the
  parent kept; the name in the log the new program's. On failure
  (-ENOENT, -ENOEXEC, -EFAULT, -E2BIG) nothing of the caller changes.
- **`exit_group` / `exit` / a fault**: the process becomes a zombie
  holding its exit status (Linux's encoding: `code << 8` for an exit,
  the signal number for a kill: SIGSEGV 11, SIGILL 4, SIGFPE 8,
  SIGBUS 7, SIGTRAP 5); its stack and space go back at the next reap;
  its slot stays until the parent waits; its children are reparented
  to pid 1. `wait4(pid | -1, status, WNOHANG?, rusage)` reaps one
  zombie child (status word written, rusage zeroed), blocks while
  children live, -ECHILD with none; `waitid(P_PID | P_ALL, …,
  WEXITED)` the same through a siginfo.
- **Signals answered minimally**: `rt_sigprocmask` keeps a per-process
  mask word (the old one returned, SIGKILL/SIGSTOP never masked),
  `rt_sigaction` records the four words per signal and returns the
  old; nothing is delivered. `kill` (62) and `tgkill` (234) are
  refused by name (-ENOSYS: "signals are not delivered yet").

### P3. What fails first on PAX

- On px13's kernel, unchanged, pelt at its prompt with `cat
  /etc/motd` typed: `rt_sigprocmask` -ENOSYS (tolerated), `clone3`
  -ENOSYS, glibc falls back to `clone`, -ENOSYS, and pelt prints a
  diagnostic of its own and prompts again (status 126 or 127), a
  named guess.
- After clone/execve/wait4 land, the first typed-session diff against
  Linux is in **`ls /bin`** (busybox's listing: a column width or a
  `/proc` read that PAX answers differently), a named guess; after the
  fix every session's diff is empty.
- Boot counts: at least 100 KVM boots on hasu for this lane's suites,
  all green.

### §3 against what was measured

| predicted | measured |
|---|---|
| P1: `rt_sigprocmask(SIG_BLOCK, ~[], [], 8)`, `clone3({CLONE_VM\|CLONE_VFORK\|CLONE_CLEAR_SIGHAND, exit_signal=SIGCHLD, stack, stack_size}, 88)`, the child's `rt_sigprocmask(SIG_SETMASK, [], NULL, 8)` and `execve`, the parent's `SIG_SETMASK` and `wait4(pid, …, 0, NULL)`; no fork, no waitid, no pipe2 | **right** (`notes/px14/pelt-spawn-path.strace`, lines 75-86): exactly those flags, `stack_size=0x9000`; no fork, no waitid, no pipe2 |
| P1: no `dup2`/`close` and no `rt_sigaction` in the child, no `getpid` | **wrong but for getpid**: pelt opens `/dev/null` (O_CLOEXEC, descriptor 5) and maps the child's stack (`mmap` 36 KiB, MAP_STACK) before the clone; the child asks its mask (`rt_sigprocmask(SIG_BLOCK, NULL, …)`), sets `rt_sigaction(SIGPIPE, SIG_DFL)` and `dup2(5, 0)` (a child's standard input is /dev/null, not the terminal); the parent `munmap`s the stack and `close(5)`s. No `getpid` |
| P1: pelt finds the program by a stat call per PATH directory; with no PATH it searches a default path or finds nothing (a guess: PATH=/bin needed) | **right**: `statx(AT_FDCWD, "/bin/cat", …)`; with no PATH it searches the working directory (`statx("./cat")`, `pelt-spawn-nopath.strace`) and says `not found`, so kmain_console's environment gained `PATH=/bin` |
| P1: an unknown name: `pelt: nosuch: not found`, status 127, no clone | **right** (the wording carries the line: `pelt: line 7: nosuch: not found`), 127, no clone |
| P1: `echo` and `false` built-ins (no spawn) | **right** |
| P1: the spawn adds 5 ± 2 distinct calls to px13's 16 (3..7) | **wrong: 8** — pelt's process adds `clone3`, `close`, `mmap`, `munmap`, `rt_sigprocmask`, `wait4` (22 distinct), the vfork child `rt_sigaction` and `dup2` |
| P2: Linux pids from 1, ppid 0 for init, gettid = pid; a vfork child borrowing the space, the parent suspended until exec or exit; execve's copy-out first, close-on-exec, handlers reset, mask kept; zombies with Linux's status words; orphans to pid 1; wait4/waitid; signal calls recorded; kill refused | as built (kernel/process, kernel/sched), and every line of procs on PAX is Linux's (`notes/px14/session-procs.*.txt`): pids 1-9, `0x300`, `0xb`, the zombie kept through a 300 ms sleep, the orphan's `ppid 1` and its reaping by pid 1, waitid's siginfo, `-2 -13 -13 -8`, the mask kept and SIGUSR1 reset across execve, dup2/dup3. Not predicted: Linux sets the core-dump bit (`0x8b`) under a piped core_pattern whatever RLIMIT_CORE says, so procs masks bit 7 |
| P3: on px13's kernel (PATH given): `rt_sigprocmask` -ENOSYS, `clone3` -ENOSYS, glibc's fallback `clone` -ENOSYS, pelt's own diagnostic and the prompt again, status 126 or 127 | **right** (`notes/px14/kasumi-p3-px13-kernel-shell-serial.serial.log`): `syscall 14`, `435`, `56: -ENOSYS`, `pelt: line 1: ls: cannot run`, the prompt; init ended with **126** after `exit` in the PS/2 session |
| P3: the first diff against Linux is in `ls /bin` | **wrong (better)**: the first boot (kasumi, TCG, native BIOS, `c1`) ran all three sessions byte-identical, 15 PASS. **Not predicted: the release tier's procs panicked** in CI (run 37731933253): `PANIC page fault … rip 0x0000000000000000` after the second child's `execve`. The cause, found by an instrumented boot (`notes/px14/kasumi-release-procs-instrumented-panic.serial.log`) and the monitor's dump of the stack (`…-panic-stack.monitor.txt`): `paging.unmap` issued INVLPG only when the PML4 it was given was live; px14's `wait4` reaps a dead child's kernel stack inside a system call, with the parent's space live, so the stack page's stale translation survived; the next child in that slot ran on the old, freed frame until execve's MOV to CR3 dropped it, and its return addresses vanished. A latent defect since px09 (every reap before px14 ran in a kernel thread, the kernel PML4 live). Fixed in `02aec6d` (a kernel-half page is invalidated whichever space is live); plant A re-plants it |
| P3: at least 100 KVM boots on hasu, all green | **right: 228**, all accel=kvm, all green (§4) |

## 4. Evidence index

### The Linux side

- The spawn, black-box: `notes/px14/pelt-spawn-path.strace` (`19e8a613…`), `pelt-spawn-nopath.strace` (`b80ce90a…`), the transcripts `pelt-spawn-*.tty`, the script `strace-spawn.sh`, the keys `shell.keys`; pelt `1e2535d7…` (px13's build of `dd22a86`), boreutils `2f15585` (`boreutils-sums-2f15585.txt`), busybox-static 1.36.1 `dbac288c…`, in a privileged rootless `px13-ubuntu` container on kasumi (Ubuntu 24.04, glibc 2.39, strace 6.8, kernel 7.2.8).
- The reference for every PAX transcript: `tools/linux-tty --root ROOT --pid1` (the same binaries chrooted in the tree the initramfs is made from, init pid 1 of a fresh pid namespace, a pseudo-terminal), kept as `notes/px14/session-*.linux.txt`.

### The typed-session diffs against Linux

**Empty, every session, every leg**: shell-serial (`ls /bin`, `cat /etc/motd`, `wc /etc/motd`, `echo hi`, `false; echo $?`, `sleep 1`, `nosuch`, `echo $?`, `exit`; 16 lines, `8bfdba51…`), shell-ps2 (`ls /bin`, `cat /etc/motd`, `exit` through the PS/2 keyboard; 5 lines, `3c672724…`), procs (23 lines, `077845a5…`): `notes/px14/session-*.pax.txt` against `session-*.linux.txt`, `cmp` equal (kasumi, native BIOS, the gauntlet at `96e5962`). A whole boot: `kasumi-native-bios-shell-serial.serial.log`, `kasumi-release-uefi-procs.serial.log`.

### Boot counts

- kasumi TCG: the gauntlet on a fresh clone of `96e5962` (`notes/px14/kasumi-gauntlet-96e5962.summary`): every suite rc 0, 0 FAIL, 0 SKIP; **156 boots, all accel=tcg**; mpx3-shell 60 PASS on 12 boots (`kasumi-mpx3-shell-96e5962.out`, runs `kasumi-mpx3-shell-runs-96e5962.txt`); mpx3-console 100 PASS (px13's sessions unchanged by PATH and pid 1); tour 44 PASS.
- hasu KVM: **228 boots, all accel=kvm, all green** (`notes/px14/hasu-kvm-96e5962.log`): mpx3-shell 8 rounds × 12 = 96 (60 PASS each), mpx3-console 20, mpx3-loader 4, mpx3-user 12, mkw 12, mpx1 12, mpx2-frames 16, mpx2-paging 4, mpx2-interrupts 20, mpx2-sched 8, mpx2-heap 24; images from the kasumi gauntlet tree at `96e5962`, the tree a `git archive` of `96e5962` (QEMU 11.1.0 through `nix-shell -p qemu`, i7-12700KF).
- CI: every job of run 37733345942 (`96e5962`) green; run 37736460248 (`e3d52b2`, the code the head keeps) green on attempt 2. Its attempt 1 was red in mpx3-boreutils only (job 113176996573): `wolf build: ICE: backend: read /tmp/wolf-llvm-…/wolf.o: No such file or directory` while `tools/mkboreutils` built boreutils with boreutils' own pin, wolf 0.2.23 — wolf-lang#583 (closed, fixed in 0.2.24), here on Linux where its witness was macOS; the same code at `96e5962` was green in that job, and the re-run of the failed job passed. The head's run is in the PR body.
- The code at the head is `96e5962`'s: `git diff 96e5962 HEAD -- kernel boot user tools tests .github` is empty (the plants and their reverts cancel).

### Planted breaks (`notes/px14/ci-planted-breaks.txt`)

- **A** `3cf167c` (unmap's INVLPG only for the live PML4, px14's fix undone): run **37733956321**, job 113169172750, red on exactly the release procs legs (BIOS, UEFI). Reverted `6f5c22e`.
- **B** `662004d` (execve closes nothing): run **37734788175**, job 113171760321, red on S2 of the four procs legs only (`fd3 PAX:` for `fd3 -9`, `fd8 PAX:` for `fd8 -9`). Reverted `24ab01b`.
- **C** `c74550a` (wait4 never blocks): run **37735420378**, job 113173727371, red on all 12 legs (20 FAIL lines). Reverted `e3d52b2`.

### The tour

Every kernel links kernel/process and the larger process table, so the tour's ISOs changed though it starts no process. Rebuilt by `tests/tour` on kasumi in a `git archive` of `96e5962` (`~/lanes/px14/tour-96e5962`; 44 PASS, `notes/px14/kasumi-tour-96e5962.out`): `pax-tour.iso` `dd2e76e6…`, `pax-tour-b.iso` `788471df…` (px13's `3dae9ac4…`, `91c0e931…`). The image grew 280 → 404 KiB, frames −39 (64976 usable, 64927 free, 64909 at the join), ending b's `rip` `0xffffffff80022952`. `~/scratch/wolf/pax-demo/` refreshed: the ISOs, SHA256SUMS, `src/` (pax's `kernel/`, `boot/`, `user/` at `96e5962`; px13's snapshot moved to `~/lanes/px14/pax-demo-src-px13` on nomad-1), the SHOTLIST's numbers (14172 lines of wolf, 1298 of assembly, the frame counts, the `rip`), the README's lines; `preflight.sh` **GO** in a 146×40 pseudo-terminal (QEMU 11.1.1, the PANIC line in about 29 s, `logs/preflight.serial.log` `6635b9cd…`).

### Booting it on nomad-1 (the maintainer's note)

`~/scratch/wolf/pax-shell/` on nomad-1: `pax-shell.iso` (`379b737d…`, the native `console-shell.iso` of the kasumi gauntlet at `96e5962`), `SHA256SUMS`, `README.md`, `logs/rehearsal.tty`. In fish:

```
qemu-system-x86_64 -machine q35 -cpu max -m 256M -display none -serial stdio -monitor none -nic none -no-reboot -cdrom ~/scratch/wolf/pax-shell/pax-shell.iso
```

At `$ ` type `ls /bin`, `cat /etc/motd`, `wc /etc/motd`, `echo hi`, `false; echo $?`, `sleep 1`, `nosuch`, `echo $?`, each with Enter, then Ctrl-D (or `exit`): `PAX: init /bin/pelt ended with status 0; nothing left to run`, `halt`. Ctrl-C quits QEMU. Rehearsed on nomad-1 (QEMU 11.1.1, TCG) in a pseudo-terminal: first prompt at 1.6 s, done at 10.7 s, Ctrl-C ended QEMU with 0 (`notes/px14/nomad-1-rehearsal-pax-shell.tty`).

### Drift from the contract, reported

1. **`false; echo $?` and `echo hi` start no process**: both are pelt built-ins (measured: no clone). The programs the typed sessions run are `ls`, `cat`, `wc` and `sleep`; procs covers the process calls pelt does not make (waitid, zombies, orphans, execve's errors, dup2/dup3, the signal records).
2. **`ls` is busybox-static's** (`/bin/ls`, a copy of `/bin/busybox`): boreutils has no `ls` at `2f15585` (still trunk).
3. **PATH**: kmain_console's environment gained `PATH=/bin` (pelt, given no PATH, searches the working directory); `tools/linux-tty` gives the Linux side the same, so px13's sessions' references moved with it (no transcript changed: mpx3-console 100 PASS).
4. **pids in the log**: a `who` line's `pid` is the Linux pid now, so init is `pid 1` (px13's log said `pid 2`, the kernel thread's id); px09's `hello` asks `_sysctl` (156, which Linux answers -ENOSYS too) where it asked `getpid`, which now answers.
5. **A child's standard input is /dev/null**, as on Linux (pelt's `dup2(5, 0)`): a program pelt starts cannot read the terminal; that is pelt's choice, measured, and PAX does the same.
6. **Not Linux's, named**: a descriptor's copy (dup, or a child's inherited one) keeps its own file position (Linux shares the open file's offset); procs reads inherited descriptors with `pread` so the comparison is about what Linux and PAX agree on. Rusage is zeros. No process groups (wait4's 0 and -pgid mean any child).
7. **A defect found and fixed outside the contract's list**: the stale kernel-half TLB entry in `paging.unmap` (§3), latent since px09.
8. The Linux side needs root now (chroot, mounts, a pid namespace): CI runs `tools/linux-tty` under `sudo -n`; on kasumi the build runs in a privileged rootless container.

### Filed

Nothing upstream: nothing in wolf, pelt or QEMU stood in the way.

## 5. Done-when

- Branch `px14` on origin; PR wolffe-lang/pax#17, open, unmerged; CI green at the head (run id in the PR body).
- The shell runs programs: pelt as pid 1 types through COM1 and the PS/2 keyboard, runs `ls /bin`, `cat /etc/motd`, `wc /etc/motd`, `sleep 1` as child processes (clone3 CLONE_VM|CLONE_VFORK, execve from the initramfs, wait4), answers `echo`, `false; echo $?`, an unknown name (`not found`, 127), and returns to its prompt; every session byte-identical to the same binaries on Linux, both tiers, BIOS and UEFI, KVM on hasu.
- Close nothing. To close: none (no pax issue names this work).
- Not yet (the next lanes'): `fork` without CLONE_VM, threads, signal delivery and Ctrl-C as a signal, process groups and job control, pipes and redirections (pelt refuses them at its pin), `cd` (no `chdir`), `#!` scripts.
- Worktrees: the local worktree removed at the end; kasumi `~/lanes/px14/` and hasu `~/lanes/px14/` keep the trees and evidence with `build/` directories pruned.
