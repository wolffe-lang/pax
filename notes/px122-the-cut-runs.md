# px122 — trunk's cut runs after #344: mpx3-shell and mpx5-pelt against their limits

Contract: px122's (2026-11-11). Trunk's push runs had not been green since `3fa24cf5` (run 42980205707). After #344
(`a04eb7b5`: Limine's menu, the boot's beeps, its stage marks) and #345 (`3b6e4b64`), `mpx3-shell` was cut at its
120-minute limit in runs 43013370273 and 43025025659 (attempt 3), and `mpx5-pelt` at its 210 in the latter, in
steps that only the all tier runs. The suspicion was that #344's boot changes made those legs hang or crawl. Find
where each step stopped making progress, reproduce the legs at the three commits, name the cause, and fix it with a
row that would have caught it on a pull request, red first; if it is runner speed, prove it and change only the
note.

Footprint: cross-cutting (`.github/workflows/ci.yml`, `tests/ci-budgets.py`, `tests/ci-budgets.d/`) and
`kernel/procfs`. Docs: the budgets README, the CHANGELOG, `kernel/README.md`. The rest is notes and the local rig
(`notes/px122/`).

## 1. Forbidden, and what was read

No kernel's, firmware's or boot loader's source was read. Read: the workflow, `tests/ci-budgets.py` and its README,
`tools/build-kernel`, `tools/usb-typing`, `tools/rootdisk-leg`, `tests/mpx6-firmware.d/typing-irq`,
`tests/mpx3-shell`, `tests/mpx6-bootlog`, #344's diff, and the kernel's own notes on the release tier's inlining
(`kernel/block`'s report, `kernel/tcp`'s lines, `kernel/xhci`'s attach; pax#215); the ci workflow's runs, jobs, job
logs and artifacts through GitHub's API (pages of 30). No suite's row, leg or image changed. No label, merge or tag.

## 2. Inputs, verified

- Base: trunk `309036ec` (#346 merged), read from GitHub before the first commit; rebased onto trunk `48ea81ba`
  (px120's hot-plug change, #348), then onto `9ba58558`, px123's pointer branch on trunk `211e5c7c`, which merges
  first. Each time the only conflicts were lists both sides added to (the CHANGELOG's top, `kernel/README.md`'s and
  `docs/SOURCES.md`'s ends), and each keeps both; no other patch changed (`git range-diff`). The shas below are
  the latest rebase's; before the first rebase the branch was `px122-before-rebase` (`e3261a5e`), where the
  measurements and the first records were taken.
- The runs: every attempt of the two jobs in the ci workflow's runs created 2026-11-01 to 2026-11-11 (181 runs, 397
  attempts; `tests/ci-budgets.d/shell-pelt.json`), and the job logs of the 38 all-tier `mpx3-shell` attempts since
  2026-11-03.
- wolf 0.2.35 (`kernel/wolf.pin`, the archive's sha256 `4cc4045b…dad1a`) and Limine 12.9.1, both by digest; QEMU
  8.2.2 in an Ubuntu 24.04 container, as on the runners.
- The record script, `gauntlet-record.sh`, sha256 `03fdbdbc…c845d4`, the planning repository's copy.

## 3. What happened

### No step hung

- `mpx3-shell`, run 43025025659 attempt 3 (`3b6e4b64`): the MSI and INTx step had passed 190 of its 192 boots when
  the limit came, 35 s after the last one. Row for row it ran 1.35 times as long as the green run's, and so did the
  two steps before it (the suite 2261 s against 1395, the USB typing step 1647 against 1213). In run 43013370273
  (`a04eb7b5`) the same step finished (3259 s) and the root disk leg was cut 140 s in.
- `mpx5-pelt`, the same attempt: the root disk leg was cut 1107 s into a leg that took 1787 s in the green run, its
  rows 1.05 to 1.10 times as long as the green run's. The time had gone before it: the main step took 8604 s (6945
  green; its Linux side failed once and `tools/ci-retry` ran it again, pax#196's known flake, about 450 s), and the
  upload after the USB typing step took 285 s instead of 1, GitHub's artifact service answering twice with an error
  page.
- No retry loop: one retry in the whole attempt, pax#196's, by name.

### The runners, and limits with no room

The hosted runners come in two speeds. In the 38 all-tier `mpx3-shell` attempts since 2026-11-03, boreutils' build
(no kernel in it) took 175 to 190 s on 16, 300 to 311 s on 15, and 216 to 245 s on 7. Under TCG the slow ones boot
about 1.35 times as long. Both jobs had run within minutes of their limits on the slow ones for days: the green
all-tier attempts since 2026-11-01 reach 7157 s of mpx3-shell's 7200 and 12280 s of mpx5-pelt's 12600, and on
2026-11-03 mpx5-pelt was cut at 210 minutes in four all-tier attempts of three pull requests' runs and mpx3-shell
in one. mpx3-shell had no budget row. mpx5-pelt's (px83's) sizes its main step and its root disk leg from runs
before its USB typing step existed, so that step (up to 2592 s) was never in its floor: the row said 8858 s against
12600; green attempts take up to 12280.

### What #344 added: the release kernel's build

The kernel's release tier (`tools/build-kernel --release`, LLVM) is built only where a job runs the release legs:
the all tier and a partial dispatch. In mpx3-shell's suite step it is the time between the native kernel's
`build-kernel: ok` line and the release one (three ISOs are made between them too), and it is where the cut
attempts lost their time. Seconds, from the job logs:

| runners | before #344, since 2026-11-03 | `a04eb7b5` | `3b6e4b64` | `309036ec` |
|---|---|---:|---:|---:|
| boreutils in 175-190 s | 302 to 642, median 392 (16 attempts) | | | 556 |
| boreutils in 300-311 s | 439 to 672, median 573 (15 attempts) | 875 | 913, 942 | |

On one host, `kmain_console` alone (`notes/px122/rig/kernel.manifest`), cold (no wolf cache), on a block of six
CPUs; wall seconds, CPU seconds in brackets where measured, each number one take:

| commit | what it holds | release build | |
|---|---|---:|---|
| `3fa24cf5` | the last green trunk | 460, 463 (478), 468 (483) | |
| `2cae65ed` | #344's beeps | 334, 330 (344) | |
| `6edfa7aa` | #344 but its last procfs commit | 466 | |
| `dfb8a0ea` | + /proc/pax-boot's framebuffer and screen lines | 562 (578) | |
| `a04eb7b5` | #344 merged (`dfb8a0ea` and an assembly file) | 584, 566 (582), 598 (615) | |
| `309036ec` | trunk (#346 adds nothing here) | 589; 615 (631) | the second on another block |
| `309036ec` + `kernel/procfs` (this change) | `paxboot` in small functions | 363 (377) | on that other block, after the 615 |

The native tier's build is 3 to 4 s at every commit. The step is `dfb8a0ea`: 57 lines in `kernel/procfs`'s
`paxboot`, which makes `/proc/pax-boot`'s text, and a `put_fb` it calls once, a loop and thirteen calls of
`put_dec` and `put_s`. The kernel has met this before: the release tier inlines each small formatter's loop at
every call, and its range pass costs the square of one function's branches (`kernel/block`'s report, pax#215;
`kernel/tcp`'s "one function a line"; `kernel/xhci`'s attach). `paxboot` grew into one such function.

### What #344 did not add: the boots

- Every boot now beeps twice (about 100 and 200 ms, timed by channel 2's edges, kernel/speaker's `boot_tone`). The
  kernel's own `boot: N ms` line, from the artifacts: release median 527 ms at `3fa24cf5`, 831 at `309036ec` on a
  runner of the same speed (+304 ms), native 1894 and 1955 (+61). Over the MSI and INTx step's 192 boots that is
  under a minute: on runners of the green one's speed the step took 2411 to 2446 s before #344 and 2456 s at
  `309036ec`.
- Locally, under TCG as on the runners (`notes/px122/rig/ab.manifest`), `3fa24cf5` against `3b6e4b64`: the suite
  step's 48 boots took 571 s and 555 s, the step as a whole 1379 s and 1457 s, all of the difference the release
  build (466 s against 579). The first of the MSI and INTx step's four passes (48 boots): 591 s and 579 s. The
  kernel's boot line: release median 368 ms and 673 (+305 ms, the beeps), native 1635 and 1815.
- Limine's five-second menu is on the USB stick's configuration and the installed disk's, not on the ISOs these
  suites boot.

### Trunk at `309036ec`

Run 43094621784 drew a runner of the green one's speed for mpx3-shell: green in 5505 s (the suite 1487 s, the USB
typing 1214, the MSI and INTx step 2456). mpx5-pelt drew a slow one: its main step took 7677 s and the USB typing
step 2508 s, and it finished green in 12010 s of its 12600, ten minutes to spare. Ten other jobs of that run were red
only because GitHub's artifact service failed their upload steps between 20:39 and 20:57Z; their rows passed.

### On real hardware

Nothing here hangs. The cuts were CI's limits, not a stop in the kernel, and the release build's cost is paid on
the build machine, not at boot. An image built from trunk, installed and booted from its disk on UEFI with a USB
keyboard, shows Limine's menu for five seconds (#344's installed configuration) and boots the first entry with no key
(`tests/mpx6-bootlog` U2), then beeps for about 0.3 s. Each beep waits for channel 2's edges and gives up after
65536 reads of port 0x61 without one (`BEEP_IDLE`), so a machine whose 8254 does not count loses at most that many
port reads per beep, not the boot.

## 4. The change

- **`kernel/procfs`**: `/proc/pax-boot`'s text one function a group of lines (`paxboot_this`, `paxboot_previous`,
  `paxboot_log`, `paxboot_screen`) and `put_fb` in three (`put_fb_size`, `put_fb_masks`, `put_fb_tail`), the same
  calls in the same order, so the text is the same byte for byte (`tests/mpx6-bootlog` prints it and holds it line
  for line on both tiers and firmwares). The release build of `kmain_console` goes from 615 s to 363 on one
  block of one host, below `3fa24cf5`'s 460 to 468.
