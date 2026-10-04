# px04 — the census

Contract: `sprints/pax/04-census/px04-the-census.md` in wolffe-lang/wolf
(planning trunk `b25d8a8`). Branch `px04` off pax `1b8945d`; PR pax#4.
The five sections are committed whole in `2e9f064` (an empty commit,
before the first trace); this note carries §2's drift, §3 against what
was measured, and §4. The deliverable is `docs/CENSUS.md` and
`tools/census/`.

## 1. Forbidden

As committed in `2e9f064`. Kept: no Linux source read beyond the one
allowed file (`arch/x86/entry/syscalls/syscall_64.tbl`), no glibc
source; nothing installed on any host; no sudo; nothing built on nomad-1
(it edited, committed, pushed and ran `tests/census`, which runs python
on committed text); every trace, build and probe ran in rootless podman
containers on kasumi under `~/lanes/px04/`, killable jobs under `setsid`,
killed by pid or by container id in the lane's own store. Disclosed:
twice a wait loop of mine on kasumi matched its own command line and
never ended; I killed it by pid, and the first time that pid list also
held the `tailscaled be-child` processes of my own ssh sessions (their
`--cmd` carried the same text). No other lane's process was in either
list.

## 2. Inputs, verified (drift)

As stated in `2e9f064` (boreutils pins 0.2.20, not 0.2.22; no boreutils
Linux binaries; no static flag in `wolf build`; lobo traced at its 0.1.1
release; Arch rolled since the base image). Found while measuring:

1. **kasumi's shared podman store is broken**: every container from the
   shared `~/.local/share/containers/storage` fails with `input/output
   error` creating its overlay mount (2026-10-04, podman 6.1.3, upgraded
   2026-10-02 while kernel 7.2.3 runs and 7.2.8 waits for the reboot).
   The census used a lane-private store (`CENSUS_PODMAN_ROOT`), which
   works. Not repaired: other lanes' images live there.
2. wolf-std `14f0ab2` (boreutils' pin) builds all 27 utilities under
   wolf 0.2.22 with `--deny-warnings`, so B151's re-derivation kept it.
3. The static link is `tools/build`'s own link line (read from
   `--verbose`: `cc … libwolf_rt.a -lpthread -ldl -lm -Wl,--gc-sections
   -fuse-ld=lld`) with `-static` added by a `cc` first on `PATH`: no
   gap to file; wolf already allows it.
4. The wolf release tier needs `clang` and `lld` on `PATH`; the image
   carries them.

## 3. Prediction against measurement

The full table is in `docs/CENSUS.md` § "Prediction against
measurement". Of seven claims, three held (the union in 120..180 at
127; static boreutils in 15..30 at 26; and every per-workload count was
the right order) and two were wrong: **pacman is not the largest
workload** (88; sshd is 89), and **8 of my top 20 by calls are absent**
(the falsifier was 6): start-up calls made 5,284 times outrank
`futex`, `ioctl` and `fcntl`.

## 4. Evidence index

- Prediction: `2e9f064`.
- Image: base `archlinux:base-devel@sha256:8185e444…`; built
  `localhost/px04-census:1`, id `0a2c2cde…`
  (`tools/census/out/image-id.txt`), packages in
  `tools/census/out/image-pacman-Q.txt`.
- Inputs by digest: wolf 0.2.22 `df0f2fea…`, lobo 0.1.1 `6e21e151…`;
  boreutils `010f3144a9ba…`, wolf-std `14f0ab2c6a64…`, the reel at lobo
  `f79418d1181d…`.
- Per workload: the command lines are `tools/census/out/<w>/o/commands.txt`
  (the same in `c/`), the run record `…/o/meta.txt`, the tally
  `…/tally.json`, the CSV `tools/census/out/<w>.csv`; raw trace manifest
  and archive digests:

| workload | raw manifest sha256 | archive sha256 (`out/raw-archives.sha256`) |
|---|---|---|
| boreutils-static | `5148e7efef11…` | `5c3f21a26393…` |
| boreutils-dynamic | `912c5e292e81…` | `a690774f9ccb…` |
| lobo | `49cd1b1136af…` | `a8e3af304dff…` |
| dash | `9c07d897888c…` | `bfb0510c60e2…` |
| bash | `780e3ba4e7ac…` | `1e3c03a2aba3…` |
| pacman | `a3f6ec93127f…` | `c0ba476c7314…` |
| cc | `1321b1e6af81…` | `a66d7021a15a…` |
| sshd | `aaca42868313…` | `3636121bb256…` |
| curl | `a8362d676cfe…` | `15649ab060d1…` |

  The injection logs are one archive, `17e0d94a1053…`. The archives
  (8.8 MB) are kept on kasumi in `~/lanes/px04/evidence/` for the
  orchestrator to keep or delete; everything else under `~/lanes/px04`
  was pruned.
- Injection verdicts: `tools/census/out/inject-static.csv`,
  `inject-dynamic.csv`, `inject-static-sets.csv`. The static single-call
  runs were made with the wrapper of `c093ba9` and its 60 s watchdog
  (the `write` run hung on `tee` until the fork watchdog of `192c3f8`,
  which also made `write`, `clock_gettime` and both set runs); the
  dynamic runs all used `192c3f8`'s. The verdict logic is the same in
  both; only a hang's handling differs.
- auxv and vDSO: `tools/census/out/auxv.csv`, `auxv-reads.csv`,
  `vdso.csv`.
- The census tools' own test, seen red: CI run **37173258264** (census
  job 111350430113) on the planted `fb9119b` — C1 FAIL (`execve: want 1
  calls/0 errors, got None`), C2 and C3 PASS, 0 SKIP lines; reverted in
  `0231a40`.
