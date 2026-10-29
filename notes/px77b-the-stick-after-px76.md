# px77b — the smoke stick, rebuilt after px76

Contract: `wolf/sprints/pax/77b-the-stick-after-px76/px77b-the-stick-after-px76.md` (P6, crawl 54), launched
at px76's merge (pax#236). px77a's stick (`6ccfe3fe` plus px76's absent-UART fix) predates px75b (AHCI) and
px76 (UEFI on metal), so kasumi would have shown faults already fixed. This lane rebuilt it from the merge
commit `101e7761` by px77a's recipe, qualified it the same way plus what px76 makes testable, and staged it
beside px77a's on nomad. Notes only: no kernel, program, tool or test change. Footprint: notes.

## Forbidden

No kernel's, firmware's, bootloader's, emulator's or driver's source was read. Read: the contract and px77a's,
RULES §1–§10, PAX's own notes (px77a, px75b, px76) and tree (`tools/mkdistribution`, `tools/mkdisk`,
`tools/qemu-run`, `tools/usb-session`, `tests/mpx6-firmware`, `kernel/screen`, `kernel/power`,
`kernel/user`, `boot/io.S`, `user/elf/reboot.S`), px77a's and px82's hasu scripts (copied under
`/home/mfwolffe/lanes/px77b/`, never moved or edited), and Limine 12.9.1's `CONFIG.md` (its documentation:
what `resolution` and `interface_resolution` do when absent). QEMU 8.2.2, OVMF and Limine were run as black
boxes. kasumi was not touched; no physical disk was opened; nothing was installed; no label, dispatch, merge,
issue or release; no attribution trailers. The maintainer's hasu data was not touched.

## Inputs, verified

