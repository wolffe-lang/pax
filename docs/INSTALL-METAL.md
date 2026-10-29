# Installing PAX on kasumi

This is the runbook for installing PAX from the USB stick onto a SATA SSD in kasumi, after the first boot (px77) has
shown that the stick boots and the keyboard works. Every step below was rehearsed in QEMU on a machine shaped like
kasumi (`tests/mpx6-kasumi`: OVMF, no serial port, the stick and the keyboard on one xHCI controller, an NVMe disk
standing in for CachyOS, three SATA disks on the AHCI controller). The reference screens it took are in
`notes/px78/screens/`; each step names the one to compare against.

## What the installer will and will not write

The installer writes to one disk only: a disk whose model and serial match a line in `/pax/install-targets` on the
stick. The stick ships with that file naming no disk, so until you add a line, the installer writes nothing anywhere.
Every other disk is listed with its model and serial and refused by name. Four refusals come before the list is even
read: the disk `/` is on, a mounted disk, a read-only disk, and the stick itself (any disk whose first partition holds
`/boot/initramfs.cpio`, which is how the installer recognises a PAX live medium).

kasumi's own disks are never to appear in the file:

| disk | what it is | rule |
|---|---|---|
| `nvme0n1` | Samsung 990 PRO, the CachyOS root | never on the list |
| `sda` | Samsung 870 EVO 4TB, `/mnt/steamlib` | never on the list |
| `sdb` | SanDisk 512G | never on the list |
| the new SSD | the install target you plug in | the only line in the file |

Under PAX the disk names can differ from CachyOS's (PAX names SATA disks in port order, then USB disks). The model and
serial are what the list matches, never the name.

## What you need

- The stick, written from the PAX image with balenaEtcher (or `tools/usb-write`), as for px77.
- The target SATA SSD, plugged into a free SATA port on the board.
- A phone camera. There is no serial port: the photos and the log the installer writes to the stick are the record.

## 1. Read the target's model and serial in CachyOS

Plug in the target SSD and boot CachyOS as usual. Find the new disk; it is the one that is not `nvme0n1`, `sda` or
`sdb`:

```sh
lsblk -o NAME,SIZE,TRAN,MODEL,SERIAL
```

Then read its identity exactly as the installer will compare it (replace `sdc` with the new disk's name):

```sh
cat /sys/block/sdc/device/model /sys/block/sdc/device/serial
```

Linux shows a SATA disk's model as the SCSI product field, at most 16 characters, so a "Samsung SSD 870 EVO 500GB"
reads `Samsung SSD 870` here. PAX shows the same 16 characters on purpose, so copy what `cat` prints, not what `lsblk`
or the label on the drive says. Trailing spaces do not matter; the installer trims both values.

## 2. Write the line on the stick

Plug the stick in under CachyOS and find it (`TRAN` is `usb` in the `lsblk` above; call it `sdX`). Its first
partition is a FAT32 EFI system partition that any OS can write. Append one line, then read the file back. The
commands are bash's; from fish, run `bash` first. Replace `sdX` with the stick and `sdc` with the target:

```sh
sudo mount /dev/sdX1 /mnt
d=sdc
printf 'model=%s serial=%s\n' "$(sed 's/ *$//' /sys/block/$d/device/model)" "$(sed 's/ *$//' /sys/block/$d/device/serial)" \
    | sudo tee -a /mnt/pax/install-targets
cat /mnt/pax/install-targets
sudo umount /mnt
```

The file's last line should read like `model=Samsung SSD 870 serial=S6PXNM0T612345A`. Lines starting with `#` are
comments. A line that is not exactly `model=… serial=…` makes the installer refuse every disk and name the line, so
nothing is written by mistake. Leave `/pax/logs/` alone: the installer writes its logs there.

## 3. The firmware settings

kasumi is an ASUS ROG Maximus XIII Extreme. Press Delete at power-on for setup and F8 for the one-time boot menu (the
board manual's keys; the splash screen names them too).

**SATA mode: AHCI.** kasumi's SATA controller already runs in AHCI mode (CachyOS sees it as `[8086:43d2]`, a SATA
controller, class 01.06), so nothing needs changing. In setup it is under Advanced, PCH Storage Configuration, SATA
Mode Selection. If someone has set it to Intel RST, PAX attaches no SATA disk and prints, early in the boot text:

```text
AHCI: Intel RST/RAID mode at 00:17.0: switch the firmware to AHCI
```

In that case set it back to AHCI. CachyOS itself needs AHCI to see `sda` and `sdb`.

**Secure Boot.** px76's notes record nothing about Secure Boot on kasumi, and nothing in PAX is signed for it: the
pinned Limine EFI program on the stick is not a Secure Boot signing or key-enrolment solution (`docs/BOOT.md`). If the
firmware enforces Secure Boot, it refuses the stick, usually by skipping it in the boot menu or showing a security
violation. If px77's first boot already worked, leave the setting as it was. If not, turn enforcement off (on ASUS
boards: Boot, Secure Boot, OS Type: Other OS). If CachyOS unlocks an encrypted disk through the TPM, changing Secure
Boot changes what the TPM measures, and CachyOS will ask for the passphrase or recovery key on its next boot: have it
to hand.

