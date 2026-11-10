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

- Base: trunk `d56fdd98` (first `4d899ea4`; rebased onto `d56fdd98` after #331 and #332 merged, the one conflict
  the CHANGELOG's top, both entries kept). Every sha this note and the prediction cite is the rebased commit's;
  the prediction's two were moved and nothing else in it.
- The runs: every run of the ci workflow created 2026-11-01 to 2026-11-09 that had completed when read (121; two
  were still queued or running and are left out), with every attempt's jobs (`filter=all`). 189 attempts of the two
  jobs have a log; an attempt a re-run copied counts once. Four runs' attempts have none: they were cancelled within
  ten minutes, or before a runner took them.
- yew's pin: `0ccb2c67` (its own toolchain wolf 0.2.35) until `aba55824`, `2eb9cb9b` (wolf 0.2.36) since.
  `1218169e` (wolf 0.2.36) ran only in a pull request's runs before that.

## 3. Prediction, scored

From `notes/px113/prediction.txt`, committed after the measurement and before any change (`5568c161`).

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
- **P4, held, the names refined:** at `98f3a4cd` (the check, before the workflow change) all eight new rows were red,
  `FAIL CI budget mpx5-yew (tier all): bound=4500s sizing-floor=5860s margin=-1360s` among them, the pr and full rows
  too; at `03d8b8a8` all eight pass and every older row is unchanged. `3ee0f254` then names each row in one word,
  `budget/<job>/<tier>`, so the plant's record can be held to it by name. `tests/ci-plan` passes unchanged (356 rows):
  no job was added, so the tier job's needs are the same.
- **P5:** the plant, below.
- **P6:** the hosted tier full under `full-matrix`, and trunk's tier all after the merge: not yet run.

## 4. Evidence index

- `075db35e` `tests/ci-budgets.d/yew-screen.json`: every attempt, phase by phase, the measurement committed first.
- `0c449818`, `3aa89d88` `notes/px113/measure/`: the scripts that read the API and the logs, the per-attempt table
  (`table.txt`) and every yew build (`yew-builds.tsv`).
- `5568c161` `notes/px113/prediction.txt`.
- `98f3a4cd` `tests/ci-budgets.py`: mpx5-yew and mpx5-screen held to their floors, each tier; red at 75 minutes.
- `03d8b8a8` `.github/workflows/ci.yml`: the two limits, tiered in mpx6-install's expression form.
- `1a4ca47b`, `9f425dc7` `tests/ci-budgets.d/README.md`: the floors, the bounds, the multiples of the worst run.
- `b7d31add` CHANGELOG.
- `3ee0f254` the rows' one-word names.
- The local record at the head and the plant's record are listed in the pull request.

What the jobs were, at `2eb9cb9b`, in the all tier:

| job | attempts | green | cut at 75 min | red | green range |
|---|---:|---:|---:|---:|---|
| mpx5-yew | 16 | 5 | 10 | 1 (cut too) | 3838-4494 s |
| mpx5-screen | 15 | 11 | 4 | 0 | 3333-4211 s |

On trunk alone, mpx5-yew was cut in 8 of 12 runs. At `0ccb2c67` neither job was cut in 29 all-tier attempts.

### yew's build, separated (pax#327)

After the pull request opened, both yew pins were built with both compilers on one host: hasu's block B (CPUs 6-11,
its three locks held, nothing beside it), in the baseline Ubuntu 24.04 image (`localhost/px88-ubuntu:1`), with no
network and a 12 GB cap. Each build was `tools/mkyew`'s, `wolf build --release --no-cache --deny-warnings src/yew.lu`
through a `cc` that adds `-static`. Each wolf used the std its archive bundles; that std is the one the matching
yew pin names. The inputs were staged by digest: the two wolf release archives and yew's two codeload archives, each
read twice. The script is `notes/px113/measure/separation.sh` and its table `notes/px113/measure/separation.tsv`. One
run per cell, interleaved, 2026-11-09T21:55Z to 2026-11-10T04:42Z:

| yew | wolf 0.2.35 | wolf 0.2.36 |
|---|---:|---:|
| `0ccb2c67` | 1198 s (user 1655 s) | 1158 s (user 1566 s) |
| `2eb9cb9b` | 1822 s (user 2431 s) | 2072 s (user 2791 s) |

The two cells that match CI (each pin with its own compiler) built yew byte for byte as CI did: `35f41aeb…`
(21,369,544 bytes) and `55cc491d…` (24,828,584 bytes).

What it shows:
- The newer yew costs 52% more to build under wolf 0.2.35 and 79% more under 0.2.36. Most of the growth is
  yew's own tree, under either compiler.
- The compiler adds about 14% on the newer yew only (1822 to 2072 s; user time 15%). On the older yew, 0.2.36 is
  about 3% faster (5% in user time).
- On this host the pin move as CI made it, old pin and old compiler to new pin and new compiler, is +73% (1198 to
  2072 s). CI's medians moved +52% (1584 to 2403 s over 129 and 114 builds); one run per cell can't say whether the
  difference is the host or the spread.

What it doesn't show: any spread, with one run a cell. A difference of 10% or less here (the compiler on the older yew,
and maybe its 14% on the newer) is within what one run on a shared host can move. Which part of yew's 243 commits, or
of 0.2.36, costs the time is also not shown.

The floors don't move for it. They are measured from CI's own attempts at the current pin and compiler, which already
carry this cost. The separation explains the floors; it adds no CI observation. A later pin move that grows yew's build
again would need new observations; `tests/ci-budgets.py` reads only what `yew-screen.json` holds. And since a build is
byte for byte the same on another host, building yew once per run and handing it on by its digest (R-px113-3) can be
checked against that digest.

## 5. Done-when

- [x] the measurement committed first, every attempt since 11-01, per leg
- [x] the prediction committed before any change
- [x] the budget rows red at the base, green at the change
- [x] `tests/ci-plan` passes; no job added
- [x] the plant red by name (the pull request lists its record)
- [x] pax#327 names yew's slower build, and the same-host separation of both pins with both compilers is added there
- [ ] the hosted tier full under `full-matrix`, both jobs inside their limits
- [ ] the audit

## Rulings

- **R-px113-1** Raise or split: (a) raise, tiered. A split by leg repeats yew's build in every job, and one leg alone
  needs 94 to 112 minutes by the same rule.
- **R-px113-2** How the raise is tiered: (a) by the plan's tier, all and partial wide, pr and full narrow, in
  mpx6-install's expression form (a partial dispatch may name every leg).
- **R-px113-3** Build yew once per run and hand it on by digest: (a) a later lane, not this change.
- **R-px113-4** yew's build grew with the pin move: (a) named in a pax issue, pax#327, with the table, both pins and
  both compilers, then the same-host separation (section 4): mostly yew's own tree, the compiler about 14% on the
  newer yew only.
- **R-px113-5** The apt stall (635-651 s, six times): (a) counted in the floors as measured.
