# px83 — the nightly's flakes

_Materialised from the body of pax#222 at the merge (`4441676d`)._

Closes #174
Closes #197
Closes #202
Closes #212

Keeps #196 open; upstream symptom: wolffe-lang/pelt#98. References #158; a green final all-tier run is still required before the nightly-red issue can be closed.

## Forbidden

No kernel, libc or shell source read or changed. Changes are to PAX's test probes, comparators, CI and documentation. Pelt is unchanged and its failing eight-background-`true` row is retained. Signal witnesses ran only in dedicated containers or PAX. No labels, workflow dispatches, installs, releases or merges performed by this lane.

## Inputs, verified

Base `187aafdf`; final head `4441676d9135ba5c6697b8ecf9ff5d40ff7860bc`. Builds use the existing pinned wolf 0.2.35 (`cf0c13d`, archive SHA256 `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a`) and baseline Ubuntu container. Pelt stays `0b5eaa5394667c485de3a134f771c87024b68a3c`.

Hasu block B was held under flock; every test container used four CPUs 6–9 and 12 GiB. Startup SigBlk/SigIgn were zero. Static probe and kernel sums were read twice: sigwolf `eb8135d38d1543590c89d9b5b81ca50c0d3f4608a3139284dfa7210cd5ac8b8f`; release console ELF `b6c69ec7004c1c387f3bc1f07a3c40534d4ba48ceafe3191a6f9d98a0e867483`. Pelt binary `25ed3ef933731d44fcbdda4b9b549252e34d18288a2f7795cde177d2b841e127`.

POSIX.1-2024 [exec DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/functions/exec.html) preserves ignored dispositions at exec; [sigaction DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/functions/sigaction.html) permits a subsequent replacement. J4 now explicitly observes the post-runtime state, not exec entry. Sources are recorded in `docs/SOURCES.md`.

## Prediction

Committed before implementation in `6c13e188`, `notes/px83-prediction.txt`:

| row | predicted cause | predicted failures/20 | observation |
|---|---|---:|---|
| F0 | background-builtin wait path, not substitution step 24 | 4 | 9/20 initial; 3/20 separate diagnostic replication |
| J4 | runtime handler installation races the status read | 2 | 0/20 locally; CI reproduced at 40258323326 attempt 1 and 40394044200 |
| heap | release compilation consumes the job envelope | 1 | 20 completed runner timings plus separately censored timeout in #212 |
| rootdisk chk-soak | disk-backed work approaches 900s on runners | 2 |0/20 locally; 11 CI timings up to 860.145s |
| K2 | host capture stretches while guest ticks stay regular | 1 |1/20 locally, 589.2ms capture with correct guest timing |

## Evidence index

### Changes

- `1b3910a6`, `5bffd0c3`: join a runtime task before J4 reads SigIgn; reject reversed/missing/duplicate events. Validate the stack-overflow PC against the current ELF's recursive function instead of an old absolute address.
- `afcea594`: one issue-scoped Linux replay retry, preserving/fingerprinting the first log, status and raw transcripts; warning names pax#196. Unknown errors and build errors are never retried. The build and PAX boots run once.
- `7ec5af29`: K2 pitch from WAV, timing from the guest event ring. Frequency, onset, hold, span and missing-evidence checks remain.
- `98e1f2e4`: only rootdisk chk-soak gets 1200s; every 100000-round command remains.
- `be1f92b0`, `d425e1d1`: measured long-job envelopes and regression checks.
- `9137fd9a`, `976676ca`: retained tables and actual failure/plant witnesses in `notes/px83-evidence/`.
- `3c11fafc`, `4441676d`: README CI paragraphs and correction of the old unconditional SigIgn0400 claim. README read in full; build/install/module interfaces unchanged.

### F0: unresolved shell/runtime stall, bounded bridge

| variant | terminal failures/takes | elapsed |
|---|---:|---:|
| baseline, both identities |9/20|green62–65s; red88–121s|
| timeout-instrumented replication |3/20|green63–65s; red89–121s|
| one-retry bridge |0/20|63–65s first-pass; recoveries154/184s|

Bridge takes 6 and 13 recovered on attempt 2. This is not an upstream fix or a guarantee of recovery. The driver waits before typing step 24; the prior background-`true`/`wait` command produces no completion marker. Snapshots show pelt's remaining task sleeping in a futex with one unreaped zombie child, while the reader is active. No source-level cause or "only under starvation" claim is made. See `notes/px83-evidence/f0-timeout-12.log`, `f0-retry-counts.tsv`, and pelt#98. Only pax#196 remains in the retry list. A second failure stays red; loss of the original evidence is independently red. Prompt/exit bounds remain 30s each; a hung command has no measured completion margin.

### J4: ordered observation

| variant | suite failures/boots | elapsed |
|---|---:|---:|
| original release-BIOS sigs, root+user |0/20|7–8s|
| first ordered probe, stale PC comparison |20/20|7–8s|
| ordered probe + current-ELF PC check |0/20|7–8s|

The middle row's ordering passed; only the absolute diagnostic PC moved. The final check requires exactly one PC inside `_Wdeep$…`, not an arbitrary address. Boot bound 900s, observed margin at least 892s. Files: `j4-counts.tsv`, `j4-after2-counts.tsv` under the evidence directory. No claim that the local baseline reproduced the CI race.

### Heap job

| sample | min / median / max | bound / measured margin |
|---|---|---|
| 20 completed all-tier jobs|1381 /2987 /3336s|old3600 /264s|
|new job envelope|final all-tier validation pending|5400 /2064s above observed max|

