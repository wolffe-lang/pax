# px85 — the flakes: the HPET check, the key-repeat row, the fetches, the nm shape

Contract: `wolf/sprints/pax/85-the-flakes/px85-the-flakes.md` (crawl 54, wave 1 of 2026-10-31), under
`sprints/the-lane-rules-1031.md`. Base pax trunk `8495bdc0`, the tree that passed tier all only on attempt 3 of trunk
push run 41153232393: attempt 1 refused a correct HPET in F8 (pax#260), attempt 2 saw 6 key repeats where the row
wants 15 (pax#261); PR run 41072978020 lost an hour to one dropped pelt fetch (pax#259); pax#256 is the
`nm | awk … exit` shape px78b fixed in `tools/qemu-halt` and left in the tests. Rebased once, at the orchestrator's
word, onto `0f043f7a` (pax#263, px86). Footprint: cross-cutting (`kernel/clock`, the harness's `tools/`, CI's plan
job).

## Forbidden

No kernel's, firmware's, bootloader's, emulator's or driver's source was read; no awk's, nm's, git's or curl's.
Written from IA-PC HPET 1.0a (§2.2, §2.3.4, §2.4.1; the Intel PDF fetched 2026-11-01, sha256 `93d98386…`), ACPI 6.5
(§4.8.2.1, §4.8.3.3), QMP's documented commands, `git-config(1)`, and QEMU 8.2.2 run as a black box; each is in
`docs/SOURCES.md` (px85's section). PAX's own code and notes were read (px76's, px77d's, px78b's, px83's). kasumi was
never touched (offline: the maintainer is installing PAX on it); hasu's `:9308` and `:9364` servers and the
maintainer's data were not touched; nothing was installed. No label, no merge, no dispatch, no issue filed or closed;
no attribution trailers.

## Inputs, verified

- **Base** `8495bdc0a8b914e407ae6644bad4fd074bb0817f`; rebased once onto `0f043f7a` (px86's merge, pax#263) after
  every batch below had run. The rebase met one conflict, `README.md`'s `tools/` row (px86 added `used-disk` to it,
  this lane `fetch-retry`): both kept. `docs/BOOT.md` merged by git (px86's new section, this lane's clock sentence).
  The rebase moved exactly trunk's files (`git diff` of the old and new heads names only `8495bdc0..0f043f7a`'s);
  `notes/px85/rebase-map.txt` pairs every commit with its twin. Every hasu run before the rebase names its commit
  by the old sha (`wt-<old sha>` worktrees); the gauntlet ran at the rebased head.
- **Clones** `~/lanes/px85/pax` on the Mac (git and `gh` only, no build there) and `/home/mfwolffe/lanes/px85/pax` on
  hasu, a worktree per tested commit, and trunk's own at `8495bdc0` (`trunk`).
- **Toolchain** wolf 0.2.35 by `kernel/wolf.pin` (archive `4cc4045b…`, copied from px83's cache, never moved; its
  sha256 read twice and `tools/fetch-wolf`'s own check every batch: `wolf 0.2.35 (wolfgang, pin cf0c13d)`), Limine
  12.9.1 (px83's staged copy).
- **Host** hasu block A (CPUs 0-5), both of its locks held per container run, the block name outside
  (`notes/px85/hasu/ctr.sh`: each `block A acquired` and `END … exit=` line is in the batch logs); first a polling
  wait, then (`d49ae6d0`) a blocking `flock -w 240` printed every 4 minutes, after the polling wait lost every race
  to px86's chained runs for half an hour. `localhost/px75-ubuntu:2` (QEMU 8.2.2, CI's; Ubuntu's OVMF; no `/dev/kvm`:
  TCG, as F8 runs on CI), `--memory 12g`. Block A was shared with px86 and s273, one container run at a time. Every
  long job detached with a pid file, a log and an exit marker (`notes/px85/hasu/launch.sh`).
- **CI's evidence**, read once each: the two failing F8 job logs of run 41153232393 (124394712226, 124441128673) and
  the three `pax-mpx6-firmware` artifacts (13025105801, 13031086753, 13032222933): both reds were the **release**
  tier's F8.

## Prediction, scored

`notes/px85/prediction.txt`, committed first (`4be12fa0`, 2026-11-01T00:27Z), before any change:

| predicted | measured |
|---|---|
| pax#260's ten word legs red at base + the words: the stalls refused (~40 ms, ~40 ms, ~5 s), the lying periods accepted | **right**, all ten, both firmwares; stall-window read 30.2 ms, not ~40 (the stall sits before the loop, which then exits at once) |
| every leg green after the fix; stall-edge retakes its closing bracket, stall-long measures a second window | **right**, native and release, both firmwares. Not predicted: every plain TCG boot also retakes its first bracket once (QEMU translating the loop), so stall-edge's row asserts the stall's own retake |
| the issue's one-line fix would leave stall-edge red | not run: reasoned from the row (the stall lies between the PM read and the HPET read that fix compares) |
| tests/usb-session-selftest red at base, green after | **right** |
| three QEMU plants red by name: `repeat lost`, `wrong key`, `stuck modifier` | **right**, each by its own name |
| 23-25 reports in a 100-tick hold | **right**: 24-26 in every head run, under every load |
| tests/fetch-retry-selftest: every row red at base, the scan listing 16 sites; green after | **right** |
| tests/pipe-shape-selftest red at base: 6 nm lookups in 5 files, 3 more early-exit awks | **right**, nine exactly |
| trunk control 5 of 5 green | **right** (24-25 reports, 31-32 s a run) |
| trunk under 50/50 red in at least 15 of 20, mostly `repeat lost`, the HPET in about half | **wrong**: 4 of 20, all the HPET; reports 18-23, none under 15. Under 200/50: 3 of 20, the HPET again. Contention starves the calibration's busy loop, not the idle hold (the stall section); the freeze load, added for that, reddened the repeat row 15 of 20 |
| head under the load 20 of 20 green | **right**: 20 of 20 under 50/50, 200/50 and the freeze, before the rebase and again in the gauntlet |
| the unplug and replug rows' wall-clock waits might fail under the load at the head | **wrong**: none did, under any load (60 head runs and the gauntlet's) |
| the plant red in CI's mpx6-firmware F1, mpx6-ahci A13 and mpx3-screen V4 | **right for two, wrong for A13**: A13 greps `^clock: HPET ` alone, which the refusal line also matches (seen reading the test before the plant was opened; its PR says so). Run 41269525005, read once in progress (55 of 61 jobs done): failed `mpx3-screen` and `mpx6-firmware`, no other |

## Evidence index

### Rulings (recommended and implemented, not decided)

- **R-px85-1, the HPET bound.** (A) within 1% of the PM interval measured across the same bracketed window (each end
  pinned between two PM reads at most 36 ticks apart; a window over 2 s measured again; three windows at most);
  (B) the old 0.5x-2x band, against the measured PM interval instead of a nominal 10 ms; (C) 0.1%, twice the HPET's
  own allowance. Recommended and implemented: **A**. B lets through a period that lies by up to a factor 2 (the
  14.318-vs-24 MHz table confusion, 1.68x, passes); C is under the brackets' own error of up to 0.2%.
- **R-px85-2, the repeat row's hold.** (A) held for 100 ticks of the guest's clock, read through QMP `memsave` of
  `pax_tick_count`; (B) a wall-clock hold with the expectation scaled to the hold the guest saw, which needs the
  release time in the guest (the probe reads a raw tty and never sees a release, so the kernel would have to log
  it); (C) hold until the guest has reported N repeats (the probe prints the row only at its end, so the harness
  cannot see them live). Recommended and implemented: **A**; the Linux guest keeps the 1000 ms wall-clock hold.
- **R-px85-3, the pipe scan's reach.** (A) nm pipes only, as pax#256 names; (B) every writer piped into an awk that
  exits before its input ends. Recommended and implemented: **B**: three more lines fixed, one of them
  (`tests/mpx6-ahci`'s recording path, under `set -euo pipefail`) able to end its script today.
- **R-px85-4, the retry policy.** (A) three attempts, 10 s and 30 s apart, a 1000 bytes/s floor over 60 s, named
  classes, the pinned commit checked; (B) retry any failure, as curl's `--retry` does (retries an unknown sha:
  refused by pax#259 itself); (C) longer waits (60 s, 300 s) for GitHub's longer incidents. Recommended and
  implemented: **A**: a fetch adds at most 40 s of waits and two attempts.
- **R-px85-5, the stall loads.** (A) the contract's contention load and a freeze load (the container paused by the
  cgroup freezer, as a hypervisor deschedules a runner), the head held to 20 of 20 under each; (B) contention alone.
  Recommended and implemented: **A**: contention cannot reach pax#261 (below), so with B the repeat row's fix would
  have no red-first witness under a stall.

### pax#260: the HPET checked over the interval it was read across

At base `hpet_ns_per_10ms` opened its window on a PM edge, read the HPET, spun until the PM timer had moved at least
35795 ticks, read the HPET again, and wanted 5-20 ms from it. The PM interval it had measured (`b - a`) was thrown
away, so a stall inside the loop (the vCPU's on a shared runner; an SMI on metal) lengthened the HPET's reading
against a fixed 10 ms and refused a correct HPET: run 41153232393's attempt 1 read 31,749,850 ns (`HPET 10000000
fs/tick read 31749850 ns across 10 ms of the PM timer; refused`), and kasumi's shape fell to the PM timer.

The fix (`adf05e1b`; its counts `c7a9d196`): each end of the window is a **bracket**, a PM read, the HPET's counter,
a PM read, taken again until its two PM reads lie at most 36 ticks (10 us) apart, so the HPET's reading is pinned
inside a known PM interval; the window is at least 35795 PM ticks from the opening bracket; the HPET's time across it
must lie within 1% of the PM interval the brackets bound (from the opening bracket's last read to the closing one's
first, at the least; first to last, at the most). A stall between the brackets is measured by both clocks; a stall
inside a bracket widens it and the bracket is taken again (64 tries); a window longer than 2 s is no verdict (the
24-bit PM timer wraps at 4.69 s and its count could hide a wrap) and is measured again, three windows at most. The
refusal names both measurements (`clock: HPET 12500000 fs/tick read 12528637 ns across 10022502 ns of the PM timer,
more than 1% apart; refused`); the accepted line is byte for byte the old one (`…, checked against the PM timer`), so
F1, F8, A13 and V4 read it unchanged. The issue's own one-line fix (`t1 - t0` against `(b - a)`) would still refuse
a stall between the window's last PM read and its HPET read: the stall-edge row is that case.

The test words (`30fe5e98`, inert in every kernel but `kernel/kmain_metal.lu`, which sets them from its command line,
`282c7172`): a stall of N PM ticks at point 1 (inside the window) or 2 (inside the closing bracket, between its PM read
and the HPET read), once; a period read as N thousandths of itself. tests/mpx6-metal's five legs (`852a0043`; the
counts they assert `b9435452`, `aa2127ec`, `903a9114`, `bc7cbe91`), on both firmwares:

| leg | the word | base + words + legs (`8223a994` before the rebase) | at the head, native and release |
|---|---|---|---|
| stall-window | 30 ms inside the window | **red**: `read 30248260 ns across 10 ms …; refused`, the tick by the PM timer | `checked against the PM timer`, the tick by the HPET |
| stall-edge | 30 ms between the closing PM read and the HPET read | **red**: `read 40057420 ns …; refused` | checked; `took 2 bracket(s) again, 1 across the stall` |
| stall-long | 5 s inside the window | **red**: `read 5000310800 ns …; refused` | checked; `measured 2 window(s), 1 too long` |
| hpet-fast | the period read x1.25 | **red**: accepted (`HPET 12500000 fs/tick, checked …`) | `read 12528637 ns across 10022502 ns …, more than 1% apart; refused`, then the PM timer |
| hpet-slow | the period read x0.8 | **red**: accepted (`HPET 8000000 fs/tick, checked …`) | `read 8021128 ns across 10026134 ns …; refused`, then the PM timer |

Logs: `notes/px85/logs/clock-legs-red-at-8223a994.log` (each word leg booted on its own after the suite's first
red), `mpx6-metal-native-at-a08cf2f1.out`, `mpx6-metal-{native,release}-at-c93731a1.out`, and the gauntlet. Under TCG
a plain boot retakes its first bracket once (QEMU translating the loop the first time costs host time while both
clocks run): every plain leg reads `took 1 bracket(s) again, 0 across the stall`, which is why stall-edge asserts the
stall's own retake rather than a count.

**On metal** (the contract's question: which clock kasumi boots on, as far as the evidence says). kasumi has an HPET
table and an FADT, and its Linux lists `tsc hpet acpi_pm` as clock sources (px76's contract, read on kasumi
2026-10-28), so both of PAX's checked clocks exist there. No PAX boot of kasumi has shown its `clock:` line in any
evidence I found: kasumi has no serial port, PAX keeps no kernel log a program can read, and the photographs on
record are px77d's triage panel and the login prompt; the line is drawn on the console during boot and scrolls away.
So which clock PAX chose on kasumi is not known. What the code says: at base, an SMI or any other stall of more than
about 10 ms inside the 10 ms window made PAX refuse a good HPET and boot on the PM timer, a working fallback; with the
fix such a stall refuses nothing. A photograph of the boot's first screen is how the next metal boot can say.

### pax#261: the repeat row held for the guest's ticks

What the guest counts. PAX's software key repeat (`kernel/xhci` `tick`), `poll`'s timeout and `CLOCK_MONOTONIC`
(`kernel/user` `now_ns`: ticks x 10000151 ns) all count LAPIC ticks, and a tick that falls due while the vCPU does not
run coalesces with the next. The HPET and the PM timer are QEMU's virtual clock and count on. So a stall during
`sendkey a 1000` (a second of the host's clock) shortens the hold the guest sees: run 41153232393's attempt 2 has
`USBTIMES 0 250003775 290004379 320004832 350005285 390005889`, delay and period exactly right, six reports: the
guest counted about 40 ticks across the host's second. The probe (`user/elf/usbkeys.c`, the same binary on Linux)
reads a raw tty and never sees a release, so the guest's own hold cannot be read from the transcript (R-px85-2).

The fix (`c897c61b`; the hold's wall-clock record `278cdbed`): on a PAX guest, row 10 presses `a` with QMP's
`input-send-event`, reads boot/isr.S's `pax_tick_count` through `memsave` until it has advanced 100 ticks (1000 ms of
the guest's clock), then releases; a hold the guest's ticks cannot finish in 30 s of the host's clock fails by name
(`repeat hold: the guest counted N of 100 ticks …`). `repeat.txt` records `hold_ticks` and `hold_wall_s`. The Linux
guest (`--linux-kernel`, no symbols) keeps `sendkey a 1000`. The verdict names its fault (`repeat_verdict`):
`stuck modifier` (0x41, 0x01 or an ESC prefix: Shift or Caps Lock, Ctrl or Alt survived), `wrong key` (any byte but
0x61), `repeat lost` (fewer than 15 reports in the hold). The delay, median and mean checks after it are unchanged:
they read the guest's own stamps, which count ticks, so a stall does not shorten them.

`tests/usb-session-selftest` (`34f015f1`, `8aaf44eb`, `0003f68e`), in the plan job: U1 24 reports pass; U2 six
reports in a 100-tick hold (attempt 2's row) and U3 none are `repeat lost`; U4-U6 0x41, 0x01, ESC are `stuck
modifier`; U7 0x62 is `wrong key`; U8 a fault beside too few reports is named by the fault; U9 the source holds row 10
for 100 guest ticks with the wall-clock bound. Red at base: `AttributeError: … no attribute 'repeat_verdict'`
(`notes/px85/logs/usb-session-selftest-red-at-base.log`); green after, on the Mac and in the container.

The three faults planted in the guest (`notes/px85/hasu/b4-usb-plants.sh`: each a scratch worktree at the pre-rebase
`707833d4`, one line of `kernel/xhci`'s `tick` changed and never committed, the diffs in `notes/px85/plants/`), F8's
release leg once each with no load:

| plant | the change | F8 says |
|---|---|---|
| lost | the software repeat stops after its first report | `RuntimeError: repeat lost: 2 reports in a hold of 100 guest ticks, at least 15 wanted: 'USBROW repeat-a 61 61'` |
| wrong | the repeat sends the next scancode (`s`) for `a` | `RuntimeError: wrong key: byte 73 in the repeat row, where only 61 (`a`) was held: 'USBROW repeat-a 61 73 73 …'` |
| stuck | the repeat presses Left Shift first, and nothing releases it | `RuntimeError: stuck modifier: Shift or Caps Lock survived into the repeat row (byte 41 where 61 is `a`): 'USBROW repeat-a 61 41 41 …'` |

### pax#259: one bounded retry for the 16 source fetches

`tools/fetch-retry DIR REPO REFSPEC [SHA]` (`d9c4a4ac`), POSIX sh, so the census container's `stage.sh` runs it too:
`git -C DIR fetch -q --depth 1` at most three times, 10 s after the first failure and 30 s after the second, the
transfer held to a floor of 1000 bytes/s over 60 s (`http.lowSpeedLimit`/`http.lowSpeedTime`) so a stalled transfer
ends as curl's 28 and is tried again instead of hanging to the job's limit. Retried, by git's and curl's own words:
`reset` (pax#259's `curl 56 Recv failure: Connection reset by peer`, `unexpected disconnect`, `early EOF`, …),
`connect`, `timeout`, `tls`, `server` (HTTP 5xx, 429). Refusals are read first and never retried: `not our ref`,
`couldn't find remote ref`, an unadvertised object, a missing repository, any other 4xx. With SHA the commit fetched
(`FETCH_HEAD^{commit}`) must be the pin; another is refused and not fetched again. Each caller still checks out and
compares HEAD with its pin as before; `stage.sh`'s `tree`, which never compared, now does (every `*_REV` in `pins.sh`
is a full sha). The sites, one commit each: the eight `tree()` helpers (`803ef1b0`, `f4654429`, `6906df47`,
`9fcc0a96`, `6ec2618e`, `4463a499`, `b48371ff`, `db97c832`), the three std fetches (`d0cf8b82`, `fe309ba5`,
`77b93fa5`), `mklupin`'s and `mkwolf`'s tag fetches with the tag's commit pinned (`e17f4882`, `d4fe0514`),
`mkwolf-std` (`e8cf3cac`), `fetch-wolf` (`52eeb2db`), the census mount and `stage.sh` (`22411472`, `42f3d0a2`). This
is R-px83-1's infrastructure kind: a fetch is retried, never a test's verdict; `tools/ci-retry` is untouched.

`tests/fetch-retry-selftest` (`f5dad152`), no network: a local repository through `file://`, a fake `git` ahead of the
real one failing the first N fetches with a real failure's words, a fake `sleep` recording the waits. At base
(`notes/px85/logs/fetch-retry-selftest-red-at-base.log`): R1-R8 red (no helper, exit 127), R9 red naming all 16
sites. With the helper and the sites, every row green, on the Mac (macOS `sh`) and in the container (Ubuntu's
`dash`):

| row | injected | result |
|---|---|---|
| R1 | a reset on attempt 1 | fetched on attempt 2 of 3, one wait of 10 s, FETCH_HEAD the pin |
| R2 | a reset every time | exit 3, `gave up after 3 attempts, the last one reset`, waits of 10 and 30 s |
| R3 | `not our ref` (GitHub's words) | exit 4, `not a network error: not retried`, one fetch, no wait |
| R4 | an unknown sha, the real git's own answer | exit 4, one fetch |
| R5 | HTTP 403 beside `the remote end hung up unexpectedly` | exit 4, one fetch |
| R6 | HTTP 503 | `failed (server)`, fetched on attempt 2 |
| R7 | curl 28 `Operation too slow` (the floor) | `failed (timeout)`, fetched on attempt 2 |
| R8 | another commit than the pin | exit 5, `refused: fetched <sha>, the pin says <sha>` |
| R9 | the scan | all 16 sites call the helper; no other `git … fetch` in `tools/` |

Not run here: the census's own stage (a hand tool whose image, `px04-census`, lives on kasumi, offline); its change is
the one call and the read-only mount.

### pax#256: the `nm | awk … exit` shape, and its kin

`tests/pipe-shape-selftest` (`1bb7aa63`): S1 scans `tools/` and `tests/` for a writer piped into an awk whose program
exits outside `END`; S2 proves the scan sees the shape (behind nm and behind other writers, on one line and across
two) and passes the fixed forms, an END-only exit and an awk that reads its own file. At base S1 was red with nine
(`notes/px85/logs/pipe-shape-selftest-red-at-base.log`): the six nm lookups pax#256 names (`sym()` in
`tests/mpx2-{interrupts,paging,sched}` and `tests/mpx3-{loader,user}`, `symsize()` in `mpx2-interrupts`) and three
behind other writers: `tests/mpx3-user`'s two disassembly pipes (behind `tr`) and `tests/mpx6-ahci`'s recording awk
(behind `sed`, under `set -euo pipefail`). R-px85-3 B: all nine read their input to the end (`380fe0d0`, `2dc6466b`,
`829fef15`, `6009e5a2`, `1df8d80e`, `3f03d79d`). S1 and S2 green after. Same output, measured
(`notes/px85/hasu/pipe-equiv.sh`): every symbol the five tests ask and every name nm lists twice, through the old and
the new `sym()` and `symsize()`, on the native and release `kmain_metal` and the release `kmain_console`; the two
disassembly pipes on `pax_isr_common`; the recording awk on a log holding the session twice: 371 comparisons, 0
differ (batch 5); in the gauntlet 323 comparisons on the native and release `kmain_metal`, 0 differ.

### The stall harness (the proof)

`tests/mpx6-firmware.d/stall` (`65c3d82a`, `cb6b34d8`, `d0516d62`) runs F8's 3840x2160 serial-less leg (UEFI, no COM1,
no PIT, the NEC xHCI on MSI behind OVMF's 64 GiB window) N times, five at once, on hasu block A in
`localhost/px75-ubuntu:2` (QEMU 8.2.2, TCG), at the **release** tier (both of CI's reds were release). The leg is the
tree's own: the F8 block of the tree's `tests/mpx6-firmware` (from its copy of `boot/limine-initramfs.conf` to its
`row "F8 …"`) is cut out and run as it stands with that tree's `tools/usb-session` and kernel; trunk's block and the
head's are the same 25 lines (sha256 `72e23ef5…` in every batch's log), so between the two trees' runs only
`kernel/clock` and `tools/usb-session` differ. Each run's QEMU, every thread, is pinned to one CPU of 1-5 at nice 19
(`PAX_QEMU`, `tools/qemu-run`'s own hook); the harness runs on CPU 0. The loads, each named:

- **contention**, `--load B/I`: one busy process per QEMU on its CPU at nice 0, spinning B ms and sleeping I ms
  (50/50, a 50% duty cycle; 200/50, 80%). The contract's load.
- **freeze** (`notes/px85/hasu/freeze.sh`): the whole container paused by podman's cgroup freezer for 300 ms
  (370-530 ms measured: `podman pause` takes 46-214 ms, `unpause` 47-89 ms) then run for 700 ms, again, across the
  batch: the guest, QEMU's main loop and the harness stop together while the host's clock runs, as a hypervisor
  deschedules a runner. 145 freezes and 62.1-62.4 s frozen of each 20-run batch's ~170 s (36%). No signal is sent to
  any process.
- **control**, `--no-load`: the pinning alone.

| tree | load | runs | green | red, by the leg's own failing line | reports | the head's hold |
|---|---|---|---|---|---|---|
| trunk `8495bdc0` | none | 5 | **5** | — | 24-25 | — |
| trunk | 50/50 | 20 | **16** | 4: `FAIL F8: the clock is not the checked HPET` (read 27.99, 53.35, 58.14, 59.63 ms across the nominal 10) | 18-23 | — |
| trunk | 200/50 | 20 | **17** | 3: the HPET (read 30.96, 70.16, 103.20 ms) | 15-24 | — |
| trunk | freeze | 20 | **5** | 15: `RuntimeError: repeat lost, stuck modifier, or wrong key` (13-14 reports); the HPET checked in all 20 | 13-16 | — |
| head (pre-rebase `a08cf2f1`) | none | 5 | **5** | — | 24-25 | 100 ticks |
| head `a08cf2f1` | 50/50 | 20 | **20** | — | 24-25 | 100-101 ticks |
| head `a08cf2f1` | 200/50 | 20 | **20** | — | 24-26 | 100-102 ticks |
| head (pre-rebase `53a7b8f4`) | freeze | 20 | **20** | — | 24-25 | 100-101 ticks in 1.32-1.84 s |
| the gauntlet, the final head `a27e73fb` | none | 5 | **5** | — | 24-25 | 100-101 ticks in 0.98-0.99 s |
| the gauntlet | 50/50 | 20 | **20** | — | 24-25 | 100-101 ticks in 1.09-1.21 s |
| the gauntlet | 200/50 | 20 | **20** | — | 24-25 | 100-102 ticks in 1.12-1.41 s |
| the gauntlet | freeze (146 freezes, 62.8 s frozen) | 20 | **20** | — | 24-25 | 100-101 ticks in 1.32-1.88 s |

`a08cf2f1` carries both fixes; `53a7b8f4` is the final code, before the rebase brought px86's installer files (which
F8 does not build). Each batch's `runs.tsv`, its F8 block and every run's `leg.log`, `serial.log`, `runner.log` and
`repeat.txt` are under `notes/px85/stall/` (the 3840x2160 screendumps and ISOs deleted after each run).

Why contention reddens the HPET check but not the repeat row. The HPET's window is a busy loop: under contention the
vCPU wants the CPU and does not get it, so the loop overshoots by a scheduler slice or more. Through the repeat hold
the guest idles (HLT until the next tick), and a fair scheduler runs a woken, mostly sleeping vCPU within one slice
even at nice 19, so few ticks are lost: trunk's reports fell from 24-25 to 15-24 and never below 15. CI's attempt 2
lost about 600 ms of ticks in one second, as a stall of the whole runner VM does and a busy neighbour on the same
scheduler does not; the freeze is that stall, and it reddens trunk's repeat row 15 times in 20 (and, the window being
10 ms of a 1000 ms cycle, never its HPET check: the two loads between them redden both of trunk's flakes, each by
its name).

### The plant, `px85-plant-hpet`

Draft PR #264 on the px85 branch, head `3ece2a72`: the final head `a27e73fb` and one line of `kernel/clock`'s
`measure`, the agreement band narrowed from within 1% of the measured PM interval to 1%..0.5% *below* it, so a correct
HPET is refused unstalled; the fix never contains it. Locally first (`notes/px85/logs/plant-hpet-local.log`, at its
pre-rebase twin `cfa12f58`, the same one line): `clock: HPET 10000000 fs/tick read 10023030 ns across 10022502 ns of
the PM timer, more than 1% apart; refused`, then `FAIL METAL firmware bios-hpet: the tick was not calibrated by the
HPET`; the stall legs refused likewise, the lying-period legs still refused. In CI, run 41269525005 (`tier pr`:
`kernel/clock` is ALL, every suite on native BIOS), its id and state read once, in progress with 55 of 61 jobs done:
failed `mpx6-firmware` and `mpx3-screen` (V4: the refusal line carries the window's numbers, so the screen and
screenless boots differ), no other. The orchestrator closes it at the merge.

### The gauntlet at the final head

`notes/px85/hasu/gauntlet.sh` at `a27e73fb1154a3fcf5b3026a2d71bedb9a71522c` (the rebased head; every commit after it is
notes), each step a block-A container of its own, stopping at the first nonzero step; its log, every step's own log
and every F8 run's transcripts are in `notes/px85/gauntlet/` (exit marker `0`):

```
END tests/ci-plan exit=0
END python3 -I tests/ci-retry.py exit=0
END python3 -I tests/mpx2-heap.d/budget.py exit=0
END python3 -I tests/ci-budgets.py exit=0
END tests/fetch-retry-selftest exit=0
END python3 -I tests/usb-session-selftest exit=0
END python3 -I tests/pipe-shape-selftest exit=0
END tests/expect-serial-selftest exit=0
END selftests exit=0
END tests/mpx6-metal native exit=0
END clock-legs native exit=0
END clock-native exit=0
END tests/mpx6-metal release exit=0
END clock-legs release exit=0
END clock-release exit=0
END pipe-equiv exit=0
END pipe-equiv exit=0
END f8-control exit=0
END f8-load-50-50 exit=0
END f8-load-200-50 exit=0
END f8-freeze exit=0
gauntlet: every step exit=0 at a27e73fb1154a3fcf5b3026a2d71bedb9a71522c
```

(`END pipe-equiv` appears twice: the script's own line, then the step's.) The F8 steps' rows are the stall table's
last four; pipe-equiv compared 323 lookups and pipes on the native and release `kmain_metal`, 0 differ.

## Done-when

- [x] Item 1 (pax#260): the HPET compared with the PM interval it was read across, both ends bracketed, within 1%
  (R-px85-1); the stall and lying-period legs red before the fix and green after, on both firmwares and both tiers;
  the metal consequence above, from the evidence there is.
- [x] Item 2 (pax#261): the repeat row held for 100 guest ticks; the verdict's three names; the selftest red then
  green; the three faults planted in the guest, each red by its own name.
- [x] Item 3 (pax#259): `tools/fetch-retry`, the 16 sites through it, the selftest's injected reset passing and its
  every-attempt reset stopping by name.
- [x] Item 4 (pax#256): the nm shape gone from the tests, with its three kin (R-px85-3); the scan red then green; the
  rewrites' output equal to the old.
- [x] Item 5: the harness and its logs (`tests/mpx6-firmware.d/stall`, `notes/px85/stall/`); trunk red under every
  load, each red named; the head 20 of 20 under each load, and again at the final head.
- [x] Item 6: this note, the plant, the PR, the audit once.
- [x] README read against the pass: the retry sentence, the harness proofs and the tools row moved and are refreshed
  (`7656b2d8`, a README-only commit; its `tools/` row merged with px86's at the rebase); nothing else in it moved.

**Issues** (none filed or closed by this lane): pax#260, pax#261, pax#259 and pax#256 are each fixed by this PR and
are to be closed by hand at the merge. Owed, for the orchestrator to file or drop:
- `tools/usb-session` still paces the unplug and replug rows (0.4 s and 1.0 s before the next key) and the ring-wrap
  (20 ms a key) by the host's clock. None failed in the 120 loaded head runs (60 before the rebase, 60 in the gauntlet), but they are the same class as pax#261:
  waiting for the guest's `xhci: keyboard usb1-N` line would make them exact.
- kasumi's `clock:` line is unknown (above): the next metal boot's photograph of its first screen says which clock it
  chose.
