# px129 — the console draws full-screen programs slowly on real hardware

At the installed machine's console (a 2560 × 1440 UEFI framebuffer) full-screen programs drew visibly slowly, while
the same programs over `ssh -t` drew quickly. This lane measured where the console's drawing time went, under QEMU at
that mode and on the machine itself as far as an ordinary user can over ssh, and changed the screen so that it draws
only what changes, once a write.

- **The cause, as the code and QEMU's numbers name it:** kernel/screen drew every cell a program wrote, at the moment
  it was written, whether or not its pixels changed, and it drew a cell through a loop with two divisions for every
  pair of pixels. So a clear followed by a repaint drew the screen twice; a scrolled line drew every cell of a screen
  of text (the metal's scroll never reads the framebuffer, px87); with the cursor shown, each character drew two cells;
  a program that rewrote its whole screen drew it all again even when nothing changed.
- **The fix:** a second grid records what each cell of the framebuffer shows. A write updates the cell grid in RAM and
  only marks cells; when the write ends, each marked cell that differs from what it shows is drawn, a run of
  neighbouring cells a pixel row at a time (whole write-combining lines, in order), each glyph row's four stores picked
  from the cell's four pixel pairs by a shift and a mask. The picture after every write is the same as before.
- **The 256-column cap** is lifted to 320, so 2560 pixels at one scale show a whole 320 × 90 grid (pax#357's part).
- **Measured under KVM at 2560 × 1440** (the CPU's share alone, since QEMU's framebuffer is host memory): a full screen
  10.6 → 4.2 ms (at 256 and 320 columns respectively), ten scrolled lines 101 → 4.1 ms, a clear and a repaint
  20.0 → 4.5 ms, the cursor shown through a repaint 21.2 → 4.6 ms, yew's F mode opening 7.8 → 2.3 ms, a step of cub
  11.2 → 5.2 ms (§4).
- **yew's F mode keypress is cheap to draw** before and after: yew already sends only the cells that change (169 and
  172 bytes for Down and Up, about 126 cells). On the installed machine yew answers a key in about 1.3 ms on its own
  pseudo-terminal, and its CPU is idle (§6). A keypress's visible delay at the console can only come from drawing those
  126 cells, which a run of the timing program at the machine's console will price (§5).

Footprint: cross-cutting (`.github/workflows/ci.yml` gains the `mpx3-conspeed` job; `tools/ci-tiers.map` and
`tests/ci-plan` its paths; `kernel/serial` and `kernel/panic` are the kernel's core; new `tests/mpx3-conspeed`,
`tests/mpx3-conspeed.d/`, `tools/mkconspeed`, `user/elf/conspeed.c`, `keylat.c`, `cpugaps.c`; `kernel/screen`,
`kernel/user`, `kernel/console`, `boot/screen.S`, `tools/screen-ref`, `tests/mpx3-screen`).

## 1. Forbidden, and what was read

- **The clean room.** No kernel's, terminal emulator's, firmware's, driver's or C library's source was read. The
  drawing is written from kernel/screen as it was and from the Intel SDM's account of write-combining memory; the
  programs' behaviour was measured black-box (their output on a pseudo-terminal, strace of the binaries an image
  ships). `docs/SOURCES.md` (px129) lists every source.
- **The installed machine.** Only the lane's own directory under the account's home was written there (the timing
  program, its wrapper, the recorded streams, the latency probes and a nine-file repository for them); `/proc`,
  `/sys` and what an ordinary user can see were read. No root, no console input, no reboot.
- **Hosts.** A Linux build host (Intel Core i7-12700KF) for every build and boot, in an Ubuntu 24.04 container
  (QEMU 8.2.2, OVMF, gcc 13.3) with KVM, on a light slot (two P-cores); the build Mac for git only.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `211e5c7c` | the fresh clone's `git rev-parse` |
| wolf | 0.2.35 (`kernel/wolf.pin`), archive sha256 `4cc4045b…dad1a` | `tools/fetch-wolf`, by digest |
| Limine | 12.9.1 | `tools/fetch-limine`, by digest |
| yew | `/bin/yew` of the installed image, sha256 `edcca94a22a424753739fcb5d9682ccf2b09bfb9b598fa6bc9578f87cdb14bb4` | read from the machine, run unmodified |
| cub | the installed `cub`, sha256 `8056dfd4a24af117d70b99721615ea475df74bf04955d22546b32bb04db1045f` | read from the machine, run unmodified |
| the installed machine's framebuffer | 2560 × 1440, 32 bpp, pitch 16384, RGB 8:16 8:8 8:0, at physical `0x4000000000` | its `/proc/pax-boot` |
| conspeed | `e03939be…de1c` (tools/mkconspeed at this head) | the same binary on the machine, in QEMU and in the records |

