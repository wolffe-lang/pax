# px40 — The core tier (a kernel-core change runs every suite on the PR leg)

Contract: px40's, `sprints/pax/40-the-core-tier/` in wolffe-lang/wolf
(planning commit `c7b99e6`, read 2026-10-13), with the rules of
`sprints/wave-53.md` down to `wave-45.md`. Branch `px40` in pax, cut
from pax trunk `58428ba` (px37 merged). §1 to §3 are committed before
the first change to the map, the planner or its test.

Ruling #76 (the maintainer, 2026-10-13): a pull request that touches the
kernel's core (serial, log, panic, boot_info, frames, paging, gdt, idt,
interrupts, apic, timer, heap, sync, sched, fpu and their `.S`) runs
**every suite on the PR leg** (`--tier native --firmware bios`), not the
full tier. The pins (`kernel/wolf.pin`, `kernel/wolf.pkg`,
`boot/limine.pin`) and the harness tools stay FULL, as do a path no rule
knows and a diff that cannot be read. The merge rule does not change:
the `full-matrix` label once the head is final, and a green `tier full`
run at that head.

One deliverable: `tools/ci-tiers.map` and `tools/ci-plan` say that,
`tests/ci-plan` has a case for each class, and `CLAUDE.md` and
`notes/px37-the-ci-tiers.md` say so. A second item is optional: px37's
untaken lever, one shared kernel-build job feeding the suites'
`--images` option, landed only if it is small and the suites provably
test the same bytes; otherwise written up (§B) and not started.

## 1. Forbidden, absolutely

- No test script's assertions change. No suite leaves the full tier:
  every job that runs on a trunk push, the nightly and the labelled run
  today runs there after this lane, on every leg.
- Nothing under `kernel/` is edited (px39 is in flight there). The one
  exception is the throwaway core-only example, a one-line comment on a
  branch of its own that is never merged, whose draft PR is closed and
  whose branch is deleted when its run has been measured.
- The map edit is tight: the core's lines change their target in place;
  no line is moved, so px39's line or two for its new suite rebases
  cleanly. One rebase, when the work is otherwise ready, if trunk moved.
- The planner's new case is seen red in a commit and a CI run of its own
  before the map changes. "Seen red" cites the run.
- No kernel build on nomad-1. No `rm` outside `~/lanes/px40/`; no
  scratch in `/tmp`; no `git add -A`; nothing under `~/.claude`; no
  `2>/dev/null` on a checkout; no commit or PR trailer.
- No merge, no tag, no issue filed or closed (listed instead). No run
  cancelled that is not this lane's own; its own superseded runs are
  listed. The PR is opened without the `full-matrix` label.
- The shared-build item is not half-landed: it lands whole with digest
  evidence, or §B says what it would take and no workflow line of it is
  committed.

## 2. Inputs, verified (2026-10-13)

- pax trunk is `58428ba` (`git rev-parse origin/trunk`), px37's merge;
  the contract says `58428ba` or later. No drift.
- `tests/ci-plan` passes at `58428ba` on this checkout (exit 0; P5:
  every one of 2,427 tracked paths is known).
- The workflow has 31 jobs: `plan`, 29 suites, `tier`.
- px37's figures, re-derived from the jobs API (sum of each job's
  completed minus started): its `tier pr` run 38357428374 is 31 jobs,
  67.3 job-minutes; its `tier full` run 38358775457 is 31 jobs, 238.1;
  trunk's push run at `58428ba`, 38361626836, is 247.0. The **275** the
  contract and px37's note compare against is px37's table (274.6: run
  38226524690's 251.2 plus mpx4-lobo's 23.4 from run 38277342063), a
  sum over two runs; the two full runs measured at `58428ba` are 238.1
  and 247.0. Reported, not absorbed: this note quotes 275 as "the old
  figure" and the measured 238 to 247 beside it.
- Today's map: the core's 15 module directories and `boot/{start,io,
  cpu,isr,sched,fpu}.S`, `boot/kernel.ld`, `boot/limine.conf` are FULL
  with the three pins and nine harness tools. The map already has the
  target this ruling needs: `ALL`, every suite on the pull-request leg
  (px37 gave it to CI's own files).
- px37's three carried lessons are in the tree and held by
  `tests/ci-plan`: the verdict job's `if: ${{ !cancelled() }}` (P4);
  each `needs` output read with a default in `tools/ci-plan --verdict`
  (P6, nine cases); `cancel-in-progress` for pull requests only (P4).
  The unique group for non-PR runs (`format('ci-{0}-{1}',
  github.event_name, github.run_id)`) is in `ci.yml` but no check
  reads it.
- Which `.S` is the core's, from a grep of each file's global names
  over `kernel/*/`: `boot/io.S` (serial, timer, panic), `boot/cpu.S`
  (paging, apic, interrupts, sched), `boot/isr.S` (gdt, idt, timer),
  `boot/sched.S` (sched, sync, interrupts), `boot/fpu.S` (fpu); modules
  outside the core call some of them too. `boot/start.S` is the Limine
  entry and requests (its names are read by boot_info and paging); with
  `boot/kernel.ld` and `boot/limine.conf` it is how the kernel is
  entered, linked and loaded, which the ruling's list does not name.
- The `full-matrix` label exists in the repository.

## 3. Prediction (committed before the first change)

1. Adding the case "a core-only change (`kernel/sched/sched.lu`): the
   pr tier, every suite" to `tests/ci-plan` against today's map fails
   that case, and only cases this ruling moves: the planner answers
   `full`, the test wants `pr`. Falsified if the test passes, or if a
   P1, P4, P5 or P6 check fails with it.
2. The planner needs no new mechanism: changing the core's lines from
   FULL to ALL in the map is the whole behaviour change. Falsified if
   `tools/ci-plan`'s code (not its text) has to change for the cases to
   pass.
3. A core-only pull request (one comment line in `kernel/sched`)
   selects `tier pr`, 29 of 29 suites, 31 jobs, and costs **67 ± 8
   job-minutes** (px37's 67.3 for a workflow change is the same
   selection). Falsified outside 59 to 75, or by any other selection.
4. This lane's own PR push (workflow, planner, map, test): the same
   selection, 59 to 75 job-minutes. Its labelled full run: 230 to 255
   (238.1 and 247.0 measured at `58428ba`).
5. The shared-build item will not be small: 25 suites take `--images`,
   and that option skips the suite's own build step, which carries
   `build-kernel`'s assertions (each suite's first PASS lines). Expected
   outcome: the write-up. Falsified if it lands.

## 4. Evidence index

(filled as the runs complete)

## 5. Done-when

(filled at the end)
