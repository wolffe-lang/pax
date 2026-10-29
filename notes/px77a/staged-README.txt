PAX smoke stick — trunk plus one unmerged UART fix

Image: pax-stick-6ccfe3fe+f1f8137b.img
Size: 794820608 bytes (758 MiB)
SHA256: a792de5e26af579fd8931df245d314d0389f6eb3f48bd0ef0bd7ebd36139110d
Base: 6ccfe3febe548df3d30fd34ed8f517dabfbfa875
Only source change: px76 f1f8137b10eafd08bb51ee02ab7e78d0b172f68a, cherry-picked cleanly
Actual local build commit: f8a3292bb3c2482a4632c407116ff5ce937387eb (px77a-smoke)
Conf: boot/limine-usb.conf, unchanged. UEFI menu, default entry, root without a password.
Payload: complete release initramfs plus BOOT.md's existing live-only login entry; no disk root or auto-install.

This is NOT stock trunk. Stock trunk hangs with no COM1, at the syscall setup line.
Only the absent-UART fix was added; the remaining px76 metal work is not included.
In particular, kasumi's xHCI interrupt route is still expected not to work.
This is for the coordinated first-look smoke boot, NOT installation on kasumi.
Never run the installer's write flow or a formatter on kasumi's existing disks.

Qualified on hasu: QEMU 8.2.2 TCG, q35, fresh OVMF 4M UEFI variables,
-serial none, USB storage boot, USB keyboard, writable 2 GiB NVMe and SATA files.
Root login and all four requested commands were typed through the USB keyboard.
uname -a exits 1: "uname: -s: raw kernel field unavailable (wolf-lang#907)".
cat /etc/pax-release, ls /dev and pax-install --inventory exit 0.
NVMe appears as nvme0n1; AHCI/SATA is not driven by this kernel.
The synthetic ttyS0 node does not mean a UART exists.
reboot ended QEMU with exit 0. Both whole-disk hashes stayed identical.
NVMe before/after: a763b026fd1ff5b666ca4a12d2bea6e4f22cd4d514641b1a3ac4b3c5a5f77cb1
SATA before/after: ad21027284e3d9a4a96bf222507a040a5ef4610253d42f0d465994e8a9df4e8f
Before/after hashes were recorded by the qualification harness; independent sha256sum agrees.
Boot count: 358 rendered lines before login (309 scrolls + 49 visible rows), including wrapping.

All four image digest reads match: twice on hasu, twice on nomad.
The repeat raw image build was byte-identical by cmp; all five ESP boot-file expectations passed.
Reference PNGs are actual QEMU screendumps, converted losslessly from PPM.

Photo checklist
1. Photograph the Limine menu before its countdown ends. Reference 01-limine-menu.png shows Limine 12.9.1 (x86-64, UEFI), with "PAX live (root, no password)" selected. Let the default boot; do not edit the kernel line.
2. Photograph the last visible boot text, especially the final complete line; if it stalls, photograph that screen without trying to install. Reference 02-last-boot-line.png shows the NVMe/block and USB-keyboard lines, the f8a3292b kernel banner, and the first live-login process being started. The separate trunk-no-serial-stall.png shows the old UART hang ending at "user: syscall star ...".
3. Photograph the login prompt before typing. Reference 03-login.png shows "PAX live medium: log in as root (no password)." and "login:". On kasumi the USB keyboard is still expected not to work until px76's interrupt-route work lands; a dead keyboard is evidence, not a reason to change disks or firmware settings.
4. Only if typing works, enter root, then run uname -a, cat /etc/pax-release, ls /dev, and pax-install --inventory, in that order. Photograph the resulting screen before reboot. Reference 04-after-commands.png shows the release identities, /dev/nvme0n1 and the read-only inventory; uname -a currently reports wolf-lang#907 and exits 1. Run no installer write flow and no formatter. End with reboot if typing works; otherwise return control to the boot-window coordinator for the machine's recovery.
