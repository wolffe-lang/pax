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

*(filled as evidence lands)*

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
