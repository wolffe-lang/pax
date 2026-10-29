# px76 — UEFI on metal: the firmware's machine as it is, not as QEMU draws it

Contract: `wolf/sprints/pax/76-uefi-on-metal/px76-uefi-on-metal.md` (P6, crawl 54), with its
2026-10-28 addendum on `kernel/clock`. Started by a Codex lane (GPT-6-Astra) on base `6ccfe3fe`,
which stopped at `8cad05e4` (`5f0f847a` after the rebase) with uncommitted work when its weekly limit ran out (2026-10-29
~03:00Z); finished by Opus from that state. Footprint: cross-cutting (the kernel's core, CI, the
harness's `tools/qemu-run`).

## Forbidden

No Linux, FreeBSD, OVMF, Limine, QEMU or any kernel's, firmware's or emulator's source was read.
Written from UEFI 2.10 §4 (the system table), ACPI 6.5 §§4.8.3, 5.2 and 20 (the tables, the PM
timer, the reset register, PM1 control, the AML encoding of `\_S5` only), PCI Local Bus 3.0 §6.8
(the MSI capability), IA-PC HPET 1.0a §2.3, the Intel SDM vol. 3A chapter 11 (the local APIC, its
timer, x2APIC's MSRs, MSI's address and data) and the Limine protocol; each is cited in
`docs/SOURCES.md` (px76's section). QEMU 8.2.2 and OVMF were run as black boxes. PAX's own code and
notes were read (px74's, px75's, px77a's). No label, no workflow dispatch, no merge, no release; no
attribution trailers.

## Inputs, verified

- Base `6ccfe3fe` (pax trunk at launch); rebased once, on the orchestrator's merge head, onto
  `10a27451` (px75b's merge, after px84's `ad732049` and px77a's notes). Every branch sha in this
  note is the rebased commit; the kasumi runs before the rebase (`broad1`, `fw1b`, `final`, `inst2`,
  `ka`, the plants) ran at their pre-rebase twins, paired by subject in
  `notes/px76/rebase-map.txt`; `verify` ran at the rebased head (below). The rebase's conflicts:
  `tools/qemu-run`'s header (px75b's `--ahci`/`--boot-ahci` beside px76's flags), the tier map, the
  planner's proof, `docs/BOOT.md` and `docs/SOURCES.md` (both sections kept), the installer's
  `install.py` (px84's 4Kn and sparse targets, then `PAX_INSTALL_NOSERIAL`'s `--no-serial`) and
  `mpx6-install`'s job bound (px84's 60/110/175 kept; the serial-less step's own 15 minutes fit
  inside the all tier's 175).
- wolf 0.2.35 (`cf0c13d38479f444b69bb8356ad5709d07eff323`), archive SHA256
  `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a` (`kernel/wolf.pin`; the
  staged archive's `.verified` digest in `/mnt/steamlib/lanes/px76/cache/wolf-0.2.35/`, read
  again at the takeover); Limine 12.9.1, SHA256
  `5cdebc518daa3af30b22c2322ba0dba2e0e2046fa8b087b9e13071b8dbcdcff4` (`boot/limine.pin`).
- kasumi cores 12-15 under `flock /home/mfwolffe/lanes/kasumi-cores-12-15.lock`, rootless podman,
  `localhost/px80-ubuntu` (QEMU 8.2.2, Ubuntu's OVMF, TCG: no `/dev/kvm` in the container), 12 GiB,
  `taskset -c 12-15`; everything under `/mnt/steamlib/lanes/px76/` (`job.sh`, `jobw.sh`,
  `batch.sh`, `steps.sh`, `measure.sh`, `runs/`). No build on the Mac (git only). `lope` at its
  pin `e6f623c7` copied from px84's clone (copy only).
- **The takeover.** At `5f0f847a` the Codex lane left 27 modified and 5 untracked files. Every one
  was read before it was committed or set aside; the kasumi clone matched the Mac tree file for
  file (sha256 of 5,554 paths) but for the notes, README, `docs/SOURCES.md` and one comment. Its
  push-triggered plant workflow (`.github/workflows/px76-plants.yml`) was set aside, not committed:
  plants on pax are draft PRs on the lane's branch (px70-px75b's), and a workflow file in a plant's
  diff would itself select every suite. No regression suite had been run on the branch; the first
  local batch found three reds the branch had made, each fixed before anything else:
  - the tour triple-faulted at its first pause (`tour` R1-R7): `stage_boot` still called
    `timer.start()`, which now calibrates the LAPIC against a clock that needs paging and the
    APIC, and `pause_early` read a clock never started (a division by its zero period).
    `3c5fe778`, `e5e8136e`; R1-R7 pass (headings 3.0 s apart).
  - `mpx1` A6: `serial.init()` re-attached the early screen through Limine's framebuffer mapping on
    every call, which page-faults once PAX's paging runs (the spin variant calls it in a loop).
    `cb0a2a7d`.
  - `mpx3-screen` V4: the serial log of a screen boot and a screenless one now differ in the
    `memory:` line (Limine lists the framebuffer), the DSDT's length (QEMU's VGA adds AML) and the
    calibrated rate. `9f107e17` folds exactly those.
  and two it would have made in CI: `kmain_timer` and the tour printed the timer line twice, and
  `mpx2-interrupts` I5's four-line tail had the ACPI lines inside it (`b781e3fd`).

## Prediction

Committed before the first change in `e7437080` (`notes/px76-prediction.txt`), scored:

| predicted | measured |
|---|---|
| `qemu-xhci,msix=off` exposes a 64-bit MSI capability | **wrong on QEMU 8.2.2** (CI's): `qemu-xhci` has neither `msi` nor `msix` property and no MSI capability at all (PAX finds none and uses INTx 11); right on hasu's QEMU 11.1. The explicit legs use `nec-usb-xhci` (R-px76-5), whose capability is 64-bit |
| `msi=off,msix=off` keeps INTx | right (`xhci 1: ports 8 INTx 11 …`, F7) |
| one message for interrupter 0; vectors 80-83 for four controllers | right: MME 0 of the NEC's MMC, vector 79 + the controller's number |
| the LAPIC timer near 62.5 MHz at divide 16 | right: 62.46 MHz by the HPET, 62.18 MHz by the PM timer (F1, TCG) |
| q35 `pit=off` exists on 8.2 and 11.1; `hpet=off` falls to the PM timer | right (F1's legs; `clock: PM 3579545 Hz`) |
| OVMF needs a large 64-bit window and RAM above 4 GiB for a high BAR | **wrong**: Ubuntu's OVMF already places QEMU's 64-bit BARs above 4 GiB (the xHCI's at `0xc020000000` with 256 MiB or 8 GiB); the window (`opt/ovmf/X-PciMmio64Mb`) only moves them (`0x1010000000` at any memory size) and RAM plays no part; SeaBIOS keeps them below 4 GiB (`measure.sh`, `docs/SOURCES.md`) |
| 4K from VGA `xres`/`yres` and Limine's `resolution:`; padding needs a synthetic framebuffer | right (F5, F8 at 3840x2160; F4's synthetic 68-byte pitch) |
| about 40 boot lines before login | wrong by an order: px77a's live stick drew **358** rendered lines before `login:` (309 scrolls and 49 rows); F8's console probe draws 40 lines before its first program (`run 1: /bin/usbkeys` is line 41 of its 93): the kernel's own boot is the predicted size |
| the absent UART's receive drain hangs; xHCI's bootstrap polls PIT reloads | right, both: `05a27531` (px77a: stock trunk stalls at `user: syscall star` with `-serial none`; this commit alone reaches `login:`), `317a52d0` |

## Evidence index

### Rulings (recommended and implemented, not decided)

- **R-px76-1 A** (settled): the local APIC timer calibrated against the HPET, else the ACPI PM
  timer, else the PIT; the 8259's line 0 stays masked, its lines 1 and 4 serve the i8042 and COM1
  where they exist.
- **R-px76-2 A** (settled): NVMe and AHCI stay polled; MSI for xHCI only.
- **R-px76-3 B** (settled): 2x glyphs above 2560 pixels wide (240x67 cells at 3840x2160).
- **R-px76-4** (settled: keep only what the protocol marks USABLE): Limine reports UEFI's boot
  services memory as bootloader-reclaimable; PAX keeps it, allocating only USABLE.
- **R-px76-5** (settled): `nec-usb-xhci` only for the explicit MSI and INTx legs.
- **R-px76-6, the high-BAR flag.** The contract asks a QEMU device's BAR above 4 GiB with the
  xHCI and NVMe suites passing. (A) a `tools/qemu-run --high-bar` (UEFI only: OVMF's
  `opt/ovmf/X-PciMmio64Mb` = 65536 and 8 GiB) with `PAX_HIGH_BAR=1` for a whole suite; (B) raw
  QEMU arguments in each test. Recommended and implemented: **A**, a firmware flag beside px76's
  five (`--usb-irq`, `--no-hpet`, `--no-pit`, `--no-serial`, `--display-mode`); px75b's
  `--ahci`/`--boot-ahci` are untouched. The orchestrator may rename it.
- **R-px76-7, x2APIC at the handover.** kasumi's CPU offers x2APIC (and ARAT); whether its firmware
  hands over in x2APIC mode is unknown until px77, and PAX reached the local APIC only through the
  xAPIC MMIO page, which x2APIC mode does not decode (the tick's calibration would panic by name).
  (A) follow IA32_APIC_BASE's EXTD: the same registers by MSR (SDM vol. 3A §11.12); (B) leave it to
  px77's photo. Recommended and implemented: **A**. Its witness is a hand leg
  (`PAX_METAL_X2APIC=1 tests/mpx6-metal`: the kernel switches the mode itself under
  `-cpu max,+x2apic`), not CI's: QEMU 8.2.2's TCG refuses the CPUID bit (`TCG doesn't support
  requested feature: CPUID.01H:ECX.x2apic [bit 21]`, `runs/x2probe.log`) and the kernel stops by
  name (`FAIL METAL x2APIC offered by CPUID`), so the MSR path's first run is a machine that offers
  it (KVM, or px77's boot). The orchestrator may prefer B (drop the path until a witness exists).
- **R-px76-8, the HPET plant's run.** `kernel/clock` is ALL in the map (every kernel's tick reads
  it), so the plant's draft PR runs `tier pr` on every suite (about 57 jobs on native BIOS). (A) the
  draft PR, as the brief says; (B) the branch with no PR and the orchestrator's partial dispatch
  (`-f tier=pr -f suites=mpx6-firmware`, RULES §7's smallest run, one job). Recommended and
  implemented: **A**, the brief's form; the clock's PM check keeps every other suite green (no
  storming tick, no timeouts), so the run costs a native-BIOS sweep, not hours of timeouts.
- **R-px76-9, what V4 compares of the firmware's lines** (the first `tier all` run's
  `mpx3-screen` red, below). V4 compares two boots of one run on one firmware, the screen's and the
  screenless one; there is no recorded golden. On UEFI the display device changes the firmware's
  own tables: OVMF installs a BGRT (UEFI's boot graphics table) only when it has a GOP, so the
  screen boot's XSDT holds one entry more (84 bytes against 76) and lists `acpi: BGRT`. (A) fold
  the firmware's display-dependent lines to their shape: the RSDT/XSDT and DSDT lengths and the
  memory map's numbers to `<n>`, the BGRT's line left out, every other line (PAX's own) compared
  byte for byte; (B) leave every `firmware:`, `memory:` and `acpi:` line out of V4; (C) record a
  golden with CI's pinned OVMF (does not apply: no golden exists, and both boots already share the
  firmware). Recommended and implemented: **A** (`466ebfec`): it keeps each line's presence and
  shape, and a PAX line that changes is still named in the row's diff. **Ruled A** (the
  orchestrator, with px75b's merge head).
- **R-px76-10, the 16-bit port instructions clef lacks** (the first `tier all` run's `kernel-as`
  K5 red, below). `kernel/power` reads and writes the 16-bit PM1 control registers (ACPI 6.5
  §4.8.3; `power_off` requires the FADT's PM1_CNT_LEN, byte 89, to be at least 2) through
  `pax_inw` and `pax_outw` (`2d99836c`, the Codex lane's), `inw %dx, %ax` and
  `outw %ax, %dx` (Intel SDM vol. 2 IN and OUT with the 66h operand-size prefix; GNU as encodes them
  `66 ed` and `66 ef`). clef at `user/clef.pin` (`996a3ccd`) has `inb`, `inl`, `outb` and `outl`
  but neither word form (`unknown_mnemonic inw`, `unknown_mnemonic outw`: `runs/clefprobe.log`),
  since no census source used one. (A) a clef issue to add `inw`/`outw` (and `xorq`), K5 red until
  user/clef.pin moves; (B) spell the two as `.byte` in `boot/io.S` (papers over the gap: not
  recommended); (C) reach PM1 control a byte at a time (changes the register's access width on
  metal: not recommended without a citation that allows it). Recommended: **A**; the instructions
  are kept. `xorq %rax, %rax` (also unknown to clef) was not needed: `4935e753` writes `xorl %eax,
  %eax`, the same zeroed `%rax` (SDM vol. 1 §3.4.1.1). **Ruled A**: clef fixed (clef#10, as02c,
  merged at `b71b43f4`), never spelled in bytes; `user/clef.pin` moves there (`e9cf674b`).
- **px75b's clock shim, deleted at the merge** (px76 merges second; the 2026-10-28 addendum).
  `kernel/ahci`'s waits move from `kernel/ahci_clock` (the 8254's channel 0) to `kernel/clock`,
  the same five names (`a9a05e2f`), and the shim is deleted (`47a9e70a`; its map rule `9cb8da27`,
  the planner's row `0a9ab24a`). R-px75b-7's refusal is narrowed, not dropped: a controller is refused by name
  only where no clock source advances at all (no HPET, no PM timer, no counting PIT), which
  `clock.start` now reports as `clock: none: the HPET, the PM timer and the PIT do not advance`
  instead of panicking (`a5edeeec`); kernel/timer then stops by name (`36bf3e94`), since no tick
  can be calibrated, so only a disk-only kernel boots on to the refusal. A gated or absent 8254
  alone no longer stops AHCI. px75b's row A13 (`pit=off`) now asserts the opposite of its old
  refusal, on both firmwares: `clock: HPET …`, `sda` named, no refusal, the session ran; the new
  row A14 keeps the refusal witnessed on the one machine QEMU can make with no clock (OVMF under
  `-machine acpi=off,pit=off`: no HPET table, no FADT, no counting PIT), with `kmain_blk`
  (`10cbc5f0`). A14 runs on UEFI on every leg (SeaBIOS supplies its own ACPI tables under
  `acpi=off`). `kernel/kmain_blk.lu`'s map rule does not name `mpx6-ahci`; a change to it reaches
  A14 in the all tier.

### Regression (the mpx suites at the branch, native BIOS, kasumi)

Batches `core1`-`core3` and `broad1` (`/mnt/steamlib/lanes/px76/runs/*.log`, each suite's exit on
a `BATCH` line), after the three fixes above:

| suite | result |
|---|---|
| `mpx1`, `mpx2-frames`, `mpx2-paging`, `mpx2-interrupts`, `mpx2-sched`, `mpx2-heap`, `tour` | pass |
| `mpx3-user`, `mpx3-speaker`, `mpx3-sound`, `mpx3-orchestra`, `mpx5-screen`, `mpx6-blk`, `mpx4-net` | pass |
| `mpx3-screen` | V4 red before `9f107e17` (the diff in `broad1.log`), then every row passes (`fw1b`) |
| `mpx6-games`, `mpx6-usb`, `census` | pass |
| `mkw`, `kernel-as` | not run in these batches: the container has no `lupin` and no `cargo` (exit 2, a missing tool). `kernel-as` was run after the first `tier all` run's K5 red, with the seam wolf copied from as02b's cache and clef built by `tools/mkclef` (below) |
| `mpx4-udp`, `mpx4-ready` | not run here: their Linux side needs root for a network namespace (T0/U0: `unshare(CLONE_NEWNET)` refused in the rootless container), so every row compares against nothing; CI runs them as root |

The suites whose Linux side needs a container engine (the `PAX_ENGINE` jobs: the shell, the tree,
the users and jobs, the disks' differentials) are CI's, on the PR's own all-tier run.

### CI wiring

- The `mpx6-firmware` job (`04746422`): `tests/mpx6-firmware $PAX_LEGS`, 90 minutes, its
  transcripts, screens and `.meta` kept. In `tier pr` and `tier full` it runs native BIOS (F5 and
  F8 UEFI regardless); in `tier all` both compiler tiers and both firmwares.
- The long legs in `tier all` only, after each job's own steps, so px83's measured budgets for
  `mpx2-interrupts` (58 of 75 minutes in the nightly) and the other long jobs are untouched: the
  typing rows of `mpx3-console` and `mpx3-shell` with the xHCI on MSI only and on INTx only
  (`tests/mpx6-firmware.d/typing-irq`), `mpx6-nvme`'s pr rows on native UEFI with `PAX_HIGH_BAR=1`,
  and the installer's serial-less row (`mpx6-install --only noserial`, its step 15 minutes, the
  job's bound 60 to 80: 56 minutes in the nightly 40690748340). The clock-less timer and scheduler
  legs (F9) are in the firmware job itself, not in those suites' jobs, for the same budgets.
- `tools/ci-tiers.map` (`f06c5318`): `kernel/acpi/*` and `kernel/clock/*` ALL; `kernel/msi/*` the
  firmware and USB suites; `kernel/power/*` the six suites whose sessions reboot and the firmware
  suite; the metal scripts and kernels the firmware suite's. `tests/ci-plan` (`1bf8e168`) holds each
  rule; the whole proof passes at the head (`final`'s second step: `ci-plan: PASS`).
- This PR touches FULL paths (`boot/start.S`, `tools/qemu-run`, `tools/qemu-halt`), so its own run is
  `tier all`, every suite on every leg, labelled or not.

### tests/mpx6-firmware at the head (native, BIOS and UEFI; `final`)

`/mnt/steamlib/lanes/px76/runs/final.log` (copied to `notes/px76/runs/`), at the pre-rebase `9b9e4301` (`c87bea00` after it), which
the docs and notes commits after it do not touch; the transcripts named below are copied into
`notes/px76/`. The same rows (F1 without its PIT-only machine) passed at the pre-rebase `8dfc0c6b` in `fw1b`, but
F9 (below).

- **F1 the clocks**, 11 machines: `clock: HPET 10000000 fs/tick, checked against the PM timer` on
  the six with an HPET, `clock: PM 3579545 Hz` on the four with `--no-hpet`, and `clock: PIT
  1193182 Hz` on OVMF under `-machine acpi=off` (its XSDT holds only BGRT: no HPET table, no FADT);
  the tick calibrated by the same source each time: HPET 62,460,659-62,464,345 Hz, PM
  62,188,668-62,194,346 Hz, PIT 62,194,382 Hz at divide 16 (QEMU's 1 GHz / 16 = 62.5 MHz: the
  HPET's reads 0.06% low, the PM timer's and the PIT's port reads cost more under TCG, 0.5% low);
  20 ticks in 150-300 ms by a reference read independently on every one: the PM timer, including
  `--no-pit` and `--no-hpet --no-pit` (the PIT-less machines) and `-m 8G`; on the PIT-only machine
  the HPET at 0xfed00000 read directly (`metal: 20 ticks took 194669730 ns by the HPET read
  directly`). `notes/px76/f1/`.
- **F2** COM1 present and absent on both firmwares: the probe says which; the absent UART's
  receive setup returns (the drain bounded, `05a27531`) and makes no input.
- **F3** each reboot way alone ends the machine, logged first: `reboot: FADT reset register`
  (q35's register is I/O 0xCF9, value 6), `reboot: port 0xCF9` (entered there),
  `reboot: triple fault` (entered there); `poweroff: ACPI S5 types 0/0` (q35's `\_S5`), QEMU exiting
  0 on every one; never `did not power down`.
- **F4** a 16-pixel framebuffer with a 68-byte pitch and red at shift 0 draws where the masks say;
  a 60-byte pitch and overlapping masks are refused.
- **F5** with no UART and no heap, the early panic's two lines read back from QEMU's screendump
  pixel for pixel: 7,552 glyph pixels at 1280x800 (1x), 30,208 at 3840x2160 (2x), the machine
  halted in `pax_halt`.
- **F6** MSI on real QEMU functions: `msi: 1033:0194 64-bit capability at 0x70, 16 messages
  offered` (NEC xHCI), `8086:2922 64-bit …, 1` (q35's ICH9 AHCI), `8086:3420 32-bit …, 2` (ioh3420:
  the layout kasumi's AHCI has); each enabled with one message, the address and edge data read
  back, INTx off, then MSI off again.
- **F7** the USB suite twice: `PAX_USB_IRQ=msi` (`nec-usb-xhci,msi=on,msix=off`: `xhci 1: ports 8
  MSI vector 80 …` on every boot) and `PAX_USB_IRQ=intx` (`msi=off,msix=off`: `xhci 1: ports 8
  INTx 11 …`); each time its 18 rows against Linux's recording (`notes/px74/linux.rows`) on root,
  hub and nested topologies, BIOS and UEFI, delay 250.004 ms and period 30.000 ms, and its
  invariants. `notes/px76/f7/`.
- **F8 kasumi's shape**, UEFI with no COM1, no PIT, the NEC xHCI on MSI only behind OVMF's 64 GiB
  window (`--high-bar`) and a 3840x2160 GOP. First F6's witness with an NVMe controller beside the
  xHCI: `bar: 1033:0194 BAR0 64-bit 0x0000001010000000`, `bar: 1b36:0010 BAR0 64-bit
  0x0000001010004000`. Then the console probe: its 18 USB rows against Linux's, the transcript
  read from PAX's memory through QMP (5,629 bytes), the screen saved
  (`notes/px76/f8/screen-3840x2160.png`), and these lines held: `xhci 1: BAR0
  0x0000001000000000`, `xhci 1: ports 8 MSI vector 80 …`, `clock: HPET 10000000 fs/tick, checked
  against the PM timer`, `timer: LAPIC calibrated by HPET …`, `screen: 3840x2160 32 bpp pitch 15360
  … font spleen 8x16 at 2x, 240x67 cells`, `console: com1 absent, …`. `notes/px76/f8/`.
- **F9** `tests/mpx2-interrupts` and `tests/mpx2-sched` whole, with `--no-hpet` on both firmwares
  and, on UEFI, `--no-pit` and both: every row passes. On BIOS the PIT-less variants are not run:
  SeaBIOS leaves its `Booting from DVD/CD..` unfinished on a PIT-less q35, so the kernel's first
  line is glued to it and I2's exact first line cannot match (`e68e2905`; red in `fw1b`, the
  firmware suite's only red there).

### Plants (contract item 8), red by name

Each is one commit on `ec38768a`, before the rebase (`84f6e008` after it), the branch's last code and
docs commit then (the notes commits after it change nothing a suite reads; `plants/cut.sh`'s
shape: the plant alone, the worktree untouched), pushed as `px76-plant-*` and opened as a draft PR on the px76 branch, so its run is the
planner's `tier pr` for the plant's one path. Both were first run locally in copies of the tree
(`/mnt/steamlib/lanes/px76/plant-{msi,hpet}/`, logs `runs/plantmsi.log`, `runs/planthpet.log`):

- **The MSI data word with the trigger-mode bit set** (`kernel/msi`'s `data`, `| 0x8000`):
  `FAIL METAL MSI edge fixed data`, then `mpx6-firmware: FAIL F6 native bios: MSI layouts exit 35`.
  The contract predicted the keyboard suite would stall on the MSI-only leg; under QEMU 8.2's TCG
  it does not: the level-triggered fixed message is delivered as an edge one would be, and
  `PAX_USB_IRQ=msi tests/mpx6-usb --topology root` passes its 18 rows with the plant in
  (`plantmsi.log`'s second step). F6's read-back row is the gate that sees it. CI: draft PR #233
  (`px76-plant-msi`, `de26eda8` on the pre-rebase `ec38768a`), run 40828277795: red in `mpx6-firmware` alone, by name (`FAIL METAL MSI edge fixed data`,
  `mpx6-firmware: FAIL F6 native bios: MSI layouts exit 35`).
- **The HPET's period taken as nanoseconds** (`kernel/clock`'s `now_ns`, the femtosecond divisor
  1): `clock: HPET 10000000 fs/tick read 9968790000000 ns across 10 ms of the PM timer; refused`,
  `clock: PM 3579545 Hz`, then `FAIL METAL firmware bios-hpet: the tick was not calibrated by the
  HPET`. The contract predicted the rate row; the clock's PM check (`db3ae0aa`) refuses the HPET
  first, so the row that names it is the calibration's source. `mpx2-interrupts` and `mpx2-sched`
  pass with the plant in (`planthpet.log`): no kernel's tick storms, so the plant's ALL-suite
  `tier pr` run (R-px76-8) was predicted red in `mpx6-firmware` alone; V4 saw it too. CI: draft PR
  #234
  (`px76-plant-hpet`, `17efb01c` on the pre-rebase `ec38768a`), run 40828281531: red by name in `mpx6-firmware` (`clock: HPET 10000000 fs/tick read 9964530000000
  ns across 10 ms of the PM timer; refused`, `FAIL METAL firmware bios-hpet: the tick was not
  calibrated by the HPET`) and in `mpx3-screen` V4 (the refusal's line carries a measurement, so
  the screen and screenless boots differ in it: `9960340000000` against `9956400000000`), and in
  `kernel-as` K5, the branch's own clef gap then (below), not the plant's.

### The rest at the head (`final`, `inst2`)

- **The serial-less halt** (`tools/qemu-halt --no-serial`, `123f670f`'s quoting): `kernel/kmain.lu`
  on UEFI with `-serial none`: `qemu-halt: HALTED in pax_halt (… serial still at 547 bytes …)`, its
  11 lines read from `pax_serial_log` through the monitor's `memsave`, from `PAX first light` to
  `halt` (`notes/px76/noserial/kmain-uefi.transcript.log`). Before the quoting fix the monitor
  parsed the file name as an expression (`invalid char 'm' in expression`) and the installer's
  serial-less row timed out at 1200 s (`runs/inst.log`); that is why it is quoted.
- **The installer's serial-less row** (`tests/mpx6-install --only noserial`, CI's all tier):
  the smoke rows first (`inst2`'s first step, every row passing, to build the inputs at the head),
  then OVMF with `-serial none`: `PASS I-install-no-vdb … 19.83s`, the oracles, the tree, the boot
  files, the log ranges and `I-session-uefi`, then `PASS I-noserial: the unattended install with no
  serial port, its transcript from PAX memory, the target verified and booted`. The transcript
  (237 lines, 16,439 bytes, `notes/px76/noserial/install-uefi.transcript.log`) says `console: com1
  absent` and `INSTALL-EXIT-0`. (`final`'s own run of this row stopped at its oracle for want of
  `sgdisk` in the base image, after the install itself passed; `inst2` ran in `localhost/px76-ubuntu`,
  the base image plus gdisk, fdisk, dosfstools and mtools, which CI's runner has.)
- **The mpx suites at the head**, native BIOS (`final`'s batch, each exit on a `BATCH` line): all 17
  pass: `mpx1`, `mpx2-frames`, `mpx2-paging`, `mpx2-interrupts`, `mpx2-sched`, `mpx2-heap`, `tour`,
  `mpx3-user`, `mpx3-screen`, `mpx6-blk`, `mpx4-net`, `mpx6-usb`, `census`, `mpx3-speaker`,
  `mpx3-sound`, `mpx6-games`, `mpx5-screen` (`mpx3-orchestra` passed in `broad1`; the
  environment-only suites above are unchanged). `tests/ci-plan` passes (`final`'s second step).
- **Measurements** (`measure.sh`, `x2probe.sh`; `docs/SOURCES.md` has each): OVMF's default 64-bit
  BAR placement, the window, `-m 34G`, the GOP pitches, `acpi=off` per firmware, SeaBIOS's
  PIT-less line, and TCG's x2APIC refusal.

### The rebased head (`verify`, at `da72fbf9`)

`/mnt/steamlib/lanes/px76/runs/verify.log` (copied to `notes/px76/runs/`), kasumi in
`localhost/px76-ubuntu`, after the rebase onto `10a27451`, the shim's deletion and the clef pin
(the commits after it are notes and `kernel/README.md`):

- `tests/ci-plan`: PASS (307 rows); `python3 tests/ci-budgets.py`: every budget passes, px84's
  `mpx6-install` bounds among them (pr 3600 s, full 6600 s, all 10500 s against their floors).
- `tests/kernel-as` (the seam wolf copied from as02b's cache, `162cc4b4…`, its runtime the release
  archive's `6b9c4852…`; clef built by `tools/mkclef` at `b71b43f4`): every row passes; K5 on both
  tiers: 17 calls through clef, and the clef kernel byte for byte the GNU-as one (native
  `1865e0b4…`, 3,174,528 bytes; release `60eacc6c…`, 2,463,288 bytes).
- `tests/mpx6-ahci --tier native --rows pr`, BIOS and UEFI: A0-A10, A13 and A14 pass on both (A11
  and A12 are the full tier's). A13: `clock: HPET 10000000 fs/tick, checked against the PM timer`,
  `ahci0: 8086:2922 at 00:02.0 port 0: sda model "QEMU HARDDISK" serial "PX75B-NOPIT" …`, the
  session ran. A14: `clock: none: the HPET, the PM timer and the PIT do not advance`, then
  `ahci0: 8086:2922 at 00:02.0: refused: no clock advances (HPET, PM timer or PIT), so no AHCI wait
  could end` and the same for `ahci1` at 00:1f.2, `disk: no virtio block device among 6 PCI
  functions`, `halt`.
- `tests/mpx3-screen --tier native --firmware both`: PASS, V4 on BIOS and UEFI (436 lines).
- `tests/mpx6-firmware --tier native --firmware both`: F1-F9 pass.
- `tests/mpx6-install` (the pr rows, with px84's) and `--only noserial`: PASS (`I-noserial`).
- `tests/mpx5-clef` (the pin selects it): Q1-Q5 pass on all four legs, the package built at the new
  pin (`usr/bin/clef d11d60f0…`); Q0 and QT need the Linux side's container engine
  (`linux-tree: no container engine`), which the rootless container does not nest: CI's.

### The first `tier all` run (40832410617, at the pre-rebase `f4fd3449`)

Two reds were the branch's; the plants' runs carried the same two because they sit on it.

- `mpx3-screen` V4 on UEFI, both tiers: `the serial differs: 3c3|< acpi: XSDT OEM BOCHS  length
  84|---|> acpi: XSDT OEM BOCHS  length 76|20d19|< acpi: BGRT OEM INTEL  length 56|`. Read in full
  from the run's `pax-mpx3-screen` artifact, those are the only two differences on either tier:
  the screen boot's OVMF has a GOP and installs a BGRT, the screenless one does not. Every local
  run of `mpx3-screen` had been native BIOS (`broad1`, `fw1b`, `final`), where SeaBIOS's tables do
  not change, so the UEFI legs were never run here. Fixed by R-px76-9 A (`466ebfec`); on the
  artifact's own logs the new comparison passes on both tiers and firmwares (436 lines), and a
  changed `clock:` line, a changed FACP length or a missing XSDT line are each named in its diff.
  At the pre-rebase `e42d2e39` (kasumi job `ka`, `runs/ka.log`) `tests/mpx3-screen --tier both
  --firmware both` passes every row, V4 on all four legs (436 lines; BIOS `fa75de06…`, UEFI
  `59e0da3f…`).
- `kernel-as` K5, both tiers: `clef: Assembly(Failure { … file: ../boot/io.S, line: 86 … reason:
  unknown_mnemonic inw … })` (the run's `pax-kernel-as` artifact, `native/K5/build.log`). clef,
  built here by `tools/mkclef` at `user/clef.pin` (`runs/clefprobe.log`), assembles every other
  `boot/*.S` and refuses three mnemonics the branch added: `inw`, `outw` and `xorq`; each other new
  construct (`subq $16, %rsp`, `movq %rax, (%rsp)` and `8(%rsp)`, `lidt (%rsp)`, `int3`, `jmp` to a
  global, `xorl`, `movzwl`) encodes as GNU as encodes it. `xorq` is replaced (`4935e753`); `inw`
  and `outw` are kept (R-px76-10). In `ka`, `tests/kernel-as` at `e42d2e39` failed K5 alone on
  both tiers (at `inw`); on a scratch copy with only those two instructions spelled as GNU as's
  bytes (`/mnt/steamlib/lanes/px76/pax-k5bytes`, never committed) every row passed, the clef kernels
  byte for byte the GNU-as ones (native `b964845a…`, 3,122,696 bytes; release `a25142cc…`,
  2,454,272 bytes): the two word ports were the only gap. R-px76-10 was ruled A: clef#10 (as02c)
  added `inw`, `outw` and `xorq` at clef `b71b43f4`, with this `boot/io.S` as its fixture, and
  `user/clef.pin` moves there (`e9cf674b`).

### Follow-ons (for the orchestrator to file or drop)

- kernel/apic's x2APIC MSR path (R-px76-7) has no QEMU witness on CI's QEMU 8.2.2 (TCG refuses
  the CPUID bit); its first run is a host that offers it (KVM, a newer QEMU if its TCG does, or
  px77's boot). `PAX_METAL_X2APIC=1 tests/mpx6-metal` is the leg to run there.
- The MSI plant shows TCG delivering a level-triggered fixed message as an edge, so no keyboard
  stall witnesses the trigger bit under QEMU; F6's read-back is the only gate. A metal boot's
  keyboard is the first place a wrong trigger mode would show.

## Done-when

- [x] Items 1-7 in code, each behaviour a QEMU row in `tests/mpx6-firmware` (F1-F9), the
  installer's serial-less row and the all tier's typing and high-BAR legs in CI.
- [x] The Codex lane's uncommitted work read, finished and committed in one-line chunks; its plant
  workflow set aside (above).
- [x] `tools/ci-tiers.map` and `tests/ci-plan` carry px76's paths; the planner's proof green.
- [x] README and `kernel/README.md` refreshed (README-only commits); `docs/SOURCES.md` cites each
  specification.
- [x] Two plants red by name locally and in CI (above), draft PRs #233 and #234 on the px76 branch
  before the rebase (their diffs are stale against the rebased branch; their runs are read).
- [x] The PR, #236: `Footprint: cross-cutting`; each head's run id read once and the audit run once
  at each hand-back (their ids and the audit's last line are in the hand-back, not here). The
  orchestrator labels, watches the full run and merges.
- [x] px75b's `kernel/ahci_clock` deleted (px76 merges second), kernel/ahci on kernel/clock, A13 on
  the firmware clock and A14 the no-clock refusal; clef pinned at as02c's merge, K5 green.
