# tl38 — remote fetches that do not red a run

Infrastructure reds this month, none of them a change of PAX's:

- **pax#210:** two plant runs (40253361683, 40253365140) went red on mpx3-speaker K0 when launchpad.net answered
  `503` to `tools/mkbeep`. Its `curl --retry 3` waited 1, 2 and 4 s (curl's own backoff) and gave up.
- **2026-11-06, pax#307's runs:** the apt step hung twice with nothing printed. In run 42231461455 (attempt 1)
  mpx4-tcp's `apt-get update` stopped after `Get:5 https://archive.ubuntu.com/ubuntu noble-security InRelease` at
  15:05:55 and was cancelled by the job's limit at 17:35:46; in run 42230956177 (attempt 1) mpx5-users-ahci's did the
  same for 90 minutes. Neither apt call had a timeout.
- **2026-11-09:** GitHub's release origin answered cold fetches with `504`. `tools/fetch-limine` (`curl --retry 3`)
  turned a green record red at mpx6-install-full-native, and in run 42566364403 `tools/mkpelt`'s wolf fetch took four
  `504`s, then sat about 20 minutes until the job's 75-minute limit cut it.

## Prediction

Written 2026-11-10 at 21:14Z, before any change, on `2dd649f0` (pax#340's head).

### What changes

- **`tools/net-retry`**, new, POSIX sh (the census container runs it under `/bin/sh`), beside `tools/fetch-retry`
  (git revisions, px85), which stays as it is. Three forms:
  - `url URL OUT [SHA256]`: curl with `--connect-timeout 20`, `--max-time 600` and a floor of 1 KiB/s over 60 s,
    into `OUT.part`, renamed to OUT only on success (and, with SHA256, only when the digest holds: a mismatch is
    refused at once, never fetched again). Tried again on name, connection, timeout, reset and TLS failures and on
    HTTP 408, 425, 429 and 5xx; a 404 or any other status stops at once (`not retried`). Five tries, 5, 15, 45 and
    120 s apart.
  - `apt PKG...`: `apt-get update`, then the packages with `--download-only`, each with `Acquire::Retries=5` and a
    30 s connect and idle timeout per file, each try under a total limit (300 s for the lists, 900 s for the
    packages), tried 4 times 30, 90 and 270 s apart; then the install, with no network.
  - `run CMD...`: any command (`docker pull`, `brew install`), every failure tried again, five tries as `url`, each
    try under a 900 s limit where `timeout(1)` exists (the macOS runner has none).
  - Lines: `net-retry: WHAT: try N of T failed (CLASS); again in S s`; at the end
    `FAIL fetch of WHAT failed after T tries (last: CLASS)` (exit 3), or `FAIL fetch of WHAT failed (CLASS), not
    retried` (exit 4), or a refused digest (exit 5).
- **`tests/net-retry-selftest`**, new, committed before the helper: N1–N9 against a loopback server, a fake
  `apt-get` and `sudo`, the pauses at 0 s; N10 holds that every fetch goes through the helper: no `curl` fetch left
  in `tools/` or the census's `stage.sh`, and no `apt-get`, `docker pull` or `brew install` in the workflow outside
  it. Red at the rows tip (N0: the helper missing; then N10 alone, 211 sites), green once every site is moved. The
  `plan` job runs it beside `tests/fetch-retry-selftest`.
- **The 25 `curl` calls in 24 files** move to `tools/net-retry url`, each writing the file it wrote before, so every digest
  check after it stays as it is: `tools/fetch-wolf`, `fetch-lupin`, `fetch-limine`, `fetch-busybox`, `disktools`
  (each of its two sources), `mkbeep`, `mkgames`, `mkroots`, `mklupin`, the wolf (and lupin) archive of `mkaspen`,
  `mkauth`, `mkboreutils`, `mkburrow`, `mkclef`, `mkden`, `mkedwolf`, `mklobo`, `mklope`, `mkpelt`, `mkscent`,
  `mksigwolf`, `mktrash`, `mkyew`, and the census's `stage.sh` (the census mounts the helper beside
  `fetch-retry`).
- **The workflow:** the 71 apt steps' `sudo apt-get update -q` and `sudo apt-get install -y -q
  --no-install-recommends PKGS` become `tools/net-retry apt PKGS`, the same packages; the 43 `docker pull`s and the
  macOS job's `brew install qemu` run through `tools/net-retry run`.
- **`tools/ci-tiers.map`:** `tools/net-retry` FULL, as `tools/fetch-retry` is; `tests/net-retry-selftest` ALL, as
  `tests/fetch-retry-selftest` is.
- **Unchanged:** every version, URL and digest; `tools/fetch-retry`; `tools/fetch-usb-linux` (its own bounded
  curl, inside its step's 660 s limit); the census image (built on a host, not in CI).

### Expected

- `tests/net-retry-selftest`: N1–N10 green; `tests/fetch-retry-selftest` and `tests/ci-plan` green (the new paths
  mapped).
- A run of the workflow (when the coordinator dispatches it): every job's apt step prints apt's own lines as before
  and no retry line on a calm day; a slow or dead mirror shows the retry lines and, past the tries, the FAIL line
  as the step's last words, instead of a job cancelled at its limit with nothing printed.
- Nothing downloaded changes, so every digest, every image and every suite's answers are as at `2dd649f0`.

### Risks

1. **The draft PR's own run.** `tools/fetch-wolf` and `tools/fetch-limine` are FULL in `tools/ci-tiers.map`, and
   `.github/*` is ALL, so opening a pull request for this branch starts a `tier all` run (every suite, every leg).
2. Worst cases are long but bounded: the apt step at most about 75 minutes (lists 4 × 300 s and packages 4 × 900 s
   plus the pauses twice), where a hang before was the job's whole limit. A total outage fails far sooner.
3. `sudo apt-get` under `timeout(1)`: the signal reaches `sudo`, which passes it on to apt.

### Choices, recommended and implemented

1. **One helper or three.** (A) One `tools/net-retry` with three forms, beside `tools/fetch-retry`; (B) a helper per
   kind. Recommended and implemented: A, one place for the policy and one selftest.
2. **`--error-on=any` for apt on the runner.** (A) Leave it out; (B) use it. Recommended and implemented: A. The
   runner's own sources are not PAX's, and a warning from one of them would become every job's error.
   `apt-get update` already fails on a list it could not fetch (the mid-sync case), and that failure is retried.
3. **`tools/fetch-retry`'s three attempts, 10 and 30 s apart.** (A) Leave them; (B) give git the same five tries.
   Recommended and implemented: A in this pass (px85's selftest pins its waits); B is a small follow-on.
4. **A mirror for `tools/mkbeep`'s source (pax#210).** The digest already pins it. (A) Retries only; (B) a second
   source with the same digest, as `tools/disktools` has. Recommended and implemented: A; B changes where a file comes
   from, which this pass does not.

## Inventory

Every network fetch in PAX's CI and container files, before this pass and after.

| what | where | pinned by | retried before | after |
|---|---|---|---|---|
| QEMU, OVMF, xorriso, clang, lld and the rest from the runner's apt mirrors | `.github/workflows/ci.yml`, 71 apt steps | not pinned (the runner's Ubuntu; apt checks signatures) | apt's own per file; no outer retry; no timeout (pax#307's hangs) | `tools/net-retry apt`: lists and packages each 4 tries, a limit per try, 30 s timeouts |
| QEMU from Homebrew | `macos-run`'s `brew install qemu` | Homebrew's own checksums | no | `tools/net-retry run` (no total limit on macOS) |
| `ubuntu@sha256:534baea6…` and `python@sha256:a6e34c59…` | 43 `docker pull`s | image digest | no | `tools/net-retry run` |
| wolf, lupin and Limine release archives | `tools/fetch-wolf`, `fetch-lupin`, `fetch-limine` | sha256 | `curl --retry 3` (1, 2, 4 s; no connect or total limit) | `tools/net-retry url` |
| wolf (and lupin) release archives for each program | `tools/mk{aspen,auth,boreutils,burrow,clef,den,edwolf,lobo,lope,lupin,pelt,scent,sigwolf,trash,yew}` | sha256 (the program's own pin), cached by digest | `curl --retry 3` | `tools/net-retry url` |
| the games' source archives (codeload) | `tools/mkgames` | sha256 | `curl --retry 3` | `tools/net-retry url` |
| the CA roots | `tools/mkroots` | sha256, read twice | `curl --retry 3` | `tools/net-retry url` |
| beep's source (launchpad.net) | `tools/mkbeep` | sha256 | `curl --retry 3` (pax#210) | `tools/net-retry url` |
| busybox-static's .deb | `tools/fetch-busybox` | sha256 | no | `tools/net-retry url` |
| the disk tools' .debs (archive.ubuntu.com, then launchpad.net) | `tools/disktools` | sha256 | no | `tools/net-retry url` for each source |
| wolf and lobo archives for the census | `tools/census/inside/stage.sh` | sha256 | `curl --retry 3 --retry-delay 5` | `tools/net-retry url` (mounted by `tools/census/census`) |
| Linux's two .debs for the USB legs | `tools/fetch-usb-linux` | sha256 and size from apt's signed metadata | curl `--retry 1`, `--connect-timeout 15`, `--max-time 240`, inside the step's 660 s limit | unchanged |
| every source tree at its commit (17 sites) | `tools/fetch-retry`, called by the `mk*` tools, `fetch-wolf` and the census | the commit id, compared | 3 attempts, 10 and 30 s apart, a speed floor (px85) | unchanged |
| the census image (Arch `base-devel` by digest, then `pacman -Syu`) | `tools/census/Containerfile`, built on a host | base by digest; packages float, recorded | no | unchanged: not a CI fetch |
| `actions/checkout`, `cache`, `upload-artifact`, `download-artifact` | the workflow | tag | the actions' own | unchanged |

## Evidence

Local, on an Apple silicon laptop (macOS); the hosted run and the records wait for the coordinator.

- **Red at the rows tip** `1e8c7c7d` (the selftest, no helper): `FAIL N0: tools/net-retry is missing`, exit 1.
- **The helper alone** `e1d826e2`: N1–N9 PASS, and N10 red by name,
  `FAIL N10: 211 fetches outside tools/net-retry, the first: tools/census/inside/stage.sh:13: …` (25 `curl` calls,
  71 × 2 apt lines, 43 `docker pull`s, one `brew install`).
- **Green at the head** `2c97aa60`: N1–N10 PASS, with `tests/fetch-retry-selftest`, `tests/ci-plan` (65 s),
  `tests/census` (C1–C6, R0–R3) and the `plan` job's other selftests, every one exit 0.
- **One live fetch through the helper:** `tools/mkroots` fetched `cacert-2026-10-20.pem` (sha256 `796f1389…`,
  read twice) and wrote `ca-roots.der` `7a713f23…`, 118 certificates, as before.

Scored against the prediction: the selftest's red and green, `fetch-retry-selftest` and `ci-plan` held as predicted.
The hosted expectations (apt's lines, a FAIL as a failed step's last words) are open until a run.

**Risk 1 seen before it cost anything:** the branch is pushed, but no pull request is opened from it yet. Opening one
starts a `tier all` run (every suite on every leg), since `tools/fetch-wolf`, `tools/fetch-limine` and
`tools/net-retry` are FULL and `.github/*` is ALL.

## Done-when

- [x] The prediction, committed first (`2bf02a35`)
- [x] `tests/net-retry-selftest` red at the rows tip, green at the head
- [x] `tests/fetch-retry-selftest` and `tests/ci-plan` green
- [ ] A draft PR, its run when the coordinator says
