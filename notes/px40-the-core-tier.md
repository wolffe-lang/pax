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

**The planted break** (the planner's new cases, red before the map
changed): branch `px40-plant` at `35ae34d` is this branch at the commit
that adds the cases and nothing else. Dispatch run 38471236869
(`-f suites=census`): `tests/ci-plan` exit 1, 22 FAIL and 97 PASS; the
22 are the core-only case, the fifteen modules, the five `.S` and "the
core beside a narrow change", each `tier full, wanted pr`; every P1,
P3, P4, P5 and P6 check passed. The `plan` job failed, all 29 suites
were skipped and `tier unplanned` failed with "the plan did not succeed
(failure)". The next commit, `8d2c09a` (the map), turns the 22 green:
`tests/ci-plan` exit 0 locally and in every run after it.

**The second plant** (the new P4 check on the concurrency group):
branch `px40-plant-b` at `a28716c` gives every run that is no pull
request's one shared group. Dispatch run 38471434401: one FAIL, "P4 a
run that is no pull request's has a group of its own run id"; plan
failed, `tier unplanned` failed.

**The core-only example**: draft PR #50, branch `px40-core-example` at
`5bbdb4b`, one comment line appended to `kernel/sched/sched.lu`, base
`px40` (so the plan read this branch's map). Run 38471672350: the plan
printed `kernel/sched/sched.lu -> ` every suite, `1 path(s): pr tier,
29 suite(s), legs --tier native --firmware bios`; 31 jobs, all green,
`tier pr`, **72.4 job-minutes**, 13.3 minutes of wall clock. PR #50 was
closed and the branch deleted once the run was measured. Before px40
the same change planned the full tier: 275 by px37's table, 238.1 and
247.0 as measured at `58428ba` (§2). 72.4 is 26% of 275 and 29% of
247.0.

**Predictions against what happened** (§3): 1 held (22 FAIL, all core
cases). 2 held: `tools/ci-plan` changed in its text only (`git diff
58428ba -- tools/ci-plan` touches the docstring). 3 held: 72.4, inside
59 to 75. 4 is in the PR, where the runs at the head are named (a
commit naming them would move the head). 5 held: §B is the write-up.

**This PR's own runs** (the pr tier at the head, then the labelled full
run) are in the PR's text for the same reason.

## A. What the map says, by class of path

| class | paths | a pull request's run |
|---|---|---|
| the pins | `kernel/wolf.pin`, `kernel/wolf.pkg`, `boot/limine.pin` | full: 29 suites, four legs |
| the harness tools | `tools/{lib.sh,build-kernel,mkimage,fetch-wolf,fetch-limine,qemu-halt,qemu-run,qemu-fault,expect-serial}` | full |
| the kernel's entry (unchanged; the ruling names neither way) | `boot/start.S`, `boot/kernel.ld`, `boot/limine.conf` | full |
| a path no rule and no test's text knows | anything new in a new place | full |
| a diff that cannot be read | no base or head, or `git diff` fails | full |
| **the kernel's core (px40)** | `kernel/{serial,log,panic,boot_info,frames,paging,gdt,idt,interrupts,apic,timer,heap,sync,sched,fpu}/`, `boot/{io,cpu,isr,sched,fpu}.S` | **pr: 29 suites, `--tier native --firmware bios`** |
| CI itself | `.github/`, `tools/ci-plan`, `tools/ci-tiers.map`, `tests/ci-plan` | pr: 29 suites, one leg |
| user mode, the network, sound, the screen, one suite's own | as px37's table | pr: the suites that run it, one leg |
| prose | `notes/`, `*.md`, licences | pr: no suite |

FULL wins over the core: a pin, a harness tool or an unknown path
beside a core change is a full run (`tests/ci-plan` P3, three cases).
The `full-matrix` label, a trunk push, the nightly and a dispatch are
full whatever changed. Nothing about the merge rule moved.

