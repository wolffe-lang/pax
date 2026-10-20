# tl29 — The second diet: pax's merge gate on the legs that catch reds

Contract: `sprints/tooling/tl29-the-second-diet.md` in wolffe-lang/wolf
(planning trunk `560c78f`, read from origin 2026-10-20), under
`sprints/RULES.md`. Branch `tl29` in pax, cut from pax trunk `d733bf4`
(px52 merged). §1 to §5 are committed before the first change to the
workflow, the planner or the map. The wolf-interp half of the contract is
wolf-interp's PR (`ci/tl29.md` there); the `lane-audit.sh` half is a patch
handed to the orchestrator.

## 1. Forbidden

- **No test of PAX changes.** No suite's script (`tests/proof`,
  `tests/mkw`, `tests/mpx*`, `tests/tour`, `tests/census`, the
  self-tests), no assertion, no kernel, user, boot, font or harness path a
  suite reads. What changes is CI's own: `.github/workflows/ci.yml`,
  `tools/ci-plan` (the planner), `tools/ci-tiers.map`, `tests/ci-plan`
  (the planner's own proof, which the map files under "CI itself" beside
  the planner, and which every lane that changes the planner extends:
  px53's P2 lines are the latest), a new `tools/nightly-red` (a red
  nightly's issue), this note and `notes/tl29/`, and CLAUDE.md's CI
  paragraph (what a lane reads before it labels). The contract's "never
  touch a repo's tests" is read as the suites; ruling R-tl29-1 below.
- **No leg leaves the nightly or the trunk push.** Every suite on every
  leg there, as before tl29; what leaves the merge gate lands in them
  in the same commit.
- **Plants** are `tier pr` dispatches naming the cheapest suite
  (`gh workflow run ci -r tl29-plant -f tier=pr -f suites=census`: the
  plan job runs `tests/ci-plan` first), never a full matrix (RULES.md §7).
- **px53 is open** (pax#92, labelled, its full run in progress): its runs
  are never cancelled and its branch never touched. Both branches touch
  `ci.yml`, `tests/ci-plan` and the map in different hunks; whichever
  merges second rebases (`.github/`, `tools/ci-*`, `tests/ci-plan`).
- No build on nomad-1 and none needed (python3 and bash only); no host
  of the pool used. No merge, tag, issue filed or closed; no trailer of
  any kind; nothing under `~/.claude`; another lane's run never
  cancelled; `gh run watch` only with `--interval 60`.

## 2. Inputs, verified (2026-10-20, against origin)

| input | re-derived | drift |
|---|---|---|
| trunk | `d733bf4` (px52), `git rev-parse origin/trunk` | none |
| the tiers | `tools/ci-plan`: `full` = every suite, every leg (`legs` empty) on a push, the nightly, a dispatch, the `full-matrix` label and a FULL path; `pr` = the selected suites (every suite for a core or CI path) on `PR_LEGS` = `--tier native --firmware bios`; `noop`. A dispatch naming suites is named `full` or `pr` by its `tier` input | none |
| the legs | each suite job runs `tests/<suite> $PAX_LEGS`; empty = native and release × BIOS and UEFI, in one job, one after another | none |
| the verdict | `tools/ci-plan --verdict`: chosen suites green, the others skipped; it does not check that a `full` run chose every suite | a one-suite dispatch is a green `tier full` (tl21's note in `lane-audit.sh`) |
| a red nightly | nothing: pax has no issue step (grep of `ci.yml`, `tools/`) | tl28's `ci/nightly-red.sh` (pelt, wolf-std, …) is the shape to copy |
| `lane-audit.sh` | planning `560c78f`: pax in `TIERED`; a green `tier full` or `tier release` from a `pull_request` or `push` run at the head; the `full-matrix` label on the PR | it knows no `tier all` |
| the plan | GitHub Team since 2026-10-20: the org record's `updated_at` is **18:13:58Z** (`gh api orgs/wolffe-lang`), the crawl's entry `560c78f` 18:24:32Z; GitHub's limits page: Free 20 concurrent jobs, 5 macOS; Team 60, 5 macOS | the switch time is the org record's, the nearest the API gives; nothing in the runs shows it (below) |
| open PRs | pax#92 px53 (`full-matrix`) | §1 |

## 3. The measurement, before the plan change

Every org repo (18; `wollf-heldout` has no runs), from the Actions API
(`notes/tl29/fetch.py`, `fetch_repo.py`; jobs `filter=latest`, cached once
completed). **Before**: each repo's last 30 runs created before
2026-10-20T18:13:58Z, every workflow, every event (fewer where the repo
has fewer: lope 16, yew 25). **After**: every run created since, re-read
at hand-back (§7). Per run (`notes/tl29/measure.py`):

- **wall**: the run's `created_at` to its last job's `completed_at`;
- **queue** (the contract's): `created_at` to the first job's
  `started_at`. It is ~0 on every tiered repo, because the first job is
  the one-minute `plan`, so beside it:
- **slot wait**: the longest any one job of the run waited for a runner
  (a job's `created_at` is when its needs were met; to its `started_at`);
- **job-minutes**: the sum of every job's `completed_at − started_at`;
  macOS minutes the same, macOS jobs only.

A job with no runner never ran (skipped, or cancelled in the queue:
GitHub still stamps it started and completed) and counts nowhere. A
cancelled run, and a re-run (its wall holds the wait before someone
re-ran it; its carried-over jobs keep the first attempt's times under the
new attempt's `created_at`), is counted and its job-minutes summed, never
in a median.
A run is the tier its verdict job names; a verdict that never ran is
"(cancelled before the verdict)".

Headline (medians; job-minutes' sum over the rows' runs in brackets):

| repo | tier | runs | wall med / p90 | slot wait med | job-min med (sum) | macOS-min med |
|---|---|---:|---:|---:|---:|---:|
| pax | tier full | 21 | 52 / 91 | 10.0 | 421 (6,010) | 0.7 |
| pax | tier pr | 5 | 17 / 125 | 1.5 | 95 (360) | 0.0 |
| wolf-interp | tier full | 13 | 200 / 230 | 9.1 | 1,438 (17,973) | 369 |
| wolf-interp | tier pr | 6 | 133 / 168 | 28 | 415 (2,416) | 11 |
| wolf-lang | tier full | 7 | 62 / 140 | 25 | 148 (1,014) | 75 |
| wolf-lang | tier pr | 4 | 58 / 106 | 33 | 49 (185) | 0.0 |
| wolf-std | (every run) | 30 | 57 / 103 | 7.3 | 131 (3,128) | 40 |
| pelt | (every run) | 30 | 39 / 98 | 6.3 | 61 (1,307) | 35 |
| lobo | (every run) | 30 | 31 / 75 | 5.1 | 40 (882) | 22 |
| wolf-book | (every run) | 30 | 18 / 91 | 2.5 | 58 (1,121) | 7.5 |

Every repo, every tier: `notes/tl29/measure-before.md` (the table) and
`measure-before.tsv` (with each row's run ids). The re-run at hand-back,
before and after side by side, is §7.

**What held the runs up.** Over the 42.2 hours before the switch with
every run of every repo in the cache (2026-10-19T00:00Z on;
`notes/tl29/saturation.py`, `saturation-before.txt`): **all 20 of the
free plan's slots were in use 8.9 h (21%)**, and **all 5 macOS slots
10.3 h (24%)**. Of 1,498 Linux jobs the median waited 1.1 min for a
runner, the 90th percentile 35.0, the longest 184.4 (16,333 job-minutes of
waiting); of 330 macOS jobs the median waited **7.3 min**, the 90th
percentile **60.9**, the longest 145.7 (a re-run's carried-over jobs read
no wait). The org never had more than 20
jobs running at any instant before the switch, nor (yet) after it: the
switch shows in no run, only in the org record. The Team plan lifts the
Linux cap to 60; it leaves the macOS cap at 5, which was full a quarter of
the time, and which wolf-interp's merge gate held four of for 76–124
minutes at every merge (its `ci/tl29.md`).

## 4. The legs: which caught a red no other leg caught

The last 60 `tier full` runs (2026-10-14T01:44Z to 2026-10-20T16:02Z:
`notes/tl29/legs-last60.tsv`, by `legs_table.py`): 17 labelled pull
requests, 13 trunk pushes, 7 nightlies, 23 dispatches. For every failed
suite job (and the first attempt of a re-run, which `filter=latest`
hides), its log's `<suite>: FAIL` lines, each naming the legs whose words
it carries (`legs.py`: a tier word and no firmware is both firmwares, a
build; neither is unattributed).

| reds | runs | legs their FAIL lines name |
|---|---:|---|
| planted breaks (the dispatches of px42 to px52) | 20 | **native BIOS in every one**: all four legs in 14 (two in px46's runs, cancelled after the suite failed), native BIOS alone in 6 (px42–px44's mpx5-users rows) |
| dispatches with no red | 3 | two cancelled before a suite failed, one green (px41) |
| labelled pull requests | 0 of 17 | every one green at its first attempt |
| nightlies | 0 of 7 | — |
| trunk pushes | 2 of 13 | one leg each, below |

The two reds of a merged tree, each **the same sha green in its pull
request's full run hours before**:

- **39086412018** (push `b274030`, px50's merge; job 117553911760,
  mpx4-udp): native UEFI `user` alone, U1–U9, an empty serial log. px52
  read its artifact: QEMU's one line `Could not set up host forwarding
  rule 'udp:127.0.0.1:37606-:7'`, a port taken in the ephemeral range:
  pax#86, **the harness, not the kernel and not UEFI**
  (`notes/px52-the-small-fixes.md` P4), fixed in px52. Its pull request's
  `tier full` 39081365475 at `b274030`: green.
- **38935970457** (push `654c9ec`, px46's merge; job 117091600956,
  mpx4-lobo): native BIOS alone, `L3 native bios load: 1 rows failed`
  (`R10 flat: moved: kernel less 32 kB a thread 7112 -> 7288 kB`, the
  load census). Its pull request's `tier full` 38811441834 at `654c9ec`:
  green. Native BIOS is the merge gate's leg either way.

So **in the last 60 full runs no leg caught a defect that native BIOS
missed**: the one red on another leg was a harness race that lands on
whichever boot draws the taken port, and every planted break was seen on
native BIOS. Just outside the 60 the same holds: 38475501062's first
attempt (px40's label run, 10-13; job 115565184433) was red on release
BIOS alone, `lobo-session: no serial socket`: pax#53, two forwards given
one host port, px41's harness race (`notes/px41-the-runner-flakes.md`).

**Before tiering** (2026-10-12/13, before px37, every push of every lane
ran every leg: the 31 failed suite jobs of 25 runs read, the same way) the reds that named one
leg other than native BIOS were each a timing artefact of a loaded
runner, found and fixed in the harness or restated with its reason:
release BIOS's `O5 wide: cost 52% of real time` (38208203649, px32's
real-time gate), K8 chord `[0, 4]` ticks (38322266282, pax#45), the load
census at −15 (38326787732, pax#47), two request timeouts in lobo's
control row under load (38222405571, a px25 plant's run whose planted red
was elsewhere);
release UEFI's T11 (38192937184, pax#29 (3): **net-peer's** fast
retransmit past its own SND.MAX, the harness's TCP, not PAX's;
`notes/px35-the-green-trunk.md`). The release tier runs faster code, so
its timings differ; nothing PAX does differed.

**What this does not show.** A defect only release codegen or the UEFI
memory map would expose has not happened in this window; the argument
for keeping those legs somewhere is a priori, and they stay on every
trunk push (the hour after the merge) and every nightly, whose red now
opens an issue. And a toolchain pin or a harness tool (the map's FULL
paths) changes every leg's build or boot at once, so a pull request that
touches one still runs every leg (§5).

## 5. The shape, and the prediction (committed before the first change)

**Choice: the label buys the merge legs; every leg stays on trunk, the
nightly, a dispatch and a FULL path.** The contract's other option, a
`legs` input on the label, is not a thing GitHub has (a label carries no
input); a dispatch does, so `-f tier=all` is how a lane asks for every leg
on its branch before the merge, and nothing else is needed.

| tier | suites | legs | when |
|---|---|---|---|
| `all` | every suite | every leg (`legs` empty) | a push to trunk, the nightly, a dispatch (the default), a pull request touching a FULL path (labelled or not) |
| `full` | every suite | `MERGE_LEGS` = `--tier native --firmware bios` | the `full-matrix` label (the merge gate); a dispatch `-f tier=full` |
| `pr` | the change's (every suite for a core or CI path) | `PR_LEGS` = `--tier native --firmware bios` | any other pull-request run; a dispatch `-f tier=pr` |
| `partial` | the suites a dispatch names | its `tier` input's legs | `-f suites=…` (a plant) |
| `noop` | none | — | another label's `labeled` event |

**Why `full` keeps the merge's name.** On every tiered repo `tier full` is
the merge gate and what it holds is the repo's: wolf-interp's is ubuntu,
macOS and one windows smoke since is78 (and one macOS smoke after tl29),
pax's is now every suite on native BIOS. A lane's step is unchanged (add
`full-matrix` at the head to merge; wait for `tier full`), and
lane-audit's rule reads the same; it learns `tier all` as the superset, as
it learned wolf-interp's `tier release`. **`partial`** is new so that
`tier full` always means every suite: today a one-suite dispatch is a
green `tier full`, and the audit has had to exclude dispatches to stay
honest; the verdict now refuses a `full` or `all` that chose fewer than
every suite or ran other legs than its tier's.

**A red nightly opens an issue** (`tools/nightly-red`, tl28's
`ci/nightly-red.sh` cut to pax, run by the `tier` job's last step on a
red `schedule` run only): one open issue, `nightly red: ci on trunk`,
label `nightly-red`, a comment for each further red night; the next lane
on pax owes it (the crawl's rule).

**Prediction.** The merge gate's run is every suite on the one leg every
pull request already runs: the shape of a `tier pr` run that touched CI
(every suite on the pr leg), measured at px49's 39058414358 (111.4
job-minutes, 31.6 min wall), 39060792129 (106.8, 25.1) and px52's
39318853869 (124.3; 125 min wall of which 115 waiting for a slot), the
longest job mpx5-users at 19–22 min. Against the last ten
non-dispatched `tier full` runs before the switch (39453863096 …
39086412018): **449 job-minutes median, 76 min wall (p90 110)**, the
longest job mpx5-users at 65 min.

- **`tier full`** (the label): **32 suite jobs + plan + verdict as now;
  105–130 job-minutes** (falsified above 160), **wall 22–35 min** with a
  free runner (falsified above 45 with a slot wait under 5 min): about
  **−330 job-minutes (−73%) and −40 to −50 min a labelled run**. macOS
  unchanged (`macos-run`, 0.5–0.9 min).
- **`tier all`** (a trunk push, the nightly): unchanged, 430–480
  job-minutes, the four legs.
- **`tier pr`**: unchanged.
- **Per merge**: the labelled run 449 → ~120; the trunk push's 449
  stays. What a merge no longer proves before it lands is release
  codegen and the UEFI boot on every suite: the trunk push proves them
  within the hour and the nightly every day; a red one opens an issue.
- This lane's own runs: its PR touches CI, so its `tier pr` run is every
  suite on the pr leg, the shape of the new `tier full` job for job: that
  run is the measurement of the new gate (§6), and the labelled run, at
  the final head, is the orchestrator's.

**R-tl29-1 (asked; recommended and implemented):** the contract's "never
touch a repo's tests, only its workflows, `tools/ci-tiers.map` and
`lane-audit`" is read as **the suites**: the planner (`tools/ci-plan`) and
its own proof (`tests/ci-plan`) change together, as every lane that moved
the planner has done (px37, px40, px51, px53), because the contract's
change is the planner's and a planner whose proof still asserts the old
shape fails its own plan job. No suite script or assertion of PAX moves.