- **The budgets**, the remedy px113 took for yew's jobs: measure step by step, raise the limits
  tiered by the plan's tier, hold them at 40% over the measured floors.
  - `tests/ci-budgets.d/shell-pelt.json`: every attempt of the two jobs, each named step's seconds and conclusion,
    and the run's tier from its verdict job's name (`notes/px122/measure/runs.py`, committed with it, before any
    change).
  - `tests/ci-budgets.py`: a tier's floor is the job's named steps' peaks (a step cut at a limit a lower bound, a
    failed step never a sample) and 180 s; rows `budget/mpx3-shell/{all,partial,full,pr}` and the same for
    mpx5-pelt. And `budget/<job>/steps`: a named step of either job that no attempt has timed is red, so a new step
    in either job is red in the plan job of its own pull request until it is measured. mpx5-pelt's USB typing step
    would have been red there.
  - `.github/workflows/ci.yml`: mpx3-shell 190 minutes in the all tier and a partial dispatch (floor 8125 s), 120 in
    pr (1704 s) and full (2446 s); mpx5-pelt 350 in the all tier and a partial dispatch (floor 14904 s), 210 in pr
    (4232 s) and full (6532 s). px83's older pelt row reads the all tier's minutes.
  - The floors are measured on trunk as it was, with the slower release build in them; they come down only with new
    observations, after this change has run.

