# px77a — the smoke stick

_Materialised from the body of pax#226 at the merge (`a39732a4`)._

## Forbidden

No kernel or program change is proposed by this PR. No third-party kernel, bootloader, firmware or driver implementation source was read. No physical disk was opened, no package installed, no kasumi connection made, no label or workflow dispatched. Planning and home configuration were untouched. Sources consulted: the lane contract and P6/rules, PAX's own px71/px73/px74 notes, builders, console/framebuffer code and README; px82's hasu scripts were read and copied, never changed.

The full five-section lane note is this PR body for materialization as `notes/px77a-the-smoke-stick.md`; the wrapper does not write report Markdown files. Reference PNGs and evidence are under `notes/px77a/`.

## Inputs, verified

**The staged smoke stick is trunk plus ONE UNMERGED FIX, not stock trunk.** Stock `6ccfe3febe548df3d30fd34ed8f517dabfbfa875` hung under OVMF with `-serial none`, before console initialization completed. `trunk-no-serial-stall.png` ends at `user: syscall star ...`; it never reached login. Its raw image is 794,820,608 bytes, SHA256 `930471709a7ad02f3c9908d58c64aa464277be63177aade2c8531597322fffff`, retained on hasu only, not staged on nomad.

Following the coordinator's pre-decided contingency, px76 commit `f1f8137b10eafd08bb51ee02ab7e78d0b172f68a` was cherry-picked cleanly and alone onto local `px77a-smoke`, producing **`f8a3292bb3c2482a4632c407116ff5ce937387eb`**. The only changed source paths are `kernel/serial/serial.lu` and `kernel/console/console.lu`; no `def4583d` or other px76 change is included. Absent COM1 reads 0xff; trunk's receive drain never finishes. This fix detects absence, bounds the drain and unmasks only present console sources. The smoke source branch is local, separate from this notes-only PR.

Fresh hasu clone `/home/mfwolffe/lanes/px77a/pax`; px82's verified payload inputs/cache and digest-pinned base archive were copied into the lane. `tools/mkdistribution` rebuilt the release kernel, installer and disk tools from each exact checkout and checked the copied program bytes against their inventories. The live archive then applies BOOT.md's existing `/etc/pax-live-login` entry and `/etc/pax-run`, adds `/root`, and updates the file inventory; every other archive row is asserted unchanged. No disk-root configuration or auto-install is added. The built release kernel is 2,449,544 bytes; live `release.cpio` is 384,873,060 bytes.

Wolf 0.2.35 archive SHA256 `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a` and Limine 12.9.1 binary archive SHA256 `5cdebc518daa3af30b22c2322ba0dba2e0e2046fa8b087b9e13071b8dbcdcff4` were independently read twice on hasu. QEMU 8.2.2/TCG; OVMF_CODE_4M `ad23261d43116abc3747d59a7837fbf578c9586a8993f4eeba064cd07eccb083`, initial OVMF_VARS_4M `5d2ac383371b408398accee7ec27c8c09ea5b74a0de0ceea6513388b15be5d1e`. Build/boot container `localhost/px75-ubuntu:2`, memory ceiling 12 GiB, affinity 6–11 inside the container, block-B flock. The lock stayed held across the trunk failure and second build; released at **2026-10-29 02:18:08Z**, immediately after the smoke witness finished.

- `a86fdca6` — record predictions before the first build.
- `a39732a4` — retain the build/qualify evidence, four reference screens and photo checklist.

## Prediction

Committed first in `notes/px77a/prediction.txt`: 512 MiB stick, 20-minute pair/stick build, no-serial login, 35 boot lines, unchanged disks.

Measured: **758 MiB / 794,820,608 bytes**. Trunk pair built 01:58:44–02:03:44Z (5m00s); second pair 02:09:39–02:16:28Z (6m49s), with each stick/repeat/negative-check phase about another minute. These timings reuse copied, verified program inputs, not cold builds of every project. Trunk no-serial login prediction was wrong; trunk plus the one UART fix reaches it. The screen records **358 rendered boot lines before `login:` = 309 scrolls + 49 visible rows**, including wrapped rows; this is explicitly a framebuffer count, not 358 UART/newline records. Both disks stayed unchanged.

