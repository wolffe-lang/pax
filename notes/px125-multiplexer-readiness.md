# px125 — PAX for a terminal multiplexer: what it can do today

A terminal multiplexer keeps one server per user. The server holds every pane's pseudo-terminal and serves its
clients over a Unix socket; each client draws on the terminal it was started from, which on the machine itself is
PAX's console. This lane asked PAX every question such a program asks of its system, on PAX under QEMU and on Ubuntu
24.04 in a container, row by row: the plumbing (section A) and what the console draws, answers and sends (section
B). Two small fixes were made here, each with its rows red first: Ctrl-Space types NUL, and the console draws the
whole box-drawing block, the four arrows and the powerline separators. Every larger gap is an issue with its
reproducer.

**The short answer.** A server written for PAX today works: 32 ptys, each pane's program in a session of its own,
one epoll loop over every master and 16 Unix-socket clients, 50 MB through one pane with every byte in order and
every other pane answering within one clock tick, back-pressure confined to its writer, SIGWINCH and the signal keys
as on Linux, a stale socket detected and replaced, peer credentials. What is missing or small: room for processes
(64 threads in the whole machine; a wolf program takes two), a Unix stream's 4096-byte buffer, the timer and
signal descriptors and descriptor passing (all have workarounds), one wait in wolf-std over files, sockets and
signals together, and on the console wide characters, five sequences the Linux VT documents and PAX's console does
not draw, and the newer query answers. The rows are in `tests/mpx7-mux`.

Footprint: cross-cutting (`kernel/console` and `font/extent.txt` with `boot/font.S`; `.github/workflows/ci.yml`
gains the `mpx7-mux` job; `tools/ci-tiers.map`, `tests/ci-plan`, `tools/linux-tree`'s `--end-wait`; new
`tests/mpx7-mux`, `tests/mpx7-mux.d/`, `user/elf/muxprobe.c`, `user/muxwolf/`, `tools/mkmux`, `tools/mkmuxwolf`).

## 1. Forbidden, and what was read

