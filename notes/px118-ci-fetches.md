# px118 — CI's fetches from Ubuntu's archive, from CI's cache

This note shares its lane number with `notes/px118-boot-diagnosis.md`, an earlier lane's; the two are unrelated.

## Why

On 2026-11-11, from about 11:40Z until at least 17:10Z, GitHub's hosted runners could not resolve or reach
`azure.archive.ubuntu.com`, `archive.ubuntu.com` or `launchpad.net`, and every pax run went red for hours on things
that had nothing to do with the change under test. The same kind of failure happened on 2026-11-06, when apt hung on
the archive until a job hit its time limit. What the logs show:

- **apt.** Every job's first step ran `apt-get update` and `apt-get install`. With the archive unresolvable, the
  update still exits 0 (it warns, and keeps the runner image's own indexes), and the install then asks the mirror
  list for each package in turn, each request waiting 20 s for the resolver. mpx3-shell's apt step in run 43025025659
  (attempt 2) took 15:48:40 to 16:07:25, nineteen minutes, and ended in exit 100. 73 of the 77 jobs install this way.
- **beep's source package.** `tools/mkbeep` fetched its two files from Launchpad only. In run 43013370273 Launchpad
  answered 503 four times; mpx3-speaker's K0 failed, and every beep row after it.
- **The disk tools.** `tools/disktools` fetched its seven pinned .debs from the archive's pool, then Launchpad. In run
  43013370273 (mpx5-pelt) and in the first attempt of 43025025659 (mpx4-lobo, mpx5-users, mpx5-jobs) both answered
  `Could not resolve host`: `disktools: cannot fetch dosfstools_4.2-1.1build1_amd64.deb`, exit 2.
- **mpx6-nvme V11** (run 43025025659, attempt 1, at 13:57Z): `tools/mkdisk --gpt --root` failed on all four legs. The
  row prints mkdisk's last two lines, and those are mkdisk's buffered progress, written at its exit after the
  error a child printed (the buffering pax#303 names), so the log does not hold the error itself. mkdisk formats the
  EFI partition with the pinned dosfstools through `tools/disktools`, and the same run's other disktools fetches failed
  as above: almost certainly the same fetch, not shown by this log.

## Every network fetch pax's CI makes

| What | From | Jobs | By digest | Before px118 | Now |
|---|---|---|---|---|---|
| Ubuntu packages (20 distinct lists: QEMU, OVMF, xorriso, clang, lld, gcc, strace, dnsmasq, openssh, e2fsprogs, mtools, fdisk, gdisk, dosfstools, musl-tools, zstd, cpio, kmod, curl, make, git, openssl, iproute2) | the archive, through the runner's mirror list | 73 of 77 (all but plan, census, macos-run, tier) | apt's own, against the archive's signed indexes | `apt-get update` and `install` every run, unbounded | `.github/actions/apt`: a snapshot from the cache, no network; the archive only when cold, bounded |
| beep's source package, 2 files (`user/beep.pin`) | Launchpad | mpx3-speaker | yes | Launchpad only, every run | the pinned store (`tools/fetch-pinned`), cached; sources: the archive's pool, Launchpad, Debian's pool |
| The disk tools' 7 .debs (`user/disktools.pin`: dosfstools, mtools, fdisk, libfdisk1, libreadline8t64, gdisk, libpopt0) | the archive's pool, then Launchpad | the 25 suites that reach `tools/disktools` (directly or through `tools/mkdisk`) | yes | fetched in every job that used them | the pinned store, cached |
| busybox-static's .deb (`user/busybox.pin`) | the archive's pool | mpx3-console (the USB stick), mpx5-accounts, mpx5-jobs, mpx5-pelt, mpx6-ext2, mpx6-nvme | yes | fetched in every job that used it | the pinned store, cached; Launchpad added as a second source |
| The USB differential's Linux kernel and modules, 2 .debs | the archive's pool | mpx3-console, full and all tiers | yes, by apt's record | fetched every run | cached under a key of the two records; the kernel is still the one the archive's indexes name |
| wolf's release archive (`kernel/wolf.pin`), lupin's | GitHub releases | every suite job | yes | every run | unchanged: GitHub |
| Limine's release archive (`boot/limine.pin`) | GitHub releases | every booting job | yes | cached (`limine-*`) | unchanged |
| Other toolchains' wolf archives, std and component trees (the `tools/mk*` builders, `tools/fetch-retry`), the games' source archives | GitHub releases, git, codeload | most user-mode suites | yes (digest or commit) | every run | unchanged: GitHub |
| lope's checkout | GitHub, another of the org's repositories, with a token | the install suites | by commit | every run | unchanged: GitHub |
| Container images: Ubuntu 24.04 (`tools/e2fs`'s), Python (the tree suites') | Docker Hub | the disk, root-disk and tree suites | yes | `docker pull` every run | unchanged: Docker Hub |
| The CA bundle (`user/roots.pin`, `tools/mkroots`) | curl.se | mpx4-console-push, the distribution tests | yes | every run | unchanged |
| QEMU for macOS | Homebrew | macos-run | no | every run | unchanged |
| The actions themselves (checkout, cache, upload and download of artifacts) | GitHub | every job | by tag | | unchanged |

Nothing in a test reaches the network at test time: mpx4-console-push's live way never runs in CI.

## The change

**Packages: `tools/ci-apt` and `.github/actions/apt`.** Every job's packages come through one composite action; no
job runs an apt-get install of its own (`tests/ci-plan` P4 holds it). The action keys a snapshot on the sorted package
list and the runner image (`pax-apt-1-<list>-<ImageOS>-<ImageVersion>`, the image's name and version GitHub sets on
its hosted runners), restores it with `actions/cache`, and `tools/ci-apt install` takes the first path that works:

- **warm**: an exact hit whose MANIFEST names these packages and every file's sha256, each read again and equal, is
  installed from its files with `--no-download`: no network and no `apt-get update`.
- **live**: `apt-get update` within 150 s (a failure is a warning; the image's indexes stand), the packages downloaded
  with `--download-only` into a fresh directory within 300 s (each request tried twice more, 30 s timeouts), then
  installed from those files with `--no-download`. The install is never cut short, and its failure is the job's.
  The downloaded files and their MANIFEST become the snapshot, saved at once with `actions/cache/save`, whatever the
  job does after.
- **stale**: only when the download failed and the cache gave an earlier image's snapshot of the same packages (the
  key's prefix): installed from its files with a warning naming it, never saved.

Whichever path ran, every package named must be installed (dpkg's status `ii`) or the job fails, and the versions are
printed. A cold job in an outage now fails within seven and a half minutes, with an error naming the key and the
packages, where it took nineteen minutes, or the job's whole limit.

**Pinned files: `tools/fetch-pinned`.** beep's source package, busybox-static's .deb and the disk tools' .debs come
through one store, `$PAX_CACHE/pinned/SHA256/NAME`, and `tools/mkbeep`, `tools/fetch-busybox` and
`tools/disktools` take them only from it (`tests/fetch-pinned-selftest` F9). A stored file is used only after its
sha256 is read again and equals the pin's, on every use. The store writes a file only after its digest matched, so a
stored copy that differs was altered after: it is refused (exit 4), never fetched over or repaired. A file not in the
store comes from the pin's sources in order (each curl bounded: 15 s to connect, 60 s a transfer, two more tries
within 90 s); bytes whose digest is not the pin's are refused at once, whatever the other sources hold. The action
restores the store under a key of every pinned file's name and digest (not their sources), warms it
(`tools/fetch-pinned --all`) and saves it only when every file verified. A file the store cannot give is a warning
in the action and the failure of the tool that asks for it, which names the file and each source and how it failed.

**The USB kernel.** mpx3-console's full and all tiers still run `apt-get update` (bounded, 150 s) so the kernel is
the one the archive's indexes name, as before. `tools/fetch-usb-linux --key` names the two packages' records (no
download), the cache restores them under that key, and the tool reads each cached .deb's size and SHA256 again
against apt's record, refusing a copy that differs.

## What a warm run still needs, and what is not cached

Once the cache holds the snapshot for a job's packages on its runner image, the pinned store and (for mpx3-console)
the current kernel, a run needs nothing from Ubuntu's archive or Launchpad. It still needs GitHub (the checkout, the
actions, the release archives and git trees), Docker Hub (the two images), curl.se (the CA bundle, two suites) and,
for macos-run, Homebrew. These were not the outage and are left as they are; each is fetched by digest but the
Homebrew formula.

- **The first run on a new runner image** has no exact snapshot. GitHub rolls a new image out about weekly; the first
  run on it needs the archive, or takes the earlier image's snapshot of the same packages, with a warning, when the
  archive does not answer.
- **A new package list** (a job asks for another package) has no snapshot at all until a run with the archive saves
  one.
- **A new pin** (a changed digest) must be fetched once; the store's older files still come from the cache.
- **The USB kernel** is the archive's newest by design, so the first run after a new kernel needs the archive. When
  the archive does not answer, the image's own indexes name the kernel, and the cache holds it when an earlier run on
  the image took the same one.
- **The cache's scope.** A pull request's run restores what trunk's runs saved; what it saves is its own. A trunk
  push or the nightly warms trunk's scope for everyone.
- **Not cached at all**: the GitHub-hosted fetches (wolf's archive is checked by digest and never cached by design,
  px05), the Docker Hub pulls, the CA bundle and Homebrew's QEMU.

## Decisions

- **Warm runs do not run `apt-get update`.** A job's package versions are those of the first run on its runner
  image, not the archive's newest at the run's hour; a security update to QEMU reaches CI with the next image. Each
  job prints the versions it installed.
- **The stale snapshot.** When the archive does not answer and the cache holds an earlier image's snapshot of the
  same packages, the job installs it and goes on with a warning, rather than failing. apt refuses a downgrade, so a
  snapshot that no longer fits the image fails the job.
- **A refused file is never repaired.** A stored or cached file whose digest is not the pin's fails the job that needs
  it until the cache entry is deleted (`gh cache delete`), by design, since only an alteration can make one.
- **`actions/cache` by its tag**, `@v4`, as every other step of the workflow names it: GitHub's own action, not a
  third party's.

## Evidence

- `tests/fetch-pinned-selftest` (F1 to F9) and `tests/ci-apt-selftest` (A1 to A9) run in the plan job of every run;
  `tests/usb-linux-fetch` gained a row for a cached package refused when altered and one for the key.
- `notes/px118/apt-container.sh` runs `tools/ci-apt` against a real apt and the archive, each take in a throwaway
  Ubuntu 24.04 container with its package indexes, as a runner image carries them. On a Linux build host: C1, cold
  with the network, installed QEMU, OVMF, xorriso and gdb (76 .debs in a bare image) and kept them as the snapshot;
  C2 installed them again with no network at all, the same versions, in seconds; C3, cold with no network, failed
  with the error naming the key; C4 installed an earlier image's snapshot with the warning; C5, apt's proxy an
  address nothing answers, was cut at its bounds (20 s and 30 s there) and failed with the error.
- `tools/mkbeep` built beep with no network from a warm store, and failed with no network from an empty one, naming
  each source; `tools/fetch-busybox` took its binary with no network from a warm store.
- The plants, each one commit on this lane's head, pushed to `px118-plant-*` branches and never merged: a wrong
  digest in `user/beep.pin`; beep's sources made unreachable (an unroutable address), run warm and cold; apt's
  network made unreachable in `tools/ci-apt` (an unroutable proxy), run warm and cold. The pull request lists their
  runs.

## Two flaky rows seen this week (recorded, not fixed)

- **mpx2-interrupts I5, native kmain_timer, BIOS** (run 42983922118, attempt 1, job 130402419942). The cause is in
  the log. Under TCG the kernel's LAPIC calibration found its first two windows apart (61987594 and 62504161 Hz),
  printed `timer: LAPIC calibration: windows 1 and 2 disagree` and `windows 2 and 3 of 6 agree`, calibrated by the
  HPET and went on: 20 ticks on vector 32, 0 spurious, halt. The row asserts that the log's last four lines are the
  apic line, the calibrated line, the ticks and the halt, so the calibration's own retry lines, which sit between the
  first two, fail it. The kernel did what it should; the row's tail match does not allow the retry's lines.
- **mpx5-trace K0** (pax#335), on the Linux reference leg, in a throwaway container on the runner's own kernel, before
  PAX is involved. Two forms: `notify-syscall` read `status=0` where the reference has `status=5` (uid 0 at
  `d56fdd98`, uid 1000 in run 42969820900 at `1c827734`), and on 2026-11-06 (run 42290139713) `regs2` poked a
  non-canonical `fs_base` (0x1000000000000) and Linux took it (`=0`, read back) where the reference has `-5` and 0.
  The failing and passing runs name the same runner image (20261101.360.1), so the image is not what varies; the
  host under the runner may be. The cause is not in the logs. For `regs2` one reading fits: 0x1000000000000 is
  canonical on a CPU and kernel using 57-bit linear addresses (five-level paging), so a host with them would take the
  poke; nothing in the log shows the host's paging.
