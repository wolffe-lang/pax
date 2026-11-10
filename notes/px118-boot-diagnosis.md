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
| f | the framebuffer is not one PAX draws on (both attaches refuse) | black for the whole boot; the kernel runs | nothing; ssh would answer | **the first beep only**; ssh answers; the next boot's log says the boot completed |
| g | the kernel draws, but the display is not showing that framebuffer (no sync, another head, a mode the display rejects) | black for the whole boot; the kernel runs | nothing; ssh would answer | **both beeps**; ssh answers |
| h | a panic or hang between `pause_early` and `fb.start` (PAX's paging, the frames) | black, halted | nothing | the first beep, the second only if the early screen drew; no ssh; the marks say `entered` or `drawn (early)`, never `memory` |
| i | a hang in a driver with the screen dark for another reason | black | nothing | both beeps; the marks name the last stage reached; ssh only if the network came up |

What the report says so far, read against this table and nothing else: **on the stick, a black screen with no menu
at all means the stop or the dark display began before PAX's kernel ran** (rows a and b), because the stick draws
Limine's menu for three seconds before the kernel is loaded. On the installed disk, today's `quiet` and `timeout: 0`
make every row look the same. Whether the stick's black boots really showed no menu at any moment is for the person
at the machine to confirm; it is the first thing the page in section 8 asks.

The one test that needs no new image: on a black screen, wait 30 seconds and try ssh from another machine. An
answer puts the boot in rows b, f, g or i (the system is up, the picture is not); no answer puts it in a, c, d, e or
h, or a network that did not come up.

## 4. Decision 1: where the stage marks live (item 4)

What the marks must do: record, at each stage (entered, drawn, memory up, framebuffer mapped, console drawn, root
mounted, first program started, the clean end), how far this boot got; survive a reset **and** a power-off, since a
person facing a black screen holds the power button as often as they press reset; be written from the kernel's first
instructions, before any driver; and be read by the next boot before it writes its own. A boot counter beside them
says how many boots there were, so a failed boot is never invisible.

**A. CMOS (the real-time clock's battery-backed RAM).**
- Reached by two port writes a byte (index to 0x70, data at 0x71; a second bank of 128 bytes at 0x72/0x73 on the
  chipsets that have one), from the kernel's first instruction, under BIOS and UEFI alike, with no driver and no
  firmware call. PAX already reads it (`kernel/rtc`).
- Survives a reset and a power-off while the board's battery holds; no flash: **zero flash writes per boot**. A
  boot writes about 30 bytes of battery-backed RAM (the counter once, then the stage, the stage set and a checksum
  at each of eight stages).
- The risk: no specification reserves CMOS bytes for an operating system. Bytes 0x10–0x2D are the AT checksum's,
  0x0F is the reset-reason byte a firmware reads after a reset, and the rest of both banks belong to the firmware by
  custom; a firmware that keeps a setting or a checksum in a byte PAX writes may load its defaults at the next
  power-on. That cannot be ruled out without the firmware's source, which this lane may not read.
- The guard, so a byte the firmware uses is never overwritten: eight bytes, picked by measurement as bytes neither
  QEMU's firmware writes; PAX writes them only when it finds them all zero (first use: it claims them with a magic
  word and a checksum) or holding its own magic with a good checksum. Anything else is another's: PAX writes nothing
  to CMOS that boot, says so in one line, and keeps the marks in memory only (item 5's area). The word
  `pax.nomarks` turns CMOS off entirely. Left over: a firmware byte that happens to read zero when PAX first looks.
- Covered in QEMU (its CMOS is emulated and survives a guest reset; measured before use).

**B. An EFI variable.**
- What PAX has: the EFI system table's address (Limine's EFI system table response), read once for the firmware's
  vendor string (`kernel/acpi`). It requests no EFI memory map, maps none of the firmware's runtime regions, has no
  call path in the Microsoft x64 convention, and has never called a runtime service (px115 found the same). A
  `SetVariable` needs all of that, and the FPU state the firmware may use, before the first stage could be written.
- UEFI only: a BIOS boot keeps no marks.
- Each `SetVariable` is a write to the firmware's flash store: **eight flash writes per boot**, plus the store's own
  reclaim cycles, on firmware whose variable store's behaviour when it fills cannot be tested here.
- Not recommended.

**C. A reserved sector of the PAX disk** (for example in the 1 MiB before the first partition, which the installer
zeroes and nothing uses past the install log's bytes 65536–131071).
- No firmware state touched. Flash wear is small: **two sector writes per boot** (the boot begun, the clean end),
  through the SSD's own wear levelling.
- But it can be written only once the disk driver is up (`block.start`, two thirds of the way through the boot), so
  every stage this report is about (before the first line, before PAX's paging, before the framebuffer is mapped)
  is invisible: a boot that stops before the disk leaves nothing, and the next boot cannot even count it.
- The stick (read-only, or absent at the next boot) keeps nothing.

**Not an option on its own, but carried with any of them: memory that survives a warm reset** (item 5's early-log
area). It costs nothing to write and holds every stage and the early log, but a power-off clears it, and whether a
firmware keeps it across a reset is the firmware's choice (measured in QEMU; unknown on the test machine).

**Recommended: A, guarded as above, with every mark also kept in item 5's memory area.** It is the only store that
sees the early stages, survives the power button, works under both firmwares and wears nothing. The guard bounds the
firmware risk to a byte that reads zero, and `pax.nomarks` removes it. If no CMOS write is acceptable on the test
machine at all, C with the memory area is the fallback: it loses the early stages after a power-off, which is the
case this report is about.

**Decision 2 (proposed beside it): a POST code at each stage.** The same stage number also written to port 0x80,
the PC's power-on self-test port: on a board with a two-digit POST code display (or a POST card), the display then
shows the last stage PAX reached, with no screen at all. One port write a stage, nothing stored. Recommended.

**Decision 3 (item 6, chosen, not asked): who may read the boot log.** `/var/log/boot.log` is root's, 0600 (the early
log can hold anything the kernel printed); a second file, `/var/log/boot.summary`, 0644, holds one line a boot (`boot N:
previous boot stopped at STAGE` or `completed`, and the time), the last ten of which `pax-boot-status` prints for
anyone. Both are bounded and rotated by count.

## 5. The beeps (item 2)

(Implementation follows; see the evidence index.)

## 6. Limine says more (item 3)

(Implementation follows.)

## 7. Evidence index

(To come.)

## 8. The page for the person at the machine (item 8)

(To come, at the end of the lane.)
