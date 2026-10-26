# px72 — fsck.ext2 from the rescue initramfs (pax#192, merged at 2f242078)

Materialised on trunk from the PR body by the orchestrator at the merge (a Codex lane writes no note file).

## Forbidden
Clean-room: filesystem specifications, e2fsck documentation and black-box binaries; only PAX's own journal implementation was read. No kernel/libc/e2fsprogs/util-linux/busybox source. No host package install, maintainer disk, merge, label, tag or release. Heavy work: hasu block A, per-suite flock, rootless containers at 12 GiB with internal CPU affinity; QEMU through the repository runner, stopped through its monitor.

## Inputs, verified
- Base `edbd385c`; compiler wolf 0.2.35, `cf0c13d38479f444b69bb8356ad5709d07eff323`, archive `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a` (read twice).
- std `78b9d3cbc41d51db44d18c40b6694403644d1c83`; manifest `06938b3f17fda10cb5b4008a5743e1a04ee5e42797e0cd8c4bc7ae3be60b8fa8` (read twice). Checker `71216ec9d3a1c271cef0e048d0549c034fb6a703d3bc1d6dd189d1561a76bece` (read twice).
- Pinned Ubuntu e2fsprogs 1.47.0; hasu QEMU 11.1.0 TCG and its BIOS/EDK2 firmware. `docs/SOURCES.md` records the format sources.

## Prediction
- `e4c288a9` committed the prediction before implementation.
- Predicted 1,600 Wolf lines; measured 739. External attributes/indexed-directory validation and ambiguous salvage are explicitly refused, not silently counted as support.
- Predicted pass 3 would first disagree. Wrong: pass 5's report-only primary-summary exit status differed first; the checker now matches the observed e2fsck status 0 for that isolated case.
- Predicted a 448 MiB check below 2 s: measured 0.076454 / 0.064379 / 0.065772 s. The installed 128 MiB tree: 0.025586 / 0.025272 / 0.024613 s. Three matched native BIOS boots without a check: 0.920 / 0.818 / 0.921 s; with one: 1.237 / 1.229 / 1.227 s. These include firmware, archive loading and process startup, not just scan time.

## Evidence index
- `10cc0a44`: seeded damage and the existing thirteen-case journal differential.
- `1d10a66b`: five-pass offline checker, exclusive opening and journal replay.
- `29bb7e8c`: byte guards, preen/usage checks and explicit refusals.
- `b28c7527`: Linux/PAX corpus, real-cut rescue boots and CI planning.
- `807fff91`, `bd225c85`: documentation and README inventory refresh.
- `a413fc87`, `2c4c0f77`: NixOS wrapper path and stale boot-log invalidation.
- `66e9ccce`: host-independent fixture ownership and whole-image length checks.
- `529bcd14`: measured costs, syscall census and reduced compiler diagnostic candidate.
- `3abeffc4`: final measured evidence and refusal-status clarification.
- `notes/px72/evidence/`: per-fixture findings and statuses, exact permitted byte differences, PAX results, oracle prompts, both-tier rescue serials, timings and named plant failures.

Tests:
- [x] Static checker build; pinned compiler/std verified.
- [x] 21 ext2 repair-parity cases on Linux and PAX; one malformed-directory case remains unsupported and byte-unchanged.
- [x] 13 journal cases on Linux and PAX: report-only identity, replay byte guards and independent clean rechecks.
- [x] Three malformed-journal cases remain unsupported with no writes on Linux and PAX.
- [x] Preen decisions, argument errors, nonexistent target not created, 1/2/4 KiB geometries.
- [x] Native/release × BIOS/UEFI: real cut, rescue repair, clean flag before mounting, two persistent root boots and mounted-volume refusal.
- [x] CI planner, workflow YAML and diff whitespace checks.
- [ ] Main PR-tier CI at the final head; orchestrator-owned full-matrix label/run.

## Done-when
Local implementation witnesses are complete. Main PR-tier run: **40222959493**, in progress when the required audit read it. No merge or final CI-green claim is made here. The audit ended `AUDIT FAIL (footprint: cross-cutting)` only for pending head CI/no green tier, the intentionally absent orchestrator-owned full-matrix label, and the retained worktree. Branch ancestry, attribution, PR head, five sections and cited shas all passed. The lane does not wait or poll CI.

| Plant draft | Fault | CI dispatch / job | Observed |
|---|---|---|---|
| #189, `155c6e79` | pass 5 omitted | 40220567440 / 121251320405 | red: `group-free-count`, `block-bit-cleared` |
| #190, `a1ac4451` | unrelated byte 17 changed | 40220569670 / 121251313665 | red: `dirty`, `unexpected_offsets: [17]` |
| #191, `48791491` | raw-device clean flag omitted | 40220571974 / 121251294849 | running at the sole status read; local rescue clean-superblock assertion red |

