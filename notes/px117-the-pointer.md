# px117 — the pointer: an arrow on the console, and the mouse's reports for the program that asks

PAX read USB mice and tablets (px109) but nothing used them. Now the console draws a pointer, an arrow over the
cell it is on, and a terminal program that asks for xterm's button-event tracking in the SGR encoding (DECSET 1002
and 1006, what the org's editor yew asks for) reads its clicks, right clicks, drags, the wheel and the modifiers as
xterm's reports, typed into the console's input in the order the devices sent them with the keys. The modes belong
to the process that set them: they end when it ends, so a crashed program leaves no reports flowing into the shell,
and they are withheld while that process is not in the console's foreground process group. A program on a pty is
its master's to serve. yew, unmodified, opens its document menu on a right click on PAX's console.

Footprint: cross-cutting (`.github/workflows/ci.yml` gains the `mpx6-pointer` job; `tools/ci-tiers.map` and
`tests/ci-plan` the pointer's paths; new `tests/mpx6-pointer`, `tools/pointer-session`, `user/elf/pointerprobe.c`;
`kernel/screen`, `kernel/console`, `kernel/mouse`, `kernel/xhci`, `kernel/interrupts`, `kernel/user`,
`boot/screen.S`, `boot/console.S`, `kernel/kmain_usbcheck.lu`; `tests/mpx5-yew`'s Y9, `tests/mpx6-usbcheck`,
`tests/mpx6-usb.d/build-once.py`).

## 1. Forbidden, and what was read

- **The clean room.** No terminal emulator's, kernel's, firmware's, driver's or C library's source was read: not
  xterm's, not Linux's, not QEMU's. The reports are written from the XTerm Control Sequences document as Ubuntu's
  xterm package ships it (its documentation file only: no binary, no source), the modes' parsing on px19's CSI
  parser (ECMA-48's syntax), the buttons from px109's record (HID's numbering). QEMU's devices and the order their
  events reach the guest were measured as black boxes. yew's public source (the org's own) was read for what it
  enables and parses. `docs/SOURCES.md` (px117) lists every source with its digests.
- **Hosts.** Linux host 1 (Intel Core i7-12700KF, 20 threads, 46 GB) for every build and boot, in an Ubuntu 24.04
  container (QEMU 8.2.2, OVMF, gcc 13.3, clang, lld 18) with KVM: the smoke runs and the first gate on a light slot
  (two CPUs), the records on «a block». The build Mac for git and the judge's selftest only (no build: its disk was
  under its floor). The metal target was never touched.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `3fa24cf5` | the fresh clone's `git rev-parse` |
