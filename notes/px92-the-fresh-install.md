# px92 — the fresh install: kasumi's stick from trunk after px87, and the dev image's compiler at wolf 0.2.36 (P6)

Contract: `wolf/sprints/pax/92-the-fresh-install/px92-the-fresh-install.md` (crawl 54, 2026-11-04), under the lane
rules of 2026-10-31 and their additions. The lane built the maintainer's install stick for kasumi's 860 from trunk
after px87, by px86's recipe, and qualified it against an 860 that already holds a PAX install.

Two additions from the coordinator followed the same day:
- the same stick from the dev archive, so that the installed system has the compiler. Its qualification found
  that every program the dev image's compiler builds reads an empty `env_args()`: wolf-lang#962, fixed in wolf
  v0.2.36;
- re-pin `user/wolf.pin` to v0.2.36, red first, and rebuild that stick.

Footprint: cross-cutting (`user/wolf.pin`, a toolchain pin; `tools/distribution-root`).

The maintainer's disk serial is written `<kasumi-serial>` in every file under `notes/px92/`, because this
repository is public. The staged sticks carry it, and their sha256s cover it.

## 1. Forbidden, and what was read

No kernel's, firmware's, bootloader's, emulator's or driver's source was read. Limine 12.9.1 was run as a binary,
and QEMU 8.2.2 and OVMF as black boxes. From wolf-lang, only what the pin needs was read:
- the v0.2.36 tag's `rust-toolchain.toml` (the channel) and `crates/wolf_driver/STD-PIN` (the std commit);
- the subject of `378a5def` and its ancestry against both tags.

The runtime's source was not read; #962's cause is the coordinator's account of wolf-lang's record. The empty
`env_args()` was measured as a black box, on PAX in QEMU and on Linux in a container.

What was read in PAX's tree:
- the contract and everything it names: px86's contract and note, px78b's, px77c's and px87's notes,
  `docs/INSTALL-METAL.md`, `~/pax-smoke/INSTALL.txt` and px89's stick README;
