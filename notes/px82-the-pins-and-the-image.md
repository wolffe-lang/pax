# px82 — px82: refresh image pins, stack capacity and build identity

_Materialised from the body of pax#224 at the merge (`cb600a4e`)._

Refresh the image inputs, qualify the new programs, and generate `/etc/pax-release` plus the boot identity. Addresses #176.


The earlier px73/px83 rebase was followed by one newly authorized rebase onto `895e9118` (px74). The complete raw USB stick is now qualified under both firmwares and against a real Linux USB/ESP oracle. No physical flashing or real-machine boot is claimed.

## Prediction

Committed first in `0b78efb2` (originally `1d7e09e9`), before implementation (`notes/px82/prediction.txt`). Yew and games did go red, but for concrete stack/fixture/probe causes, not a blind typing rig. Scent needed three expectation updates; its full transcript already matched Linux. Pelt's ordinary prompt remained compatible; opt-in features pass separately. Boreutils' root oracle hit a local container capability limit, not a pin verdict.

Image-size estimates were wrong. The prior verified dev ISO was 267,001,856 bytes; the new dev ISO is 535,083,008 bytes and release ISO 391,450,624 bytes. No comparable prior release ISO was available, so no invented release-before measurement. The images now carry 107 boreutils binaries, all three games and corresponding sources, and the offline installer payload/tools.

Game-size predictions held within their 20% bands: pack 15,413,192 bytes (gm01: same), cub 17,023,984 (15,579,480), trail 15,319,376 (15,317,552). Cub remains largest.

## Forbidden

No external kernel, libc, shell, grep, filesystem-tool or installer implementation source was read. The org's own source, documentation, fixtures and build tools were read; upstream projects were built unmodified. In particular, no yew or game source was changed. Spleen remains unmodified; the extra glyph drawings are PAX's own.

Builds and boots ran on hasu CPUs 0–5 under the block-A lock, in rootless Ubuntu containers capped at 12 GiB. No packages installed, host block devices used, service changes, Mac builds, merge, tag, release or PR labels. The root-oracle mount failure was not retried with sudo or a privileged container. The earlier Linux-reference sessions used the repository's existing isolated reference-container harness. Kasumi received the earlier `0252f60c` release ISO at the requested path; no additional kasumi writes were made in the rebase/USB follow-up; its existing playground data was not modified. The requested directory was absent and was created for this single copy; `lanes/orch-paxplay` was not touched. Planning repository and `~/.claude` unchanged. No attribution trailers.

This PR body is the five-section lane note: the agent wrapper prohibits report `.md` files. Materialize it as `notes/px82-the-pins-and-the-image.md` at merge.

## Inputs verified

Final code head: `cb600a4ecbade585f5053a886c1eeabba18242f8`. Final base: `895e9118`; launch base was `187aafdf`. The existing kernel/initramfs pair and ISOs remain built at `b925a7ab`, with USB qualification at `65ed60b0`. As directed, no hasu jobs or artifact regeneration were performed for the px74 rebase. These artifacts are not relabelled as builds of the new USB-keyboard kernel; the new labelled head goes through CI. Launch heads were read twice; source archives and release digests were read twice. Full pins/digests are in the pin files and `user/install/games.txt`.

| project | old | shipped | commits | visible change |
|---|---|---|---:|---|
| yew | `77c10839` | `0ccb2c67` | 1066 | search, undo, workspace features and Fletch prompt; unmodified |
| boreutils | `575dc7b9` | `0f7a57b6` | 347 | 107 command binaries; new checksum/numeric rows; df remains unshipped |
| scent | `b6f63a48` | `81d761d6` | 102 | recursive matching and current help/version; -P still explicitly refused |
| pelt | `0b5eaa53` | `4683b3f5` | 25 | friendly prompt/right prompt, noexec and floating printf fixes |
| lupin | `28547b43` / 0.1.56 | `6240efe5` / 0.1.58 | 101 | published musl interpreter, installed byte-for-byte |
| pack | `e10835f2` | `27848095` | 1 | source metadata refresh; binary unchanged |
| cub | `6153d975` | `6a1db765` | 446 | progression, opening, effects, block-digit HUD and cb08 diagonal atlas |
| trail | `6dbe253f` | `24099a81` | 8 | four-leg art; held before the broken probe inventory |
| lair for cub | `aa6c4dc0` | `74b89744` | 32 | follows cub's own lair.pin |
| lair for pack/trail | `aa6c4dc0` / `57870143` | unchanged | 0 | each game's own engine pin |
| lope / aspen / lobo | `e6f623c7` / `3692cf5d` / `49ed870e` | unchanged launch trunks | 0 | rebuilt; lobo included in the distribution |
| base std | `78b9d3cb` | unchanged | 0 | no backward pin movement |
| wolf | 0.2.35 | unchanged | 0 | compiler/kernel toolchain pin stays put |

