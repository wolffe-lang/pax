# px127 (follow-up) — the NMI suite's frames point, which the release tier may inline

After `211e5c7c` (recvmsg on a datagram socket) trunk's tier-all run went red in `mpx6-firmware` (run
43168648483): `mpx6-nmi: FAIL N0 release: injection points that are not one symbol in …kmain_console.elf:
frames.start(0)`, then `FAIL F11 release`. The same job was green at `48ea81ba`. No pull request run builds the
release tier's mpx6-nmi, so the branch's own records never saw it.

## 1. The cause (measured before this file)

On the release kernels of `48ea81ba`'s tree and `211e5c7c`'s, built by `tools/build-kernel --release` from
`kernel/kmain_console.lu` with `kernel/wolf.pin`'s wolf 0.2.35:

| | `_Wframes.start$…` in the ELF (nm) | defined in wolf's IR (`--emit=llvm-ir`) | calls to it in the IR | `_Wframes.init$…` |
|---|---|---|---|---|
| `48ea81ba` (2,835,296 bytes) | 1 | yes, `define internal` | 1 (kmain's) | 1 |
| `211e5c7c` (2,810,840 bytes) | 0 | no | 0 | 1 |

wolf's own mid-end inlined `frames.start` into its one caller before LLVM saw the module. `frames.start` is
`init()` and three named panics, a single-use callee small enough for the inliner's single-use budget, so it is
inlined exactly when it is in, or is imported into, its caller's codegen cluster. The release tier partitions
the call graph into clusters by size and imports bodies under a per-cluster budget; the new socket code changed
the sizes, the partition moved, and about fifty functions across the kernel were inlined that were not before
(and about forty the other way), `frames.start` among them. That is also why the release kernel shrank by
24,456 bytes. Nothing in `frames` changed, and nothing was lost that the kernel promised: wolf has no attribute
that keeps a function out of line, and `frames.start` never had one.

So the fault is the row's choice of point. Its own header already names the case: `pci.scan` went the same way in
pax#252's run and the suite moved to `pci.scan_bus`, the walk itself, which calls itself and so is never inlined.
`frames.start` is `frames.init`'s one-call wrapper: a breakpoint at `frames.init`'s entry is the same moment of
the boot (start does nothing before it calls init), and `init` is far over any inline budget (about 1,550 lines of
IR against `start`'s 300), one symbol in both tiers at both heads.

## 2. Prediction

- **Red first.** At trunk `9ba58558`, `tests/mpx6-nmi --tier release` stops at N0 with `frames.start(0)` before any
  boot.
- **The fix.** `tests/mpx6-nmi` names `frames.init` where it named `frames.start` (N1 and N2), the header saying
  why; N0 prints `FAIL N0 …` at column 0 and exits 1 (a row's red, not a tool error).
- **Green.** At the head, release and native: N0 PASS (seven points), every N1 row survives and every N2 row is a
  named machine-check panic on both firmwares, under KVM.
- **The plant** (`frames.start` named again in N2): `FAIL N0 release … frames.start(0)` by name.

## 3. Evidence and done-when

The records are the pull request's: red at `d5924c9d` (N0's row at column 0, the point unmoved), green at the
head (release and native tiers, both firmwares), and the plant `px127-plant-nmi-start` red by name; each record's
sha256 and every `END` line are in the body. Footprint: cross-cutting (`tests/mpx6-nmi`, which the tier-all run's
`mpx6-firmware` runs as F11).

- **R-px127-8, where the fix belongs: the suite.** (a) The row names `frames.init`, as it named `pci.scan_bus`
  after pax#252, recommended and done; (b) keep `frames.start` out of line in the kernel: wolf has no attribute for
  it, and `#[consttime]`'s barrier would bind a contract the function does not mean; (c) change wolf's inliner: it
  works as designed. The other single-call points (`serial.init`, `paging.switch_to`, `fb.start`,
  `initramfs.report`, `apic.start`) stayed functions at both heads; N0 names any that a later partition inlines.