- px86's stick recipe (`notes/px86/hasu/stick.sh`) and px87's qualification script (`notes/px87/stick/qual.py`);
- px65's and px90's notes, where they built the dev compiler and den;
- the code the stick and the installer run through: `tests/mpx6-install.d/metal.py`,
  `user/install/{allow,main,prepare,snapshot,ui}.lu`, `kernel/identity` (the boot line's format), `kernel/serial`
  (the memory transcript), `tools/{mkdisk,mkdistribution,distribution-root,mkwolf,mkwolf-std,mkdev,mkinstall,
  ci-plan}`, `tests/{distribution,distribution-boot,mpx5-wolf}` and `user/console/{distribution,wolf}.keys`.

kasumi was not touched. On satoyama every run held both locks, A outside and then B, except the takes the
maintainer exempted (§2). hasu was read and copied from, never run on. Nothing was installed; no label, merge,
tag, issue or release; no attribution trailers. On nomad only `~/lanes/px92/` and the staged files in
`~/pax-smoke/` were written.

## 2. Inputs, verified

- **Heads.** The contract named trunk `a6e2fcb5` (px87's merge) or a later trunk head. By the build, trunk was
  `9c88ec8a`, with notes only since `a6e2fcb5`; the release stick and the first dev stick are at `9c88ec8a`
  (R-px92-2). The re-pin is on this branch: the v0.2.36 dev stick is at `8b4e98ae` and the gauntlet at `086dc4e0`,
  with only notes and the README between the two.
- **Inputs.** px86's stick inputs, copied from hasu's `~/lanes/px86`: the cache, `build/inputs`, `base-dev.cpio`
  `098b918e…`, `limine-download`, `lope-local` and `live-payload.py`. The two hosts' manifests are equal (561 paths,
  by size and type). Added to them:
  - den (`user/den.pin`, px90), copied from px90's record at `b38643a5`: `den d4d3d6b8… 16698144`, as px90's note
    records (R-px92-1);
  - for the re-pin, `INPUTS/wolf` and `INPUTS/wolf-std`, built from source (§4.4).

  wolf 0.2.35 `4cc4045b…` and Limine 12.9.1 `5cdebc51…` were each read twice.
- **Containers.** `localhost/px75-ubuntu:2` for builds, `localhost/px78-ubuntu:1` for the legs and the Linux checks,
  and `localhost/r41-toolchain:1` for the compiler (rustup 1.97.1 with the musl target).
- **satoyama's slots.**
  - The release stick's build held slot B alone; it started before the maintainer's one-heavy-job ruling reached
    the lane. Its legs held both locks.
  - The two dev-stick takes and the compiler build ran under the maintainer's exception, "no locks, slot B's
    CPUs, beside vc17", with a 12 GiB cap and a sensor log beside each take (`logs/sensors-*.log`).
  - The waiting flock the exception replaced (pid 1383525, a blocked `-> FLOCK WRITE` on `satoyama-A.lock`, with
    no child) was stopped by its pid, as the coordinator asked.
  - The gauntlet, the plant and the facts were one take of both locks on slot A's CPUs.

Commits on `px92`. The failing row comes before the fix; the lane's tools, records and README follow.

- `c639bb04` notes/px92/prediction.txt, first.
- The release and first dev sticks' tools:
  - `58d866e4`, `634992bf`, `34abd8e9` make-variant.py;
  - `6f15664a`, `a37e3c62`, `45c1888d`, `0f5ec9d1`, `8548a940` satoyama/stick.sh;
  - `f45214d0` live-payload-dev.py;
  - `752ac0af`, `c1eb83e9` dev-compare.py;
  - `438fc98f`, `b8cf9209` the argument check on Linux;
  - `32b6d900` wolf.sh, `24ef3d37` i2.sh, `8b4e98ae` dev2.sh, `6a3a7aaa` facts.py, `086dc4e0` take3.sh.
- Records: `754d11ad` qualification.txt, `f90e3c79` dev-record.txt, `037b8edd` the paxfat issue draft,
  `5d33b425` the re-pin's prediction.
- **Red first:**
  - `f4b5083d` user/console/distribution.keys: on a dev image, build a program printing `env_args()` and run it with
    two arguments;
  - `bf8c0b04` tests/distribution-boot: I2 holds that program's output on the dev ISO.
- **The fix:** `8d1fa272` user/wolf.pin (v0.2.36), `ea29923c` user/wolf.sums, `7e16f25e` tools/distribution-root.
- **Docs:** `341ab63c` and `85078c03`, the README (README-only commits).
- Then this note.

## 3. Prediction, scored

The first prediction (`c639bb04`) was written at 05:00Z, before any build. `notes/px92/qualification.txt` scores
it in full:
- **Right:** the head; the size (one MiB more than the base case, 791 MiB); the reproducibility and corruption
  rows; the install-list digest; every M and P row; `by copy` under KVM; and the installed system being quiet,
  against px87's owed item.
- **Wrong:** the install times, 76.7 s and 57.1 s against 35–50 and 30–50 predicted. satoyama ran at 100 °C,
  shared with two lanes and the maintainer's builds.
- **Not foreseen:** the boot line wraps at a space at 1280x800.

The addendum (`5d33b425`) was written at 08:40Z, after the fix and the staged stick but before the gauntlet and
the plant. **Departure:** no prediction preceded the re-pin itself; the maintainer was waiting on the stick.

| predicted (`5d33b425`) | found |
|---|---|
| the second mkwolf build reproduces `user/wolf.sums` byte for byte; mkwolf-std `78b9d3cb` | **right** (`PASS the build reproduces user/wolf.sums`) |
| the release pair, I0 on both variants; I2 PASS on all four boots, the dev ones with `PX92-ARG=one`, `PX92-ARG=two`, `PX92-ARGS=0` | **right** |
| 35-45 minutes with the plant | **wrong**: 25 minutes (08:38:25Z to 09:03:35Z) |
| the plant: mkwolf reproduces v0.2.35's sums (`ef5dd0c2…`); I2 red by name on dev-bios after both release boots pass | **right** |
| d2cmp's `bin/` differences: a stamp of the head (its hash or its time) | **wrong for `bin/`**: the builders' random temporary names (§4.6). **Right** for `boot/pax`, `etc/pax-banner`, `etc/pax-release` and `boot.sha256`, which carry the kernel's head and digest |

## 4. Evidence index

The chains' logs are in `notes/px92/logs/`, compiler progress lines dropped and the serial masked (`build.log`, `legs.log`, `devresume.log`, `dev2.log`, `i2-red.log`, `take3.log`); the full trees are on satoyama under `/home/mfwolffe/lanes/px92/` until pruned, and on nomad under `~/lanes/px92/evidence*`.

### 4.1 The release stick, `pax-install-kasumi-9c88ec8a.img`

829,423,616 bytes, sha256 `850ff60b8e5e614233deb82fa040a8d99ece802569123b9cc93d91aef7179f7e`, read seven times.
The legs ran under KVM, each on a copy:
- **mpx6:** adb53141's staged stick over a used FAT32 860, kept as the 860 that M-PX6 left. Install 76.7 s.
- **pax:** this stick over that disk:
  - `--check` reads the 860 as `PAX's install layout`, and the page says `This install erases /dev/sdc's PAX's
    install layout.`;
  - install 57.1 s.
- **fat32, ext4:** px86's used-disk cases.

px87's rows in every leg:
- the kernel line, with the boot line after it, at the live login and at the installed login;
- the transcript quiet, live and installed;
- `poweroff` at both shells and at the installer's prompt, an ACPI power-off (QMP `guest-shutdown`, since
  `-no-reboot` makes a restart exit 0 too);
