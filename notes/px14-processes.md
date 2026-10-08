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
