# px87 — the console on metal: no framebuffer reads, a quiet live session, poweroff, the non-root answers, the kernel's name

Contract: `wolf/sprints/pax/87-the-console-on-metal/px87-the-console-on-metal.md` (P6, crawl 54, batch B, 2026-11-02),
under `sprints/the-lane-rules-1031.md` and its 11-01 and 11-02 additions. Base pax trunk `3e28a8bc`. PAX runs installed
on kasumi (M-PX6); on its RTX 4090's GOP framebuffer the console scrolled by copying the framebuffer onto itself, about
23 MB of uncached reads a line (pax#253). This lane makes the console write the framebuffer only, quiets the live
session (pax#246), adds `poweroff` (pax#243), answers a user's `reboot` and `pax-install --check` by name (pax#265,
pax#266), has the kernel name its own commit and digest (pax#176), and stages a stick with the steps for a metal
session. Footprint: cross-cutting (`boot/start.S` and `tools/build-kernel` are FULL paths: the PR's run is tier all).

**Commit names.** The lane was rebased onto trunk `5da8daaf` after its runs (R-px87-14, §4.10). Every commit named
in this note is the rebased one, except where the text says what ran before the rebase (`<old>`, rebased `<new>`)
and inside quoted log lines and the INSTALL.txt copy, which keep the names they printed. Each pre-rebase commit and
its rebased commit are the same patch and the same tree but for trunk's `notes/pm00*`, checked commit by commit
(`notes/px87/rebase/map.sh`, its table `notes/px87/rebase/map.txt`).

## 1. Forbidden, and what was read

No kernel's, firmware's, bootloader's, emulator's, debugger's or driver's source was read: not Linux's, not QEMU's
(its gdb stub, QMP and devices were run as a black box), not Limine's, not OVMF's, not busybox's or systemd's (busybox
was run as a binary), not gdb's. Written from the GDB manual's Remote Protocol chapter, FIPS 180-4, the Limine protocol
(PROTOCOL.md at `3a0526b7`, copied from px15's and px19's lane directories, sha256 `9e69fdd0…`, never moved), the
System V gABI's ELF-64 layout, the Intel SDM vol. 2 (RDTSC, REP MOVS), reboot(2), reboot(8), errno(3) and open(2); each
in `docs/SOURCES.md` (px87's section). PAX's own tree and notes were read: the contract, px76's, px77d's, px82's, px85's
and px86's notes, the crawl's M-PX6 entry (2026-11-01 00:02), pax#253, #246, #243, #265, #266 and #176 whole.

kasumi's disks were never written or read by this lane: every boot ran under QEMU in a container, the stick's own
allow-list names no disk. kasumi's `ggml-rpc-server` was not touched. hasu was used only to copy px86's stick inputs
(read-only, by `tar` through nomad); nothing ran on its blocks. On nomad only `~/lanes/px87/` and one new stick and
its INSTALL.txt block under `~/pax-smoke/` were written. Nothing was installed. No label, dispatch, merge, issue or
release; no attribution trailers.

## 2. Inputs, verified

- **Base** pax trunk `3e28a8bc` (px85's notes head, trunk at launch); rebased onto `5da8daaf` after the runs (§4.10). Branch `px87`, the Mac clone
  `~/lanes/px87/pax` for git and `gh` only (no build on the Mac), the branch asserted before every commit. On
  kasumi a clone under `/home/mfwolffe/lanes/px87/pax` and a worktree per tested commit (`w/<sha8>`, made by
  `notes/px87/kasumi/wt.sh`, refused if dirty or not at the sha): every build ran from a commit.
- **Toolchain** wolf 0.2.35 (`kernel/wolf.pin`, archive `4cc4045b…`), Limine 12.9.1 (`5cdebc51…`), copied (never
  moved) from px74's kasumi cache; each archive's sha256 read twice in the stick chain (`archive-reads.txt`,
  `limine-reads.txt`, all equal to the pins) and `tools/fetch-wolf`'s own check on every run (`wolf 0.2.35
  (wolfgang, pin cf0c13d)`). The stick's inputs (`base-dev.cpio` `098b918e…`, px77c's built inputs, `lope-local`
  at the pin `e6f623c7`, px86's `live-payload.py`) copied read-only from hasu's `/home/mfwolffe/lanes/px86/`.
- **Host** kasumi CPUs 0-3 under `kasumi-cores-0-3.lock`, one hold per run or per chain (`notes/px87/kasumi/ctr.sh`,
  `hostchain.sh`), never idle; the wait a single `flock -w 21600` with a line every 4 minutes. Rootless podman,
  `localhost/px76-ubuntu` (`e594d38c`: QEMU 8.2.2 `1:8.2.2+ds-0ubuntu1.18`, Ubuntu's OVMF, clang, lld 18, gdisk,
  dosfstools, mtools, xorriso), `--memory 12g`, `taskset -c 0-3` inside. `tools/mkdisk`'s disk tools ran on the host
  through podman (`PAX_ENGINE=podman`, `tools/e2fs`'s pinned `ubuntu@sha256:534baea6…`, present). Every long job
  detached with a pid file, a log and an exit marker (`launch.sh`).
- **Found at launch: kasumi's firmware has VT-x off.** CachyOS's kernel logged `x86/cpu: VMX (outside TXT) disabled
  by BIOS` (boot of 2026-11-02 12:29 EST) and there is no `/dev/kvm`, so every QEMU run here was TCG, as CI's are.
  The contract planned KVM; nothing here needed it (V7 needs TCG). Re-enabling VT-x is an optional step of the metal
  session (§5.5).
- **The Linux side of `mpx3-console`** (`tools/linux-tty --pid1`, a pid namespace) needs `CAP_SYS_ADMIN`, which
  rootless podman drops by default: as the container's root with `--cap-add SYS_ADMIN` (inside the rootless user
  namespace; still the host's `mfwolffe`, unprivileged on the host) every T row ran (`console-caps`); without it
  T2 and T5 compare against nothing (`console-green`).
- **The measurement of Linux's message** (pax#265): `notes/px87/linux/measure-reboot.sh` as uid 1000 in a rootless
  container, its output `notes/px87/linux/reboot-as-user.log` (§4.3).

## 3. Prediction, scored

`notes/px87/prediction.txt`, committed first (`ac0d327f`, 18:05Z), before any change and before any guest ran:

| predicted | found |
|---|---|
| QEMU 8.2.2's gdb stub takes one `Z3` over the whole framebuffer (about 4 MB) under TCG | **right**: 4,096,000 bytes at 1280x800, `OK`; it stops after each guest load from it; the stop reply names the watchpoint's first byte, not the byte read, so V7 reports `%rsi` inside `pax_fb_copy` |
| V7 red at base by name: at least the cap's reads in the first scroll, the first by `pax_fb_copy` one band above the first scrolled band | **right**: `64+ framebuffer reads in 393 scrolls, the first by pax_fb_copy+0x7 (rsi …fd014008, framebuffer + 0x14008) called from _Wscreen.scroll` (BIOS and UEFI; 0x14000 is one band, 16 rows of 5120 bytes) |
| at the head 0 reads in every scroll; the `fbread` boot red the way the base was | **right** on all four legs: `0 reads of the framebuffer's 4096000 bytes in 393 scrolls` (394 on UEFI), the control `reads=8+`, the first by `pax_fb_copy` called from `_Wscreen.scroll_readback` |
| V2, V5, V6 pixel-identical | **right**, every leg (8000 of 8000 cells) |
| V3's scrolled-line cost lower at the head under TCG | **wrong first, then right**: base 0.98 ms native; the first fix (`9d6d78b5`) 1.56 ms native and 0.24 ms release (TCG copies cheap VRAM fast with REP MOVSQ, while the first diff loop went through volatile state reads and calls per cell); after `0c4ce54e` (the grid's words read directly, row by row) 0.63 ms native (§4.1). Metal's cost was the uncached reads, which are gone either way |
| the plant red by V7, V2 green | **right** for V7, locally and in CI's first run; that run also failed `mpx3-console`'s T6 and T7, because the first cut sat below the identity code (my fault, §4.6); the re-cut's run is the orchestrator's |
| metal: seconds to tens of seconds before, about a second after | **not measured here**: the maintainer's session (§5.5) |
| U7 red at base (per-exec lines), green with `quiet` | **right**: at `43937c5d` `user: exec pid 1 cr3 …` on both firmwares (12 `user:` lines), at `0c7e1710` none (2 left: the boot's own `user: syscall …` setup lines) |
| `poweroff` by name; the row red at base by `poweroff: not found` | **right on the fix, wrong on the red's mechanism**: the row's own image carries `/bin/poweroff` (the reboot program), so at base it was found, read no name, and restarted the machine: `reboot: FADT reset register`, red by the last power line |
| Linux's message for a user's `reboot`, measured: `reboot: Operation not permitted` or close | **right**: busybox's `reboot -f` exactly that, `poweroff -f` `poweroff: Operation not permitted`, each exit 1; the image has no systemd `reboot`, so none was measured |
| `--check` as a user red at base (`inventory: io`), then the node, the errno and root named | **right**; the wording implemented: `pax-install: inventory: /dev/vda: Permission denied; pax-install opens every disk to measure it, so run it as root` (errno(3)'s text, not the prediction's lower case) |
| the kernel names its commit (written by `tools/build-kernel`) and the SHA-256 of its loaded file (a new Limine request); T6 red at base | **right**: at `c337a03e` `no kernel: line`, at `5c33b1c7` `kernel: b9e54a31… sha256 07aabe04…, 3283920 bytes`, the ELF's own sha256 and size |
| the hash costs about 1 s under TCG, under 0.1 s on metal | **right under TCG**: 1,444-1,477 ms to the first program with it, 160-164 ms without, three boots each (`hashprobe`): 1.3 s for the native kernel's 3,283,920 bytes. Metal unmeasured (the stick's kernel is the release tier's) |
| not predicted | the `boot:` line (T7) and the identity line's repeat before it: on metal the banner scrolls off before the prompt (R-px87-9, R-px87-10) |
| the stick: px86's recipe, its allow-list empty, qualified under OVMF shaped like kasumi | **right** at `0eadf6b4` (rebased `e9887549`; stick3, §4.7), after faults of my own in the qualification script, not in PAX: 256 MiB for a 385 MB archive; disks passed to qemu-run beside a stick, which it refuses; three row expectations (escapes, the boot medium's `boot:` line, root's `--check` under a read-only stick); QMP memsave given unsigned higher-half addresses |
| Footprint: cross-cutting | **right** (`boot/start.S`, `tools/build-kernel`: tier all) |

## 4. Evidence index

Every log named here is under `notes/px87/kasumi/runs/` (copied from kasumi's `/home/mfwolffe/lanes/px87/runs/`);
each run's first line names its commit, and each step prints `END <step> exit=N`.

### 4.1 pax#253: the console writes the framebuffer and never reads it

**The change** (`9d6d78b5`, `0c4ce54e`, in `kernel/screen` alone). The cell grid already held every cell of the
screen in RAM; it is the framebuffer's shadow. The framebuffer shows each cell of the active grid as `draw` draws it
(every writer of a cell draws it; `attach` and `repaint_palette` clear and draw the whole grid), but for the cursor's
cell while it is shown, and `scroll` hides the cursor first. So `scroll` moves the cells up in RAM and draws only the
cells whose value changed; a cell that already shows what moves into it is left alone. No pixel copy, no new storage,
nothing under `boot/`. `attach` checks that the font's space is empty (so the cleared framebuffer already shows every
BLANK cell) and draws the grid otherwise. px19's scroll (REP MOVSQ of the framebuffer onto itself) stays behind the
command-line word `fbread`, read once at `attach` (R-px87-3). Pixels right of and below the grid stay background: a
scroll no longer moves them (they took the scrolled-in rendition's background before; `tools/screen-ref` models cells
only, and no QEMU mode has such a margin at 1x).

**The witness, V7** (`tests/mpx3-screen.d/readwatch.py`, `c0101798`, `ed5b144c`; the row `d0e243d1`). Under TCG,
QEMU's gdb stub, driven by the lane's own remote-protocol client (no gdb): a hardware breakpoint on the first
`pax_fb_fill` (the screen's clear; `%rdi` and `%rdx` give the framebuffer's range), then one read watchpoint (`Z3`)
over the whole range until `pax_halt`; each stop is a guest instruction that loaded framebuffer memory, counted (to a
cap of 64, then the watch is removed so the boot ends whole). The emulator is the witness, not the kernel. The control
boots the same kernel with `fbread` and must be seen reading, so the witness is never vacuous (R-px87-1).

| row | base `3e28a8bc` + V7 (`d0e243d1`) | head (`9d6d78b5`; `v7-green2.log`) |
|---|---|---|
| V7 native BIOS | `64+ framebuffer reads in 393 scrolls, the first by pax_fb_copy+0x7 (rsi 0xffff8000fd014008, framebuffer + 0x14008) called from _Wscreen.scroll$917b10a6eb8f6acc+0x19e` | `0 reads of the framebuffer's 4096000 bytes in 393 scrolls`; the control `reads=8+`, the first by `pax_fb_copy` called from `_Wscreen.scroll_readback` |
| V7 native UEFI | the same, `rsi 0xffff800080014008` | 0 reads in 394 scrolls; the control read |
| V7 release BIOS, UEFI | (base not run on release) | 0 reads in 393 and 394 scrolls; the control read |
| V2, V5, V6 | pass | pass, every leg (`8000 of 8000 cells`) |

The probe before the row (`probe-rw-base.log`, base code): the same reads on BIOS and UEFI, 11 s and 16 s a watched
boot.

**V3, the scrolled line's cost under TCG** (a measurement, no bound; QEMU's VRAM is ordinary host memory, so TCG
shows CPU cost, not metal's uncached reads):

| commit | native BIOS | native UEFI | release BIOS | release UEFI |
|---|---|---|---|---|
| base + V7 (`d0e243d1`) | 0.98 ms | 0.98 ms | not run | not run |
| `9d6d78b5` (the first diff loop) | 1.56 ms | 1.61 ms | 0.26 ms | 0.24 ms |
| `0c4ce54e` (the grid read directly; `plant-local.log`, the plant's own copy of one band included) | 0.63 ms | | | |

The gauntlet's V3 lines at the head are in `gauntlet3.log` (§4.8).

### 4.2 pax#246: the live session is quiet

`boot/limine-usb.conf`'s live entry gains `cmdline: quiet` (`5da10840`), px15's word: kernel/user prints no line
for a program's ordinary life (its exec, its exit, the first system call it tries that PAX lacks, the frames line);
refusals, faults and bad buffers still print. kmain_console's `run N:` lines stay, so `tools/qemu-halt`'s typing
still finds its anchor (`run 1:`, px15) (R-px87-4).

| row | red (`43937c5d`, `u7-red3.log`) | green (`0c7e1710`, `u7-green.log`) |
|---|---|---|
| U7 (`tests/usb-stick`; `d704c536` names the matched line) | BIOS and UEFI: `user: exec pid 1 cr3 0x00000000001c0000 …`, 12 `user:` lines | BIOS and UEFI: no per-program line (2 `user:` lines left: the boot's `user: syscall …` setup report) |

U7 ran alone (`notes/px87/kasumi/probe-u7.sh`: the suite's own commands, the stick image built by `tools/mkdisk` on
the host because its disk tools want a container engine, the boots in the container); the whole `tests/usb-stick` is
CI's (its Linux oracle needs `tools/fetch-usb-linux`'s kernel packages).

### 4.3 pax#243, #265, #266: poweroff, and what a user is told

- **`poweroff`** (`dc41ead5`): `user/elf/reboot.S` reads argv[0]'s base name; run as `poweroff` it sends
  LINUX_REBOOT_CMD_POWER_OFF whatever its arguments (reboot(8): `reboot`, `halt` and `poweroff` are one program);
  `reboot`, `reboot -h` and `reboot -p` are unchanged. The image carries `/bin/poweroff`, the same bytes
  (`tools/distribution-root`, `82d605d7`; `tests/distribution`'s `image-poweroff-is-reboot`, `e52b4393`) (R-px87-5).
- **A refused reboot(2)** (`dc41ead5`): `<name>: <errno's text>` on standard error and exit 1, as Linux's tools
  answer, measured black-box (`notes/px87/linux/reboot-as-user.log`: Ubuntu 24.04's busybox-static 1.36.1 as uid
  1000: `reboot -f` -> `reboot: Operation not permitted`, `poweroff -f` -> `poweroff: Operation not permitted`,
  `halt -f` -> `halt: Operation not permitted`, each exit 1) (R-px87-6).
- **`pax-install --check` as a user** (`55ca3bfc`, `73d188e7`): the inventory opens every disk's node read-only to
  measure it; a disk's node is root's alone (`brw-------`, kernel/files' MODE_BLK, px79), so the open is refused.
  `open_disk` now says `pax-install: inventory: /dev/<name>: Permission denied; pax-install opens every disk to
  measure it, so run it as root` (EPERM's text when the errno is EPERM; any other errno by number) and the inventory
  stops `denied`, main printing nothing more (R-px87-7).

The rows (`tests/mpx6-install.d/asuser.py`, `f694a9b1`, hooked after I-inventory by `5d96b19f`): one boot of an
initramfs whose run list is `/bin/su pax /check-user.sh` (uid 1000 through su, px46) and then `/bin/poweroff` as root,
one 64 MiB virtio disk.

| row | red (`5d96b19f`, `asuser-red.serial.log`) | green (`73d188e7`, `asuser-green.log`) |
|---|---|---|
| I-user-check | `pax-install: inventory: io`, status 1 | `pax-install: inventory: /dev/vda: Permission denied; pax-install opens every disk to measure it, so run it as root`, status 1 |
| I-user-reboot | `reboot` and `poweroff` silent, status 1 each | `reboot: Operation not permitted`, `poweroff: Operation not permitted`, status 1 each, the machine still up |
| I-poweroff | root's `/bin/poweroff` restarted the machine: `reboot: FADT reset register` | `poweroff: ACPI S5 types 0/0`, QEMU status 0 |
| I-user-disk | (not reached: the first assertion stopped the red run) | the disk byte-identical |

The probe ran the row alone with its inputs built directly (`probe-asuser.sh`); the gauntlet runs it inside
`tests/mpx6-install` whole (§4.8).

### 4.4 pax#176: the kernel names itself; the boot times itself

- **The commit** (`d76911ce`, `9ba59ea8`): `boot/start.S` reserves 48 zeroed bytes, `pax_kernel_commit`, in
  `.rodata`; `tools/build-kernel`'s new step 4 writes the tree's `git rev-parse HEAD` there after the link (with
  `-dirty` when a tracked file differs; `PAX_KERNEL_COMMIT` instead when set; nothing outside a checkout, which the
  kernel prints as `unknown`), found through the ELF's symbol table and its PT_LOAD's file offset, refusing a slot
  that is not zero. Two builds of one commit are still byte-identical (the stick's repeat build, §4.7).
- **The digest** (`d76911ce`, `e0621eb1`, `b1ea1480`): Limine's Executable File response (`boot/start.S`'s
  eleventh request) gives the file as loaded; `kernel/identity` hashes it with FIPS 180-4's SHA-256 in one frame,
  so the line names exactly what `sha256sum /boot/pax` and `/etc/pax-release`'s kernel row read (R-px87-8).
- **The lines** (`348256a8`, `4ee44add`, `db518ae1`): `kernel: <commit> sha256 <digest>, <n> bytes` under `PAX: the
  console`, and the same line again just before the boot line, because on metal the banner scrolls off the screen
  long before the prompt (R-px87-9); then `boot: <n> ms from the kernel's entry to its first program; the console
  drew for <m> ms of it (<s> scrolls, <b> bytes)`: the TSC at kmain's first statement, its rate measured against
  10 ms of the firmware's clock (kernel/clock: the HPET, else the PM timer), the console's share from
  `kernel/screen`'s own TSC cycles inside `put` and `attach` (`09295398`) (R-px87-10). This is the metal A/B's number.

| row | red | green |
|---|---|---|
| T6 (`7b50779d`) | `c337a03e` (`console-red.log`): `'no kernel: line', not 'kernel: 6fce7a12… sha256 6969c859…, 3265904 bytes'` | `5c33b1c7` (`console-caps.log`): `kernel: b9e54a31… sha256 07aabe04…, 3283920 bytes`, every session |
| T6's repeat (`40eeb4a1`) | `40eeb4a1` (`t6r-red.log`): `not repeated before the boot line ('ahci0: 8086:2922 at 00:1f.2 port 2: ATAPI skipped …')`, every session | the gauntlet (§4.8) |
| T7 (`c337a03e`) | `c337a03e`: `no boot line as expected ('')` | `5c33b1c7`: `boot: 1568 ms from the kernel's entry to its first program; the console drew for 34 ms of it (0 scrolls, 2724 bytes)` |

**The hash's cost** (`hashprobe.log`; the head and the same commit with `identity.report()` dropped, a probe commit
made on kasumi and never pushed; three BIOS boots each, TCG): 1,444-1,477 ms to the first program with it, 160-164
ms without. The SHA-256 of the native kernel's 3,283,920 bytes costs about 1.3 s of every console-kernel boot under
TCG; CI boots run that kernel (R-px87-8 names the trade).

### 4.5 Rulings (recommended and implemented, not decided)

- **R-px87-1, V7's witness.** (A) QEMU's gdb stub under TCG: one read watchpoint over the framebuffer, counted
  from outside the kernel, with the `fbread` boot as its control; (B) a guest-side MMU tracer (the framebuffer's
  pages not present, the #PF error code's W bit telling reads from writes, a single step to re-arm), which would also
  run on metal but changes the fault path every suite runs; (C) a count kept by kernel/screen of its own source
  operands (the code under test reporting on itself). x86 has no write-only page, so the issue's "map it
  write-only" is not available. Recommended and implemented: **A**.
- **R-px87-2, the shadow.** (A) the existing cell grid as the shadow, a scroll drawing only the cells that change;
  (B) a pixel shadow in RAM (up to 33 MB at 3840x2160, from kernel/frames), scrolled with REP MOVSQ there and blitted
  whole, so every scroll writes the whole grid; (C) redraw every cell of the region (writes only, but the most
  writes). Recommended and implemented: **A**: no new storage and the fewest framebuffer writes.
- **R-px87-3, px19's scroll kept behind `fbread`.** (A) kept, read once at `attach`, for V7's control and the metal
  A/B, with the second Limine entry on the staged stick only (`notes/px87/stick/limine-usb-ab.conf`); (B) removed,
  the A/B by stopwatch between an old stick and the new one (different kernels and payloads); (C) A, and the second
  entry in the repository's own `boot/limine-usb.conf`. Recommended and implemented: **A**. Its cost is one
  function and one module boolean; the orchestrator may drop the word once the metal numbers are in, V7's control
  going with it.
- **R-px87-4, the quiet live session.** (A) px15's `quiet` on the live entry (the lines are not printed at all);
  (B) a console level that keeps the lines in the kernel's memory log for the stick's log file, the issue's wish;
  (C) both. Recommended and implemented: **A**; B is a follow-on (§5.4). The installed system's entry is unchanged.
- **R-px87-5, `poweroff`.** (A) the reboot program under a second name, by argv[0] (one program, as reboot(8)); (B)
  a second program; (C) a shell alias in `/etc/shrc` (not a command for `su -c` or a script). Recommended and
  implemented: **A**.
- **R-px87-6, a user's `reboot`.** (A) busybox's measured `<name>: Operation not permitted`, exit 1 (the same
  semantics as PAX's: sync, then reboot(2)); (B) systemd's message (the image has no systemd `reboot`; its own path
  asks logind, not reboot(2)); (C) a PAX sentence. Recommended and implemented: **A**.
- **R-px87-7, `--check` as a user.** (A) the first refused node named with errno(3)'s text and the need for root,
  the inventory stopping there, status 1; (B) carry on past the refused disk, listing what can be read; (C) refuse a
  non-root `--check` up front by uid. Recommended and implemented: **A**: the refusal is the open's own, so it is true
  whoever runs it.
- **R-px87-8, the kernel's name.** (A) the kernel names itself: the commit written by `tools/build-kernel`, the
  digest measured at boot (about 1.3 s of every TCG boot of the native kernel, measured); (B) the image's
  `/etc/pax-banner` gains the ELF's digest (a claim of the image's, on distribution images only, printed after the
  mount); (C) A with the hash behind a command-line word (cheaper CI, but most transcripts then name no digest).
  Recommended and implemented: **A**. If the CI time matters, the hash's inner loop can be written without calls
  (a follow-on, §5.4).
- **R-px87-9, the line at the prompt.** (A) the same `kernel:` line again just before the boot line; (B) a
  `/proc/version` (a new fixed procfs entry and its place in every listing a differential suite compares); (C)
  nothing (the photo shows only the banner's scroll). Recommended and implemented: **A**; B is a follow-on.
- **R-px87-10, the metal number.** (A) the kernel's `boot:` line: TSC from the entry, calibrated against the
  firmware's clock, with the console's own share; (B) the maintainer's stopwatch only. Recommended and implemented:
  **A**, and B as the cross-check (§5.5).
- **R-px87-0, the plant's base.** (A) the lane's head, its draft PR against `px87`, so its run is the planner's
  `tier pr` for `kernel/screen` alone (the @console suites and `mpx6-firmware`), RULES §7's smallest run that shows
  it, and every other row of those suites green; (B) an earlier commit of the fix. B was my first cut (on `4e27eb30`,
  rebased `0c4ce54e`) and was wrong: its run tested the plant merged into the head pushed at the time, `c27c9810`
  (rebased `82d605d7`), which carried T6 and T7's red-first rows without the identity code, so `mpx3-console` failed
  T6 and T7 beside V7's red (§4.6). Recommended and implemented: **A**: `26439858` on the pre-rebase head `0eadf6b4`,
  then the same commit on the rebased head (R-px87-14; its commit in #269's body).
- **R-px87-11, the Linux side on kasumi.** `mpx3-console`'s `tools/linux-tty --pid1` makes a pid namespace, which
  needs `CAP_SYS_ADMIN`: (A) `--cap-add SYS_ADMIN` inside the rootless user namespace, for the lane's runs only; (B)
  leave T2 and T5 to CI. Recommended and implemented: **A** (nothing on the host gains a capability; CI is unchanged).
- **R-px87-12, the qualification's disks.** `tools/qemu-run` refuses `--nvme`, `--ahci` and `--drive` beside
  `--usb-stick` (a stick boots alone): (A) the NVMe and SATA disks as QEMU's own options after `--`, in the lane's
  `qual.py` only; (B) teach `tools/qemu-run` to attach disks beside a stick. Recommended and implemented: **A** (no
  shared tool changes for a lane's qualification); B when a suite needs it.
- **R-px87-13, the boot line in the triage.** `tests/mpx6-triage`'s T2 compares a plain boot's transcript with a
  triage boot's, masking what moves between boots (the clock's numbers); the new `boot:` line's milliseconds,
  scroll and byte counts move too (1470 ms and 0 scrolls plain, 1518 ms and 2 scrolls under triage in gauntlet2):
  (A) mask the line's numbers as the clock's are (`a3a9ba6f`); (B) a command-line word to drop the line under
  triage. Recommended and implemented: **A**: the triage still sees the line, only its measured numbers are masked.
- **R-px87-14 (the orchestrator's, decided): rebase before the label; gauntlet3 stands by tree.** The lane is
  rebased onto trunk `5da8daaf` before the `full-matrix` label, every cited commit mapped by script, and gauntlet3
  at `0eadf6b4` stands for the rebased code because the trees differ only in `notes/pm00*` (§4.10). The plant is
  re-cut on the rebased head; the main branch and the plant are pushed once each.
- **R-px87-15 (the orchestrator's, decided): gauntlet3's red step again under a short path.** gauntlet3's
  mpx6-firmware failed on a 108-byte QMP socket path (sun_path holds 107), not on the code; the step runs once
  more from the same tree under `/home/mfwolffe/lanes/px87/g/`, the socket's length printed first, and with
  gauntlet3's earlier steps completes the gauntlet (§4.8). The tests' follow-on is pax#273.
- **R-px87-16 (ruled A by the orchestrator): the boot line's readers.** (A) the tests find the timing line by its own
  words, and `boot:` stays the kernel's family of boot reports (Limine, firmware, the medium, the timing); (B)
  rename the kernel's line away from `boot:` (the kernel, the docs, qual.py and the staged stick's text change).
  **A** (`0aeab4e2`, `08da7c51`; §4.11).


### 4.6 The plant, `px87-plant-scroll-read`

One commit: the scroll copies one band of the framebuffer onto the band above it with `pax_fb_copy` before its cell
redraw, as px19's copy did for every band. The picture is still right (the redraw covers whatever the band copy got
wrong), so only a witness of reads can see it. Never merged; draft PR #269 against `px87`.

- **The first cut, `bc142626` on `4e27eb30` (rebased `0c4ce54e`), run 41503056548: wrong.** Two jobs red. `mpx3-screen`: V7 red by name,
  `64+ framebuffer reads in 393 scrolls, the first by pax_fb_copy+0x7 (rsi 0xffff8000fd014008, framebuffer +
  0x14008) called from _Wscreen.scroll$917b10a6eb8f6acc+0xf4`, the plant. `mpx3-console`: T6 and T7 red on every
  session (`'no kernel: line'`, `no boot line as expected ('')`), T1 to T5 green. That is not the scroll read-back
  (`mpx3-console` has no row that sees framebuffer reads): GitHub tested the plant merged into `c27c9810` (rebased
  `82d605d7`), the lane head pushed then (`Merge bc142626… into c27c9810…`, the job's checkout), which held T6 and T7's red-first rows
  (`7b50779d`, `c337a03e`) but not the identity code (`d76911ce` to `348256a8`, pushed later). The plant was cut
  from a commit whose own rows were still red (R-px87-0).
- **The second cut, `26439858` on the pre-rebase head `0eadf6b4` (rebased `e9887549`), run 41527028948** (read
  once at 21:17Z; the watch is the orchestrator's). Expected: V7 alone red, by the same name; `mpx3-console` green.
- **The third cut, after the rebase** (R-px87-14): the same one commit on the rebased lane head, pushed once; its
  commit and run id are in #269's body and the hand-back.

Locally (`plant-local.log`, kasumi, native BIOS): `FAIL V7 native bios readwatch: 64+ framebuffer reads in 393
scrolls, the first by pax_fb_copy+0x7 (rsi 0xffff8000fd014008, framebuffer + 0x14008) called from
_Wscreen.scroll$917b10a6eb8f6acc+0xf4`, every other row passing (V1 to V6, V2's screendump `8000 of 8000 cells`):
red by name, by the default scroll (`_Wscreen.scroll`, not `scroll_readback`).

### 4.7 The stick

`notes/px87/stick/stick.sh` (px86's recipe, `notes/px86/hasu/stick.sh`) at a commit, under one hold of the lock
(`hostchain.sh`): **sbuild** (container) `tools/mkdistribution`'s release pair at the commit, `tests/distribution` on
both archives, px86's live payload, the toolchain archives read twice; **sstick** (host, `tools/mkdisk`'s disk tools
in podman) `tools/mkdisk --usb` with `notes/px87/stick/limine-usb-ab.conf` (the live entry, `quiet`, and a second
entry with `quiet fbread`, R-px87-3), `tools/check-usb`, the allow-list naming no disk, a second build compared
byte for byte, two deliberately broken copies (the EFI loader removed, the protective MBR shrunk) refused by name,
the image read twice, and a copy whose `default_entry: 2` boots the second entry; **squal** (container)
`notes/px87/stick/qual.py` on copies of the image, with a blank NVMe and a blank SATA disk beside it (QEMU's own
options, R-px87-12) that must stay byte-identical: `serial` (COM1, the live session's rows), `kasumi` (no COM1, the
USB keyboard by QMP, the xHCI on MSI behind OVMF's 64 GiB window, the transcript read from PAX's memory log by QMP
memsave), `fbread` (the second entry, the serial rows).

**stick3 at the pre-rebase head `0eadf6b4` (rebased `e9887549`, the same tree but for `notes/pm00*`, §4.10;
`stick3.log`): every step green.** The staged image:

| | |
|---|---|
| image | `pax-stick-0eadf6b4.img`, 795,869,184 bytes, sha256 `e65b28090768f3501c4df3a028ed968c8c764756d3e28b75eeafb08adf6ad1f6` (read twice on kasumi, twice on nomad after the copy, then `chmod 444`) |
| U1, U2 (`tools/check-usb`) | the protective MBR covers the disk, both GPT copies agree; `/EFI/BOOT/BOOTX64.EFI` `90a9a6a5…`, `/boot/pax` `02119659…`, `/boot/initramfs.cpio` `7b0594af…`, `/boot/limine/limine.conf` `6d8e185f…`, `/pax/install-targets` `f282a6d7…` (19 lines, 0 entries: the stick writes no disk) |
| repeat, faults | the second build byte-identical; `a copy with its efi broken is refused by name ('required boot file missing: /EFI/BOOT/BOOTX64.EFI')`, the same for the MBR (`'protective MBR must cover the disk'`) |
| serial leg (`stick3-q1-serial.txt`) | Q1-login; Q1-banner `kernel: 0eadf6b42fa350ae763b1b88e3aa5596b049a6d4 sha256 02119659470ce41c9ddfc2016f4b4bdc7e1c7e7cfeb33101a9fbe66c735c39cb, 2577072 bytes`; Q1-boot `boot: 1016 ms … the console drew for 565 ms of it (340 scrolls, 19056 bytes)`; Q1-quiet; Q1-user-reboot `reboot: Operation not permitted`, status 1; Q1-user-check `pax-install: inventory: /dev/nvme0n1: Permission denied; pax-install opens every disk to measure it, so run it as root`, status 1; Q1-check `Disks (3)`, the NVMe and the SATA disk refused (`no usable install allow-list`), the stick refused (`read-only`), `No disk may be a target, so nothing will be written.`, status 1; Q1-power `poweroff: ACPI S5 types 0/0`, QEMU status 0; Q-nowrite |
| kasumi leg (`stick3-q2-transcript.txt`) | Q2-login with `console: com1 absent`, `xhci 1: BAR0 0x0000001000008000`, `xhci 1: ports 8 MSI vector 80`; Q2-banner (the same line); Q2-boot `boot: 1119 ms … 570 ms of it (343 scrolls, 19198 bytes)`; Q2-quiet; Q2-root (typed on the USB keyboard); Q2-power, QEMU status 0; Q-nowrite |
| fbread leg (`stick3-fbread-serial.txt`) | every serial row again through the second entry; Q1-boot `boot: 804 ms … the console drew for 361 ms of it (340 scrolls, 19055 bytes)` |

Under TCG the old scroll is the cheaper one (361 ms against 565 ms for 340 scrolls): QEMU's framebuffer is ordinary
host memory, so reading it back costs nothing there, while the cell redraw writes every changed cell. On kasumi's
4090 the read-back is what was slow (pax#253); the two entries' `boot:` lines on metal are the measurement (§5.5).

**How it got there** (each fault mine, in order):

1. `stick` (`4658a0dd`'s fix): the first qualification booted with `tools/qemu-run`'s default 256 MiB, which cannot
   hold the 385 MB archive; QEMU sat in Limine's load and was ended by its own pid. The legs boot with 3 GiB.
2. `stick2` at `14d5237b` (rebased `db518ae1`): sstick printed `FAIL USB: required boot file missing: /EFI/BOOT/BOOTX64.EFI` and `FAIL
   USB: protective MBR must cover the disk`. Those were `tools/check-usb`'s refusals of the two copies the chain breaks
   on purpose, the expected answers in check-usb's own words; the good image's U2 had read BOOTX64.EFI's sha256. The
   chain now says each as `PASS a copy with its <fault> broken is refused by name` (`7edb9cdf`). squal-serial then
   failed every row with an empty transcript: `tools/qemu-run` exits 2 at once when `--nvme` or `--ahci` is given
   beside `--usb-stick` (as `96f35f71` gave them), so no guest started. `7edb9cdf` attaches the disks as QEMU's own
   options and keeps qemu-run's output (`qemu-run.out`) for a leg that does not boot.
3. `probe-fix` at `ae380b14` (rebased `7edb9cdf`) against stick2's image (`probe-fix.log`): the serial leg ran the whole session (Q1-login,
   -quiet, -user-reboot, -user-check, -power and Q-nowrite green) and three rows failed on the script, not on PAX:
   Q1-banner read the line with the console's cursor escapes in front (`ESC[01;01HESC[01;01HPAX: the console`);
   Q1-boot took the boot medium's line, `boot: /boot/initramfs.cpio from a disk: …`, which also begins `boot: `;
   Q1-check expected a live-medium refusal, but under QEMU the stick is attached read-only and refused as
   `read-only`, the two blank disks for the allow-list naming none. The kasumi leg failed Q2-login on an empty
   transcript, yet its screendump (`probe-fix-q2-screen-login.png`) shows the stick at `login:` behind
   `nec-usb-xhci` on MSI (`xhci 1: ports 8 MSI vector 80`, the identity and boot lines, `run 1:`, `login:`). The
   transcript was empty because QMP's memsave declares `val` an int64 and refuses the kernel's higher-half addresses
   as unsigned numbers (`probe-memsave.log`, QEMU 8.2.2: `0xffffffff80123450` -> `Invalid parameter type for 'val',
   expected: integer`; the same address as its two's complement accepted, `Invalid addr 0xffffffff80123450/size 8`
   on a stopped machine). So the stick does boot behind the NEC controller under QEMU 8.2.2 and OVMF, and no run on
   the stock `qemu-xhci` (INTx) was needed. `196b1371` reads every line with the escapes removed, picks the boot line
   by its own pattern (and checks the identity line just before it), checks root's `--check` by every listed disk
   refused, nothing written, status 1, and passes memsave's address as int64; the new rows were checked against
   probe-fix's own transcript (green) and against it with the stick's refusal removed (red) before the commit.
4. `stick3` at `0eadf6b4` (rebased `e9887549`): green, above.

### 4.8 The gauntlet

`notes/px87/kasumi/gauntlet.sh HEAD`, run by `hostchain.sh` (one hold of the lock, CPUs 0-3): a fresh clone of
GitHub's `pax` at HEAD, fresh build directories, steps ci-plan, ci-budgets, pax-release, mpx1 (both firmwares),
mpx3-screen (both tiers and firmwares: V0-V7), mpx3-console (both tiers and firmwares, the Linux side with
`CAP_SYS_ADMIN` in the user namespace, R-px87-11), u7 (`probe-u7.sh`), mpx6-install (`--rows smoke --tier native
--firmware bios`, the as-user rows included), mpx6-firmware (`--tier native --firmware both`, F10 the triage). It
stops at the first nonzero step and prints `END <step> exit=N` for each.

**gauntlet2 at `14d5237b` (rebased `db518ae1`; `gauntlet2.log`): red at mpx6-firmware.** `END ci-plan exit=0`, `END ci-budgets exit=0`,
`END pax-release exit=0`, `END mpx1 exit=0`, `END mpx3-screen exit=0`, `END mpx3-console exit=0`, `END u7-build
exit=0`, `END u7-disk exit=0`, `END u7-boot exit=0`, `END u7 exit=0`, `END mpx6-install exit=0`, `END mpx6-firmware
exit=2` (`mpx6-triage: FAIL T2 bios: triage changed a line PAX prints`, `mpx6-firmware: FAIL F10 native: the metal
triage`), `END gauntlet2 exit=2`. T2 compares a plain boot's transcript with a triage boot's; the one line that
differed (`gauntlet2-triage-bios.transcript.diff`) was the new `boot:` line's measurements, `1470 ms … 31 ms of it
(0 scrolls, 2799 bytes)` plain against `1518 ms … 50 ms of it (2 scrolls, 2799 bytes)` under triage. The change
did not break what the triage protects; the expectation moves with the new line (R-px87-13): `a3a9ba6f` masks the
line's numbers as T2 masks the clock's. Green at `ae380b14` (rebased `7edb9cdf`; `probe-fix.log`): `PASS T1/T2 bios: plain and triage,
the same transcript but for the screen line (41 lines)`, the same on UEFI (42 lines), every TRIAGE row passing,
`END triage exit=0`.

**gauntlet3 at the pre-rebase head `0eadf6b4`** (rebased `e9887549`, the same tree but for `notes/pm00*`, §4.10;
`gauntlet3.log`): `END ci-plan exit=0`, `END ci-budgets exit=0`, `END pax-release exit=0`, `END mpx1 exit=0` (1084
s), `END mpx3-screen exit=0` (1070 s), `END mpx3-console exit=0` (674 s), `END u7-build exit=0`, `END u7-disk
exit=0`, `END u7-boot exit=0`, `END u7 exit=0`, `END mpx6-install exit=0` (826 s), `END mpx6-firmware exit=2` (593
s), `END gauntlet3 exit=2`. Every row before the red passed (F1 to F9, T0, TRIAGE plain, triage, stop6 and fault3,
`PASS T1/T2 bios`); then `tests/mpx6-triage.d/leg.py` line 66 raised `OSError: AF_UNIX path too long`, and
`FAIL mpx6-triage bios fault3-reset`, `FAIL F10 native: the metal triage` followed. The rig's path, not the code:
leg.py puts its QMP socket in the leg's output directory (line 28), under PAX_BUILD, and gauntlet3's
`/home/mfwolffe/lanes/px87/gbuild/mpx6-firmware/firmware/native/mpx6-triage/native/bios/fault3-reset/qmp.sock` is
108 bytes, past sun_path's 107 and its NUL; probe-fix's shorter directory had passed the same legs.

**The step again under a short path (R-px87-15, `firmware-short.log`, `notes/px87/kasumi/firmware-short.sh`)**: the
same tree (`0eadf6b4`, a worktree at `/home/mfwolffe/lanes/px87/g/t`), PAX_BUILD `/home/mfwolffe/lanes/px87/g/b`,
one hold of the lock, the socket's length printed first: `…/g/b/firmware/native/mpx6-triage/native/bios/
fault3-reset/qmp.sock: 91 bytes` (the same on UEFI). F1 to F11 pass, `PASS TRIAGE fault3-reset: no triage IDT,
the fault became a reset` on both firmwares, `PASS T1/T2 bios` (41 lines) and `uefi` (42), `PASS F10 native: the
metal triage on bios uefi`, `END mpx6-firmware exit=0` (631 s), `END firmware-short exit=0`. With gauntlet3's earlier
steps that completes the gauntlet for `0eadf6b4` = `e9887549`. The socket's dependence on the caller's path is
pax#273, filed by the orchestrator.

### 4.9 Commits (rebased on `5da8daaf`, oldest first; the failing row before each fix)

- `ac0d327f` the prediction, first.
- pax#253: `c0101798`, `ed5b144c` (the witness), `d0e243d1` (V7, red at `3e28a8bc` + V7: `64+ framebuffer reads … by
  pax_fb_copy … called from _Wscreen.scroll`), `9d6d78b5` (the fix; V7 0 reads), `0c4ce54e` (V3's loop, after
  `9d6d78b5`'s 1.56 ms), `09295398` (the console's TSC cycles, for T7).
- pax#265, #266, #243: `f694a9b1`, `5d96b19f` (the as-user rows, red at `5d96b19f`: `inventory: io`, a silent
  `reboot`, root's `poweroff` restarting), `dc41ead5` (reboot.S), `55ca3bfc`, `73d188e7` (the inventory),
  `e52b4393` (red by the missing name), `82d605d7` (`/bin/poweroff`).
- pax#176: `7b50779d`, `c337a03e` (T6 and T7, red at `c337a03e`: `no kernel: line`, `no boot line`), `d76911ce`,
  `e0621eb1`, `9ba59ea8`, `b1ea1480`, `348256a8` (green at `5c33b1c7`), `5c33b1c7` (the tier map), `40eeb4a1` (T6's
  repeat, red at `40eeb4a1`), `4ee44add`, `db518ae1` (green).
- pax#246: `43937c5d` (U7, red at `43937c5d`: `user: exec pid 1 …`), `d704c536` (U7 names the line), `5da10840`
  (`quiet`; green at `0c7e1710`).
- The triage: `a3a9ba6f` (T2 red at `db518ae1` in gauntlet2: only the `boot:` line's numbers differed; R-px87-13).
- Docs: `4e7fce98` (BOOT.md), `0c7e1710` (INSTALL-METAL.md), `144db186` (README, README only), `8a8fb5b2`
  (SOURCES.md).
- The stick and the lane's tools: `a28dc800`, `96f35f71`, `4658a0dd`, `7edb9cdf`, `196b1371` (notes/px87/stick),
  `7c20722b` (notes/px87/linux), `ad345890`, `e9887549` (notes/px87/kasumi); then this note and the logs.
- After the rebase (§4.10): `8460ebe0`, `7b7a99fe` (the map), `a9a3d548` (the short-path step), `f90dd16d` (CI's reds
  on kasumi, the engine stand-in); the fixes after CI's tier all (§4.11): `0aeab4e2` (T6, T7; red at `088312b1` in
  `ci-red-native-usb.log`), `08da7c51` (P9; red at `088312b1` in `ci-red.log`); gauntlet4's script; the note and
  the logs.

### 4.10 The rebase (R-px87-14)

After gauntlet3 began and stick3 ended, trunk had moved from `3e28a8bc` to `5da8daaf` by pm00's notes alone
(`notes/pm00-the-design.md`, `notes/pm00/SOURCES.md`, `notes/pm00/matrix.md`, `notes/pm00/prediction.txt`; no
path in common with this lane). The 47 commits were rebased onto `5da8daaf` without a conflict.
`notes/px87/rebase/map.sh 3e28a8bc fa6796d8 5da8daaf <rebased head>` pairs each pre-rebase commit with its rebased
one in order and stops unless the subjects are equal, the patches equal (`git patch-id --stable`) and the trees
differ by exactly trunk's four paths; it passed for all 47, and its table is `notes/px87/rebase/map.txt` (old,
new, subject). The table resolves every pre-rebase name in the logs, the transcripts and the stick: the stick's
`kernel: 0eadf6b42fa3…` line and gauntlet3's head `0eadf6b4` are the rebased `e9887549`.

The code head before and after (`notes/px87/rebase/code-head-diff.txt`):

```
$ git diff --stat 0eadf6b4 e9887549
 notes/pm00-the-design.md  | 222 ++++++++++++++++++++++++++++++++++++++++++++++
 notes/pm00/SOURCES.md     | 126 ++++++++++++++++++++++++++
 notes/pm00/matrix.md      |  59 ++++++++++++
 notes/pm00/prediction.txt |   6 ++
 4 files changed, 413 insertions(+)
$ git diff 0eadf6b4 e9887549 -- . ':(exclude)notes/pm00*' | wc -c
0
$ git diff --name-only 0eadf6b4 e9887549 -- . ':(exclude)notes/pm00*' | wc -l
0
```

So the rebased code is gauntlet3's and stick3's tree plus pm00's notes, and gauntlet3 at `0eadf6b4` stands for it.
The staged stick stays as it was built: the pre-merge stick, its kernel line naming `0eadf6b4`.

### 4.11 CI's tier all at `088312b1`: two reds, both one cause (R-px87-16)

Run 41530916165 (the PR's labelled tier all at `088312b1`): 59 jobs green, two red, `mpx3-console` and
`mpx6-part`; the plant's run 41530700041 (`d82d30f0`) red in `mpx3-screen` and `mpx3-console`.

**The cause.** A boot from a disk prints the medium's line, `boot: /boot/initramfs.cpio from a disk: partition 1,
GPT disk …, partition …`, and the kernel now prints its own `boot: <n> ms from the kernel's entry …` line on every
boot. Two readers took "the first `^boot: ` line" or "no `^boot: ` line" to mean the medium's:
- `tests/mpx3-console`'s T6 (the identity line repeated before the boot line) and T7 (`grep -m1 '^boot: '`). On
  the ISO the first `boot:` line is the timing line, so the suite's own job and every gauntlet here passed them;
  booted from the stick (`tests/usb-stick`'s U5, `tests/mpx3-console --usb-stick`) the medium's line comes first.
  U5's console suite writes to `$work/native-usb.log` and the script stops under `set -e`, so CI's log shows only
  U4's lines (`FAIL USB: required boot file missing: …` and `FAIL USB: protective MBR must cover the disk` are
  `tools/check-usb`'s answers to the two copies U4 breaks on purpose; `PASS U4: efi rejected by name`, `PASS U4: mbr
  rejected by name`) and then the job's exit 1.
- `tests/mpx6-part`'s P9 (`! sgrep -q '^boot: '`, "the ISO prints no boot medium line"): the timing line matched.
- A sweep of `tests/` and `tools/` found no other reader that takes the first `boot:` line or refuses any; every
  other `boot:` pattern names its own words (`boot: /boot/initramfs.cpio from a disk: …`, `boot: Limine …`, `boot:
  firmware …`, mpx6-triage's `boot: [0-9]+ ms` mask).

Why the lane's runs missed it: the gauntlets ran U7 alone (`probe-u7.sh`) and left the whole of `tests/usb-stick`
and `tests/mpx6-part` to CI (§5.2), because their disk tools (`tools/e2fs`, `tools/disktools`) start a container
and the lane's QEMU runs inside one. CI's stick did not differ from the lane's: U1 to U4 green, the same ESP.

**Red, reproduced on kasumi** (`ci-red.log`, `notes/px87/kasumi/probe-ci.sh` at `088312b1`): the disk tools ran
inside the container through `notes/px87/kasumi/engine-local.sh` (PAX_ENGINE: the program run in the container,
the pinned disktools packages from their own store; the container's e2fsprogs checked first against the pinned
image's: `e2fsprogs: 1.47.0-2.4~exp1ubuntu4.1`, mke2fs, e2fsck and debugfs the same sha256, `the same programs,
pinned and in the container`). tests/usb-stick: U1 to U4 green, U5's ISO leg green (70 PASS T rows, 0 FAIL), its
USB leg red on every session (`ci-red-native-usb.log`, 20 FAIL lines):

```
mpx3-console: FAIL T6 native bios ask-serial: not repeated before the boot line ('ahci0: 8086:2922 at 00:1f.2 port 2: ATAPI skipped (0x00000000eb140101)');
mpx3-console: FAIL T7 native bios ask-serial: no boot line as expected ('boot: /boot/initramfs.cpio from a disk: partition 1, GPT disk dad29f0e-363f-4763-6a5e-c9167573a524, partition 407e1c0d-9130-145d-9467-3854200e2116');
```

and `END usb-stick exit=1`. tests/mpx6-part (native, BIOS and UEFI legs): every row green but

```
mpx6-part: FAIL P9 native bios iso: fstab: /dev/vda on /home: ext2, read-write, write-back boot: 2008 ms from the kernel's entry to its first program; the console drew for 184 ms of it (16 scrolls, 3996 bytes)  (qemu-halt 0)
```

and `END mpx6-part exit=1`. In the container `tools/fetch-usb-linux` failed (`apt-cache depends linux-image-generic`
exit 100, `E: No packages found`: the container's apt lists are empty). That is the environment, and U8 was not
reached here; it is not counted as a pass.

**The fix** (R-px87-16, ruled A): `0aeab4e2` T6 and T7 find the line by its own words (`^boot: [0-9]+ ms from the
kernel's entry to its first program; `); `08da7c51` P9 refuses the medium's line (`^boot: /`). The kernel does not
change; `boot:` stays the kernel's family of boot reports. The green is gauntlet4's (`notes/px87/kasumi/gauntlet4.sh`,
at the pushed head; its END lines go in the PR's body) and CI's.

## 5. Done-when

### 5.1 Checklist

- [x] Item 1, pax#253: the scroll draws from the cell grid and never reads the framebuffer; V7 red at base by name
  and green on every leg, its control seen reading; V2, V5, V6 pixel-identical. The metal before/after is the
  maintainer's (§5.5), on one stick with two entries.
- [x] Item 2, pax#246: the live entry `quiet`; U7 red at base, green.
- [x] Item 3, pax#243: `poweroff` (and `reboot -p`, unchanged) send LINUX_REBOOT_CMD_POWER_OFF; I-poweroff: QEMU
  ends on S5 with no debugger; `docs/INSTALL-METAL.md`'s checklist and the stick's steps use `poweroff`.
- [x] Item 4, pax#265 and #266: I-user-reboot (Linux's measured message, status 1) and I-user-check (the node, the
  errno's text, root needed), each red at base and green, as uid 1000 under QEMU.
- [x] Item 5, pax#176: the kernel's commit and its file's SHA-256 under the banner and again before the boot line;
  T6 red at base, green; the boot's time (T7).
- [x] Item 6: the stick staged under `~/pax-smoke/` with its INSTALL.txt block, qualified under OVMF shaped like
  kasumi; the session's steps in §5.5 and the hand-back.
- [x] Item 7: no kernel, firmware or driver source (§1).
- [x] Item 8: this note, the plant (`px87-plant-scroll-read`, draft PR #269), the PR, the audit.
- [x] README read against the pass: the banner sentence, the live stick's paragraph, the console paragraph, the
  power commands and two rows of the test table moved and are refreshed (`144db186`, a README-only commit).

### 5.2 Departures and limits

- Every QEMU run was TCG: kasumi's firmware has VT-x off (§2). The contract's KVM was not needed by any row.
- Until §4.11, `tests/usb-stick` (but U7) and `tests/mpx6-part` were left to CI; from gauntlet4 they run here,
  their disk tools through `engine-local.sh` inside the container (the programs checked equal to the pinned
  images'). The rest below stays CI's.
- Not run here, left to CI's tier all (the PR touches FULL paths): `tests/kernel-as` (K5 assembles `boot/start.S`'s
  new request and slot through clef; it needs a source-built wolf), `tests/mpx6-ext2` (E7's `/bin/reboot` restart;
  its disk tools want a container engine beside its QEMU), `tests/mpx6-kasumi` (metal.py's legs: M9 still types
  `reboot -p`, unchanged), the whole of `tests/usb-stick` (U7 ran alone; U8's Linux oracle needs
  `tools/fetch-usb-linux`'s kernel packages), and every other suite of the tier.
- The `kernel:` line costs about 1.3 s of every console-kernel boot under TCG (§4.4).
- The stick's second entry (`fbread`) exists on the staged stick only; the repository's `boot/limine-usb.conf` has
  the first entry alone.
- The plant's CI runs were read once each and handed over; the re-cut's verdict is the orchestrator's to read.
- The stick's qualification ran under TCG at 1280x800 on QEMU's devices; kasumi's own GOP, xHCI and disks are the
  metal session's (§5.5).

### 5.3 The measurements

- The framebuffer's reads in kmain_screen's boot, every scroll included: base 64+ (the cap) by the first scroll;
  head 0 in 393 scrolls (BIOS) and 394 (UEFI), native and release (§4.1).
- V3's scrolled line under TCG: base 0.98 ms native; 0.63 ms native at `0c4ce54e` (§4.1); gauntlet3's V3 lines at the
  head are in its log (§4.8).
- The live stick under TCG (stick3, release kernel, 1280x800): `boot:` 1016 ms, the console 565 ms of it in 340
  scrolls with the new scroll; 804 ms and 361 ms with `fbread` (§4.7).
- The boot's time under TCG (T7, the console kernel, a serial session): about 1.5 s to the first program, of which
  the console drew 34-40 ms; the SHA-256 about 1.3 s of it (§4.4).
- Metal (kasumi's 4090 at 2560x1440): the maintainer's, §5.5.

### 5.4 Issues

Filed or closed by this lane: none (a lane files and closes nothing); the orchestrator filed pax#273 (the tests' QMP
sockets under the output tree overflow sun_path when PAX_BUILD is deep, §4.8). Fixed here, to close at the merge: pax#253 (its metal
numbers to come from §5.5's session), #246, #243, #265, #266, #176. Owed to file (pax), the orchestrator's call:

- `/proc/version` (pax#176's second half): a fixed procfs entry naming the kernel as its banner does.
- The installed system's console is not quiet: pax-install writes its own Limine configuration, without `quiet`.
- pax#246's other half: the per-program lines kept in the kernel's memory log for the stick's log file.
- kernel/identity's SHA-256 inner loop through calls: about 1.3 s of every TCG boot of the native kernel.
- The `fbread` word and V7's control: drop both once the metal A/B is in (R-px87-3).

kasumi's VT-x is a firmware setting, not an issue: the orchestrator tells the maintainer, and the metal session's
optional step 6 turns it on.

### 5.5 The metal session (the maintainer's; the same text heads `~/pax-smoke/INSTALL.txt`)

```
READ THIS FIRST (px87, 2026-11-02): the console stick, to look and to time, never to install
=============================================================================================
  pax-stick-0eadf6b4.img   pax branch px87 at 0eadf6b4 (PR #272, not yet merged; since rebased onto trunk as
                           e9887549, the same code: the kernel line still names 0eadf6b4)
      795869184 bytes, SHA256 e65b28090768f3501c4df3a028ed968c8c764756d3e28b75eeafb08adf6ad1f6

  It writes no disk: its install allow-list names none, so pax-install refuses every disk. Leave the 860
  (PAX's install) and the CachyOS NVMe plugged in as they are; nothing on this stick writes either.

  New on it: the console never reads the framebuffer back (pax#253: on the 4090 every scrolled line read
  about 23 MB through the GPU's write-combining mapping); the live session prints no per-program lines
  (#246); `poweroff` (#243); `reboot` and `pax-install --check` as a user say why they refuse (#265, #266);
  the kernel names its commit and file digest (#176), and how long its boot took.

  Limine's menu has two entries, the same kernel and archive:
    1  PAX live (root, no password)                                the new console (the default, 3 s)
    2  PAX live, the old scroll (fbread: px87's measurement only)   the old scroll, for the timing only

The session (about 15 minutes; four photos):
  1. Write the stick (balenaEtcher), plug it into kasumi, power on, F8, choose the stick (UEFI).
  2. Let entry 1 boot. Start a phone stopwatch (or a video) when Limine's menu goes away.
     At `login:`, stop it and take PHOTO 1. The last lines should read:
       kernel: 0eadf6b42fa350ae763b1b88e3aa5596b049a6d4 sha256 02119659470ce41c9ddfc2016f4b4bdc7e1c7e7cfeb33101a9fbe66c735c39cb, 2577072 bytes
       boot: <n> ms from the kernel's entry to its first program; the console drew for <m> ms of it (<s> scrolls, <b> bytes)
       run 1: /bin/pelt /etc/pax-live-login
       PAX live medium: log in as root (no password).
       login:
     and no `user: exec pid ...` lines above them.
  3. Log in as root and type these one at a time:
       su pax -c reboot
         -> reboot: Operation not permitted        (the machine stays up)
       su pax -c 'pax-install --check'
         -> pax-install: inventory: /dev/<a disk>: Permission denied; pax-install opens every disk to measure it, so run it as root
     PHOTO 2: this screen. (Optional, read only: `pax-install --check` as root lists every disk with its verdict;
     on this stick every one is refused.)
  4. Type `poweroff`. The machine should switch itself off within a few seconds (no power button).
     If it does not, PHOTO 3 of the screen, then hold the power button.
  5. Power on, F8, the stick, and this time choose entry 2 in Limine's menu (arrow down, Enter) within 3 s.
     Time it the same way. At `login:`, PHOTO 4 (the same kernel: and boot: lines). Then `root`, `poweroff`.
  6. Optional, while you are in the firmware: Intel Virtualization Technology (VT-x) is off now (CachyOS logged
     "VMX (outside TXT) disabled by BIOS" on 2026-11-02); turning it on gives kasumi's lanes KVM again.
  7. Remove the stick, boot CachyOS, then the pool's recovery order (Tailscale, rpc-server, hasu's llama-server).

What we read off: photo 1's and photo 4's boot: lines (n and m, the new and the old console) and the two
stopwatch times; photo 2's two answers; whether step 4 switched the machine off by itself.
```