One judgement of this lane's, for the orchestrator to confirm or
reverse: `boot/start.S`, `boot/kernel.ld` and `boot/limine.conf` stay
FULL. The ruling lists fifteen modules "and their `.S`" and keeps the
pins and the harness tools full; these three are neither. `start.S`
holds the Limine requests that boot_info reads, so it could be read as
boot_info's `.S`; it is also the one assembly file whose behaviour
differs by firmware, which the pr leg (BIOS only) does not see. Left
as it was; moving it is three lines of the map and three of the test.

## B. The shared kernel-build job: not landed; what it would take

px37 left one lever untaken: a job that builds each kernel once and
feeds the suites' `--images` option, "could halve the full tier". No
line of it is in this branch. Measured, it is neither small nor worth
half:

**What a full run spends on builds.** From the log of trunk's full run
at `58428ba`, 38361626836 (247.0 job-minutes), each suite's time from
the start of its test step, or its previous `built` line, to each
`built` line (so a suite's first figure includes making its programs
and initramfs):

| suite | images or kernels built (both tiers) | native (min) | release (min) |
|---|---:|---:|---:|
| mkw | 6 | 0.0 | 0.0 |
| mpx1 | 6 | 0.4 | 8.5 |
| mpx2-frames | 8 | 0.3 | 7.7 |
| mpx2-paging | 2 | 0.2 | 1.7 |
| mpx2-interrupts | 10 | 0.5 | 11.6 |
| mpx2-sched | 4 | 0.2 | 2.6 |
| mpx2-heap | 12 | 0.4 | 16.9 |
| mpx3-user | 6 | 0.3 | 7.9 |
| mpx3-loader | 2 | 0.1 | 1.4 |
| mpx3-boreutils | 2 | 0.7 | 2.8 |
| mpx3-console | 4 (one ELF a tier) | 0.3 | 2.5 |
| mpx3-screen | 6 | 0.4 | 5.1 |
| mpx3-shell | 8 (one ELF a tier) | 1.5 | 2.6 |
| mpx3-threads | 4 (one ELF a tier) | 0.1 | 2.6 |
| mpx3-tree | 8 (one ELF a tier) | 1.1 | 1.7 |
| mpx3-speaker | 2 | 1.0 | 2.5 |
| mpx3-sound | 2 | 0.7 | 2.5 |
| mpx3-orchestra | 2 | 1.3 | 2.5 |
| tour | 4 | 0.2 | 3.1 |
| mpx4-net | 2 | 0.1 | 5.2 |
| mpx4-udp | 2 | 0.2 | 1.2 |
| mpx4-tcp | 2 | 0.2 | 1.4 |
| mpx4-ready | 2 | 0.2 | 1.4 |
| mpx4-session | 2 | 0.9 | 1.3 |
| mpx4-unix | 6 (one ELF a tier) | 1.2 | 2.5 |
| mpx4-lobo | 3 | 3.4 | 2.4 |
| **all** | **117** | **16.0** | **101.6** |

(`notes/px40/builds-38361626836.txt` is the script's output,
`notes/px40/builds.py` the script.) Builds are 117.6 of the 247.0
minutes, 101.6 of them the release tier's.

