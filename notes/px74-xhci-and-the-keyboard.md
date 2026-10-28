# Drive xHCI USB boot keyboards

_Materialised from the body of pax#219 at the merge (`5f66f694`)._


## Forbidden

No Linux, BSD, firmware, hypervisor or USB driver's implementation source read. Written from xHCI 1.2, USB 2.0/3.2, HID 1.11 and the HID Usage Tables, cited in `docs/SOURCES.md`. Linux is an unmodified binary guest; the probe includes only installed uapi declarations. No hardware configuration writes, metal boot, attribution trailers, labels, merge or release.

## Inputs, verified

Launch base `187aafdf`; rebased exactly once onto `dd87163e` (px73 at `c4d2b3c0` plus its materialised note). Kernel and assembly sources are unchanged from the validated `049f5cad` head. Both USB launchers and CI groups are retained, with USB-keyboard replay after the USB-stick steps. Rebased planner, matrix guards, USB launcher/fetch tests and a mocked combined stick+nested-keyboard launch pass; records are `/home/mfwolffe/lanes/px74/runs/rebase-check.log` and `/home/mfwolffe/lanes/px74/runs/rebase-combined.log`. Kernel compiler: wolf 0.2.35, `cf0c13d38479f444b69bb8356ad5709d07eff323`; cached archive SHA256 read twice: `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a`. QEMU 8.2.2/TCG in the existing Ubuntu container; kasumi cores 12–15 under its lock. No Mac builds. The validated snapshot's source hashes were matched against the worktree before committing the hardening.

- `11c9ba2f`: prediction before implementation.
- `0d44bb92`, `b6b50144`: six HID usages and one shared USB/PS2 key mapping.
- `fca3a4ea`, `f210c816`: controller/rings, hubs, hotplug, repeat and ownership/timeout/DMA hardening.
- `9d74c3a8`: additive QEMU USB keyboard topologies; boot-disk parsing unchanged.
- `21c299fc`, `973d1c87`, `9122b446`: Linux differential, hotplug, ring wrap, undriven SuperSpeed device and every Shift+arrow.
- `ad55f5f0`: hardware gate and existing typing-suite USB replays in CI.
- `7b14eef5`, `3a12e5f9`: firmware image reuse; refuse counting one supplied image as two compiler tiers.
- `9b429068`, `3f072786`, `48ee0eaf`: original sources, README and evidence.
- `23f53fbf`, `bcb86d8d`: build each kernel/tier once; enforce all distinct matrix legs, cache-tier identity and failure propagation.
- `151cae52`: isolate the shared pure invariants and consolidate diagnostic loops.
- `ba531273`, `bd3b9e84`, `5f66f694`: updated documentation and cold-build/IR evidence.

Dispositions received from the orchestrator, not decided by the lane:
- **R-px74-1:** INTx (B), as the current PCI/APIC transport supports; MSI/MSI-X follows.
- **R-px74-2:** enumerate/log SuperSpeed devices; drive USB2 keyboards and hubs only.
- **R-px74-3:** no mass-storage driver here; the live payload rides in the initramfs.
- **R-px74-4:** use Linux's measured 250ms/33ms settings, not the contract's “33 cps”; carry fractional ticks.
- **R-px74-5:** px76 owns the interrupt route on metal before the target keyboard is called ready.

## Prediction

`notes/px74-prediction.txt` is the pre-change record. QEMU exposes no legacy ownership capability under either firmware; no semaphore exchange occurred. Root and two-deep hubs enumerated on their first boots, contrary to the predicted hub debugging need. The native BIOS root raw-input witness records first key-to-read latency **0 ticks at 10ms resolution**, not zero elapsed time.

Linux `EVIOCGREP` reports 250ms delay / 33ms period. Corrected observations: delays **253.509–257.321ms**, median periods **33.984–34.004ms**. PAX uses 250/33ms on its 10ms clock: alternating 30/40ms intervals, example mean **33.182ms**, not fixed 30ms repeats.

Two harness errors were rejected rather than recorded as parity: HMP's held-key timer delayed hotplug input on both guests, so the gate now uses explicit QMP transitions and independently requires **b then c**; Linux dropped 6ms ring-wrap pulses, so injection now allows 20ms per transition and independently requires all **300** keys.

## Evidence index