Lupin 0.1.58 archive SHA256 `6ad6e008f97bce36b875e102906e2a949df5fd5d6f5cc693ae70fa19e376b533`; binary `b4f0f23c4028a4e37fb650dff1d417e90522a408de4b3a8ca3b8e80387676195`. Neither 0.1.57 nor 0.1.58 musl archive bundles a std tree/STD-PIN; the mirror's compiler STD-PIN is older `2386522e`, so base std stays `78b9d3cb`. Dev wolf keeps its own paired std at `/usr/share/wolf/compiler-std`; lupin uses `/usr/share/wolf/std`.

R-px82-1: take available 0.1.58, last, as directed. R-px82-2: wolf stays 0.2.35. R-px82-3: each game's own engine pin, never an unrelated lair trunk. R-px82-4: retain the newer base std. R-px82-5: recommendation A implemented on coordinator direction: one `procfs.USER_STACK_PAGES = 256` policy for a 1 MiB initial ELF stack and RLIMIT_STACK. The pinned compiler needs an accessor rather than an imported const in a comptime initializer. Cost is 224 additional eagerly allocated 4 KiB pages (896 KiB) per ELF address-space initial stack; fork copies it, runtime-created thread mappings are unchanged.

The B alternative is an unapplied, apply-checked input/policy switch: `git apply notes/px82/yew-policy-B.patch`. It selects yew `7249ff86` and 128 KiB, and requires rebuild/requalification; it is not a claimed final B gauntlet and that older editor lacks Fletch. Instructions are in `notes/px82/yew-policy.txt`.

## Evidence index

Implementation chunks:
- `72935fe9`, `f521edab`, `1d641d8a`, `a9b403ce`: separate yew/boreutils/scent/pelt pins and census snapshots.
- `50154b21`, `bedecc18`, `fdf32cc1`, `4126a13f`: game launch pins and lupin; `3b99b225`, `cf56c80e`, `df28b2c0`: final game selections.
- `63db001e`, `b2f0fae1`, `7dede6bb`: generated identity, banner and image assembly.
- `2d1b1345`, `c7bde23c`, `7812fa43`, `bc9261c8`: stack witness, shared policy/accessor and portable loader comparison.
- `21600f9d`, `909be478`, `97da488d`, `f5b1fae0`: font inventory and animation/replay fixtures.
- `72dc4ff1`, `8b8ce1cb`, `24a821fb`, `67047291`: measured scent rows, editor screenshots, shell prompt rows and new utility rows.
- `f6e20ce7`, `e0b8dd17`, `c74435b1`, `13f476eb`: installer integration, actual-image install test, exact interpreter/server packaging and live-snapshot fix.
- `04a4d7a2`, `12db04b0`, `cb9290e6`: README, sources/planner coverage and explicit fallback.

- `7a80ee0f`, `b925a7ab`, `1f77b939`, `65ed60b0`: cb08 refresh, full-pair USB qualification, large-volume and contained-oracle corrections.

### Named dispositions

**Boreutils B0/root B2: LOCAL SKIP, CI arbiter.** `tools/linux-run` could not `mount --rbind /dev` in the rootless build container (exit 32). Root reference outputs were absent, so their B2 comparisons are not pin failures and not local greens. The separate user oracle and both user boots passed 38 commands before the fourteen new checksum/numeric rows. Those new rows are wired into CI and are not claimed locally green. No privileged local retry. The existing mpx5-bore suite passed locally.

**Typing rig: proven working.** Launch-trunk `187aafdf` with its old pinned payload passed an explicitly typed line and clean halt through both serial and PS/2 in the same container. `/home/mfwolffe/lanes/px82/control/{serial,ps2}.log` and `control.log` retain it. No blanket “rig blind” waiver.

**Scent A2:** usage now says `grep`, version is 0.2.0, and `-r` returns the four correct fixed-directory matches/status 0. The full 225-line transcript already matched Linux. Precisely those expectations changed; old usage/version and wrong recursive output are negative controls. Final fresh-kernel runs pass all 49 rows on both firmwares. The phased -P refusal remains asserted.

