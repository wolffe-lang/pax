# px118 — a boot that goes black leaves evidence

Branch `px118` from trunk `d1270bb0`. Footprint: cross-cutting (the kernel's entry, `boot/`, the installer's
configuration). Instrumentation first: this note claims no cause it has not seen.

**The report this answers.** On the test machine (an X58-class desktop with an I225-V, UEFI, no serial port),
choosing the installed disk's entry from the firmware's one-time boot menu sometimes gives a black screen from that
moment: no Limine menu, no text. It happened four boots in a row on one image, then a boot worked with nothing done
differently; the live stick does the same now and then, on every image made so far. PAX keeps no boot log, so nothing
says whether the firmware never reached Limine, Limine never reached the kernel, or the kernel ran with a dark screen.
(A general-protection panic after the console has drawn, seen on a hosted CI run, is a different fault and another
lane's.)

## 1. Forbidden, and what was read

No other kernel's, boot loader's or firmware's source. Read: PAX's own tree (`docs/BOOT.md`, `docs/INSTALL-METAL.md`,
`boot/`, `kernel/kmain_console.lu` and the modules it calls, `user/install/`, `user/login/`, the notes of earlier
lanes); Limine's own documentation at the pinned release, `CONFIG.md`, `USAGE.md` and `FAQ.md` at tag `v12.9.1`
(the options below are quoted from `CONFIG.md`); the UEFI 2.10 and ACPI 6.5 specifications; the Intel SDM; the
8254 and MC146818 data sheets and the PC/AT port map as earlier lanes cite them (`kernel/speaker`, `kernel/rtc`).
QEMU, SeaBIOS and OVMF are run as black boxes.

## 2. How PAX boots on the test machine today (item 1)

The installed disk, UEFI, step by step, with what the screen shows at each step on a boot that works.

1. **The firmware.** Power on, the firmware's splash, F8 for its one-time boot menu, and the disk's entry chosen
   (the firmware names it after the disk; it makes the entry itself for the removable-media path
   `\EFI\BOOT\BOOTX64.EFI` on the disk's EFI partition; PAX writes no firmware boot entry and no EFI variable).
   The firmware loads Limine's UEFI program from that path and starts it.
2. **Limine.** It finds its configuration on the boot volume (`CONFIG.md`, "Location of the config file": on EFI the
   volume holding the booted program is scanned first; PAX's file is `/boot/limine/limine.conf` on the EFI
   partition). The installer writes it (`user/install/prepare.lu`, `config_text`):

   ```text
   timeout: 0
   quiet: yes

   /PAX ext2 developer preview
       protocol: limine
       path: boot():/boot/pax
       cmdline: quiet root=PARTUUID=<the root partition> rootfstype=ext2 rw
   ```

   `timeout: 0` boots the entry "instantly, without showing the menu"; `quiet: yes` suppresses "all screen output
   except panics and important warnings" (`CONFIG.md`, global options). **So on a boot that works, Limine draws
   nothing at all**: from the menu choice until the kernel's first line, the screen is whatever the firmware left
   (its splash, or black). Limine reads `/boot/pax` from the EFI partition, sets up the framebuffer the kernel asks
   for (`boot/start.S`'s framebuffer request; with no `resolution:` in the entry, Limine picks the mode), the memory
   map, its page tables and the higher-half direct map, leaves the firmware's boot services, and jumps to the kernel.
   A missing kernel file or a refused hash is a Limine `PANIC` that waits for a key, `quiet` or not (px115's probe
   P1b).

   The live stick's `boot/limine-usb.conf` differs: `timeout: 3` and no `quiet`, so **the stick shows Limine's menu
   for three seconds before any PAX code runs**. Under BIOS (not the test machine's path) the firmware runs the
   protective MBR's boot code, which loads Limine's stage 2 from partition 3; the rest is the same.
3. **The kernel's entry.** `boot/start.S` `_start`: interrupts off; Limine's base-revision word checked (refused:
   a byte to QEMU's exit port, then `cli; hlt` forever, which on a real machine is a black, silent stop); the stack
   aligned; `kmain` called. The console kernel's `kmain` (`kernel/kmain_console.lu`) then, in order:
   - `identity.mark_entry` (the TSC at entry); `triage.start` (nothing without the word `triage`);
     `interrupts.early`: PAX's GDT, TSS and IDT and CR4.MCE. **Before this line an exception is a triple fault,
     which resets the machine**: the firmware's splash comes back by itself.
   - `serial.init`, which calls `screen.early_start`: **the first use of the framebuffer.** When Limine's
     framebuffer is 32-bit RGB 8:8:8, the screen attaches through Limine's own mapping, clears the whole framebuffer
     to black and replays what was written so far. Otherwise nothing is drawn now.
   - `PAX: the console`: **the first line drawn**, through Limine's mapping, when the early screen attached.
   - `frames.start`, the identity line, `paging.build`; `screen.pause_early` (the screen stops drawing across the
     switch, since Limine's mapping of the framebuffer is not in PAX's tables), `paging.switch_to`: PAX's page
     tables live. A panic in this window prints into the screen's buffer, not onto the screen.
   - `fb.start`: the framebuffer mapped in PAX's tables (write-combining where the PAT allows) and the screen
     attached again (cleared, everything since the entry replayed). It refuses a framebuffer with no response, not
     32-bit RGB 8:8:8, outside the HHDM or not mappable; then **the console is serial only for the whole boot**, and
     the test machine has no serial port. `fb.report` says which (`screen: off, <why>`), on the serial port only.
   - Then, each with lines on the screen: the interrupts, the local APIC and timer, the FPU, the scheduler, user
     mode, the console's input, the clock, the PCI scan, the network device (an Intel controller: up to 12 s), sound,
     xHCI, the disks (AHCI), the root mounted from `root=` (a missing root panics by name), the other mounts,
     `/etc/pax-net` (DHCP, at most `wait=` seconds, 10 on the images), interrupts on, the USB disks, the lease and the
     echo, the run list read, the identity line again, `boot: <n> ms from the kernel's entry to its first program`.
4. **The first program**: `/bin/login` (`INSTALLED_RUN`), pid 1, the `pax login:` prompt. Over the network the
   system answers ssh once its daemon is up.

## 3. Where a stop leaves the screen black, and what tells them apart

"Today" is the installed disk's configuration above; "with this image" is what the instrumentation of sections 5
and 6 adds. A stop that leaves text on the screen (a Limine `PANIC`, a kernel panic after `fb.start`, a hang after
some lines) is not in this table: the photo says where it stopped.

| | where the boot stops | the screen | from outside, today | from outside, with this image |
|---|---|---|---|---|
| a | the firmware never starts Limine's program (a read error, a stale entry) | the firmware's, or black | nothing | no Limine menu, no beep, no ssh |
| b | Limine runs but its picture never reaches the display (a mode the display does not take, the output on another connector) | black | nothing: with `quiet`, a working Limine is black too | no menu seen; **then, after the menu's timeout, the kernel's two beeps**, and ssh answers if the kernel's picture is also dark |
| c | Limine stops after its menu: loading the kernel, leaving boot services, setting the kernel's mode | black, or its last screen | nothing | the menu (and Limine's verbose lines) seen, then no beep |
| d | the base revision refused (`start.S`) | black, `cli; hlt` | nothing | no beep (cannot happen with the pinned pair; listed for completeness) |
| e | an exception before `interrupts.early` | the machine resets by itself | the reset | the first beep, then the reset; the marks say `entered` |
| f | the framebuffer is not one PAX draws on (none handed, or not 32-bit RGB 8:8:8: refused at the entry) | black for the whole boot; the kernel runs | nothing; ssh would answer | **the first beep, then three pips**, never the low beep; POST codes with E (1E … 7E); ssh answers; the next boot says the previous one ran with its screen refused, and names the framebuffer and why |
| g | the kernel draws, but the display is not showing that framebuffer (no sync, another head, a mode the display rejects) | black for the whole boot; the kernel runs | nothing; ssh would answer | **both beeps**; ssh answers |
| h | a panic or hang between `pause_early` and `fb.start` (PAX's paging, the frames) | black, halted | nothing | the first beep, the second only if the early screen drew; no ssh; the marks say `entered` or `drawn (early)`, never `memory` |
| i | a hang in a driver with the screen dark for another reason | black | nothing | both beeps; the marks name the last stage reached; ssh only if the network came up |

What the report says, read against this table and nothing else. On the stick, a black screen with no menu at all
would mean the stop began before PAX's kernel ran (rows a and b), because the stick draws Limine's menu for three
seconds before the kernel is loaded. **Asked, the person at the machine says the stick's menu does show, then the
screen goes black**: so on the stick rows a and b are ruled out, and the stop or the dark display is at or after
Limine's hand-off (rows c to i). On the installed disk, `quiet` and `timeout: 0` make every row look the same, so the
installed disk's black boots say nothing yet. The kernel's early window (the entry, the first use of the
framebuffer, the pause across the switch to PAX's page tables, a refused framebuffer: rows d to h) is where the
instrumentation below looks first.

The one test that needs no new image: on a black screen, wait 30 seconds and try ssh from another machine. An
answer puts the boot in rows b, f, g or i (the system is up, the picture is not); no answer puts it in a, c, d, e or
h, or a network that did not come up.

**The leading suspect, unproven: row f.** It is the only black hand-off this lane could produce (section 8): Limine
hands the kernel a framebuffer PAX does not draw on, or none, and the kernel runs to its prompt on a screen that shows
nothing it writes. Nothing yet shows the test machine's firmware hands Limine such a mode on its black boots; its
boots that worked drew, so PAX was handed a 32-bit framebuffer then. An image from this branch tells row f apart by
ear (three pips after the first beep), by the POST digits (a second digit E) and in the next boot's log; the ssh test
above tells it apart with no new image (an answer, then `cat /proc/pax-boot` on an image from this branch).


## 4. Decisions

**Decision 1, where the stage marks live (item 4): CMOS, guarded, with every mark also in memory.** The options as
put:

- **A. CMOS**, the real-time clock's battery-backed RAM. Two port writes a byte, from the kernel's first
  instruction, under BIOS and UEFI alike, no driver and no firmware call; it survives a reset and a power-off while
  the board's battery holds; no flash, so **no flash write at any boot** (a boot writes about thirty bytes of
  battery-backed RAM). The risk: no specification reserves a CMOS byte for an operating system, so a byte PAX
  writes may be one a firmware keeps a setting or a checksum in, and such a firmware may load its defaults at the
  next power-on.
- **B. An EFI variable.** PAX has only the EFI system table's address (read once, for the vendor's name); it
  requests no EFI memory map, maps none of the firmware's runtime regions, has no call path in the Microsoft x64
  convention and has never called a runtime service. UEFI only, and each `SetVariable` is a write to the firmware's
  flash: eight a boot. Not taken.
- **C. A reserved sector of the PAX disk.** No firmware state touched, two sector writes a boot; but it can be
  written only once the disk driver is up, two thirds of the way through the boot, so it never sees the early
  stages, and a boot that stops before the disk is not even counted. Not taken.

As taken (kernel/bootmark):

- **Eight bytes, 0x78 to 0x7f of the lower bank.** Never written by PAX, whatever they hold: 0x00–0x0D (the clock's
  registers, the MC146818 data sheet), 0x0E (diagnostic status) and 0x0F (the reset reason a firmware reads after a
  reset), 0x10–0x2D and the checksum over them at 0x2E–0x2F (the PC/AT's configuration bytes), 0x30–0x3F (extended
  memory, the century at 0x32, and 0x38–0x3F, which an Intel chipset can lock), and the byte the FADT names as the
  century (checked once ACPI is read; were it among the eight, CMOS writing would stop for the rest of the boot).
  Measured (M1, both firmwares): on a cold QEMU the bytes past the clock that are set are 0x14–0x18, 0x30–0x32, 0x35,
  0x37, 0x38 and 0x3d; 0x78–0x7f read zero; QEMU has no upper bank (it reads 0xff).
- **The claim, once.** At the entry the eight bytes are read before anything is written. All zero: PAX claims them
  (`P` `X`, a boot number, the stage, the stage set, a version and a checksum), and the boot's first program logs the
  claim with the offsets in `/var/log/boot.log`. PAX's magic and a good checksum: they are PAX's, and the boot
  number goes up by one. **Anything else is another's: PAX writes nothing to CMOS that boot** and says what it
  found (`CMOS 0x78-0x7f refused (found 0x…)`), keeping the marks in memory only (R1 shows the bytes untouched
  afterwards).
- **Off:** `pax.nomarks` on the kernel's command line: CMOS is neither read nor written.
- **Writes a boot:** the eight bytes at the entry, then three (the stage, the set, the checksum) at each of up to
  seven further stages: at most 29 byte writes of battery-backed RAM; nothing to flash.
- **Left over:** a firmware byte that happens to read zero the first time PAX looks. Section 9 tells the person at
  the machine how to see whether the firmware's settings were reset and how to turn the marks off.

**Decision 2: a POST code at each stage** (yes, as ruled). Port 0x80 gets the stage as two equal hex digits, 0x11
(entered) to 0x88 (the end), so a board with a two-digit POST-code display shows the last stage with no screen. On a
boot whose framebuffer PAX refused (decision 4) the low digit is E instead: 0x1E at the refusal, then 0x3E, 0x5E,
0x6E, 0x7E and 0x8E for the stages after it, so the display tells "ran blind" from "stopped".

**Decision 4: a framebuffer PAX does not draw on stays undrawn, and is said** (as ruled). Section 8's black hand-offs
(16 or 24 bits a pixel, or no framebuffer) are not drawn on yet. Instead every boot records the framebuffer it was
handed (its size, bits a pixel, pitch, colour masks and physical address) and, when PAX refuses it, why: in the
kernel's `marks:` line, `/proc/pax-boot`, `/var/log/boot.log` and `pax-boot-status`. A refused screen is judged at
the entry, from the framebuffer's description alone (kernel/fb's `judge`, the same tests its attach makes), and has
its own sound (three pips right after the entry's beep) and POST codes (decision 2), and its mark (bit 7 of the last
stage's CMOS byte, and the same in memory) lets the next boot say the previous one ran with its screen refused.

**Decision 3 (item 6, chosen): who reads the log.** `/var/log/boot.log` is root's, 0600 (it holds the previous
boot's console); `/var/log/boot.summary` is 0644, one line a boot, and `pax-boot-status` prints its last ten for
anyone.

## 5. The beeps (item 2)

kmain_console sounds a **high beep at the entry** (count 1140, 1046.6 Hz, about 100 ms), before any use of the
framebuffer, and a **low beep the first time the console is drawn** (count 2280, 523.3 Hz, about 200 ms): after the
early screen's first line, or after kernel/fb's attach when the early screen did not attach. Each lasts 210 edges of
the 8254's channel 2 output, read back on port 0x61 bit 5, so the wait is the tone itself and needs no clock; a
channel that never turns over ends the wait after 65,536 reads with no edge. Neither touches the speaker's own books,
so no transcript moves. **A framebuffer PAX refuses** (none, or not 32-bit RGB 8:8:8; decision 4) is heard right
after the entry's beep: a rest of about 150 ms, then **three pips** of about 80 ms with 80 ms between, low, higher,
low (count 1808, 659.9 Hz; count 1356, 879.9 Hz); the rests are timed by the same edges with the speaker's data bit
off (kernel/speaker's `boot_rest`), and the low beep never follows. `pax.nobeep` silences them all.

Measured (B1–B3 and F1–F5, both firmwares, KVM): a plain boot's capture holds 1046.8–1051.4 Hz for 103–105 ms, then
522.0–524.3 Hz for 177–182 ms; `pax.nobeep` none; a machine with no display device, and each refused shape of section
8, the high tone then the three pips, 654.5–659.6 Hz, 880.5–882.5 Hz and 658.8–659.6 Hz (QEMU's capture holds 56–72
ms of each pip: it writes samples only while the speaker sounds, so the rests are not in it), and no low tone. The
pips and their rests add about half a second to a refused boot before its first line (tests/mpx3-console's legs with
no display: 972–973 ms from the entry to the first program, against 620–624 ms with one).

| heard | means |
|---|---|
| nothing | the kernel never started (or the machine has no speaker, or its 8254 does not count: check on a good boot) |
| high only | the kernel started, took the framebuffer, and stopped before drawing its first line |
| high, then three pips | the framebuffer was refused (none, or not 32-bit RGB 8:8:8): the kernel runs blind; ssh may answer |
| high, then low | the kernel drew its console; a black screen then is the display not showing what was drawn |

## 6. Limine says more (item 3)

From Limine's `CONFIG.md` at the pinned v12.9.1 (global options): `timeout` (seconds before the default entry boots;
`0` boots at once with no menu), `quiet` (suppresses every line but panics and important warnings), `verbose`
("print additional information during boot") and `serial` ("enable serial I/O for the bootloader").

- **The installed disk** (`user/install/prepare.lu`'s `config_text`): `timeout: 5`, `verbose: yes`, `serial: yes`,
  and no `quiet`. A boot now shows Limine's menu for five seconds and its loading lines, so a black screen before the
  menu (the firmware, or Limine's own picture) is told apart from one after it (the hand-off, the kernel). An upgrade
  regenerates a root copy that still holds the earlier quiet text (its digest for the root's PARTUUID is a known
  installer text).
- **The stick** (`boot/limine-usb.conf`): the same three options; its menu goes from three seconds to five.
- Unchanged: the ISO's and the tests' configurations, and the configuration `pax-upgrade arm` writes (`timeout: 5`,
  `default_entry: 1`).
- Measured: U1 (both firmwares), the installed options: Limine's lines on the serial port before PAX's first, then
  the boot to its program with no key; U2 (both firmwares), the armed shape (`timeout: 5`, `default_entry: 1`, a
  staged stand-in entry first, the installed entry in the new text second): the first entry boots with no key.

## 7. The marks and the log (items 4–6)

- **kernel/bootmark**: the stages, in order, each recorded when reached: `entered` (the first statement), `drawn`
  (the early screen's first line, through Limine's mapping), `memory` (PAX's frames and page tables live),
  `framebuffer` (mapped by PAX, the console on it), `devices` (PCI, network, USB and disks up), `root` (the volumes
  mounted), `init` (the first program started), `end` (the kernel's own end: halt, reboot or power-off). Each goes to
  port 0x80, to CMOS when it is PAX's, and to the memory area. A test-only `pax.bootstop=STAGE` halts just after a
  stage is recorded; `pax.cmosfill=XX` and `pax.logflip` are the rows' only other words.
- **kernel/bootlog**: 128 KiB at physical 64 MiB, two slots of 64 KiB, used when Limine's map lists the range as
  usable (kernel/frames withholds it). A boot keeps every console byte from its entry to its first program in one
  slot, with a check word over its header and a running sum over its bytes, flushed to memory at each line's end; the
  other slot, the previous boot's, is read at the entry and never written. A slot whose sums do not hold is refused
  and never printed.
- **The kernel's line**, on the screen before the first program: `marks: boot N; the previous boot, P, stopped at
  STAGE (CMOS); CMOS 0x78-0x7f held; log M bytes kept; framebuffer 1280x800 32 bpp pitch 5120 rgb 8:16 8:8 8:0 at
  0xfd000000, drawn` (QEMU's standard VGA under SeaBIOS; OVMF puts it at 0x80000000), or `…, refused: not 32-bit
  RGB 8:8:8`, or `framebuffer none, refused: no framebuffer`; the previous boot's part says `, its screen refused`
  when it ran blind (F1: `marks: boot 2; the previous boot, 1, completed, its screen refused (CMOS); CMOS 0x78-0x7f
  held; log 4770 bytes kept; framebuffer 1024x768 16 bpp pitch 2048 rgb 5:11 6:5 5:0 at 0xfd000000, refused: not
  32-bit RGB 8:8:8`).
- **/proc/pax-boot** (0444): `boot`, `stage`, `cmos`, `found`, `previous`, `from`, `stages`, `log`, `framebuffer`,
  `screen` (`drawn`, `refused: WHY` or `not drawn`) and `prevscreen`, one a line; **/proc/pax-bootlog** (0400): the
  previous boot's kept console.
- **user/bootlog's `pax-boot-status`**: `record` (root's) appends a block a boot to `/var/log/boot.log` (how the
  previous boot ended and whether its screen was refused, its stages, the framebuffer this boot was handed and what
  PAX made of it, what CMOS was, the claim once, the previous boot's console between markers or "refused by its
  checksum; not printed"), rotated past 256 KiB to `boot.log.1` … `.4`; and a line to `/var/log/boot.summary`
  (`screen=` and `prevscreen=` among its words), kept to its last 100 lines once past 200. With no argument, anyone:
  the last ten boots and how each ended (`boot 1: completed, its screen refused (found by boot 2 at …, from cmos)`,
  `boot 2: this boot, at init, its screen refused: not 32-bit RGB 8:8:8`). Who runs `record`: `/bin/login` as pid 1 on an installed system, before its first prompt; the live
  stick's login script. Both are on the images (`tools/mkbootstatus`, `tools/mkdistribution`).
- An install never copies the boot log (it is the running machine's own, as sudo's log is: `snapshot.lu`'s runtime
  state), and an upgrade keeps it (it is in no manifest; `tests/mpx6-install.d/upgrade.py` holds it byte for byte).

What memory does across a reset: QEMU keeps it across the monitor's reset and across the kernel's own (L1, W1, both
firmwares); a power-off of QEMU clears CMOS too (QEMU keeps no CMOS file), which a board with a battery does not. On
the test machine's firmware class, whether memory survives a reset is the firmware's choice and was not measured.

## 8. A black hand-off in QEMU (item 9)

`tests/mpx6-bootlog.d/handoff.py` boots the console kernel under one display shape a case and, at the kernel's halt,
takes QEMU's screendump of what the display scans out:

| shape | firmware | the kernel's screen line | the picture | beeps (at `bf210a69`, before the pips) |
|---|---|---|---|---|
| standard VGA | BIOS, UEFI | 1280x800 32 bpp | text | high, low |
| Limine `resolution: 1024x768x16` | BIOS | `off, not 32-bit RGB 8:8:8` | **black, the kernel ran** | high only |
| Limine `resolution: 1024x768x24` | BIOS | `off, not 32-bit RGB 8:8:8` | **black, the kernel ran** | high only |
| the same two | UEFI | 1280x800 32 bpp (the firmware offers 32 only) | text | high, low |
| cirrus | BIOS | `off, not 32-bit RGB 8:8:8` | **black, the kernel ran** | high only |
| cirrus | UEFI | 800x600 32 bpp | text | high, low |
| virtio-gpu-pci (512 MiB and 8 GiB) | UEFI | `off, no framebuffer` | **black, the kernel ran** | high only |
| VGA without EDID | BIOS, UEFI | 1024x768, 1280x800 | text | high, low |
| VGA at 3840x2160; and a 2-s menu, then that mode | UEFI | 3840x2160 32 bpp at 2x | text | high, low |
| Limine `resolution: 1366x768` | BIOS | 1280x800 (Limine fell back) | text | high, low |
| Limine `resolution: 1366x768` | UEFI | 1366x768, pitch 5464 | text; QEMU's scanout 1360 wide | high, low |
| bochs-display, ramfb | UEFI | 1280x800, 800x600 | text | high, low |
| virtio-vga | BIOS | 1024x768 | text | high, low |
| qxl | UEFI | not run: the test image's QEMU has no QXL | | |

So QEMU does show a black hand-off, of one kind: **Limine hands the kernel a framebuffer PAX does not draw on (16 or
24 bits a pixel, under BIOS) or none at all (a UEFI display with no framebuffer Limine passes on)**, and the kernel
runs to its program on a screen that shows nothing it writes. At `bf210a69` each was heard as one beep and logged as
stages without `drawn` and `framebuffer`; since decision 4 each sounds the pips and says what it was handed (the F
rows, the head's take): Limine's `resolution: 1024x768x16` under SeaBIOS, `1024x768 16 bpp pitch 2048 rgb 5:11 6:5
5:0 at 0xfd000000`; `x24`, `1024x768 24 bpp pitch 3072 rgb 8:16 8:8 8:0 at 0xfd000000`; the cirrus card under
SeaBIOS, `1024x768 24 bpp pitch 3072 rgb 8:16 8:8 8:0 at 0xfc000000`; virtio-gpu under OVMF, `none`; and the control,
`resolution: 1024x768x16` under OVMF, `1280x800 32 bpp pitch 5120 rgb 8:16 8:8 8:0 at 0x80000000`, drawn. None was
produced by a mode change, a missing EDID, a large mode or an odd pitch,
and no case put the framebuffer above 4 GiB. This is not shown to be the test machine's cause: its console has drawn on
boots that worked (PAX draws only on a 32-bit framebuffer), and nothing here says what its firmware hands Limine on a
boot that goes black. It is the leading suspect (section 3, row f), and the image now names it: such a boot sounds
the entry's beep then three pips, writes POST codes with E, and its marks, `/proc/pax-boot` and the next boot's log
name the framebuffer handed and why it was refused (decision 4; the F rows hold each of the shapes above, and a
control where OVMF hands 32 bits). If the test machine's black boots give the pips, this is the class; if they give
high then low, it is not.

## 9. The page for the person at the machine (item 8)

Nothing here was tried on the test machine; every row above is QEMU. This page says what an image from this branch
does there, what to look and listen for, and what to send back.

**The leading suspect, not proven.** In QEMU the one way this lane could make a boot go black after Limine's menu is
Limine handing PAX a screen mode PAX does not draw on (16 or 24 bits a pixel instead of 32, or no framebuffer at
all): PAX then runs all the way to its login prompt with nothing on the screen. Whether the test machine's firmware
ever does that is not known; on its good boots it hands 32 bits. **The test that needs no new image:** on the next
black screen, wait 30 seconds and try `ssh YOU@ADDRESS` from another machine. If it answers, the system is up and only
the picture is wrong, which fits this suspect (and a few other display faults); if it does not, the boot really
stopped. With an image from this branch, the three pips below and `cat /proc/pax-boot` over that ssh settle it.

**Once, on a boot that works.**
1. Limine's menu now shows for five seconds on the installed disk too, with its loading lines under it. Let it
   count down.
2. Listen as the menu's countdown ends: **a high beep, then a low one**, a second or two apart. If a boot that
   works makes no beep at all, this machine cannot sound them (no speaker on the board's speaker header, or the
   timer that drives it does not run), and on a black screen their silence means nothing: go by the marks.
3. Just above the login prompt, one line: `marks: boot 1; the previous boot: none; CMOS 0x78-0x7f claimed; log none;
   framebuffer 1920x1080 32 bpp pitch 7680 rgb 8:16 8:8 8:0 at 0x…, drawn` on the first boot of the image (the size
   is whatever the firmware gave), then `marks: boot 2; the previous boot, 1, completed (CMOS); …` and so on.
   Photograph the framebuffer part once: it is what a good boot is handed.
4. Then check the firmware's settings once (the next part).

**Did the firmware reset its settings?** The marks write eight bytes of the firmware's battery-backed CMOS (offsets
0x78–0x7f), which no standard reserves for an operating system. PAX writes them only when it finds them all zero or
holding its own record, never anything else; but a firmware that keeps a setting in a byte that reads zero could
take PAX's write for corruption. After the first two or three boots of the image:
- watch the firmware's own screen at power-on for a message that its settings were reset or are bad, or a prompt
  to press a key to enter setup or load defaults;
- enter setup (Delete at power-on) and compare with what you set before: the SATA mode (it must stay AHCI), the
  boot options and their order, Secure Boot, the memory profile and any overclock, the clock's date and time.
If anything moved, turn the marks off (below) and say so: that ends the CMOS store on this machine.

**Turning the marks or the beeps off.** Words on the kernel's command line: `pax.nomarks` (CMOS neither read nor
written; port 0x80 and the memory log stay) and `pax.nobeep`. For one boot: at Limine's menu use the edit key its help
line names on the entry, add the word to the `cmdline:` line, and boot from the editor with the key it names. For
good: add the word to the `cmdline:` line of `/boot/limine/limine.conf` on the disk's EFI partition from another
system. An edited `limine.conf` makes `pax-upgrade arm` refuse (it never merges an edited configuration): take the
word out before an upgrade over ssh, or upgrade from the stick.

**On the next black screen.**
1. When did it go black: before Limine's menu, during it, or after its countdown ended?
2. What did you hear: **nothing** (the kernel never started), **one high beep** (the kernel started and stopped
   before drawing its console), **a high beep then three quick pips, low, higher, low** (PAX refused the screen it
   was handed and is running blind: the leading suspect), or **high then low** (the kernel drew its console; the
   screen is not showing it)?
3. If the board has a two-digit POST-code display, what does it read? PAX writes `11` (entered), `22` (drawn), `33`
   (memory), `44` (framebuffer), `55` (devices), `66` (root), `77` (the first program), `88` (the end); on a boot
   whose screen it refused, the same stages with `E` as the second digit (`1E`, `3E`, `5E`, `6E`, `7E`, `8E`).
   Anything else is the firmware's own code, so the kernel never wrote one.
4. **Wait 30 seconds and try ssh from another machine** (`ssh YOU@ADDRESS`, the address it had before). An answer:
   the system is up and only the picture is wrong. Run `cat /proc/pax-boot` and `pax-boot-status` there and send
   both: their `framebuffer` and `screen` lines say what the screen was handed and whether PAX refused it. The ssh
   test alone needs no new image.
5. Then press the reset button rather than holding the power button: a reset may keep the kernel's console in
   memory for the next boot to save; the marks survive either.

**After the next good boot.**
- The `marks:` line above the login prompt: `the previous boot, N, stopped at STAGE` (or `completed`), with `, its
  screen refused` when that boot ran blind. Photograph it.
- `pax-boot-status` (any user): the last ten boots and how each ended.
- `sudo cat /var/log/boot.log` (or as root): this boot's block names the previous boot's end, its stages and, when
  memory survived the reset, its console between `--- console of boot N ---` and `--- end of the console of boot N
  ---`. Send the block (or a photo).

What each end means (any of them with `, its screen refused`: that boot ran blind, the leading suspect):
`entered` or `drawn` (stopped in the kernel's first moments, before PAX's own page tables);
`memory` (stopped before the framebuffer was mapped); `framebuffer`, `devices` or `root` (the console was up; a hang
in the drivers or the disks; the console log says which); `init` (the system reached its first program: a black
screen then is the display); `completed` (shut down cleanly).

## 10. Prediction, scored

`notes/px118-prediction.txt`, committed before the first change (`d3887d20`):

| predicted | measured |
|---|---|
| 1. two tones, high then low; none with `pax.nobeep`; the high alone with no framebuffer; a quarter second longer; the speaker's books unmoved | **right**: 1046.6–1051.4 Hz for 103–105 ms, then 522.0–523.4 Hz for 177–182 ms; none; 1046.6 Hz for 90–91 ms (B1–B3, both firmwares; since decision 4 a boot with no framebuffer sounds the pips after it); no `speaker:` line. **Not predicted:** the speaker suite's captures would hold the boot's tones too (its beep row counts two), so `tests/mpx3-speaker` boots with `pax.nobeep`; a sound card's capture holds none (B4) |
| 2. Limine's menu and loading lines on the serial port before PAX's first line, both firmwares; the suites that read the serial log from PAX's first line unmoved | **right** on the first (U1: 51 lines under BIOS, 3 under UEFI, where the firmware's console carries less); the second is section 11's regression take |
| 3. QEMU's CMOS kept across a guest reset and the monitor's reset; the bytes picked untouched by either firmware; zero on a cold start | **right** (M1, M2, W1, both firmwares). **Not predicted:** QEMU has no upper bank (0x80–0xff read 0xff) |
| 4. guest memory kept across both resets; the log intact by its checksum under SeaBIOS and OVMF; none on a cold start | **right** (L1, W1, both firmwares) |
| 5. each stop leaves its stage; the next boot logs it; a changed log refused; an upgrade keeps boot.log; the stick unchanged when the store is absent or read-only | **right** (S1–S7, K1–K3, L2, R1, N1); the upgrade row is the full tier's upgrade leg, not run here (section 12). **Not predicted:** Limine does not boot under OVMF in 64 MiB, so N1's missing area is shown under BIOS only |
| 6. no black hand-off in QEMU | **wrong**: four shapes give one (section 8): a 16- or 24-bit framebuffer under BIOS (Limine's `resolution:` with a depth, or a cirrus card) and OVMF with virtio-gpu (no framebuffer at all) |

## 11. Evidence index

Every take ran under KVM on the Linux build host's light slots (two CPUs, 6 GiB, the lane's Ubuntu 24.04 container
with QEMU 8.2.2 and Ubuntu's OVMF), never on a machine of the kind in the report.

- **The beeps**, red first: `tests/mpx6-bootlog` committed alone at `6160c548`, where B1 and B3 fail on both
  firmwares ("the capture holds no tone") and B2 (no tone wanted) passes; green at `2fcc5b9d` (B1–B3, both
  firmwares, 43 s).
- **The marks, the log, the stops**: `tests/mpx6-bootlog --tier native --firmware both`, rows B1–B4, M1, M2, L1,
  S1–S7, R1, L2, W1, N1, U1, U2, P1, K1–K3 on each firmware; the takes at `b38a3bf8`, `c6b9eab7`, `4d74a909` (every
  row on both firmwares) and the head (the first two found K1's mode test reading debugfs's permission bits as a
  whole mode, and N1 asking OVMF to boot in 64 MiB; both fixed in the rows, `f8d10113`, `c8213cbf`).
- **A refused screen** (decision 4), red first: the F rows, B3's pips and M2's framebuffer part committed alone at
  `091ab2c0` and `16cc60c2` and taken there (`PX118_ROWS="B M F"`, both firmwares): B3 fails on both (the high tone
  alone, no pips), M2 and F1–F5 fail on their firmwares (the marks line has no framebuffer part), B1, B2, B4 and M1
  pass; green from `d6e25761` on: every row of `tests/mpx6-bootlog` on both firmwares, F1–F5 included (362 s), with
  `tests/ci-plan`.
- **Item 9**: `tests/mpx6-bootlog.d/handoff.py` at `bf210a69`, 20 cases, section 8's table.
- **The neighbours**, at `d6e25761`: `tests/mpx6-triage`, `tests/mpx3-screen`, `tests/mpx3-speaker`,
  `tests/mpx6-install --only snapshot` and `--only pax-upgrade`, `tests/mpx6-staged`, and `tests/mpx3-console`, each
  `--tier native --firmware both` where it takes legs, all exit 0: the `marks:` line, the beeps, the pips and the new
  Limine options move no other suite's rows. `tests/mpx3-console` needs its Linux reference (`tools/linux-tty`) to
  unshare a pid namespace, which the build host's container allows only with that capability added: its first try
  without it ran PAX's side whole but had no Linux session to compare (T0, and T2 and T5 against an empty one).
- **The assembler seam**: `tests/kernel-as`. The hosted run at the PR's first head found K5 red, the only
  red job: the pinned clef refused `boot/cpu.S` line 140, `clflush (%rdi)` (`unknown_mnemonic clflush: SDM vol.2
  instruction set`), and its table has no `mfence` either. `pax_clflush` now writes both as their encodings
  (`401439cb`), as `cpu.S` already writes the debug-register moves for clef, and the clef kernel is again byte for
  byte the GNU-as one (K5). The lane's local records had not run this suite.
- **The plant** (section 12): `px118-plant-guard-4`, one hunk in `kernel/bootmark/bootmark.lu` on the final head:
  another's CMOS bytes taken as free. R1 goes red by name on both firmwares.
- **The gauntlet** at the final head, through the org's recorder, kept with the lane's evidence outside the tree:
  `tests/ci-plan`, `tests/mpx6-bootlog`, the two installer units, `tests/mpx6-staged`.

## 12. Done-when

**Decisions** (section 4): 1, CMOS guarded with every mark also in memory, the offsets excluded and the claim logged
once, as ruled; 2, POST codes at port 0x80 (with E for a refused screen), as ruled; 3, `/var/log/boot.log` 0600 and
`/var/log/boot.summary` 0644, chosen; 4, a 16- or 24-bit framebuffer (or none) is not drawn on yet, and every boot
names the framebuffer it was handed and why it refused one, with its own pips and POST codes, as ruled; the Limine
options (section 6) and the beeps (section 5), accepted as done.

**Not done.**
- The test machine itself: section 9 is the page for it.
- The full tier's upgrade leg (`tests/mpx6-install.d/upgrade.py`, which now also holds `/var/log/boot.log` byte for
  byte), `tests/usb-stick`, the metal-shaped install leg, `tests/mpx6-install --rows full` and the over-ssh upgrade leg
  (`ssh-upgrade.py`): heavy legs left to CI's full tier. U1 and U2 show the new installed options and the armed
  shape booting with no key.
- A framebuffer above 4 GiB: no QEMU display device here put one there.
- `tests/mpx6-firmware` (kernel/fb is in its map: the metal shapes, 8 GiB guests, the USB and timer suites): too
  heavy for a light slot, left to CI's full matrix with the cross-cutting footprint.
- Whether the test machine's firmware keeps memory across a reset, and whether its board has a speaker or a
  POST-code display: section 9 asks.

**Checklist** (light takes; the gauntlet at the head):
- [x] `tests/ci-plan`
- [x] `tests/mpx6-bootlog --tier native --firmware both` (B1–B4, M1, M2, L1, S1–S7, R1, L2, W1, N1, U1, U2, P1, K1–K3, F1–F5)
- [x] `tests/mpx6-bootlog.d/handoff.py` (item 9's probe)
- [x] `tests/kernel-as --tier native` (K5: the clef kernel byte for byte the GNU-as kernel)
- [x] `tests/mpx6-install --only snapshot` (I-runtime-boot-log, red first at `389f933e`)
- [x] `tests/mpx6-install --only pax-upgrade`
- [x] `tests/mpx6-staged --tier native --firmware both`
- [x] `tests/mpx3-console`, `tests/mpx6-triage`, `tests/mpx3-screen`, `tests/mpx3-speaker` (`--tier native --firmware both`)
- [ ] the full tier's install, stick and upgrade legs, and `tests/mpx6-firmware` (CI)
