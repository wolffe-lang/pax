# px13 — The console (typing into PAX, and pelt as the first program)

Contract: `sprints/pax/13-the-console/px13-the-console.md` in
wolffe-lang/wolf (planning trunk, read 2026-10-08). Branch `px13` in
pax, cut from pax trunk `23fcfc9` (px12, M-PX3). §1–§3 are committed
before the first change to the kernel and before the first strace of
pelt; §4 and §5 fill in as the evidence lands.

## 1. Forbidden, absolutely

- No Linux kernel, glibc, musl or any other kernel's or libc's source
  is read (ruling #22), and no shell's source (ruling #43): pelt is
  used as built from its own repository (`user/pelt.pin`,
  `tools/mkpelt`), never read for how it works. Allowed: the uapi
  headers and the syscall `.tbl` in the refs clone's sparse checkout
  (never widened), the ELF/psABI specs, the Intel/AMD manuals, the
  PC16550D and i8042/8259 data sheets, man-pages sections 2, 4 and 7,
  and black-box runs of Linux (strace of a binary; a C program that
  prints what an ioctl returns on a pseudo-terminal).
- No `region` held open across a yield, a switch or a return to user
  mode (wolf-lang#611): the console's queues are `.bss` bytes reserved
  in assembly and read volatile; nothing here allocates from wolf's
  heap.
- Test binaries for PAX (pelt, the line program) are built in an
  Ubuntu 24.04 container on kasumi and on the CI runner, **never with
  kasumi's CachyOS glibc**.
- No `rm` outside `~/lanes/px13/` and this lane's worktrees; no `git
  add -A`; nothing under `~/.claude`; no merge; no attribution
  trailers; no "seen red" without a run id, sha, path or digest.
- The tour (`kernel/pax_tour`, `kmain_tour*`, `tools/tour`,
  `tests/tour`) keeps passing; if its ISOs change,
  `~/scratch/wolf/pax-demo/` is refreshed and its preflight run to GO.
  No word implying filming anywhere in pax.

## 2. Inputs, verified (2026-10-08, from origin)

| input | found |
|---|---|
| pax trunk | `23fcfc9` (px12 merged, PR #15, M-PX3), as the contract says |
| the 16550 driver | `kernel/serial`: transmit only, as the contract says. `init` writes IER 0 (no interrupts), FCR 0xc7 (FIFOs on, **receive trigger 14 bytes**), MCR 0x0b (DTR, RTS, OUT2: OUT2 is the PC's gate on the UART's interrupt line, already up); `put` polls LSR bit 5. No receive path at all |
| the interrupt routing | `kernel/timer`: the 8259s remapped to vectors 32 (master) and 40 (slave), every line masked but line 0 (master OCW1 0xfe). `kernel/apic`: LINT0 set to ExtINT, unmasked (virtual wire), so an 8259 line reaches the CPU. `kernel/idt`: interrupt gates 32-47 through `boot/isr.S`'s trampolines. `kernel/interrupts`: 32 ticks, 39 and 47 spurious-checked, **any other 8259 vector panics** "unexpected interrupt". So IRQ1 (the i8042) is vector 33 and IRQ4 (COM1) vector 36, both gated and both masked today |
| the scheduler's sleep and wake | `kernel/sched`: states FREE READY RUNNING SLEEPING BLOCKED DEAD; SLEEPING is woken by the tick (`wake_sleepers`), BLOCKED only by the last exit for `wait_all`. A system call can put its thread to sleep (`sleep_current`, px12's `clock_nanosleep`) with its frame saved; **nothing wakes a thread from an interrupt other than the tick** |
| console reads today | `kernel/files`: descriptors 0-2 are the console (`K_CONSOLE`), `read` on them answers 0 (end of file: "no console input until px13"); `ioctl` answers -ENOTTY to everything; `fstat` says character device 4:64, mode 020620 |
| pelt trunk | **`dd22a86`** (sh02 merged, PR pelt#2): "Plain `pelt` … is an interactive shell: it prompts with `PS1` and `PS2`, reads a line, runs it, and loops until `exit` or Ctrl-D" (its README); "`printf 'echo hi\n' \| pelt` prompts on standard error"; no `os_isatty` at its pin (`tests/session/PENDING.md`), so interactivity is decided by `fs_fstat(0)` telling a regular file from anything else. Pinned at wolf **0.2.24** / lupin 0.1.47 / wolf-std `2f389a7` (its `wolf-toolchain.toml`). The contract's "sh02: interactive, reads stdin byte-wise, prompts with PS1/PS2" holds by its README; byte-wise is measured below, not read from its source |
| pelt, built static | `tools/mkpelt` (this lane), in the `px13-ubuntu` container on kasumi (Ubuntu 24.04 by digest `f610ab94…`, the Containerfile px12's, the image id `ad896450…` identical): **`pelt` `1e2535d7…`, 12,362,688 bytes**, ET_EXEC, no PT_INTERP, linked against Ubuntu's glibc 2.39 `libc.a` |
| pelt's session cases | `tests/session/*.keys`/`.tr` at `dd22a86`: `echo_hi`, `arith_assign` (`x=3; echo $((x*2))`), `func_define_call`, `eof_at_once` (Ctrl-D at the first prompt: exit 0) are recorded from `dash -i +m` through a pseudo-terminal; the prompt is `$ ` |
| the termios ioctls pelt makes | **not taken yet**: the strace on Linux is the measurement §3 P2 predicts, run after this commit |
| kasumi | QEMU 11.1.1, podman, no `/dev/kvm` since the 2026-10-04 reboot (TCG only); `/home` 95% (54 GB free) |
| hasu | `/dev/kvm` present (KVM boots, `nix-shell -p qemu`) |
| the uapi termios header | **not read**: the read of `include/uapi/asm-generic/termbits.h` in the refs clone was refused by this session's tool permissions. The `struct termios` layout and the default flags are taken black-box instead: strace's decoding and a hexdump of what `TCGETS` fills on a Linux pseudo-terminal (§4) |

## 3. Prediction (committed before the first change and the first strace)

### P1. The interrupt lines and the input path

- COM1's receive interrupt is the 8259 master's line 4, **vector 36**;
  the i8042's keyboard interrupt is line 1, **vector 33**; both reach
  the CPU through LINT0's virtual wire as the timer's does. The master's
  mask goes 0xfe → **0xec** (lines 0, 1 and 4 open); the slave stays
  0xff.
- The UART needs IER bit 0 (received data available) and a receive
  trigger of 1 byte (FCR 0x07): with px01's trigger of 14, a single
  keystroke would wait for QEMU's character-timeout interrupt. The
  handler drains RBR while LSR bit 0 is set, then EOIs the master.
- The i8042: the firmware leaves the controller with scancode
  translation on (configuration byte bit 6) under **both** SeaBIOS and
  OVMF, so PAX reads set 1 make and break codes from port 0x60
  (predicted configuration bytes as handed over: SeaBIOS **0x61**, OVMF
  **0x41 or 0x61**; logged at boot, so this can be wrong). PAX sets bit
  0 (IRQ1) and bit 6 itself rather than trust them.
- QEMU's monitor `sendkey` reaches the PS/2 keyboard of a `-nographic`
  q35 machine (no USB keyboard is attached), so the PS/2 path is
  testable headless; falsified if no scancode arrives.
- Both sources feed one queue and one line discipline; echo goes to
  the serial console (the only output PAX has). A blocked `read(0)`
  is a thread in a new wait state, woken from the interrupt handler
  when a line completes; the thread re-executes its `syscall` (RIP − 2,
  RAX = 0), so the copy into its buffer always happens in its own
  address space.

### P2. What pelt asks of the terminal at start-up (strace, Linux, a pseudo-terminal)

- **No `ioctl` at all** in an interactive session (no `TCGETS`, no
  `TIOCGWINSZ`, no `TIOCGPGRP`): pelt at 0.2.24 has no termios surface
  and no `os_isatty`. Falsified by any ioctl on descriptors 0-2.
- Interactivity decided by one `fstat(0)` or `statx(0, "", AT_EMPTY_PATH)`.
- Input read **one byte per `read(0, …, 1)`**; the prompt `$ ` written
  to descriptor 2 in one `write`. Falsified if pelt opens `/dev/stdin`
  or reads more than one byte at a time.
- The session's distinct system calls: px12's start-up set plus the
  reads: **18 ± 3** (15..21). `getpid` (39) is not among them unless
  `$$` is expanded.

### P3. What fails first when pelt runs as PID 1 on PAX

- On px12's kernel, unchanged (console read = end of file), pelt
  writes `$ ` and exits 0 at once, as dash does on Ctrl-D: the first
  read is EOF. (Not a failure, the measurement of "no input".)
- With input, pelt reaches its prompt and answers `echo hi`; the first
  failure is a system call outside px12's 35 answered `-ENOSYS`,
  predicted to be **`rt_sigaction` (13) or `rt_sigprocmask` (14)** from
  wolf's runtime arming a signal, tolerated (pelt goes on). Falsified
  if no new `-ENOSYS` appears, or if pelt dies.
- The typed session (`echo hi`, `x=3; echo $((x*2))`, a function,
  `exit`) differs from Linux's on the first attempt in **echo only**
  (what the terminal writes back, not what pelt writes), named guess:
  the echo of Ctrl-D or of a CR. After the fix, the diff is empty.
- Ctrl-D at the prompt: pelt exits 0; the kernel prints its own line
  and halts.
</content>
</invoke>
<invoke name="Bash">
<parameter name="command">cd ~/lanes/px13/pax && test "$(git branch --show-current)" = px13 && git add notes/px13-the-console.md && git commit -q -m "notes: px13 — the contract's first three sections, before any change" && git add user/pelt.pin && git commit -q -m "user/pelt.pin: pelt dd22a86 (sh02), the shell PAX runs as PID 1" && git add tools/mkpelt && git commit -q -m "tools/mkpelt: pelt from its own tree and pin, static, as mkboreutils builds boreutils" && git push -q -u origin px13 2>&1 | tail -2; git log --oneline -4
### §3 against what was measured

| predicted | measured |
|---|---|
| P1: COM1 is vector 36, the i8042 vector 33, the master's mask 0xfe → 0xec | **right**: every boot's `console:` line (`notes/px13/kasumi-mpx3-console-e31b962.out`, T1 on 20 boots; CI and hasu the same) |
| P1: a receive trigger of 1 byte is needed | as built (FCR 0x07); not measured against the trigger of 14 |
| P1: the i8042's configuration byte as handed over: SeaBIOS 0x61, OVMF 0x41 or 0x61 | **half right**: SeaBIOS **0x61** (kept: 0x61); OVMF **0x67** (bit 1, the second port's interrupt, and bit 2 set; PAX writes 0x65). Translation (bit 6) was on under both, as predicted |
| P1: `sendkey` reaches the PS/2 keyboard of a `-nographic` q35 machine | **right**: 73 keys, 164 scancodes for ask's session; 9 keys, 18 scancodes for pelt's (T3) |
| P1: a blocked `read(0)` re-runs its `syscall` when woken | as built; every session's reads that waited (`14 waited` for ask, `5` for pelt's session) came back with the line |
| P2: no `ioctl` at all | **right** (`notes/px13/pelt-session.strace`, `pelt-eof.strace`) |
| P2: interactivity decided by one `fstat(0)` or `statx(0, "", AT_EMPTY_PATH)` | **right**: `statx(0, "", AT_STATX_SYNC_AS_STAT\|AT_EMPTY_PATH, STATX_ALL, …)`, which PAX answered already (px12): character device, mode 020620 |
| P2: input read one byte a `read(0, …, 1)`; falsified if pelt opens `/dev/stdin` | **wrong**: one byte a call, but on descriptor 4, **`openat(AT_FDCWD, "/dev/stdin", O_RDONLY\|O_CLOEXEC)`**, and output through `openat("/dev/stdout", O_WRONLY\|O_CREAT\|O_APPEND\|O_CLOEXEC)` (boreutils' shape, wolf-lang#405). px12's synthetic `/dev` already reopens descriptor 0 there, so it cost nothing |
| P2: the prompt `$ ` written to descriptor 2 in one write | **right**: `write(2, "$ ", 2)` |
| P2: 18 ± 3 distinct calls (15..21), no `getpid` | **right: 16**, no `getpid` (`notes/px13/pelt-session.calls`) |
| P3: on px12's kernel pelt writes `$ ` and exits 0 at the first read | not re-run (px12's console answered end of file, which is `eof_at_once`'s session; the Linux strace of that session is `pelt-eof.strace`: `read` 0, `write(2, "\n")`, `exit_group(0)`) |
| P3: with input, the first failure is a call outside px12's 35, `rt_sigaction` or `rt_sigprocmask` | **wrong**: there was no failure. pelt's first boot on PAX (kasumi, TCG, `notes/px13/kasumi-c1-first-boot.out`) ran the whole session byte-identical to Linux; the only `-ENOSYS` are glibc's `set_robust_list` and `rseq`, as for boreutils |
| P3: the first typed session differs from Linux's in echo only; empty after the fix | **wrong (better)**: empty on the first attempt, for pelt and for ask (erase, kill, word erase, `^C`, Ctrl-D on a non-empty line, no-echo, non-canonical bytes) on every session of the first boot round. The first round's only red was the test's own T4 (it required glibc's two `-ENOSYS` of ask, which has no libc; `notes/px13/kasumi-c1-first-boot.out`, native BIOS, the tree before `d81d916`), fixed before the test's first commit (`d81d916`) |
| P3: Ctrl-D at the prompt: pelt exits 0, the kernel says so and halts | **right**: `PAX: init /bin/pelt ended with status 0; nothing left to run`, `halt`, qemu-halt HALTED (T5) |

## 4. Evidence index

### The programs and the Linux side

- pelt `dd22a86`, built by `tools/mkpelt` (`e384eac`) with pelt's own pin (wolf 0.2.24 `501d6d3f…`, wolf-std `2f389a7`), static: **`1e2535d7…`, 12,362,688 bytes, byte-identical in the kasumi container and on the CI runner** (run 37722794093's mpx3-console log, `program: bin/pelt`). ask (`user/elf/ask.S`, `tools/mkuser`): `e506d215…`, 11,488 bytes on CI.
- What pelt asks on Linux: `notes/px13/pelt-session.strace`, `pelt-eof.strace` (16 distinct calls each, `*.calls`); the terminal's numbers: `notes/px13/termios.txt` (TCGETS's 36 bytes, TIOCGWINSZ 0×0), `termios-v.strace` (c_cc names), `bits.strace` (each flag bit's name).
- The Linux reference for every session: `tools/linux-tty` on a pseudo-terminal with ISIG and IXON cleared, the same keys (`user/console/*.keys`), argv[0] `/bin/…`, environment `HOME=/ TERM=linux PAX=1` (kasumi: Ubuntu 24.04 container on kernel 7.2.8; CI: the runner).

### The typed-session diff against Linux

**Empty, for all five sessions on every leg**: ask (TCGETS, TIOCGWINSZ, a refused request, a line without echo, six bytes in non-canonical mode, then lines with erase, kill, word erase, `^C` as a byte, Ctrl-D on `abc`, Ctrl-D at the prompt) through COM1 and through the PS/2 keyboard; pelt (`echo hi`, `x=3; echo $((x*2))`, `f() { echo "f:$1:$#"; }`, `f one two`, `exit`) through COM1; pelt (`echo hi`, Ctrl-D) through COM1 and PS/2. Both sides kept: `notes/px13/session-*.pax.txt` and `session-*.linux.txt` (kasumi, native BIOS; `cmp` equal). A full pelt boot: `notes/px13/kasumi-native-bios-pelt-serial.serial.log`.

- CI: run **37722794093** (`0126377`, job 113134084106: 101 PASS, 20 boots), **37722656397** (`e31b962`), 37723707466 (`2b53769`), and the final head's run (PR body). Every job green.
- kasumi TCG: the gauntlet on a clone of `e31b962` (`notes/px13/kasumi-gauntlet-e31b962.summary`): every suite exit 0, 0 FAIL, 0 SKIP; mpx3-console 100 PASS on 20 boots (`kasumi-mpx3-console-e31b962.out`, runs `kasumi-mpx3-console-runs-e31b962.txt`). mpx3-boreutils' build in the container failed at `tools/linux-run` (its chroot needs a privileged container, which this lane did not use); mpx3-boreutils ran green on CI at every head, and its kernel never starts the console.
- hasu KVM: **272 boots, all accel=kvm, all green** (`notes/px13/hasu-kvm-e31b962.log`): mpx3-console 8 rounds × 20 = 160 (100 PASS each), mpx3-loader 4, mpx3-user 12, mkw 12, mpx1 12, mpx2-frames 16, mpx2-paging 4, mpx2-interrupts 20, mpx2-sched 8, mpx2-heap 24; images from the kasumi gauntlet tree, the tree a `git archive` of `e31b962` (kernel code identical to the head: `git diff e31b962 HEAD -- kernel boot user tools` is `kernel/README.md` only).

### The input path, measured

- `console: com1 irq 4 vector 36, i8042 0x61 -> 0x61 irq 1 vector 33, 8259 master mask 0xec; iflag 0x100 oflag 0x05 cflag 0xbf lflag 0x8a3a` under SeaBIOS; `i8042 0x67 -> 0x65` under OVMF (every boot, T1).
- T3: ask's session is 73 bytes on COM1 (`73 bytes from com1, 0 keys`) or 73 keys, 164 scancodes on the keyboard (`0 bytes from com1`); pelt's 66 bytes; pelt's Ctrl-D session 9 (9 keys, 18 scancodes).

### Planted breaks (`notes/px13/ci-planted-breaks.txt`)

- **A** `9bd1e03` (VERASE leaves the byte): run **37723718019**, job 113136981411, only mpx3-console red: the 8 ask legs (`helxlo` for `hello`, then the kill loop never ends), the 12 pelt legs green. Reverted `79b93bf` (run 37724351826 green).
- **B** `f3d6628` (the keyboard ignores Shift): run **37725033056**, job 113141146271: T2 red on exactly the 4 ask-ps2 legs. Reverted `a1d3eeb` (run 37725086579 green).
- **C** `b9883aa` (Ctrl-D at an empty line is not end of file): run **37725229985**, job 113141768227: T2/T3/T5 red on the 16 legs ending in Ctrl-D, pelt-serial green. Reverted `0b805dd` (run 37725621311 green).

### The tour

Every kernel links kernel/console now (kernel/interrupts routes 33 and 36), so the tour's ISOs changed though it never starts the console. Rebuilt by `tests/tour` on kasumi in a `git archive` of `e31b962` (44 PASS in the gauntlet; the archive build's R0): `pax-tour.iso` `3dae9ac4…`, `pax-tour-b.iso` `91c0e931…` (px12's `a7c3a6df…`, `3bae5d83…`). The image grew 252 → 280 KiB, frames −15 (65015 usable, 64966 free, 64948 at the join), ending b's `rip` `0xffffffff8001c41b`. `~/scratch/wolf/pax-demo/` refreshed: the ISOs, SHA256SUMS, `src/` (pax's `kernel/`, `boot/`, `user/` at `0b805dd`; nothing removed; px12's snapshot moved to `~/lanes/px13/pax-demo-src-px12`), the SHOTLIST's numbers (12951 lines of wolf, 1285 of assembly, the frame counts, the `rip`), the README's build lines; `preflight.sh` **GO** in a 146×40 pseudo-terminal (QEMU 11.1.1, the PANIC line in about 29 s, `logs/preflight.serial.log` `8fe2cae4…`).

### Drift from the contract, reported

1. **"pelt as PID 1"**: pelt is the first and only process the kernel starts, init in role; PAX's ids number its kernel threads first (0 main, 1 idle), so the log says `pid 2`, and `getpid` is still -ENOSYS (px09's hello requires it). pelt never asks for its pid. Real process ids come with px14's `clone`/`execve`/`wait4`.
2. **"TIOCGWINSZ 80x25 or the serial default"**: the serial default, **0 rows, 0 columns**, which is what a Linux pseudo-terminal answers too (measured, `termios.txt`).
3. **Ctrl-C delivered as a byte**: so the console's ISIG is clear, and so is IXON; TCGETS says so (iflag 0x100, lflag 0x8a3a, where a Linux pseudo-terminal says 0x500, 0x8a3b). The Linux reference clears the same two bits, so the comparison is like for like.
4. The uapi termios header was not read (a tool-permission refusal, §2); its facts were measured black-box instead.
5. Not in the contract: `tools/qemu-run --serial-input` (QEMU's file chardev with `input-path`), `tools/qemu-halt --type`, `tools/linux-tty`, and `ask`, the console's own test program.

### Filed

Nothing upstream: nothing in wolf, pelt or QEMU stood in the way.

## 5. Done-when

- Branch `px13` on origin; PR wolffe-lang/pax#16, open, unmerged; CI green at the head (run id in the PR body).
- Typing reaches PAX: COM1 (IRQ4) and the i8042 (IRQ1) into one line discipline, `read(0)` blocking until a line is ready, echo through the console; TCGETS/TCSETS/TCSETSW/TCSETSF/TIOCGWINSZ/TIOCSWINSZ answered, everything else refused by name; typed sessions over serial and over PS/2 byte-identical to Linux on both tiers, BIOS and UEFI; pelt as PID 1 answers `echo`, arithmetic, a function, `exit`, and Ctrl-D ends it, the kernel says so and halts.
- What pelt as PID 1 cannot do yet: run anything external (`clone`/`execve`/`wait4`, px14), `cd` (no `chdir`), pipes and redirections to files (pelt refuses them at its pin), job control and Ctrl-C as a signal (no signals, no process groups), line editing beyond the discipline's (no arrows).
- Close nothing. To close: none (no pax issue names this work).
- Worktrees: the local worktree `~/lanes/px13/pax` removed at the end; kasumi `~/lanes/px13/` and hasu `~/lanes/px13/` keep the trees and evidence with `build/` directories pruned; the container image `px13-ubuntu` on kasumi is the lane's (the same image id as px12's).