Plants remain open for the orchestrator. Their base is px72, not trunk; each dispatch names only `mpx6-fsck` with `tier=pr`.

## Note
This is the note fallback: the lane wrapper prohibits writing report Markdown files. Please materialize this Note on trunk when closing the lane.

R-px72-1 A is recommended and implemented as clarified: observed e2fsck prompts count as documented decisions, format invariants decide specified bytes, and unsupported damage is refused by name without committing a repair plan. The exact prompts are retained under `notes/px72/evidence/prompts/`, keyed by the fixture that elicited them. They include `Fix? yes`, `Clone multiply-claimed blocks? yes`, `Connect to /lost+found? yes`, and `/lost+found not found. Create? yes`. Ambiguous malformed-record `Salvage? yes` is not imitated.

`-n` never writes or replays. Repair stages metadata, writes dirty first and clean last after flushes; journal home blocks are flushed before emptying the log. Mounted block devices are rejected through `O_EXCL`. The checker does not provide transactional arbitrary-repair crash recovery; the documentation tells users to retain an image copy.

### Corpus
Statuses are report/repair; PAX is repair. Every supported row also passes e2fsck `-fn` afterward, matches the repaired payload tree and its specified bytes. Differences permitted by name are check/write timestamps, orphan deletion time, new lost+found times, and duplicate-block clone placement; no blanket metadata mask is used.

| Fixture | Finding / decision | e2fsck | Wolf/Linux | Wolf/PAX |
|---|---|---|---|---|
| clean | none | 0/0 | 0/0 | 0 |
| lost-writes | none; older committed payload is structurally clean | 0/0 | 0/0 | 0 |
| dirty | filesystem not clean | 0/1 | 0/1 | 1 |
| group-free-count | Free blocks count wrong for group | 4/1 | 4/1 | 1 |
| super-free-count | Free blocks count wrong | 0/1 | 0/1 | 1 |
| group-inode-count | Free inodes count wrong for group | 4/1 | 4/1 | 1 |
| super-inode-count | Free inodes count wrong | 0/1 | 0/1 | 1 |
| directory-count | Directories count wrong for group | 4/1 | 4/1 | 1 |
| block-bit-cleared | Block bitmap differences | 4/1 | 4/1 | 1 |
| block-bit-set | Block bitmap differences | 4/1 | 4/1 | 1 |
| inode-bit-cleared | Inode bitmap differences | 4/1 | 4/1 | 1 |
| inode-bit-set | Inode bitmap differences | 4/1 | 4/1 | 1 |
| link-count | ref count | 4/1 | 4/1 | 1 |
| inode-block-count | i_blocks | 4/1 | 4/1 | 1 |
| directory-size | i_size | 4/1 | 4/1 | 1 |
| bad-directory-inode | deleted/unused inode | 4/1 | 4/1 | 1 |
| bad-directory-type | incorrect filetype | 4/1 | 4/1 | 1 |
| cross-linked-block | multiply-claimed block | 4/1 | 4/1 | 1 |
| disconnected-file | Unattached inode | 4/1 | 4/1 | 1 |
| orphan | Deleted inode has zero dtime | 4/1 | 4/1 | 1 |
| missing-lost-found | lost+found not found | 4/1 | 4/1 | 1 |
| bad-directory-record | directory corrupted | 12/1 | 4/4 | 4 |

`bad-directory-record` is **unsupported**, not a passing parity row. The lost-write fixture models an older committed payload; no checker reconstructs absent writes. The seeded generator reproduces crash classes; the historical 24-cut churn trace itself was not rerun. Four fresh real root cuts are the rescue witnesses below.

| Journal fixture | Case | e2fsck | Wolf/Linux | Wolf/PAX |
|---|---|---|---|---|
| A | two logged blocks | 0/0 | 0/0 | 0 |
| B | later revocation | 0/0 | 0/0 | 0 |
| Bnf | revocation without feature flag | 0/0 | 0/0 | 0 |
| C | same-transaction revocation | 0/0 | 0/0 | 0 |
| C2 | overwrite then revoke | 0/0 | 0/0 | 0 |
| D | revoke then later write | 0/0 | 0/0 | 0 |
| D2 | write/revoke/later write | 0/0 | 0/0 | 0 |
| E | escaped magic | 0/0 | 0/0 | 0 |
| F | torn second commit | 0/0 | 0/0 | 0 |
| G | uncommitted transaction | 0/0 | 0/0 | 0 |
| H | wrapped log | 0/0 | 0/0 | 0 |
| I | committed prefix plus open transaction | 0/0 | 0/0 | 0 |
| Z | recovery with empty start | 0/0 | 0/0 | 0 |