What would have caught it on a pull request: the mpx3-shell rows. With the observations since 2026-11-01 the all
tier's floor was over 7157 s before #344, so 120 minutes was red under the 40% rule in the plan job of every pull
request for days before #344 tipped a run over. No plan-map change would have: a pull request that touched the
kernel and ran the all tier would have drawn a fast runner about half the time, and passed. The release build's
growth itself has no row: a build time is the runner's as much as the code's.

## 5. Prediction, scored

From `notes/px122/prediction.txt`, committed before the local takes reported and before trunk's run finished.

- **P1, right:** not a hang; every cut step was passing rows at its rate (190 of 192; 1107 s of about 1787).
- **P2, half right:** the cut attempts ran on the slower runners, as predicted, but #344 is not innocent: one of its
  commits made the release kernel's build about a quarter longer on one host and about half again on the slower
  runners, which the prediction left out.
- **P3, right in size, wrong in kind:** the boots grew by about 0.3 s each (the release tier's boot line +304 ms;
  native +61) and the MSI and INTx step by under a minute, as predicted; but the time #344 adds is the release
  build's, not the boots'. `a04eb7b5` and `3b6e4b64` differ only in sudo's files, which these legs do not read.
- **P4, right for mpx3-shell, close for mpx5-pelt:** mpx3-shell at `309036ec` finished in 92 minutes, as
  predicted; mpx5-pelt drew a slow runner, not the green one's (main step 7677 s against 6945), and finished in 200
  minutes of its 210, not about 190.