- **The clean room.** No kernel's, terminal emulator's, multiplexer's or C library's source was read. The rows'
  questions come from the Linux manual pages (pty(7), unix(7), epoll(7), signal(7), termios(3), credentials(7),
  console_codes(4)), POSIX.1-2024's General Terminal Interface, the XTerm Control Sequences document as Ubuntu's
  xterm package ships it, and ECMA-48. Ubuntu was measured as a black box: the same static binaries, run as pid 1
  on a pseudo-terminal in a throwaway container. wolf-std (the org's own, public) was read at `77cf3210` for its
  terminal, process, signal, socket and file calls. `docs/SOURCES.md` (px125) lists every source with its digests.
- **QEMU only.** Every PAX row ran under QEMU with KVM; nothing ran on a physical machine.
- **Pins.** The wolf-std probe pins its own toolchain (`user/muxwolf/wolf-toolchain.toml`: wolf 0.2.39, wolf-std
  `77cf3210`), as the signal probe does, so it asks the std the rows name whatever the images' pins say.

## 2. The probe

- `user/elf/muxprobe.c`, a static C program, does a server's work in one process and prints one line a question
  (`A1.4 ...`); a line that starts with `~` is a measurement (a count, a time) and is never compared. Its pane
  programs are its own modes (`muxprobe pane`, a one-thread program that answers a typed line), so that A1 asks
  about ptys and the loop and not about how many threads a shell takes; A1.9 asks that question with pelt.
- `user/muxwolf/muxwolf.lu` does the same work with wolf-std alone (rows W1 to W13).
- The screen image plays `tests/mpx7-mux.d/cases.py`'s cases with px59's player (`user/elf/vtcases.c`), reads the
  console back cell by cell from QEMU's screendumps, and types keys at the PS/2 keyboard
  (`tests/mpx7-mux.d/screen.py`).
- `tests/mpx7-mux` holds them: M1 every row of the C and wolf probes against Ubuntu's (the references in
  `tests/mpx7-mux.d/linux/`, recorded in the suite's own container), or the line the ruled file names for PAX;
  M2 the kernel's refusals by name; M3 how the image ended; M4 every line of what the console drew, answered and
  sent, against `tests/mpx7-mux.d/screen.rows`; M5 the screen image's end; M6 the repaint at the size of the target
  machine's display (2560 x 1440).

## 3. A. The plumbing a server needs

Ubuntu is 24.04.5 in a container on a Linux 7.2 host; the probe is pid 1 there as it is on PAX. "works" means PAX
answers as Ubuntu does.

| # | question | PAX today | Ubuntu | verdict | evidence line (PAX) |
|---|---|---|---|---|---|
| A1.0 | processes at once | 60 forks, then `EAGAIN` (`refused: no free process slot`) | 100 (all asked) | gap #354 | `A1.0 100 processes at once besides this one: NO, fork EAGAIN after 60` |
| A1.1-A1.3 | 32 ptys in one process, a session each, one epoll object | yes | yes | works | `A1.3 one epoll object holds the 32 masters` |
| A1.4 | a line typed at all 32 at once, answered through one loop | yes | yes | works | `A1.4 typed at once, every pane answered through the one loop: yes` |
| A1.5 | 50 MB through one master, in order, none lost | yes; 5.97 s (8.4 MB/s) | yes; 82 ms | works (the rate a measurement) | `A1.5 the flood: 50000000 bytes through one master, in order, none lost` |
| A1.6 | the other panes answer during the flood | about 300 pings, none missed, every one inside one 10 ms tick | 6 pings (the flood ends first) | works | `~A1.6 pings 300 answered, 0 missed; latency median 0 ms, p90 0 ms, max 0 ms` |
| A1.7-A1.8 | closing masters ends their shells by SIGHUP; the ptys come back | yes; the count back to 0 | yes | works | `A1.8 28 masters closed: 16 shells ended by SIGHUP, 0 otherwise, 0 left running` |
| A1.9 | 32 pelt shells at once, each answering a line, then again after 5 s idle | 30 started, every one answered twice; the 31st fork `EAGAIN` | 32 of 32 | gap #354 | `~A1.9 started 30 of 32 (then EAGAIN), answered 30 once and 30 again after 5 s idle` |
| A2.1-A2.3 | a pane nobody reads stops only its writer | yes: the queue holds 20480 bytes, the writer asleep, the others answer, it resumes when read | yes (4095 bytes) | works | `A2.1 a pane nobody reads: its writer asleep, the master's queue full and still` |
| A2.4 | a master written non-blocking | `EAGAIN` after 20480 bytes, POLLOUT clear, the others writable | the same after 18048-22048 | works | `A2.4 a master its program never reads, written non-blocking: EAGAIN, POLLOUT clear; another master POLLOUT set` |
| A3.1-A3.2 | TIOCSWINSZ: SIGWINCH to that pty's group alone; `stty size` | yes | yes | works | `A3.1 TIOCSWINSZ on a master: its program heard SIGWINCH and read 41 120; another pane's heard nothing` |
| A3.3 | a pty inside a pty passes a resize end to end | yes | yes | works | `A3.3 a pty inside a pty: the inner program read 33 97, then 41 120` |
| A4.1-A4.2 | 0x03, 0x1c, 0x1a written to a master | INT, QUIT, TSTP to the foreground group | the same | works | `A4.2 at their defaults, sleep 30: 0x03 killed by INT, 0x1c killed by QUIT, 0x1a running` |
| A4.3-A4.4 | a parent that ignores SIGINT and SIGQUIT (burrowd's start before px123's hook) | the child inherits the ignore across exec unless it resets them | the same | works (the server must reset its panes' signals) | `A4.3 SIGINT and SIGQUIT ignored by the parent and inherited across exec: 0x03 running, 0x1c running` |
| A5.1 | a setsid daemon whose starter ended | its parent is pid 1, its own session, no terminal | the same | works | `A5.1 a daemon (setsid) whose starter ended: its parent is pid 1; its own session yes, no terminal yes` |
| A5.2 | after its starter's terminal hung up | still running | the same | works | `A5.2 after its starter's terminal hung up: still running` |
| A5.3 | its end | a zombie until pid 1 waits | the same | works | `A5.3 ended by SIGTERM: until its parent waits it is a zombie; then killed by TERM` |
| A5.4 | pid 1 (the console's program) ends | the kernel sends SIGTERM to what is left (§5) | not compared (the container ends with it) | as designed; px124 | `PAX: the end: SIGTERM to 1 process` |
| A6.1-A6.2 | a socket at a path: mode, owner, a user refused | the umask's mode; `EACCES`; chown honoured | the same | works | `A6.2 a user's connect to root's 0700 socket: EACCES` |
| A6.3 | 16 clients on one listener in the loop beside the panes | all accepted and answered; the panes answered meanwhile | the same | works | `A6.3 16 clients on one listener in the loop beside the panes: 16 accepted, 16 answered, 16 ended well; ...` |
| A6.4 | the peer's credentials | `SO_PEERCRED`: the client's pid, uid 1000, gid 1000 | the same | works | `A6.4 SO_PEERCRED: 16 of 16 name the client's own pid; the user's: uid 1000 gid 1000` |
| A6.5-A6.6 | a stale socket after a crash | the file stays; connect `ECONNREFUSED`, bind `EADDRINUSE`; unlink then bind | the same | works | `A6.6 then connect ECONNREFUSED, bind EADDRINUSE; unlink 0, bind 0` |
| A6.7 | SCM_RIGHTS | `sendmsg` `ENOSYS` | the descriptor passed | gap #356 (not needed: the server keeps every pty) | `A6.7 SCM_RIGHTS over a socketpair: sendmsg ENOSYS; nothing` |
| A6.8 | an abstract name; SEQPACKET or DGRAM at a path | refused by name (`EINVAL`, `ESOCKTNOSUPPORT`) | made | named (a path and a stream are what a server needs) | `A6.8 an abstract name: bind EINVAL` |
| A7.1 | a non-blocking unix stream | partial at 4096 bytes, then `EAGAIN` | 100000 bytes whole, 194208 in all | gap #355 | `A7.1 a non-blocking unix stream: a 100000-byte write partial; then EAGAIN` |
| A7.2 | EPOLLOUT while full and after the peer drained | none, then set | the same | works | `A7.2 EPOLLOUT while full: none; after the peer drained: set` |
| A7.3 | timerfd, signalfd, ppoll | `ENOSYS` each | a descriptor each; answered | gap #356 (workarounds: A7.4-A7.6) | `A7.3 timerfd_create: ENOSYS` |
| A7.4 | epoll_wait's deadline as the timer | 110 ms for 100 | 100 ms | works | `A7.4 epoll_wait with nothing to wait for and 100 ms: 0, no earlier than its deadline` |
| A7.5-A7.6 | an eventfd and a SIGCHLD self-pipe wake the loop | yes | yes | works | `A7.6 SIGCHLD through a self-pipe wakes the loop: yes` |
| A8.1 | raw mode and back on a pty | cfmakeraw's flags; put back field for field | the same | works | `A8.1 a pty put back: every field as saved` |
| A8.2 | a raw client killed by SIGKILL | its terminal stays raw; the master's holder puts it back from the master | the same | works (the server restores a pane whose client died) | `A8.2 a client in raw mode killed by KILL: its terminal is still raw (nobody restores it)` |
| A8.3 | raw mode and back on the console | cfmakeraw's flags; put back field for field (IXON clear as found) | the same on the container's terminal | works | `A8.3 the console put back: every field as saved` |

**A9, wolf-std at `77cf3210`** (`user/muxwolf`, rows W1-W13: each as Ubuntu's).

| # | question | wolf-std | verdict |
|---|---|---|---|
| W1-W2 | 8 ptys (`term.open_pty`), a shell leading a session on each (`process.fork`, `lead_session`, `term.open_controlling`, `exec`), lines through `fs.write_some`, `fs.read_chunk` | works on both | works |
| W3 | `signal.wait_fds` over 8 masters | answers the lowest ready index alone, one a call | gap wolf-std#144 (a flooding pane listed first starves the others unless the loop rotates its list) |
| W4 | `term.set_size`, then `stty size` | `40 120` | works |
| W5, W7 | 0x03 to a master; a server ignoring `interrupt()` | the pane ends by `interrupt()`; an inherited ignore holds unless `signal.reset` before exec | works |
| W6 | masters closed | the shells end by the hangup | works |
| W8 | `unix.listen`, `fs.set_mode 0600`, 4 clients | a user denied; all answered; `net.close_listener` unlinks the file | works |
| W9 | one wait over a master and a socket | `signal.wait_fds` refuses a socket's handle (`io`), `net.wait` a master's | gap wolf-std#144 |
| W10 | a stale socket | `unix.connect` refused, `unix.listen` `exists`; `fs.remove`, then listen binds | works |
| W11 | `term.restore_at_exit` | restores after an exit, not after `kill()` (as Linux: nothing runs) | works |
| W12 | the console raw through `term.set_mode` | raw and back | works |
| - | the peer's credentials | no call | gap wolf-std#145 |

What wolf-std lacks, as the issues ask for it:

```
// std.net.unix (wolf-std#145)
pub struct Peer { pid: int, uid: int, gid: int }
pub fn peer(s: net.Socket) -> Peer ! {unsupported, io}

// std.signal or std.net (wolf-std#144): one wait over files, sockets and signals, every ready element
pub struct Ready { meaning: int, files: List[int], sockets: List[int] }
pub fn wait_all(files: List[fs.File], sockets: List[int], set: int, deadline_ms: int) -> Ready ! {invalid, io, unsupported}
```

Not asked of wolf-std: a timer descriptor (the wait's deadline serves) and descriptor passing (the server keeps every
pty).

## 4. B. What the console draws

Measured on PAX's console under QEMU (1280 x 800, 160 x 50 cells, unless named) and compared with xterm as the
XTerm Control Sequences document describes it; where the Linux VT is PAX's reference (px59), console_codes(4) says
what it documents. The lines are `tests/mpx7-mux.d/screen.rows`'.

**B1, the screen's operations.**

| case | PAX today | verdict |
|---|---|---|
| alternate screen `?1049` on and off; DECSC/DECRC (`ESC 7`, `ESC 8`); DECSTBM; IL, DL (and inside a region); ICH, DCH, ECH; EL 0-2; ED 0-2; autowrap; CUP, CHA, VPA | as xterm | works |
| `?47` (the old alternate screen) | ignored | not in console_codes(4); named in #357 |
| `CSI s` / `CSI u` (SCOSC/SCORC) | ignored | gap #357 (console_codes(4) documents them) |
| RI (`ESC M`) at the region's top | does not scroll | gap #357 (documented) |
| IRM (`CSI 4 h`) | overwrites | gap #357 (documented) |
| DECOM (`CSI ? 6 h`) | ignored | gap #357 (documented) |
| DECAWM off (`CSI ? 7 l`) | still wraps | gap #357 (documented) |
| SU/SD (`CSI S`, `CSI T`), REP (`CSI b`), CHT (`CSI I`; HT itself works) | ignored | not in console_codes(4); named in #357 |

**B2, SGR.** The 16 colours, their backgrounds, reverse, `22`, `27` and `39` exact; bold drawn as the bright colour
(15, and 9 for bold red); dim as 8, italic as 2, underline (and `4:3`, `21`, an underline colour) as 6 or 14: the
VT's colour renditions (approximated); 256-colour and true colour mapped to the nearest of the 16 (approximated); the
colon form `38:2::r:g:b` drawn in the default colour (misparsed: the VT's parser takes `;` alone); blink, conceal,
strikethrough and overline ignored. Verdict: works as the Linux VT (px59 holds it); a client that wants more colours
than 16 gets the nearest.

**B3, glyphs and widths.**

| case | before | after px125 | verdict |
|---|---|---|---|
| block elements U+2580-U+259F | 32 of 32 | 32 of 32 | works |
| braille | 29 of 29 sampled (every pattern in the font) | the same | works |
| Latin-1 | 5 of 5 | the same | works |
| box drawing, light, heavy, double, rounded | 8, 1, 0, 0 of 11, 11, 11, 8 | all | small fix made |
| the whole box block U+2500-U+257F | 9 of 128 | 128 of 128 | small fix made |
| powerline separators U+E0A0-U+E0A2, U+E0B0-U+E0B3 | 0 of 7 | 7 of 7 | small fix made |
| arrows U+2190-U+2193 | 0 of 4 | 4 of 4 | small fix made |
| a code point with no glyph (U+1F600, U+2603, U+4E2D) | `?` | `?` | named |
| a CJK character, a combining mark, an emoji | one cell each (the cursor one column on); a combining mark a `?` of its own | the same | gap #357 (xterm: two cells, none, two) |

The font is Spleen 8x16 (already vendored, BSD-2-Clause); `font/extent.txt` now names the whole box block, the
arrows and the separators, and `boot/font.S` holds 690 glyphs (was 560).

**B4, the cursor and the answers.** DECSCUSR is consumed and changes nothing (the VT's); `?25 l` and `h` hide and
show it. DA1 is answered `ESC [ ? 6 c`, DSR 5 `ESC [ 0 n`, CPR and DECXCPR `ESC [ 1 ; 1 R`: as the VT. No answer to
DA2, DA3, DECRQM (2004, 1049, 25, 1006, 1004, IRM), XTVERSION, OSC 10, the kitty keyboard query `CSI ? u`, DECRQSS
or XTGETTCAP: a client must time out (half a second here) and assume the VT. Verdict: works as the VT; named in
#357.

**B5, input.**

| key | bytes | verdict |
|---|---|---|
| Ctrl-Space | `20` before, `00` after px125 | small fix made (a multiplexer's default prefix) |
| Ctrl-@, Ctrl-A, Esc, Tab, Enter, Backspace | `00`, `01`, `1b`, `09`, `0d`, `7f` | works |
| Ctrl-2 | `32` (a digit) | as the VT |
| Alt-a | `1b 61` | works |
| arrows with Shift, Alt, Ctrl, Ctrl-Shift | `ESC [ 1 ; m X`, m 2, 3, 5, 6 | works |
| Home, End, PgUp, Insert, Delete | `ESC [ 1 ~`, `4 ~`, `5 ~`, `2 ~`, `3 ~` | the VT's |
| F1, F5, F12; Shift-F1; Ctrl-F1; Alt-F1 | `ESC [ [ A`, `ESC [ [ E`, `ESC [ 24 ~`; `ESC [ 23 ~`; as F1; nothing | the VT's (Alt-F1 switches consoles there) |
| Shift-Tab; Ctrl-Backspace | `09`; `7f` | the VT's |
| bracketed paste (2004), focus (1004) | nothing ever sent: the console has no paste and never loses focus | named |
| SGR mouse | 1002 with 1006 (px117); 1000 and 1003 send nothing | px117's |

**B6, OSC and DCS.** OSC 0, 2 (ended by BEL or ST), 8, 52 (short and 4 KiB) and an unknown OSC are swallowed whole:
nothing drawn. DCS, APC, PM and SOS strings are drawn as text after their introducer (`a1$r0mb` for `a`, a DECRQSS
answer, `b`). That is console_codes(4)'s Linux console, which lists them as not implemented; kept as the VT's
(R-px125-4) and named in #357 for a client: never send them to the console.

**B7, the repaint.** `muxprobe paint` on the console, under KVM: 100 full screens in each of three forms, each
screen one `write`: "cells" a cursor motion before every cell, "runs" one motion a row and then the row's
characters, "coloured" an SGR colour before every cell. Then 1000 writes of one cell each. The range of five
quick checks:

| display | grid | cells | runs | coloured | 1000 one-cell writes |
|---|---|---|---|---|---|
| 1280 x 800 | 160 x 50 | 1010-1060 ms | 1000-1010 ms | 1000-1070 ms | 50-60 ms |
| 2560 x 1440 (the target machine's) | 256 x 90 | 1100-1160 ms | 1000-1020 ms | 1040-1110 ms | 50-70 ms |

About 10 ms a full screen in every form and at both sizes, though 256 x 90 is 2.9 times the cells: under QEMU the
cost is not per cell, and what it is was not taken apart here. The number a compositor's damage tracking has to
beat is 10 ms a full frame; one changed cell costs about 50 microseconds. The grid is at most 256 columns
(`kernel/screen`), so a 2560-pixel display shows 256 columns and leaves the right 512 pixels blank. On the metal
the framebuffer is write-combining and never read (px87); not measured here.

**B8, through burrow's `ssh -t`.** Not measured in this lane (R-px125-6). What is known: PAX's pty carries every
byte value in raw mode (A1.5's stream is every byte value, checked in order), and px123's rows hold the size, a
resize and Ctrl-C, Ctrl-\ and Ctrl-Z through burrow's `ssh -t` (`tests/mpx5-burrowd` B19-B27).

## 5. A5 and what px124 changes

Today a console image's first program is pid 1 (`/etc/pax-run`), and on an installed system that is the login
shell. A daemon that calls setsid is reparented to pid 1 and outlives its starter's hangup (A5.1, A5.2), and it is a
zombie until pid 1 waits for it (A5.3), so a pid 1 that never waits leaves zombies. When pid 1 ends, the kernel
ends everything it left (`PAX: the end: SIGTERM to N process`, then SIGKILL): the server of a multiplexer started
from the console cannot outlive the console session. px124 is changing pid 1 and adding a per-user runtime
directory; after it, A5's rows will say who reaps a daemon and where its socket lives, and A5.4 will no longer be
the end of the machine. Nothing here designs that.

## 6. Prediction, scored

`notes/px125/prediction.txt`, written before the first change.

| P | said | scored |
|---|---|---|
| P1 | 32 ptys, sessions, one epoll object | held |
| P2 | 50 MB in order, none lost | held |
| P3 | every ping answered, worst under 250 ms; PAX's rate a fraction of Linux's | held: every ping inside one tick; 8.4 MB/s against 610 |
| P4 | 20480 bytes before the writer stops; non-blocking `EAGAIN` at 20480 | held |
| P5 | SIGWINCH, `stty size`, the nested resize | held |
| P6 | the signal keys; the inherited ignore; a reset needed | held |
| P7 | pid 1 reparents and reaps; the end of pid 1 ends everything | held |
| P8 | mode, owner, `EACCES`, 16 clients, `SO_PEERCRED`, the stale file; no SCM_RIGHTS; refusals by name | held |
| P9 | partial writes, `EAGAIN`, EPOLLOUT; timerfd, signalfd, ppoll `ENOSYS`; the deadline, eventfd, self-pipe | held; the 4096-byte unix buffer not predicted |
| P10 | termios raw and back; a SIGKILLed client leaves raw | held |
| P11 | wolf-std works; lacks peer credentials and an all-ready wait | held |
| P12 | B1 as xterm; CSI s/u, REP, SU/SD, DECOM, IRM as the VT | held for the ops; wrong for CSI s/u, DECOM, IRM: the VT documents them and PAX does not draw them |
| P13 | SGR | held |
| P14 | nine box glyphs; powerline `?`; Spleen has them | held |
| P15 | DECSCUSR, ?25, 6n and DA1 answered; DA2, DECRQM not | held |
| P16 | no paste or focus; arrows' `1;m`; Ctrl-Space a space | held |
| P17 | DCS drawn as text, a small fix | measured as predicted; not fixed (R-px125-4: the VT draws them too) |
| P18 | a repaint at 2560 x 1440 in tens of milliseconds | held (about 10 ms) |
| P19 | burrow 8-bit clean | not measured (R-px125-6) |
| P20 | three small fixes; the rest issues | two fixes made (Ctrl-Space, the glyphs); the DCS fix not made |

## 7. Decisions

Each implemented as recommended.

- **R-px125-1, the probe's toolchain: its own file, recommended.** `user/muxwolf/wolf-toolchain.toml` pins wolf
  0.2.39 and wolf-std `77cf3210` for that one probe, as the signal probe pins its own; the images' pins are left as
  trunk has them. (b) move the images' pins (another lane's change).
- **R-px125-2, the process slots: an issue, recommended.** 64 slots is `kernel/sched`'s and `boot/sched.S`'s table,
  the kernel's core: not a few lines. (b) raise the constant here (every suite's footprint, untested beyond).
- **R-px125-3, A1's panes: one-thread programs, recommended.** A1 asks about ptys and the loop with `muxprobe pane`;
  pelt shells took two slots each and made A1 depend on when pelt's runtime starts its second thread. A1.9 asks the
  shells' question on its own.
- **R-px125-4, DCS, APC, PM and SOS: as the Linux VT, recommended.** console_codes(4) lists them as not implemented
  on the Linux console, which draws their payload, and px59 holds PAX to it. (b) swallow them to ST, a few lines in
  `kernel/screen` but a departure from the VT that px59's rows would have to rule.
- **R-px125-5, RI, SCOSC/SCORC, IRM, DECOM, DECAWM off: an issue, recommended.** Each needs a measurement on a
  Linux VT and `tools/screen-ref` taught the same, as px59 measured the rest. (b) draw them here from the document
  alone.
- **R-px125-6, B8: not measured here, recommended.** The `ssh -t` rows live in `tests/mpx5-burrowd`, whose hook
  px123 is changing; one row there (every byte value both ways through `ssh -t`, raw at both ends) belongs after
  px123's merge. (b) a second burrowd image in this suite.
- **R-px125-7, the Linux references: recorded and committed, recommended.** `tests/mpx7-mux.d/linux/` holds Ubuntu's
  transcripts with `record.meta` (the container image, the binaries' digests), recorded by `--only linux --record`;
  the boot compares with them, so the boot needs no container. (b) run the container on every boot (root or
  podman on every CI leg).
- **R-px125-8, the font: the whole box block, the arrows and the separators, recommended.** Spleen has all of
  them, and a client's borders and status line need more than the nine the games used. (b) only the 11 a split's
  borders use.
- **R-px125-9, the bounds: loose, recommended.** M1 bounds the latency during the flood at one second and the pty
  count's move at zero; the flood's rate is a measurement, never a bound, so a CI leg without KVM does not fail it.

## 8. Issues filed

| issue | what |
|---|---|
| #354 | 64 thread slots for the whole machine |
| #355 | a Unix stream socket holds 4096 bytes |
| #356 | sendmsg/recvmsg (SCM_RIGHTS), timerfd, signalfd, ppoll |
| #357 | the console's subset: RI, SCOSC/SCORC, IRM, DECOM, DECAWM off; widths; the unanswered queries |
| wolf-std#144 | one wait over files, sockets and signals, every ready element |
| wolf-std#145 | a Unix socket's peer credentials |

## 9. Evidence index

Every PAX row ran on a Linux x86-64 build host under QEMU with KVM, in the Ubuntu 24.04 container
(`localhost/px75-ubuntu:2`); Ubuntu's rows in throwaway containers of the same image. The quick checks below are
the suite's own runs at a commit (build, the Linux side, the boot on native BIOS); the records, by
`notes/px125/rig/` (the recorder's steps mode, `--keep-going` and `--preflight`), are taken once trunk has
settled, and their files, digests and END lines are in the pull request.

| check | at | what it said |
|---|---|---|
| the Linux references | `f9cd0c95` (the rows' commit) | recorded in the container: `tests/mpx7-mux.d/linux/record.meta` (muxprobe `5095ff1d…`, muxwolf `5a788505…`, plumb.txt 69 lines, wolf.txt 15) |
| rows red | `f9cd0c95` | M0-M3 PASS for both probes (61 and 15 rows and bounds; 5 and 0 refusals, each ruled; the daemon's SIGTERM after init's exit); **M4 red, 8 lines**: `FAIL M4 B5 ctrl-space: 20; expected 00` and the seven B3 lines (`box-light: 8 of 11 drawn`, `box-heavy: 1 of 11`, `box-double: 0 of 11`, `box-round: 0 of 8`, `box-all: 9 of 128`, `powerline: 0 of 7`, `arrows: 0 of 4`); M5, M6 PASS; `END boot exit=1` (log sha256 `d0caed3a…`) |
| the font's table | `5673d03d` | `tools/mkfont --check`: `boot/font.S matches the font (690 glyphs …, in 11 ranges)`; `tests/ci-plan` PASS |
| green | `5673d03d` (the code of the head; what follows it is prose) | `END build exit=0`, `END linux exit=0` (`PASS M0 (linux): … each row as the committed reference`), `END boot exit=0`: M1-M3 as at the rows' commit, `PASS M4 … 134 lines of what the console drew, answered and sent, each as screen.rows has it`, M5, M6 PASS (log sha256 `12994cd9…`) |
| the plant | `px125-plant-ctrl-space`: one hunk in `kernel/console` (Ctrl-Space a space again) over the head (its quick check over `5673d03d`, the same code) | red by name, one line alone: `FAIL M4 B5 ctrl-space: 20; expected 00`, `FAIL M4 native bios auto: 1 of the screen's lines differ`; M0-M3, M5, M6 PASS; `END boot exit=1` (log sha256 `e7d3ef63…`) |

While the rows were written, the quick checks found four of the probe's own faults, fixed before the rows'
commit: a pane table too small for the whole run (A1.9, A8.2 and A8.3 had answered from a stale `errno`), A1's
shells taking two slots each (R-px125-3), W3 racing Linux's echo, and M3 naming init's own exit as the daemon's.

## 10. Done-when

- [x] the prediction, committed first; scored (§6)
- [x] sections A and B as tables, each row PAX's line and Ubuntu's (§3, §4)
- [x] the two small fixes, each with its rows red first (Ctrl-Space; the glyphs)
- [x] issues filed for the rest (§8)
- [ ] the full records, once trunk has settled
- [x] the plant, red by name (its quick check; its record with the others)
