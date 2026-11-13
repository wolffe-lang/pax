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
- **The installed machine's own table put the cost elsewhere** (§5, §11): a UART answers at COM1 there, and every
  console byte waited for it with interrupts off, 86.8 µs a byte (a 115200 line, one byte in flight), so a screen of
  text took 2 s to write whatever the drawing cost. kernel/serial now sends through a 64 KiB ring that the UART's
  transmit interrupt drains, and no writer waits on the UART (R-px129-15).

Footprint: cross-cutting (`.github/workflows/ci.yml` gains the `mpx3-conspeed` job; `tools/ci-tiers.map` and
`tests/ci-plan` its paths; `kernel/serial`, `kernel/panic` and `kernel/power` are the kernel's core; new
`tests/mpx3-conspeed`, `tests/mpx3-conspeed.d/`, `tools/mkconspeed`, `user/elf/conspeed.c`, `keylat.c`, `cpugaps.c`;
`kernel/screen`, `kernel/user`, `kernel/console`, `kernel/procfs`, `boot/screen.S`, `boot/io.S`, `tools/screen-ref`,
`tools/qemu-run`, `tests/mpx3-screen`).

## 1. Forbidden, and what was read

- **The clean room.** No kernel's, terminal emulator's, firmware's, driver's or C library's source was read. The
  drawing is written from kernel/screen as it was and from the Intel SDM's account of write-combining memory; the
  programs' behaviour was measured black-box (their output on a pseudo-terminal, strace of the binaries an image
  ships). The UART's transmit side is written from the PC16550D data sheet's facts (IER bit 1, the transmitter
  holding register empty interrupt; LSR bit 5), and the slow UART's far end from pipe(7), fcntl(2) and QEMU's
  documentation of its pipe character device. `docs/SOURCES.md` (px129) lists every source.
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
evidence: `bytes` ≈ `plain` ≈ `clear`). px76 recorded no serial port on the installed machine, so the drawing's rows
boot without one. That record was wrong for this purpose: a UART answers at COM1's address there, and a byte waited on
it far longer than on QEMU's, which takes a byte as fast as it is written (§11).

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

A person at the console runs the wrapper's one command; its table is saved beside it. The table (conspeed 4, on an
image of trunk's console, 256 × 90 cells, the TSC at 3503.7 MHz) is in §11: every figure is its bytes at 86.8 µs, the
UART's, and only a scroll's whole-screen redraw shows above them. What is measured from ssh:

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
| P1 | no COM1 on the installed machine; a byte costs CPU work alone | **wrong**: a UART answers at COM1, and every console byte waited 86.8 µs on it (§11) |
| P2 | write-combining; a cell 0.5-3 µs on the metal | write-combined, faster than predicted: a scroll's whole-screen redraw at trunk is about 5.0 ms, 0.22 µs a cell (§11) |
| P3 | plain 15-70 ms on the metal; sgr 1.2-2 x plain | **wrong**, for the UART: plain 2054 ms (23,661 bytes), sgr 8.8 x plain (its 208,251 bytes); under KVM sgr was 2.4 x plain at trunk (the bytes) |
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
| the slow-UART leg and C9, before the UART's fix | `b090aa43` (tools/qemu-run's `--serial-chardev`), `45898fd7` (uart.py, screen-run.py), `59e0a314` (the leg, C9), `7d8a3221` (`uart.manifest`) | |
| **C9 red before the UART's fix** | `7d8a3221`, `uart.manifest`, record sha256 `2fd7a6f17057db1d6abd5f0e45bb9d63b8a149fb5553f3d9235a5c5b4cc0dee0` | `FAIL C9 (f) a slow UART: bytes 2468.265 ms least for 28800 bytes, 704.01 units of 3.506 ms (bound 3; 85.704 us a byte)`; C1 and C8 PASS; `END conspeed exit=1 secs=69` |
| the UART's fix | `726f2cc4`, `3383d346` (boot/io.S), `94800de4`, `c0595b88`, `77c0a7e6` (kernel/serial), `b0f2c0fd` (kernel/console), `30231573` (kernel/user), `601ce4b8` (kernel/panic), `f7755c4c` (kernel/procfs), `7de7797c` (kernel/power) | |
| C10 | `e806939b` (uart.py's pause), `8aa8b9c8` (rows.py), `39e25a64` (the suite), `f07fb22f` (`uart.manifest`) | |
| **C9 red at trunk's kernel** | `px129-uart-trunk` (`f82e2c4d`: `7d8a3221` with kernel/ and boot/ exactly as trunk `0e2843cf`), `uart.manifest`, record sha256 `7a7bac3059ad88d1661a94a2e48b3a23c592ef239d2bfb045bf1f913f238543c` | `FAIL C9 (f) a slow UART: bytes 1797.172 ms least for 23040 bytes, 540.34 units of 3.326 ms (bound 3; 78.002 us a byte)`, `FAIL C8 the grid: 256x90 cells`; `END conspeed exit=1 secs=78` |
| **C9 and C10 red at trunk's kernel** | `px129-uart-trunk` (`7fd1f794`: `f82e2c4d` with C10's commits picked onto it), `uart.manifest`, record sha256 `c1caf246865e31bb1ef965c13fd3e7df5eeefec69ea07fdd38566559e637292e` | `FAIL C9 … 542.85 units … (78.388 us a byte)`, `FAIL C10 (g) COM1's backlog: the line paused at most 0.809 s once 64 KiB were sent (bound 0.5; at byte 725892 of 728127 in 71.7 s)`, `FAIL C8`; `END conspeed exit=1 secs=79` |
| the slow-UART take, the quick take and C10's plant at this branch's head | `uart.manifest`, `quick.manifest` (mpx3-conspeed's two legs on both firmwares, and every suite there reads COM1), the plant `px129-plant-*` (COM1's interrupt leaves the ring alone) | their records and `END` lines are in the PR |

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
- **R-px129-15, a console write and the UART (§11).** (A) a program's terminal output kept off COM1 on an installed
  system by default, mirrored with a command-line word, the kernel's own lines still on COM1; (B) a transmit ring
  the UART's transmit interrupt drains, the FIFO filled 16 bytes at a time, a full ring dropping and counting, no
  writer ever waiting; (C) both. Implemented: B, and A's word, `pax.serial=log`, which keeps a program's output off
  COM1; mirroring stays the default everywhere, the installer's boot entry included. B alone already means no
  writer waits on the UART. Writing the word into the installer's boot entry is a follow-up with the suites that
  read an installed system over COM1: tests/mpx6-install's `metal.py` (its live login and M7, `login:` on COM1),
  `session.py`, `den.py` and `root-nvme.py` (each boots an installed disk with COM1 on its standard output and reads
  it); each must boot with mirroring kept, and an upgrade must take an install's current boot entry as an earlier
  installer's text (`known_texts`).