**What sharing could save.** A shared job saves only a build that some
other job also makes. The table's 117 are 113 `built` lines that print
an ELF digest and tour's four kernels, which print none. A suite that
wraps one ELF in several images prints it once an image, and builds it
once. By digest each tier has 35 distinct kernels (34 printed, tour's
two counted as one). The kernels more than one job builds: `kmain_console` is built by nine
suites (mpx3-console, -screen, -shell, -threads, -tree, -speaker,
-sound, -orchestra, mpx4-unix), `kmain_sockets` by three (mpx4-udp,
-tcp, -ready), `kmain` by two (mpx1, mpx2-frames), `kmain_session` by
two (mpx4-session, mpx4-lobo). The time spent in a build whose ELF
another job also built is **25.7 release minutes and at most 7.3
native** (the native figure is mostly the first-build gaps, which are
programs and initramfs, not the kernel). The ceiling is therefore about
26 to 33 of 247 job-minutes, **11 to 13%**, before the shared job's own
setup and the artifact upload and 25 downloads are paid; on the pr leg
(72.4, run 38471672350: 16.1 minutes of builds, at most 8.0 repeated)
it is under 8 minutes and likely nothing after overhead. It is not
half: the release tier costs what it costs because there are 35
different kernels, each built once already. Halving the full tier would
take not building at all (a cache of ELFs across runs keyed by the
kernel's tree and the pin), which the workflow's own first rule
forbids ("fetched and checked by digest on every run, never cached").

**Would the suites test the same bytes?** For the kernel, yes, and the
logs already show it: in run 38361626836 the nine jobs that build
`kmain_console`, on nine runners, print one ELF digest a tier (native
`514823850767…`, release `02dda5cf493d…`); `kmain_sockets` (native
`faaa8f9d5151…`, release `f17cfc569e2f…`) and `kmain` (native
`5f926e328068…`, release `1fcd1612ee18…`) likewise. The build is
reproducible across runners at one tree and one pin. This lane built no
kernel itself; the ISOs were not compared, and need not be the same
across suites (each wraps its own programs and Limine configuration).

**Why it is not small.** `--images DIR` means "boot what this script
built earlier": `DIR/<tier>/<name>.{iso,elf}`, with each suite's own
initramfs, programs, Linux-side recordings and Limine configuration
inside the ISO. So:

1. A shared job that only builds ELFs cannot feed `--images`; every
   suite would need a new way in (take the ELF, make the rest), which
   is an edit to 25 test scripts' build sections.
2. With `--images` a suite skips its build step, and that step carries
   assertions: `build-kernel`'s (no SSE, no red zone, the import list,
   the runtime archive) reported as each suite's first PASS lines (56
   lines of run 38361626836 name them). Fed
   images, those PASS lines stop being printed by the suite: the
   assertions would have to move into the shared job and the verdict
   would have to count them there. That changes what each suite's job
   asserts, which this lane's contract forbids.
3. A shared job makes every suite wait for it: little on the pr leg
   (a native kernel is seconds), but `kmain_console` release
   is two and a half minutes and the longest release kernel four and a
   half, so on the full tier the shared job either builds 35 release
   kernels in sequence (about 76 minutes before the first boot, where
   today the slowest job is 22) or is itself a matrix of builds, which
   is a second planner.
4. Artifacts between jobs are a new failure the verdict has to read (a
   suite that booted a stale or missing artifact must be red, never
   skipped), and px37's three lessons would each need a new case.

**What would be small**, if the 26 minutes are wanted: one job that
builds `kmain_console` for both tiers (eight of the twelve repeated
release builds: 18.6 of the 25.7 minutes) and hands the ELF to the
nine suites through a `build-kernel` option that takes a prebuilt ELF
and still runs its assertions on it. That is a harness-tool change (a
full run by the map), nine script edits, and a digest check in each
suite against the shared job's printed digest. A lane of its own, with
its own plant (a suite handed the wrong ELF must fail).

## 5. Done-when

- [x] branch `px40` on origin, a fast-forward of trunk `58428ba`
- [x] `tests/ci-plan` exit 0 locally (P1 to P6) and first in every run's `plan` job
- [x] the planner's case red before the map changed: run 38471236869
- [x] a core-only example measured (run 38471672350, 72.4), its PR #50 closed, its branch deleted
- [x] the shared build: written up (§B), nothing of it landed
- [ ] PR open without the label; `tier pr` green at the head (in the PR)
- [ ] `full-matrix` added at the final head; `tier full` green there (in the PR)
- [ ] `lane-audit.sh pax px40 <PR>`: exit status read directly (in the PR)

Not filed (no issue is this lane's to file): none found. Left on
origin: `px40-plant`, `px40-plant-b` (evidence; never to be merged).
