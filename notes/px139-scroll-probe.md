# Scroll probe samples

Footprint: module. This changes the screen's probe instrumentation and the console's boot line, not its selection policy.

## 1. Boundaries and sources

Only PAX's own source, its recorded QEMU runs and documentation were read. No other kernel, driver or firmware source was used. Every new boot is QEMU; no physical machine, firmware setting or disk was touched.

The starting implementation already warms a read and write, then takes the minimum of five costs of each (`c77d8f70`, November 3). The earlier account of issue #409 as one sample was wrong. This change keeps that policy and the `fbread` and `fbwrite` overrides.

## 2. Prediction and implementation

The prediction was committed before the changes in `notes/px139-prediction.txt`.

The first attach keeps every cost it compares, in acquisition order. The boot line adds `minimum of 5 samples`, the five reads, the five writes and the elapsed window in cycles and calibrated microseconds. The window spans the five timed pairs and bookkeeping, excluding the warm-up. Integer microseconds round down. Reporting reads retained state, not the framebuffer. The later attach under PAX's page tables neither probes again nor changes the decision.

The minimum discounts an isolated added delay without changing the hardware-dependent threshold. It does not reject a whole window of slow reads. Test-only cost injection enters the existing reduction after actual framebuffer I/O: one first read of 1000 among four of 100 chooses copy; five reads of 1000 choose redraw against five writes of 100. The log explicitly names injection. The two overrides bypass it, and a machine with no display reports no probe.

## 3. The hosted event and the mask

The artifacts of [job 131845805614](https://github.com/wolffe-lang/pax/actions/runs/43411746963/job/131845805614), `mpx6-firmware`, show:

| Fact | Plain boot | Triage boot |
|---|---|---|
| Kernel | `22f0860b`, ELF SHA256 `d5096319e00e8114129eae7c2ffedd590309b066bacb6be03f501b20d78b9939` | same |
| Firmware path | OVMF, UEFI64, Ubuntu EDK II, revision 0x10000; DVD-ROM boot entry 0001 | same |
| Emulator | QEMU 8.2.2, q35, cpu max, 256 MiB, TCG | same |
| Display | VGA with 64 MiB, 1280x800; framebuffer 32-bit RGB, pitch 5120, physical 0x80000000 | same |
| Console grid | 160x50 | 160x37, above the triage band |
| Limine CR3 | 0xbf96000 | 0xbf95000 |
| Initramfs address | 0xbfa6000 | 0xbfa5000 |
| Read minimum, cycles | 67,007 | 15,141 |
| Write minimum, cycles | 13,990 | 13,548 |
| Selected way | redraw | copy |
| Kernel boot time, ms | 3,253 | 3,331 |
| Whole QEMU elapsed time, s | 5.883 | 5.883 |

Each boot has a fresh OVMF variable store. There is no evidence of a different display device, firmware route or kernel. The triage entry installs diagnostic tables and draws its panel before the screen attaches. Its shorter console clears fewer pixels; both grids still leave room for the full 16 KiB probe. Those are differences in preparation, not proof of a cause. The final `wc` mapping in each transcript is PAX's later mapping, not a measurement of Limine's mapping at the first probe.

All five plain reads were at least 67,007 cycles, because that is their minimum. A single isolated descheduling pause would normally charge one interval, not all five: the guest cannot execute the remaining reads while descheduled. The artifacts contain neither individual costs, the window, calibrated TSC frequency nor host scheduling traces. They cannot establish a host stall lasting a particular number of microseconds. A lower bound for the five timed pairs is 404,985 cycles in the plain boot and 143,445 in triage (five times each pair of minima), not the actual window. Converting either to microseconds from these artifacts would invent the missing TSC rate. The equal process elapsed times are too coarse to resolve it.

A longer or spaced probe might sample after a transient condition, but nothing recorded says when that condition ended or whether it was transient. Do not change the default on that assumption. Proposed next experiment: collect the retained samples and window on repeated TCG boots of both shapes, then compare the existing probe with additional measured windows separated by a stated delay, under the same host conditions. Add independent scheduling traces before attributing differences to host stalls. A policy change needs those measurements and a boot-time cost, not the two minima alone.

The serial-console change (#405) masks the old-format probe's selected way in T2. Its expression ends at `x write)`, so it cannot consume this new report. `tests/mpx6-triage.d/probe-mask` extends the same numeric-masked stream for the full new measured reason: exactly five costs each, the minimum statistic, cycle and microsecond units, and no injection. It changes only `copy` versus `redraw`; the rule and report structure remain compared. Forced and injected choices are not masked. On integration with #405, apply this extension after its extracted `mask`, retaining all its fixtures and calibration handling. The two expressions match disjoint old and new formats.

## 4. Evidence

The rows were committed without implementation at `8272a56a`. The recorder's red-first native take on both firmwares produced `FAIL P-plain`, `FAIL P-outlier` and `FAIL P-slow` for absent sample reports; `P-fbread`, `P-fbwrite` and `P-none` passed. Its step ended `END probe-native exit=1 secs=61`.

At `0259dac1`, all six rows passed on BIOS and UEFI (`END probe-native exit=0 secs=37`). The ordinary probe's recorded windows in that KVM check were 10,330 cycles / 2 us on BIOS and 4,474 / 1 us on UEFI. These are different runs under a different accelerator, not estimates of the historical TCG window.

The mask's selftest holds meaningful differences apart: statistic, sample shape, units, injection and overrides. The deterministic boots also validate that the printed minima are computed from the printed samples. The plant changes only the loop bound from five samples to one, on a separate branch. Its named row is `P-outlier`; its record and the final green record are linked from the pull request.

## 5. Completion targets

- QEMU sample rows on native and release, BIOS and UEFI.
- The complete triage suite, including its unchanged fault, no-display and high-resolution paths.
- The screen suite: pixels against the reference renderer, scroll ways, no-read watchpoint and typed sessions.
- The CI planner's own tests; the unchanged assembler seam remains covered by the hosted kernel tests.
- Recorder preflight, every step's END line, and a one-file, one-hunk single-sample plant red by name.
- A hosted release-tier run before merge: firmware suite F10 runs the triage suite and its sample rows; the screen suite covers both scroll paths and the reference pictures.

The README was read against the change and its screen paragraph now names all samples and the window. The historical event is explained only as far as the artifacts support; no cause or improvement from spacing is claimed.