**Release-time correction, current head:** [performance record and per-function censuses](https://github.com/wolffe-lang/pax/blob/049f5cad408bcb4531352bd40b5ddc0f12f3950b/notes/px74/performance/README.txt). Cold `--no-cache --release --emit=obj` builds on the same four kasumi CPUs: trunk invariant control **165.148s**, old USB invariant kernel **321.787s**, final isolated invariant kernel **0.920s**. The actual console is **210.332s versus trunk 227.117s**, near trunk rather than a statistically established speedup. The control adds only the test entry/pure helpers to trunk because trunk has no USB invariant entry.

The invariant kernel now uses the exact shared production helpers without importing the OS dispatcher/driver. Diagnostic formatting is factored out of branch-heavy attachment and transfer paths: console IR attachment setup changes from **49 loops/249 conditional branches** to **4/87**, control from **20/97** to **9/65**; diagnostics remain in smaller callers. Full per-function CSVs preserve all counts. No compiler optimization flags, pin, or CI timeout changed.

The fresh complete matrix passes in **814s (13m34s)**: all sixteen invariants on four compiler/firmware legs and all eighteen hardware rows on twelve legs. Both invariant and console images are built once per tier and reused for firmware runs; existing object/IR/no-SSE assertions remain. New performance-regression plant `9026ca23`, [run 40518531386](https://github.com/wolffe-lang/pax/actions/runs/40518531386), fails in **USB matrix builds once without dropping boots** on six builds versus the required four; `notes/px74/performance/plant-rebuild-ci.log`. The strengthened guard also checks all twelve distinct sessions, wrong-tier cache refusal and build-error propagation.

The records below describe the original feature validation; the performance correction's matrix/transcripts are under `notes/px74/performance/`. Earlier typing records remain identified as earlier-head evidence, and CI reruns typing at this head.

[Complete index, bounds and reproduction](https://github.com/wolffe-lang/pax/blob/049f5cad408bcb4531352bd40b5ddc0f12f3950b/notes/px74/README.txt).

- `notes/px74/final/final-validation.log`, `.inputs`, `.exit`: exit 0; planner, 16 invariants per compiler/firmware leg, all USB topologies and session-entrypoint build. Hashes matched before hardening commits.
- `notes/px74/final/arrow-validation.log`, `.exit`, `arrows/`: exit 0; **18 byte rows × 12 PAX boots**, native/release × BIOS/UEFI × root/hub/nested, compared to the fresh Linux recording. All four shifted arrows, six-key chord, caps, Alt, repeat, hot-unplug held Shift, spare/replug, 300-key wrap and SuperSpeed-not-driven witness. Kernel ELFs are the exact validated ones; the changed probe was rebuilt.
- `notes/px74/linux6/`, `linux.rows`: final Linux oracle. Earlier corrected repeat measurements remain in `linux3/` and `linux5/`.
- `notes/px74/final/{console-sibling,shell-sibling2,pelt-typing}.log` and `.exit`: all 0. Console and shell suites, plus pelt's friendly console rows, run baseline and USB root/hub on native BIOS/UEFI. **Twenty USB keyboard transcripts** independently require positive key counts and zero COM1/i8042 input; copies are under `final/usb-typing-*`. Pelt's full fork replay is CI's existing gate, not a local claim here.
- Linux references were regenerated in **rootless sibling containers**, launched from the host through `tools/linux-tree`; no engine socket or host PID namespace entered the build. The old shell build phase's seven reference-mount failures were narrowly checked, then every reference regenerated before the unchanged gate passed. Recipes are committed beside the index.
- `notes/px74/final/usb-cli.log`: one supplied image cannot count as both compiler tiers.
- Original feature-head clone: `/home/mfwolffe/lanes/px74/verify-head`. The correction's exact final-head clone is `/home/mfwolffe/lanes/px74/perf/final-head`; both `tests/ci-plan` and the strengthened matrix guard pass in `/home/mfwolffe/lanes/px74/perf/final-guards.log`.

Required plants, both **red by name**:
- `75f992e5`, [run 40470752239](https://github.com/wolffe-lang/pax/actions/runs/40470752239), job 122077887897: **FAIL USB hub route first port**; `notes/px74/plant-route-ci.log`.
- `c7ee72f9`, [run 40470754883](https://github.com/wolffe-lang/pax/actions/runs/40470754883), job 122077823787: **FAIL USB boot report sixth key**; `notes/px74/plant-sixth-ci.log`.

`notes/px74/kasumi-xhci.txt` is read-only inspection under Linux: BAR0 **0x485a200000**, 64KiB; PCI 0x3c bytes **ff 01 00 00**; Linux reports MSI(X) IRQ133–140 and INTx disabled. This is **not firmware-handoff evidence**. QEMU INTx success proves no interrupt route on the board.

## Done-when

- [x] Controller, USB2 hubs, boot keyboard and hotplug implemented; one console character/sequence table.
- [x] Both compiler tiers and firmwares, root and nested hubs; Linux differential and independent byte/path assertions.
- [x] Console/shell/pelt typing replays through USB root ports and hubs on both firmwares; CI wiring retained.
- [x] Both required CI plants red; final source/evidence committed; README refreshed; planner green from a clean final-head clone.
- [x] Release build correction measured against trunk, full USB matrix rerun, and compile-count regression plant red; no timeout increase or dropped rows.
- [ ] New-head CI; existing full-matrix label retained, orchestrator watches. No lane CI wait or merge verdict.
- [x] Rebased once after px73 merged; both mpx3-console step groups retained, keyboard replay after stick testing. Existing label left unchanged.
- [ ] Orchestrator materializes `notes/px74-xhci-and-the-keyboard.md` from this body at closeout.

Bounds: four controllers, 32 slots/controller, five hub hops, 31 hub ports, one boot keyboard interface in the first configuration/default alternate setting, 1024-byte configuration descriptors, low DMA pages, default single-TT hubs. QEMU's full-speed hub transport is tested; high-speed TT parent/inheritance fields have invariant witnesses, not a real high-speed hub test. No LEDs, USB storage, SuperSpeed class drivers or metal validation. No issues filed or closed.