**Yew / R-px82-5:** first-parent bisect and remeasurement identify first bad `d53daaea`, last green `7249ff86`. The merge embeds JobTable/ShSession values in Ed; variable storage is List-backed, not a giant new inline array. Compiled ed_new grows 160 bytes and ed_run 9,136 bytes (+9,296 together). At trunk, ed_run reserves 124,104 bytes and ed_new 13,128: 137,232 before saved registers/deeper calls, already beyond the former 131,072. The new 1 MiB policy keeps trunk yew unchanged. Y1–Y7 pass both firmwares, byte-identical to the preserved Linux references. Y8 adds five screenshots per firmware: editor, search, insertion, undo, interactive Fletch result 42; all 8,000 cells per screenshot match screen-ref. The loader L9 touches a real 256 KiB automatic object and checks 1 MiB soft/hard limits on both firmwares. L3's separate failure was unavailable awk `strtonum`, not a wrong stack literal; Python now parses readelf and the page expectation derives from the policy.

**Pelt:** F4 existing friendly sessions remain green. F5 verifies friendly identity/status/right prompt, float rounding, noexec and clean halt through framebuffer and explicitly sized serial, on both firmwares. The ordinary default remains opt-in.

**Games:** the refreshed cub scene animates; the old three-second quiet wait stopped later typing. The new 50 ms capture must match a generated 600-frame trajectory; the authored 120-frame committed-golden check is retained separately. Recorded cub gameplay uses explicit `--no-title`. The derived paused trail fixture omits stale score metadata from the original scored run. All G0–G6 pass native/release × BIOS/UEFI: exact 18/259/17 glyph probes, 262-codepoint union, 10 screenshot comparisons plus 3 withheld per leg, keys recorded and terminal restored for every game. Spleen remains unchanged; font has 560 glyphs, 16 ranges and four original PAX extra glyphs.

