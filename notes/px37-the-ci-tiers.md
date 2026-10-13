# px37 — The CI tiers (fast per push, full at trunk, nightly and before merge)

Contract: px37's, `sprints/pax/37-the-ci-tiers/` in wolffe-lang/wolf
(read 2026-10-12). Branch `px37` in pax, cut from pax trunk `6316c51`
(px32 merged); rebased onto `feba3fc` (px25 merged, which added
`mpx4-lobo`: 29 suites since), then once more onto `c86ba5e` (px33 and
px33b merged: `user/play/parts-test/replay`, read by mpx3-orchestra,
falls under `user/play/*`, sound's four suites; `tests/ci-plan` P2),
and onto `89f04a9` (px36 merged: `user/console/shell-changes.keys` is
mpx3-tree's by the test's own text, with the other suites that read
`user/console`; P2), and last onto `c3e3fc2` (px35 merged:
`tests/paxtcp-selftest`, a step of the mpx4-tcp job with no leg of its
own, is mpx4-tcp's by that job's text and runs whenever mpx4-tcp does;
mpx4-net's new renew step is part of its peer boot on every leg; P2).
Last, onto `fe7c05b` (px38, notes only).

**Changed by px40 (ruling #76, 2026-10-13; `notes/px40-the-core-tier.md`):**
a pull request that touches the kernel's core runs every suite on the
pr leg, no longer the full tier. The tables of §1, §2 and §4 below say
what holds now; the pins, the harness tools, the kernel's entry
(`boot/start.S`, `boot/kernel.ld`, `boot/limine.conf`), an unknown path
and an unreadable diff are still full, and the merge rule is unchanged.

One deliverable: pax CI in tiers, with no loss of coverage before a
merge to trunk. Measured on 2026-10-12 a green run was 28 jobs and 251
job-minutes; the org has 20 concurrent jobs for every repository, and
every push of every pax lane, planted breaks and superseded heads
included, paid the whole of it.

## 1. What runs when

| event | tier | suites | legs |
|---|---|---|---|
| push to trunk | full | all 29 | all four |
| nightly (`schedule`, 06:17 UTC, trunk) | full | all 29 | all four |
| pull request labelled `full-matrix` (any push, or adding the label) | full | all 29 | all four |
| pull request touching a FULL path (below: a pin, a harness tool, the kernel's entry) | full | all 29 | all four |
| pull request touching the kernel's core or CI itself (px40) | pr | all 29 | `--tier native --firmware bios` |
| any other pull-request push | pr | those the change can affect | `--tier native --firmware bios` |
| pull request touching only prose (`notes/`, `*.md`, licences) | pr | none (the plan and the verdict only) | — |
| `labeled` with another label | noop | none | — |
| `workflow_dispatch` | full (input `tier: pr` for the pr leg) | all, or input `suites` | per `tier` |

A leg is one compiler tier on one firmware: native or release, BIOS or
UEFI. Every suite already took `--tier` and `--firmware` (each test's
usage line); px37 changes no test.

**The merge rule.** A lane's PR is merged only with a green *full* run
at its head. The lane gets one by adding the `full-matrix` label once
the head is the one to merge; every later push to a labelled PR runs
full again. Open the PR without the label (`opened` and `labeled` may
both fire for a PR created with it, and the second full run would
cancel the first). The last job of every run is named `tier full` or
`tier pr`: that name is how a reader, or `lane-audit`, knows which tier
a green run was.

**Superseded runs.** A pull request's runs share a concurrency group
per branch and tier with `cancel-in-progress`: a new push cancels the
run of the head it replaces. The pr and full groups are separate, so
adding the label never cancels the pr run at the same head. Trunk
pushes, the nightly and dispatches get a group of their own run id:
never cancelled, never replaced while pending (a shared group would
keep only the newest pending run, and each trunk push's full run is the
coverage that merge is owed). The setting applies to runs started after
it lands; no run already queued was touched. The verdict job runs on `!cancelled()`, not
`always()`: under `always()` a superseded run (38275354849, this lane's
first pr-tier run) cancelled its suites but kept its verdict job queued,
which held the group and left the newer run pending behind it.

**Planted breaks.** A plant needs only the suite it breaks:
`gh workflow run ci -r <plant-branch> -f suites=<job>` runs that one job
on every leg (`-f tier=pr` for the pr leg alone) instead of 251 minutes.

## 2. The path mapping

`tools/ci-plan` reads the changed paths (`git diff` of the PR's base and
its merge commit) and selects, for each, the union of:

- every rule of `tools/ci-tiers.map` whose glob matches;
- `tests/S` and `tests/S.d/…`: suite S;
- `kernel/kmainNAME.lu`: each suite whose script names `kmainNAME`;
- any `tools/`, `user/`, `boot/`, `font/`, `kernel/` or `tests/` path a
  suite's script, its job's block in `ci.yml`, or a tool the script
  names (followed through the tools those name) mentions, or a
  directory above it.

FULL wins. A path nothing matches is FULL. `macos-run` runs with `proof`.

Why kernel modules are mapped by hand: every kernel imports every
module. The import closure of each of the 31 kmains, computed from the
`use` lines, is 43 to 47 of the 47 modules (`kernel/interrupts` reaches
the system-call table, which reaches everything), so imports cannot
choose. The map names the suites that *run* a module's code. A change
that breaks the *build* fails in any suite, since each compiles the
whole package.

| area | paths | suites (pr tier) |
|---|---|---|
| pins, entry and harness: FULL | `kernel/wolf.pin`, `kernel/wolf.pkg`, `boot/limine.pin`; `boot/limine.conf`, `boot/start.S`, `boot/kernel.ld`; `tools/{lib.sh,build-kernel,mkimage,fetch-wolf,fetch-limine,qemu-halt,qemu-run,qemu-fault,expect-serial}` | all 29, all legs |
| the kernel's core (px40; FULL before) | `kernel/{serial,log,panic,boot_info,frames,paging,gdt,idt,interrupts,apic,timer,heap,sync,sched,fpu}`, `boot/{io,cpu,isr,sched,fpu}.S` | all 29, pr leg (the label's full run before merge covers the rest) |
| CI itself | `.github/`, `tools/ci-plan`, `tools/ci-tiers.map`, `tests/ci-plan` | all 29, pr leg (the label's full run before merge covers the rest) |
| user mode | `kernel/{user,process,elf,files,initramfs,signal,futex,rtc,vm,uaccess,procfs,tree,ready,event,console}`, `boot/{user,console,tree,event}.S`, `user/programs.S`, `tools/mkinitramfs` | every mpx3-* and mpx4-* (18) |
| network | `kernel/{net,netd,arp,ip,icmp,udp,tcp,socket,unix}`, `boot/{net,unix}.S`, `user/net/`, `user/unix/`, `user/mpx4-*.run` | mpx4-net, -udp, -tcp, -ready, -session, -unix, -lobo |
| lobo (px25) | `user/lobo/`, `tools/lobo-*`, `tools/mklobokit`; `user/lobo.pin` also mpx4-unix | mpx4-lobo |
| the bus and transport | `kernel/{pci,virtio}` | network's seven + mpx3-sound, mpx3-orchestra |
| sound | `kernel/{speaker,sound}`, `boot/{speaker,sound}.S`, `user/{play,tunes,scores,sound}/` | mpx3-speaker, -sound, -orchestra, mpx4-session |
| the screen | `kernel/{fb,screen}`, `boot/{screen,font}.S`, `font/spleen-8x16.bdf` | every suite booting kmain_console or kmain_session, and tour |
| one suite's own | `kernel/schedtest` → mpx2-sched, tour; `kernel/heapthreads` → mpx2-heap; `kernel/pax_tour` → tour; `boot/stub/`, `tools/qemu-gdb`, `tests/gdb-attach` → proof; `tests/expect-serial-selftest` → proof, mkw, mpx1; `tools/census/`, `docs/CENSUS.md` → census | as named |
| prose, and a hand-run probe | `notes/`, `*.md`, `LICENSE*`, `tools/tw-probe` | none |
| everything else | derived from the tests' text (kmains, tools, user programs, Limine configurations, key files) | the suites that read it |

Each of the 2,312 tracked paths at `c3e3fc2` plus px37 is known to the map or read
by a suite (`tests/ci-plan` P5). A new file in a new place is FULL until
a rule names it.

`tests/ci-plan` (run first in the `plan` job) proves the tiers by event
(P1), one change per area selecting its suites and nothing else (P2),
every suite on the pr leg for the core (P2, px40), FULL for the pins,
the harness, the kernel's entry, an unknown path and an unreadable diff
(P3), the wiring of every job (P4), the map's
coverage of the tree (P5, a warning), and the verdict (P6). Seen red: below, §5.

## 3. The legs: measured

From the log of pr run 38226524690 (px32's head, green, 251.2
job-minutes), each suite's time split by its own PASS lines. The
release tier's LLVM build is 125.6 of the 251.2 minutes: each suite
builds its own kernels, and a release kmain takes about three minutes
(mpx2-heap builds six: 18.0 minutes).

| suite | full (min) | release builds | pr leg (est.) |
|---|---:|---:|---:|
| proof | 0.5 | — | 0.5 |
| macos-run | 0.6 | — | 0.6 |
| mkw | 0.7 | 0.0 | 0.3 |
| mpx1 | 13.1 | 11.7 | 1.0 |
| census | 0.1 | — | 0.1 |
| mpx2-frames | 15.2 | 13.7 | 0.8 |
| mpx2-paging | 2.7 | 1.8 | 0.5 |
| mpx2-interrupts | 14.1 | 12.0 | 1.2 |
| mpx2-sched | 6.5 | 5.4 | 0.7 |
| mpx2-heap | 19.8 | 18.0 | 1.0 |
| mpx3-user | 7.6 | 6.2 | 0.9 |
| mpx3-loader | 2.3 | 1.3 | 0.7 |
| mpx3-boreutils | 2.8 | 1.5 | 1.0 |
| mpx3-console | 6.9 | 4.1 | 1.3 |
| mpx3-screen | 9.8 | 7.2 | 1.2 |
| mpx3-shell | 11.2 | 2.5 | 3.3 |
| mpx3-threads | 9.1 | 4.3 | 1.6 |
| mpx3-tree | 11.2 | 4.2 | 3.1 |
| mpx3-speaker | 9.6 | 4.2 | 3.4 |
| mpx3-sound | 5.0 | 2.5 | 1.4 |
| mpx3-orchestra | 25.3 | 4.2 | 7.4 |
| tour | 13.8 | 8.0 | 2.0 |
| mpx4-net | 5.5 | 2.9 | 0.9 |
| mpx4-udp | 4.5 | 1.4 | 1.4 |
| mpx4-tcp | 14.9 | 1.6 | 5.1 |
| mpx4-ready | 25.6 | 1.0 | 8.2 |
| mpx4-session | 7.8 | 3.0 | 2.7 |
| mpx4-unix | 5.0 | 2.9 | 1.5 |
| mpx4-lobo (px25's run 38277342063) | 23.4 | 4.1 | 13.4 |
| **all 29** | **274.6** | **129.7** | **67.2** |

The pr leg is the job's setup, the native build and the native BIOS
boots. Native BIOS is the leg on which every suite runs its widest set:
mpx3-orchestra's study, marks, timbres and balance run on native BIOS
and release UEFI, its long and wide stresses on release BIOS alone;
mpx3-sound's scenarios past tone and ramp on native BIOS and release
UEFI; mpx3-speaker's tunes on native BIOS alone; mpx4-lobo's load, diff
and control on BIOS, its serve-release on native BIOS alone. What the pr leg does
not run (release codegen, UEFI's memory map, orchestra's stresses) the
full run before merge does.

Both firmwares on the native tier would be 90.9 (+24).

## 4. Before and after, per pull-request push

| change | before | after (pr tier, est.) | jobs |
|---|---:|---:|---:|
| network: `kernel/tcp/tcp.lu`, `tests/mpx4-tcp`, its note | 275 | 33.2 + plan + verdict ≈ 34 | 29 → 9 |
| music: `user/play/parts.lu`, `tests/mpx3-orchestra`, its note | 275 | 14.9 + plan + verdict ≈ 16 | 29 → 6 |
| notes only | 275 | plan + verdict ≈ 1 | 29 → 2 |
| CI itself (this lane) | 275 | ≈ 68; measured 62.0 (run 38297084222, on `feba3fc`) | 31 |
| a FULL path (pin, harness, the kernel's entry) | 275 | 275 + plan + verdict | 31 |
| the kernel's core (px40) | 275 | every suite on the pr leg; measured in `notes/px40-the-core-tier.md` | 31 |

A real notes-only change: px38 (`c3e3fc2..fe7c05b`, 115 paths, all under
`notes/`) plans as the pr tier with no suite: the plan and the verdict,
about a minute, where its push paid the full run.

The planner over every open and recent PR, whole diff, in its own tree:
px33b (#43), px33 (#38) and px29 (#33) take the music tier (4 to 6
suites); px35 (#41) touches `ci.yml` (every suite, pr leg); px36 (#42,
the wolf pin), px25 (#40, `kernel/sched`, `kernel/paging`) and px34
(#37, `kernel/interrupts`, `kernel/sched`) are full (px36 still is;
since px40 the other two are every suite on the pr leg). A lane that touches
the core pays that on every push after it, because a pull request's
paths are its whole diff against its base, not the last push's (a
superseded run may have been cancelled before it proved anything).

## 5. Evidence

The planted break, seen red before the planner was trusted: branch
`px37-plant` (`53083e5`, never to be merged) drops the one line
`kernel/tcp/* @net` from the map. Locally and in CI (dispatch run
38250338023, `-f suites=census`) `tests/ci-plan` fails three P2 checks:
the network change selects mpx4-net, -udp, -tcp, -ready and -session
(the tests' own text still names `kernel/tcp`) but not mpx4-unix, which
only the rule gave. The plan job failed, every suite job was skipped,
and the verdict job, named `tier unplanned`, failed with "the plan did
not succeed (failure)": a broken plan turns the run red, never into a
quiet run of nothing. Every P1, P3, P4 and P5 check passed in the same
run.

The verdict job seen red on its own fault: the first labelled full run
(38344726280, on `4675690`) had all 29 suites green on its second
attempt (the first lost mpx1 to a 403 from the wolf release download,
before any test ran) and `tier full` red: `KeyError: 'legs'`. GitHub
leaves an output that is empty out of `needs`, and the full tier's legs
are the empty string, so every full run's verdict would have failed;
the pr tier's never did. The check moved into `tools/ci-plan --verdict`
(each output read with a default) and `tests/ci-plan` P6 holds it to
nine cases, that one first.

The pull request's own runs (the pr tier, then the labelled full run)
are named in the PR, since a commit naming them would move the head.

## 6. What lane-audit should read under tiers

Today `lane-audit.sh` takes any `completed success` run at the head. A
`tier pr` run is green with most jobs skipped, so that check would pass
a head that never ran its full suite. Under tiers it should:

- require a run at the head with a job named `tier full` whose
  conclusion is `success` (the `tier` job checks every chosen suite
  succeeded and every other was skipped, so its name and its
  conclusion together say "every suite, every leg, green");
- go on accepting `tier pr` runs as evidence of nothing more than the
  pr tier, and never as the merge gate;
- read a `tier noop` run as no evidence;
- keep its zero-step-cancelled rule (a pr-group run cancelled by the
  next push is the expected shape).