- the live entry writing no disk.

M5's witnesses (px78's `23e7b466…`, `e1203a73…`, `303fd56e…`) were unchanged after every boot. The record is
`notes/px92/qualification.txt`. Three findings:
- **The installed system is quiet.** pax-install's own configuration (`prepare.lu` `new_config`) has said
  `cmdline: quiet` since `61949606`, so px87 §5.4's owed item is stale.
- **The boot line wraps at a space** at 160 columns; make-variant.py's reader tries the next row both ways.
- **paxfat is slow on a large file:** `paxfat cat` of a 545 MB file ran over six minutes with nothing written
  (`notes/px92/issue-paxfat-cat.txt`, filed by the coordinator).

### 4.2 The dev stick at v0.2.35, and #962 found

`pax-install-kasumi-dev-9c88ec8a.img`, 1,116,733,440 bytes, `9e82ca4f…`. It is now superseded; its README says so.
- **Against the release stick:**
  - identical: the ESP's kernel, Limine files, configuration and list, and every file under `bin/`, `boot/` and
    `usr/share/pax-install/` (151 rows);
  - only in the dev archive (128 paths): `usr/bin/{wolf,wolf-cimport-worker,libwolf_rt.a,cc,ld.lld}`,
    `usr/lib/wolf-musl/` and `usr/share/wolf/compiler-std/`;
  - changed: `etc/shrc` (two lines), `etc/motd` (`PAX dev:`) and the file inventory.
- **The leg,** over the 860 as it is today (adb53141's install, then the release stick's): every row passed until
  D3. `wolf --version` gave 0.2.35; `wolf build px92args.lu` exited 0 in 6.6 s; then `./px92args one two`
  printed nothing, with status 0.
- **On Linux** (black box), with the dev image's own toolchain mounted at its paths:
  - the binary built on the 860 prints nothing;
  - the same source built on Linux prints nothing;
  - `count.lu` gives `count 0`, and so does `wolf run count.lu one two`.

  PAX's kernel and the installer are not involved (`notes/px92/dev-record.txt`).

### 4.3 The re-pin, red then green