Malformed journal findings (all remain unsupported and unchanged by Wolf):

| Fixture | e2fsck report/repair | Wolf report/repair | PAX repair |
|---|---|---|---|
| tag-past-end | 0/0 | 0/4 | 4 |
| bad-revoke-count | 0/0 | 0/4 | 4 |
| csum3 | 12/1 | 4/4 | 4 |

### Rescue rows
| Kernel | Firmware | Cut → rescue clean | Repaired root → reboot → persistence | Mounted `-y` |
|---|---|---|---|---|
| native | BIOS | PASS | PASS | refused |
| native | UEFI | PASS | PASS | refused |
| release | BIOS | PASS | PASS | refused |
| release | UEFI | PASS | PASS | refused |

Each row preserves `/etc/motd`, the lope store, the home note and `/root/note`, checks mount tables, and ends with an independently clean ext2 partition. Rescue is an explicitly supplied archive/entry, not an existing installed menu. Root/boot defaults and maintainer images are untouched. The checker has a measured 28-call repair census; PAX only reports the established glibc 273/334 fallbacks as ENOSYS.

## Follow-ons
- pax: expose a rescue menu/archive in distributed images; this PR proves/stages the fixture but does not retrofit installed disks.
- pax: external attribute blocks, indexed-directory validation, orphan-chain processing and ambiguous directory salvage remain named limitations. The kernel's existing orphan-list follow-on is not closed here.
- wolf-lang: `notes/px72/region-witness.lu` is accepted by wolf 0.2.35 although a region-local buffer escapes inside a newly constructed aggregate. The reduced candidate was compiled, not executed. The initial checker crashed with that shape; copying the whole aggregate at the outer push fixed it. Please verify and file separately; no compiler change here.
- Reconcile pax#151 and the README inventory item pax#181 at merge; no issue was filed or closed by this lane.
- README read and refreshed in its own commit. Its dated host-history paragraphs were not rewritten.
- Prune after evidence review: hasu `/home/mfwolffe/lanes/px72/`; Mac `/Users/mfwolffe/lanes/px72/` (main and three plant worktrees, bundle, scratch logs); remote `px72-plant-pass`, `px72-plant-bytes`, `px72-plant-clean` after their drafts are closed. No shared images/stores are ours to prune.

Footprint: cross-cutting



### CI rescue-monitor follow-up

The first PR run `40222959493` and full run `40223566059` failed in the
fixture, before the checker ran: the cut serial reached `PX72_CRASH_READY`,
then `boot.py` timed out waiting for the repository runner after sending
HMP `quit` and immediately disconnecting. QEMU booted successfully under
explicit TCG; this was not missing KVM/QEMU, a path failure, or an fsck repair
failure. The delayed-peer regression reproduces premature disconnect as
`FAIL M-close` without a QEMU version or timing dependency.

- `b9cdc3f9`: prediction before changes.
- `e1bfab11`: regression first, original dispatch `40230322026` (queued
  at its sole read). Draft #199 was auto-marked merged into px72 when this
  test-only commit became an ancestor of the fixed branch; no merge command
  or trunk change occurred.
- Replacement draft #200 carries distinct faulty commit `456a54dc` beyond
  fixed head `524514cd`: dispatch `40231926353`, queued at its sole read.
  It restores the old HMP send-and-close and must fail `M-close`.
- `2295ab27`: acknowledged QMP fix; `524514cd`: retained failure and replay
  evidence. The main-head run was not indexed at the immediate query;
  the coordinator confirmed the labeled run is on its watch.
- The fix negotiates QMP capabilities, checks the quit response ID/error,
  waits for acknowledgement and monitor closure, then reaps the runner.
  A reset counts as closure only after acknowledgement. The process wait
  timeout is unchanged. Monitor transcripts are now retained in CI.
- Local delayed-consumption, rejected-command and missing-acknowledgement
  cases pass. The real native/release × BIOS/UEFI rescue rows pass again,
  followed by all 38 PAX corpus rows (34 parity, four explicit unsupported
  immutable refusals). `tests/ci-plan` passes.
- Evidence: `notes/px72/evidence/monitor/`, including the original CI cut
  serial/failure and real QMP acknowledgements through EOF.

The checker, kernel, pelt and chk-soak code are unchanged. The existing
full-matrix label is left in place; the orchestrator watches the new run.
No further pruning was performed. README read: this fixture-only change
moves no public checker interface or build claim.