## 3. The instruments

- **`user/elf/conspeed.c`** (tools/mkconspeed; static, glibc): one command at any terminal. It writes test frames to
  the terminal inside the alternate screen with the cursor hidden, each frame one `write`, timed with RDTSC (PAX's
  CLOCK_MONOTONIC moves in 10 ms ticks), the TSC's rate taken over an idle second before and after; then it puts the
  terminal back (main screen, cursor, rendition, margins, mouse modes, the palette for TERM=linux) and prints one
  table: `unit` (a fixed CPU loop, the yardstick for a test's drawing), `bytes` (a screen's worth of `ESC [ m`, nothing drawn),
  `cell`, `plain` (a), `same`, `sgr` (b), `scroll1` and `scroll10` (c), `clear` (d), `cursor`, and the recorded
  streams (e): `fuss` (yew's Down and Up in F mode), `fussopen` (F mode's opening), `cub` (four steps of cub).
- **The streams** (`tests/mpx3-conspeed.d/streams`, its README): yew started as `yew .` in a small repository and cub,
  each the binary the image ships, on a Linux pseudo-terminal of 256 × 90 with TERM=linux; cub's writes taken one by
  one under strace.
- **On the installed machine:** one command at the console (a two-line wrapper outside the tree runs conspeed over
  the three streams and saves the table beside it). Over ssh, two probes: `keylat` (a full-screen program on a pseudo-terminal of
  its own, a key typed and the time to the frame's first and last byte) and `cpugaps` (how much of the CPU a spinning
  program gets).
