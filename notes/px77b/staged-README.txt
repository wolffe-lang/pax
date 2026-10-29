PAX smoke stick: pax trunk 101e7761, rebuilt after px76 (px77b, 2026-10-29)

BOOT THIS ONE: pax-stick-101e7761.img
Size:    794820608 bytes (758 MiB)
SHA256:  598d34396c2c8c05d70a92037dc5dc041fd346b5d5d14312f6db6feaabf7378e
Commit:  101e7761cd648accacf9e4fbcb1bede5443a6de7 (stock trunk at px76's merge, pax#236; no cherry-pick)
Kernel:  /boot/pax, 2463288 bytes, sha256 ba8fda6f9c11e14107827ef5f43c2213370b512f517fd497b77b4fed4df3b98e
Archive: /boot/initramfs.cpio, 384888308 bytes, sha256 08a0c1dd2d7dff4755d834b71bb641628c76a1e52256dbda55242430a5e32b52
Conf:    boot/limine-usb.conf, unchanged (sha256 d3b4a14b848cbcb69a2ca605bc415d78236e28e7fde869e27a5110f17b38fb39,
         the same file as on px77a's stick): a three-second menu, default entry "PAX live (root, no password)".
Payload: px77a's recipe: the release initramfs plus BOOT.md's live-only login entry; no disk root, no auto-install.
Screens: the reference PNGs are in 101e7761/ (the checklist below names each).

The older stick beside it, pax-stick-6ccfe3fe+f1f8137b.img, and the PNGs at this folder's top level are
px77a's (2026-10-28). Its README is README-6ccfe3fe+f1f8137b.txt (px77a's README.txt, copied unchanged).

This is for the coordinated first-look smoke boot, NOT installation on kasumi.
Never run the installer's write flow or a formatter on kasumi's disks. `pax-install --inventory` only reads.

What changed since px77a's stick
- Stock trunk. px77a's stick was trunk 6ccfe3fe plus px76's absent-UART fix cherry-picked; that fix is merged.
- px76 (UEFI on metal): the kernel prints the firmware's machine first (firmware, memory map, every ACPI
  table, the clock and the tick it calibrated); the tick no longer needs the 8254 PIT (HPET, else the ACPI
  PM timer); kasumi's xHCI is driven on MSI, so the USB keyboard is expected to type; xHCI BARs above 4 GiB;
  the screen at whatever GOP mode it is handed, glyphs doubled above 2560 pixels wide; reboot through the
  FADT reset register, then port 0xCF9, then a triple fault, each named on screen; ACPI S5 power-off in
  the kernel (no program on the image asks for it: see step 6); x2APIC by MSR if the firmware hands over
  in x2APIC mode.
- px75b (AHCI): the SATA disks are driven read-only at boot: one line per controller and per disk, and
  `pax-install --inventory` lists each with its model and serial.
- px84: the installer and disk tools past 2 TiB (not used in a smoke boot).

