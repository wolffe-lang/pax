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