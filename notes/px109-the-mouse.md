# px109 — the mouse: USB HID pointers on xHCI, a bounded queue a reader, and /dev/mouse0

PAX had no mouse. Now a USB mouse or tablet works beside the USB keyboard, on the same xHCI stack: QEMU's boot-protocol
`usb-mouse` and its report-descriptor `usb-tablet`, several at once, a pointer interface on the same device as a
keyboard, plugged and unplugged while the system runs. Each device report goes into `kernel/mouse`, which keeps one
bounded queue a reader: it merges motion when a queue fills and never drops a button transition while there is motion
to merge. `/dev/mouse0` reads a queue as fixed 32-byte records, so a person can watch the stream from userspace. The
console's own use of the queue (the pointer, xterm's mouse modes and SGR reports into the terminal) is the next
lane's; its consumer API is in §5.3.

Footprint: cross-cutting (`tools/ci-tiers.map` and `tests/ci-plan` gain the mouse's paths; new `kernel/usb_mouse`
and `kernel/mouse`; `kernel/xhci`, `kernel/files`, `kernel/kmain_console.lu`, `kernel/kmain_usbcheck.lu`;
`tests/mpx6-usb` and its fixture, `tests/mpx6-usbcheck`; `tools/mouse-session`, `user/elf/mouseprobe.c`).

## 1. Forbidden, and what was read

- **The clean room.** No kernel's, firmware's, USB stack's or device model's implementation source was read: not
  Linux's, not any BSD's, not QEMU's. The driver and the report reader are written from USB HID 1.11, the HID Usage
  Tables 1.7 and xHCI 1.2. QEMU's devices were measured as black boxes, over PAX's own stack (§2, §3). The one Linux
  text read is `Documentation/admin-guide/devices.txt`, for a free device number. `docs/SOURCES.md` (px109) lists
  every source with its digest.
- **Hosts.** Linux host 1 (Intel Core i7-12700KF, 20 threads, 46 GB) for every build and boot, behind its lock names
  (a build or a gauntlet holds a block's six CPUs; the invariant kernel's checks ran light, on two), in an Ubuntu
  24.04 container (QEMU 8.2.2, OVMF, gcc 13.3, clang, lld 18) with KVM. The build Mac for git, the probe's syntax and
  the planner's own test. The metal target was never touched.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `db516c69` | the fresh clone's `git rev-parse` |
| wolf | 0.2.35 (`kernel/wolf.pin`), archive sha256 `4cc4045b…dad1a` | `tools/fetch-wolf`, by digest |
| Limine | 12.9.1, sha256 `5cdebc51…dcff4` | `tools/fetch-limine`, by digest |
| HID 1.11, HUT 1.7, xHCI 1.2, QEMU's three documentation pages, devices.txt | the digests in `docs/SOURCES.md` | each fetched twice, sha256 read twice, equal |
| QEMU | 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.18), `qemu-xhci`; `nec-usb-xhci` on the firmware suite's MSI and INTx legs | `qemu-system-x86_64 --version` in the container |

## 3. Prediction, scored

`notes/px109/prediction.txt`, committed before the first change. The measurement is `notes/px109/measured/`: each
device's descriptors and every report, logged by the driver with `usbraw`, the report protocol and the boot protocol
(`hidboot`) in one session each, every row injected.

