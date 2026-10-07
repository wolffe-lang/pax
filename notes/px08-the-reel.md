# px08 — the reel (a PAX boot the maintainer can film)

Contract: `sprints/pax/08-the-reel/px08-the-reel.md` in wolffe-lang/wolf
(planning trunk `e51691d`). Branch `px08` off pax `94364ad`; PR pax#11.
The five sections were committed whole in `7387076`, an empty commit
pushed before the first change. This note carries §2's drift, §3
against what was measured, §4 and §5.

## 1. Forbidden

As committed in `7387076`, and kept:
- No Linux, glibc, musl or other kernel's or libc's source was read.
  Read: pax's own tree, Limine 12.9.1's `CONFIG.md`, the lobo reel's
  SHOTLIST (read only). `docs/SOURCES.md` § px08.
- `~/scratch/wolf/lobo-demo` was read, never written; port 8088, the
  wolf-demo tunnel, `~/.cloudflared` and port 8080 were not touched.
- Nothing built on nomad-1: kasumi built every image (`tools/reel
  build`); nomad-1 ran QEMU, the preflight and the rehearsal; hasu ran
  QEMU under KVM through `nix-shell -p qemu python3`.
- No kernel feature added (below), no `region`, no module `var`.
- No issue closed.

## 2. Inputs, verified (drift)

Stated in `7387076`. Two drifts in the contract's inputs:
- **kasumi has no KVM**: no `/dev/kvm`, no kvm module loaded (since the
  2026-10-04 reboot). The contract's "kasumi (KVM and TCG)" became kasumi
  TCG plus hasu KVM.
- **pax is public** (wave-53, 2026-10-06); `CLAUDE.md` still says
  "private until the maintainer says otherwise". Not edited here.

Found while working:
- pax#10 (px06's heap) stayed open (head `bc86ea5`): **the heap stage is
  the next cut** (§ Next).
- macOS's `/bin/bash` is 3.2 and is what `#!/usr/bin/env bash` finds on
  nomad-1; `tools/reel` and `preflight.sh` are written for it.
- `tput cols` inside `$(…)` reads 80 on macOS whatever the window;
  `preflight.sh` asks `stty size </dev/tty`.

## What the reel is

`kernel/reel/reel.lu` holds the stages; `kernel/kmain_reel.lu` (finale
a) and `kernel/kmain_reel_text.lu` (finale b) call them in order:

| stage | heading | the test kernels' path it repeats |
|---|---|---|
| banner | `PAX: a kernel written in wolf` / `wolf 0.2.24, …` | (the version is checked against `kernel/wolf.pin` by R1) |
| 1 | `[1/5] boot: what Limine handed over` | `kmain.lu`'s boot_info lines |
| 2 | `[2/5] frames: …` | `frames.start`, `report`, an alloc/write/read/free round trip (`kmain_frames`) |
| 3 | `[3/5] paging: …` | `paging.start`, `report`; each section's permissions read back from the live tables |
| 4 | `[4/5] interrupts: …` | `interrupts.start`, `apic.start`, `timer.start`, ticks counted 3 s (`kmain_timer`) |
| 5 | `[5/5] threads: …` | `sched.start`, four spinning threads, `wait_all` (`kmain_sched` S1) |
| close | `PAX today: … Next: user mode, then Linux binaries, unmodified.` / `finale in 3... 2... 1...` | — |
| finale a | `PANIC stack overflow thread …` | `kmain_sched_overflow` (S5) |
| finale b | `PANIC page fault vector 14 … cr2 …` | `kmain_text_write` (I1) |

The reel's own code is display and pacing only: headings; `leaf`, a
read-only walk of the live page tables; `pax_reel_worker`, `pax_t_spin`
with a name and one line every fifth run; and the pauses for the
viewer, each marked `PAUSE` at its call. Before the timer interrupt is
live a pause polls the 8254's channel 0 (the counter-latch command),
which `timer.start` has programmed; then `timer.wait`; then
`sched.sleep` on thread 0.

The menu (`boot/limine-reel.conf`) has both finales; `serial: yes`
shows it on the serial console, so a terminal running QEMU with
`-serial stdio` sees it and answers it with the arrow keys and Enter
(rehearsed). `tools/mkimage` learned `--conf` and `--add ELF NAME` for
it; with neither it builds what it built before.

## 3. Prediction against measurement

