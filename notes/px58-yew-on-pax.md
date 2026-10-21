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

**P6, by row** (added after the first boots, before either plant ran;
the plants are `px58-plant-a` `c15467d` and `px58-plant-b` `9f0bf41`,
one commit each on `45364a3`). **A** (a VMIN 0 read answers at once,
VTIME ignored): Y1 red as root and as `pax` at the two timed rows (`T:
VMIN 0 VTIME 1 …` and `VTIME 5 …` read `early (N ms)` where Linux's are
`in bounds`); green at the query rows (their half-second loop only spins
faster) and the keys (VMIN 1); Y2, Y3, Y4, Y5 green (yew's VTIME polling
spins between its deadlines and writes nothing more; weak). **B** (the
cursor keys give nothing again): Y3 red (`typed '2e'`), every other row
green.

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | `tools/mkyew` builds yew `77c1083` the same bytes twice, 15–30 MB | **`c2daa653e398640e98c627c3b6cfb6bf454b60fa3d6444ed754767e0c8764b67`, 16,101,824 bytes**, two builds in `px13-ubuntu` the same bytes (167 s, 126 s; §A); every suite build since gave the same | right |
| P2 | the calls by name; ioctls exactly TCGETS, TCSETSW, TIOCGWINSZ; the termios states; no `/dev/tty`; WINCH CONT TSTP CHLD TERM HUP QUIT caught, and SEGV and BUS on an alternate stack; the guard's seven ignored; CUP and SGR dominate, then EL … | **50 calls by name** (§B): every predicted family, and `fcntl(F_DUPFD_CLOEXEC)` (the runtime sets the mode and waits on a duplicate of fd 0), `prctl(PR_SET_NAME, "wolf-signal")`, `recvfrom` (the spawn's handshake), `linkat`, `chmod` (the save) that I did not name; **no `sigaltstack` and no SEGV or BUS handler** (wolf 0.2.33 installs none in yew); ioctls exactly the three; the termios states exactly as predicted (§C); no `/dev/tty`; the seven caught and the guard's seven ignored, and SIGPIPE ignored; CUP and SGR dominate, but **no EL, no ED**: yew's renderer writes spaces | right on the terminal, wrong on the stack guard and on EL |
| P3 | -ENOSYS 273 and 334 only, no `refused:`; every termios bit round-trips; the initial c_iflag divergent; the raw-mode behaviours served; TIOCGWINSZ 0 by 0 after COM1 input; `/dev/tty`; the screen draws SGR 0 1 7 30–37 39 40–47 49 90–97 and drops the rest; the queries unanswered on both; the cursor keys dropped | -ENOSYS 273 and 334 only, nothing refused, in every boot (Y5); every bit and every c_cc round-trips on PAX, and **Linux's pty refuses four cflag bits** (CS6 CS7 CREAD PARENB: a divergence I did not foresee); **the initial c_iflag is the same** (0x100 on both: the harness clears the pty's IXON, as PAX starts); yew's three modes leave the same termios on both; the timed reads in bounds on both; OCRNL and OLCUC dropped on PAX (Linux converts); the window as predicted (PAX's screen grid before any key, root's rows); `/dev/tty` served; the screen exactly as predicted, SGR 22 and 27 among the dropped (§D) | right but the cflag bits |
| P4 | the keyboard's cursor and editing keys, in `kernel/console/`, checked against a Linux VT | measured on kasumi's kernel's VT first (§E), then served (`c8ec73d`): Y3 red at the first boot, green after | right |
| P5 | yew draws; the session byte-identical to the container's at 24 by 80; the file alpha beta gamma delta; weak: the pauses | **yew draws, edits and saves on PAX**; byte-identical (3,732 bytes) once both sides' pauses outlast yew's 4 s info message: the first boot parted at byte 3,279 because PAX's 6 s pause let "wrote notes.txt" expire before `:` (an extra statusline frame) where Linux's 1.5 s did not, a timing of the keys and not of PAX (§F); `o` on the last line opened a line after yew's phantom last line, so the keys use `O` | right but the pause (the weak point, in a way I did not foresee) |
| P6 | the suite's rows; plants A and B red at their rows | §H | (scored there) |

## A. The static yew (item 1)

