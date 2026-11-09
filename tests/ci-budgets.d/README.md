# Long-job budgets

The four long jobs retain every row and compiler/firmware leg. Their
workflow bounds are interrupts **75 min**, heap **90 min**, pelt **210 min**,
and users **210 min**. `tests/ci-budgets.py` checks at least 40% headroom
above the measured sizing floors below; heap also retains its separately
checked, stronger 50% headroom rule.

| job | measured sizing floor | allowance included | bound | margin above floor |
|---|---:|---|---:|---:|
| interrupts | 2885 s | completed whole-job maximum | 4500 s | 1615 s |
| heap | 3336 s | completed whole-job maximum, 20 samples | 5400 s | 2064 s |
| pelt | 8858 s | main 6535 + root 1543 + replay 600 + overhead 180 | 12600 s | 3742 s |
| users | 8920 s | main 5018 + root 3422 + deadline delta 300 + overhead 180 | 12600 s | 3680 s |

These are mixed-head runner observations, not controlled benchmarks. For
pelt, the largest completed rootdisk step was 1454 s, while one cancelled
step had already spent 1543 s. **1543 s is only a lower bound**, not a claimed
completion or upper bound. It raises the sizing floor; the final all-tier
run must validate the larger envelope. No shortened failing run is counted
as a completed runtime.

Pelt's 600 s allowance covers one repeat of its Linux reference only. In
run 40505003163 the interval from the build-complete marker 12:53:00.677Z to
the first friendly-image output 13:01:24.369Z was under 504 s, including image
creation after Linux finished. An extra prompt/exit timeout adds at most 60 s
to that measured replay shape. The 180 s overhead allowance is separate
from the measured main/root steps. Users adds 300 s for the new rootdisk
chk-soak deadline. Bounds are rounded upward after applying the headroom,
not multiplied from an already censored job timeout.

## Runner observations

Seconds from GitHub's job/step timestamps. `C` means cancelled (censored),
`F` means failed before completing the leg, `S` means skipped. Unmarked
values completed successfully. Early runs had no rootdisk step. Raw status
and duration fields are in `runs.json` and `interrupts.json`; heap's 20-run
sample is in `../mpx2-heap.d/ci-durations.tsv`.

| run | interrupts job | pelt main / rootdisk | users main / rootdisk |
|---|---:|---|---|
| 39907088686 | 1650 | 5855 / not present | 4331 / not present |
| 39951081735 | 1450 | 5306 / not present | 4424 / not present |
| 40025587241 | 1523 | 5215 / not present | 4282 / not present |
| 40043721537 | 1957 | 4871 / not present | 5018 / not present |
| 40062274427 | 1412 | 4944 / not present | 2679 / not present |
| 40126577436 | 2228 | 5790 / 1396 C | 2954 / 1941 |
| 40146035531 | 2513 | 4087 / 1104 | 2383 / 1806 |
| 40153833245 | 2885 | 1293 F / 0 S | 4457 / 945 C |
| 40178690366 | 2635 | 5414 / 1446 | 4302 / 3395 |
| 40208110580 | 2648 | 5439 / 1446 | 4318 / 3404 |
| 40229780577 | 2119 | 1277 F / 0 S | 4317 / 3414 |
| 40229784922 | 2633 | 5405 / 1435 | 4322 / 3402 |
| 40244080881 | 2437 | 5518 / 1454 | 3211 / 2555 |
| 40258431439 | 1846 | 6365 / 835 C | 3480 / 2798 |
| 40258619129 | 2232 | 6015 / 1164 C | 3223 / 2643 |
| 40322892901 | 2643 | 5974 / 1280 C | 2408 / 1890 |
| 40322972367 | 2712 | 6374 / 821 C | 4397 / 3414 C |
| 40326263858 | 2789 | 1175 F / 0 S | 4352 / 3422 |
| 40394044200 | 2714 | 5611 / 1543 C | 4372 / 3133 C |
| 40411390471 | 2661 | 6507 / 688 C | 3368 / 2602 |
| 40505003163 | 2452 | 6535 / 669 C | 3749 / 2875 |

