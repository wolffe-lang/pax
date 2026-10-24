# px65 — The pins at 0.2.35, and boreutils' new utilities

Crawl 54, Opus 5.5. Contract `sprints/pax/65-the-pins-0235`. Branch
`px65` from trunk `68807993` (px64's merge), rebased at the
orchestrator's word onto trunk `f0617320` (px66's merge: GPT, `mkdisk
--gpt`, `pax-disk.img`) at a commit boundary, 77 commits replayed, the
conflicts only in the README's lists, the CHANGELOG and
`docs/SOURCES.md` (both sections kept). The prediction was committed
first, `b32f0984` after the rebase (`notes/px65/prediction.txt`). Every
build, boot and test ran on kasumi's CPUs 12-15 under `flock
~/lanes/kasumi-cores-12-15.lock`, in the lane's own Ubuntu 24.04
container (`notes/px65/Containerfile`, `localhost/px65-ubuntu`), the
Linux sides in their own throwaway containers, long jobs by
`notes/px65/launch.sh` (`setsid -f`, pid files, `ulimit -c 0`); nothing
was built on nomad-1.

boreutils: pinned at `575dc7b` (bu30 + bu31) before bu32 merged; at the
orchestrator's word it stays there, and bu32's checksums (`e690513`) go
to the next pins lane.

## 1. Forbidden, and what was read

No Linux kernel source, no other kernel's, no glibc's, musl's, gnulib's,
GNU coreutils', any shell's or any grep's; nothing of GNU coreutils was
run (the sessions run boreutils' binaries on both sides), and Linux's
calls were read by strace only. What was read is in `docs/SOURCES.md`
(px65): the org's own trees at their pins
(wolf-lang `cf0c13d3`'s CHANGELOG and version identity, wolf-interp
`v0.1.56`'s release and musl scripts, wolf-std `78b9d3c`, lope, aspen,
pelt, lobo `49ed870` and `v0.1.5`, boreutils `575dc7b`), the man pages
of the calls the census names, POSIX.1-2024's utilities, RFC 4648, and
PAX's own tree.

## 2. Inputs, verified

| input | found |
|---|---|
| pax trunk | `68807993` at launch; `f0617320` (px66) after the rebase |
| wolf | `v0.2.35` at `cf0c13d3`; linux x86-64 archive `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a`, 81,369,914 bytes: the release API twice, then two downloads on kasumi, each read twice (`notes/px65/kasumi-archives.out`); `wolf 0.2.35 (wolfgang, pin cf0c13d)`, bundled std `2386522e` |
| lupin | `v0.1.56` at `28547b4`; glibc archive `ad703550…` (3,027,812), and new at this release a musl archive `6303b47a8634e21d30336227022d4e70cf7cc6272946aa523b8edcee205cceb3` (3,045,794), each downloaded twice and read twice; the musl binary `c0ac08884199929e778c5cd87ea06f3643af33f1a98b2720957d1a181ef4b581`, 7,584,968 bytes, ET_EXEC, four PT_LOAD, no PT_INTERP, no dynamic section |
| wolf-std | `78b9d3c` (sc72, 0.2.36's STD-PIN) |
| lope, aspen, pelt | `e6f623c`, `3692cf5`, `70eec14` (sh24, sh25), each on wolf 0.2.35 / lupin 0.1.56 / std `2386522e` |
| lobo | trunk `49ed870` (v0.1.5 + 38, +dev) on 0.2.35; its newest release `v0.1.5` (`91b7613`) on wolf 0.2.33, archive `4f955e8d…` |
| boreutils | `575dc7b` (bu30 + bu31, 61 utilities; 14 new since `12de639`) |

## 3. Prediction, scored

| predicted | measured | score |
|---|---|---|
| P1: 0 bytes of any section on every kernel, native and release; weakest the freestanding runtime archive | +80 bytes of `.text` on every kernel, native (all 33 since px66's `kmain_part`) and release (`kmain_console`, `kmain_session`), `.rodata`, `.data`, `.bss` unmoved: the runtime archive, exactly the case named weakest. `libwolf_rt_none` gained `__wolf_rt_list_reserve`, 76 bytes (0x4c) padded to 80, and every kernel links the archive whole (§6) | wrong, the named weakest case |
| P2: every rebuilt program a new digest; scent unmoved (`bd860457…`); the musl archive a static PIE, so lupin from the tag; the dev compiler unpatched, with the release line | every digest moved but scent's, as predicted (§6); the musl archive is ET_EXEC with no PT_INTERP, not a PIE, so PAX takes it by digest (R-px65-1, the branch the prediction named); the tag built by `tools/mklupin` (Rust 1.97.1, the tag's own toolchain file, musl, static) gives other bytes (`804773f5…`, the same size); the dev compiler built unpatched at the first try, `wolf 0.2.35 (wolfgang, pin cf0c13d)`, two builds one set of bytes (R-px65-2) | right but the archive's type |
| P3: no utility blocked by a call; `tty`'s `/dev/ttyS0` the first thing to differ; else tty, then mktemp | none blocked: 34 calls, all served but glibc's 273 and 334; `tty` the one line typed `{tty}`; not foreseen, the file `/proc/self/maps` (§6, R-px65-5) | right, with one surprise |
| P4: none of the five tool suites' sessions moves; px57's recordings the same bytes (weak: pjobs) | three moved: mpx5-scent's abort row (pelt sh24 puts the signal notice through the redirected stderr), mpx4-lobo's Linux side (lobo ws68's `nobody` drop, R-px65-4), and of the recordings `sigs` and `sigs-user` (0.2.35's main-thread handler: SigIgn 0, and the overflow's `wolf-trap` lines); pjobs, groups, execs, eds and the rest held, 62 of 64; mpx5-lupin's and mpx5-wolf's literal versions (0.1.55, 0.2.34) moved by construction | wrong |
| P5: each new session about 60 s; byte-identical at the first boot but `tty` | the text sessions byte-identical at their first boot; the files sessions needed three fixes of the keys and rows, none of PAX (§6); a files boot (two sessions) 176 s, a text boot 102 s on kasumi | half right |

## 4. What was built

**The pins, one commit each** (rebased hashes): the kernel `27156fe4`
(`kernel/wolf.pin` 0.2.35 / lupin 0.1.56, the tour's line), lupin
`2979a025`, std `ff79aa50`, `tools/mkwolf` `42cbb9b0` and the dev
compiler `86de675c` (`user/wolf.pin` v0.2.35, `user/wolf-musl.patch`
gone), su `48139f35`, sigwolf `3cb6c93f`, edwolf `bf4c4c1b`, lope
`d18c908e`, aspen `b86dc6d6`, pelt `af584069`, `tools/mklobo`
`1349f5fc` and lobo `bccabf7e`, boreutils `b8e2eb31`, lupin's release
archive `f541f67d` + `1e657c02`.

**`tests/mpx5-bore`** (mpx5-scent's shape): two kmain_console images,
`files` (bu30's eight with `cat env id ln mkdir rm stat`) and `text`
(bu31's six with `cat env id mkdir rm sort wc`), pelt as `/bin/sh`,
`as`, the fixture (`tests/mpx5-bore.d/fixture.py`: the codecs' inputs,
the join and comm tables, tsort's graphs); `user/console/bore-files.keys`
and `bore-text.keys` typed as root (`env HOME=/ sh -i -m`) and as `pax`
(`as 1000 1000`). B0 the build; B1 each session byte-identical to the
container's, the console's name typed `{tty}`; B2 the rows
(`tests/mpx5-bore.d/rows.py`: 66 files rows, 46 text rows: POSIX's
answers, RFC 4648's encodings computed from the fixture, the
diagnostics' shape, tsort's order checked as a predicate, and `tty`
`/dev/ttyS0` on PAX); B3 -ENOSYS 273 and 334 only, nothing refused, init
ended 0, halted. CI job `mpx5-bore` (`d4206ea8`), mapped in
`tools/ci-tiers.map` (`@user`, `@asuser`, the keys), proven in
`tests/ci-plan`.

**Other changes.** `tests/mpx5-lupin` reads its record's identity from
`user/lupin.pin`; `tests/mpx5-wolf` reads its version line from
`user/wolf.pin` and takes its CPU list from `PAX_TASKSET_CPUS`;
`tests/mpx5-wolf.d` holds the 0.2.35 dev sessions
(`notes/px65/wolf-pax-*.tty`); `tests/mpx4-lobo` and
`tools/lobo-session` hand the Linux side the image's account files
(R-px65-4); `user/sigwolf` prints its fault-ignore row as `~X:` and
`tests/mpx5-jobs` holds each side's answer (R-px65-5);
`tests/mpx5-scent.d/rows.py`'s abort row takes pelt sh24's notice; the
mpx5-lupin CI step installs no Rust when the pin builds nothing.

## 5. Rulings asked (recommended, implemented, not decided)

- **R-px65-1: lupin from the release's musl archive, by digest.**
  v0.1.56 publishes a static musl lupin (ET_EXEC, no PT_INTERP, no
  dynamic section); PAX's tag build makes other bytes of the same size.
  Options: (a) take the archive by its digest and the binary's (`user/lupin.pin`
  `LUPIN_FROM=release`, `tools/mklupin` checks both, the type, no
  interpreter and the version line); (b) keep building from the tag.
  **Recommendation (a)**, implemented: the bytes the release ships are
  the ones its own CI tested, and no Rust is needed. Reversible: unset
  `LUPIN_FROM` and the tag build returns.
- **R-px65-2: the dev compiler unpatched, with the release stamp.**
  0.2.35 carries the musl fix (wolf-lang#886), so the tag builds for
  musl as it is; `tools/mkwolf` grants `WOLF_RELEASE` only when no patch
  is named and the tree is the tag's, clean. **Recommendation: so**,
  implemented; `wolf --version` in the dev image is the release's line.
  Reversible: name a patch and the stamp goes.
- **R-px65-3: lobo's release image at v0.1.5 with its own wolf.** No
  lobo release is on 0.2.35; v0.1.5 pins 0.2.33. **Recommendation: take
  v0.1.5 by its own wolf digest** (`LOBO_RELEASE_WOLF_SHA256`),
  implemented; the alternative, the trunk's wolf for the release tree,
  builds a binary lobo never shipped.
- **R-px65-4: mpx4-lobo's Linux side reads the image's accounts.** Since
  lobo ws68 a root lobo with no `user` line drops its hands to `nobody`
  when the account files name it; the container's do, PAX's image's do
  not. **Recommendation: copy the image's `/etc/passwd` and `/etc/group`
  into the container**, implemented: both sides then run one process with
  lobo's warning. Alternative: put `nobody` in PAX's image and hold the
  master-and-hand steps (a follow-up for lobo's session on PAX).
- **R-px65-5: `/proc/<pid>/maps` not served: name the row, file the
  issue.** wolf 0.2.35's runtime asks glibc's `pthread_getattr_np` for
  the main thread's stack, which reads `/proc/self/maps`; on PAX the
  call fails, the runtime installs no main-thread guard, and a program
  started with SIGSEGV ignored reads it still ignored. **Recommendation:
  the row as `~X:` (PAX's own), the missing file listed to file**,
  implemented; the alternative is to serve the file here (a procfs file
  from the address space's regions, larger than this pins lane).

## 6. Witnesses and measurements

**The kernel's cost** (`notes/px65/cost.sh`, `cost-table.py`):
every kernel built from trunk `f0617320` (wolf 0.2.34) and from the
branch (0.2.35), the same kernel source but the tour's one line, in the
lane's container on CPUs 12-15 (`notes/px65/kasumi-cost-native-f0617320.out`,
`kasumi-cost-release-f0617320.out`; before the rebase, the 32 kernels
against `68807993` gave the same +80, `kasumi-cost-68807993.out`). All 33
kernels on the native tier and `kmain_console` and `kmain_session` on the
release tier: `.text` +80, `.rodata`, `.data`, `.bss` +0. The 80 bytes
are one new function of the freestanding runtime, `__wolf_rt_list_reserve`
(76 bytes, the next symbol 80 bytes on at 16-byte alignment): `nm -S`
of both kernels' ELFs differs by that symbol alone
(`notes/px65/cost-symbols.txt`), and every kernel links
`libwolf_rt_none.a` whole (px21a). The release tier's other 31 kernels
were not built here.

| kernel | tier | trunk .text | branch .text | .text | .rodata | .data | .bss | branch ELF (first 16 of sha256) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| kmain | native | 1167787 | 1167867 | +80 | +0 | +0 | +0 | `27d1b764ad13e161` |
| kmain_blk | native | 1171867 | 1171947 | +80 | +0 | +0 | +0 | `386efa48ad535b48` |
| kmain_boreutils | native | 1170763 | 1170843 | +80 | +0 | +0 | +0 | `ada1b33e02a22716` |
| kmain_console | native | 1188011 | 1188091 | +80 | +0 | +0 | +0 | `628eaded088a5cae` |
| kmain_double_fault | native | 1166043 | 1166123 | +80 | +0 | +0 | +0 | `46145cd9ab7489e2` |
| kmain_double_free | native | 1166107 | 1166187 | +80 | +0 | +0 | +0 | `a226e513e99e76ad` |
| kmain_frames | native | 1171435 | 1171515 | +80 | +0 | +0 | +0 | `9473c0203d2293e1` |
| kmain_free_unusable | native | 1166059 | 1166139 | +80 | +0 | +0 | +0 | `31b9febbea19289e` |
| kmain_heap | native | 1172379 | 1172459 | +80 | +0 | +0 | +0 | `71dae48bb6737d1a` |
| kmain_heap_double_free | native | 1166123 | 1166203 | +80 | +0 | +0 | +0 | `441d61a12f56f192` |
| kmain_heap_fault | native | 1166267 | 1166347 | +80 | +0 | +0 | +0 | `d2c57ab61a02b2d9` |
| kmain_heap_oom | native | 1166395 | 1166475 | +80 | +0 | +0 | +0 | `a870e471bf998a2c` |
| kmain_heap_threads | native | 1174587 | 1174667 | +80 | +0 | +0 | +0 | `8aa73c8e7543dfad` |
| kmain_heap_wild_free | native | 1166235 | 1166315 | +80 | +0 | +0 | +0 | `41bc5705343962a1` |
| kmain_int3 | native | 1166139 | 1166219 | +80 | +0 | +0 | +0 | `37b519d943f2d505` |
| kmain_loader | native | 1169675 | 1169755 | +80 | +0 | +0 | +0 | `7e81553e650ad250` |
| kmain_net | native | 1186155 | 1186235 | +80 | +0 | +0 | +0 | `e171f4707cbc9088` |
| kmain_paging | native | 1170315 | 1170395 | +80 | +0 | +0 | +0 | `40a56bc2d302b5bd` |
| kmain_panic | native | 1166027 | 1166107 | +80 | +0 | +0 | +0 | `15a0ee2361000b3d` |
| kmain_part | native | 1170939 | 1171019 | +80 | +0 | +0 | +0 | `27439024eccd1816` |
| kmain_sched | native | 1175291 | 1175371 | +80 | +0 | +0 | +0 | `afab0bff5fac25e6` |
| kmain_sched_overflow | native | 1172475 | 1172555 | +80 | +0 | +0 | +0 | `f92111c923cb24ff` |
| kmain_screen | native | 1180011 | 1180091 | +80 | +0 | +0 | +0 | `e4fb8d841fdd90a9` |
| kmain_session | native | 1178251 | 1178331 | +80 | +0 | +0 | +0 | `dfb11c136d1e742b` |
| kmain_sockets | native | 1174379 | 1174459 | +80 | +0 | +0 | +0 | `09449369d5688224` |
| kmain_text_write | native | 1166171 | 1166251 | +80 | +0 | +0 | +0 | `29f1c611064590fd` |
| kmain_timer | native | 1167787 | 1167867 | +80 | +0 | +0 | +0 | `49c50eca58541f63` |
| kmain_tour | native | 1188203 | 1188283 | +80 | +0 | +0 | +0 | `3456c430a69a8b36` |
| kmain_tour_text | native | 1183195 | 1183275 | +80 | +0 | +0 | +0 | `c5e518b986dfa248` |
| kmain_ud2 | native | 1165963 | 1166043 | +80 | +0 | +0 | +0 | `34bdc16700b7a7d7` |
| kmain_user | native | 1168827 | 1168907 | +80 | +0 | +0 | +0 | `622e10e6b9dca68e` |
| kmain_user_smap | native | 1167451 | 1167531 | +80 | +0 | +0 | +0 | `520c74cfeef2f2a7` |
| kmain_user_smep | native | 1167339 | 1167419 | +80 | +0 | +0 | +0 | `4bcf399e6a25f296` |
| kmain_console | release | 1070715 | 1070795 | +80 | +0 | +0 | +0 | `a8b3c84b03867a46` |
| kmain_session | release | 987611 | 987691 | +80 | +0 | +0 | +0 | `ba4df60e1d067d3d` |

**The binaries** (built on kasumi, in the suites' builds and again in the
playground's at `92c26bf2`, the same digests; lobo's two in CI's
mpx4-lobo job, run 40038884586; where both built a program, the runner
built kasumi's bytes: pelt and the fourteen new utilities in the plant
runs' logs):

| program | sha256 | bytes |
|---|---|---:|
| pelt `70eec14` | `c24ab1ed04aae129a4b02313bcfd6dd0e111a810b49fcfb3a734f3160af78d97` | 15,967,448 |
| lope `e6f623c` | `013f0335e072e9fd2edeca89fe72103511cb1271e689f2d344638e33c68c80e6` | 15,281,616 |
| aspen `3692cf5` | `77a974bfe16e97d825d3da27ee3f83080d999eda885fd9e503bada26d84a64a5` | 15,523,376 |
| lobo `49ed870` | `b28a532aec3bcab36dad0c5c05ba33b4550102ab58e62c34b63c28036a47ab37` | 16,640,320 |
| lobo `v0.1.5` | `c8ad582dbf42abbff7c8731e891ca2ff81ee5c309a536a523cab7f5f702ef20a` | 15,993,632 |
| lupin 0.1.56 (the release's) | `c0ac08884199929e778c5cd87ea06f3643af33f1a98b2720957d1a181ef4b581` | 7,584,968 |
| su | `acfcc313f9a3386dc043e7cbc2a0ec13e7ef2194942049071a0b17d6aadbf2e0` | 14,788,000 |
| sigwolf (`~X`) | `39d0ae9b277b186c5da84f2087c94b24bb0df2074397336244d5698a777ec056` | 15,174,000 |
| edwolf | `6572d4660cf7182acd2dcf8c910a1eb36c616ab27c77d781165058a8604643c8` | 15,254,832 |
| yew `77c1083` (its pin unmoved; its own toolchain) | `c2daa653e398640e98c627c3b6cfb6bf454b60fa3d6444ed754767e0c8764b67` | 16,101,824 |
| play (`user/play`) | `feef16f3873489ac10b4b0d09f20cfe3859a1c1647bbd4ed3150addeb63f2d14` | 14,854,640 |
| scent `b6f63a4` (unmoved) | `bd860457f2ff97591b7525da5f46c186feee4b8266d3f51b121866b001135d89` | 14,846,984 |
| std tree `78b9d3c` | manifest `06938b3f17fda10cb5b4008a5743e1a04ee5e42797e0cd8c4bc7ae3be60b8fa8` | 56 files |
| dev `wolf` (v0.2.35, musl) | `ef5dd0c20872af1014fc65f399d49aa8fce319b5b762a92157cf6f6b6a7ce9ca` | 16,020,016 |
| dev `wolf-cimport-worker` | `2e658a17954ad8e77a29133d9d97ac8f4d55798f436d323fd485b725fb96cb3c` | 618,688 |
| dev `libwolf_rt.a` | `9d859b9e6b5319f5a6f609e73ba0d71981d2dfa489882648ac9f454cd9db739c` | 45,363,160 |

The dev compiler's three were built twice on kasumi to one set of bytes
(`user/wolf.sums`). boreutils' 61 at `575dc7b`:
`notes/px65/boreutils-sums.txt` (the playground build's `sums.txt`);
the fourteen new ones also in each mpx5-bore run's log.

**The census** (`notes/px65/census.sh`, `census/`, `census.out`; the
table in `docs/CENSUS.md`, "Served since px04: boreutils' new
utilities"): strace 6.8 over a short session of each new utility's
common options in the lane's container: 34 calls, every one with a PAX
handler but `set_robust_list` and `rseq`; new to the px04 union
`mknodat` (mkfifo, px62) and `linkat` (link, px36). Not asked: `sync(2)`,
`syncfs(2)`, `fstatfs`, `fallocate` (bare `sync` and `sync -f` are
refused by boreutils itself, wolf-lang#906). `getrandom` served. The one
file PAX lacks: `/proc/self/maps` (R-px65-5).

| utility | blocked on PAX by |
|---|---|
| mkfifo, link, unlink, truncate, sync, mktemp, realpath, tty | nothing |
| base64, base32, comm, join, tsort, shuf | nothing |

**The sessions** (kasumi, chain D, native BIOS, `0bf1bbe`'s tree):
files: 306 lines byte-identical to the container's as root
(`f8b6ac1e16dc…`) and as `pax` (`735ddfa79415…`, its own paths), 66 of
66 rows each; text: 256 lines (`81580fc0304c…`, root's and pax's the
same bytes), 46 of 46; B3 both. The files keys needed three fixes on
the way, none of PAX: a typed line longer than the console's 80 columns
(the console wraps it; split in two), `mktemp -u`'s random name leaking
into a `stat` diagnostic (now only `stat`'s status), and `truncate -s
1Q`, which boreutils reads as `Q`, quetta (2^100, GNU 9's suffix), an
overflow (`Value too large for defined data type`), where the row had
expected a bad number; the container's same binary said the same.

**The suites at the new pins on kasumi** (every one on the `68807993` base, before the rebase; after it the CI dispatch below ran them all, px66's suites with them): mkw (M-KW) and the tour
(R0 native and release) PASS; mpx5-accounts, -aspen, -lope, -lupin,
-pelt (72 checks), -wolf, -scent and -bore PASS; mpx5-jobs (238 checks, every image against real root's recordings as they now stand) PASS; and the suites whose builds run a chroot (`--privileged`): mpx3-boreutils, mpx3-shell, mpx3-tree PASS (chains A to D, `notes/px65/kasumi-chain-*.out`; chain D at `0bf1bbe`, the pre-rebase head with every fix).

**px57's recordings, again** (`notes/px65/vm-rec.sh`, `rec-twice.sh`:
real root's guest, the same binaries, recorded twice): 62 of 64 are the
committed bytes, both records alike; `sigs` and `sigs-user` moved: the
0.2.35 runtime's SEGV handler means a child started under the fault
ignore now reads SigIgn 0 on Linux, and the overflow prints
`wolf-trap: stack-overflow` and its `at pc=` line before the task's
`wolf-rt:` line. Re-recorded (`cff34e4d`), rec1 = rec2
(`notes/px65/kasumi-recordings-twice.out`). On PAX the row reads
SigIgn `…0400` (no main-thread handler: R-px65-5), held as `~X:`.

## 7. The dev ISO

`notes/px65/dev-iso/` (px64's recipe, px62's before it, lane-local:
`verify.sh`, `build.sh`, `assemble.sh`, `boot.sh`, driven by
`notes/px65/dev-all.sh` at one tree commit): the base userspace at the
head's pins (61 boreutils utilities, pelt, lope, aspen, yew, scent with
its link and wrappers, su, play, the musl lupin, the std tree), the dev
compiler of R-px65-2 (`wolf`, worker and runtime verified twice against
`user/wolf.sums`, px60's link stack against `user/wolf-link.sums`);
booted with 2 GiB under TCG and typed px64's `dev.keys` (mpx5-scent's
session as root, `su pax`, the session as pax, then px62's dev session).

| | |
|---|---|
| tree | `92c26bf2` (`SOURCE_DATE_EPOCH` 1792801437, its commit time; the trunk-base `f0617320` tree with every px65 change but the notes after it, none of which an image reads) |
| kmain_console.elf | `0fb3628137b99e6fb14f9a2a4f2a39add86677bb5588bdfcd6522b0fd2006105` |
| `pax-dev.iso` | `02f979bedf5520661f8a5e5623f1f9a7f5cb18b2b1d8c936b3d51f8c0336d4d9`, 264,144,896 bytes: read twice after assembly, again twice after kasumi's first crash (21:41) and once after its second (22:01), and twice on nomad-1 after the copy (`~/pax-playground/pax-dev.iso`, 22:02:52; px64's, `e9abd454…`, kept as `pax-dev.iso.px64`) |
| `pax-dev-smoke.iso` | `4c2430f0721512efb624ee1310943f921c5d0d40da4b5e7c97a68be541b0f5c0`, read twice after assembly and twice after the first crash; not copied |
| the archive | 257,111,844 bytes: `link 120777 5 bin/grep -> scent`, `bin/scent` 14,846,984 (unmodified), `bin/egrep`, `bin/fgrep` 240, `bin/sh` (stripped pelt) 2,346,136 (`kasumi-dev-assemble.out`) |
| the boot | 153 s, HALTED; `wolf --version` at the console `wolf 0.2.35 (wolfgang, pin cf0c13d)`; px62's `check-dev-session.py` PASS (pax identity, typed checked execution, object emission, native build and run, the release tier refused by name, the jump to /home/pax, no mapping refused, a clean exit); px64's `check-scent-session.py` PASS, 49 rows as root and as pax (`kasumi-dev-boot.out`, the serial log `kasumi-dev.serial.log`) |

kasumi crashed at 21:41 (no shutdown record) during this boot: the
verify, build and assemble steps had finished (their logs and the
ISO's two reads stand); the boot's half-written `dev-boot/` was
discarded and the boot alone run again by `notes/px65/chain-f.sh`, after
the ISO, its smoke twin, the kernel and the edk2 file read the same as
before the crash.

## 8. The playground

Built once (`notes/px65/play/build.sh`: the head's pins, 61 boreutils
utilities, pelt, lope, aspen, scent, yew, the musl lupin, su, play, std,
`/bin/reboot`) and assembled two ways, both driven by
`notes/px65/play-all.sh` at `92c26bf2`. The binaries are stripped copies
but scent (unmodified, `/bin/grep` its archive link, the wrappers); the
motd names px65's pins and the fourteen new utilities.

- **The ISO** (px63's recipe, `notes/px65/play/`): `pax-playground.iso`
  `cabfee58ae268dc5fb274c5ba95023233a073137c6d71f9f66aa02b0ef169a55`,
  124,170,240 bytes (px63's had no scent and 47 utilities: 84,846,592);
  with a TEST disk (`tools/mkdisk --home 128M`, `58800cd6…`, never the
  maintainer's) the maintainer's session PASS: both boots mount /home
  from the disk, mount 1 then 2, `notes.txt` 34 bytes, reboot(2) writes
  the volumes, the second boot reads the note, `exit` halts; e2fsck -fn
  clean, debugfs reads the note.
- **The disk** (px66's recipe, `notes/px65/disk/`): `pax-disk.img`
  `edb02ddfda7786748f9018d693eeea5a2f7d64f1f1090cc7803870ffa698cb2e`,
  536,870,912 bytes (BIOS boot, ESP 192 MiB FAT32, /home ext2), a
  second `tools/mkdisk --gpt` byte-identical; the oracles: sgdisk -v `No
  problems found`, fsck.fat -n `10 files, 235485/387101 clusters`,
  e2fsck -fn `12/81408 files`. The maintainer's session on a copy, under
  SeaBIOS and under the Mac's own `edk2-x86_64-code.fd` (`33090cc0…`) as
  a read-only pflash (`-drive if=pflash,format=raw,unit=0,readonly=on,file=…`,
  the README's line; `-bios` with that file is refused, px66): PASS both,
  8 checks each (both boots `boot: … from a disk: partition 1, GPT disk
  …` and `fstab: /dev/vda2 on /home`, mount 1 then 2, the note written,
  reset, read back, `exit` halts), the host's dumpe2fs `clean`, mount
  count 2, e2fsck -fn clean, debugfs reads the note.

Copied to nomad-1's `~/pax-playground/` with `rsync -S` and read twice
there (`notes/px65/play-out/digests.out`): `pax-dev.iso` (px64's
`e9abd454…` kept as `pax-dev.iso.px64`), `pax-playground.iso` (px63's
`d51e473f…` kept as `pax-playground.iso.px64`), `pax-disk.img` (px66's
kept as `pax-disk.img.px66`). `pax-home.img` was never written: the
same size, mtime and digest (`aee2c192…`) before and after. The
maintainer's QEMU (pid 39991) had px66's `pax-disk.img` open
read-write throughout, so that file was not hashed (its bytes were
live) and was renamed, not copied: the session keeps its open file and
goes on writing to `pax-disk.img.px66` (lsof: the same inode); the next
boot by the README's line takes the new disk.

kasumi crashed a second time at 22:01 (a hard stop) during the first
playground build: its half-built `play/w` was discarded and play-all run
again from the start (`notes/px65/play-out/kasumi-play-all.out`); the
dev ISO there read the same after this reboot too.

## 9. CI

Plants, each a branch never merged, cut from `95d72f57` (pre-rebase),
dispatched `-f tier=pr -f suites=mpx5-bore`, predicted by row before
either ran (`notes/px65/plants.txt`):

- `px65-plant-tool` (`6da5404c`, the files image without
  `/bin/realpath`): run 40042007705: B0 green; B1 red, both sessions
  (`realpath: not found`, status 127, where the container answers); B2
  red at the PATH row and at the 12 realpath rows (predicted 13: the
  rows are 12), both sessions; B3 green; the text image green
  (`notes/px65/ci-40042007705-plant-tool.txt`).
- `px65-plant-enosys` (`116468df`, kernel/user's `linkat` answered
  -ENOSYS): run 40042009610: B0 green; B3 red for the files image
  (`-ENOSYS for '265 273 334'`); B1 red, both sessions (`link: cannot
  create link 'b' to 'a': Function not implemented`); B2 red at the
  link rows and the rows that read link counts after them (four), as
  predicted; the text image green
  (`notes/px65/ci-40042009610-plant-enosys.txt`).

Discovery and gates: dispatch 40033403434 green (the R-px65-4 fix;
40030216474 was its red); dispatch 40038884586 at `5c03f9d5`: every job
green but mpx5-jobs, mpx5-bore and mpx5-wolf, each since fixed (the
`~X` row, the keys, the sessions and CPU list); after the rebase onto
`f0617320`, dispatch 40044745506 at `940bedd9` (`-f tier=pr`: the plan
selects every suite, px66's mpx6-part among them): 47 jobs, every one
green. The final head's `tier pr` run is named in the PR.

## 10. What a PAX user sees (the gaps, by whose)

- **PAX's:** `/proc/<pid>/maps` is not served, so a wolf program's
  main-thread stack overflow ends by SIGSEGV where Linux prints
  `wolf-trap: stack-overflow`; task threads' overflows are reported on
  both. A program started with SIGSEGV ignored keeps it ignored.
- **boreutils', by design and on Linux too:** bare `sync` and `sync -f`
  are refused (wolf has no `sync(2)` or `syncfs(2)`, wolf-lang#906).
- **the environment's:** `tty` says `/dev/ttyS0`, the serial console,
  where a terminal emulator's says `/dev/pts/N`.

## 11. Issues and what to prune

To close: none. To file (listed, not filed):

- pax: serve `/proc/<pid>/maps` (glibc's `pthread_getattr_np` reads it
  for the main thread; wolf 0.2.35's runtime needs it for its
  main-thread guard; `notes/px65/probes/`), then drop `~X` back to `X`.
- pax: lobo's session with `nobody` in the image (the master and one
  hand, R-px65-4's alternative), so PAX holds lobo's privilege drop.
- wolf-interp: the v0.1.56 tag built at its own toolchain gives other
  bytes than the release's musl archive (`804773f5…` against
  `c0ac0888…`, both 7,584,968 bytes); a note for its reproducibility.
- the next pins lane: boreutils bu32's checksums (`e690513`).
- pax: the release-tier cost of the 31 kernels not measured here.

Prune (the lane's own) once the PR merges: kasumi `~/lanes/px65/`
(`build/`, `dev/`, `play/`, `vm/`, `exp/`, `ev/`, `cache/`, `tmp/`,
`trunk/`, `trunk-f0617320/`, `wolf-b1/`, `wolf-b2/`, `wolf-out/`,
`lope/`, the worktrees `w-a` to `w-e` and the pax clone) and the image
`localhost/px65-ubuntu`; on nomad-1 the lane's checkout `~/lanes/px65/` with its plant worktrees; the plant
branches `px65-plant-tool` and `px65-plant-enosys` stay on origin as
evidence (never merged).

## 12. Evidence index

### What was written

- The pins: `kernel/wolf.pin`, `kernel/pax_tour/pax_tour.lu`'s line,
  `user/lupin.pin`, `user/std.pin`, `user/wolf.pin` and `user/wolf.sums`
  (`user/wolf-musl.patch` removed), `user/{su,sigwolf,edwolf}/wolf-toolchain.toml`,
  `user/lope.pin`, `user/aspen.pin`, `user/pelt.pin`, `user/lobo.pin`,
  `user/boreutils.pin`.
- Tools: `tools/mklupin` (the release archive by digest), `tools/mkwolf`
  (the release stamp for an unpatched tag), `tools/mklobo` (the release's
  own wolf digest), `tools/lobo-session` (the tree's accounts).
- Tests: `tests/mpx5-bore` with `tests/mpx5-bore.d/` and
  `user/console/bore-{files,text}.keys`; `tests/mpx4-lobo`,
  `tests/mpx5-lupin`, `tests/mpx5-wolf` (+ `.d/rows.py`, `test_rows.py`),
  `tests/mpx5-jobs` (+ `.d/linux/sigs*.tty`, `vm-sigs*.meta`),
  `tests/mpx5-scent.d/rows.py`, `tests/ci-plan`; `user/sigwolf/sigwolf.lu`.
- CI: `.github/workflows/ci.yml` (the mpx5-bore job, the lupin step, the
  comments), `tools/ci-tiers.map`.
- Docs: `README.md`, `kernel/README.md`, `CHANGELOG.md`, `docs/CENSUS.md`,
  `docs/SOURCES.md`; this note.
- The lane's scripts (`notes/px65/`): `Containerfile`, `launch.sh`,
  `build.sh`, `boot.sh`, `regress.sh`, `wt.sh`, `mkw.sh`, `archives.sh`,
  `cost.sh`, `cost-table.py`, `mkwolf-twice.sh`, `census.sh`,
  `census-table.py`, `vm-rec.sh`, `rec-twice.sh`, `chain-{a..f}.sh`,
  `dev-all.sh`, `dev-iso/`, `play-all.sh`, `play/`, `disk/`, `probes/`.

### What was measured, and where it is

| measurement | file |
|---|---|
| the prediction, before the first change | `notes/px65/prediction.txt` |
| the three release archives, twice each | `notes/px65/kasumi-archives.out` |
| the kernels' cost against `f0617320` (and `68807993`) | `notes/px65/kasumi-cost-native-f0617320.out`, `kasumi-cost-release-f0617320.out`, `kasumi-cost-68807993.out`, `cost-symbols.txt` |
| the dev compiler twice | `notes/px65/kasumi-mkwolf-twice.out`, `user/wolf.sums` |
| boreutils' 61 digests | `notes/px65/boreutils-sums.txt` |
| the census | `notes/px65/census/`, `docs/CENSUS.md` |
| the main thread's stack and the fault ignore, PAX and Linux | `notes/px65/probes/` |
| the suites on kasumi | `notes/px65/kasumi-chain-{a,b,c,d}.out` |
| px57's recordings again, twice | `notes/px65/kasumi-recordings-twice.out` |
| the dev compiler's sessions on PAX | `notes/px65/wolf-pax-root.tty`, `wolf-pax-user.tty` |
| the plants, predicted and run | `notes/px65/plants.txt`, `ci-40042007705-plant-tool.txt`, `ci-40042009610-plant-enosys.txt` |
| the dev ISO | `notes/px65/kasumi-dev-{verify,build,assemble,boot}.out`, `kasumi-dev.serial.log` |
| the playground, ISO and disk | `notes/px65/play-out/` (`digests.out` both hosts) |

### Measured, inferred, not verified

- Measured: everything in the tables above, on kasumi or in CI.
- Inferred: that the 80 bytes are the same function in the 31 kernels
  whose symbols were not diffed (their `.text` moved by the same 80 and
  nothing else, and they link the same archive).
- Not verified: the release tier for 31 kernels; the dev ISO and the
  playground under UEFI on nomad-1's own QEMU (the disk's UEFI boot ran
  on kasumi's QEMU 11.1.1 with the Mac's code file; px66 measured the
  Mac's line).

## 13. Done-when

- [x] Every pin moved, one commit each, each with its digest (§4, §6).
- [x] Every kernel's `.text` delta recorded: +80, all 33 native, 2 release (§6).
- [x] px57's recordings redone and what moved named (§6).
- [x] mpx5-pelt, mpx5-lope, mpx5-aspen, mpx4-lobo, mpx5-scent green (kasumi and CI).
- [x] boreutils at `575dc7b`, its 14 new utilities in `/bin`; census first; a typed session per group, root and `pax`, byte-identical to the container; none blocked (§6).
- [x] The dev ISO, the playground ISO and the playground disk rebuilt, hashed twice on kasumi and on nomad-1, the previous kept as `.px64` / `.px66`, `pax-home.img` never written (§7, §8).
- [x] CENSUS, SOURCES, README; two plants red as predicted (§9).
- [ ] `tier pr` green at the final head; lane-audit's last line (the PR).
