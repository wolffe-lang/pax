# px71 — the installer

Materialised from pax#193 (head 1f7cec1e, merged 2026-10-25) at the merge; evidence under `notes/px71/`.

Footprint: cross-cutting

Guided, whole-disk **ext2 developer-preview** installation on a separate QEMU virtio disk. No journalled-root, hardware-install or pack-playability claim.

- `43fdd354` — prediction before implementation
- `ae7ef819` — read-only inventory and bounded planner
- `d6bbb90f` — explicit UI and source snapshot/staging
- `61949606` — argv executor, durable phases and optional games
- `2cffaedc` — log/loader byte isolation and fault rows
- `5fb984b1` — tiered installer gate
- `1f1fe82c` — actual guided firmware sessions and payload guard
- `d46c29bc` — clean-runner cache propagation
- `51813e16`, `b1505929`, `2168c582` — BOOT, CENSUS, SOURCES and README
- `cda85bc0` — final gate evidence and fsck addendum

## Note

Full lane note lives here because the lane's tooling prohibits report `.md` files. Evidence and the initial prediction are tracked under `notes/px71/`.

### Prediction

Committed first in `43fdd354` (`notes/px71/prediction.txt`).

| prediction | measured | score |
|---|---|---|
| first inventory discrepancy: absent sysfs queue/serial fields | PAX reports unavailable model/serial as unknown and queries sector size by ioctl; mounted-device lookup needed mountinfo because `/dev/root` can be synthetic. No new live Linux-device inventory differential was run; px79's measured ABI is the input. | unscored, not claimed a fresh differential |
| first prewrite refusal: running root | first QEMU refusal was the read-only second disk; running-root refusal passes in every target-alone session | wrong order |
| first completed installation would fail a firmware boot | the completed disk booted and persisted under both; early defects were harness cleanup/assertion issues, source atime capture ordering, and a raw-read request exceeding Wolf's 1 MiB clamp | wrong |
| 1600 Wolf lines + 600 test/build lines | 1198 Wolf lines; 1000 lines in installer tests/builders, excluding the assembly membrane, CI and notes | high on implementation, low on tests |
| copy 60 s and guest peak RSS 64 MiB | final full-tree stage/recheck: 17.760 s BIOS, 16.900 s UEFI; whole installs 45.10/44.38 s. PAX getrusage returns ENOSYS, so guest RSS is unavailable. Linux-only reference: 3.389 s and 11884 KiB peak RSS | time overestimated; guest RSS unscored |
| games yes/no land the right bytes/owners without touching source | both answers pass independent readback; yes also includes pinned corresponding source/licences | correct |

### Forbidden

No third-party kernel, libc, shell, formatter, bootloader or installer implementation source read. No host-disk formatting, package installation, Mac build/QEMU, playground writes, signal/trap scripts, merge, label, tag, release or issue action. Existing Ubuntu containers and pinned oracle packages unpacked with `dpkg-deb -x` only; no package scripts ran. All QEMU/build suites used kasumi CPUs 8–11 under the assigned lock, with affinity inside the container. No attribution trailers.

### Inputs verified