| row | red | green |
|---|---|---|
| I2 on the dev ISO (`tests/distribution-boot`) | `bf8c0b04` against 9c88ec8a's images (v0.2.35): `I2 PASS release-bios`, `I2 PASS release-uefi`, then `AssertionError: guest-dev-args: b'PX92-ARG=one'`; the serial log shows the build and the run, `PX92-ARGS=0`, and no `PX92-ARG` line (`logs/i2-red.log`) | the gauntlet (§4.5) |
| D3 on the installed 860 (the variant's leg) | the v0.2.35 dev stick: `./px92args one two` printed nothing, status 0 | the v0.2.36 dev stick: `arg one`, `arg two`, status 0 |
| D4 `wolf run count.lu one two` | `count 0` (Linux, v0.2.35) | `count 2`, status 0 (the 860) |

### 4.4 The compiler at the pin, and how the dev archive takes it (R-px92-7)

- **The pin.** v0.2.36 at `5adf3d91…`, version line `wolf 0.2.36 (wolfgang, pin 5adf3d9)`.
  - Rust 1.97.1, from the tag's `rust-toolchain.toml`: the same channel as v0.2.35.
  - The std is `78b9d3cb…`, from the tag's `crates/wolf_driver/STD-PIN`: the commit `user/std.pin` already gives
    lupin.
  - `378a5def` (#962) is an ancestor of the tag and not of v0.2.35.
- **The build.** `tools/mkwolf` and `mkwolf-std`, unchanged, in `r41-toolchain:1`, `-j 8`:
  - the first build: 08:08:46 to 08:11:09Z, from a WIP commit whose `user/wolf.pin` is byte-identical to
    `8d1fa272`'s;
  - the second, in the gauntlet: 08:39:50 to 08:42:25Z, from a fresh clone of GitHub at `086dc4e0`, `PASS the build reproduces user/wolf.sums` (`cmp` of its `sums.txt`, all three files).

  `user/wolf.sums`: `wolf 2df1fb76… 16257584`, `wolf-cimport-worker 11850e70… 618688`, `libwolf_rt.a
  6892dac8… 46700882`.
- **`tools/distribution-root`.** The dev compiler's three files now come from `INPUTS/wolf`, held to
  `user/wolf.sums`, and replace the base payload's v0.2.35 rows (mode and owner kept). The compiler std is
  `INPUTS/wolf-std`, its `STD-REV` asserted against the pin's `WOLF_STD_REV`, in place of the base payload's
  `2386522e`.
  - Unchanged: the base payload (`BASE_SHA`), the link stack (`cc`, `ld.lld` and the sysroot, still the base's
    and held to `user/wolf-link.sums`), `kernel/wolf.pin`, `user/std.pin`, and the release variant.
  - `tests/distribution` I0 passes on both variants.
- **The v0.2.36 dev stick** (`8b4e98ae`): `pax-install-kasumi-dev-8b4e98ae.img`, 1,119,879,168 bytes,
  `665f815ab193907c007d7b431b6f833730bf1b51adbddf5ad92fb13d4d67501b`, read six times.
  - A second build of the plain stick was byte-identical.
  - Its leg ran over the 860 as it is today: P0, P1, P2 and M0–M11 passed, D1 `wolf 0.2.36 (wolfgang, pin
    5adf3d9)`, D2 `wolf build` 0 in 6.6 s, and D3 and D4 green. Install 62.5 s; the leg 197.0 s.
  - Staged in `~/pax-smoke/` with its README. The coordinator read it and put it at the top of INSTALL.txt.

### 4.5 The gauntlet and the plant

One take of both satoyama locks (A, then B; slot A's CPUs 0-3,8-11), 08:38:25Z to 09:03:35Z, `notes/px92/satoyama/take3.sh`.

**The gauntlet**, at `086dc4e0` in a fresh clone of GitHub with fresh directories. It stops at the first nonzero step and prints every END line (`logs/take3.log`):

```
2026-11-04T08:39:50Z END ci-plan exit=0
2026-11-04T08:39:50Z END ci-budgets exit=0
2026-11-04T08:42:25Z END mkwolf exit=0              (PASS the build reproduces user/wolf.sums)
2026-11-04T08:50:40Z END release-pair exit=0        (I0 PASS release 253 and dev 320 file digests)
2026-11-04T08:52:05Z END distribution-boot exit=0   (I2 PASS release-bios, release-uefi, and dev-bios and
                                                     dev-uefi with `a built program reads its argv`)
2026-11-04T08:52:05Z GAUNTLET GREEN at 086dc4e01efdfd161c37b05c7724c495d196f65e (exit 0)
```

Only notes and this note follow `086dc4e0`.

**The plant**, `px92-plant-wolf035` at `ff5ee469`: `086dc4e0` plus one commit putting `user/wolf.pin` and `user/wolf.sums` back at v0.2.35. It was pushed with no PR and run locally the same way:

```
2026-11-04T08:54:24Z END plant-mkwolf exit=0              (wolf 0.2.35 (wolfgang, pin cf0c13d); PASS the build reproduces user/wolf.sums)
2026-11-04T09:02:28Z END plant-release-pair exit=0
I2 PASS release-bios.serial.log … clean halt
I2 PASS release-uefi.serial.log … clean halt
AssertionError: guest-dev-args: b'PX92-ARG=one'
2026-11-04T09:03:29Z END plant-distribution-boot exit=1
```

It is red by name on dev-bios, the first dev boot, as at `bf8c0b04`. Not in the gauntlet, and left to CI's full-matrix: `tests/mpx5-wolf`, the pin's own suite, whose Linux side runs its own container engine, and the other suites `tools/ci-plan` selects for these paths (census, mpx3-console, mpx3-shell, mpx3-tree, mpx3-speaker, mpx4-session, mpx5-lupin, mpx5-wolf, mpx6-disktools, mpx6-install, mpx6-fsck).

### 4.6 The dev archives across two heads (d2cmp)

Against the v0.2.35 dev stick, the 8b4e98ae dev stick differs, as it must:
- `boot/pax`: the kernel writes its head into itself (px87's `tools/build-kernel`);
- the compiler, its std and the inventory.

It also differs in `bin/{pax-install,paxgpt,paxfat,paxext2,limine,reboot,poweroff}` and
`usr/share/pax-install/boot.sha256`, though none of their sources changed between the heads. `notes/px92/satoyama/facts.py` (`logs/take3.log`) compared the bytes. The stamping inputs are named:
- `boot/pax`: the kernel's head, at its `pax_kernel_commit` (px87).
- `usr/share/pax-install/boot.sha256`: `/boot/pax`'s digest, so it follows the kernel.
- `etc/pax-banner` and `etc/pax-release`: the kernel's head and digest, SOURCE_DATE_EPOCH, and the dev pin.
- `bin/pax-install`, `paxgpt`, `paxfat`, `paxext2` and `limine`: the builders' temporary directories. These are
  `mktemp -d $TMPDIR/pax-install.XXXXXX` in `tools/mkinstall`, `pax-disktools.XXXXXX` in `mkdisktools` and
  `pax-limine-static.XXXXXX` in `mklimine-static`, written into each binary's paths (for example
  `install.27BcPd/src/exe…` against `install.EG19y1/src/exe…`). The GNU build-id note follows from those bytes.
- `bin/reboot` and `bin/poweroff`: the C driver's temporary object name in the symbol table (`ccqeZ7EU.o` against
  `cc6Fqgjl.o`).

Neither the head's hash nor its time is in those programs. The gauntlet's build at `086dc4e0` differs from
`8b4e98ae`'s in the same files, though no source of theirs differs between those two heads. **A finding, owed to
file (pax):** the release pair's programs are not byte-reproducible across two builds of one commit, because their
builders write random temporary paths into them. One build's images are self-consistent (`tests/distribution`
holds them to that build's identity, and a second stick from one build is byte-identical), but two builds of one
head differ.

### 4.7 Rulings (recommended and implemented)

- **R-px92-1, the den input.** (A) copy px90's built den from its trunk record and check it against the digest
  px90's note records; (B) rebuild it with `tools/mkden`. **A**: it is px86's own way with inputs, and
  `tools/install-den` and `tests/distribution` hold den's bytes to its sums.
- **R-px92-2, the head.** (A) `a6e2fcb5`, as named; (B) trunk's head at the build, `9c88ec8a`, notes only since
  `a6e2fcb5`. **B**, as the contract says when trunk moves.
- **R-px92-3, the qualification's harness.** (A) a lane-local variant of the head's `metal.py`, made by
  `make-variant.py`, each edit asserted once and the diff the record; (B) the rows in `metal.py` itself, through a
  PR; (C) a separate script, which cannot see the installed system because `metal.py` deletes the target. **A**.
  Owed if CI should hold them: B, meaning `PAX_METAL_USED=pax`, px87's rows, the QMP shutdown reason and the dev
  rows.
- **R-px92-4, the 860 that M-PX6 left.** (A) a used FAT32 860, then adb53141's exact staged stick; (B) A after
  replaying 197330ad's failed attempt; (C) a blank 860, then adb53141. **A**.
- **R-px92-5 (the coordinator's, decided): the dev stick's minimal qualification.** One leg over the 860 holding
  the release stick's install, the kernel line, `wolf --version`, the `env_args()` row and the witnesses. The
  fat32 and ext4 legs were not repeated: the installer is byte-identical.
- **R-px92-6, the red row's place.** (A) `tests/distribution-boot`'s I2 on the dev ISO, the real image with the
  link stack; (B) `tests/mpx5-wolf`, whose fast root omits the link stack on purpose (its native build is red by
  design) and whose W rows run the checked machine; (C) a new suite. **A**. No CI job runs
  `tests/distribution-boot` today, only lanes before a release, so it is owed: a CI job for it, or a link-stack
  leg in mpx5-wolf.
- **R-px92-7, how the dev archive takes the new compiler.** (A) `INPUTS/wolf` and `INPUTS/wolf-std`, built by
  `tools/mkwolf` and `mkwolf-std`, replacing the base payload's compiler rows, with `BASE_SHA` unchanged; (B) a new
  `base-dev.cpio` with 0.2.36, rebuilding px82's whole payload; (C) a published musl archive (none exists, #887).
  **A**: the smallest change, and the compiler comes from the pin's own builder.

## 5. Done-when

### 5.1 Checklist

- [x] Item 1: the stick at trunk's head (`9c88ec8a`, R-px92-2), px86's recipe, the 860's line; sha256 read twice.
- [x] Item 2: the kasumi leg under KVM on an 860 that already holds a PAX install, and px86's used-disk cases;
  the witnesses unchanged; px87's rows on the installed system and the live entry.
- [x] Item 3: staged read-only at `~/pax-smoke/` with its README and reference screens; the INSTALL.txt line went
  to the coordinator.
- [x] Item 4: handed back at qualification. The qualification found no defect in this stick.
- [x] The coordinator's dev stick: built and compared, and its compiler found to give built programs no
  arguments (wolf-lang#962), discriminated on Linux.
- [x] The re-pin, red first: I2's row (`f4b5083d`, `bf8c0b04`) red at v0.2.35 by name; the fix (`8d1fa272`,
  `ea29923c`, `7e16f25e`); the v0.2.36 dev stick (`8b4e98ae`) qualified and staged (D3, D4); the gauntlet green
  at `086dc4e0`; the plant red by name; the README rows; this note; the PR; the audit.
- [x] README read against the pass: the pin table, the dev additions and the three facts moved (`341ab63c`,
  `85078c03`, README-only commits).

Test targets:
- [x] `tests/distribution-boot` (I2), both ISOs and both firmwares, KVM: green at `086dc4e0`; red at `bf8c0b04`
  (v0.2.35 images) and at the plant
- [x] `tools/mkdistribution` with `tests/distribution` (I0, I1) on both variants
- [x] `tools/mkwolf` and `mkwolf-std` at the pin, twice, reproducing `user/wolf.sums`
- [x] `python3 -I tests/ci-plan`, `python3 -I tests/ci-budgets.py`
- [x] The stick legs (the head's `metal.py` through `make-variant.py`, KVM): the release stick's four legs and
  the v0.2.36 dev stick's leg
- [ ] CI full-matrix (cross-cutting: `user/wolf.pin`): the 11 suites `tools/ci-plan` selects, mpx5-wolf among
  them; the orchestrator's

### 5.2 Departures and limits

- No prediction preceded the re-pin (§3).
- The release stick's build held slot B alone; the dev takes ran under the maintainer's exception (§2).
- The first dev take's `paxfat cat` was stopped by its pid; the check stands on `check-usb`'s U2.
- `tests/distribution-boot` has no CI job: the red row is the lanes' and the releases' until one exists
  (R-px92-6).
- The v0.2.36 dev stick's leg gave the guest 4 GiB (the dev root is larger). kasumi has more. The release legs
  kept 2 GiB.
- Nothing ran on kasumi.

### 5.3 Issues

Filed or closed: none. The coordinator files the paxfat issue from `notes/px92/issue-paxfat-cat.txt`. Owed to
file (pax), the orchestrator's call:
- the release pair's programs embed their builders' temporary paths, so two builds of one commit differ (§4.6);
- a CI job for `tests/distribution-boot`, or a link-stack leg in mpx5-wolf (R-px92-6);
- px87 §5.4's "the installed system's console is not quiet" is stale (§4.1);
- `metal.py`'s rows from `make-variant.py`, if CI should hold them (R-px92-3).