**R-px77a-1 recommendation, implemented, not decided:** use unchanged `boot/limine-usb.conf`. It shows the three-second Limine menu and boots the live-root entry without a typed kernel line. `limine-initramfs-quiet.conf` used by `tests/distribution-usb` skips the menu; neither conf alone creates the login, so the documented live-only archive entry is supplied explicitly.

## Evidence index

### Stick and staging

`tools/mkdisk --usb`, followed by `tools/check-usb` with all five `tests/distribution-usb` expectations: exact kernel, live archive, BOOTX64.EFI, limine-bios.sys and chosen conf. Second raw build is byte-identical by `cmp`. Host USB tool/fetch tests pass (14 and 6). Local negative checks reject both missing EFI file and short protective-MBR coverage by name in `usb-efi-red.log` and `usb-mbr-red.log`. No CI dispatch was used.

Staged on nomad, after `df -h ~` showed 77 GiB available:

`/Users/mfwolffe/pax-smoke/pax-stick-6ccfe3fe+f1f8137b.img`

**794,820,608 bytes; SHA256 `a792de5e26af579fd8931df245d314d0389f6eb3f48bd0ef0bd7ebd36139110d`.** Two `sha256sum` reads on hasu and two `shasum -a 256` reads on nomad all match (`image-{hasu,nomad}-read-{1,2}.sha256`). Four PNGs and `README.txt` are beside the image. The README identifies the unmerged fix and says this is a coordinated smoke boot, not an installation image for kasumi's existing disks.

### Qualify transcript

Exact argv: `command.json`. q35, fresh OVMF UEFI variable store, no CSM, **`-serial none`**, no NIC; exact raw stick read-only as `usb-storage` on `qemu-xhci`; `usb-kbd` on another xHCI controller, matching px74's launcher topology; one writable 2 GiB NVMe image; one writable 2 GiB `ide-hd` on q35's ICH9 AHCI bus. Both disks are fully materialized known, distinct byte patterns, not read-only or snapshot drives.

The default Limine entry boots; root is typed without a password through QMP USB-keyboard events. The serial-free transcript is read from PAX's own exported framebuffer text grid while paused, never from a hidden UART. A hardware breakpoint at first user entry captures the last boot screen; the other screens are QEMU `screendump` captures, losslessly converted from PPM to PNG.

- `uname -a` — executed, exits **1**: `uname: -s: raw kernel field unavailable (wolf-lang#907)`; no fix attempted.
- `cat /etc/pax-release` — exits 0; reports kernel `f8a3292b...`, ELF SHA256 `67af51425432e8e948336bc71b4ad93b495b67d2c0f98609f0cc3aa2c06e26ab`, release-file SHA256 `c7e92424ff5401830cb864dd911e2e6bc013dc5cf6d38af7c71033ebeb06acc7` (the banner prints its eight-digit prefix).
- `ls /dev` — exits 0, shows `nvme0n1`; synthetic `ttyS0` remains despite the absent UART.
- `pax-install --inventory` — read-only path, exits 0: `/dev/nvme0n1 bytes=2147483648 sector=512 readonly=false mounted=false root=false`, identity `259:0-seq1`, model/serial unknown.
- `reboot` — ends QEMU with **exit 0** at 02:18:05Z; no installer write flow was entered.

NVMe boot line: `nvme0: 1b36:0010 at 00:04.0, NVMe 1.4.0 "QEMU NVMe Ctrl" serial "px77a-nvme" firmware "8.2.2"`; namespace 1 is 4,194,304 512-byte blocks, followed by `block: nvme0n1: 4194304 sectors (2147483648 bytes), 259:0, read-write, flush`. AHCI/SATA is attached but not driven: no SATA boot line or node/inventory row, as expected before px75b. The console's inherited diagnostic still prints `com1 irq 4`; that string does not override `-serial none` or the absence detection.