- **In QEMU:** `tests/mpx3-conspeed` boots kmain_console at 2560 × 1440 with `fbwrite` (the metal's scroll) and no
  COM1, conspeed as init over the streams, and reads the table off the screen (`screen-run.py`: the monitor's
  screendump every 3 s, each cell matched against the BDF's glyphs), since with no UART the kernel keeps only its
  first 64 KiB of console and the table comes after megabytes of frames.

## 4. QEMU: before and after

Native tier, UEFI, 2560 × 1440, `fbwrite`, no COM1, the least of each test's frames (ms). Trunk KVM is the red record
at the rows' commit (`18761431`, record sha256 `1f4f8277…`, §8). Trunk's
grid is 256 × 90, px129's 320 × 90 (25 % more cells in the synthetic tests; the streams were recorded at 256 wide).

| test | trunk KVM | px129 KVM | trunk TCG | px129 TCG |
|---|---|---|---|---|
| unit | 1.787 | 1.790 | 1.788 | 1.788 |
| bytes (23,040 at trunk, 28,800 at px129) | 1.569 | 1.231 | 18.97 | 19.19 |
| plain (a) | 10.614 | 4.219 | 103.86 | 46.60 |
| same | 10.768 | 1.984 | 103.64 | 31.41 |
| sgr (b) | 25.992 | 16.050 | 266.59 | 212.02 |
| scroll1 (c) | 8.390 | 2.525 | 77.36 | 20.61 |
| scroll10 (c) | 101.428 | 4.145 | 772.13 | 49.73 |
| clear (d) | 20.021 | 4.527 | 178.85 | 51.91 |
| cursor | 21.216 | 4.625 | 183.40 | 52.09 |
| fuss (e) | 0.056 | 0.021 | 0.581 | 0.237 |
| fussopen (e) | 7.817 | 2.317 | 74.99 | 19.49 |
| cub (e) | 11.153 | 5.230 | 120.56 | 71.26 |

(trunk KVM is the red record's screen; px129 KVM is `tests/mpx3-conspeed.d/selftest/green-kvm.txt`, the same kernel
code as the head, its comments apart; the TCG columns are `red-tcg.txt` and `green-tcg.txt` there.)

**What the numbers say.** At trunk every write drew what it wrote: `same` cost what `plain` did, `clear` twice
`plain`, `cursor` twice `plain`, and one scrolled line about one full screen (`scroll10` ten of them). After px129 the
cost follows the cells that change: `same` is the parse alone, `clear` and `cursor` are `plain`, ten lines one screen.
Per cell drawn, the CPU's share fell from 0.53 µs to 0.11 µs (conspeed's derived line: `plain` less its bytes; the
divisions and per-pixel tests gone).
What remains in `sgr` and `cub` is mostly the bytes: about 50 ns a byte under KVM, which `sgr`'s 288 KB and `cub`'s
82 KB make the larger share (R-px129-8).

**The UART.** With COM1 present (the harness's usual machine) every byte is also two port accesses, which QEMU serves
in user space: under KVM about 6 µs a byte, which swamps the drawing (a table with COM1, kept in the lane's
evidence: `bytes` ≈ `plain` ≈ `clear`). The installed machine has no COM1, as px76 recorded for it, so the rows boot
without one.

**The clock.** PAX's CLOCK_MONOTONIC lost time during the tests: a console write runs with interrupts off, and the
ticks that fall inside it are lost. At trunk the tick clock kept 35 % of the time the tests took under KVM (84 %
after px129, the writes being shorter). px125's B7 ("about 10 ms a full screen" at both sizes) read that clock; the
10 ms was a tick, and the true cost at 256 × 90 was about the same by coincidence (R-px129-6).

**A second host.** The rows were first bounded on one host's tables (a desktop i7-12700KF), each against a test's raw
`ms least` in units. On a laptop i7-10870H the quick take at this branch's head read the fix's `sgr` at 13.26 units
(BIOS; 12.43 UEFI) against 11.5, and `cub` at 4.52 against 4.3: red with the fix in. Its BIOS screen is
`tests/mpx3-conspeed.d/selftest/green-kvm-10870h.txt` (`6edfa215`, screen text sha256 `c8f115c3…`), and rows.py at
`a6d2a2ac` fails it at C3 and C7. The laptop runs the unit as fast as the desktop (1.72-1.85 ms against 1.79), but a
byte's parse costs about half as much again (62-66 ns against 43). `sgr` and `cub` are mostly bytes, so a bound on
their raw figures carried the host's byte cost. The rows against the unit now hold a test's drawing (`731990dc`): its
`ms least` less its bytes at the same boot's `bytes` rate (`bytes` is 9,600 `ESC [ m`, a parse with nothing drawn). In
units of each boot's own `unit`:

| a test's drawing | trunk, desktop | trunk, laptop | px129, desktop | px129, laptop (BIOS; UEFI) | bound |
|---|---|---|---|---|---|
| plain (C2) | 5.12 | 17.14 | 1.65 | 2.09; 1.93 | 3 |
| sgr (C3) | 6.65 | 19.35 | 2.76 | 3.85; 3.11 | 5 |
| scroll1 (C4) | 4.73 | 17.35 | 1.40 | 1.82; 1.77 | 2.8 |
| fussopen (C7) | 3.88 | 16.04 | 0.97 | 1.34; 1.18 | 2.3 |
| cub (C7) | 3.23 | 10.49 | 0.97 | 1.57; 1.34 | 2.3 |
| fuss (C7) | 0.02 | 0.08 | 0.01 | 0.01; 0.01 | 0.05 |

(The selftest's tables: `red-kvm.txt` and `green-kvm.txt` on the desktop, `red-kvm-10870h.txt` and
`green-kvm-10870h.txt` on the laptop; trunk at 256 columns.) Each bound sits 1.3 times or more from the fix's worst and
from trunk's best. The laptop's trunk is slower still against its unit (its package read 91-100 °C through the trunk
boot), so every row but C1 is red there, yew's keypress among them (record sha256 `fa7c961a…`, §8). Under TCG these
rows are still SKIPPED by name (R-px129-3). No CI leg runs them under KVM: a hosted runner has `/dev/kvm` (root:kvm,
0660), but the job's user cannot open it, so `--accel auto` takes TCG there, as every other suite's leg does. These
rows are held by local records only (R-px129-11).

**mpx5-pty's session (pax#382).** At `4f3b30f6` the hosted mpx5-pty leg (TCG) went red in two attempts of two at
Y3 session-root, `S|4`: one `$ ` where Linux's reference has two before `stty size; echo :do''ne2:`. The session's
driver (user/elf/ptyprobe.c) resized the pty the moment the command's marker `:done1:` came. Whether pelt redrew its
prompt for the new size turned on how far pelt had got from the command to its prompt: before the prompt, pelt draws
it once; after it, pelt redraws it. The race is trunk's. In ten session boots under TCG it failed once at the base
`0e2843cf` and twice at `4f3b30f6`, and none of ten under KVM at either. Between the marker and the resize, the
driver's only work is one console line, which this branch makes cheaper, so the branch moves the odds; on the hosted
runners it moved them far enough to fail the row. The driver now waits for pelt's prompt after the marker, then as long
again as it waits before typing a key, before each of its two resizes (`9a992b29`). Linux's side was recorded again
with that probe, on the same kernel and QEMU (`08a1a31b`). The session's transcripts came out byte for byte the
reference's; the probe's matched too, but for P10b#2, a row that R-px111-6 rules. As a rate
(`notes/px129/rig/pty-rate.manifest`: the session image booted 20 times under TCG, each run checked as the suite
does), the rig before the fix (`f2524f73`) is red, `session-root differs in 2 of 20 boots` (record sha256
`e6f49c7a…`, §8); the head's rate is in the PR's records.

## 5. The installed machine

A person at the console runs the wrapper's one command; its table is saved beside it. **Not yet run at this writing;**
the note's evidence index will name the table when it is in. What is measured from ssh:

- `cpugaps 5`: the spinner had 99.9 % of the CPU, 177 gaps over 20 µs, the longest 0.068 ms, none over 0.1 ms. The
  machine is idle: no thread polls in the background, so a key's interrupt switches to the reader at once (§6).
- `conspeed -q -o /dev/null` and a run on a pseudo-terminal over ssh: the program runs on PAX, RDTSC works in user
  mode (3503.9 MHz), `/proc/pax-boot` gives the framebuffer's line.

## 6. A keypress in yew's F mode, end to end

| leg | what happens | measured |
|---|---|---|
| key to read | the USB keyboard's report (its own polling interval, 1-8 ms, as on any system); xHCI's MSI interrupt; `console.key_event` queues all of `ESC [ B` through the line discipline in one handler run; `sched.wake_input`, then `sched.kick`, which switches to the reader at once when the CPU is idle (kernel/interrupts, the USB branch). Nothing on this path waits for a tick. yew's lone-ESC timeout (25 ms, `src/term/input.lu`) is armed only when ESC ends a read, and the console delivers the whole sequence in one read | by reading; the CPU idle (§5) |
| read to write | yew's turn: decode, dispatch, one render, one write. On some keys yew first refreshes its git status, forking `git status --porcelain=v2` and `git ls-files --others --ignored` before it renders | on the installed machine, its own pseudo-terminal at 256 × 90: median 1.28 ms, least 1.13 ms over 16 keys; 2 of 16 at about 40 ms (the git refresh) |
| write to pixels | 161 to 172 bytes, about 126 cells (two rows of 63) | QEMU KVM: 0.055 ms at trunk, 0.021 ms after; the installed machine: its table's `fuss` row |

So a single keypress's budget is about the keyboard's interval plus 1.3 ms plus the drawing of 126 cells, or about
40 ms when yew refreshes git. The full-screen frames are where the drawing's cost lives: F mode's opening (26,856
bytes, about 11,600 cells), a directory expanded in a large tree, any scroll, and every step of cub (about 81 KB,
14,000 cells).

## 7. The prediction, scored

The prediction (`notes/px129/prediction.txt`, `e91d6ce7`) was committed before the instrument and any change.

| # | predicted | found |
|---|---|---|
| P1 | no COM1 on the installed machine; a byte costs CPU work alone | not measurable from ssh (the boot line is root's); the installed machine's `bytes` row will say. px76 recorded none |
| P2 | write-combining; a cell 0.5-3 µs on the metal | awaits the installed machine's table |
| P3 | plain 15-70 ms on the metal; sgr 1.2-2 x plain | metal awaits; under KVM sgr was 2.4 x plain at trunk (the bytes) |
| P4 | a scrolled line about one full screen; scroll10 ten | right: at trunk scroll1 0.79 x plain, scroll10 12 x scroll1 (KVM) |
| P5 | clear about 2 x plain | right: 1.89 x |
| P6 | cursor about 2 x plain | right: 2.00 x |
| P7 | yew's keypress rewrites most of the screen | **wrong**: yew sends only the two rows that change (169-172 bytes); its opening is the full frame. cub's step is a near-full screen, as predicted |
| P8 | QEMU's cost the CPU's alone, plain under 10 ms at 256 × 90; COM1 dominates under KVM | plain 10.6 ms (just over); COM1 right (about 6 µs a byte) |
| F1 | draw only what changes, against a second grid | done |
| F2 | draw at the end of the write | done (`batch_begin`, `batch_end`) |
| F3 | a run of cells a pixel row at a time, no division a pixel | done; the per-cell CPU share 4.7 x less |
| F4 | lift the cap to 320 if the storage grows by under 1 MiB | done: about 238 KiB more (the two grids 64 KiB, the front grid 160 KiB, the dirty rows and a run's scratch 13.5 KiB, the state's 16 words) |
| R1 | a repeated frame at most 1/4 of a changing one | 0.47 under KVM (the parse of the frame's bytes is most of it); the row is 0.7 |
| R2-R4 | scroll10 <= 3 x scroll1, clear and cursor <= 1.3 x plain | held: 1.64, 1.07, 1.10 (KVM) |
| R5 | yew's keypress and cub's frame bounded | cub's and F mode's opening red at trunk, green after; yew's keypress green before and after on the desktop (P7), red at trunk on the laptop (§4) |
| R6 | the existing screen rows pixel-identical | held: mpx3-screen (V2, V5, V9 pixel for pixel, V7 no framebuffer read), mpx5-screen, mpx6-games, mpx6-pointer, mpx3-console in the quick take (§8) |

## 8. Evidence index

| what | where | result |
|---|---|---|
| the prediction | `e91d6ce7` | before the instrument |
| the rows, before the fix | `5c724c46` (the screen reader), `99f65fe7` (rows.py and its selftest), `f63dea6a` (the suite), `bdd13a2d` (the rig), `18761431` (CI's job and paths) | |
| **red at the rows' commit** | record `red-18761431.log`, sha256 `1f4f827764e4fbefb0ea119fa8983b7a0efeaf5bd313f6e3bad7b059f2456a8a` (`notes/px129/rig/red.manifest`) | `FAIL C8 the grid: 256x90 cells (want 320x90)`, `FAIL C2` (plain 5.94 units), `FAIL C3` (sgr 14.55), `FAIL C4` twice (scroll1 4.70 units; scroll10 12.09 x scroll1), `FAIL C5` (clear 1.89 x plain), `FAIL C6` twice (cursor 2.00 x; same 1.01 x), `FAIL C7` twice (fussopen 4.37, cub 6.24 units); C1 and yew's keypress PASS; `END conspeed exit=1 secs=39` |
| the fix | `f237ed4e` (boot/screen.S), `acb14394` (kernel/screen), `29e604a8` (kernel/user), `8ee55dd2` (kernel/console), `83c47fdd` (kernel/panic), `8f81580b` (kernel/serial), `e01bdbfa` (320 columns), `8e4e5a8b` (screen-ref and V1) | |
| green quick take before the rebase | `quick.manifest` (the planner's test; mpx3-conspeed native on both firmwares; mpx3-screen native on both; mpx5-screen, mpx6-games, mpx6-pointer and mpx3-console native BIOS) at `a26a54df`, record sha256 `565ef4f4db1d1bfc999f76dc33904b7fb450ba595a681ceca4216e9e72acec6a` | `END ci-plan exit=0`, `END conspeed exit=0`, `END screen exit=0`, `END vt exit=0`, `END games exit=0`, `END pointer exit=0`, `END console exit=0`; `RECORD-END worst=0 steps=7` |
| the plant before the rebase | `px129-plant-same` (`6e184d02`): `a26a54df` with one hunk in `kernel/screen`'s `draw_span`, every touched cell drawn, changed or not (`plant.manifest`), record sha256 `dd6c8228f3eb494a7186ea98652fdae42f8ce37d2857714ab48dc50d91359fc9` | red by name and alone: `FAIL C6 the same screen written again: same 4.010 ms least, 1.02 x plain 3.950 ms (bound 0.7)`; `END conspeed exit=1` |
| **red on a second host with the fix in, at the raw-figure rows** | the quick take at `a6d2a2ac` on a laptop i7-10870H; its BIOS screen is `selftest/green-kvm-10870h.txt` (`6edfa215`, screen text sha256 `c8f115c3c95800dbee962223b39cef068317fd858c8183a874e88249bb57eacc`) | `FAIL C3 (b) an SGR before every cell: sgr 22.799 ms least, 13.26 units of 1.719 ms (bound 11.5)`, `FAIL C7 (e) cub's step: cub 7.767 ms least, 4.52 units of 1.719 ms (bound 4.3)`; UEFI `FAIL C3` at 12.43 units; `END conspeed exit=1 secs=65` |
| the rows restated against a test's drawing | `731990dc` (rows.py), `6edfa215` (the laptop's px129 table), `b38cbdc9` (its trunk table), `2a7c9027` (the suite's header) | the selftest: both hosts' trunk tables fail (10 and 11 rows), both fix tables pass (12 rows each) |
| **red at trunk on the second host, at the restated rows** | `px129-rows-red-r3` (`d169ba3f`: the rows' commit `fbc47605` with `731990dc` picked onto it), `red.manifest` on the laptop, record sha256 `fa7c961a8a29f24b37192041d614137e79af3c1f91dfd66abdf43d2f3688fc7a` | `FAIL C8 the grid: 256x90 cells (want 320x90)`, `FAIL C2` (plain's drawing 17.14 units, bound 3), `FAIL C3` (sgr's 19.35, bound 5), `FAIL C4` twice (scroll1's 17.35; scroll10 10.02 x scroll1), `FAIL C5` (1.89 x), `FAIL C6` twice (1.94 x; same 1.00 x), `FAIL C7` three times (fussopen's 16.04, cub's 10.49, fuss's 0.08 units); C1 PASS; `END conspeed exit=1 secs=83` |
| **mpx5-pty's session, red as a rate before the fix** | `px129-pty-red` (`f2524f73`: the rig `ce8e4740` and `f2524f73`, before the fix), `pty-rate.manifest`, record sha256 `e6f49c7af0b50dbb863201bdb10ece3c53d44ecf884692c86db660cc2b12b09c` | `FAIL Y3 native bios tcg session: session-root differs in 2 of 20 boots, session-user in 0, 0 not ended; rows: 2 session-root/S|4`; `END ptyrate exit=1 secs=654` |
| the session's fix | `9a992b29` (the driver waits for pelt's prompt before a resize), `08a1a31b` (Linux's side recorded again: the session's transcripts unchanged) | |
| the quick take, the rate and the plant at this branch's head | the same manifests at the head (the quick take now with mpx5-pty, both firmwares, KVM and TCG) | their records and `END` lines are in the PR |
| QEMU's legs, trunk and fix, KVM and TCG, with and without COM1 | the lane's evidence | §4 |

**The rebase.** The work above was done on trunk `211e5c7c`, and every commit this note names before this paragraph
is on the branch `px129-before-rebase` (its head `a26a54df`). The branch was then rebased, unchanged but for the
CHANGELOG's, docs/SOURCES.md's and kernel/README.md's neighbouring entries, onto the queue ahead of it (px122's,
px127's, px123's and px128's, at `0e2843cf`; px123's starts mpx3-screen's and mpx3-console's pelt as
`/bin/pelt +o friendly`, which this branch keeps, and mpx3-conspeed runs no shell). There the same commits are: the
prediction `d3478ba3`; the rows `feda806e`, `80b9a8c4`, `2c23daa7`, `2a1daf62` and `fbc47605` (the red record's
`18761431`); the fix `b4fec940` (boot/screen.S), `cf795abf` (kernel/screen), `c5e02cb9` (kernel/user), `a342a8d3`
(kernel/console), `92f82e74` (kernel/panic), `aef3a3b6` (kernel/serial), `3d818daa` (320 columns), `eee9f144`
(screen-ref and V1).

## 9. Decisions

- **R-px129-1, when the screen draws.** (A) once at the end of each console write, every byte otherwise
  (implemented, recommended): a program's frame is drawn as it leaves it, and the kernel's own lines and the echo
  draw at once as before; (B) every byte, against the front grid only (no hold): keeps the clear's and the cursor's
  double drawing; (C) a timer's refresh (say 60 Hz): a frame could be seen half drawn and a halted kernel's last lines
  would wait for a tick that never comes.
- **R-px129-2, the rows' yardstick.** (A) ratios of two figures of one boot: a test's drawing (its figure less its bytes
  at the same boot's `bytes` rate) against a fixed CPU loop, or one test against another (implemented): a shared host
  moves both; (B) a test's raw figure against the CPU loop (the first version: red with the fix in on a laptop whose
  byte parse costs half as much again against its loop, §4); (C) absolutes (refused by the contract).
- **R-px129-3, TCG.** (A) the rows against the CPU's unit, and `same`, SKIPPED by name under TCG (TCG's multiply chain
  runs at the host's speed while the kernel's memory goes through QEMU's software TLB); the other rows with TCG's own
  bounds (implemented); (B) one set of bounds for both: either loose or red under TCG.
- **R-px129-4, the cap.** (A) 320 columns, which 2560 pixels at scale 1 and 5120 at scale 2 fill (implemented); (B)
  the grid sized at attach from the framebuffer (needs memory before the allocator); (C) leave 256.
- **R-px129-5, yew's keypress row.** yew already sends only what changes, so its keypress is cheap at trunk under QEMU
  on the desktop and cannot be seen red there (on the laptop it is: 0.08 units, §4). (A) keep it as a guard that is green before and after, and say so (implemented);
  (B) drop it. The contract's "red at trunk" holds for (a)-(d), F mode's opening and cub.
- **R-px129-6, the clock's lost ticks.** CLOCK_MONOTONIC loses the ticks that fall inside a console write (35 % kept
  at trunk under KVM). (A) an issue for a later lane: read the clock from its counter (HPET, the TSC) rather than
  counting ticks (recommended; listed for filing); (B) shorten what runs with interrupts off (this lane's fix helps).
- **R-px129-7, yew's git refresh before its frame.** On some keys yew forks two git processes before it renders, about
  40 ms on PAX. (A) an issue on yew: render before refreshing (recommended; listed for filing); (B) nothing.
- **R-px129-8, a byte's cost.** After the fix the bytes are the larger share of colour-heavy frames (about 50 ns a byte
  under KVM: kernel/user's per-byte read, the serial layer, the parser). (A) wait for the installed machine's table:
  if its cells cost far more than its bytes, nothing more is needed; otherwise a block path, a write's bytes copied in
  chunks and fed to the screen in one call (recommended, the next lane's); (B) do it now, unmeasured on the metal.
- **R-px129-9, C3's bound.** Superseded by R-px129-2 (A): `sgr` is mostly bytes, and its raw bound (11.5 units), 1.27 x
  from the fix and from trunk on the desktop, was red with the fix in on the laptop. Its drawing's bound (5 units) sits
  1.30 x from the fix's worst (3.85, the laptop) and 1.33 x from trunk's best (6.65, the desktop).
- **R-px129-10, an orphan on the installed machine.** The first keylat run killed yew by its pid; a child yew had forked
  was reparented to init (pid 1, the console's shell) and remains a zombie there (no memory, one process slot) until the
  next boot. keylat now ends a program by its own keys first. (A) list for an issue: PAX's init should reap orphans
  (recommended); (B) nothing.
- **R-px129-11, KVM in CI.** (A) every CI leg TCG, as the runner gives it to the job; the rows against the unit are
  held by local records only, under KVM (implemented); (B) give the job the runner's `/dev/kvm` (a udev rule): the
  runner's CPU is shared and differs from job to job, and the other suites' legs name TCG for that reason; the drawing
  rows might hold there, unproven.
- **R-px129-12, mpx5-pty's session race (pax#382).** (A) the driver waits for pelt's prompt before each resize, and
  Linux's side is recorded again with that probe (implemented): the row sees the redraw on both systems, every time;
  (B) ruled.txt accepts either form of `S|4`: the race stays, and the row could no longer see a redraw that went
  missing.
- **R-px129-13, a console write and the rest of the machine (§11).** (A) the drawing moves to a kernel thread that
  draws from the shadow grid with interrupts on, a write only parses its bytes into the cell grid, in chunks of at
  most 4 KiB with an interrupt window between chunks, and a console write lock keeps two writers' sequences whole
  (recommended): every span with interrupts off is one chunk's parse, about 0.2 ms, whatever the framebuffer costs,
  and a flood is drawn at the thread's pace, its frames coalesced; (B) the same chunked parse, the flush in slices of
  a few rows with an interrupt window between slices: no thread, but the writer still pays for every frame's
  drawing, and on an uncached framebuffer a slice of eight rows is tens of milliseconds with interrupts off; (C) a
  woken network thread preempting at once: the interrupts-off span itself is untouched. Not built; its row is
  tests/mpx3-conflood's F2, red now.
- **R-px129-14, the framebuffer's mapping on record (§11).** (A) kernel/fb's choice (`wc` or `uc`), IA32_PAT as read
  back, and kernel/screen's scroll way (redraw or copy, how it was decided, the probe's read and write costs) on
  /proc/pax-boot's framebuffer line, so the boot log keeps them, with a row in mpx3-screen holding the line there
  to the console's `screen:` line (recommended); (B) the console line only, as now: on the installed machine nothing
  an ordinary user or root can read after boot says whether the framebuffer is write-combined. Not built.

## 10. Done-when

- [x] a timing program for the console, one command, on the installed machine with its streams
- [x] the same program in QEMU at 2560 × 1440, KVM and TCG, with and without COM1, and at 1280 × 800
- [x] the cost attributed from the numbers and the code (§4, §6)
- [x] the rows red at trunk (`1f4f8277…`) and green after, the screen's existing rows unchanged (the quick take)
- [x] the 256-column cap lifted (C8)
- [x] the rows hold on a second host: its fix table passes, its trunk table fails every row but C1 (`fa7c961a…`)
- [x] one plant, red by name
- [ ] the installed machine's table (a run at its console)

## 11. The installed machine's run: a console flood and the rest of the machine

**What happened.** The timing program (version 3) was run at the installed machine's console on an image of trunk's
console. It drew for about 20 minutes where its wrapper promised a minute or two; ssh sessions froze, ping round
trips reached 2 s, a new ssh connection timed out at the banner, its results file stayed empty, and the wall clock
fell 20 minutes behind and stayed there (pax#384). The person at the console saw each new line start a repaint that
travelled down the screen row by row, slowly enough to watch.

**Why the program ran so long.** Version 3 bounded each test by 8 s of CLOCK_MONOTONIC, the clock that loses the
ticks a console write's interrupts-off span swallows (#370, R-px129-6); under TCG at trunk's drawing the clock kept
29 % of the time the tests took, and on the metal less still, so the bound never came and every test ran its 100
frames. Version 4 bounds the run by the TSC at the idle second's rate: 60 s of tests, 4 s a test, frames fitted to
the first frame's cost, 10 ms asleep between frames, each test's line written to a file as it ends, Ctrl-C leaving
those lines (`1909d4de`); its first line says what the kernel's records say about the framebuffer's caching, and
right after `plain` it infers it from a full screen drawn: about 10 ms means write-combined, 100 ms or more uncached
(`e5fcf3f1`, `d4574d95`). Under TCG at trunk's drawing it ended in 42 s where version 3 would run for many minutes.

**Why the machine starved.** Every system call runs with interrupts off: SYSCALL's FMASK, 0x44700, clears IF
(kernel/user's header), and nothing inside a console write sets it again. A write's bytes go to `serial.put` and
`screen.put` one at a time, and with no UART there is nothing to wait on, so a write is one span with interrupts
off: no tick (its time lost), no network interrupt, no switch. After the write the pending tick switches away only
when the writer's quantum, two delivered ticks, is used; the device's interrupt only queues kernel/netd at the run
queue's tail. A process that writes the console back to back therefore holds the CPU for about two writes a turn,
and every hop of a reply (netd for a ping; netd, the server, netd for an ssh keystroke) waits about that long. At
trunk a scroll redraws every cell whose value changed, top row to bottom, straight to the framebuffer (`scroll`,
the redraw way px87 chose for a GPU): with text on the screen that is the whole screen, about 14.7 MB of stores a
line at 2560 × 1440, and the travelling repaint the person saw. The CPU's share is about 0.5 µs a cell; a pass slow
enough to watch means each 8-byte store costs a bus round trip, which is what an uncached mapping does, and nothing
on the machine records whether kernel/fb mapped it write-combined (R-px129-14). px129's head draws each changed
cell once a write, never reading the framebuffer, so a ten-line write is one pass, not ten; a one-line write that
scrolls is still one full pass, still with interrupts off.

**Measured in QEMU** (tests/mpx3-conflood, `3cd49a6c` and `bf78b054`: user/elf/conflood as init, its UDP echo
child, 6 s idle, a 12 s flood, 6 s idle; tests/mpx3-conflood.d/peer.py the whole network, pinging the machine and
timing a process's echo every 50 ms; KVM, native BIOS, 2560 × 1440 with `fbwrite`, no COM1, on the laptop). Every
request was answered; idle, both took under 0.5 ms. During the flood (p95, ms):

| a write | trunk: writes, ping, echo | px129's head: writes, ping, echo |
|---|---|---|
| ten scrolled lines | 42 (about 288 ms each), 605, 1242 | 3848, 19.5, 39.2 |
| a whole screen of changed text | 184 (65 ms), 120, 258 | 3542, 20.0, 38.3 |
| 256 KiB, an SGR before every character | 3 (about 5 s), 10237, 14294 | 217 (55 ms), 108, 217 |

The echo waits about two or three writes, the ping about one. F2 (ping and echo each at least 95 % answered, p95 at
most 50 ms during the flood) is red at trunk in every mode and at px129's head for large writes: px129 shrinks the
starvation and bounds none of it, and on the metal, where a pass of stores costs more, its small writes would cost
more too. R-px129-13 is the fix's design. F2's record at `d4092dee` (`notes/px129/rig/flood.manifest`, record
sha256 `a43adc490ecea58356f5322b9d7f05ae98404450f75ecfab4b616b50d2bb9cb3`): `FAIL F2 ping during the flood: 119 of 119
answered (100%, at least 95%), p95 104.032 ms` and `FAIL F2 echo during the flood: … p95 212.351 ms` for the large
writes, the other two modes passing; `END flood exit=1 secs=83`.