Qualified on hasu: QEMU 8.2.2 (TCG), q35, fresh OVMF 4M variables, -serial none, the exact image read-only
as USB storage, a USB keyboard, writable 2 GiB NVMe and SATA files of known content. Four boots, all exit 0:
  a  px77a's machine unchanged (qemu-xhci, INTx; the PIT present; 2 GiB); ends `reboot`.
  b  kasumi's shape (px76's F8): no PIT, both xHCIs on MSI only, BARs above 4 GiB, 8 GiB, a display that
     offers 3840x2160; Limine still hands over 1280x800 (it keeps the firmware's mode); ends at ACPI S5,
     reached by a debugger turning `reboot -h`'s halt into a power-off request (no program asks for it).
  c  b with `resolution: 3840x2160` added at Limine's editor for that boot only: the screen at 3840x2160,
     glyphs at 2x, 240x67 cells; ends `reboot`.
  d  b ended as step 6 asks: `reboot -h`; the end summary and `halt` stay on screen.
Root and every command typed through the USB keyboard, first try, on INTx (a) and on MSI (b, c, d).
uname -a exits 1: "uname: -s: raw kernel field unavailable (wolf-lang#907)" (known, as on px77a's stick).
Both disk files byte-identical before and after every boot (sha256 of every byte).
Boot lines before the login prompt: 383 lines in the kernel's transcript; 388 rendered rows at 1280x800
(px77a's stick: 358), 385 at 3840x2160.
All four image digest reads match: twice on hasu, twice here.

Photo checklist (px77b): see PHOTOS below.

PHOTOS
0. Take a phone VIDEO from the Limine menu to the login prompt. Without a serial port the screen is the only
   record, and about 380 lines scroll past; the firmware, ACPI, clock, xHCI and disk lines will have
   scrolled off by the login prompt. Then the photos below.
1. The Limine menu before its countdown ends: 101e7761/01-limine-menu.png ("Limine 12.9.1 (x86-64, UEFI)",
   "PAX live (root, no password)", "Booting automatically in 3..."). Let the default boot. Do not press E
   (the qualification used Limine's editor only to test another screen mode).
2. The last boot screen before the login, and the video's frames of the early lines.
   101e7761/02-last-boot-line.png is the moment the first program starts: firmware:, memory:, the acpi:
   lines, clock:, timer:, console: com1 absent, xhci N: BAR0 ... / ports 8 MSI vector 8N ..., ahci0:,
   nvme0:, block:, "PAX: kernel 101e7761...; release 98bbabc6", "xhci: keyboard ...", "run 1: /bin/pelt".
   On kasumi expect instead: its board vendor on firmware:; its own ACPI tables (not BOCHS); clock: HPET
   ... checked against the PM timer; timer: LAPIC calibrated by HPET; perhaps "apic: x2APIC mode ..."
   (the first witness of that path); screen: <the mode kasumi's firmware left> (at 2x if wider than 2560);
   console: com1 absent; for each xHCI a BAR0 above 4 GiB and "ports N MSI vector 8N"; "ahci0: 8086:43d2
   at 00:17.0, ..." and "ahci1: 1b21:0612 at 6e:00.0, ..."; "sda model "Samsung SSD 870 EVO 4TB" serial
   ..." and sdb the SanDisk; nvme0: 144d:a80c ...; their block: lines. Photograph any line that says
   refused, INTx, timeout, FAIL or PANIC, or that a controller has no line at all (an Intel controller in
   RST/RAID mode prints none). If the boot stops, photograph the whole screen: its last line names where.
3. The login prompt before typing: 101e7761/03-login.png (1280x800) and 03-login-3840x2160.png (a 4K mode):
   "PAX live medium: log in as root (no password)." then "login:".
4. Type root and Enter. NEW: the keyboard is expected to work (MSI). If nothing appears, photograph the
   screen and note which USB port the keyboard is in. The video tells the next lane which failure it is:
   no "xhci: keyboard ..." line means the keyboard was never found; the line present but no typing means
   its interrupts do not arrive.
5. Type, in order: uname -a (exits 1, wolf-lang#907, expected), cat /etc/pax-release (kernel 101e7761...),
   ls /dev (NEW: sda and sdb beside nvme0n1). Photograph: 101e7761/04-after-commands.png.
   Then pax-install --inventory and photograph: 101e7761/05-disk-listing.png (05-disk-listing-3840x2160.png
   at 4K). NEW: one row per disk with "model=... serial=...": /dev/nvme0n1 (the CachyOS NVMe), /dev/sda (the
   Samsung 870 EVO 4TB), /dev/sdb (the SanDisk 512G), each "mounted=false root=false". It only reads.
6. The end. There is no `poweroff` on this image ("pelt: line 104: poweroff: not found"): PAX's only end
   command is `reboot`, which asks for a restart, or a halt given any argument. The kernel's S5 path works
   (101e7761/06-poweroff.png, "poweroff: ACPI S5 types 0/0", reached under a debugger) but nothing typed
   can ask for it yet. So type: reboot -h
   The end summary stays on the screen (101e7761/07-halt.png): one block: line per disk with
   "0 writes (0 sectors), 0 flushes", the NVMe "shut down", then "halt". PHOTOGRAPH IT: it is the
   no-write witness on metal. Then hold the power button to turn kasumi off.
   (`reboot` alone restarts at once through the FADT reset register; its summary is gone before it can be
   photographed.) If any block: line shows writes above 0, photograph it and stop.