- `user/yew.pin` (`7bcfaa2`): yew's repository and `77c1083` (trunk;
  yw04's PR #19 open, so not its head). `tools/mkyew` (`45fac96`):
  `tools/mkpelt`'s shape with yew's names, the tree from `PAX_YEW_REPO`
  when set (yew is public; CI fetches it as pelt), the archive by the
  digest yew's `wolf-toolchain.toml` names and wolf-std at its commit,
  `wolf build --release --no-cache --deny-warnings src/yew.lu` through a
  `cc` that adds `-static` (yew's own `tools/build --static` exactly),
  ET_EXEC and no PT_INTERP checked, `yew --version` run (`yew
  1.0.0-dev`, `modules: lsp ai fuss plugins`).
- **`c2daa653e398640e98c627c3b6cfb6bf454b60fa3d6444ed754767e0c8764b67`,
  16,101,824 bytes**, built twice in `localhost/px13-ubuntu`
  (`ad8964505189`, Ubuntu 24.04, libc6-dev 2.39), the same bytes
  (`notes/px58/kasumi-bins-yew-twice.out`), and the same in each of the
  suite's builds since (`notes/px58/kasumi-t2/programs.txt`).
- termwolf (`user/termwolf`, `f2bcb31`): wolf 0.2.33 by digest, std
  `cceda63`, its builder `user/termwolf/build` (`tools/mksigwolf`'s
  shape, the directory a package so `asm: ["tio.S"]` carries the raw
  terminal ioctls); 14,355,784 bytes at the head (`960e7e22…`).

## B. The Linux census (item 2): the calls

Two workloads, both the static yew of §A, under `strace -f -n -v -xx`
in `px13-ubuntu` (strace 6.8), read by `notes/px58/census.py` (a
process's role by its execve: `yew --guard` the guard, `yew` the
editor, anything else other):

1. **yew's goldens** (`notes/px58/census-goldens.sh`): the oracle (C
   yew at `9ace98c2`, `tools/oracle --cc gcc --build-only`) and yew's
   `tools/goldens` with the static yew as a wrapper that `exec`s `strace
   -D -f` (so the PTY runner's pid and signals stay yew's): `version`,
   `help` and campaign 03's 62 editor cases by name, **64 of 64 green
   under strace** (`notes/px58/linux-census-goldens-verdicts.txt`), 102
   traces (`linux-census-goldens.txt`). The runner's `modern` profile
   (TERM xterm-256color, a terminal that answers the probe), 24 by 80
   (two cases 12 by 40).
2. **the typed session** (`notes/px58/census-session.sh`): `tests/
   mpx5-yew`'s keys typed by `tools/linux-tty` into the suite's own
   binaries on a pty as `pax` with PAX's environment (TERM=linux, an
   unsized pty), the whole session traced (`linux-census-session.txt`;
   the file saved alpha, beta, gamma, delta).

