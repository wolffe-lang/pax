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
  table: `unit` (a fixed CPU loop, the rows' yardstick), `bytes` (a screen's worth of `ESC [ m`, nothing drawn),
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
| R5 | yew's keypress and cub's frame bounded | cub's and F mode's opening red at trunk, green after; yew's keypress green before and after (P7) |
| R6 | the existing screen rows pixel-identical | held: mpx3-screen (V2, V5, V9 pixel for pixel, V7 no framebuffer read), mpx5-screen, mpx6-games, mpx6-pointer, mpx3-console in the quick take (§8) |

## 8. Evidence index

| what | where | result |
|---|---|---|
| the prediction | `e91d6ce7` | before the instrument |
| the rows, before the fix | `5c724c46` (the screen reader), `99f65fe7` (rows.py and its selftest), `f63dea6a` (the suite), `bdd13a2d` (the rig), `18761431` (CI's job and paths) | |
| **red at the rows' commit** | record `red-18761431.log`, sha256 `1f4f827764e4fbefb0ea119fa8983b7a0efeaf5bd313f6e3bad7b059f2456a8a` (`notes/px129/rig/red.manifest`) | `FAIL C8 the grid: 256x90 cells (want 320x90)`, `FAIL C2` (plain 5.94 units), `FAIL C3` (sgr 14.55), `FAIL C4` twice (scroll1 4.70 units; scroll10 12.09 x scroll1), `FAIL C5` (clear 1.89 x plain), `FAIL C6` twice (cursor 2.00 x; same 1.01 x), `FAIL C7` twice (fussopen 4.37, cub 6.24 units); C1 and yew's keypress PASS; `END conspeed exit=1 secs=39` |
| the fix | `f237ed4e` (boot/screen.S), `acb14394` (kernel/screen), `29e604a8` (kernel/user), `8ee55dd2` (kernel/console), `83c47fdd` (kernel/panic), `8f81580b` (kernel/serial), `e01bdbfa` (320 columns), `8e4e5a8b` (screen-ref and V1) | |
| green quick take at the head | the rig's `quick.manifest` (the planner's test; mpx3-conspeed native on both firmwares; mpx3-screen native on both; mpx5-screen, mpx6-games, mpx6-pointer and mpx3-console native BIOS) at the PR's head | its record's sha256 and every `END` line are in the lane's hand-back and the PR |
| the plant | the PR's head with one hunk in `kernel/screen`'s `draw_span`: every touched cell drawn, changed or not (`plant.manifest`) | red by name: `FAIL C6 the same screen written again`; its record in the hand-back |
| QEMU's legs, trunk and fix, KVM and TCG, with and without COM1 | the lane's evidence | §4 |

## 9. Decisions

- **R-px129-1, when the screen draws.** (A) once at the end of each console write, every byte otherwise
  (implemented, recommended): a program's frame is drawn as it leaves it, and the kernel's own lines and the echo
  draw at once as before; (B) every byte, against the front grid only (no hold): keeps the clear's and the cursor's
  double drawing; (C) a timer's refresh (say 60 Hz): a frame could be seen half drawn and a halted kernel's last lines
  would wait for a tick that never comes.
- **R-px129-2, the rows' yardstick.** (A) ratios of two figures of one boot, against a fixed CPU loop or against
  another test (implemented): a shared host moves both; (B) absolutes (refused by the contract).
- **R-px129-3, TCG.** (A) the rows against the CPU's unit, and `same`, SKIPPED by name under TCG (TCG's multiply chain
  runs at the host's speed while the kernel's memory goes through QEMU's software TLB); the other rows with TCG's own
  bounds (implemented); (B) one set of bounds for both: either loose or red under TCG.
- **R-px129-4, the cap.** (A) 320 columns, which 2560 pixels at scale 1 and 5120 at scale 2 fill (implemented); (B)
  the grid sized at attach from the framebuffer (needs memory before the allocator); (C) leave 256.
- **R-px129-5, yew's keypress row.** yew already sends only what changes, so its keypress is cheap at trunk under QEMU
  and cannot be seen red there. (A) keep it as a guard that is green before and after, and say so (implemented);
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
- **R-px129-9, C3's bound.** `sgr` is mostly bytes, so its bound (11.5 units) sits 1.27 x from the fix's 8.97 and 1.27
  x from trunk's 14.55, inside the 1.4 x the other rows keep. (A) keep it and revisit with R-px129-8 (implemented);
  (B) a looser bound that trunk might pass.
- **R-px129-10, an orphan on the installed machine.** The first keylat run killed yew by its pid; a child yew had forked
  was reparented to init (pid 1, the console's shell) and remains a zombie there (no memory, one process slot) until the
  next boot. keylat now ends a program by its own keys first. (A) list for an issue: PAX's init should reap orphans
  (recommended); (B) nothing.

## 10. Done-when

- [x] a timing program for the console, one command, on the installed machine with its streams
- [x] the same program in QEMU at 2560 × 1440, KVM and TCG, with and without COM1, and at 1280 × 800
- [x] the cost attributed from the numbers and the code (§4, §6)
- [x] the rows red at trunk (`1f4f8277…`) and green after, the screen's existing rows unchanged (the quick take)
- [x] the 256-column cap lifted (C8)
- [x] one plant, red by name
- [ ] the installed machine's table (a run at its console)