| | predicted | measured | score |
|---|---|---|---|
| P1 | usb-mouse at full speed, bMaxPacketSize0 8, vendor 0627 | high speed (xHCI speed 3) on QEMU's USB 2 ports, which follow its USB 3 ones (root ports 5 to 8); bMaxPacketSize0 64; 0627:0001; bcdUSB 0200 | wrong: the speed and EP0's packet |
| P2 | one interface 3/1/2, bcdHID 0101 or 0111, a report descriptor of 40 to 80 bytes, endpoint 81h, 4 to 8 bytes, bInterval 10 or less | 3/1/2; bcdHID **0001**; 52 bytes; 81h, 4 bytes, bInterval 7 (a high-speed exponent: 8 ms) | right but bcdHID |
| P3 | appendix B.2 with a wheel: three buttons, 8-bit relative X, Y, wheel, no Report ID, 4 bytes | the same but **five buttons** (5 bits, then 3 of padding) | wrong by two buttons |
| P4 | usb-tablet at full speed, 3/0/0 | 3/0/0, high speed, a 74-byte descriptor, endpoint 8 bytes, bInterval 4 (1 ms) | right but the speed |
| P5 | three buttons, 16-bit absolute X and Y over 0..32767, a relative 8-bit wheel, 6 bytes | the same | right |
| P6 | reports: x+10 `00 0a 00 00`, y+5 `00 00 05 00`, buttons 01/02/04, wheel-up +1, wheel-down -1, abs `00 20 4e 90 01 00`; side and extra reach neither | as predicted for every row the session injects (`00 f9 fe 00` for x-7 y-2; the tablet `00 00 40 00 20 00` at 16384, 8192); side and extra not injected | right; side and extra not measured |
| P7 | a move over 127 is split over reports | not injected | not measured |
| P8 | under the boot protocol usb-mouse keeps its 4-byte report | byte-identical reports under both protocols, the wheel byte included | right |
| P9 | rel to the usb-mouse, abs to the tablet, btn to the mouse `info mice` marks current; `mouse_set` moves it; with two mice rel reaches only the current one | the same (`notes/px109/measured/info-mice.txt`; the two-mice row: x+3 reached one mouse, x+4 the other after `mouse_set`) | right |
| P10 | reports only on change | none while still (each click two reports) | right |
| P11 | on trunk both devices configured silently, no `/dev/mouse0` | the same: `open` -ENOENT | right |
| P12 | the reader parses QEMU's two descriptors and five real-mouse shapes, refusing Push, Pop, long items, Delimiter, no X or Y, over 32 bits, over 64 bytes | so, plus three refusals named on the way (X and Y split or of different kinds, nesting, an empty extent): 25 rows of `kmain_usbcheck` (the queue has 14) | right |
| P13 | one queue a reader, 126 records of 32 bytes, at most 8 readers; merge above half, compact when full, an edge never merged | so; the first body put the records 512 bytes into the frame, not 64, and slots 112 on spilled into the next frame: the burst row found it (§4) | right in design; the body had a bug |
| P14 | a boot mouse by the boot protocol (SET_PROTOCOL 0, SET_IDLE 0), the tablet by its descriptor, a pointer beside a keyboard, hot-plug, two at once | a boot mouse whose descriptor parses is set to the **report** protocol (R-px109-2); no SET_IDLE (mice default to an infinite idle, HID 1.11 §7.2.4); the rest as predicted | wrong on the protocol, by ruling |
| P15 | `/dev/mouse0` present with an xHCI controller, whole records, waits, POLLIN, root's 0600 | present from the first pointer's arrival (R-px109-3); the rest as predicted | wrong on when |
| P16 | kmain_console grows 12 to 24 KiB a tier | native 3,537,512 to 3,607,640 bytes, +70,128 (`.text` +48,064); release 2,640,248 to 2,847,808, +207,560 (`.text` +209,248, `.rodata` -5,408). The release growth is spread over functions this lane never touched (`net.report` +10.9 KB, `sound.summary` +9.0 KB, `user.serve` +5.8 KB, …): the release tier's inliner chose differently across the package; the new functions themselves are about 15 KB (`xhci.pointer` 5.8, `xhci.raw_flush` 3.5, `usb_mouse.parse` 3.0, `xhci.configure` +5.3). The same choice makes the release console's cold build 252 s against trunk's 169 (R-px109-8) | wrong: 3 and 8 times the bound |
| P17 | the 17 invariant rows stay, about 30 join | 17 stay; 39 join (56 PASS lines) | right |
| P18 | the keyboard rows do not move | every keyboard topology's 18 rows equal the Linux reference on both tiers and firmwares, repeat 250.004 ms then 30 ms as before; the firmware suite's keyboard sessions on MSI and INTx green | right |
| P19 | on trunk plus the rows every mouse row red by name, the keyboard rows green | the rows tip `f98b5574`: the session's 16 mouse rows red by name (`FAIL mouse-open open=-2` first), keyboard-path green; the invariants red at their first (`FAIL USB mouse boot report buttons and signed motion`) | right |
| P20 | moves, buttons, drag and wheel green on both devices; the burst (3 s unread, about 400 motions, 10 clicks) keeps 20 edges with the sum exact and a MERGED record; unplug GONE with buttons 0; replug a new number; keys byte-exact | all green; the burst grew so the queue must fill and compact (4.5 s unread, 500 motions, 25 clicks: 126 records carrying about 400 reports, 50 edges in order, the sum exact, 22 compactions on the books, none lost) | right; the burst row made stronger |
| P21 | TCG 2 to 4 times KVM, no longer deadline | a session 21.6 s under TCG against 20.0 s under KVM (native, BIOS): the probe's and the host's waits are most of it; no deadline moved | wrong: about 1.1 times |