| wolf | 0.2.35 (`kernel/wolf.pin`), archive sha256 `4cc4045b…dad1a` | `tools/fetch-wolf`, by digest |
| Limine | 12.9.1 | `tools/fetch-limine`, by digest |
| yew | `user/yew.pin`'s `2eb9cb9b` (its own toolchain, wolf 0.2.36) | `tools/mkyew`, by the pin's source digest |
| XTerm Control Sequences | `ctlseqs.txt` sha256 `8855b3e1…a868ba` from `xterm_412-1ubuntu1_amd64.deb` sha256 `b1c91b72…0b11371` | both digests read on the build Mac |
| the recorder | `tools/gauntlet-record.sh` sha256 `03fdbdbc…c845d4` | the same on the build Mac and the Linux host |
| QEMU | 8.2.2 (Ubuntu's `qemu-system-x86`), `qemu-xhci`, `usb-kbd`, `usb-tablet`, `usb-mouse`, the i8042 | `qemu-system-x86_64 --version` in the container |

## 3. Prediction, scored

`notes/px117/prediction.txt`, committed before the first change.

| | predicted | measured | score |
|---|---|---|---|
| P1 | 1280 × 800, 160 × 50 cells on both firmwares | `screen: 1280x800 … 160x50 cells` on BIOS and UEFI | right |
| P2 | the scroll copies the framebuffer under KVM | «» | «» |
| P3 | a relative move over 127 in one event is split, its sum kept | not injected: the rows move 100 an event | not measured |
| P4 | the tablet's 32768 (2c + 1) / 2 cols lands in column c | every row's cell as sent | right |
| P5 | keys and tablet events in send order 20 ms and 2 ms apart | in order 20 ms apart; 2 ms apart a USB key typed before a tablet click reached the guest after it (QEMU polls the USB keyboard, the tablet every 1 ms); through the PS/2 keyboard 3 ms apart, in order | wrong at 2 ms on USB |
| P6 | SGR reports as the document gives them | as predicted, every row | right |
| P7 | nothing else served | the unserved row's eight steps type nothing | right |
| P8 | modes owned by the setter's process, ended with it, withheld while it is in the background | so (owner-exits, owner-background; the books' 2 withheld, 3 ended) | right |
| P9 | reports and keys in the devices' order | so, both steps | right |
| P10 | a pty's program is its master's | the master read the slave's DECSET unchanged; the console typed nothing; the slave read the master's report | right |
| P11 | the arrow over one cell, two cells drawn a move, never copied by a scroll | pointer-drawn, pointer-scroll | right |
| P12 | 1,000 to 5,000 TSC cycles a move under KVM | «» | «» |
| P13 | /dev/mouse0 only once a pointer came; every record to its readers | the mouse session green beside the console's reader | right |
| P14 | no existing transcript or picture changes | «» | «» |
| P15 | kmain_console grows 8 to 16 KiB | «» | «» |
| P16 | every row red at the rows' commit, Y9 too | «» | «» |
| P17 | every row green on both tiers and firmwares under KVM, native BIOS under TCG | «» | «» |
| P18 | Y9: the document menu after the right click, none before | «» | «» |
| P19 | the plant red at the rows that click the right button, only those | «» | «» |
| — | not predicted | kernel/mouse's merge and compaction panicked (a checked wrap) on any motion or wheel of negative sign: px109's `a + b` of two's complement words. The console's reader makes that path live on every machine with a pointer once a reader lags; fixed here, with two rows (R-px117-12) | found |

## 4. Design

- **Where the modes live.** kernel/screen parses the console's output, so it keeps the modes DECSET chose, as the
  document's two sets of mutually exclusive members (the protocol: 9, 1000, 1001, 1002, 1003; the encoding: 1005,
  1006, 1015, 1016). A DECSET selects its member; a DECRST clears its set only when it names the member selected;
  RIS (`ESC c`) clears both; a new screen (an attach) starts with none. A pty's slave writes into its master's
  queue and never reaches the screen, so its program is the master's to serve (px111's shape).
- **Who owns them.** kernel/user's `write` and `sendfile`'s path (`put_kernel`) call `console.after_write`: when the
  screen counted a DECSET of either set during the write, the writing process (its pid) owns the modes. A DECSET
  that reached the screen otherwise (an echo) has no owner, and its modes end at once.
- **When reports are typed.** Only under 1002 with 1006, while the owner lives and its process group is the console's
  foreground group (or no group holds the console). An owner that has ended (its pid gone, or a zombie) ends the
  modes, counted; one that is not in the foreground group has its reports withheld, counted, not queued, and they
  flow again when it is given the foreground.
- **The reader and the order.** The console opens its own kernel/mouse reader when the first pointer attaches
  (kernel/xhci's enumeration thread, where `open` may take a frame; so /dev/mouse0 still appears only once a pointer
  came). It takes the reader's records on every tick and at the start of every key (USB's `key_event`, the
  i8042's and COM1's `irq`): kernel/xhci hands keyboard and pointer reports over in its event ring's order, so a
  report that came before a key is typed before it.
- **One pointer.** Every device moves one pointer, kept in pixels of the grid: a relative count is a pixel (no
  acceleration), an absolute position 0..32767 is scaled to the grid's width and height, and both are held to the
  grid; the cell is the pixel's. Its first position is the grid's centre. A re-attach (another grid) holds the
  pixel to the new grid at the next record, and the screen holds the drawn cell to it.
- **A record's reports**, in order: a motion into another cell with a button held (Cb 32 + the lowest held, the
  document's button-event tracking), each button that changed (left 0, middle 1, right 2; press `M`, release `m`
  with that button), then each wheel detent (64 away from the user, 65 towards; at most eight a record), every one
  with the keyboard's Shift (4), Alt (8) and Ctrl (16). The buttons are every pointer's together (a per-pointer
  table of sixteen), so one pointer's motion is not another's release. A report goes into the line discipline
  whole or not at all: no room for all of it (the ring raw, the line canonical) drops it, counted.