- **Base** pax trunk `101e7761cd648accacf9e4fbcb1bede5443a6de7` (px76's merge), a fresh clone on hasu at
  `/home/mfwolffe/lanes/px77b/pax`; `build-inside.sh` asserts the head and a clean tree before building, and
  `tools/mkdistribution` asserts both again after it. The branch `px77b` (this PR) holds notes only.
- **Recipe** px77a's, unchanged but for the lane's directory, the block (A, CPUs 0–5) and the head:
  `build.sh` / `build-inside.sh` (px82's container: `localhost/px75-ubuntu:2`, `--memory 12g`,
  `--pids-limit 16384`, `taskset -c 0-5` inside), `live-payload.py` (px77a's, byte-identical: BOOT.md's
  live-only login entry, every other archive row asserted unchanged), `stick-build.sh` (px77a's
  `stick-smoke-build.sh`), the podman shim (px77a's with 0-5). The copied inputs are px77a's copies of px82's:
  `base-dev.cpio` (`098b918e…`, equal to px77a's), the built programs under `build/inputs`, the cache.
  No pin the image carries moved between `6ccfe3fe` and `101e7761` (`user/clef.pin` moved; clef is opt-in
  and in no image, R-as02-3 A), so the copied program inputs still match their pins.
- **Toolchain** wolf 0.2.35, archive sha256 `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a`;
  Limine 12.9.1, `limine-binary.tar.gz` sha256
  `5cdebc518daa3af30b22c2322ba0dba2e0e2046fa8b087b9e13071b8dbcdcff4`; each read twice
  (`archive-reads.txt`, `limine-read-{1,2}.sha256`). QEMU 8.2.2 (Ubuntu 1:8.2.2+ds-0ubuntu1.18, TCG);
  OVMF_CODE_4M `ad23261d…`, OVMF_VARS_4M `5d2ac383…` (`*/versions.txt`), the same as px77a's.
- **The conf** (R-px77a-1, kept): `boot/limine-usb.conf`, unchanged between `6ccfe3fe` and `101e7761` (px76
  changed `boot/io.S`, `isr.S`, `screen.S` and `start.S`, no conf), the stick's copy sha256
  `d3b4a14b848cbcb69a2ca605bc415d78236e28e7fde869e27a5110f17b38fb39`, the same bytes as on px77a's stick
  (both `usb-check.log`s). px76 changed no boot line.
- **Host** hasu block A under `flock /home/mfwolffe/lanes/hasu-block-A.lock`, shared with px78: every hold
  waited in a printing loop when px78 had it (1m31s before the build, 30 s before boots a and b, 2 min
  before d) and was
  released the moment its build or boot ended (each `RELEASED` line in `build.log` and `*/qualify.log`).

Commits on `px77b`: the prediction (`7a45beff`) first, then the build evidence, the qualification
evidence, the reference screens, the staging records and this note (the PR body lists their shas).

## Prediction

Committed first (`notes/px77b/prediction.txt`, `7a45beff`), before the first build:

| predicted | measured |
|---|---|
| 794,820,608 bytes (758 MiB), as px77a's: the ESP is twice the payload plus 16 MiB rounded up to a MiB, and px77a's left about 126 KB | **right**: 794,820,608. The payload grew 28,992 bytes (kernel 2,449,544 → 2,463,288; live archive 384,873,060 → 384,888,308); 97,236 bytes remain before the next MiB |
| the MSI keyboard types at the login on the first try, its line `xhci 1: ports 8 MSI vector 80 …` | **right** that it types (root and every command, first try, on b, c and d); **wrong** on the line: the stick's controller is `xhci 1` (vector 80), the keyboard's `xhci 2: ports 8 MSI vector 81` |
| about 390 rendered lines before the login at 1280x800 (px77a: 358), a few fewer at 3840x2160 | **right**: 388 (339 scrolls + 49 rows, 160x50 cells) and 385 at 3840x2160 (319 + 66, 240x67 cells at 2x). The kernel's transcript holds 383 lines before `login:` on every machine |
| `poweroff` not found; S5 only if CMD_POWER_OFF is asked | **right**: `pelt: line 104: poweroff: not found` |

Not predicted: Limine, with no `resolution:` in the conf, hands the kernel the firmware's 1280x800 even when
the display offers 3840x2160 (machine b), so a mode other than OVMF's default needed Limine's editor for one
boot (machine c); QEMU 8.2's gdb stub reports a breakpoint only after the client's own resume, which stalled
the first S5 attempt (b-run1); an indented key typed in Limine's editor is drawn red and ignored (c-run1).

## Evidence index

Everything under `notes/px77b/`; the hasu working tree is `/home/mfwolffe/lanes/px77b/`.

### The release pair and the stick

`build.log`: block A acquired 21:47:04Z, `tools/mkdistribution` 21:47:04–21:52:40Z (5m36s, the kernel and
the installer, disk tools, Limine and probe built from the checkout; the copied programs checked against
their inventories), the live payload (`live-payload.txt`: only `etc/pax-files.sha256`, `etc/pax-live-login`,
`etc/pax-run`, `root` differ from the verified release archive), then on the host `tests/usb-tools` (14
tests) and `tests/usb-linux-fetch` (6), `tools/mkdisk --usb`, `tools/check-usb` with the five expectations
`tests/distribution-usb` uses (`usb-check.log`), a second `mkdisk --usb` byte-identical by `cmp` (`PASS second
stick build byte-identical`), and both negative checks red by name (`usb-efi-red.log`: `required boot file
missing: /EFI/BOOT/BOOTX64.EFI`; `usb-mbr-red.log`: `protective MBR must cover the disk`). Released 21:53:15Z.

| | px77a's stick | this stick |
|---|---|---|
| commit | `f8a3292b` (6ccfe3fe + f1f8137b) | `101e7761` (trunk) |
| image | 794,820,608 bytes, `a792de5e…110d` | 794,820,608 bytes, **`598d34396c2c8c05d70a92037dc5dc041fd346b5d5d14312f6db6feaabf7378e`** |
| `/boot/pax` | 2,449,544, `67af5142…` | 2,463,288, `ba8fda6f9c11e14107827ef5f43c2213370b512f517fd497b77b4fed4df3b98e` |
| `/boot/initramfs.cpio` | 384,873,060, `79865121…` | 384,888,308, `08a0c1dd2d7dff4755d834b71bb641628c76a1e52256dbda55242430a5e32b52` |
| conf, BOOTX64.EFI, limine-bios.sys | `d3b4a14b…`, `90a9a6a5…`, `96867c2b…` | the same three |
| release banner | `f8a3292b` | `PAX: kernel 101e7761…; release 98bbabc6` |

### Qualify: four machines

`qualify.py` is px77a's `qualify-smoke.py` with the machines below; `qualify.sh` holds block A for one boot.
Each boot makes two fully written 2 GiB files of known content (NVMe and SATA), boots the exact image
read-only as `usb-storage`, with `-serial none`, fresh OVMF variables, TCG, takes Limine's default, logs in
as root by typing through the USB keyboard (QMP key events), and reads its transcript from PAX's own memory
(the screen's cells, and px76's 64 KiB `pax_serial_log`), never from a UART. Exact argv: `*/command.json`.

- **a, px77a's machine** (its argv but for paths and the NVMe serial: q35, 2 GiB, `qemu-xhci`, the PIT
  present). `xhci 1: ports 8 INTx 11 …` and `xhci 2: … INTx 11` (QEMU 8.2's `qemu-xhci` offers no MSI),
  `clock: HPET 10000000 fs/tick, checked against the PM timer`, `timer: LAPIC calibrated by HPET divide16
  62448136 Hz … PIT IRQ masked`, `ahci0: 8086:2922 at 00:1f.2 port 0: sda model "QEMU HARDDISK" serial
  "QM00001" …`. Ends `reboot`: QEMU exit 0 (`-no-reboot`). Screens `a/*.png` for side-by-side with px77a's.
- **b, kasumi's shape** (px76's F8 with px77a's disks): `q35,pit=off`, 8 GiB, both xHCIs
  `nec-usb-xhci,msi=on,msix=off` (R-px76-5), `opt/ovmf/X-PciMmio64Mb=65536` (`--high-bar`), `-device
  VGA,vgamem_mb=64,xres=3840,yres=2160` (`--display-mode`), the SATA disk `serial=px77b-sata`. The lines:
  `xhci 1: BAR0 0x0000001000008000`, `xhci 1: ports 8 MSI vector 80 …`, `xhci 2: BAR0 0x0000001000004000`,
  `xhci 2: ports 8 MSI vector 81 …`, `xhci: keyboard usb2-5 speed 3 boot report 8`, `xhci: usb1-1
  SuperSpeed enumerated, not driven` (the stick), `clock: HPET …`, `timer: LAPIC calibrated by HPET …`,
  `console: com1 absent, …`, `ahci0: … port 0: sda model "QEMU HARDDISK" serial "px77b-sata" …`, `screen:
  1280x800 …` (b/03-login.transcript.log). The NEC xHCI keeps its INTx pin (QEMU cannot drop a PCI
  device's legacy line as kasumi's reads 255); PAX takes MSI wherever it is offered, which the `MSI vector`
  lines show. Ends at S5 (below).
- **c, the GOP at another mode**: b's machine; at the menu the harness pressed E, added the line
  `resolution: 3840x2160` after `module_path:` (`qualify-only-limine-editor.png`) and pressed F10, for that
  boot only; the image is unchanged. `screen: 3840x2160 32 bpp pitch 15360 … font spleen 8x16 at 2x,
  240x67 cells`; the session typed and listed as b's. Ends `reboot`: QEMU exit 0.
- **d, the end the checklist asks for**: b's machine, `reboot -h` with nothing changed: `user: reboot pid
  11 reboot(2): the volumes written and marked clean; halting`, `block: nvme0n1: 1 reads (1 sectors), 0
  writes (0 sectors), 0 flushes …`, `block: sda: 1 reads (1 sectors), 0 writes (0 sectors), 0 flushes …`,
  `nvme0: … shut down`, `halt`; the screen unchanged 5 s later, the machine running (halted CPU); QMP
  `quit` as the power button (d/07-halt.txt, `07-halt.png`).

On every machine `uname -a` exits 1 (`uname: -s: raw kernel field unavailable (wolf-lang#907)`, known, as
on px77a's stick), `cat /etc/pax-release` and `ls /dev` exit 0 (`ls /dev` now lists `sda` beside
`nvme0n1`), and `pax-install --inventory` exits 0 with both disks:

    /dev/nvme0n1 bytes=2147483648 sector=512 readonly=false mounted=false root=false
      identity=259:0-seq1
      model=QEMU NVMe Ctrl serial=px77b-nvme
    /dev/sda bytes=2147483648 sector=512 readonly=false mounted=false root=false
      identity=8:0-seq2
      model=QEMU HARDDISK serial=px77b-sata

**S5 (b).** The image has no command that asks for a power-off: `poweroff` gives `pelt: line 104:
poweroff: not found`, and PAX's `reboot` (`user/elf/reboot.S`) asks reboot(2) for RESTART, or HALT given any
argument, never POWER_OFF (`0x4321fedc`). So b typed `reboot -h`; at `user.the_end` (a breakpoint; `RIP`
read back) `end_cmd` held `0xcdef0123` (CMD_HALT, the typed request), the debugger wrote CMD_POWER_OFF
there and read it back, and the stick's own kernel went on: the end summary as in d, then `poweroff: ACPI S5
types 0/0`, the screen saved at the first `pax_outw` (the PM1a write, `06-poweroff.png`), and QEMU exited 0
at S5. That witnesses the kernel's S5 path on the stick, on kasumi's shape, not a path the keyboard has.

**Boot lines before the login** (`*/boot-line-count.txt`): the kernel's transcript holds 383 newline-ended
lines before `login:` on all four machines; rendered, 388 at 1280x800 (339 scrolls + 49 rows) against
px77a's 358, and 385 at 3840x2160 (319 + 66). px76's early screen replays 103 bytes at the framebuffer's
attach, inside the first screen, so no scroll is counted twice.

**Harness attempts kept** (no fault of the image): `b-run1/` — the first S5 attempt waited for the gdb
stub's stop reply after a QMP `cont`; QEMU 8.2's stub sends one only after the client's own resume, so the
breakpoint at `user.the_end` was reached silently (`failure.png` shows `$ reboot -h` and nothing after) and
the wait timed out; the harness now polls QMP's run state for `debug` (`qualify-run1.py` is the first
version). `c-run1/` — the editor line typed indented was drawn red and ignored, the screen stayed 1280x800
and the harness's own check stopped it; the key is now typed at the line's start. Both kept their disks
unchanged (`*-run1/images-at-prune.sha256`, the same digests as every boot).

### The no-write witness

sha256 over every byte of each writable image, before QEMU starts and after it ends; `before.json` and
`after.json` per machine. Every boot made the same known content, so the digests repeat:

| boot | NVMe 2 GiB before = after | SATA 2 GiB before = after |
|---|---|---|
| a, b-run1, b, c-run1, c, d | `1b3abf6fd5903f677d6b64755fc4e6b565d49ad8cfdc4da8c9b1b55dd0f41547` | `4858d95e127a15b083e35d03c1b39ea88da9008ef3875f9d054e2eef5eb209aa` |

PAX's own end summary agrees (b and d): each disk one read of one sector, 0 writes, 0 flushes. Both disks
appear at boot: `nvme0: 1b36:0010 at 00:04.0, NVMe 1.4.0 "QEMU NVMe Ctrl" serial "px77b-nvme" firmware
"8.2.2"; …` with `block: nvme0n1: 4194304 sectors …, 259:0, read-write, flush`, and (new since px77a's stick)
`ahci0: 8086:2922 at 00:1f.2, CAP.NP=5 CAP.NCS=31 S64A=1 PI=0x000000000000003f BOH=0; ports idled; one slot,
polled`, `ahci0: … port 0: sda model "QEMU HARDDISK" serial "px77b-sata" firmware "2.5+"; 2147483648 bytes
(2 GB); logical 512 physical 512 bytes`, `block: sda: 4194304 sectors …, 8:0, read-write, flush`.

### Staged on nomad

`df -h ~` first: 68 GiB available. `~/pax-smoke/pax-stick-101e7761.img`, 794,820,608 bytes, sha256
`598d34396c2c8c05d70a92037dc5dc041fd346b5d5d14312f6db6feaabf7378e`: read twice on hasu after the build
(`image-hasu-build-read-{1,2}.sha256`), twice on hasu at staging (`image-hasu-read-{1,2}.sha256`), twice on
nomad after the copy (`image-nomad-read-{1,2}.sha256`, `shasum -a 256`); all six agree. The reference PNGs
are in `~/pax-smoke/101e7761/` (the same bytes as `notes/px77b/*.png`). `~/pax-smoke/README.txt` is this
stick's (`staged-README.txt`); px77a's README.txt was first copied unchanged to
`~/pax-smoke/README-6ccfe3fe+f1f8137b.txt` (both sha256 `cf7f5570…`). px77a's image
(`pax-stick-6ccfe3fe+f1f8137b.img`, `a792de5e…`, read again) and its PNGs stay where they were.

### What changed since px77a's stick

- Stock trunk: px76's absent-UART fix is merged; no cherry-pick.
- px76: the firmware's machine on screen first (firmware, memory map, every ACPI table, the clock and the
  calibrated tick); a tick that needs no PIT; kasumi's xHCI on MSI (the keyboard is expected to type); BARs
  above 4 GiB; any GOP mode, 2x glyphs above 2560 wide; reboot by the FADT reset register, then 0xCF9, then a
  triple fault; S5 in the kernel; x2APIC by MSR.
- px75b: the SATA disks driven read-only, named at boot and in the inventory with model and serial.
- px84: the installer and disk tools past 2 TiB (unused by a smoke boot).
- The same conf, the same live payload, the same size.

### The photo checklist (updated)

`photo-checklist.txt`, also in `~/pax-smoke/README.txt`:

0. A phone **video** from the menu to the login: with no serial port the screen is the only record, and
   about 380 lines scroll past; the firmware, ACPI, clock, xHCI and disk lines are gone by the login.
1. The Limine menu before its countdown ends (`01-limine-menu.png`, as px77a's). Let the default boot; do not
   press E.
2. The last boot screen and the video's early lines (`02-last-boot-line.png`). Expected on kasumi: its board
   vendor on `firmware:`, its own ACPI tables, `clock: HPET … checked against the PM timer`, `timer: LAPIC
   calibrated by HPET`, perhaps `apic: x2APIC mode` (R-px76-7's first witness), `screen:` at the mode its
   firmware left, `console: com1 absent`, each xHCI's BAR0 above 4 GiB and `MSI vector 8N`, `ahci0:
   8086:43d2 at 00:17.0` and `ahci1: 1b21:0612 at 6e:00.0`, `sda` the Samsung 870 EVO 4TB, `sdb` the
   SanDisk, `nvme0: 144d:a80c`. Photograph any `refused`, `INTx`, `timeout`, `FAIL` or `PANIC`, a
   controller with no line (RST/RAID mode prints none), or the whole screen where the boot stops.
3. The login prompt before typing (`03-login.png`; `03-login-3840x2160.png` at a 4K mode).
4. `root`, Enter. **New:** the keyboard is expected to work. If not, photograph and note the USB port; the
   video says which failure: no `xhci: keyboard` line (never found) or the line and no typing (interrupts).
5. `uname -a` (exits 1, wolf-lang#907), `cat /etc/pax-release`, `ls /dev` (**new:** `sda`, `sdb`), photograph
   (`04-after-commands.png`); `pax-install --inventory`, photograph (`05-disk-listing.png`): **new:** each
   disk's model and serial, `mounted=false root=false`.
6. The end: no `poweroff` on the image. `reboot -h`; photograph the end summary (`07-halt.png`: `0 writes`
   per disk, the on-metal no-write witness, then `halt`), then hold the power button. `reboot` alone resets
   at once and loses the summary. Any `block:` line with writes above 0: photograph it and stop.

### Follow-ons (for the orchestrator to file or drop)

- pax: a power-off a live session can ask for. The kernel's S5 is witnessed (b), but no program asks
  reboot(2) for POWER_OFF: `user/elf/reboot.S` asks RESTART, or HALT given any argument. A `poweroff` (or
  `reboot -p`) would let the maintainer end a metal session at S5.
- pax: the stick's Limine keeps the firmware's GOP mode (measured: 1280x800 under OVMF with 3840x2160
  offered). kasumi's photo will show the mode its firmware leaves; a fixed `resolution:` in
  `boot/limine-usb.conf` would be a ruling, not taken here.
- Pre-existing, unchanged (px77a's): README line 347 says merging needs a green `tier full` or `tier all`
  run and omits the notes and module footprints (ruling #104).

## Done-when

- [x] Prediction committed before the first build (`7a45beff`).
- [x] The release pair and the stick at `101e7761` by px77a's recipe, copied, never moved or edited; the same
  conf (px76 changed no boot line); a second build byte-identical (`cmp`); the five ESP checks and both
  negative checks.
- [x] Qualified under OVMF shaped like kasumi: the keyboard on MSI-only xHCIs, typing first try; the GOP at
  3840x2160 (2x, 240x67) by Limine's editor for one boot; S5 reached by the stick's kernel (QEMU exit 0),
  the power-off request written by a debugger because no program asks for it; the AHCI disk listed with model
  and serial; seven reference PNGs plus two at 3840x2160.
- [x] The no-write witness on both images in every boot: identical.
- [x] Staged on nomad with README.txt, px77a's image kept; six matching digest reads.
- [x] The photo checklist updated.
- [x] README read against this pass: current (a notes-only pass; "real-machine boots are not tested here"
  still holds).
- [ ] The orchestrator reviews the audit; no label, no CI wait (notes).

Issues filed or closed: none. Owed to file: the two pax follow-ons above.
