# px107 — the clock reads forward

The goal: `clock.now_ns` never panics and never jumps. It panicked `overflow ./clock/clock.lu:313` in three TCG
soaks on CI (pax#293), all on a disk leg, when a reading of the HPET's 64-bit main counter came out below the one
before and the wrap branch turned the step back into a delta near 2^64.

The cause, measured (`notes/px107/measure.txt`): QEMU 8.2's HPET answers one 8-byte load of the main counter as two
4-byte reads, the low half first, each taken at its own instant. When the low word rolls over between them, the
reading is 2^32 ticks (42.9 s) ahead, and the next one is 2^32 behind it. At trunk the first moved the clock 42.9 s
forward (every deadline ended that much early) and the second panicked. With the counter put 20 us before a
rollover 50,000 times, one 8-byte load was torn in 14.4% of the crossings under TCG and 0.46% under KVM; the read
IA-PC HPET 1.0a §2.4.7 gives (high, low, high, until the highs agree) in none.

Now `raw()` reads a 64-bit HPET that way; the HPET's check against the PM timer reads the low word alone (one 4-byte
read, which nothing can tear, so a bracket stays one device read wide); and `now_ns` takes a reading of a 64-bit
counter below the last as no time passing, counted, with `previous` left where it was, while a counter narrower
than 64 bits still counts forward across its rollover. Every step's arithmetic is bounded so no overflow check can
fire, and a session kernel prints one line at its end when any reading was refused: `clock: <n> reading(s) of the
HPET taken as no time passing; the first 0x<current> after 0x<previous>, mask 0x<mask>`.

Footprint: cross-cutting (`kernel/clock`, which every suite reads, and the session kernels' end lines;
`kernel/kmain_metal`, `tests/mpx6-metal`).

