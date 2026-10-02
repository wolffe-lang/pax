# px00 — the harness

Lane note and contract. **Class:** pax, Opus. **Track:** `sprints/pax/index.md`
in the planning repo (`wolffe-lang/wolf`, trunk `4281d470`; the track and this
lane's brief landed in `c6ba91a`). **Brief:**
`sprints/pax/00-scaffolding/px00-the-harness.md`. One deliverable: the pax
repository made workable before any wolf kernel code exists — the layout, the
boot protocol chosen and argued, a QEMU harness, an assembly proof seen red
then green, CI, and the consulted-sources log.

§1, §2 and §3 were written 2026-10-02, before any file outside this note was
written and before any boot.

## 1. Forbidden, absolutely

- **The clean-room rule.** No Linux kernel source is read, copied or
  translated (`.c`, `.S`, `.h` outside the uapi trees, Kconfig, Makefiles).
  `wolf/refs/repos/linux` is not opened at all by this lane: it is being
  narrowed to the allowed paths, and nothing here needs it. Every source
  consulted is named in `docs/SOURCES.md`.
- No wolf kernel code (that is px01, after KWC). The only non-wolf code is the
  assembly proof under `boot/stub/`, and it says so in its header.
- Nothing is made public: the repo stays private; no release, no tag, no
  public artifact.
- No package installed on any host: the orchestrator installs on the pool,
  lanes never do. A missing tool on kasumi is reported and that item stops.
- No `rm` outside `~/lanes/px00/` on kasumi, `/private/tmp/px00` and this
  lane's scratch directory; kill only this lane's own pids, never a pattern or
  a process group; `setsid` on kasumi, `nohup … & disown` on the Mac, never
  `ssh -f`.
- No `~/.claude`; no `git add -A`; no merge; no commit or PR trailers of any
  kind.
- No "seen red" or "seen green" without a run id, log path or digest in the
  same paragraph. `gh run watch` only with `--interval 60`; poll with
  `gh run view`.
- Third-party boot code is fetched BY DIGEST, never vendored unpinned and never
  built from an unpinned source.

## 2. Inputs, re-derived against origin (2026-10-02)

| the brief says | origin / the host says | verdict |
|---|---|---|
| repo `wolffe-lang/pax`, private, trunk has a scaffold commit | `gh repo view`: `PRIVATE`, default branch `trunk`; trunk is `3e6ec98` "scaffold: README, CLAUDE.md with the clean-room rule, GPL-3.0 and the training-data permission"; four files (README.md, CLAUDE.md, LICENSE, LICENSE-TRAINING-DATA); Actions enabled, all actions allowed | holds |
| worktree `/private/tmp/px00` on branch `px00` | **did not exist**; created here with `git worktree add -b px00 /private/tmp/px00 origin/trunk` at `3e6ec98` | drift, repaired |
| QEMU work runs on kasumi under `~/lanes/px00/` | kasumi (CachyOS, kernel 7.2.3): **`qemu-system-x86_64` MISSING**, `xorriso` MISSING, no OVMF/edk2 firmware under `/usr/share`; present: `gdb`, `as`, `ld`, `gcc`, `clang`, `ld.lld`, `make`, `mtools`, `curl`, `sha256sum`, `timeout`, `setsid` | **drift: the kasumi item stops** (reported; the orchestrator installs `qemu-full` or `qemu-system-x86` + `xorriso` + `edk2-ovmf`) |
| CI on GitHub Actions, ubuntu runners take qemu from apt | unmeasured until §4's first run | measured in §4 |
| macOS: the harness states whether it runs there | this Mac: `qemu-system-x86_64` present (Homebrew, "QEMU emulator version 11.1.1"), with `edk2-x86_64-code.fd` under `/opt/homebrew/share/qemu`; no x86_64 ELF binutils, no `xorriso` | run is measurable here; build is not |
| **(orchestrator, mid-lane, 2026-10-02)** kasumi cannot get QEMU without a full system upgrade; use hasu, through a nix-shell; the harness takes its QEMU from the environment | hasu (NixOS, kernel 7.2.3, 20 cores, KVM usable): `nix-shell -p qemu xorriso` gives QEMU 11.1.0 and xorriso 1.5.8.pl02; nixpkgs `OVMF.fd` is `OVMF-202608-fd` (`FV/OVMF_CODE.fd`, `OVMF_VARS.fd`, combined `OVMF.fd`); system `as`, `ld`, `gcc`, `make`, `curl`, `gdb` present. Work under `~/lanes/px00/` only | holds; `PAX_QEMU` added (`58e2df0`) |
| boot protocol: Limine, multiboot2 or a direct UEFI stub | Limine latest release `v12.9.1` (2026-09-26), BSD-2-Clause; its release ships `limine-binary.tar.gz`, GitHub digest `sha256:5cdebc51…`, hashed here to the same value. **The protocol text has moved** out of the bootloader repo into `Limine-Bootloader/limine-protocol` (0BSD), trunk `3a0526b700e356f0eac1b71a77697b3fd1c707a3`; its PROTOCOL.md specifies base revisions 0–6, 0–5 deprecated | holds, with the protocol's new home recorded |

## 3. Prediction, committed before any boot

1. **Protocol: Limine, base revision 6**, one hybrid ISO that boots under both
   SeaBIOS (QEMU's default firmware) and OVMF (UEFI). Reason in short: it is
   the only one of the three that enters the kernel already in 64-bit long
   mode, in the higher half, with a memory map, an HHDM and a framebuffer on
   request, so the kernel's own assembly is zero lines beyond what the proof
   itself needs. `docs/BOOT.md` argues it in full.
2. The proof (`boot/stub/pax-stub.S`) writes `PAX` and a firmware line to
   COM1 and exits QEMU through `isa-debug-exit` with value `0x10`, which QEMU
   reports as status **33** (`(0x10 << 1) | 1`). Both legs (BIOS, UEFI) see
   `PAX`, their own firmware name, and 33.
3. Seen red first: a planted wrong string (`PAZ`) makes `tests/proof` fail
   on the serial assertion, in a CI run of its own, before the fix commit.
4. Each boot completes in under 10 s on an ubuntu-latest runner (TCG, no
   KVM assumed); the whole CI job under 5 minutes.
5. On this Mac the harness runs a CI-built ISO and reaches the same `PAX`
   and 33 on both legs; it cannot build one (no ELF binutils, no xorriso),
   and the README says so.
6. On kasumi nothing runs: QEMU is absent (§2). That item is reported, not
   worked around.

## 4. Evidence index

| claim | evidence |
|---|---|
| red first, CI, both legs, for the planted reason only | run **37058843828** at `92bd40c` (stub writes `PAZ`): `proof: FAIL bios: serial assertion (status was 33 …)`, serial `PAZ` / `firmware: bios`; same for uefi; ISO `e488ba79…` |
| red again after the harness fixes, plant still in | run **37059469066** at `a23536c`: both legs status 33, `PAZ`, `FAIL … serial assertion`; ISO `55a8cd6b…` |
| red on macOS (Homebrew QEMU 11.1.1, TCG), the CI ISO | this Mac, `tests/proof --image` on run 37058843828's artifact: both legs status 33, `PAZ`, rc 1 (logs in the lane's scratch `mac-red/`) |
| green, CI, the plant removed | run **37059770404** at `6514290`: `PASS bios … elapsed 0.309s, accel tcg`, `PASS uefi … elapsed 2.957s`; both gdb attaches `rip=0xffffffff80000000`; `macos-run` green |
| green, CI, at the branch head | run **37062609320** at `8775565`: proof job 44 s (20:46:25–20:47:09Z); QEMU 8.2.2 (Ubuntu), xorriso 1.5.6; ISO `ce9c1cb1…`; `PASS bios … 0.307s`, `PASS uefi … 2.443s`, accel tcg; gdb bios and uefi stop at `0xffffffff80000000`; `macos-run`: `build/pax-stub.iso: OK` (the same digest), QEMU 11.1.1, `PASS bios`, `PASS uefi` |
| green on this Mac, the head's CI ISO | `shasum -c` OK on `ce9c1cb1…`; `PASS bios … 1.000s`, `PASS uefi … 2.000s`, accel tcg (scratch `mac-green/`) |
| hasu, red then green at the head | `~/lanes/px00/final.log` at `8775565`: plant in a scratch copy → `FAIL bios`/`FAIL uefi` on `PAZ`, status 33, `RED proof rc=1`; then `GREEN proof rc=0` (`PASS bios … 0.209s`, `PASS uefi … 0.515s`, accel **kvm**), selftest 0, gdb bios 0, gdb uefi 0; ISO `a6369e19…` |
| the image is reproducible on one toolchain | hasu: two builds 2 s apart, one digest (`583885ba…`); `SOURCE_DATE_EPOCH=1` gives another (`a773995c…`); the proof's and gdb's builds at the head, one digest (`a6369e19…`). **Not across toolchains**: CI (binutils/xorriso 1.5.6) `ce9c1cb1…` vs hasu (xorriso 1.5.8) `a6369e19…` at the same commit |
| split OVMF hangs under KVM on hasu | `~/lanes/px00/rep.log`: split `OVMF_CODE.fd`+`OVMF_VARS.fd` under KVM: 1 of 6 boots, 5 timeouts (firmware never reaches BdsDxe); combined `OVMF.fd` under KVM 6 of 6 (0.51–0.62 s); TCG 12 of 12 either way. First met as `run-split.log`'s uefi FAIL (status 124) |
| kasumi | §2: no `qemu-system-x86_64`, `xorriso` or OVMF; not run |

**Predictions (§3), scored.** 1 held (Limine rev 6, one ISO, both firmwares).
2 held (33, `PAX`, firmware line, every host). 3 held (37058843828). 4 held
(slowest boot 2.957 s on CI TCG; proof job 44 s; runner queueing, up to
~17 min for `macos-run`, is not the job). 5 held (CI and this Mac). 6 held,
and the orchestrator moved the pool item to hasu.

**Not predicted.** (a) The first CI artifact was not the ISO the proof
booted: `tests/gdb-attach` rebuilt it in place (run 37059770404's
macOS-booted ISO `60f842ff…` ≠ the proof's `a2c521ad…`). Fixed in
`92bf27a` (its own path), `7b545d2` (reproducible) and `a138c4c` (macOS
checks the digest). (b) The split-OVMF KVM hang on hasu, worked around by
the combined image and written into the README. (c) Firmware consoles write
`ESC c` and `ESC [=3h`, which the first normaliser missed (harmless there,
fixed in `ce54844` with a self-test row).

## 5. Done-when

- `docs/BOOT.md`, `docs/SOURCES.md`, the README's and `CLAUDE.md`'s layout
  sections exist on the branch.
- `tools/qemu-run`, `tools/qemu-gdb`, `tools/expect-serial` exist, each with a
  usage line, and `tools/expect-serial` is proven able to fail (its own
  self-test).
- The proof is seen red (planted `PAZ`, a CI run id) and then green (a CI run
  id) on both firmware legs.
- The kasumi run is either recorded green or reported as blocked on the
  missing QEMU (§2) — this lane does not install it.
- The macOS run is recorded (§3.5) and the harness states its macOS support.
- PR open on pax, unmerged, five sections, commit-hash bullets, a test
  checklist.
