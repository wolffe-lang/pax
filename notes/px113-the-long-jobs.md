# px113 — the long jobs: mpx5-yew and mpx5-screen against their limit (pax#305)

Contract: px113's (2026-11-09), under the lane rules of 2026-10-31 and their additions. pax's trunk was red in most
all-tier runs because `mpx5-yew` was cut at its 75-minute limit, and `mpx5-screen` ran close to it. Measure the two
jobs first, per leg, then split them by leg or raise their limits with the measured spread as margin, held by the
planner's own checks, red first. No suite's content changes.

Footprint: cross-cutting (`.github/workflows/ci.yml`, `tests/ci-budgets.py`, `tests/ci-budgets.d/`). Docs: the
budgets README, the CHANGELOG. The rest is notes.

## 1. Forbidden, and what was read

No kernel's, firmware's or driver's source was read; nothing here touches PAX's code. Read: the workflow, the planner
(`tools/ci-plan`, `tests/ci-plan`, `tools/ci-tiers.map`), the budget check and its README, `tests/mpx5-yew`,
`tests/mpx5-screen`, `tools/mkyew`, `user/yew.pin`; the ci workflow's runs, jobs and job logs through GitHub's API
(pages of 30). No suite's script, row, leg or image changed; no job was added or removed. No label, merge or tag.
One issue was filed, pax#327, naming yew's slower build, as the contract asks of a measured slowdown.

The machines: the build Mac, for git, the API reads and the Python-only rows (`tests/ci-plan`,
`tests/ci-budgets.py` and the plan job's other selftests), behind its build lock.

## 2. Inputs, verified

- Base: trunk `4d899ea4`.
- The runs: every run of the ci workflow created 2026-11-01 to 2026-11-09 that had completed when read (121; two
  were still queued or running and are left out), with every attempt's jobs (`filter=all`). 189 attempts of the two
  jobs have a log; an attempt a re-run copied counts once. Four runs' attempts have none: they were cancelled within
  ten minutes, or before a runner took them.
- yew's pin: `0ccb2c67` (its own toolchain wolf 0.2.35) until `aba55824`, `2eb9cb9b` (wolf 0.2.36) since.
  `1218169e` (wolf 0.2.36) ran only in a pull request's runs before that.

## 3. Prediction, scored

From `notes/px113/prediction.txt`, committed after the measurement and before any change (`5ec2b5f3`).

- **P1, right:** builds, not boots. yew's build is about 95% of the programs, which are 58-61% of an all-tier attempt
  and 84-87% of a pr one. The four legs' boots are 22 to 23 minutes (mpx5-yew) and 20 (mpx5-screen), the same at
  both pins within 5%. Every cut attempt was cut in its third or fourth leg on rows that were passing; the one red
  attempt (run 42566364403, attempt 1) was a failed release download in `tools/mkpelt` (HTTP 504), a fetch flake
  of its own.
- **P1's number, corrected:** the prediction put yew's build at +44% (medians 1586 and 2283 s). That count left out
  the builds of attempts that were cut later, in a leg, after their build had finished. Counting every build that
  reached its `--version` line, as pax#327 does: 129 at `0ccb2c67`, median 1584 s; 114 at `2eb9cb9b`, median
  2403 s; +52%. The floors are unchanged: they come from phase peaks, which held every attempt.
- **P2, held:** raise, not split (R-px113-1). The numbers are in the budgets README.
- **P3, held:** the bounds as predicted: mpx5-yew 140 minutes in the all tier and a partial dispatch, 95 in pr and
  full; mpx5-screen 130 and 95.
- **P4, held, the names refined:** at `73e59f30` (the check, before the workflow change) all eight new rows were red,
  `FAIL CI budget mpx5-yew (tier all): bound=4500s sizing-floor=5860s margin=-1360s` among them, the pr and full rows
  too; at `96872133` all eight pass and every older row is unchanged. `a6632f8c` then names each row in one word,
  `budget/<job>/<tier>`, so the plant's record can be held to it by name. `tests/ci-plan` passes unchanged (356 rows):
  no job was added, so the tier job's needs are the same.
- **P5:** the plant, below.
- **P6:** the hosted tier full under `full-matrix`, and trunk's tier all after the merge: not yet run.

## 4. Evidence index

- `40390df5` `tests/ci-budgets.d/yew-screen.json`: every attempt, phase by phase, the measurement committed first.
- `413183f0`, `ef631b58` `notes/px113/measure/`: the scripts that read the API and the logs, the per-attempt table
  (`table.txt`) and every yew build (`yew-builds.tsv`).
- `5ec2b5f3` `notes/px113/prediction.txt`.
- `73e59f30` `tests/ci-budgets.py`: mpx5-yew and mpx5-screen held to their floors, each tier; red at 75 minutes.
- `96872133` `.github/workflows/ci.yml`: the two limits, tiered in mpx6-install's expression form.
- `20e6495a`, `561f4488` `tests/ci-budgets.d/README.md`: the floors, the bounds, the multiples of the worst run.
- `c50fe0f0` CHANGELOG.
- `a6632f8c` the rows' one-word names.
- The local record at the head and the plant's record are listed in the pull request.

What the jobs were, at `2eb9cb9b`, in the all tier:

| job | attempts | green | cut at 75 min | red | green range |
|---|---:|---:|---:|---:|---|
| mpx5-yew | 16 | 5 | 10 | 1 (cut too) | 3838-4494 s |
| mpx5-screen | 15 | 11 | 4 | 0 | 3333-4211 s |

On trunk alone, mpx5-yew was cut in 8 of 12 runs. At `0ccb2c67` neither job was cut in 29 all-tier attempts.

## 5. Done-when

- [x] the measurement committed first, every attempt since 11-01, per leg
- [x] the prediction committed before any change
- [x] the budget rows red at the base, green at the change
- [x] `tests/ci-plan` passes; no job added
- [x] the plant red by name (the pull request lists its record)
- [x] pax#327 names yew's slower build; a same-host measurement of both pins with both compilers is owed there
- [ ] the hosted tier full under `full-matrix`, both jobs inside their limits
- [ ] the audit

## Rulings

- **R-px113-1** Raise or split: (a) raise, tiered. A split by leg repeats yew's build in every job, and one leg alone
  needs 94 to 112 minutes by the same rule.
- **R-px113-2** How the raise is tiered: (a) by the plan's tier, all and partial wide, pr and full narrow, in
  mpx6-install's expression form (a partial dispatch may name every leg).
- **R-px113-3** Build yew once per run and hand it on by digest: (a) a later lane, not this change.
- **R-px113-4** yew's build grew with the pin move: (a) named in a pax issue, pax#327, with the table, both pins and
  both compilers; the cause is not separated yet.
- **R-px113-5** The apt stall (635-651 s, six times): (a) counted in the floors as measured.