**Boot order.** Change nothing. PAX writes no firmware boot entries; the stick and the installed disk both boot by
the removable-media path `\EFI\BOOT\BOOTX64.EFI`, which the firmware offers from its boot menu.

## 4. Boot the stick and check the list

With the target SSD and the stick both plugged in, power on, press F8, and pick the stick's UEFI entry. Limine shows
its menu (px77a's `01-limine-menu.png`); let the default boot. At `login:` type `root` (the live medium has no
password). Then:

```sh
pax-install --check
```

Compare with `02-check.png`. You should see:

- `Install log: not written: --check writes nothing`;
- `Disks (N); install allow-list /dev/sdX1:/pax/install-targets, 1 line(s)`;
- `nvme0n1`, and each SATA disk that is not the target, with its `model=… serial=…` and
  `refused: not on the install allow-list: …`, followed by the line that would allow it (never add it);
- the target with `on the install allow-list`;
- the stick with `refused: a PAX live medium (the boot stick, or a copy of it)`.

**Photo 1: this screen.** If the target is refused, stop here: its refusal prints the exact line that would allow it,
so compare that with the file on the stick (step 2). If `nvme0n1`, `sda` or `sdb` is anything but refused, stop and
power off (`reboot -p`); do not install.

## 5. Install

Run the guided installer:

```sh
pax-install
```

1. The target page (`03-target-page.png`) numbers every disk and marks the refused ones; only the target can be
   chosen. Type its number and Enter.
2. Type a user name (uid 1000, no password in this preview).
3. Answer `y` or `n` for the games.
4. The plan appears (`04-plan.png`): the target, its size, the partitions, the seed and a line starting with
   `confirmation ERASE /dev/…`. **Photo 2: the plan, before typing anything else.**
5. Type `ext2-preview` (the root is ext2 without a journal) and Enter.
6. Type the whole confirmation line after the word `confirmation `, exactly as shown, and Enter. It is long: the disk
   name, its identity, its size in bytes and 64 hex digits. A typing mistake cancels with nothing written; run
   `pax-install` again.

The installer stages the live system, then writes the partition table, the EFI partition, the root and Limine,
saying `durable` after each phase. In the QEMU rehearsal onto a 500 GB disk it took 24 s from the confirmation
under KVM and 161 s under full emulation (the root's 7.8 GB of inode tables are written in full); a real SSD over
SATA should be nearer the first. When it says `Installation complete` (`05-complete.png`), **photo 3**, then type `poweroff`.

## 6. The install log

The installer writes its full transcript to the stick as it goes, flushed after every step: the inventory, every
refusal, the plan, each phase's verdict, and the SHA-256 of the first MiB of each partition it wrote. It is on the
stick's EFI partition as `/pax/logs/install-1.txt` (the next install writes `install-2.txt`). From CachyOS:

```sh
sudo mount /dev/sdX1 /mnt && cat /mnt/pax/logs/install-*.txt; sudo umount /mnt
```

Copy the file off for the lane that reads the result. If the screen ever said `install log: stopped: …`, the install
carried on without the log; the photos are then the record. The target also keeps its own short phase log in its
first MiB (bytes 65536 to 131071), which survives even if the stick is lost.

## 7. Boot the installed disk

Remove the stick. Power on, press F8, and pick the target SSD's UEFI entry (the firmware lists it by its model). PAX
boots from the disk with no boot entry of its own: the firmware makes the menu's option for the device and loads
`\EFI\BOOT\BOOTX64.EFI` from its EFI partition. Choose it from the menu rather than waiting: in the QEMU
rehearsal, with the stick gone and nothing chosen, the firmware went to its UEFI shell instead of trying the disk.
The login prompt reads (`06-disk-login.png`):

```text
PAX: log in as root or as the user pax-install made.
login:
```

**Photo 4: this screen.** Log in as `root`, or as the user you made, and run `ls /home` and `cat /etc/pax-release`.
To check the safety rule from the installed system, `pax-install --check` refuses its own disk as `the running root`.
Power off with `reboot -p`.

## 8. Back to CachyOS

Power on, press F8, and pick CachyOS's entry on the Samsung 990 PRO (it is where it always was: PAX never writes
`nvme0n1`, `sda` or `sdb`, and writes no firmware variables). If the firmware has put the new SSD first in its boot
order by itself, set Boot Option #1 back to CachyOS in setup (Boot, Boot Option Priorities), or unplug the SSD.

## If something goes wrong

- The boot stops before `login:`: photograph the last screen, power off, boot CachyOS, and send the photo.
- The installer stops with `pax-install: stopped: …` or `pax-install: staging …`: photograph the screen, then read
  the stick's log (step 6). Nothing is rolled back; the target may be partly written, and that is harmless to every
  other disk. Running the installer again on the same target starts over.
- The installed disk does not boot: photograph the screen, then boot the stick again and run `pax-install --check`;
  the target should now show `PAX's install layout`.
