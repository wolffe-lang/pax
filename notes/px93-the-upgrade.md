# px93 — `pax-install --upgrade`: a new image over the 860's install, your files kept

Contract: px93's (crawl 54, 2026-11-04), under the lane rules of 2026-10-31 and their additions, launched on the
maintainer's word: they will test many images on kasumi's 860 and want each installed over the last without losing
their files. Their rulings bind: R-px93-A, in place now, slots later; R-px93-B, keep yours and save the new beside it
as `FILE.pax-new`, the accounts always kept; R-px93-C, the image on a flashed stick, the network later.

The coordinator added, during the lane:
- R-px93-D: the upgrade installs the dev variant, with the compiler (wolf, its musl sysroot and compiler-std), and a
  row builds a program printing `env_args()` on the upgraded system and holds its output to the Linux build's;
- R-px93-E: speed. The upgrade, the KVM rows, the staged stick and a hand-back first; what is not load-bearing cut
  and named;
- px92 found that wolf 0.2.35's static musl programs see an empty `env_args()` (wolf-lang#962, fixed in v0.2.36):
  this branch was rebased onto px92's re-pin of `user/wolf.pin`;
- after the first hand-back (stick `769bac07`), the 860 was installed fresh from px92's dev stick
  (`pax-install-kasumi-dev-8b4e98ae.img`). R-px93-6 brought back what R-px93-E had cut, in its order (5.1), and
  R-px93-7 put px92 first: this branch was rebased onto px92's head `44b44435`, then onto trunk `b8e77f7a` after
  px92's and px96's merges, onto px98's head `946245e6` (den as a user, which merged first), and last onto trunk
  `37217ba0` (px98's merge and px89's mpx4-ready pipe guard), so this branch's commits are px93's alone.

Footprint: cross-cutting (`boot/limine-usb.conf`, the loader and the boot path; `kernel/fstab` and
`kernel/kmain_console.lu`; `tools/install-manifest`, which the CI plan maps to the full set).

The maintainer's disk serial is written `<kasumi-serial>` in every file under `notes/px93/`, because this
repository is public. The staged sticks carry it, and their sha256s cover it.

## 1. Forbidden, and what was read

