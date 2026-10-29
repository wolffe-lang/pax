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