## 4. Evidence index

Every take ran on Linux host 1 in the container. Records are `gauntlet-record.sh`'s; their END lines are in the PR.

| record | what | at |
|---|---|---|
| m1-m6 | the measurement: descriptors and reports under both protocols, `info mice`; m5 found the burst row red (21 edges, one release twice, the sum 382): record 112 read twice, 113 lost | the scratch heads of the driver |
| the frame row | `mouse queue stays inside its frame` red before the fix (the kernel hung, exit 124: the spill corrupts whatever owns the next frame), green after | `28e2caa1`, `e642e1c5` |
| rows red | the session's 16 mouse rows red by name, the keyboard path green | the rows tip `f98b5574` |
| check red | the invariants red at their first mouse row | the rows tip `f98b5574` |
| working gauntlet | the judge's selftest, the fixture, `tests/ci-plan`, `tests/mpx6-usb` (three keyboard topologies and the mouse session) on both tiers and firmwares under KVM, the mouse session under TCG on the four, `tests/mpx6-firmware` native on both firmwares (F7 runs the mouse session on MSI and INTx): 12 steps, every one exit 0, 29 minutes | `1f68bbcd` |
| release time | the release console's cold build, trunk and the head interleaved twice on a held block (169 s and 252 s), and the IR census at trunk, three of this lane's commits and the head: kernel/log's formatters inlined across the cluster cut (`notes/px109/measured/release-time.txt`, R-px109-8) | trunk, `f6c33ac8`, `74f980bd`, `6a1c843f`, `1f68bbcd`/`638ee7ae` |
| the final records | red at the rows tip (the session's rows and the invariants, two records), green at the head (the gauntlet above, recorded), the plant `px109-plant-burst` red by name at `burst-edges` (compaction folding an edge into the motion after it): their END lines are in the PR | `f98b5574`; the head; the head and one commit |

## 5. Done-when

### 5.1 Rulings

- **R-px109-1, the debug record: (a), ruled.** `/dev/mouse0` gives PAX's own 32-byte record (§5.2), char 60:0
  (`devices.txt`'s local range for character devices; 13:32 is Linux's `/dev/input/mouse0`, whose PS/2 protocol this
  is not), root's 0600. (b) evdev's `struct input_event` at `/dev/input/eventN` with its ioctls, (c) PS/2 packets at
  `/dev/input/mice`: a Linux program that needs either is a later lane's.
- **R-px109-2, the protocol: (a), ruled.** A boot mouse whose report descriptor parses is set to the report
  protocol and read by its descriptor, so a real mouse's wheel and buttons 4 and 5 arrive; HID 1.11 appendix B says a
  class driver changes a boot interface to the report protocol after reading its report descriptor. The boot
  protocol's three bytes are the fallback when the descriptor is refused, and every boot mouse's under `hidboot`.
  (b) the boot protocol wherever offered (the contract's first word): a boot report has three buttons and no wheel.
  (c) the boot protocol, with the bytes after the third read by the descriptor: device-specific by appendix B.
  QEMU's usb-mouse sends the same bytes under both protocols (P8), so QEMU cannot tell (a) from (c): a real mouse is
  the first witness (§5.4).
- **R-px109-3, when /dev/mouse0 exists: (a), ruled.** From the first pointer's arrival (or the first reader's
  open) to the end of the boot, so no machine without a pointer lists anything new in `/dev`. (b) whenever an xHCI
  controller is, (c) always.
- **R-px109-4, the queue: (a), ruled.** One bounded queue a reader (each open of `/dev/mouse0`, and the console's),
  every record to every reader, so a watcher never takes the console's events; 126 records a frame, 8 readers, 16
  pointers at once. (b) one queue with readers' cursors: the slowest reader would set the bound for all.
- **R-px109-5, the time: (a), ruled.** CLOCK_MONOTONIC's nanoseconds at the report (the tick's 10 ms today), so a
  program compares a record with its own clock. (b) kernel/clock's finer count: a different base from every program's.
- **R-px109-6, no edge dropped: (a), ruled.** Under half full every report is a record; above it motion merges into
  the tail; a full queue compacts its oldest two adjacent motion records; a button edge never merges, and is lost
  only when nothing can be compacted (every other record an edge): counted (`lost`, the books' `edges lost`) and
  the next record says LOST. (b) block the producer: the interrupt cannot wait. (c) drop the oldest: an edge.
- **R-px109-7, absolute positions: (a), ruled.** Scaled to 0..32767 across the device's logical extents (QEMU's
  tablet is already 0..32767), so the console maps one range to its grid. (b) the device's own units and extents in
  every record.
- **R-px109-8, the release tier's build time: (a), ruled.** The release console's cold build is 252 s at
  the head against 169 s at trunk (wolf 0.2.35, both twice, on a held block). The time is the mid-end's loop
  versioning, which costs a function its loops times its branches squared (wolf-lang#983), and the loops are
  kernel/log's: at the head `log.dec` (two loops) is inlined at all of its call sites and `log.put` (one loop) at
  about 1,500 more than at trunk, mostly in functions this lane did not change (`sound.summary` 0 loops to 81). Which
  sites inline them follows wolf's cluster cut of the whole package, which every change moves: three of this lane's
  commits in a row gave 1.9, 2.0 and 1.3 times trunk's cost, the head 2.3 (`notes/px109/measured/release-time.txt`).
  (a) take the time with the mouse; the fix is wolf's (#983, or the cut's import of looping callees). (b) reshape
  the mouse's code until the cut falls as trunk's did: it falls anew at the next lane's change. (c) a kernel/log
  whose formatters inline without loops: a change to every kernel's code, and wolf has no attribute that only keeps
  a function out of line (`#[consttime]` does, with a contract), so it is another lane's if wanted. It is build time
  alone: the release rows run as before.

### 5.2 The record

`/dev/mouse0`'s `read` gives whole records of 32 bytes, little-endian, oldest first (a buffer shorter than 32 is
-EINVAL; with none waiting `read` waits, or answers -EAGAIN under O_NONBLOCK; `poll` and epoll say POLLIN while one
waits). The same 32 bytes are what `kernel/mouse`'s `pull` copies for the console.

