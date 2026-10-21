# px58 — yew on PAX: the census

Contract: px58's, `sprints/pax/58-yew-on-pax/px58-yew-on-pax.md` in
wolffe-lang/wolf (read 2026-10-21 from the planning checkout), under
`sprints/RULES.md`, Track 13's rules (`sprints/pax/index.md`) and Track
12's (`sprints/yew/index.md`). Branch `px58` in pax, cut from pax trunk
`ebbef86` (px54's rebase onto px56). §1 to §3 are committed before the
first change to a pin, the kernel, a tool, a probe or a test, and before
the first measurement.

The maintainer's question: "How far are we from an editor in pax?" This
lane measures the distance (what yew asks of Linux, what PAX answers)
and closes the small part of it. It changes no line of yew.

## 1. Forbidden, absolutely

- No kernel's source is read or searched for, Linux's above all, nor any
  libc's, terminal driver's, terminal emulator's or other editor's
  (ruling #22; RULES.md §1; Track 12's rule 1: never vim, neovim, emacs,
  helix, kakoune, nano, micro, nor fackr's crates). yew and sagitta are
  the maintainer's and are read and cited as such (yew `77c1083`:
  `src/term/tty.lu`, `src/term/input.lu`, `src/term/render.lu`,
  `src/edit/driver.lu`, `src/edit/cmdline.lu`, `src/yew.lu`,
  `tools/build`, `tools/goldens`, `tools/oracle`, `runtime/init.fl`;
  sagitta `9ace98c2`: `tests/pty/registry.c`'s notepad cases). Facts
  about Linux come from the man pages (`termios(3)`, `ioctl_tty(2)`,
  `console_codes(4)`, `strace(1)` as documentation), POSIX.1-2024 (XBD
  11, the General Terminal Interface), ECMA-48 for the escape classes'
  names, the terminfo database's `linux` entry (`infocmp linux`: a
  terminal's documented strings, not a kernel's code), the allowed uapi
  headers and syscall table, pax's own source and notes, and black-box
  runs: the same static binaries on a pseudo-terminal in a throwaway
  container (`tools/linux-tree`), real root's guest (kasumi's own kernel
  image under QEMU, never read, px48's `linux-vm.sh`), and `strace -f`
  of yew's own runs in `px13-ubuntu`. `wolf/refs/repos/linux` stays
  sparse and is not opened. No word implying filming.
- Every check gets a user row: the probe as root and as `pax`
  (1000:1000); the session as `pax`. Signals and id changes only inside
  QEMU or a container.
- Probe and test binaries static, built in `px13-ubuntu` on kasumi,
  never with kasumi's CachyOS glibc (AVX-512). No build on nomad-1.
  kasumi under `bash`, long jobs `setsid -f` with a pid file, ended by
  that pid only, never by process group; `ulimit -c 0` in containers;
  work under `~/lanes/px58/`, pruned (kasumi `/home` 25 GB free at the
  start, 98% used); never `/tmp`. Boots under `taskset -c 0-3`. Ports
  8080 and 8088 unused; nothing installed on any host.
- Toolchains from release archives by digest, each read twice: yew's own
  wolf 0.2.33 (`4f955e8d…`, release 417610226, 80,128,936 bytes; the
  API's digest read twice, 2026-10-21) and wolf-std `cceda63`; termwolf
  by the same (its own `wolf-toolchain.toml`, sigwolf's shape). The
  kernel's pin (wolf 0.2.33 / lupin 0.1.54) unmoved.
- **No change to yew** (its repository untouched; the worktree under
  `~/lanes/px58/yew` is a read-only checkout). What yew needs from PAX
  goes in the gap table; what PAX finds wrong in yew is a yew issue,
  listed, never filed.
- Files: `kernel/console/`, `user/yew.pin`, `tools/mkyew`,
  `user/termwolf`, `tests/mpx5-yew`, `tools/ci-tiers.map` (and the
  suite's wiring: its CI job, `tests/ci-plan`'s cases, its keys under
  `user/console/`), this note and `notes/px58/`, the kernel README's
  console row and the CHANGELOG. px57 (the 0.2.34 pins, aspen, lupin,
  the ISO) lands beside: rebase as it does; no ISO rebuild here.
- No `rm` outside `~/lanes/px58/` and this worktree; no `git add -A`;
  nothing under `~/.claude`; no merge, no tag; no issue filed or closed
  (listed); no `2>/dev/null` on a checkout; no trailer on a commit or the
  PR. No other lane's run cancelled; a plant by dispatch, `-f tier=pr`
  with its suite; the PR opened without the label, `full-matrix` added
  at the final head. "Seen red" cites a run. No assertion deleted or
  weakened, no timeout or retry as a fix. If the harness refuses an
  action I stop and report.

## 2. Inputs, verified (2026-10-21)

| input | found |
|---|---|
| pax trunk | `ebbef86` (px54's rebase onto px56 `f83d627`); its push run 39667476855 green; no open PR; px57's three plant dispatches (39680111521, 39680114939, 39680118584) red as plants are; no `nightly-red` issue open; open issues #55, #56, #62, #67, #90, #100–#109 (none this lane's; #106 execve of `/proc/self/exe` and #108 `flock` noted) |
| yew | trunk `77c1083` (tl30's merge; yw03's `9bd219c` before it, M-YW3); **yw04 (PR #19) is open, not merged**, so this lane builds trunk. Public. Its own toolchain (`wolf-toolchain.toml`): wolf 0.2.33 `4f955e8d…` (`wolf 0.2.33 (wolfgang, pin 85dab5d)`), lupin 0.1.54, wolf-std `cceda631…`. `tools/build --static` is the shape PAX runs: `wolf build --release --no-cache --deny-warnings src/yew.lu` through a `cc` first on `PATH` that adds `-static` (`tools/mkpelt`'s exactly). The editor needs a file argument at trunk (no file: "not yet ported: the workspace resume", `src/edit/driver.lu:186`) |
| what yew does at a terminal | (`src/term/tty.lu`) both standard streams must be terminals; the mode read and packed (`os_term_mode`); the size read (`os_term_size` on fd 1; 0 by 0 is "never told", and the editor falls back to 24 by 80, `src/edit/driver.lu:213`); **a guard sibling** (ruling #93 R1 interim B): itself again by `os_exe()` as `--guard <mode>` in its own process group, the tty its 0–2, a pipe's read end its 3 (`/dev/fd/3`), ignoring HUP INT QUIT TERM TSTP TTIN TTOU; raw mode (canonical, echo, signals, flow, extended off, VMIN 1, VTIME 0), read back and compared; the listen set WINCH CONT TSTP CHLD TERM HUP QUIT; the alternate screen (`ESC 7`, `CSI ?1049h`); the capability probe (`CSI ?u`, `CSI ?2026$p`, `CSI c`, 50 ms); the input modes (`CSI ?2004h`, `?1002h`, `?1006h`, `?1004h`); `VMIN 0 VTIME 1` polling while a deadline is armed (the 25 ms lone-ESC timer, the probe), `VMIN 0 VTIME 0` for the typeahead drain; at exit the restore blob (`CSI <u`, `?2004l`, `?1002l`, `?1006l`, `?1004l`, `?2026l`, `CSI 0m`, `CSI 0 SP q`, `?1049l`, `?25h`) and the saved mode. `TERM=linux` is the 16-colour tier (`src/term/render.lu:227`) |
| the session's keys | `runtime/init.fl`: L mode `o` opens a line below in I mode, `<esc>` leaves it, `G` the buffer's end, arrows move; `:` the narrow command line (`src/edit/cmdline.lu`), `w` the abbreviation of `ed.file.write`, `q` of `ed.quit` (`src/edit/cmdtab.lu`) |
| the oracle | sagitta `9ace98c2` (public), `tools/oracle` builds it; `tools/goldens --yew BIN` runs its PTY runner against BIN; yew's CI gates campaign 01 (18 cases, the paint and restore ones driving the port's `demo_paint`) and campaign 03 (62 cases, the editor: `notepad_*`, `s15_*`–`s17_*`) by name |
| wolf 0.2.33's terminal calls | `spec/11-os.md` at `v0.2.33`: `[os.term.mode]` (one int: CANONICAL ECHO SIGNALS FLOW EXTENDED, VMIN, VTIME; every other field left as found, so ICRNL and OPOST stay set in yew's raw mode, G34; the set is TCSADRAIN), `[os.term.size]` (TIOCGWINSZ; SIGWINCH is RESIZE), `[os.term.chars]`, `[os.signal.wait.fd]` |
| 0.2.34's editor calls | `spec/11-os.md` at `v0.2.34`, `[os.editor.calls.note]` (s248): `os_term_restore_at_exit` (a duplicate of the tty at 3 or above, close-on-exec; at exit `tcsetattr` with SIGTTOU blocked, then `write`), `os_signal_wait_fds` (`poll(2)` on a duplicate of each handle and one wake pipe, a deadline), `fs_sync` (`fsync`), `fs_sync_dir` (an `O_DIRECTORY` open and `fsync`), `fs_realpath`, `os_clock_ns`, the mode's bits 5..7 (`RAW_CR` ICRNL cleared, `RAW_OUTPUT` OPOST cleared, `STRIP8` ISTRIP set). Coming with yw05's pin bump; listed, not measured |
| PAX's console | `kernel/console/console.lu`: the settings a Linux pty starts with less IXON; every flag word and control character stored and answered; acted on: ICRNL INLCR IGNCR, ICANON, ECHO ECHOE ECHOK ECHOKE ECHOCTL ECHONL, ISIG with VINTR VQUIT VSUSP, NOFLSH, TOSTOP, IEXTEN's VWERASE, VERASE VKILL VEOF VEOL, VMIN/VTIME both shapes (px46, px48), OPOST\|ONLCR on output; ioctls TCGETS TCSETS TCSETSW TCSETSF TIOCGWINSZ TIOCSWINSZ (SIGWINCH to the foreground group on a change) TCFLSH TCSBRK TIOCSTI and the controlling terminal's five, KIOCSOUND KDMKTONE; anything else `refused: tty ioctl 0x…` and -ENOTTY. The window size is the device last typed at (px48, pax#68): 0 by 0 after COM1, the screen's 50 by 160 after the keyboard or before any input. The keyboard (set 1, US) gives no character for arrows, Home, End, PgUp, PgDn, Insert, Delete or the function keys (`scancode`: an E0 key but keypad Enter and `/` gives 0) |
| PAX's screen | `kernel/screen/screen.lu`: printable UTF-8, CR LF BS TAB, deferred wrap, scrolling; CSI read whole, **SGR 0 1 7 30–37 39 40–47 49 90–97 honoured, every other CSI and every private sequence ignored**, ESC then not `[` two bytes ignored. `tools/screen-ref` is its reference renderer and `tests/mpx3-screen` holds the two together pixel for pixel |
| the harness | `tools/qemu-halt --type` and `tools/linux-tty` type the same keys format; a step's bytes are its characters (a raw ESC byte in the file is typed as 27 by both: bash's `printf %d "'c"`, Python's `encode`), Enter unless it ends `^D` or `^.`; `^~` a step typed a pause after the one before (PAX_TYPE_PAUSE, 2 s; 1.5 s on Linux), every other step after its prompt; serial bytes 20 ms apart; `--keyboard ps2` maps no arrow; `--cmd screendump FILE` on the halted machine |
| PAX's system calls | `kernel/user/user.lu`'s table: 160 numbers, among them `poll`, `pipe2`, `socketpair`, `clone`, `clone3`, `execve`, `wait4`, `setpgid`, `futex`, `sigaltstack`, `sched_getaffinity`, `madvise`, `fsync`, `fdatasync`, `renameat2`, `statx`, `fchown`, `fchmod`, `readlinkat`; not `ppoll`, `pselect6`, `select`, `rt_sigtimedwait`, `mremap`, `flock`, `close_range`, `set_robust_list`, `rseq` |
| kasumi | Linux 7.2.8-1-cachyos, 16 cpus, load 5 (other lanes), QEMU 11.1.1, strace at `/usr/bin/strace`, `px13-ubuntu` `ad8964505189` (Ubuntu 24.04, gcc, clang, strace, ld.lld, git), `/home` 25 GB free (98% used): pruned as I go |

## 3. Prediction (committed before the first change and measurement)

**P1. The static yew.** `tools/mkyew` (new, `tools/mkpelt`'s shape:
yew's tree at `user/yew.pin`'s commit, its own `wolf-toolchain.toml`'s
archive by digest and std by commit, `wolf build --release --no-cache
--deny-warnings src/yew.lu` through a `cc` that adds `-static`, ET_EXEC
and no PT_INTERP checked, `yew --version` run, `yew <sha256> <bytes>` in
`sums.txt`) builds yew `77c1083` in `px13-ubuntu` to **the same bytes
twice**, between 15 and 30 MB (pelt is 15.2 MB, lope 14.4 MB; yew carries
the embedded runtime, the Unicode tables and the command table). yew is
public, so CI fetches it as it fetches pelt; CI's runner builds the same
bytes (px54 saw `ubuntu-latest` link what `px13-ubuntu` links). Weak:
the size.

**P2. The Linux census.** `strace -f` over yew's goldens (version, help
and campaign 03's 62 editor cases, the static yew run by a wrapper that
`exec`s `strace -D -f`, so the runner's pid stays yew's and its signals
reach it) and over the typed session (P5's keys) names, as a static
glibc wolf program with a guard sibling and wolf's signal thread:
`execve`, `brk`, `arch_prctl`, `set_tid_address`, `set_robust_list`,
`rseq`, `prlimit64`, `mprotect`, `mmap`, `munmap`, `getrandom`,
`readlink`/`readlinkat` (`/proc/self/exe` for the guard), `rt_sigaction`,
`rt_sigprocmask`, `sigaltstack`, `openat`, `read`, `write`, `close`,
`fstat`/`newfstatat`/`statx`, `lseek`, `getcwd`, `ioctl`, `poll`,
`pipe2`, `socketpair` (the spawn's handshake), `clone`/`clone3`,
`setpgid`, `dup2`/`dup3`, `wait4`, `futex`, `kill`/`tgkill` (a stop
raised at itself), `mkdir` (the state directories), `rename`, `unlink`,
`fchmod`/`fchown` (the save keeps the mode and owner), `exit_group`; no
`clock_gettime` (the vDSO's). **ioctls: exactly TCGETS, TCSETSW and
TIOCGWINSZ.** **termios** decoded by strace: the saved mode the
terminal's (a pty's default, IXON cleared by the harness); the raw mode
c_lflag `ECHOE|ECHOK|ECHOCTL|ECHOKE` (ISIG, ICANON, ECHO, IEXTEN off),
c_iflag `ICRNL` (IXON off; ICRNL kept, G34), c_oflag `OPOST|ONLCR` (kept,
G34), c_cflag unchanged, VMIN 1 VTIME 0; the poll shape VMIN 0 VTIME 1;
the drain VMIN 0 VTIME 0; the saved mode back at exit. `TIOCGWINSZ` on
fd 1, answered 24 by 80 by the goldens' runner and 0 by 0 on an unsized
pty. No `/dev/tty` open. **Signals caught** (a handler): WINCH, CONT,
TSTP, CHLD, TERM, HUP, QUIT (yew's listen set) and the runtime's SEGV
and BUS (the stack guard, on an alternate stack); the guard ignores HUP,
INT, QUIT, TERM, TSTP, TTIN, TTOU. **Escape classes** the renderer
emits, by count: cursor position (CUP) and SGR dominate, then erase in
line (EL), the alternate screen, cursor visibility (`?25l`/`?25h`),
cursor shape (DECSCUSR), DECSC/DECRC, bracketed paste, mouse (1002,
1006), focus (1004), synchronized output (2026's DECRQM query, `?2026l`
in the restore), kitty keyboard (the `CSI ?u` query, the `CSI <u` pop),
DA1's query; SGR only in the 16-colour tier (30–37, 90–97, 40–47,
100–107, 0, 1, 7 and their resets). Weak: the exact list of calls (a
call I have not foreseen, `madvise`, `sched_getaffinity`, `gettid`) and
whether the save syncs (it cannot at 0.2.33: G3).

**P3. PAX, served or refused.** Every call of P2 is in PAX's table but
`set_robust_list` (273) and `rseq` (334), which glibc's start copes with:
**-ENOSYS for 273 and 334 only, no `refused:` line**, in any boot of yew
or the probe. The probe (`user/termwolf`, sigwolf's shape, wolf 0.2.33):
- **termios: every flag bit and every control character round-trips**
  (TCSETS then TCGETS, set and cleared one at a time): served, identical
  to Linux's pty. **Divergent at one place by design**: the initial
  c_iflag (PAX 0x100, ICRNL; Linux's pty 0x500 with IXON, which the
  harness clears). Kept and answered but not acted on (silently dropped
  as behaviour; none is a bit yew's raw mode relies on): IXON, IXOFF,
  IXANY (no output flow control), ISTRIP, INPCK, PARMRK, BRKINT, IGNBRK,
  IGNPAR, IUCLC, IMAXBEL, IUTF8, the output delays and OLCUC, OCRNL,
  ONOCR, ONLRET, OFILL, the speed, ECHOPRT, FLUSHO, PENDIN, XCASE,
  VLNEXT, VREPRINT, VDISCARD.
- **The behaviours yew's raw mode needs are served**: canonical, echo
  and signals off; VMIN 1 VTIME 0 waits for a byte; VMIN 0 VTIME 1
  answers 0 after a tenth of a second; VMIN 0 VTIME 0 answers at once;
  Ctrl-C, Ctrl-Z, Ctrl-\ are bytes; CR becomes LF under ICRNL; LF becomes
  CR LF under OPOST|ONLCR.
- **TIOCGWINSZ**: 0 by 0 after COM1 input, as Linux's pty and serial
  line answer an unsized terminal (served); TIOCSWINSZ then TIOCGWINSZ
  served, with SIGWINCH to the foreground group on a change (served).
  Named, not a gap: the screen's 50 by 160 after keyboard input.
- **`/dev/tty`** opens to the console and answers TCGETS (served).
- **Escape classes on the framebuffer** (the probe writes each into a
  known layout; the halted screen read cell by cell from QEMU's
  screendump against the Spleen font): **served** CR, LF, BS, TAB, SGR
  0, 1, 7, 30–37, 39, 40–47, 49, 90–97; **silently dropped** everything
  else yew writes: CUP, EL, ED, cursor movement, DECSC/DECRC, the
  alternate screen, cursor visibility and shape, bracketed paste, mouse,
  focus, synchronized output, kitty keyboard, SGR 2, 3, 4, 22–27 and
  100–107. The serial transcript carries every byte unchanged
  (byte-identical to Linux). The queries (DA1, DECRQM, kitty) get no
  answer on PAX or on a pty; Linux's VT answers DA1 (console_codes(4)),
  named, not measured.
- **The keys yew binds that PAX's keyboard cannot give**: arrows, Home,
  End, PgUp, PgDn, Insert, Delete (silently dropped at the scancode
  decoder); over COM1 they arrive as the bytes the terminal sends.

**P4. The small gaps, my call.** In `kernel/console/` only, each under a
day: **the keyboard's cursor and editing keys** (the E0-prefixed set-1
arrows, Home, End, PgUp, PgDn, Insert, Delete) put the `linux`
terminal's sequences in the input (`infocmp linux`: `\E[A` `\E[B` `\E[C`
`\E[D`, `\E[1~` Home, `\E[4~` End, `\E[5~` `\E[6~`, `\E[2~` Insert,
`\E[3~` Delete), checked against a Linux guest's virtual terminal when
kasumi's kernel image gives one, through the line discipline as typed
bytes (echoed as `^[[A` in canonical mode with ECHOCTL, as Linux's VT
echoes them). **Not here, listed for px59** ("yew on PAX: the console"),
because the fix is in `kernel/screen/` and its reference renderer
`tools/screen-ref` (held together by `tests/mpx3-screen`) and not local
to `kernel/console/`: the framebuffer console's CSI interpretation (CUP,
ED, EL, ECH, cursor movement, DECSC/DECRC, the alternate screen, cursor
visibility, SGR 2/4/22–27/100–107), a DA1 answer, Alt as an ESC prefix,
the function keys.

**P5. The session.** yew draws its first frame on PAX: started as `pax`
(`/bin/as 1000 1000 /bin/env HOME=/home/pax /bin/sh -i -m`, `cd
/home/pax`, `yew notes.txt` on a 1000:1000 file `alpha`/`beta`/`gamma`),
typed over COM1: the shell's command, then each key a `^~` step of its
own (`G` to the last line, `o` a line below, `delta` a key at a time,
ESC, `:w` Enter, `:q` Enter), then `cat notes.txt` and `exit`. The
window is 0 by 0 on both sides (COM1 input; an unsized pty), so yew lays
out 24 by 80 on both. **The serial transcript is byte-identical to the
same binary typed the same keys on a Linux pty** (the container, live,
`tools/linux-tree`, as `pax`), and the file reads `alpha beta gamma
delta` on both. The screen shows a smear (every frame's text appended:
CUP and EL dropped). Weak: the pause PAX needs under TCG between keys
(yew's paint must finish before the next key, or two keys batch into
one frame and the bytes part from Linux's); the guard's spawn of a
second 15–30 MB static program from the tree under TCG (seconds); the
lone-ESC timer (25 ms) against ESC typed alone (it is: a step of its
own).

**P6. The rows.** `tests/mpx5-yew`, a suite of its own (mpx5-lope's
shape: one kmain_console image, the container its live reference), in
`tools/ci-tiers.map` (`user/yew.pin`, `tools/mkyew`, `user/termwolf/`,
its keys) and `tests/ci-plan`: Y0 the build (yew, termwolf, pelt,
boreutils' `env` and `cat`, `as`, static); Y1 the probe's termios and
size rows on PAX as root and `pax` held to the container's; Y2 the
escape classes on the halted screen (served and dropped as P3); Y3 the
keys (the keyboard's sequences, after P4); Y4 the session byte-identical
to the container's, the saved file's bytes; Y5 -ENOSYS 273 and 334 only,
no `refused:` line, init's end, halted. Plants, each a branch never
merged, by dispatch `-f tier=pr -f suites=mpx5-yew`: **A** the console
keeps no VTIME with VMIN 0 (a read answers 0 at once): red at Y1's
timed-read row and, weak, the session (yew's polling turns into a spin:
the bytes still match); **B** the keyboard's arrows give nothing again
(P4 reverted): red at Y3 only.