No kernel's, firmware's, bootloader's, emulator's, driver's or file-system tool's source was read. Limine ran as a
binary (its menu driven by keys, its two `module_path` lines in the stick's configuration). e2fsprogs (`debugfs
rdump`, `debugfs cat`, `e2fsck -fn`, `mke2fs -d`), mtools (`mcopy`, `mtype`) and dosfstools (`fsck.fat`) ran as black
boxes.

Read:
- the contract, the coordinator's additions and continuation, the lane rules of 2026-10-31 (every Added item), RULES
  §1–§10;
- px92's contract and branch (by copy), its two stick READMEs, and the px86, px78b and px77c notes;
  `docs/INSTALL-METAL.md`;
- PAX's `user/install/*.lu`, `kernel/fstab/fstab.lu`, `kernel/ext2/ext2.lu`'s header (its write path and journal),
  `kernel/boot_info`, `kernel/block`'s identity and partition accessors, `kernel/tree`'s mount and mkdir,
  `user/disktools/{paxfat,paxgpt}`;
- `tools/{distribution-root,mkdistribution,mkinstall,mkinstall-payload,mkdisk,build-kernel}`,
  `tests/mpx6-install` and `tests/mpx6-install.d/{metal,verify}.py`, `tests/mpx6-disktools.d/fat.py`,
  `tests/mpx5-wolf` and `tests/mpx5-den.d/rows.py`, px60's native-link note;
- the wolf checker's builtin signatures (wolf-lang's own source, the maintainer's).

kasumi was not touched, booted or written. Only QEMU images this lane made were written.
- satoyama: both locks, A outside then B, and slot A's CPUs `0-3,8-11` inside every container;
- hasu: block B's two lock names and CPUs `6-11`, for two unit takes (the second stood down: satoyama had run it);
  never a commit on hasu;
- nothing in `/tmp` or `/var/folders` (TMPDIR under `~/lanes/px93/` on every host); nothing installed;
- no label, merge, tag, issue or release; no attribution trailers.

## 2. Inputs, verified

- **Base**: trunk `37217ba0`: px89's mpx4-ready pipe guard (`tests/mpx4-ready` and its fixture) over px98's merge
  (`946245e6`, den as a user: the console terminals' owners and modes in `kernel/files`, the installed login's
  terminal handover in `installed_login()`, `tests/mpx5-den`), over `b8e77f7a`: px92's merge
  (`44b44435`, fast-forward) and then px96's (the quiet console's write-error lines: `kernel/user`,
  `kernel/kmain_user.lu`, `tests/mpx3-user`, `user/programs.S`, docs). px92's head brought its wolf v0.2.36 re-pin
  (`user/wolf.{pin,sums}`, `tools/distribution-root`, `user/console/distribution.keys`), `tests/mpx5-wolf.d/test_rows.py`,
  `tools/ci-tiers.map` and its notes. Until then this branch sat on px92's branch at `5d33b425`; `git rebase --onto
  44b44435 5d33b425` replayed this lane's commits alone, with no conflict (px92 touched none of this lane's files),
  and so did the rebases onto `b8e77f7a`, onto `946245e6` and onto `37217ba0` (px96 and px89 touched none of
  them; px98 touched `user/install/prepare.lu` in `installed_login()` alone, apart from this lane's hunks there).
  Records run before that rebase name the commit they ran at; the same subject's commit is in the list below
  (4.3 maps each).
- **The old sticks**, each copied from px92's satoyama directory and read twice there, equal to px92's figures:
  - `pax-install-kasumi-9c88ec8a.img` (px92's release stick), 829,423,616 bytes, sha256
    `850ff60b8e5e614233deb82fa040a8d99ece802569123b9cc93d91aef7179f7e`;
  - `pax-install-kasumi-dev-8b4e98ae.img` (px92's dev stick, wolf 0.2.36, the 860's install since 2026-11-04
    03:30), 1,119,879,168 bytes, sha256 `665f815ab193907c007d7b431b6f833730bf1b51adbddf5ad92fb13d4d67501b`.
- **The baselines**, `tools/install-manifest` over each stick's ESP (`/boot/pax`, `/boot/initramfs.cpio`), two runs
  byte-identical:
  - `user/install/baselines/9c88ec8a.manifest`, 308 rows, sha256 `a1d775f7…`;
  - `user/install/baselines/8b4e98ae.manifest`, 436 rows, sha256 `2cdeb661…`.
- **Build inputs**: px92's (px86's by px78b's provenance, plus px90's den), by copy, `build/inputs` equal file by
  file on satoyama and hasu; `base-dev.cpio` `098b918e…`; Limine 12.9.1 `5cdebc51…`, read twice; wolf at the pin,
  v0.2.36, by `tools/fetch-wolf` and `tools/mkwolf`.
- **Containers**: `localhost/px75-ubuntu:2` for the builds, `localhost/px78-ubuntu:1` for the oracles and the legs
  (QEMU 8.2.2, OVMF, e2fsprogs 1.47.0, mtools 4.0.43, dosfstools 4.2), `--memory 12g`, `--device /dev/kvm` for the
  legs.

**Commits** (`44b44435..` this branch's head), the failing rows before the code they hold:

- `601b7a6f` notes/px93/prediction.txt, first.
- The rows first (red first where they can be): `bb3bbcb8` tools/install-manifest; `bb410e33` the 9c88ec8a baseline;
  `1e31839b` the upgrade leg (`tests/mpx6-install.d/upgrade.py`); `a5f70c84` fat.py's replace row.
- The change:
  - `cf345515` kernel/fstab, the upgrade entry's mount;
  - `57f744f2` boot/limine-usb.conf, the upgrade entry;
  - `71fc1acb` paxfat replace;
  - `b46b4816` prepare.lu, `70464244` snapshot.lu, `3c6a6874` tools/mkinstall-payload;
  - `d9fc44e4` manifest.lu;
  - `ab2392fb` `pax-install --upgrade`.
- Fixes the units and the legs found: `f8e10009` (a kept link's `.pax-new` is a link), `1d0c186a` and `76206a01`
  (the uses after a move), `29c343f7` (the upgrade's disk page); in the leg script `93fca3db`, `be1fd925`,
  `a3c2e95c`.
- R-px93-6: `5dc9d125` the 8b4e98ae baseline; `0a300a09` verify.py's I-manifest; `96d60ef6` flow.lu (the unit
  builds); `43e53a83` every fresh install writes its manifest; `e666d38b` the leg's three sections.
- R-px93-9, red first: `c87a5017` U12; `91426820` the earlier installers' texts; `6c876db1` the regeneration and
  the manifest's record; `ae35e31a` U12 answering pax-install's question and logging in at the regenerated login.
- The lane's job script (`notes/px93/satoyama/`): `9ade9041`, `0eb5d981`, `377e46bb`, `85e61b7f`, `8360473c`,
  `8762c632`, `f9fc6637`, `d286ddaf`, `c2f97484`, `6c5ccbe2`, `7c451942`, `3d82a205`, `2ed8e583`, `eef06dc2`,
  `8e330570`, `fb0327f6`, `63dc473c`, `2010c379`, `d66df783`; `5f8ee912` rec-gauntlet.sh, the recorded take.
- Then this note and its logs.

## 3. Prediction, scored

`notes/px93/prediction.txt`, written before the first change and before any guest ran:

| predicted | found |
|---|---|
| R-px93-1 by a second Limine module, the stick's own `/pax/install-targets`; the ESP unmounted | **right**: U8-wrong-serial, and U3's mount (`/dev/sdc2 /mnt/target ext2 rw,relatime` in `/proc/self/mounts`) |
| the identity: commit, kernel, release, files; the stick's sha256 outside it | **right** (R-px93-2) |
| the baseline from the staged stick's ESP, matched by kernel and release together | **right**: both baselines, two runs byte-identical each |
| paxfat replace red first (an unknown command), then green | **right**: `fat.py:108`, `paxfat: invalid`, at the tests-only head; F5 green |
| U0, the default entry mounts nothing | **right** |
| U1 and U2, the old install and the typed user state | **right**: 52–54 s installs; 50 user paths, den with three commits |
| U3: a few hundred new paths, most of `/bin` equal, `/etc/shrc` kept with `.pax-new`, `/etc/motd` written again, `fstab` and `limine.conf` unchanged, nothing appended to the accounts, `/boot/pax` replaced | **right but the count**: from 9c88ec8a, 129 written and 11 replaced (140 steps and one `.pax-new`), not a few hundred |
| U4, U6 | **right** |
| U5, the compiler's `env_args()` | **wrong at the 0.2.35 pin** (px92's finding, wolf-lang#962: a static musl link saw `argc` 0); **right** at v0.2.36, the same bytes as Linux |
| U7: e2fsck may report what a cut leaves | **better than predicted**: clean, the cut at step 100 of 141 |
| U8: wrong serial and mistyped in the leg; the other three at the unit level only | **superseded**: R-px93-6 put no-baseline, not-PAX and no-space in the leg, each by name |
| the upgrade 60–240 s from the line; the leg 20–40 min | **wrong, both far under**: 10.71 s from 9c88ec8a and 3.7 s from 8b4e98ae; the three sections 484.83 s, 319.29 s and 541.01 s |
| the dev stick near 1.1 GB | **right**: 1,119,879,168 bytes |

Not predicted:
- four uses after a move in the first compile (each refusal's text made from a value already moved into its tuple);
- the upgrade's disk page called its own target `refused: mounted` and printed "No disk may be a target", a fresh
  install's words (fixed: the page shows the upgrade's target as listed);
- the leg's stop pattern matched the previous command's line still on the screen (fixed: each command's waits read
  what follows its own echo);
- the installer's unit builds replace `main.lu`, so the helpers both flows use moved to `flow.lu` before the unit
  rows could build;
- two faults of the lane's own job script: the kernel unit without `PAX_WOLF`, and satoyama's lane directory being
  `/mnt/space/lanes`, so a worktree's git pointer needs that path mounted in the container;
- the 860's install changed under the lane (8b4e98ae's dev stick), which R-px93-6 answered with a second baseline and
  a section of its own.

## 4. Evidence index

### 4.1 The change

**The mount (R-px93-1, `kernel/fstab`, `boot/limine-usb.conf`).** The stick's Limine menu has a second entry, "PAX:
upgrade the installed system": `cmdline: quiet pax.upgrade` and two modules, the archive and the stick's own
`/pax/install-targets`.
- Under that word alone, after the table, `mount_upgrade` reads the second module as `allow.lu` reads the file: any
  line that is not `model=… serial=…` refuses the whole list.
- It takes the one disk whose model and serial (kernel/block's identity, trimmed as sysfs gives it) a line names.
- Only when that disk's GPT partition 2 begins at sector 135168 and holds an ext2 volume labelled `pax-root` does it
  mount it read-write, write-back, at `/mnt/target`, made in the memory tree.
- Each refusal is one line, `upgrade: nothing mounted at /mnt/target: <why>`. The default entry has neither the word
  nor the module and mounts nothing (U0).

PAX has no FAT driver, so the ESP is not mounted: the installer writes it through the disk's node at byte 2097152
with `paxfat`, as a fresh install does. The PARTUUID is matched in userland: the target's own `/etc/fstab` must name
the mounted partition's GUID (read by `paxgpt --dump`), or the upgrade is refused.

**The manifest (`user/install/manifest.lu`, `tools/install-manifest`).** `/etc/pax-install/manifest` holds:
- the image's identity (R-px93-2): the commit in `/etc/pax-release`'s kernel row, the kernel's sha256, and the
  sha256s of `/etc/pax-release` and `/etc/pax-files.sha256`;
- one line a shipped path, `kind mode uid gid size sha256 path`, with `g` for the installer-written paths.

Never listed: `/home`, `/root`, `/dev`, `/proc`, `/sys`, `/tmp`, `/mnt`, `/lost+found`, `/usr/share/pax-install`,
`/etc/pax-install`.

Every fresh install writes its own manifest (`user/install/execute.lu`, after `configure_tree`; R-px93-6's item 2):
the same identity and rows, its `g` rows' digests the installed text's. An upgrade writes the new image's manifest
last. So an install made by this stick or a later one needs no baseline (U9).

`verify.py`'s I-manifest row holds a fresh install's manifest to the installed root:
- the directory 0755 and the file 0644, both root's;
- its header;
- each row's kind, mode, owner and bytes against the root's tree;
- every listed path of the root in it;
- `/etc/pax-install` and the manifest as the only paths beyond the source's in the exact-tree check.

It was red first: at 4f2f6f10 (`96d60ef6` now), before the installer wrote the manifest, `mpx6-install`'s smoke rows failed by name
(4.3).

For installs made before manifests, the two baselines (section 2) are carried at `/usr/share/pax-install/baselines/`
by `tools/mkinstall-payload`. An install is matched by its ESP kernel's and its `/etc/pax-release`'s sha256 together.

**The upgrade (`user/install/upgrade.lu`, `flow.lu`, `main.lu`, `prepare.lu`, `snapshot.lu`).** `pax-install
--upgrade`:
- The target is the one allow-listed disk in PAX's layout whose partition 2 alone is mounted, at `/mnt/target`.
- The old manifest is, in order, a cut run's record, the root's manifest or a baseline. Anything else is refused by
  name.
- The new image is the running stick's tree, walked as a fresh install walks it (`/mnt/target` excluded).
- The plan, in the module header's order:
  - each path written, left, replaced, or kept with `FILE.pax-new`;
  - each dropped path deleted, or kept;
  - accounts appended;
  - `fstab` and `limine.conf` regenerated for the target's PARTUUID (a root copy the user changed is kept, the
    regenerated text beside it, R-px93-5);
  - the ESP's kernel, Limine and `limine.conf` by `paxfat replace` where their bytes differ;
  - space and inodes checked against the root's superblock first.
- The confirmation is the line the contract names, `UPGRADE /dev/sdX <model> <serial> <seed>`, its seed eight hex
  digits fresh each run (R-px93-3), or `--seed S --confirm LINE` scripted.
- Every file goes to `PATH.pax-tmp`, is fsynced, held to its sha256 and renamed over.
- The order of the writes:
  1. the record (`/etc/pax-install/upgrading`, `previous`);
  2. the root;
  3. the ESP;
  4. the manifest;
  5. the record removed.
- Both logs are appended at every step: the stick's `/pax/logs/install-<n>.txt` and the target's
  `/etc/pax-install/upgrade-<n>.txt`.

**`paxfat replace` (`user/disktools/paxfat`).**
1. A new chain is written and its FAT sectors saved, then fsynced.
2. The entry's one sector is rewritten, then fsynced.
3. The old chain is freed, then fsynced.

A cut leaves the old file or the new one, never a mix, and at worst a lost chain for `fsck.fat`.

### 4.2 The rows

Each leg row boots a copy of a stick under KVM on metal.py's kasumi-shaped machine: an NVMe with two partitions, a 4 TB
870, a SanDisk with four, the 860-shaped 1 TB target (`model=Samsung SSD 860`, the 860's serial) and the stick. Every other
disk's witness is held unchanged over every boot. The screens are read from PAX's own memory (`pax_screen_cells`), and
Limine's menu is found by its green bottom line.

| row | holds |
|---|---|
| F5 (`fat.py`) | `paxfat replace` with larger, smaller, empty and grown bytes, `fsck.fat` clean, the other files kept; an absent file, a directory and a copy onto itself refused, the image unchanged |
| I-manifest (`verify.py`) | a fresh install's own manifest, as above; in every smoke install of `mpx6-install` |
| **section a**: the 9c88ec8a install | |
| U1-install | the old stick installs the target |
| U2-state | 50 user paths typed at the installed console: files under `/home/wolf`, a den repository there with three commits (its log saved in `/root`), `/etc/shrc` edited, `/etc/mine.conf`, `/usr/local/bin/hello`, `/etc/motd` deleted; e2fsck clean |
| U0-default | the new stick's live entry: no `/mnt`, the target byte-identical over the boot |
| U8-wrong-serial | a list naming another serial: nothing mounted, pax-install refused by name, the target byte-identical |
| U8-no-baseline | an install matching no baseline refused by name, before any write |
| U8-mistyped | the line mistyped by one character: cancelled by name, `/etc/pax-install` not made |
| U3-upgrade | the upgrade entry from Limine's menu, the plan naming 9c88ec8a's baseline and `beside /etc/shrc.pax-new`, the line typed, complete |
| U4-after | every user path byte-identical, den's log the same, `/etc/shrc` yours and its `.pax-new` the new image's, every shipped path the new image's, every dropped path gone, the manifest equal to the host tool's; the upgraded disk boots alone with `kernel: <head>` |
| U5-compiler | `/usr/bin/wolf` builds the `env_args()` program on the upgraded system; it prints `arg: one`, `arg: two words`, the Linux build's bytes |
| U6-again | the second upgrade: "Nothing to change", every path as it was |
| U7-cut | QEMU killed after 100 steps, the upgrade re-run from the record: complete, U4's checks, e2fsck clean |
| **section d**: the 8b4e98ae dev install, the 860's | |
| U1d-install | px92's dev stick installs the target |
| U2d-state | U2's state, and a program built on the target by its own `/usr/bin/wolf` (its source, binary and output under `/home`); e2fsck clean |
| U3d-upgrade | the plan from the 8b4e98ae baseline, `beside /etc/shrc.pax-new`, the line typed, complete |
| U4d-after | U4's checks over 54 user paths (the program's among them); the program still prints its arguments; boots with `kernel: <head>` |
| U6d-again | the second upgrade: "Nothing to change" |
| **section x**: disks of their own | |
| U9-fresh | the new stick installs the target fresh, with its own `/etc/pax-install/manifest`; the upgrade with the same stick reads it, no baseline: "Installed: <head>, from its manifest", "Nothing to change", every path as it was |
| U10-not-pax | a listed disk holding an older system (`tools/used-disk fat32`): nothing mounted, refused by name (not a PAX install), the disk byte-identical |
| U11-no-space | a 1 GiB 860 installed by the old stick, its root filled by a user file: refused by name (too little space), `/etc/pax-install` not made |
| U12-installer-text | R-px93-9: a fresh install from the new stick; in the upgrade entry `/etc/pax-login` given an earlier installer's text and the install's manifest row naming it; the upgrade regenerates it (`text /etc/pax-login (the installed login: an earlier installer's text, regenerated)`), nothing beside it; the upgraded disk boots alone and root logs in at that login; then a line of the user's added: kept, the new text beside it as `.pax-new`; a third run "Nothing to change" (the manifest records the installer's text, not the user's); e2fsck clean |

### 4.3 The records

Every step's END line, in the order run (satoyama unless named; the logs under `notes/px93/logs/`, the serial masked):

Before the rebase onto `44b44435` (run at; the same subject's commit now):

| run at | now | END lines | what |
|---|---|---|---|
| 6a965973 | `a5f70c84` | `08:04:09Z END red-fat exit=1`; `08:07:30Z END red-leg exit=1` | **red first, by name**: `fat.py:108`, `paxfat: invalid` (no replace yet); `FAIL U8-wrong-serial: /^usage: pax-install/` (no `--upgrade` yet) |
| 77eca689 | `0eb5d981` | `08:17:37Z END units-install exit=2` | the first compile: four uses after a move (E1001) |
| 2ae903d7 | `76206a01` | `08:28:52Z END units-install exit=0`; `08:28:52Z END units-kernel exit=2`; then `08:29:59Z END units-install exit=0`, `08:38:09Z END units-kernel exit=0`, `08:38:23Z END units-fat exit=0`, `08:38:23Z END units-args exit=0` | the kernel unit without `PAX_WOLF` (the job script's), then every unit green; the Linux `env_args()` program printed `arg: one`, `arg: two words` |
| hasu, 2ae903d7 | `76206a01` | `08:52:23Z END units-install exit=0`; `08:52:24Z END units-kernel exit=2` | the same job-script fault, before its fix reached hasu |
| 2ae903d7 | | `09:03:35Z END sbuild exit=2` | stood down on purpose (its output directory made first): 0.2.35's build, superseded by the re-pin |
| 58da8e55 | `6c5ccbe2` | `09:03:35Z END sbuild exit=1` | `fatal: not a git repository: /mnt/space/lanes/…` (the worktree's real path not mounted) |
| 60303fa8 | `7c451942` | `09:14:00Z END sbuild exit=0`; `09:14:34Z END sstick exit=0`; `09:18:45Z END legs exit=1` | `FAIL U8-mistyped`: the stop pattern matched the previous command's line still on the screen |
| 769bac07 | `a3c2e95c` | `09:29:05Z END sbuild exit=0`; `09:29:38Z END sstick exit=0`; `09:38:38Z END legs exit=0` | every row of the first leg; the upgrade 10.77 s; the leg 488.93 s; the first hand-back's stick |
| ce1a8862 | `3d82a205` | `10:46:44Z END sbuild exit=0`; `10:47:17Z END sstick exit=0`; `10:52:57Z END legs-d exit=0`; `10:57:30Z END legs-x exit=0`; `11:10:00Z END legs-a exit=0` | R-px93-6's rows, all three sections green: d 323.45 s (U3d 4.01 s), x 272.65 s, a 492.72 s (U3 11.06 s) |
| 4f2f6f10 | `96d60ef6` | `11:30:09Z END red-verify exit=1` | **red first, by name**: `mpx6-install --rows smoke`'s first install, `AssertionError: no /etc/pax-install/manifest on the installed root` (verify.py's I-manifest in, the installer not yet writing it) |

After the rebase onto `44b44435` (run at, before the rebase onto trunk's px96 merge; now):

| run at | now | END lines | what |
|---|---|---|---|
| 7a65f930 (job.sh only) | `fb0327f6` | `15:16:39Z END ci-plan exit=0`, `15:16:39Z END ci-budgets exit=0`, `15:16:47Z END mpx6-disktools-fat exit=1` | the fat rows' oracles could not open the work directory: fat.py resolves `/mnt/space/lanes/…`, tools/disktools mounted the `/home/…` path (fixed in `2010c379`) |
| 9dd66333 | `63dc473c` | `15:24:55Z END sbuild exit=0`, `15:25:28Z END sstick exit=0`, `15:28:19Z END red-text exit=1` | **red first, by name**: `FAIL U12-old-text: missing 'text /etc/pax-login (the installed login: an earlier installer'` |
| 00c902f4 | `6c876db1` | `16:16:01Z END sbuild exit=0`, `16:16:33Z END sstick exit=0`, `16:21:53Z END legs-d exit=0`, `16:30:02Z END legs-a exit=0`, `16:38:16Z END legs-x exit=1` | U12's row fault (4.1, R-px93-9): the regeneration right, the question after it unanswered |
| 9dd66333's stick, e64d1751's leg | `63dc473c`, `2010c379` | `17:21:21Z END legs-x exit=1` | **red again, by name**, with the corrected row: `FAIL U12-old-text` |
| e64d1751 | `2010c379` | `18:30:22Z END sbuild exit=0`, `18:30:55Z END sstick exit=0`, `18:36:15Z END legs-d exit=0`, `18:44:20Z END legs-a exit=0`, `18:53:21Z END legs-x exit=0` | every row of the three sections, U12 among them; the staged stick |
| e64d1751 | `2010c379` | `19:01:57Z END ci-plan exit=0`, `19:01:57Z END ci-budgets exit=0`, `19:02:30Z END mpx6-disktools-fat exit=0` | gauntlet-1 |
| e64d1751 | `2010c379` | `20:11:49Z END mpx6-install exit=0` | gauntlet-2, the smoke rows, verify.py's I-manifest |
| e64d1751 | `2010c379` | `22:25:02Z END kasumi-build exit=0`, `22:26:19Z END kasumi-870 exit=0`, `22:28:12Z END kasumi-860 exit=0`, `22:30:34Z END mpx6-ahci exit=0` | gauntlet-3 |

Every chunk above is the lane's job script's own log (`notes/px93/logs/`): its START and END lines carry a time, and
its lock lines sit outside any step, so `tools/gauntlet-record.sh --verify` cannot read them (`malformed record
header/footer`). The recorded take is therefore run once more at this branch's head, both locks held for the whole
take, each chunk one step (`notes/px93/satoyama/rec-gauntlet.sh`): the green record and the plant's, verified by the
recorder, are the PR's evidence, their END lines in its body.

The first recorded take, at the head on px98's (b57be3ca, its plant 0915a5da), verified, before px89's guard merged
and moved trunk under it (both on satoyama, both locks for the whole take; the inner END lines are the chunks'):

| record | steps (END, secs) | the chunks' END lines inside |
|---|---|---|
| green, worst 0, 4 steps, 01:36:26Z–02:29:03Z | stick 1837, gauntlet-1 107, gauntlet-2 878, gauntlet-3 334 | `01:44:13Z sbuild 0`, `01:44:45Z sstick 0`, `01:50:04Z legs-d 0`, `01:58:11Z legs-a 0`, `02:07:03Z legs-x 0`, `02:08:11Z ci-plan 0`, `02:08:11Z ci-budgets 0`, `02:08:50Z mpx6-disktools-fat 0`, `02:23:28Z mpx6-install 0`, `02:23:42Z kasumi-build 0`, `02:25:00Z kasumi-870 0`, `02:26:51Z kasumi-860 0`, `02:29:02Z mpx6-ahci 0` |
| plant, worst 1, 02:29:03Z–02:41:11Z | plant 727 (exit 1) | `02:36:44Z sbuild 0`, `02:37:16Z sstick 0`, `02:41:10Z legs-d 1`; `FAIL U3d-upgrade: missing 'beside /etc/shrc.pax-new' on the screen:` at column 0 |

On px98's login U3 and U3d's plans read `text /etc/pax-login (the installed login: an earlier installer's text,
regenerated)` (U3 10.46 s, U3d 3.67 s), and U4, U4d and U12 logged in through px98's login.

### 4.4 The plant

`px93-plant-overwrite`: one commit on the head, one file, one hunk, pushed with no PR. In `plan_paths`, a shipped
file the user changed is replaced as if the user had left it (`same_as(t, old.rows[oi])` dropped):

```
-        if oi >= 0 && old.rows[oi].kind == n.kind && same_as(t, old.rows[oi]) {
+        if oi >= 0 && old.rows[oi].kind == n.kind {
```

Red by name each time it was recut (on e528bbb5 as ca48f483, on e64d1751 as 8ec660a6, both before the last rebase): its stick, then section
d to the upgrade, `FAIL U3d-upgrade: missing 'beside /etc/shrc.pax-new' on the screen` (`14:49:35Z END legs-d
exit=1`; `22:53:38Z END legs-d exit=1`). The plan read `replace 12 the user left as shipped`, with no `keep` line:
the user's `/etc/shrc` would have been overwritten. Its recorded take is the plant record beside the green one.

### 4.5 The staged stick

`~/pax-smoke/pax-upgrade-kasumi-e64d1751.img`, read-only, from e64d1751 (`2010c379` now), the last code commit on
px92's head, before this branch was rebased onto trunk's px96 merge (`b8e77f7a`: the quiet console's write-error
lines) and px98's head (`946245e6`: px98's login, which this stick does not carry). The recorded take at this
branch's head builds and runs the stick again on that base:
- 1,119,879,168 bytes, sha256 `62e6c8944c8d6185ceddc49ddb1176af30466f755526b103e4ef4d457ae8dd63`: read twice on satoyama after the build, twice on nomad after the copy, and twice
  again staged;
- built by `tools/mkdistribution` (the dev variant: wolf 0.2.36, its musl sysroot and compiler-std) and `tools/mkdisk
  --usb`; `tools/check-usb` on the plain stick and again after the 860's line was appended by the stick's own
  `paxfat`, read back equal; a second build byte-identical;
- the stick of the three sections at the same head (4.3);
- its README, `README-upgrade-kasumi-e64d1751.txt`, names the 860's current install (8b4e98ae's dev install, upgraded
  by e528bbb5) and the
  steps: the second Limine entry, `pax-install --upgrade`, the line typed, the four photos, and a re-run after a cut.

It supersedes `pax-upgrade-kasumi-769bac07.img` (made before the 860 held 8b4e98ae's install: it carries no 8b4e98ae
baseline, so it would refuse that install by name) and `pax-upgrade-kasumi-e528bbb5.img` (sha256 `89e58a1e…490db0`,
the stick the 860 was upgraded with; it predates R-px93-9).

## 5. Done-when

### 5.1 Rulings (recommended and implemented)

- **R-px93-1, the mechanism.** A: a command-line word that kernel/fstab reads, with the disk's model and serial on
  the command line too (a second place to write the 860's line, which `limine.conf` would carry). B: a second fstab
  the word selects (`LABEL=pax-root /mnt/target`: no model or serial, so any PAX disk would mount). C: the word plus
  the stick's own `/pax/install-targets`, loaded by Limine as a second module, so the kernel and the installer read
  one file, written once from any OS. Recommended C, implemented. The ESP is not mounted (no FAT driver): `paxfat`
  writes it through the disk's node.
- **R-px93-2, the image's identity.** The stick's own sha256 cannot be known from inside it: it carries its
  allow-list line and its logs, and no file can hold its own image's digest. So the identity is the commit, the
  kernel's sha256, and the sha256s of `/etc/pax-release` and `/etc/pax-files.sha256`, which together fix every
  shipped byte. The staged stick's sha256 is in the baseline's `source` line, the README and this note. Implemented.
- **R-px93-3, the confirmation.** A: the contract's line, `UPGRADE /dev/sdX <model> <serial> <seed>`, typed as the
  screen shows it, its seed eight hex digits fresh each run. B: px78b's one word after the summary, the line kept for
  the scripted path and the log. Recommended and implemented A, the contract's text. B is a one-line change if the
  maintainer finds the line a chore.
- **R-px93-4, the homes.** `/home` is never touched, as ruled, and `/root` likewise (root's home is a user's too):
  neither is listed in a manifest. Implemented.
- **R-px93-5, a generated file the user changed.** `/etc/fstab`, the root's `limine.conf`, `/etc/pax-run` and
  `/etc/pax-login` are regenerated when they hold the installer's text. One the user changed is kept, with the
  regenerated text beside it as `.pax-new` (R-px93-B's rule, rather than overwriting it). The ESP's `limine.conf` is
  always regenerated. Implemented.
- **R-px93-6, what R-px93-E cut, brought back in the coordinator's order:**
  1. the 8b4e98ae baseline from px92's dev stick, read twice, and section d over it (U1d–U6d), the program built on
     the target by `/usr/bin/wolf` among the user's paths; the 9c88ec8a baseline kept;
  2. every fresh install writes its own manifest; `verify.py` holds it and counts it as installer-generated in its
     exact-tree check, red first (4.3); U9, the same stick's upgrade with no baseline;
  3. the non-PAX-disk and too-little-space refusals in the leg, each by name (U10, U11);
  4. no adb53141 baseline;
  5. Limine's BIOS stage, named as not exercised: the upgrade re-runs it when `limine-bios.sys` changes, and both
     old images carry Limine 12.9.1, as this one does.
- **R-px93-8, the 860's black first boot after the e528bbb5 upgrade** (the second boot worked). What in the upgrade
  path could make a first boot differ, and what each is held to:
  - *The ESP's write order.* The root is written before the ESP, `/boot/pax` by `paxfat replace` (a new chain, the
    entry, the old chain freed, each fsynced through the disk's node), the manifest last. PAX's fsync of a disk node
    is a FLUSH CACHE EXT (`kernel/ahci`), and the halt unmounts every volume, written back and flushed
    (`kernel/tree`'s `halt_volumes`). Nothing writes the ESP between the first boot and the second, so their bytes
    cannot differ. Under KVM the upgraded disk boots on its first boot every time (U4, U4d). Not a first-boot cause
    unless the upgrade did not complete, which its log on the 860 says.
  - *A journal replay.* None: the installed root is ext2 without a journal (`user/install/plan.lu`); kernel/journal
    serves ext3 volumes only. A root left not clean by an earlier hard power-off stays not clean and is mounted the
    same way at every boot (PAX runs no fsck).
  - *Limine's `quiet: yes` and `timeout: 0`* in the installed `limine.conf`, and the kernel's `quiet`: Limine draws
    nothing and boots at once, and the kernel prints only its summary and the login, so a black screen covers the
    firmware, Limine and the kernel alike, and a slow boot looks like a hung one. Unchanged by the upgrade (the same
    text before and after it).
  - *Outside the upgrade:* the firmware's first boot after its boot stick was removed, and the display's mode set
    at a cold power-on (the 4090, px87's console notes).
  - *The kernel:* e528bbb5's differs from 8b4e98ae's by kernel/fstab's upgrade entry, which returns at once without
    `pax.upgrade` (`kernel/fstab/fstab.lu`), and the commit it names.

  Recommended: no change without evidence. First the read-only evidence: the 860's
  `/etc/pax-install/upgrade-*.txt` (every `phase …: durable` line and `Upgrade complete`), and the root's
  superblock from CachyOS (`dumpe2fs -h`: the mount count, the last mount and write times, the state). Each boot
  that reaches PAX's root mount adds one to the count, so the count says whether the black boot got as far as the
  kernel's root mount. Then, if it did, PAX's console on the 4090; if it did not, the firmware or Limine. A
  diagnostic entry without `quiet` (and with a timeout) is the next step, and only on the maintainer's word: it
  changes the installed configuration px78 chose. R-px93-9's head changes none of this: the boot path (the ESP's
  order, `limine.conf`, the kernel's boot) is the same as e528bbb5's, so R-px93-8 stays open.
- **R-px93-9, an earlier installer's generated text** (the coordinator's, from px98's R-px98-3). `text_step`
  regenerated a generated file only when it equalled the new installer's text, so an unedited file in an earlier
  installer's text was kept as the user's. Now:
  - an upgrade writes it again when its sha256 is a known installer text for that path: the stick's
    `/usr/share/pax-install/baselines/generated.sha256` (`user/install/baselines/generated.sha256`: `/etc/pax-login`
    `85a48ba8…`, px78's through 44b44435's; `/etc/pax-run` `681996e1…`; both read from the 9c88ec8a and 8b4e98ae
    installs the leg made), or the old manifest's own row for the path when that manifest records installers' texts
    (a fresh install's, or an upgrade's whose source line says so);
  - the upgrade's manifest records each generated file's installer text, never a text of the user's it kept (an
    e528bbb5 upgrade recorded the text it left, so its rows are not trusted);
  - `/etc/fstab` and the root's `limine.conf` name the target's PARTUUID; their template is the only text any
    installer has written there (the same at 9c88ec8a, 8b4e98ae and this head), so equality already serves them;
    `limine.conf`'s digest is recorded from now on, and `/etc/fstab` has no manifest row (the image ships none);
  - U12, red first: an earlier installer's `/etc/pax-login`, the install's manifest naming it, regenerated with
    nothing beside it, and the console's login through it; then the user's edit kept with `.pax-new`; a third run
    "Nothing to change". Its first green take at 00c902f4 (`6c876db1` now) stopped after the regeneration, a fault of the row: the
    plan and the result were right (the regenerated line on the screen, `Upgrade complete`), but pax-install then asks
    "Type reboot to reboot now or poweroff to power off" at its own `pax-install>` prompt, which the row did not
    answer, so it waited 60 s for a shell's. The row now answers by powering off, as every other row does, and boots
    the upgraded disk to log in at the regenerated login: it is the text every fresh install writes, byte for byte
    (`85a48ba8…`), the login every U4 and U4d boot has used.

  Up to trunk `b8e77f7a` every installer's `/etc/pax-login` and `/etc/pax-run` were the same text: under KVM the
  e528bbb5 upgrade over the 8b4e98ae install left both equal to the installer's and wrote no `.pax-new` for either
  (U3d's plan and U4d's tree). px98's `installed_login()` is the first change to that text, and this branch sits on
  it: an upgrade from any earlier install (the 860's among them) finds `85a48ba8…` in the table and writes px98's
  login, nothing beside it, so U3 and U3d's plans now carry `text /etc/pax-login (the installed login: an earlier
  installer's text, regenerated)`, and U4 and U4d boot through px98's login.
- **R-px93-7, px92 first.** This branch was rebased onto px92's head `44b44435`, then onto trunk `b8e77f7a` (px92's
  and px96's merges), onto px98's head `946245e6` (merged first), and last onto trunk `37217ba0`; the recorded take
  and the plant are from this branch's head.

### 5.2 Not done

- Slots (R-px93-A) and the network (R-px93-C): later, as ruled.
- Limine's BIOS stage on an upgrade (R-px93-6's item 5): written, not exercised.
- U5's twin on the dev install: section d holds the program the target built before the upgrade and runs it after;
  the compiler is not exercised again there (U5 does it on section a's upgraded system, the same compiler).
- The upgrade on kasumi itself: the README's steps, for the maintainer. The 860 was upgraded with the e528bbb5 stick;
  its first boot after it was a black screen and its second worked (R-px93-8, open).
- The 860's exact history under KVM (8b4e98ae's install, the e528bbb5 upgrade, then this stick): not run. That
  upgrade reads the install's own manifest (an upgrade's, its generated rows not trusted), the path U6, U6d and U9
  take, with the same plan as from a baseline.

### 5.3 Checklist

Run before the PR, at e64d1751 (`2010c379` now) unless named (4.3), and recorded once more at the head:
- [x] `tests/ci-plan`, `tests/ci-budgets.py`
- [x] `tests/mpx6-disktools --only fat` (F5, `paxfat replace`), red first at the tests-only head
- [x] `tests/mpx6-install --rows smoke --tier native --firmware bios` (verify.py's I-manifest), red first at 4f2f6f10 (`96d60ef6` now)
- [x] `tests/mpx6-install --only metal`: the kasumi build, the 870 leg and the 860 leg over a used fat32 disk, KVM
- [x] `tests/mpx6-ahci --tier native --firmware bios --rows pr`
- [x] the upgrade leg (`tests/mpx6-install.d/upgrade.py`), sections a, d and x, KVM; U8 red first at the tests-only
  head
- [x] the plant, red by name
- [x] the staged stick: `tools/check-usb` twice, a second build byte-identical, sha256 read twice on each host
- [ ] CI at the PR head: full matrix, tier full (cross-cutting)
- [ ] on kasumi: the README's steps, by the maintainer