| predicted (`7387076`) | measured | verdict |
|---|---|---|
| stages: menu, 1-5, the closing line, finale a/b; no heap stage (pax#10 not merged) | as predicted | right |
| nomad-1 TCG BIOS boot-to-last-line 28.7 s | 28.47 s (`notes/px08/nomad1-tcg-bios-pax-reel.times`) | right (−0.2) |
| nomad-1 TCG UEFI 30.0 s | 29.89 s (finale a), 29.88 s (b) | right |
| kasumi TCG BIOS 28.7 s | 28.46 s (`notes/px08/kasumi-tcg-bios-pax-reel.times`) | right |
| KVM (hasu) BIOS 28.6 s | 28.41 s (`notes/px08/hasu-kvm-bios-pax-reel.times`) | right |
| no stage start differs between hosts by > 0.5 s beyond the firmware's offset | headings [1/5]..[5/5]: nomad-1 5.14/8.14/11.14/14.14/19.14, kasumi 5.13/8.13/11.14/14.14/19.14, hasu KVM 5.08/8.09/11.09/14.09/19.08 s | right |
| slowest stage under emulation, pauses excluded: the paging build, < 50 ms | the paging stage's lines land with its heading (same 10 ms stamp on every host); the only stage with a measurable gap is frames: its first line 10 ms after its heading under TCG (nomad-1 8.14 → 8.15, kasumi 8.13 → 8.14), 0 under KVM; paging's lines share its heading's stamp | **wrong**: frames (`frames.start` builds the bitmaps), not paging; both far under 50 ms, at the 10 ms resolution of the stamps |
| UEFI firmware the slowest thing on screen that is not a pause, ~1.3 s on nomad-1 | the kernel's first line comes 1.42 s later under UEFI than BIOS on nomad-1 (6.56 against 5.14 s) | right |

Kernel time: 23.4 s predicted, 23.3 s measured (banner 5.14 s to PANIC
28.47 s on nomad-1 BIOS).

One thing nobody predicted: **the BIOS serial logs are byte-identical on
three hosts and two accelerators.** `pax-reel.iso` under BIOS gives
the serial log `a761e009…` on nomad-1 (TCG), kasumi (TCG) and hasu
(KVM, `~/lanes/px08/h-bios-pax-reel.log`). Every number the reel prints, the thread lines' ticks
included, is the same: the run is paced by the virtual PIT, and the
threads' interleaving is decided by ticks, not by host speed.

## 4. Evidence index

- **Serial logs**: nomad-1 TCG BIOS `notes/px08/nomad1-tcg-bios-pax-reel.serial.log`
  `a761e009…`; kasumi TCG BIOS `notes/px08/kasumi-tcg-bios-pax-reel.serial.log`
  `a761e009…` (identical). Per-line timings beside them (`*.times`),
  plus nomad-1 UEFI finale b and hasu KVM BIOS.
- **Per-scene timings on nomad-1**: `notes/px08/rehearsal-scene2.times`
  (`86cda6cb…`), `notes/px08/rehearsal-scene3.times` (`989e1a65…`); the
  SHOTLIST's table (`demo/reel/SHOTLIST.md`).
- **ISO shas** (kasumi, native, `tools/reel build`, no `.git`, so
  `SOURCE_DATE_EPOCH` 0): `pax-reel.iso` `a41ba883…`, `pax-reel-b.iso`
  `755b433a…`; rebuilt twice from the same sources, same shas. Release
  tier: `d1b4dc62…`, `54277dcd…`.
- **tests/reel, kasumi**, QEMU 11.1.1 TCG, `PAX_REQUIRE_UEFI=1`, both
  tiers and firmwares: 44 PASS, 0 FAIL, 0 SKIP (`~/lanes/px08/reel1.out`
  `2319931a…`). It found its own hole on the way: R4's join check read
  the wrong fields and compared 0 with 0; fixed before the first push
  (the PASS line now prints the counts, 65040 = 65040).
- **Planted red**: `9004374` puts stage 2's heading after its frames
  line. kasumi: R1 FAIL on both ISOs, everything else PASS
  (`~/lanes/px08/plant.out` `bd712531…`). CI: run 37561248505,
  job `reel` 112598767198: R1 FAIL on all eight legs (two tiers, two
  ISOs, BIOS and UEFI; `line 10 not found after log line 25: frames: …`),
  R0 and R2-R7 PASS; every other job green. Reverted in `65db21e`.
- **CI green at head**: the run id is in the PR body (a note cannot name the run of the commit that carries it).

## 5. Done-when

See the PR body. Closes nothing. Next cuts:
- **the heap stage** once pax#10 merges: a `List` and a `Map` built,
  printed, freed, live blocks back to 0 (stage 6/6), with R-rows beside
  it;
- user mode in the closing line becomes a stage when P2's ring 3 lands.