- **P5, right:** the limits are the cause these runs share: mpx3-shell had no row, and mpx5-pelt's floor had no USB
  typing step (a green attempt uses up to 97% of 210 minutes, not 71%).

## 6. Evidence index

- `b8c2d674` `notes/px122/prediction.txt`.
- `bb1272bb` `notes/px122/measure/runs.py`; `e7841de9` `tests/ci-budgets.d/shell-pelt.json`, the measurement
  committed first.
- `ea873879` `tests/ci-budgets.py`: the rows, red at 120 and 210 minutes; `78effef6` px83's row reads a tiered limit.
- `3325e305` `.github/workflows/ci.yml`: the two limits, tiered.
- `e8ad9704` `kernel/procfs`; `e91a42a7` `kernel/README.md`; `33cda521` `docs/SOURCES.md`.
- `55fbbe04`, `d63a57d5` the budgets README; `d10ac43b`, `d3910bb2` the CHANGELOG.
- `notes/px122/rig/`: the local takes (`ab.manifest`, the timing takes; `kernel.manifest`, the kernel built alone;
  `budget.manifest`, the plan's checks; `gauntlet.manifest`, the green take). The records, with their sha256, are in
  the pull request.

## 7. Done-when

- [x] where each step stopped, from the hosted logs: no hang, no retry loop, the limit
- [x] the legs at `3fa24cf5` and `3b6e4b64` on one host under TCG; #344's kernel commits built in turn
- [x] the cause named: limits with no room on the slower runners, and the release build `dfb8a0ea` slowed
- [x] the measurement committed first, the prediction before the takes reported
- [x] the budget rows red at 120 and 210 minutes, green at the change
- [x] `kernel/procfs`'s text the same on both tiers and firmwares (`tests/mpx6-bootlog`, 106 rows), its release build
  faster
- [x] a plant red by name at `budget/mpx3-shell/steps` (the pull request lists its record)
- [ ] the hosted `tier full` under `full-matrix`, and trunk's all tier after the merge, both jobs inside their limits
- [ ] the audit

## Decisions

- **D1** Raise or split: raise, tiered by the plan's tier, as px113 did for yew's jobs. mpx5-pelt's 350 minutes is
  10 under the hosted runners' ceiling, and its floor can grow 3.5% more before no limit can hold it at 40%: the
  split the budgets README asks for (the USB typing step and the root disk leg as a job of their own) is due next.
- **D2** The release build: fixed where it grew (`kernel/procfs`), in this change, not left for a kernel lane. Every
  all-tier job that builds the release kernel gains about four minutes on one host, more on the slower runners.
- **D3** The local Linux side: the rig's container has no engine for the as-a-user sessions and lists `ls -l` totals
  of its own file system, so those rows are red locally whatever the kernel does. The timing takes read the boots,
  which ran; the MSI and INTx step stops after its first pass there, so one pass of four was timed.