**Trail:** filed [trail#8](https://github.com/wolffe-lang/trail/issues/8), because `59050227` documents 18 glyphs but probes 17, omitting U+259B. The pre-scatter boundary `24099a81` is now qualified on all four game legs. Keep the issue open; do not silently waive the inventory check or modify trail here.

**Installer:** actual live-ISO installation exposed two integration failures. A generated live marker now omits only canned `/home/pax/Games` from the source snapshot, leaving the verified payload's yes/no choice authoritative; unmarked/custom sources still refuse pre-existing Games. Then the real live-root run refused `source_changed`: scratch creation changed retained `/tmp` metadata after snapshotting `/`. `0252f60c` reserves scratch first; mutation checks remain strict, including a new excluded-directory-metadata counterexample. The test detects missing command completion, unchanged target/zero effective writes, and nonzero installer status separately. The corrected live ISO installs onto a fresh 1 GiB guest disk, independent e2fsck passes all five phases, and the target boots alone under BIOS and UEFI with its complete release identity. No host block device is used.

**Final rebase and USB:** the one rebase preserved both source-log/CI-map additions and the px73/px83 README changes; `/Users/mfwolffe/lanes/px82/rebase-range.txt` records the comparison. Cub was then moved to supplied trunk `6a1db765` (cb08 source `1d0680a1` plus its note), 54 commits after `c8e5cf15`; its source digest is `257eeaec7f2d702ccd2b4d9eda25ae0f8d6aa25c7e321a1f78722cb58ebad372`, read twice. Ten additional braille patterns were already generated, so only the inventory changed. The refreshed four-leg games suite and all four ISO boots pass at `b925a7ab`.

The first full-payload USB qualification found three lane failures, not infrastructure outages:
- `usb-build`: `FAIL USB: FAT32 ESP geometry`. The builder succeeded and both firmware boots worked, but mkfs.fat's default 63-sector geometry rounded the FAT volume from 1,546,240 to 1,546,209 sectors. The pinned mkfs.fat(8) documents this rounding. USB only now uses synthetic `-g 1/1`, keeping exact partition coverage; the strict validator and legacy disk recipe remain unchanged.
- `usb-boots`: both sessions passed; the final hash check failed because the preceding checker had stopped before writing `usb.sha256`. This was a dependent failure, not failed boot/input.
- `usb-linux`: `tools/linux-part: line 91: docker: command not found`. Its engine-dependent staging had been called inside the container. Optional `--userland` now accepts the same pre-staged lsblk/blkid/library root, copied from the existing Ubuntu container; the guest remains contained without a nested engine, host socket, package install or privilege expansion. Default host staging is unchanged.

Only those phases were retried, with fresh logs/artifacts. `/home/mfwolffe/lanes/px82/usb-retry1.log` reports exit 0: staging 1 s, build/strict checks/repeat/negative controls 18 s, BIOS+UEFI 34 s, Linux oracle 13 s. The block-A lock was released between attempts and immediately after the retry; no idle allocation was held. Both GPT copies, protective MBR coverage, exact FAT extent and reserved Limine BIOS stage pass. All five boot files match their source bytes. Two builds are identical; missing EFI and shortened protective MBR are rejected by name. Both PAX boots have USB-only xHCI topology, no CD/virtio alternative, exact release identity and command witnesses. Real Ubuntu Linux 6.8.0-147 mounts the same ESP read-only and verifies all five digests; the raw image is unchanged afterward. Fourteen host unit tests plus six binary-fetch tests pass. The supplied initramfs is preserved byte-for-byte, including its root-shell startup, not silently replaced with the separate USB-login fixture.

### Local run records

Hasu `/home/mfwolffe/lanes/px82/`:
- `final-validation-logs/`: successful steps at `dbc60680`: census, planner, fallback, lobo, loader, games, session-kernels, yew, pelt-friendly, scent, distribution, distribution-boot (twelve exit-zero steps including preparation); one explicitly named local boreutils root skip. The first distribution-install failure is retained, never called green.
- `logs/install-fix-unit.log`: metadata/hash/link/copy guards and the new runtime-directory mutation counterexample pass.
- `logs/install-retry-image.log`, `logs/install-retry-e2e.log`, `install-retry.exit`: affected image rebuilt at `0252f60c`, then installer/e2fsck/target-alone BIOS+UEFI pass, all exit 0. No rerun of the earlier green suites was needed: only installer/test code changed. The kernel ELF is byte-identical across `dbc60680` and `0252f60c`.
- `yew-bisect/`: candidate binaries, boot transcripts, bisect log, first-bad/last-green records.
- `final-validation/mpx5-yew-*-features/`: screenshot offsets, PPMs and decoded grids; game screenshot/probe/record evidence is under `final-validation/mpx6-games-*`.
- `regression-logs/`: earlier full static pelt replay, lupin and installer suites; original named failures retained.
- `usb-refresh-logs/`: refreshed games/ISO inputs at `b925a7ab`, all four game legs and four ISO boots green; the three first USB failures retained.
- `usb-retry1-logs/` and `out/b925a7ab-usb-retry1/`: repaired raw build, positive/negative checks, exact repeat, both USB boots and real Linux ESP verification, all exit 0. The oracle uses px73's two exact binary Ubuntu packages, verified twice and extracted only under this lane; no install or maintainer script.


Plants, never merge:
| draft PR | run | named red |
|---|---:|---|
| #216 | 40463483046 | wrong pack archive digest; local `tools/mkgames` source archive mismatch, exit 2 |
| #217 | 40464179988 | generated yew release line differs from pin; local `AssertionError: release-yew` |
| #223 | 40528707070 | old stack policy: CI `FAIL L9 native kmain_loader bios: stack-probe did not touch its pages and exit 0…`; L3 was also red, with the parser limitation distinguished above |

Original plant CI verdicts remain coordinator-owned observations; no extra polling or labels by this lane.

### Final artifacts

All current artifact digests were read twice on hasu. The pair/ISOs identify their actual build at `b925a7ab`; the fixed raw-stick builder/checker is `65ed60b0` and wraps that pair unchanged. The kernel ELF remains byte-identical to the earlier qualified kernel.

| artifact | bytes | SHA256 |
|---|---:|---|
| release ISO | 391450624 | `a893e7e806033c1da36ac4249eda999c957629cc2a119c85e0c0e70650c5d04e` |
| dev ISO | 535083008 | `c0add739600ce24ca97e31a5c60e3288fce6ea2bd9c2d97617cb48a4d9c5bd6d` |
| release initramfs | — | `f23b7752d03097c88c8285b057a00cb32438eb1859997f197da58c6f6d7462e4` |
| dev initramfs | — | `d1ffd20f58be04065e1717d3f47d65e7e79357cd63d4b55e5f5f24c69fdbd84b` |
| kernel ELF | — | `7a1830d85b3f72b20c3c80b4851c3f2fa4a7292186ac04e1dbee3620d58c1aeb` |
| raw USB stick | 794820608 | `28500f5553033a120a5ffec308344ed1885c4091e5317d56ba510b5d256c3ff3` |

Hasu paths:
- `/home/mfwolffe/lanes/px82/out/b925a7ab/pax-b925a7ab.iso`
- `/home/mfwolffe/lanes/px82/out/b925a7ab/pax-dev-b925a7ab.iso`
- `/home/mfwolffe/lanes/px82/out/b925a7ab/release.cpio` and `dev.cpio`
- `/home/mfwolffe/lanes/px82/out/b925a7ab/kernel/kmain_console.elf`
- `/home/mfwolffe/lanes/px82/out/b925a7ab-usb-retry1/pax-stick-b925a7ab.img`

The original one kasumi copy remains untouched at `/home/mfwolffe/pax-playground/pax-0252f60c.iso` (SHA256 `16f8b1e3385a95322306215e2ba0a7b9a8a1018f86e575b6f3ef09c891f59037`, read twice there). It predates the cb08 refresh and is not represented as the current artifact. The current pair and stick are staged on hasu above.

`pax-release` and guest sha256sum were checked against the build's file. Each ISO's initramfs was extracted back and byte-compared; the USB validator independently extracts and compares its five files. Actual packed ownership, game/source bytes, boot payload and file inventory are validated, including the packed release-file corruption negative.

## Done-when

- [x] Prediction first; separate project pin commits; inputs/digests verified.
- [x] Current yew, pelt, scent, lupin and game qualification as named above; no upstream edits.
- [x] New editor screenshots, shell prompt rows, glyph coverage and CI-planned utility rows.
- [x] Image identity generated and checked against actual packed/guest content.
- [x] Live ISO install, independent e2fsck, target-alone BIOS and UEFI boots.
- [x] Refreshed release/dev ISOs and qualified raw stick on hasu, digests read twice; earlier one kasumi copy retained explicitly as historical.
- [x] README/SOURCES and CI planner refreshed; B fallback materialized but unapplied.
- [ ] PR-tier/full-tier verdict at the pushed head; coordinator adds labels and watches CI.
- [ ] Boreutils root differential including new rows: CI arbiter for the named local skip.
- [x] Final audit run once after the lease push; clean lane worktree removed without force. Only CI/tier/label gates remain.
- [x] Rebase exactly once after px73/px83; full-pair raw USB build, strict checks, both firmware boots and real Linux USB/ESP comparison.

Issues: trail#8 filed and stays open. #176 is addressed for review/closure at merge. No other issue closed, no merge or release performed.

### Prior audit handoff (65ed60b0)

Previous code head `65ed60b02ae84a362a3b52c8acb8a1e884a397f6`, pushed with an explicit lease. The immediate head-filtered run read returned `[]`; the single mandatory audit subsequently observed **40597497156**, in progress. No CI wait or second poll. The coordinator owns the full-matrix label and subsequent run watch.

Exact audit last line: `AUDIT FAIL (footprint: cross-cutting)`. The only holds are an in-progress head run, no green tier yet and the missing coordinator-owned label. Fast-forward ancestry, PR/head agreement, all five sections, all68 cited SHAs, no attribution, untouched spec, worktree removal and no orphaned lane processes pass. Audit record: `/Users/mfwolffe/lanes/px82/audit-final.log`.


### px74 integration handoff

Rebased once for this request onto `895e9118`, producing `27777c3a7aa793c697a01eda36ea89ecfa275af7`. Both conflict sides were retained: px74's USB keyboard paragraph, layout entries for mpx6-usb/mpx6-usbcheck and two booting commands, plus px82's image section; both CI-map additions remain. The tests-list changes merged without loss; px82 adds only its seven planner assertion lines over the new base. Range-diff shows all functional px82 commits unchanged; only README/CI-map conflict integration differs. Record: `/Users/mfwolffe/lanes/px82/px74-rebase-range.txt`. No second rebase, CI wait or hasu-job relaunch in this request. Existing artifacts at b925a7ab stand with their original provenance.


### Boreutils CI sizing correction

Run40606908064 at27777c3a, job122550550686, exposed a lane error: the fourteen added utilities grew initramfs-user.cpio to326878784 bytes, while the Linux-reference `/r` tmpfs still had a256MiB (268435456-byte) quota. `cp` first ran out of space at bin/expr, then later binaries and tiny configuration files also failed. This is separate from the earlier local root-mount restriction, and is not a runner-disk flake or an ELF-stack allocation failure.

`cb600a4e` uses one ROOT_MIB=512 constant for that reference quota and the already-512MiB QEMU budget. No assertion, utility, pin, runtime or shipped artifact changes. The23 local binary files alone occupy326897664 page-rounded bytes; both this measurement and the CI archive exceed the old quota and fit the new536870912-byte quota with over16MiB reserved margin. Shell syntax passes on hasu. No privileged local oracle retry or full local gauntlet is claimed; the new labelled CI run is the arbiter. Original failing log: `/Users/mfwolffe/lanes/px82/boreutils-ci-red.log`.