## 10. Done-when

- [x] a timing program for the console, one command, on the installed machine with its streams
- [x] the same program in QEMU at 2560 × 1440, KVM and TCG, with and without COM1, and at 1280 × 800
- [x] the cost attributed from the numbers and the code (§4, §6)
- [x] the rows red at trunk (`1f4f8277…`) and green after, the screen's existing rows unchanged (the quick take)
- [x] the 256-column cap lifted (C8)
- [x] the rows hold on a second host: its fix table passes, its trunk table fails every row but C1 (`fa7c961a…`)
- [x] one plant, red by name
- [x] the installed machine's table (a run at its console, §11)
- [x] no console write waits on the UART: C9 red at trunk's kernel (`7a7bac30…`, `c1caf246…`) and before the fix
  (`2fd7a6f1…`), green after (the PR's records)
- [x] COM1's backlog drained by its interrupt: C10 red at trunk's kernel (`c1caf246…`); green at the head and red by
  name at its plant (the PR's records)

## 11. COM1: a console write waited on the UART

**The installed machine's table.** The timing program (version 4) at the installed machine's console, on an image of
trunk's console: 256 × 90 cells, the TSC at 3503.7 MHz, the tests 93.4 s. A frame's mean in ms, beside its bytes at
the `bytes` test's rate (2000.255 ms for 23,040 bytes: 86.82 µs a byte):

| test | frames | bytes | cells | ms | its bytes at 86.82 µs |
|---|---|---|---|---|---|
| unit | 100 | 0 | 0 | 1.750 | |
| bytes | 1 | 23,040 | 0 | 2000.255 | 2000.3 |
| cell | 100 | 9 | 1 | 0.782 | 0.78 |
| plain | 1 | 23,661 | 23,040 | 2054.110 | 2054.2 |
| same | 1 | 23,661 | 23,040 | 2054.036 | 2054.2 |
| sgr | 1 | 208,251 | 23,040 | 18079.073 | 18079.9 |
| scroll1 | 100 | 265 | 256 | 28.032 | 23.0 |
| scroll10 | 14 | 2,587 | 2,560 | 275.458 | 224.6 |
| clear | 1 | 23,668 | 23,040 | 2058.869 | 2054.8 |
| cursor | 1 | 23,673 | 23,040 | 2054.992 | 2055.2 |
| fuss | 100 | 170 | 126 | 14.880 | 14.76 |
| fussopen | 1 | 13,435 (26,863 ran) | 11,648 | 2336.339 | 2332.2 |
| cub | 1 | 81,550 | 13,996 | 7132.486 | 7080.0 |

86.8 µs is ten bits at 115200 baud: a byte's time on a serial line. Every row is its bytes at that rate, give or take
what draws in one span. trunk draws a cell when its byte is written, and the CPU draws one byte's cell while the UART
sends the byte before it, so `plain`'s 23,040 cells hide inside the bytes' time. A scroll redraws the whole screen in
one span after its line feed, so it shows above the bytes: `scroll1` 5.0 ms, `scroll10` 5.1 ms a line, about 0.22 µs
a cell, write-combined (P2), and `clear`'s fill 4 ms. `fussopen` only seems to take twice its bytes' time: a stream's
`bytes` and `cells` are the means over its rotation's frames, and `fussopen` has two (F mode's opening, 26,863 bytes,
and a 7-byte cursor move), so the table says 13,435, while its one frame was the first. Its 2336 ms are those 26,863
bytes at the UART's rate and about 4 ms of drawing, the same clear as `clear`'s. Nothing in the table is
unexplained.

**Why.** kernel/serial's `init` programs COM1 at 0x3f8 (115200 8N1, divisor 1, FIFOs on, no UART interrupt) and calls
it present when the scratch register keeps 0x5a and then 0xa5 and a byte sent in loopback comes back; a port with
nothing behind it reads all ones and fails both. Every console byte, a program's write among them (kernel/user's
`write` hands its bytes to `serial.put` one at a time, interrupts off since SYSCALL), went to the screen, then the
boot log, then the UART: `put` polled LSR until bit 5 was set (the transmit FIFO empty) and wrote the one byte. So one
byte was ever in flight, 86.8 µs each with interrupts off, whatever the screen cost; the poll's bound (2^20 reads)
only kept a dead UART from hanging the kernel. QEMU's UART takes a byte as fast as it is written, which is why no
QEMU table showed it (§4's had no COM1 by choice); and the first account of this machine's run, which assumed no UART
and blamed the drawing, was wrong. On the image the machine ran, nothing turns it off: the console kernel reads no
word about the serial port on its command line and /proc has no switch. Turning the serial port off in the
firmware's setup makes `init`'s checks fail, so `put` never waits; turning it back on undoes that.

**The fix (R-px129-15).** kernel/serial keeps a 64 KiB transmit ring (boot/io.S's `pax_serial_tx`, about 5.7 s of a
115200 line). From kernel/console's start, once COM1's 8259 line is unmasked (`tx_irq_on`), `put` adds a byte to the
ring and never waits:
- when the ring was idle, it moves what the transmit FIFO takes (LSR bit 5: up to 16 bytes) at once and arms the
  THRE interrupt (IER bit 1) while bytes wait;
- while that interrupt is armed, a byte is a store and no port access, and COM1's vector (36, the receiver's already)
  refills the FIFO 16 bytes at a time (`tx_irq`), disarming it when the ring is empty;