The completed sample spans heads; cancelled jobs are censored, not successful 60-minute observations. Data: `tests/mpx2-heap.d/ci-durations.tsv`.

### Rootdisk chk-soak

| sample | failures/runs | min / median / max |
|---|---:|---|
| local before |0/20|456 /460.5 /472s|
| local after |0/20|455 /464 /475s|
| completed CI disk sessions |11 timing observations|423.142 /622.884 /860.145s|

Each local take proves one real disk boot. The new 1200s bound leaves 339.855s above the observed CI maximum and 725s above the after-loop maximum. Memory-root chk-soak and chk-soak-user stay 900s; existing ident soak-user stays 1200s. U3's existing rootdisk memory-census skip is named. Data: `users-before-counts.tsv`, `users-after-counts.tsv`, `tests/mpx5-users.d/ci-durations.tsv`.

### Speaker K2

| sample | failures/boots | capture durations | guest timing |
|---|---:|---|---|
| before |1/20|449.4–589.2ms|onsets50–51; span351; holds48–49 ticks|
| after |0/20|449.4–540.9ms|onsets50–51; span350–351; holds48–49 ticks|

Same image; 12–15s per take. Guest maxima retain 2 ticks of margin to the existing upper bounds. The failed 589.2ms capture had correct guest timing (`speaker-before-1.log`). Local K9 printed a named missing-strace skip in all 40 targeted takes; these are K2 measurements, not a full-speaker-suite claim. CI still requires K9.

### CI plants and final local checks

Both deliberate draft PRs are closed unmerged by the coordinator:

- #220, `3ac56a56`, run[40503159119](https://github.com/wolffe-lang/pax/actions/runs/40503159119): `mpx5-jobs: FAIL J4 Linux SigIgn ordered probe`, also sigs/sigs-user boots. Actual probe read precedes the readiness event; unchanged validator rejects it.
- #221, `c8d58c8c`, run[40503159456](https://github.com/wolffe-lang/pax/actions/runs/40503159456): `ci-retry-first-log-loss: first-attempt evidence was removed or changed` in the plan job. The retry discards its first log; unchanged guard rejects it.

Exact lines: `notes/px83-evidence/ci-plants.log`. At final head 4441676d, `tests/ci-plan`, retry/budget/deadline/J4/K2 selftests, shell syntax and checks against real J4/K2 artifacts all passed on hasu. Full log: `/home/mfwolffe/lanes/px83/final-selftests.log`, completion marker 0. The old deadline and old job budgets were separately observed red before their fixes.

### Rulings and whole-job capacity

- **R-px83-1(A)** accepted by the coordinator: one issue-scoped retry, first evidence retained, warning, entries retired as fixes land. Implemented; only #196 remains.
- **R-px83-2(A)** accepted: the 20 real all-tier heap durations are the before distribution; the 90-minute envelope plus final `tier all` are post-change validation. The contract's 20-run local loops apply to rows measurable in a four-CPU container, not the compilation-dominated CI job. Future runner data accumulates.
- **R-px83-3(A)** accepted: rootdisk chk-soak 1200s from 20 local and 11 runner observations; no count reduction.
- **R-px83-4(A)** recommended and implemented on coordinator direction for the maintainer's ruling: interrupts 75, heap 90, pelt 210, users 210 minutes; no split in this change. [The 21-observation table and derivation](https://github.com/wolffe-lang/pax/blob/4441676d9135ba5c6697b8ecf9ff5d40ff7860bc/tests/ci-budgets.d/README.md) distinguish completed and censored steps.

| job | sizing floor | timeout | margin |
|---|---:|---:|---:|
| interrupts |2885s completed peak|4500s|1615s|
| heap |3336s completed peak|5400s|2064s|
| pelt |6535 main +1543 root floor +600 retry +180 overhead|12600s|3742s|
| users |5018 main +3422 root +300 deadline delta +180 overhead|12600s|3680s|

Pelt's completed root maximum is 1454s; 1543s is a censored lower bound, not a proven upper bound. Forty-percent headroom is rounded upward; final all-tier validation remains required. The next budget lane's first item should split pelt replay/rootdisk jobs with digest-checked fixture transfer; users ISO/rootdisk is next if growth continues.

210 minutes is 3.5h, below the 6h hosted per-job ceiling. There are still 54 suite jobs, no extra matrix expansion, and the org's 20-concurrent-job budget is unchanged. Longer jobs occupy the existing slots longer. Historical total workflow wall times: last green all-tier 40208110580 **2h10m23s**; cancelled all-tier 40505003163 **2h2m3s**. A job timeout is not a workflow wall-time guarantee; the final new all-tier run's wall time is not yet known.

## Done-when

- [x] Prediction committed before implementation; clean-room sources recorded.
- [x] 20-run targeted before/after evidence for J4, K2 and rootdisk chk-soak; 20-run F0 retry bridge with original logs retained.
- [x] Both CI plants red by their intended names; fixes committed before plants.
- [x] Timing READMEs, measured margins, README CI paragraph and durable data.
- [x] Final-head local regression checks pass; no row/leg/count dropped.
- [ ] Main PR-tier green at this head.
- [ ] Coordinator applies full-matrix and dispatches tier all; both required results verified before merge.
- [ ] Final all-tier wall time recorded; #158 closed only after its required green evidence.

No claim that #196/pelt#98 is fixed. The five-section lane record is this PR body; no separate lane-report Markdown file was written.