| offset | type | field | meaning |
|---|---|---|---|
| 0 | u64 | time | CLOCK_MONOTONIC's nanoseconds when the report came (10 ms resolution today) |
| 8 | u32 | seq | this reader's record number, from 1 (a compaction leaves a gap: two records became one) |
| 12 | u16 | device | the pointer's number: 1, 2, … in the order pointers arrive, never reused in a boot |
| 14 | u8 | kind | 1 relative (a mouse), 2 absolute (a tablet) |
| 15 | u8 | flags | 1 EDGE (the buttons differ from this pointer's previous record), 2 MERGED (more than one report), 4 GONE (the pointer left; its buttons read 0), 8 LOST (records were lost before this one), 16 NEW (the pointer arrived; no motion) |
| 16 | i32 | x | relative: dx, right positive; absolute: x, 0..32767 |
| 20 | i32 | y | relative: dy, down positive; absolute: y, 0..32767 |
| 24 | u16 | buttons | bit n-1 is button n: 1 primary (left), 2 secondary (right), 3 tertiary (middle), 4, 5 |
| 26 | i16 | wheel | detents, positive away from the user |
| 28 | u32 | reports | the device reports the record carries: 1, more when MERGED, 0 for NEW and GONE |

A MERGED record's motion is the sum of its reports' (relative) or the last report's position (absolute), and its
time the last report's. An EDGE record's motion came in the same report as the buttons' change.

### 5.3 The consumer API (for the console, px110)

`kernel/mouse` is a leaf (it uses only `kernel/frames`, `kernel/sync` and `kernel/log`); every call saves and
restores IF itself. `open` and `close` take and give back a frame: call them from a system call or a kernel thread.
`pull`, `pending`, `changes` and `lost` allocate nothing and may be called anywhere, the timer's tick included.

- `open() -> u64`: a reader, 1 to 8, its queue empty at first; 0 when all are taken. The console opens one when it
  starts and keeps it.
- `pull(r, out) -> bool`: the oldest record copied to the kernel address `out` (32 bytes) and taken; false when none
  waits. The offsets are the module's `R_*` constants, the kinds `REL` and `ABS`, the flags `EDGE`, `MERGED`, `GONE`,
  `LOST`, `NEW`.
- `pending(r) -> u64`: how many wait.
- `changes(r) -> u64`: a count that moves with every record made or merged into, for a cheap "anything new?" (what
  edge-triggered epoll compares).
- `lost(r) -> (u64, u64)`: edges and motion reports this reader lost.
- `close(r)`: the queue given back.

A producer's side, for another bus later: `attach(kind, now) -> number`, `report(number, x, y, buttons, wheel, now)
-> bool` (whether a reader got a record; kernel/xhci then wakes waiting readers with `sched.wake_pipes`), `detach(
number, now)`. Nothing wakes the console: it pulls on its own schedule (a tick, or when `changes` moved).

### 5.4 The first metal check

The target machine's USB mouse is the first real witness of R-px109-2 and of a descriptor QEMU does not have. Boot
with `usbraw` added to the kernel's command line (the Limine entry's `cmdline:`), log in as root, and read
`/dev/mouse0` with `head -c 320 /dev/mouse0 | od -A d -t x1` (ten records, sixteen bytes a line, two lines a
record; run it again for the next ten). Neither `head` nor `od` was run on `/dev/mouse0` here (the probe was): a
reader that asks for less than 32 bytes is told -EINVAL, and one that waits to fill a large buffer prints nothing
until it is full. Then:

1. The boot log has one line for the mouse: `xhci: mouse usb1-<port> speed <s> interface <i> report protocol,
   relative, <n>-byte reports[, report ID <k>], buttons <b>, wheel; pointer 1`. A `refused: <why>` names what the
   reader could not read; a `report descriptor refused (<why>): boot protocol` line means the fallback is in use, and
   then the wheel and buttons 4 and 5 will not arrive. With `usbraw`, the descriptor's bytes are on the log too: they
   are what a fix needs.
2. Move the mouse: records of kind 1 (byte 14) with dx and dy at bytes 16 and 20, right and down positive.
3. Click each button: a record with flag 1 (EDGE, byte 15) and the button's bit at byte 24 (01 left, 02 right, 04
   middle), then one with the bit clear.
4. **The wheel**: a record with byte 26 at 01 rolled away from you, ff toward you. **Buttons 4 and 5** (the side
   buttons, where the mouse has them): bits 08 and 10 at byte 24. Either missing means the descriptor's wheel or
   buttons were not found: send the `usbraw` lines.
5. Unplug the mouse holding a button: a GONE record (flag 04, buttons 00); plug it back: a NEW record (flag 10) under
   the next pointer number.
6. A wireless receiver that is a keyboard and a mouse in one device: both work, the keyboard's line first.

### 5.5 Bounds, and what is not done

Bounds: one pointer interface a device (the first boot mouse's, else the first class-3 interface of subclass 0); a
report descriptor of at most 1024 bytes, a report of at most 64; X, Y, the wheel and buttons 1 to 5 in the first
top-level Mouse or Pointer collection; 16 pointers and 8 readers at once; 126 records a reader. Not done: horizontal
scrolling (AC Pan, read past), the Resolution Multiplier (a high-resolution wheel counts one per detent at its
default), digitizers and touch, a pointer on the PS/2 port, SuperSpeed devices (logged, not driven, as before); the
console draws no pointer and reads no queue yet (px110). The release console builds about 80 s slower cold
(R-px109-8). A STALLed request to a pointer resets the default pipe; no QEMU device stalls, so that path is not
exercised.

### 5.6 Checklist

- [x] the prediction, committed first; the measurement, scored
- [x] 39 invariants: the reader on appendix B.2's descriptor and five real shapes, its refusals; the queue's records,
  merges, compaction, a lost edge said LOST, a full queue inside its frame
- [x] the session's 17 rows: moves, each button, a drag and the wheel on the mouse and the tablet; the burst that
  fills the queue with no edge lost; two mice and a tablet; unplug with a button held; replug; typing during motion;
  the keyboard path clean
- [x] the rows red at the rows tip, by name
- [x] the working gauntlet: every keyboard topology and the mouse session on both tiers and firmwares under KVM, the
  mouse session under TCG, the firmware suite on MSI and INTx
- [x] tests/ci-plan with the mouse's map lines
- [x] the release console's build time measured against trunk's, and where it goes (R-px109-8)
- [ ] the final records: red at the rows tip, green at the head, the plant red by name at `burst-edges`
- [x] README read and refreshed (the console row, the hardware list, the switches, the USB suites' row); `kernel/README.md`
  and the CHANGELOG

### 5.7 The rebase

The branch was rebased from trunk `db516c69` onto `2dd649f0`, the head of pax#340, which reaches trunk first by
fast-forward. The 27 commits before it are kept on `px109-before-rebase` (head `d7199a4e`); the shas this note
cites above §5.7 are theirs. Three files conflicted, all prose, and each kept both sides:
- `docs/SOURCES.md`: px109's section follows the sections trunk added since (px107, px108, tb03, px114, px115, px112);
- `README.md`: the USB suites' row takes the mouse's rows, the firmware row keeps trunk's new clock rows;
- `CHANGELOG.md`: the mouse's paragraph heads the Unreleased list, above trunk's newer ones.

`git range-diff` shows every other commit's patch unchanged but for its context lines: `kernel/kmain_console.lu`,
`tests/ci-plan` and `tools/ci-tiers.map` merged by themselves, beside trunk's new lines. No kernel module this lane changes moved on
trunk (`kernel/xhci`, `kernel/files`, `kernel/usb_keys` and the USB suites are as at `db516c69`), and `/dev/mouse0`'s
60:0 and the descriptor kinds 17 and 18 are still free.

pax#340's head then moved to `1c0148eb` (kernel/user's STAR: the SYSRET base 0x13, so SS is 0x1b in ring 3 on
processors that do not force the privilege bits; a row each in `tests/mpx3-user` and `tests/mpx5-burrowd`), and the
branch was rebased onto it. The 29 commits before that are kept on `px109-before-rebase2` (head `a1c85b41`).
Nothing conflicted, and `git range-diff` shows all 29 patches unchanged. Nothing in the mouse work assumes STAR's
value or reads a ring-3 selector: `/dev/mouse0`'s `read` reaches the user's buffer through `kernel/uaccess`'s walk
of the page tables (`writable`, `put`), the queue and the driver run in the kernel alone, and the probe has no
assembly. The cited commits after each rebase:

| before | after the first | after the second | what |
|---|---|---|---|
| `d11b997b` | `21b9b851` | `6a9aa510` | the prediction |
| `f98b5574` | `d8a0cfd1` | `233a49ed` | the rows tip: the 38 invariants |
| `f6c33ac8` | `dd0621e1` | `c6e937ab` | kernel/xhci's pointers |
| `74f980bd` | `88137dd3` | `000a75f5` | /dev/mouse0 |
| `6a1c843f` | `93995e16` | `02204c4a` | the books line |
| `28e2caa1` | `a8f4d396` | `0ab83944` | the frame invariant, red first |
| `e642e1c5` | `7edaf8c1` | `89d1b68f` | the fix |
| `1f68bbcd` | `4c790d20` | `fe303ad0` | CHANGELOG.md |
| `638ee7ae` | `5872f7d2` | `731cff9f` | the note |
| `d7199a4e` | `a585dba9` | `6a77e6ba` | the note's release-time section |

The release console's build time (§5.1) was measured before the rebases and not again: the cluster cut it
follows moves with every change, trunk's included. The final records, green at the head after the second rebase
and the plant red by name at `burst-edges` on one commit over it, are in the PR with their END lines.