- **The pointer.** An arrow over a cell, 8 × 16 pixels (scaled with the cell): its outline black, its fill white,
  the cell's own pixels elsewhere. kernel/screen's `draw` draws the pointer's cell with the arrow whenever it draws
  that cell, so text written under it keeps it, and a move draws two cells: the old one plainly, the new one with
  the arrow (1 KiB of framebuffer at scale 1). The cell grid is never written, so no cell is corrupted. The scroll
  that copies the framebuffer (px87's `fbread` way, which the probe picks under QEMU) draws the pointer's cell
  plainly first and with the arrow after, so the arrow is never copied up a row. Each move's TSC cycles are counted.
- **No reports asked for.** The pointer is drawn from the first record that moves it or clicks, whether or not a
  program asked; its buttons and the wheel then do nothing. Selection and paste are not done: they need a
  selection buffer, a highlight the grid does not have and a paste path into the line discipline.

```
X.......  XX......  X#X.....  X##X....  X###X...  X####X..  X#####X.  X######X
X###XXXX  X#X#X...  XX.X#X..  X..X#X..  ....X#X.  ....X#X.  .....X..  ........
```

## 5. Evidence index

«»

## 6. Done-when

### 6.1 Rulings

Each implemented as recommended (none is a spend, a public step or irreversible).

- **R-px117-1, what is served: (a), recommended.** Button-event tracking (1002) in the SGR encoding (1006), both
  set, and nothing else: exactly what yew enables, and the one encoding that names the released button and has no
  coordinate limit. (b) also 1000 and 1003 in SGR (a few lines each; no program here asks). (c) also X10's bytes,
  1005, 1015 and 1016. Left out and named: 9, 1000, 1001 (highlight tracking, which needs a cooperating program),
  1003, motion with no button, the X10 bytes, 1005, 1015, 1016, focus events (1004: one screen never loses focus),
  1007 (alternate scroll), buttons 4 and 5 (R-px117-8), DEC locator mode.
- **R-px117-2, DECSET and DECRST: (a), recommended.** The document's two sets of mutually exclusive modes: a DECSET
  selects its member; a DECRST clears the set only when it names the member selected (so `CSI ? 1000 l` under 1002
  changes nothing: the unserved row's step 6); RIS clears both and nothing else of RIS is served yet. (b) any DECRST
  of a member clears its set.
- **R-px117-3, the pointer's shape: (a), recommended.** The arrow over a cell, drawn by `draw`, two cells a move.
  (b) the cell inverted (the text cursor's look: the two would be confused). (c) a sprite at pixel resolution: up to
  four cells a move and their pixels saved, which px87's rule against reading the framebuffer forbids.
- **R-px117-4, with no reports asked for: (a), recommended.** The pointer is drawn from the first motion or click;
  buttons and the wheel do nothing; no selection or paste (not trivial). (b) drawn only while a mode is on. (c) never.
- **R-px117-5, coordinates: (a), recommended.** One pointer for every device, in the grid's pixels; relative a pixel
  a count, no acceleration; absolute scaled to the grid; held to the grid; the cell the pixel's; a new grid holds
  it. (b) a pointer a device. (c) acceleration (a choice to make with a real mouse in hand).
- **R-px117-6, the modes' owner: (a), recommended.** The process whose console write set them; they end when it
  ends; its reports are withheld while it is not in the console's foreground group, and flow again when it has the
  foreground. (b) the modes end when the owner leaves the foreground group: a job its shell gives the terminal
  after the program's first write (a race at every start under job control) would lose them, and a program
  continued after Ctrl-Z would have to set them again. (c) the foreground group at the time, ended when it has no
  member: a program run by a shell without job control shares the shell's group and would leave them on.
- **R-px117-7, the order with keys: (a), recommended.** The console's reader is taken before every key and on every
  tick. (b) on the tick alone: a key up to 10 ms after a click would be typed before it.
- **R-px117-8, buttons 4 and 5: (a), recommended.** Not reported: which of xterm's buttons they are (8 and 9, Cb 128
  and 129) is a choice, and yew reads only their presses, so their releases would reach it as sequences it does not
  know. (b) as xterm's 8 and 9, press and release.
- **R-px117-9, the wheel: (a), recommended.** One report a detent, at most eight a record (a merged record can carry
  many; the rest dropped). (b) every detent.
- **R-px117-10, the modifiers: (a), recommended.** From the console's keyboards' state (PS/2 and USB): Shift 4,
  either Alt 8 (the document's Meta), Ctrl 16.
- **R-px117-11, a report with no room: (a), recommended.** Typed whole or dropped and counted, so a program never
  reads half a report. (b) byte by byte, as keys are.
- **R-px117-12, kernel/mouse's signed merge: (a), recommended.** Fixed here, with two invariant rows red first:
  px109's merge and compaction added two's complement words with wolf's checked `+`, and panicked on any negative
  motion or wheel; the console's reader makes the merge path live on every machine with a pointer once a reader
  lags. (b) left to a lane of its own (the kernel panics meanwhile).
- **R-px117-13, the window's device: (a), recommended.** A report does not change which device the window's size
  follows (px48's `typed_at`): the size changes only with what a person types, and no SIGWINCH is sent for a move.
  (b) a report as the screen's input.
- **R-px117-14, yew's witness: (a), recommended.** Y9 in `tests/mpx5-yew`, its session image as built for Y4-Y8, typed
  at the USB keyboard through QMP and clicked on the tablet by `tools/pointer-session --yew`; `--only pointer` runs it
  alone. (b) a session image of its own in `tests/mpx6-pointer` (a second yew build).

### 6.2 The reports

What the console types under 1002 with 1006, `Cx` and `Cy` the pointer's 1-based column and row:

| event | bytes |
|---|---|
| a button pressed (left, middle, right) | `ESC [ < 0 ; Cx ; Cy M` (1, 2) |
| a button released | `ESC [ < 0 ; Cx ; Cy m` (1, 2): the button released |
| a motion into another cell, a button held | `ESC [ < 32 ; Cx ; Cy M` (33, 34: the lowest held) |
| a wheel detent away from the user, towards | `ESC [ < 64 ; Cx ; Cy M`, `ESC [ < 65 ; Cx ; Cy M` |
| Shift, Alt, Ctrl held | 4, 8, 16 added to the button value |

`console: pointer <m> moves, <c> cycles a move (least <l>), reports <t> typed, <w> withheld, <d> dropped, modes
ended <e>` closes a run once a pointer came.

### 6.3 What yew needs

Nothing. yew enables 1002 and 1006 (with paste, 2004, and focus, 1004, which PAX reads and ignores as before), and
parses every report PAX types. Two notes for yew's side, no change asked: it refuses the X10 release (`Cb` 3), so it
relies on 1006, which it always sets with 1002; and a release of buttons 8 or 9 in SGR (`CSI < 128 ; … m`) is not
in its decoder, which is why PAX does not report buttons 4 and 5 (R-px117-8).

### 6.4 Bounds, and what is not done

Bounds: sixteen pointers' buttons at once (kernel/mouse's own bound); eight wheel detents a record; a report of at
most 22 bytes. Not done: the modes and encodings R-px117-1 leaves out; selection and paste; the pointer on a serial
terminal (it has its own); acceleration; the rest of RIS; a real mouse (QEMU's devices only: the first metal check
moves a mouse over yew's document and right-clicks it).

### 6.5 Checklist

- [x] the prediction, committed first; scored
- [x] the rows first, red by name at the rows' commit: «»
- [x] the pointer drawn and erased cell-exact, never copied by a scroll; press, release, drag, wheel and modifiers at
  known cells from the tablet and the relative mouse; nothing before a mode, after a reset or RIS, or for a mode not
  served; a mode ended with its owner (an exit, a SIGKILL); withheld while the owner is in the background, flowing
  when it has the foreground; reports and keys in order (USB 20 ms, PS/2 3 ms); a pty's program its master's; the
  books
- [x] kernel/mouse's merge and compaction of either sign, two invariant rows red first (a panic), then green
- [x] yew's right click opens its document menu on PAX's console (Y9), the screen kept
- [x] tests/ci-plan with the pointer's map lines; the `mpx6-pointer` job in CI's verdict
- [ ] the final records: green at the head on both tiers and firmwares, the plant `px117-plant-right-as-left` red by
  name: «»
- [x] README, `kernel/README.md`, CHANGELOG, `docs/SOURCES.md`