**The calls, 50 by name** (the union, editor and guard; counts over the
goldens, the session's within them):

| | calls |
|---|---|
| files | `read` 0, `write` 1, `close` 3, `fstat` 5, `openat` 257, `statx` 332, `getdents64` 217, `getcwd` 79, `mkdir` 83, `rename` 82, `unlink` 87, `linkat` 265, `chmod` 90, `fchown` 93, `readlink` 89, `readlinkat` 267 (`/proc/self/exe`), `fcntl` 72 (F_DUPFD_CLOEXEC of fd 0 and 1, F_GETFL/F_SETFL), `dup2` 33, `pipe2` 293 |
| terminal | `ioctl` 16 (§C), `poll` 7 |
| processes | `clone` 56 (the guard's fork), `clone3` 435 (the runtime's signal thread), `execve` 59, `wait4` 61, `setpgid` 109 (the guard's own group: EACCES from the parent once the child has exec'd, as POSIX says), `socketpair` 53 and `recvfrom` 45 (the spawn's handshake), `exit_group` 231, `getpid` 39, `gettid` 186, `tgkill` 234 (a stop raised at itself) |
| memory, start-up | `brk` 12, `mmap` 9, `mprotect` 10, `munmap` 11, `arch_prctl` 158, `set_tid_address` 218, `set_robust_list` 273, `rseq` 334, `prlimit64` 302, `getrandom` 318, `prctl` 157 (PR_SET_NAME `wolf-signal`), `futex` 202, `geteuid` 107, `getegid` 108 |
| signals | `rt_sigaction` 13, `rt_sigprocmask` 14, `rt_sigreturn` 15, `restart_syscall` 219 (strace's name for a wait resumed after a stop: the suspend goldens only) |

Failures, each by design: `mkdir` EEXIST (the state directories),
`statx`/`openat` ENOENT (the runtime and config lookups), `read` EAGAIN
(fd 0 non-blocking in the drain), `setpgid` EACCES (above).

**Signals.** The editor catches WINCH, CONT, TSTP, CHLD, TERM, HUP,
QUIT (yew's listen set, through wolf's signal thread) and ignores PIPE
(the runtime); **no SEGV, BUS or alternate stack** at 0.2.33. The guard
ignores HUP, INT, QUIT, TERM, TSTP, TTIN, TTOU and catches nothing.
**`/dev/tty`**: never opened by yew (pelt opens it in the session).

## C. The census: the terminal

**ioctls, exactly three** (yew's processes): TCGETS (5,124 in the
goldens), TCSETSW (1,508: wolf's `os_term_set_mode` is TCSADRAIN),
TIOCGWINSZ (108, on fd 1). The guard: TCGETS and TCSETSW (its restore
after a death). pelt adds TIOCGPGRP and TIOCSPGRP.

**The termios states yew sets** (strace's own decoding):

| shape | c_iflag | c_oflag | c_cflag | c_lflag | VMIN | VTIME | count (goldens) |
|---|---|---|---|---|---|---|---|
| raw (`rawios`) | ICRNL | OPOST\|ONLCR | B38400\|CS8\|CREAD | ECHOE\|ECHOK\|ECHOCTL\|ECHOKE | 1 | 0 | 612 |
| drain (`drainios`) | ICRNL | OPOST\|ONLCR | as found | as raw | 0 | 0 | 532 |
| poll (`pollios`) | ICRNL | OPOST\|ONLCR | as found | as raw | 0 | 1 | 266 |
| restored (the mode as found) | ICRNL\|IXON | OPOST\|ONLCR | as found | ISIG\|ICANON\|ECHO\|ECHOE\|ECHOK\|IEXTEN\|ECHOCTL\|ECHOKE | 1 | 0 | 98 (+4 by the guard) |

Bit by bit, the raw mode clears ICANON, ECHO, ISIG, IEXTEN and IXON and
keeps ICRNL, OPOST and ONLCR (G34: wolf 0.2.33's mode int cannot reach
them), every c_cc as found. **The window**: TIOCGWINSZ on fd 1, 24 by 80
from the runner and 0 by 0 from an unsized pty, where yew lays out 24
by 80 (`src/edit/driver.lu:213`); SIGWINCH caught.

**The escape classes yew wrote**, by name (ECMA-48's and the DEC
private modes', console_codes(4)), the goldens' (`modern`) and the
session's (TERM=linux):

| class | goldens | session |
|---|---|---|
| SGR | 6,178 | 73 |
| cursor position (CUP, `CSI r;c H`) | 3,522 | 63 |
| cursor visibility (`?25l` / `?25h`) | 390 / 492 | 14 / 15 |
| synchronized output (`?2026h` / `?2026l`) | 290 / 392 | 0 / 1 (restore) |
| cursor shape (DECSCUSR 2, 6, 0) | 214, 104, 102 | 4, 3, 1 |
| bracketed paste, mouse 1002, mouse 1006, focus 1004 (`h` / `l`) | 202 / 196 each | 2 / 2 each |
| alternate screen (`?1049h` / `?1049l`) | 102 / 196 | 1 / 2 |
| DECSC / DECRC (`ESC 7` / `ESC 8`) | 102 / 94 | 1 / 1 |
| kitty keyboard push `CSI >21u` / pop `CSI <u` | 102 / 196 | 0 / 2 |
| queries: kitty `CSI ?u`, DECRQM `?2026$p`, DA1 `CSI c` | 100 each | 1 each |
| cursor forward (CUF) | 86 | 1 |
| LF, CR | 69, 6 | 0, 0 |

No erase (EL, ED, ECH), no scroll region, no OSC in either (OSC 52 is
the clipboard's, not reached). SGR parameters: the goldens' truecolor
`38;2` (5,996) and `48;2` (1,076), `0`, `1`, `22`, `7`, `27`, `38;5`;
the session's 16-colour tier `37 90 0 40 1 22 30 41 47 43 97 46 44`.

**What 0.2.34 adds once yw05 bumps yew's pin** (`[os.editor.calls.note]`,
listed as coming, not measured): `os_term_restore_at_exit` (a duplicate
of the terminal at 3 or above, close-on-exec: `fcntl(F_DUPFD_CLOEXEC)`;
at exit `tcgetattr`, `pthread_sigmask`, `tcsetattr` TCSADRAIN, `write`:
TCGETS, TCSETSW, `rt_sigprocmask`, `write`, all served today) in place
of the guard (the guard's fork, exec, pipe and `/dev/fd/3` go);
`os_signal_wait_fds` (`poll(2)` on duplicates and one wake pipe, with a
deadline: `poll`, `pipe2`, served) in place of VTIME polling, so the
poll and drain TCSETSW shapes go; `fs_sync` (`fsync`, 74) and
`fs_sync_dir` (an `O_DIRECTORY` `openat` and `fsync`), both in PAX's
table; `fs_realpath` (a walk of `readlink`/`newfstatat` or glibc's
`realpath`); `os_clock_ns` (the vDSO's clock, or `clock_gettime` 228,
served); the mode's bits 5–7 (`RAW_CR`, `RAW_OUTPUT`, `STRIP8`: ICRNL
and OPOST cleared, ISTRIP set, which PAX's console stores and acts on
for ICRNL and OPOST, and stores for ISTRIP). px57, beside this lane,
measures these calls on PAX itself (its `user/edwolf` probe,
`tests/mpx5-jobs`' `eds` image); what yew does with them is yw05's.

## D. The gap table (item 3)

termwolf (`user/termwolf`) on PAX (`kmain_console`, the probe image) as
root and as `pax`, against the same binary on a pty in a container
(`tools/linux-tree`), and the halted screen read cell by cell
(`tests/mpx5-yew`'s Y2). served = byte-identical to Linux; dropped = an
escape the screen ignores, a bit kept and not acted on; divergent =
served with another answer; refused = an errno.

| row | Linux (pty) | PAX | verdict |
|---|---|---|---|
| isatty 0 1 2; the foreground group; `/dev/tty` opened, a terminal, its mode fd 0's | true; true; true | the same | served |
| the termios as found | iflag 0x100 oflag 0x5 cflag 0xbf lflag 0x8a3b, c_cc `03 1c 7f 15 04 00 01 00 11 13 1a 00 12 0f 17 16 00 00 00` | the same | served |
| every iflag, oflag and lflag bit flipped alone, TCSETS, TCGETS | kept | kept | served |
| cflag CS6, CS7, CREAD, PARENB | **not kept** (a pty keeps CS8, CREAD, no parity) | kept | divergent (not yew's) |
| c_cc, all 19 set and read back | kept | kept | served |
| wolf's mode as found; yew's raw, poll, drain modes and the termios each leaves; the mode back | 0x117; the four rows of §C | the same | served |
| VMIN 0 VTIME 0 / VTIME 1 / VTIME 5, nothing typed | 0 bytes at once / after a tenth / after half a second | the same, in bounds | served |
| OPOST\|ONLCR, OPOST cleared, ONLCR cleared (`ab LF cd CR`) | `ab CR LF cd CR` / `ab LF cd CR` / `ab LF cd CR` | the same | served |
| ONLRET set | `ab CR LF cd CR` | the same | served |
| OCRNL set | `ab CR LF cd LF` | `ab CR LF cd CR` | dropped (not yew's) |
| OLCUC set | `AB CR LF CD CR` | `ab CR LF cd CR` | dropped (not yew's) |
| TIOCGWINSZ before any key | 0 by 0 | **50 by 160** (the screen's grid, px19) | divergent by design (pax#68's model: the device last typed at) |
| TIOCGWINSZ after COM1 input; `os_term_size` | 0 by 0 | 0 by 0 | served |
| TIOCSWINSZ 30 by 100, read back; SIGWINCH; again, none; back, SIGWINCH | 30 by 100, true, false, true | the same (back to 50 by 160 as root) | served |
| DA1, CSI 6n, kitty `CSI ?u`, DECRQM 2026 | no answer in half a second | the same | served (a Linux VT answers DA1 `ESC [ ? 6 c` and 6n `ESC [ 3 ; 1 R`, §E: **no answer on PAX's screen**, px59's) |
| keys typed over COM1 in yew's raw mode (`a b ^C ^Z ^\ DEL ESC [ A .`) | `61 62 03 1a 1c 7f 1b 5b 41 2e` | the same | served |
| the keyboard's arrows, Home, End, PgUp, PgDn, Insert, Delete | a VT: `ESC [ A`…`D`, `ESC [ 1 ~`…`6 ~` (§E) | nothing at trunk; **the VT's sequences** from `c8ec73d` | **closed here** |
| the escape classes' bytes on the serial line (`termwolf screen`) | 890 bytes | the same 890 bytes | served |
| on the screen: text, CR, LF, SGR 0 1 7 30–37 39 40–47 49 90–97 | (console_codes(4)) | drawn | served |
| on the screen: CUP, HVP, CUU, CUD, CUF, CUB, CHA, VPA, EL 0 1 2, ECH, ICH, DCH, IL, DL, DECSTBM, DECSC, DECRC, the alternate screen, DECTCEM, DECSCUSR, bracketed paste, mouse 1002/1006, focus, synchronized output, kitty push/pop | (console_codes(4); paste, mouse 1006, focus, sync and kitty are no VT's either) | `<>`: read and dropped | **dropped (px59)** |
| on the screen: SGR 2, 3, 4, 22, 27, 101, `38;5` | dim, italic, underline, bold off, inverse off, bright background, 256-colour | drawn plain, or bold and inverse left on (22, 27) | **dropped (px59)** |
| on the screen: OSC 52 | a string, not drawn | `52;c;eA==` drawn as text (ESC `]` two bytes dropped) | **divergent (px59)** |
| system calls: yew's 50 | — | 47 in PAX's table; `set_robust_list` 273 and `rseq` 334 -ENOSYS (glibc copes); `restart_syscall` 219 is the kernel's own resume, PAX restarts by rewinding (px48) | served |

What yew's session needs and PAX serves: every call, every ioctl, every
termios state, the timed reads, the output processing, the window size
at 0 by 0, the guard's process group and `/dev/fd/3`, the save (temp,
`linkat`, `rename`, `chmod`, `fchown`). What a person at PAX's screen
and keyboard still lacks (px59): the screen's cursor addressing and
erase, the alternate screen, cursor visibility and shape, SGR 22 and 27
and the bright backgrounds, DA1 and the cursor report, the modifiers on
the cursor keys, Alt, the function keys.

## E. The keyboard, measured, and the gap closed (item 4)

A Linux virtual terminal's answer, black-box (`notes/px58/vtkeys.c`,
`vt-run.sh`): kasumi's own kernel image (7.2.8-1-cachyos, `f4c00d5d…`,
its VT, VGA console, i8042 and atkbd built in, as its
`/proc/config.gz` says) under QEMU 11.1.1 (TCG, a VGA display), a probe
as pid 1 that opens `/dev/tty1`, sets yew's raw mode there, asks the
window size and the four queries, then reads what the keyboard gives
while the host sends `up down right left home end pgup pgdn insert
delete dot` through QEMU's monitor; twice, the same rows
(`notes/px58/kasumi-vt-run.out`):

```
VT S: iflag 0x4500 oflag 0x5 cflag 0x4bf lflag 0x8a3b
VT W: TIOCGWINSZ 0, 25 rows 80 columns
VT Q: DA1 (CSI c): 1b 5b 3f 36 63
VT Q: the cursor's position (CSI 6n): 1b 5b 33 3b 31 52
VT Q: kitty's keyboard (CSI ? u): no answer in half a second
VT Q: DECRQM 2026 (CSI ? 2026 $ p): no answer in half a second
VT P: typed: 1b 5b 41 1b 5b 42 1b 5b 43 1b 5b 44 1b 5b 31 7e 1b 5b 34 7e 1b 5b 35 7e 1b 5b 36 7e 1b 5b 32 7e 1b 5b 33 7e 2e
```

terminfo's `linux` entry agrees (`kcuu1=\E[A`, `khome=\E[1~`,
`kend=\E[4~`, `kich1=\E[2~`, `kdch1=\E[3~`, `kpp=\E[5~`, `knp=\E[6~`).

**Closed here** (`c8ec73d`, `kernel/console/`, `cursor_key`): an
E0-prefixed set-1 make code of the cursor and editing block puts the
VT's sequence in the input through the line discipline as if typed
(so raw mode reads it and canonical mode echoes `^[[A` with ECHOCTL);
any other E0 key still gives nothing. At trunk the probe's `ps2` run
read `2e` alone (`notes/px58/first-boot/`, Y3 red); after, the VT's
bytes exactly (Y3 green, `kasumi-t2/`). yew's L mode moves by these keys
(`runtime/init.fl`: `<up>`, `<down>`, `<home>`, `<end>`, `<pgup>`,
`<pgdn>`), so a person at PAX's keyboard can now move in yew. Under a
day; the other gaps are px59's (§D).

## F. The session (item 5)

`tests/mpx5-yew`'s session image: `/bin/as 1000 1000 /bin/env
HOME=/home/pax /bin/sh -i -m` (pelt `90d7c64`), `/home/pax/notes.txt`
(alpha, beta, gamma; 1000:1000), typed over COM1
(`user/console/yew.keys`): `cd /home/pax`, `yew notes.txt`, then each
key a `^~` step 6 s apart on PAX (1.5 s on Linux): `G`, `O`, `d e l t
a`, ESC, `:`, `w` Enter, three empty steps, `:`, `q` Enter; then `cat
notes.txt` and `exit`. The window is 0 by 0 on both (COM1; an unsized
pty), so yew lays out 24 by 80 on both.

**yew draws its first frame on PAX**, moves, opens a line, inserts,
saves through its atomic save (temp file, `linkat`, `rename`, `chmod`,
`fchown`), quits, and pelt's `cat` shows `alpha beta gamma delta`. The
raw serial transcript (from `run 1:` to the kernel's `frames free`
line, every kernel `user:` line taken out, CR LF kept) is
**byte-identical to the container's: 3,732 bytes, sha256
`3ad835bdef3c…`** (`notes/px58/kasumi-t2/pax-session.raw`,
`linux-session.tty`). The kernel's own lines say yew pid 3 and its guard
pid 5 ran, the signal thread started in each, -ENOSYS 273 and 334 and
nothing refused.

**Every difference named against §D, at the first boot**
(`notes/px58/first-boot/`): one, at byte 3,279: an extra statusline
frame on PAX between `:w` and `:q`. yew's info message ("wrote
notes.txt, 5 lines") lasts 4 s (`MESSAGE_INFO_MS`, yew
`src/edit/message.lu:17`); PAX's 6 s pause outlived it, Linux's 1.5 s did
not, so PAX's yew repainted the statusline when the message expired and
Linux's did not before `:` replaced it. A timing of the keys, not a row
of §D: the keys now wait three empty steps after `:w` on both sides
(4.5 s more on Linux, 18 s more on PAX), past the expiry on both, and
the bytes match. `G` then `o` (the first text) opened a line after yew's
empty last line (the line after the final newline), saving `gamma`,
an empty line, `delta` with no final newline, the same on both sides;
`O` opens it above, which is the shape the contract asks.

**On the screen** (not the record): the framebuffer shows every frame's
text appended, CUP and the alternate screen dropped
(`build/mpx5-yew-*-session.ppm` in CI's artifact). The serial transcript
is what is compared, as the contract says.

The whole session boot under TCG on kasumi: 96 s (the probe image's:
17 s); yew's start under TCG fits inside the 6 s pause.

## G. The rows (item 6)

`tests/mpx5-yew` (`dbb6f03`, `45364a3`), its own suite (mpx5-lope's
shape), two images on `kmain_console`:

| row | what |
|---|---|
| Y0 | the build: kmain_console; yew, termwolf, pelt, `env`, `cat`, `as` static; both images; the container's runs |
| Y1 | the probe as root and as `pax`: every record the container's but the gap table's named rows (cflag's four, OCRNL, OLCUC; as root the window before any key and set back), each PAX's recorded answer; the screen run's 890 bytes the container's |
| Y2 | the halted screen (QEMU's screendump against `font/spleen-8x16.bdf`): the drawn classes as ECMA-48 says, every other `<>`, SGR 22 and 27 leaving bold and inverse on, OSC 52's text drawn |
| Y3 | the keyboard's cursor keys, sent through a second monitor: the VT's sequences |
| Y4 | yew's session byte-identical to the container's; `cat notes.txt` alpha beta gamma delta on both |
| Y5 | per boot: -ENOSYS 273 and 334 only, nothing refused, init's end, halted |

Wired as every suite (`159e1d3` the job and the tier's needs;
`9daafd7` `tools/ci-tiers.map`: yew's pin, builder, probe and keys
mpx5-yew's alone, and mpx5-yew in @user, @console, @asuser; `65fd73f`
`tests/ci-plan`, 195 PASS). No ISO rebuilt (px57's).

## H. The plants (P6)

Each a branch never merged, one commit on `45364a3`, dispatched `-f
tier=pr -f suites=mpx5-yew` (a `tier partial` run of the one suite on
native BIOS):

| plant | the break | run, job | red at | green at | verdict |
|---|---|---|---|---|---|
| A, `px58-plant-a` `c15467d` | a VMIN 0 read answers at once, VTIME ignored (`kernel/console` `read`) | **39689580461**, mpx5-yew 119532339241 | Y1 root and `pax`: `T: VMIN 0 VTIME 1 …: 0 bytes, early (0 ms)` where Linux's is `in bounds` | Y0, Y1 screen, Y2, Y3, Y4 (byte-identical: yew's polling spins between deadlines and writes nothing more), Y5 | as predicted |
| B, `px58-plant-b` `9f0bf41` | the cursor keys give nothing again (`cursor_key`'s answer times 0) | **39689583322**, mpx5-yew 119532308640 | Y3: `typed '2e'` | every other row | as predicted |

Extracts: `notes/px58/ci-39689580461-plant-a.txt`,
`ci-39689583322-plant-b.txt`. Both runs' builds on CI's runner gave the
same programs as `px13-ubuntu` (yew `c2daa653…`, termwolf `960e7e22…`,
pelt `5448cb27…`) and the same session digest (`3ad835bdef3c…`). The
first boot's Y3 red (`notes/px58/first-boot/`) is the same gap seen
before the fix.

## I. Issues to file (none filed)

**pax** (each for px59, "yew on PAX: the console", unless said):

1. The framebuffer console draws none of the cursor addressing yew
   writes (CUP 3,522 times in the goldens, 63 in a short session), nor
   cursor visibility (`?25l/h`), cursor shape (DECSCUSR), DECSC/DECRC
   or the alternate screen (`?1049h/l`): yew's frames are a smear on
   PAX's screen while COM1 carries every byte (Y2's rows; §D).
   `kernel/screen` and `tools/screen-ref` together.
2. SGR 22 (normal intensity) and 27 (inverse off) are dropped, so bold
   and inverse stay on after them; yew writes 22 in every frame (8 times
   in the session); 100–107 (bright backgrounds) and `38;5`/`48;5` drawn
   plain (Y2's SGR22, SGR27, SGR101, SGR38;5 rows).
3. PAX's console answers no DA1 (`CSI c`) and no cursor-position report
   (`CSI 6n`) where a Linux VT answers `ESC [ ? 6 c` and `ESC [ r ; c R`
   (§E); yew asks DA1 at every start, pelt asks 6n at every prompt.
4. An OSC string's text is drawn on the screen (`ESC ]` is two bytes
   dropped, then `52;c;eA==` drawn): yew's OSC 52 clipboard writes would
   land on the screen (the `OSC52` row).
5. The keyboard gives nothing for the function keys and nothing more
   for a modifier on a cursor key; Alt is not an ESC prefix (yew binds
   `A-…` throughout `runtime/init.fl`).
6. OCRNL and OLCUC are kept and not acted on (Linux's pty converts),
   and cflag's CS6, CS7, CREAD and PARENB are kept where Linux's pty
   forces CS8 and CREAD (§D): small, not yew's; a console lane's.
7. Not measured here: yew stopped and continued (`C-z`, SIGTSTP then
   SIGCONT: its suspend restores, stops and re-enters raw), a resize while
   yew runs, and yew from the keyboard rather than COM1 (the screen's 50
   by 160): rows for px59.

**yew** (listed for the maintainer, none filed): `G` lands on the empty
line after a final newline, and `o` there saves `gamma`, an empty line
and `delta` with no final newline (the first session's keys, both
sides: notes/px58/first-boot/linux-session.tty); whether that is C
yew's own behaviour was not checked against the oracle here.

## J. What was not done

- No ISO rebuilt (px57's); the playground takes yew in a later lane.
- Only native BIOS ran in CI (the merge gate); the four legs ran on
  kasumi (§K).

## K. The four legs on kasumi

`tests/mpx5-yew` at `c8ec73d`'s suite (the kernel fix in), native and
release × BIOS and UEFI under `taskset -c 0-3`, TCG
(`notes/px58/kasumi-t3/t3.boot.log`): **37 PASS, 0 FAIL**, every leg's
session the same 3,732 bytes (`3ad835bdef3c…`), the probe image's boots
15.5–17.2 s and the session's 94.6–96.1 s. The UEFI screen is the BIOS
one's (50 by 160: Y1's named window rows hold on every leg).