The outer wrapper's final `rc=1` retains the earlier trunk failure; **smoke `result.json` explicitly records `exit: 0`, `no_write: true`**, and `build.log` shows the successful commands/reboot and lock release. It is not represented as a wholly green trunk attempt.

### No-write witness

Whole-file SHA256 before and after the smoke boot (also unchanged for the failed trunk attempt):

| writable disk | before | after |
|---|---|---|
| NVMe, 2 GiB | `a763b026fd1ff5b666ca4a12d2bea6e4f22cd4d514641b1a3ac4b3c5a5f77cb1` | `a763b026fd1ff5b666ca4a12d2bea6e4f22cd4d514641b1a3ac4b3c5a5f77cb1` |
| SATA, 2 GiB | `ad21027284e3d9a4a96bf222507a040a5ef4610253d42f0d465994e8a9df4e8f` | `ad21027284e3d9a4a96bf222507a040a5ef4610253d42f0d465994e8a9df4e8f` |

The harness records these with SHA256 over every byte before launch and after QEMU closes. Independent `sha256sum` afterward equals both, and `sha256sum -c before.sha256` passes. `before.json`, `after.json`, `before.sha256`, `after.sha256`, `result.json` retain the witness. Disk images stay on hasu at `/home/mfwolffe/lanes/px77a/qualify-smoke/`; no physical target was used. This proves this tested boot/session leaves the two images unchanged, not that every possible PAX/installer session is harmless.

### Photo checklist

1. Photograph the Limine menu before its countdown ends. Reference 01-limine-menu.png shows Limine 12.9.1 (x86-64, UEFI), with "PAX live (root, no password)" selected. Let the default boot; do not edit the kernel line.
2. Photograph the last visible boot text, especially the final complete line; if it stalls, photograph that screen without trying to install. Reference 02-last-boot-line.png shows the NVMe/block and USB-keyboard lines, the f8a3292b kernel banner, and the first live-login process being started. The separate trunk-no-serial-stall.png shows the old UART hang ending at "user: syscall star ...".
3. Photograph the login prompt before typing. Reference 03-login.png shows "PAX live medium: log in as root (no password)." and "login:". On kasumi the USB keyboard is still expected not to work until px76's interrupt-route work lands; a dead keyboard is evidence, not a reason to change disks or firmware settings.
4. Only if typing works, enter root, then run uname -a, cat /etc/pax-release, ls /dev, and pax-install --inventory, in that order. Photograph the resulting screen before reboot. Reference 04-after-commands.png shows the release identities, /dev/nvme0n1 and the read-only inventory; uname -a currently reports wolf-lang#907 and exits 1. Run no installer write flow and no formatter. End with reboot if typing works; otherwise return control to the boot-window coordinator for the machine's recovery.

## Done-when

- [x] Preserve failed stock-trunk boot and image digest; cleanly isolate the coordinator-authorized single fix.
- [x] Fresh exact-source release pair; documented live-login payload, reproducible raw stick and all five ESP-file checks.
- [x] No-serial OVMF, default menu entry, USB root login, four requested commands and reboot; uname's known failure named, not hidden.
- [x] Both writable disks unchanged; four real reference PNGs, compact transcript and executable recipe retained.
- [x] Stage image, README and PNGs on nomad; four matching image digest reads; release hasu block B.
- [x] Read README against this notes-only pass; no newly moved statement. Pre-existing cleanup to file: README lines 315–316 say every merge needs full/all and omit the standing notes/module footprint exceptions; not changed here.
- [ ] Orchestrator materializes this body as `notes/px77a-the-smoke-stick.md`, reviews the audit and CI once available; no lane CI wait, label or merge.

Issues filed/closed: none. Existing wolf-lang#907 is observed, not newly filed. No metal readiness, working kasumi keyboard, AHCI support, Secure Boot support or safe hardware installation is claimed.