Run 40505003163 was `tier all`, despite being initiated through a labelled
PR: its full-path change selected every leg. Pelt's main step completed in
108 min 55 s; rootdisk then got only 11 min 9 s before cancellation. The run
wall time was **2 h 2 min 3 s**, created/started 12:35:46Z to updated 14:37:49Z,
with final conclusion `cancelled`. Last green all-tier run 40208110580 took
**2 h 10 min 23 s**, 15:41:12Z–17:51:35Z on 2026-10-25. Neither is a prediction
of the post-change workflow's total wall time, which includes queueing.

## The AHCI-root job (px75b, R-px75b-6)

`mpx5-users-ahci` builds mpx5-users' native BIOS images (`tests/mpx5-users
--only build`) and boots all 25 again with `/` on AHCI. It is a job of its
own because the users job could not hold a third root leg: its all-tier
floor is 8920 s against 12600 s, and another 3436 s would need 289 minutes
at the 40% rule; in the full tier it already holds its native BIOS
sessions (1678 s in run 40620130831), the virtio leg (up to 3422 s) and
the NVMe leg (28 to 53 minutes, px75), about 8460 s, and the AHCI leg
would put it near 11900 s, past the 9000 s that 40% below 210 minutes
allows. Its floor is the larger of
its own CI leg and the users job's virtio root floor scaled by the two legs'
ratio, measured side by side on one host under TCG (`ahci-root.json`):

| job | measured sizing floor | allowance included | bound | margin above floor |
|---|---:|---|---:|---:|
| users-ahci | 3666 s | build 50 + leg 3436 (CI; 3422 x 1733/1728 = 3432 scaled) + overhead 180 | 5400 s | 1734 s |

One CI observation so far (run 40818748481, a plant's `tier pr` run:
3510 s whole, the leg 3436 s); the next budget lane adds the rest. The
workflow now has 58 suite jobs: px75b adds `mpx6-ahci` and this one, so
one more of the org's 20 slots is held for about an hour in each full and
all run, and in a pull request that changes kernel/ahci, its clock, the
users suite's script or the root-disk tools.

## Capacity and follow-up

210 min is **3.5 hours**, below the hosted **6-hour per-job ceiling**. The
workflow still selects the same 54 suite jobs and adds no matrix expansion
or new parallel jobs. The org's 20-concurrent-job budget is unchanged;
longer timeouts permit existing jobs to occupy those slots longer, not
additional slots. A per-job timeout is not a whole-workflow wall-time bound.

The next CI-budget lane's first item should split **pelt's replay and
rootdisk leg into separate jobs**, transferring the already-built fixtures
by digest. They have different failure modes and should not consume one
another's timeout. Users' ISO and rootdisk legs are the next split if growth
continues. No split or fixture-transfer dependency is introduced here:
the measured sums plus reserves fit the 210-minute envelope, subject to the
final all-tier validation.

## The installer (px84, R-px84-6)

`mpx6-install`'s limit is tiered: **60 min** in `tier pr`, **110 min** in
`tier full` and any partial run, **175 min** in `tier all`. The full tier
adds a full-density install onto a sparse 500 GB target, and `tier all`
adds one onto 4 TB. `install.json` keeps each run's phases, read from the
job log's timestamps. A phase's floor is its peak over the runs. Seconds:

| run | tier | units | inputs (yew alone) | smoke | faults | faults tail | full rows |
|---|---|---:|---:|---:|---:|---:|---:|
| 40817980461 | full, cut at 60 min | 18 | 3141 (1701) | 151 | 267 | not reached | not reached |
| 40620130831 | full | 18 | 2122 (1123) | 99 | 126 | 40 | 277 |
| 40532219747 | full | 20 | 502 (99) | 100 | 152 | 45 | 334 |
| 40690748340 | all | 21 | 2541 (1450) | 128 | 199 | 58 | 412 |
| 40634374652 | all | 15 | 2580 (1488) | 131 | 202 | 59 | 418 |

The phases sum to 4057 s at their peaks. No runner has finished a big row
yet. Each row is therefore its whole kasumi wall time scaled by 1.669, the
larger runner/kasumi ratio of the same smoke installs in run 40817980461
(I-install-yes-vdc: 43.80 s on the runner against 26.24 s on kasumi):

- 500 GB: 262 s on kasumi, 438 s scaled;
- 4 TB: 1655 s on kasumi, 2763 s scaled.

| tier | measured sizing floor | allowance included | bound | margin above floor |
|---|---:|---|---:|---:|
| pr | 642 s | the one completed pr-tier job (run 40817751644) | 3600 s | 2958 s |
| full | 4675 s | phases 4057 + 500 GB 438 + overhead 180 | 6600 s | 1925 s |
| all | 7438 s | full 4675 + 4 TB 2763 | 10500 s | 3062 s |

At the old limits (60 and 120 minutes) the check fails for both full and
all. The full tier misses even without the 500 GB row: its floor would
still be 4237 s against 3600 s. The inputs phase is mostly building the
installed tree's programs, and yew's build alone has ranged from 99 s to
1701 s on the runner. That build, not px84's rows, is what pushed run
40817980461 past 60 minutes before its full rows began. 175 minutes is
below the 6-hour per-job ceiling. It holds one of the org's 20 slots for
up to three hours in each trunk push and nightly run.

## mpx5-trace (px102)

Not a long job: `timeout-minutes: 60`. An estimate, not a runner
observation: on a 2-CPU KVM slice the native BIOS leg ran its 43 modes as
root and 42 as uid 1000 in 192 s (boots of about 1.5 s each, a build of
under a minute). Four legs are about 13 minutes plus the apt and wolf
fetches and `--only linux` (43 containers); the bound leaves more than four
times that. The first runner observation replaces this paragraph.

## yew at the keyboard: mpx5-yew and mpx5-screen (px113, pax#305)

Both jobs build yew (`tools/mkyew`) and then boot it on four legs. Their
limit was 75 minutes. Since yew's pin moved to `2eb9cb9b` (`aba55824`),
yew's build alone has taken 1602-2848 s (median 2403 s), against 1037-1877 s
(median 1584 s) at `0ccb2c67`. mpx5-yew was then cut at 75 minutes in 10 of
its 16 all-tier attempts, and mpx5-screen in 4 of 15. The boots did not
change: each leg is about 5.5 to 6 minutes at both pins. The build's growth
is pax#327.

`yew-screen.json` holds every completed attempt of the two jobs in the
runs created 2026-11-01 to 2026-11-09 (121 runs), each phase read from the
job log's own timestamps: setup, the programs (yew's build is about 95% of
it), the native and release kernels, Y0/S0, each leg in boot order, and the
artifact upload. A cancelled attempt's last phase is a lower bound (`cut`);
an attempt with a FAIL row (`red`) is never a sample. The scripts that read
the logs are in `notes/px113/measure/`.

The limit is tiered, as mpx6-install's is. The all tier, and a partial
dispatch (it may name every leg), runs every phase; pr and full run native
BIOS alone, with no release build. Each phase's floor is its peak over the
attempts, and a tier's floor is the sum of the phases it runs:

| job | tier | measured sizing floor | bound | margin above floor |
|---|---|---:|---:|---:|
| mpx5-yew | all, partial | 5860 s | 8400 s (140 min) | 2540 s |
| mpx5-yew | pr, full | 4044 s | 5700 s (95 min) | 1656 s |
| mpx5-screen | all, partial | 5568 s | 7800 s (130 min) | 2232 s |
| mpx5-screen | pr, full | 3951 s | 5700 s (95 min) | 1749 s |

As multiples of the worst run: mpx5-yew's 140 minutes is 1.87 times its
worst green all-tier attempt (4494 s), and 1.69 times its worst cut attempt
completed at the median of the phases it never reached (4967 s);
mpx5-screen's 130 is 1.85 times 4211 s and 1.63 times 4776 s. The 95
minutes is 1.55 times mpx5-yew's worst pr or full attempt (3687 s) and
1.76 times mpx5-screen's (3238 s). The floors carry one apt stall of about
640 s, seen six times in these runs (635 to 651 s).

A split by leg would not have helped: each job would build yew again, and
by the same rule one leg alone needs 94 to 112 minutes (mpx5-yew) and 92 to
108 (mpx5-screen). What would shorten both jobs is building yew once per
run and handing the binary on by digest; that is a later change.