- a full ring drops the byte and counts it, and tries the FIFO, so an interrupt that never comes cannot stop COM1 for
  good; `/proc/pax-boot` has a new line, `serial present|absent tty mirrored|log dropped <n>`;
- kernel/panic's halt and kernel/power's reboot and power-off send what the ring holds first, waiting (`drain`), so a
  kernel's last lines still reach the wire before it stops.

Before the console starts, the kernel's early lines wait per byte as before, and kernels that never start the
console (every test kernel but the console's and the session's) are unchanged. `pax.serial=log` on the command line
keeps a program's terminal output (kernel/user's console `write`, kernel/console's output, its echo, and `sendfile`
to the console) off COM1, which then carries the kernel's own lines alone. Nothing writes the word yet: mirroring
stays the default, the installed system's boot entry included (R-px129-15 says what writing it there must touch).

**The suites that read COM1.** No suite's command line changes. Under QEMU the UART's FIFO empties as it is written
unless the far end pushes back, so `put` finds the ring idle and moves each byte at once: COM1's bytes are what they
were, in order, none dropped. A far end that stops reading now loses the bytes past 64 KiB of backlog where the
kernel used to wait up to 2^20 polls a byte. The quick record's suites (the screen, the VT, the games, the pointer,
the typed console sessions, the pseudo-terminals) all read COM1 and are taken at the head.

**The rows.** mpx3-conspeed has a second leg (`--uart slow`; both legs by default) with COM1 on QEMU's pipe character
device (tools/qemu-run's `--serial-chardev`). Its far end, tests/mpx3-conspeed.d/uart.py, shrinks the pipe to one page
and reads it at 11,520 bytes a second, so the emulated UART's FIFO fills and THRE stays clear as a real 115200 line's
would. That leg holds C1 and C8 and two rows of its own, stated under KVM and SKIPPED by name under TCG:
- C9: `bytes`' write is at most 3 units of the CPU loop (about 0.7 with no COM1);
- C10: COM1's backlog drains while its writer sleeps. Once the line has carried 64 KiB, it never pauses more than
  0.5 s: through conspeed's idle second after the tests, the ring still holds bytes, and only the THRE interrupt moves
  them. A kernel that waits per byte has no backlog, so its line pauses when the writer does.

At trunk's kernel C9 is red at 78 µs a byte (the pipe's page and the FIFO give a little slack against the metal's
86.8), and C10 at a 0.81 s pause (records `7a7bac30…` and `c1caf246…`, §8). Before the fix on this branch C9 is red at
85.7 µs a byte (`2fd7a6f1…`). The head's records and the plant, which leaves the ring to the writer's next byte, are
in the PR.

**The timing program, version 5.** Version 4 bounded the run at 60 s by the TSC, but a frame already started is
finished, and on that machine `sgr`'s one frame took 18 s; the tests took 93 s. Version 5 also bounds by bytes:
before the tests, a probe of 512 bytes of `ESC [ m` (the least of three writes) gives a byte's cost, and a test whose
largest write would outrun its budget at that cost is skipped, its line saying so. With the UART's fix in, a byte's
cost is the parse's again, and nothing is skipped.