This pull request is the lane's first item. The others follow in their own: the T1 `tgkill` probe (pax#306), and
CI's DHCP intervals under load and the yew jobs' time limits (pax#308, pax#305).

## 1. Forbidden, and what was read

- **Clean room.** IA-PC HPET 1.0a (Intel, October 2004; sha256 `93d98386…dab6`): §2.3.4 the capabilities, §2.3.8
  the main counter (writes only while halted; reads monotonic), §2.4.7 and its note on 64-bit reads broken into two
  32-bit ones. ACPI 6.5 §4.8.3.3 (the PM timer, as px76 and px85 cite it). QEMU was run, never read: every claim
  about it is a measurement here. No kernel's, emulator's, firmware's or driver's source.
- **Hosts.** Linux host 1 (Intel Core i7-12700KF) in an Ubuntu 24.04 container (QEMU 8.2.2, the CI runner's
  release), behind each block's two lock names or a light slot; the build Mac for git and CI logs. The metal target
  was never touched.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `db516c69` (pax#313 merged) | `git rev-parse origin/trunk` |
| the witnesses | 41805401996 (`efe12e51`), 42055543811 (`411fc9f5`, `chk-soak-user` on the root-on-disk leg), 42403298471 (`db516c69`, `rights-soak`, the AHCI job, attempt 1) | the job logs; attempt 1's artifact `13587797526`, whose serial log ends `PANIC overflow ./clock/clock.lu:313` after `clock: HPET 10000000 fs/tick, checked against the PM timer` |
| raw() at trunk | one 8-byte load, `mov (%rax),%rax` | objdump of a native `kmain_console` built from a tree whose `kernel/clock` is trunk's |
| the spec | IA-PC HPET 1.0a, `93d98386…dab6` | read twice (the PDF and its text) |

## 3. Prediction, scored

`notes/px107/prediction.txt`, committed first (`e5cafb13`, 23:13Z); the measurement began 23:16Z.

| predicted | measured | score |
|---|---|---|
| (A) the read is torn; the backward reading 2^32 behind; a forward step of 2^32 before it if the device reads the low half first | the forced crossings: torn 14.4% (TCG) and 0.46% (KVM) of one 8-byte load; every torn reading has the new high word and the old low word (ahead by 2^32), the next one 2^32 behind it | right |
| not (B) a reset, not (C) another cause | no reading of another shape in any boot | right |
| the soak: 0 or 1 backward readings in 20 or more | 0 in 24 on the ISO leg (3,317,691 readings); the disk-leg rate is unmeasured, and the three CI witnesses were all disk-leg soaks on loaded runners | right |
| the hammer: at least one under TCG | 0 in 13 rollovers (510,877,436 reads, 1.17 us apart: about 6% a rollover, none 42% of the time) | wrong |
| at least one under KVM | the hammer's KVM boot refused the HPET (the PM timer measured instead); the forced crossings tore 232 times under KVM | right, by the forced test |
| raw() reads high, low, high; now_ns takes a reading behind as no time, `previous` kept; the bounds | so, and the check's bracket reads the low word alone (not predicted: the §2.4.7 read is three device reads, which would widen a bracket past its 10 us under KVM) | right, and one change more |
| the backward row red at the rows' commit: `PANIC overflow ./clock/clock.lu:<elapsed's line>` | `clock-behind` at the rows' tip `df3ab92e`: `PANIC overflow ./clock/clock.lu:406` (elapsed's sum, moved from 313 by the test words above it), BIOS and UEFI, KVM and TCG; green at the head (`1 reading(s) taken as no time passing`, the clock read 33054390, 33054390, 231122330 ns) | right |
| (not predicted) the torn read as a row of its own | `clock-torn` at the rows' tip: 2,351 of 20,000 crossings torn under TCG, 945 of 19,999 under KVM; at the head 0 under both | red first, then green |
| clock-32 and clock-pmwrap green at both | green at the rows' tip and at the head, BIOS and UEFI, KVM and TCG; the largest steps read exactly (2^32 - 1 ticks of the HPET as 42,949,672,950 ns; 2^24 - 1 of the PM timer as 4,686,968,595 ns) | right |
| under 2 KiB of ELF a tier | at the head's code `cec3efda`: native +7,520 bytes (.text +3,104), release +8,648 (.text +6,864); +102,896 in release at `c799aa59` (§3.1) | wrong |
| no existing row moves | F1's other legs (mpx6-metal), mpx2-interrupts, mpx2-sched and mpx6-nmi's release tier on BIOS (N0: each injection point one symbol) green at the head | right |

### 3.1 The kernel's size

`kmain_console`, built at the base and at the head (`tools/build-kernel`, Linux host 1, wolf 0.2.35):

| head | tier | bytes | .text |
|---|---|---|---|
| `db516c69` (base) | native | 3,534,824 | 1,725,771 |
| `c799aa59` | native | 3,542,320 (+7,496) | 1,730,427 (+4,656) |
| `cec3efda` (the head's code) | native | 3,542,344 (+7,520) | 1,728,875 (+3,104) |
| `db516c69` (base) | release | 2,640,248 | 1,485,867 |
| `c799aa59` | release | 2,743,144 (+102,896) | 1,591,883 (+106,016) |
| `cec3efda` (the head's code) | release | 2,648,896 (+8,648) | 1,492,731 (+6,864) |

By symbol (`nm -S`, base against head):
- **Native** (+4,701 of it the clock's own symbols): the fix's code, `hpet` (the §2.4.7 read) 780, `now_ns` +629,
  `report` 456, `hpet_low` 160, `refuse` 123; and the test words, which the native tier keeps in every kernel that
  uses the clock, as it keeps px85's: `test_crossings` 1,736, `test_rollover_in` 436, `test_skip` 87, `reading` 73
  and a few accessors. `test_crossings`, the torn-read row's loop, now lives in `kernel/kmain_metal`, the one kernel
  that runs it (`5e0b232d`); what stays in the clock are the words that reach its own state.
- **Release** (the clock's own symbols +410 net: `report` 2,515, `raw` 500, `now_ns` +252, `start` -2,171 as LLVM
  inlines differently into it; the test words dropped as dead): the other ~101 KB is no clock code. LLVM's inliner
  now inlines `log.hex` (and, after it, its 16-digit loop, unrolled) and `log.put` at most of their call sites across
  the kernel: calls to `log.hex` fall from 278 to 117, to `log.put` from 2,032 to 1,470, and calls to
  `serial.put` rise from 3,916 to 8,882. The largest movers are `interrupts.fatal` +6,840, `user.serve` +6,026,
  `net.report` +4,394, `ahci.controller` +4,291 and `fb.report` +3,867, each one's `log.hex` calls expanded in
  place. The change is not tied to any line that runs: the rows' first commit alone (`52fcd86d`, the clock's test
  words, none of which writes a line and all of which the release tier drops as dead) gives 2,853,896 bytes (calls
  to `log.put` 567, to `serial.put` 18,151), and every commit after it lands between that and the head. The release
  tier's inliner answers the module as a whole, so adding functions anywhere can move its choices elsewhere; wolf
  has no attribute to hold `log.hex` or `log.put` out of line (only `consttime`, whose barrier is not for this).
  tests/mpx6-nmi's N0 (each NMI injection point one symbol of the release kernel) holds at the base, at
  `52fcd86d`, at `576060c8` and at `c799aa59`.

  The release kernel at each commit of the change (`tools/build-kernel --release`, the same host):

  | at | bytes | against the base | calls to `log.hex` |
  |---|---|---|---|
  | `db516c69` (base) | 2,640,248 | | 278 |
  | `52fcd86d` (the rows' test words) | 2,853,896 | +213,648 | 170 |
  | `3f1f012d` (the §2.4.7 read) | 2,764,312 | +124,064 | 281 |
  | `69c3f2ba` (now_ns) | 2,873,904 | +233,656 | 107 |
  | `576060c8` (kmain_console's end line) | 2,743,144 | +102,896 | 117 |
  | `c799aa59` | 2,743,144 | +102,896 | 117 |
  | `cec3efda` (the row's loop moved out) | 2,648,896 | +8,648 | |

  It goes up and down with commits that add no call on any path the boot runs, so no one commit causes it; at the
  head, the torn-read row's loop moved into `kmain_metal`, it is back within 9 KB of the base (.text +6,864).

## 4. Evidence index

Every take ran on Linux host 1 in the Ubuntu 24.04 container (QEMU 8.2.2), behind a block's two lock names or a light
slot; the records are kept in the lane's directories.

| record | what | at |
|---|---|---|
| m1 | 24 rights soaks (TCG), the hammer (TCG, KVM): `notes/px107/measure.txt` items 2 and 3 | the measure kernel `6339ae92` |
| m2a, m2 | the forced crossings, TCG and KVM, twice: item 1 | the measure kernel `63954e10` |
| r1 | the first rows' take: `clock-behind` red by name (`PANIC overflow ./clock/clock.lu:401`); two bugs of the rows' own found (the step lines' doubled `0x`, the crossings' 64 reads too few under TCG), so the rows were rebuilt | `4f10b56b`, superseded |
| t2 | red at the rows' tip, BIOS and UEFI, KVM and TCG: `clock-behind` and `clock-torn` red, `clock-32` and `clock-pmwrap` green; at the head two more rows' bugs (the behind row's grep against the serial CR; `clock-32` under KVM met pax#314, its HPET refused) | `df3ab92e`, `c799aa59` |
| t3 | green at the head after both fixes: every clock leg on BIOS and UEFI under KVM and TCG (`clock-torn`: 0 of 20,000 crossings torn under either), F1's other legs, mpx2-interrupts, mpx2-sched, mpx6-nmi release BIOS (`PASS N0 release: every injection point is one symbol in the kernel (7 points)`) | `cec3efda` |
| sz1, bs1, bs2 | `kmain_console`'s size at the base and the head, and the commit that moves the release tier's inlining (§3.1) | `db516c69`, `c799aa59`; `52fcd86d`, `69c3f2ba`, `3f1f012d`, `576060c8` |
| the final records | red at the rows' tip and the plant red by name; green at the head | the PR's head |

## 5. Done-when

### 5.1 Rulings

- **R-px107-1, the cause: (A), measured.** The torn read, the low half first (`notes/px107/measure.txt`).
- **R-px107-3, a reading behind the last: no time, `previous` kept (recommended, implemented).** (a) the counter's
  high-water mark: an isolated misread costs nothing, and the clock never moves back; (b) `previous` moved to the
  misread: the next good reading would count the misread's distance again, a forward jump; (c) (a) until a second
  reading in a row is behind, then (b): covers a counter that restarted, at the cost of a branch no witness needs.
  With the §2.4.7 read nothing tears, so (a). A counter that restarted would hold the clock until it passed its old
  reading again; the end line says so if it ever happens.
- **R-px107-4, a step past what the clock can hold: no time, counted (recommended, implemented).** A step whose
  nanoseconds would carry `elapsed` past 2^64 - 1 (584 years) comes only from a misread of a 64-bit counter (all
  ones from an absent device, say): taken as no time passing and counted with the readings behind, never a panic.

### 5.2 Issues

- Filed: pax#314, under KVM on a loaded host the HPET's check against the PM timer can refuse the HPET (2 of 4
  `kmain_console` boots here; CI runs TCG, where it does not show).
- Closed: none (pax#293 is the orchestrator's to close at the merge).

### 5.3 Checklist

- [x] clock-behind and clock-torn red at the rows' tip, green at the head (BIOS, UEFI; KVM, TCG)
- [x] clock-32 and clock-pmwrap green at both
- [x] F1's other legs (mpx6-metal) green at the head
- [x] mpx2-interrupts, mpx2-sched, mpx6-nmi (release, BIOS) green at the head
- [x] tests/ci-plan
- [ ] the final records at the head: green, and the plant red by name
- [ ] the PR's tier pr (every suite: `kernel/clock/*` is ALL in `tools/ci-tiers.map`), then `full-matrix`