- Base pax `edbd385c91f2ff0eadb1ab4e52b276f1a1412b63`. The adopted px69 draft, RULES, px79 and px68 evidence, BOOT/CENSUS and existing disk tools/interfaces guided implementation. The named px69 Markdown report was absent; its actual report is `notes/px69/report.txt`.
- Wolf 0.2.35 `cf0c13d3`, archive SHA256 `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a`, reread twice. Installer uses the archive's bundled std; installed playground std is `78b9d3c`, manifest `06938b3f…`. Limine 12.9.1 remains pinned and unchanged.
- Pack pinned at lane start to `91d93ac38b1e99933ed15818bedc79d37eb98738`, source archive `7cf8a1ed814ba26889840b16d9004951562a2304c416181f98b3e7bce217b73e`. Local staged binary `9aeedb1f71b4cc66e83bbdabfe177ca630a7a2b5ac2e37d249f135e7cbcb6a3f`; checked twice and against installed bytes. Static glibc, Ubuntu 24.04 baseline, not musl. The initial musl contract fact was corrected; the failed GNU-runtime/musl link is not hidden.
- Lope pin `e6f623c778dd486436bcb0a7d481333e0463b906` verified after correcting the initial stale private bundle. Bootstrap-03 completed; payload hashes reread twice after kasumi's 13:32 reboot.
- R-px71-1…6 implemented as recommended: fresh whole disk, explicit ext2 preview, tested layout, exact confirmation/recheck, fresh recorded seed and bounded capacity without hidden truncation. R-px71-7/-8 follow the answered A/A: explicit games answer (`GAMES_REQUIRE_ANSWER`) and named uid/gid-1000 account (`INSTALL_USER_ID`), no password, root shell unchanged.
- R-px71-10 recommendation A implemented, not declared decided: persistent 64 KiB JSONL at byte 65536. Exact `bios-install DEVICE 3` writes stage 2 into the BIOS partition. Both install firmwares show byte-change envelopes `[0,423)` and `[1048576,1071464)`, disjoint from `[65536,131072)`. Exact ranges and before/after/after-log dumps exist; Linux and PAX images match before the log-last witness. Both firmware boots pass with the log written last. A new loader pin must pass this proof again.
- R-px71-11 recommendation implemented: payload contents excluded from installed root, preventing a hidden copy on “no games”. Nonstandard payload locations must be outside the source tree. Reinstallation needs a supplied payload again.

### Evidence

**Evidence index:** `notes/px71/installer-final-01.log`, `final-inputs.sha256`, `final-input-window.log`, `installer-full-01.log`, `guided-{bios,uefi}-01.log`, `limine-{bios,uefi}-ranges.json`, `linux-rss-01.log`, and `ci-plan-final.log`.

Final implementation gate on kasumi: `/home/mfwolffe/lanes/px71/runs/installer-final-01.log`, exit marker `installer-final-01.exit` = 0; 14:37:54–14:43:44 EDT, **61 PASS, 0 FAIL, 0 SKIP**, 5m50s using staged inputs. Input digests match the final implementation and all input mtimes precede the start marker at nanosecond precision. Earlier complete gate `/home/mfwolffe/lanes/px71/runs/installer-full-01.log` was 5m52s. Full-tree/both-firmware rows therefore live in `tier full`; PR tier keeps compact installs and fault rows. Payload construction was separately completed by bootstrap-03, not counted in these staged-input timings.

- [x] Planner: alignment, exact min/max, overflow, sector sizes, similar names, changed identity/capacity/mounts, explicit decisions and exact tokens.
- [x] Real QEMU read-only inventory, unavailable target, byte-identical dry-run/cancel/refusal disks; target-alone running-root refusal.
- [x] UI EOF at each prompt, no blank games default, n/p navigation, terminal resize and exact confirmation. Actual guided confirmation flow under BIOS and UEFI, not only scripted flags.
- [x] Sorted lstat metadata, numeric owners/modes, hard-link equivalence, symlink targets, whole-second times, quoted names, exclusions, non-empty lost+found refusal, source changes and interrupted scratch copy.
- [x] Every external status including 2, literal argv, zero-exit error diagnostics, fsync before durable; guest faults at GPT/FAT/root/Limine, missing executable, invalid manifest, ENOSPC and missing/corrupt boot assets.
- [x] Independent sgdisk/sfdisk, strict fsck.fat output, e2fsck, complete tree bytes/metadata, new PARTUUID/configuration, and Linux/PAX Limine equality.
- [x] Games **no** on vdb: no game or hidden payload. Games **yes** on vdc: exact staged pack plus corresponding source/licences, modes 0755/0644 and owners 1000:1000; source guards unchanged in both cases. The maintainer's playground was never touched.
- [x] Complete installed tree from both firmware environments; target alone persists motd, home/root notes and lope entries across reboot; clean ext2 and mount count 2 afterward.
- [x] `tests/ci-plan`, `tests/census`, syntax checks and warning-denied Wolf builds.
- [ ] Final-head `tier pr`; read once after opening, no polling/waiting.
- [ ] Orchestrator applies the full-matrix label and watches `tier full`; no label added here.

Plants are draft PRs against px71, left open for orchestrator closeout:

| plant | PR | head | run | expected named row |
|---|---|---|---|---|
| wrong target identity accepted | #186 | `21ef4d70` | 40220472582 | I-identity |
| copied ESP configuration omitted | #187 | `5fc77f2c` | 40221717604 | I-boot-files / verify-boot-2 |
| formatter exit 2 ignored | #188 | `e0ebe504` | 40220482658 | I-external-2 |

The orchestrator confirmed #186/#188 completed failure and is recording the exact rows. #187 was rerun after the clean-runner cache propagation fix; **old run 40220478629 at 9e792f51 is not used as boot-file evidence**. The replacement run was still in progress at the last supplied status; its red row is not assumed.

### Follow-ons

**Done-when:** local implementation and oracle rows above pass; merge readiness still requires final-head CI and the replacement plant's named red. No merge or final CI green is claimed.

1. `paxext2 --journal` and its Linux/PAX/e2fsck rows before a journalled installer default. Setting has_journal alone is not enough; existing host ext3 defaults/gates are unchanged.
2. PAX getrusage/RSS support: ENOSYS measured, already handed to the orchestrator to file. Linux RSS is labelled only as a reference.
3. Timer-driven blink #118, hardware drivers/USB transport, and pack playability remain their own lanes. True musl payload waits for wolf 0.2.36 plus the republished link bundle (wolf-lang#962/#963).
4. No resize/dual boot/repair/resume, rescue initramfs, non-UTF-8 input tree, nonempty lost+found migration or existing Games merge. Staging needs enough temporary storage/RAM. Source-change detection is not an adversarial/live snapshot guarantee; writable-source reads may update atime. Generated metadata epoch is documented.
5. `notes/px71/px72-next.txt` adds installer-facing acceptance rows to px68's existing fsck draft without deciding that lane.
6. README read and refreshed for this change. Its older historical sections still contain stale host/version wording and a partial test list; those pre-existing cleanup items are not an installer deployment claim.

Prune only after retaining evidence: `/Users/mfwolffe/lanes/px71/pax`, the three `/Users/mfwolffe/lanes/px71/plant-{identity,boot,exit}` worktrees, lane bundles/downloads/tmp, and `/home/mfwolffe/lanes/px71/` (clone, lope bundle/clone, caches, builds, logs, oracle unpacking and scripts). Exact image-only reclamations are logged under `runs/pruned-*.txt`; source fixtures, logs and range dumps were retained. Shared container images and other lanes' directories are not ours to prune. No issue was filed or closed by this lane.



#### Snapshot fixture correction after hand-back

Run 40221717604 at boot-plant head 5fc77f2c failed before reaching the plant:
`tests/mpx6-install.d/snapshot.py` differed ONLY at `/bin/tool` atime,
actual `1792953470` versus expected `1700000000`. Its earlier-sorted hard-link
alias retained the expected old atime. Hashing that alias advanced the
shared inode's atime on relatime; the fixture incorrectly assumed its
pre-walk metadata would remain unchanged for the later alias. No installer
or formatter behavior was changed. The formatter still uses the first
explicit hard-link metadata.

`dc7e0292` stabilizes the fixture by placing atime one day ahead of mtime and
ctime, checks that reads leave it unchanged, and retains the exact full
metadata comparison. Expected whole seconds now come from integer ns
fields rather than floating-point timestamps. The unchanged installer
reproduced the old failure on isolated relatime tmpfs, then passed the
fixed fixture as both root and uid/gid 1001; the ordinary snapshot gate also
passed. Evidence: `notes/px71/snapshot-relatime-before-02.log`,
`snapshot-relatime-after-0-0.log`, `snapshot-relatime-after-1001-1001.log`,
and `snapshot-atime-final.log`.

Main head is now `1f7cec1e` (evidence follows the fixture-only fix); boot plant
#187 is now `216f738e` after cherry-picking only that fix. Immediate run
listings for both new heads returned no rows yet; no subsequent polling.
Neither old boot-plant failure is accepted as I-boot-files evidence. #186
and #188 were not touched. The earlier full gate remains evidence for the
unchanged installer; these targeted red/green rows cover this harness edit.

