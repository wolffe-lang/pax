# px60 — wolf on PAX

Crawl 54, GPT-6-Astra. The dev image is separate from the base image.
The kernel, the base `user/shrc`, and the base toolchain pin are unchanged.

## 1. Forbidden

No kernel or libc source was read. The compiler patch was prototyped in
an isolated wolf-lang worktree, never pushed upstream. The LLVM source
experiment is a tool build, not a source for PAX code. Builds ran on
kasumi in containers; QEMU ran under `taskset -c 0-3`, TCG, with core
dumps disabled. No host package was installed. No issue was filed or
closed, and no branch was merged. The playground scripts were copied
into px60's directory, never edited in the shared playground.

One initial attempt to write a builder containing a variable cleanup
trap was refused by the harness. The lane stopped and reported it. On
resume the new builder omitted automatic deletion entirely; the denied
removal was not retried through another tool. Its fresh build directories
are printed and retained for explicit inspection and cleanup.

## 2. Inputs and recipe

- PAX: cut from `d13d6f96`, rebased onto px59's `e988ce72`.
- wolf: `v0.2.34`, commit `9da7bdcf2aea9adf48df6570bedc58e16e9ef853`.
- Rust: 1.97.1; target `x86_64-unknown-linux-musl`.
- Build image: px57-rust,
  `e93022a6c0d0c12d00af80f639d637cc80332210eb38e170c9058736ebe32181`.
- std: the compiler's STD-PIN,
  `e036bec318ad81ecd5a025612bc2c2adb17527f3`.
- The complete patch and its digest are in `user/wolf-musl.patch` and
  `user/wolf.pin`. It changes only the locale creation sites and the
  ownership of opaque pthread handles, with a cross-thread join test.

The unmodified musl build failed with E0425 at
`wolf_mem/src/ubcheck.rs:14669`: `libc::LC_ALL_MASK` is unavailable;
`wolf_rt/src/signal.rs:1681` used it too. `newlocale(3)` specifies that
with a null base, every category absent from the mask defaults to
POSIX, equivalent to C. The patch uses a zero mask, not a guessed
libc-specific constant.

The next build failed with E0277 at `wolf_rt/src/task/pool.rs:905`:
musl's `pthread_t` is pointer-shaped and therefore not automatically
`Send`. The patch wraps the uniquely owned joinable handle, documents
its transfer safety, and consumes it on join. The existing signal-text
rows and the new cross-thread join test passed on both musl and glibc,
inside a container on CPUs 0–3 (`notes/px60/portability-tests.log`).

`tools/mkwolf` builds the three packages `wolf_driver`, `wolf_rt` and
`wolf_cimport`, with `--release --locked`, `+crt-static`,
`relocation-model=static`, `strip=symbols`, and linker build-id disabled.
It remaps source, generated-target and registry paths. Both executables
must be ET_EXEC, without PT_INTERP or a dynamic section. The runtime
archive is staged beside wolf. Nothing is installed by the helper.

The locale-only intermediate patch in `notes/px60/wolf-musl-locale.patch`
reproduces the second build failure; it is not the active pin patch.

The patched build deliberately has no WOLF_RELEASE stamp:
`wolf 0.2.34+dev.9da7bdc (wolfgang, pin 9da7bdc)`. The source revision
and patch digest together identify the build. Move this pin to a
published archive once wolf-lang ships the fixes and a musl archive.

### Reproducibility was measured, not assumed

The first CI attempt stopped at the byte gate, before either plant.
The worker and runtime already matched; wolf did not. Cranelift's
generated source paths were embedded under the randomized target
folder. Remapping that folder made every code/data section identical
to CI, but private LLVM symbol suffixes still differed in `.symtab`
and `.strtab`, and hence in the build-id. `elf-diff.py` and its log
record that section-by-section comparison. Stripping symbols and
omitting the build-id removes that metadata rather than altering code.
The earlier `e19f25cc…` and `94b56f38…` bytes are superseded.

Canonical bytes, each read twice on kasumi (`user/wolf.sums`):

| file | bytes | SHA256 |
|---|---:|---|
| wolf | 15,831,600 | `fe45d431d017379ef2c5d282ef93cbeffff2534e168bf90bac601ad845d9c676` |
| wolf-cimport-worker | 618,688 | `06a58258f29a08fbaef924af4831befb38f6a61f1d1797030a91ad5dc39debc4` |
| libwolf_rt.a | 44,800,284 | `2d2b14c50011e13ad0b060aa90c83ef4a4ec9d0477c1cd17adc72776d9575e36` |

CI control `39796051044`, job `119883769940`, reproduced all three
canonical files and passed the live sessions. A prior byte-gate failure
is not counted as evidence of a successful plant.

## 3. Prediction and contract corrections

Prediction committed before implementation and measurements:
`9ca73356`, `notes/px60/prediction.txt` (originally `cfd2e8a9` before rebase).

| prediction | measured | score |
|---|---|---|
| packaged static LLVM links; M1 needs no compiler patch | wolf does not link LLVM; it emits IR and invokes clang. Two musl portability fixes were needed | wrong assumptions |
| stripped wolf 80–160 MiB, point estimate 120 MiB | 15,831,600 bytes after canonical stripping | wrong |
| 8–15 syscall names beyond lupin, point estimate 11, none missing on the no-link commands | 18 additional names in this workload, including child pelt; mremap is unserved and falls back | wrong |
| M2 reaches hello with a cc front end, musl and lld | PAX builds and runs hello, loop and signal as uid 1000, byte-identical to Linux after the native link stack is supplied | right on outcome; source lld and decompressed library metadata were needed |

Three corrections accepted by the coordinator:

1. There is no linked LLVM dependency in this compiler. The default
   native backend is Cranelift; `--release` invokes external clang.
2. `wolf run --checked` is still a native build. The checked machine is
   **`wolf conform-run --json --checked`**, used for M1 here.
3. `wolf check` does not exist at 0.2.34. Its exact refusal is retained
   as a negative row; `conform-run --json --phase=typecheck` is the
   positive typecheck row. This phase is not claimed to run the memory
   checker.

## 4. Sessions and census

`tests/mpx5-wolf` stages the dev root, boots PAX, and runs the same
binaries and keys live in a Linux container. Root and `pax` each run:
version; a typed program; typecheck, canonical-format check and checked
execution of hello, loop, signal, task spawn, process spawn, fork, the
clock/environment/tree program, and a real `std.str` import. Dev copies
of px57's programs were formatted; the base copies were not changed.

The first boot already matched its Linux twins byte for byte, including
the then-unformatted fixtures and unknown `check` command. Independent
witnesses correctly did not pass that as completion. After correcting
the fixtures and assertions, the root/user comparisons and every witness
passed on px59's kernel. The final canonical-binary run is recorded in
`notes/px60/sessions-native-bios.log`; normalized PAX and Linux twins
are `pax-root.tty`, `pax-user.tty`, `linux-root.tty`, `linux-user.tty`.
The checker has its own passing-record and deliberately broken-record
tests; mere agreement on failure cannot pass.

Observed answers:

- hello: `hello, wolf`; loop: sum of squares 385.
- signal: signal 2, `Interrupt`, from the same musl binary on both OSes.
- task spawn: joined, answer 42; process spawn: child ran, status 7.
- fork: `os_fork` returns the checked machine's `unsupported` error row;
  the fixture catches and names it. This is not a protocol-level
  `unsupported` verdict, nor a claim that a native fork is unsupported.
- clock: a 20 ms sleep takes at least 20 ms on both sides. No finer
  resolution is claimed; pax#112 remains open and outside this lane.
- environment: HOME is `/` for root and `/home/pax` for pax, then the
  program's `/home/wolf`. Unlike lupin's overlay, wolf observes these
  inherited values. The file/tree rows match too.
- `wolf check`: ``wolf: `check` is not a wolf command.``, status 2.
- native object emission succeeds. The checked-only CI variant names
  the absent cc and clang; the full dev image supplies the native link
  stack and builds/runs programs. The release backend still needs clang.

### Syscall table

The union is 45 names across the M1 commands, including the pelt child
started by `os_spawn`. Raw strace records, per-command sets, exit codes
and output live under `notes/px60/census/`. A repeated census using a
pseudo-terminal instead of redirected files produced the same union.
The final trace records the exact compiler digest in `census/wolf.sha256`.
The table describes the **measured workload**, not every possible flag
or mapping shape of each Linux call. New means absent from px57's
31-call lupin union; different workloads are not a coverage ratio.

| nr | call | new | PAX on this workload |
|---:|---|---|---|
| 0 | read |  | served |
| 1 | write |  | served |
| 2 | open |  | served |
| 3 | close |  | served |
| 4 | stat |  | served |
| 5 | fstat |  | served |
| 7 | poll |  | served |
| 8 | lseek | yes | served |
| 9 | mmap |  | served |
| 10 | mprotect |  | served |
| 11 | munmap |  | served |
| 12 | brk |  | served |
| 13 | rt_sigaction |  | served |
| 14 | rt_sigprocmask |  | served |
| 24 | sched_yield | yes | served |
| 25 | mremap | yes | unserved, fallback works |
| 33 | dup2 | yes | served |
| 45 | recvfrom | yes | served |
| 53 | socketpair | yes | served |
| 56 | clone |  | served |
| 57 | fork | yes | served |
| 59 | execve |  | served |
| 60 | exit |  | served |
| 61 | wait4 | yes | served |
| 72 | fcntl |  | served |
| 79 | getcwd |  | served |
| 80 | chdir | yes | served |
| 110 | getppid | yes | served |
| 131 | sigaltstack |  | served |
| 157 | prctl |  | served |
| 158 | arch_prctl |  | served |
| 186 | gettid |  | served |
| 202 | futex |  | served |
| 204 | sched_getaffinity | yes | served |
| 217 | getdents64 |  | served |
| 218 | set_tid_address |  | served |
| 230 | clock_nanosleep |  | served |
| 231 | exit_group |  | served |
| 267 | readlinkat | yes | served |
| 273 | set_robust_list | yes | unserved, fallback works |
| 293 | pipe2 | yes | served |
| 302 | prlimit64 | yes | served |
| 318 | getrandom | yes | served |
| 334 | rseq | yes | unserved, fallback works |
| 435 | clone3 | yes | served |

Linux's vDSO hides clock_gettime from this trace; PAX has no vDSO.
Its clock syscall requirement is inferred from the implementation and
the live clock row, not claimed as a Linux strace observation.

The mremap requests were `MREMAP_MAYMOVE`, 151552 → 299008 bytes, in
spawn/std typechecks and checked runs. PAX returns ENOSYS; musl falls
back, and the sessions remain byte-identical. The coordinator explicitly
kept this as a follow-up: no partial implementation treating arbitrary
adjacent pages as one mapping, and no VMA-metadata work in this lane.

### CI evidence

The glibc attempts `39790417448` and `39792627435` failed at the byte
gate, before the intended plant. The other early attempts
`39790422267`, `39790427725`, `39792635591`, `39792640395` are not
counted as successful control or plant evidence either.
Final symbol-free runs, at `af5199cf`:

| run | job | result |
|---|---:|---|
| glibc plant `39796041663` | `119883727765` | byte gate passes, then exec is refused on PAX: `ET_DYN: a PIE or shared object (PIE is later)`; W1/W2/W3 red |
| std plant `39796046313` | `119883750430` | byte gate passes, then `E0301: module std has no item named str` names the absent standard library; W2 rejects the missing std observations for root and pax; W3 also notices mremap is no longer reached |
| control `39796051044` | `119883769940` | bytes reproduce; both live Linux/PAX sessions and all independent witnesses pass |

The extracts are `ci-glibc-39796041663.log`, `ci-std-39796046313.log`,
and `ci-control-39796051044.log`. The glibc substitution is deliberately
after static/pin checks, so the loader—not a checksum guard—sees it.

The fast CI root intentionally omits the native link bundle. Native
linking is additionally a real local container/QEMU differential test,
exposed through `tests/mpx5-wolf --only native --images DIR`; CI checks
its recorded witnesses, failure mutations, and the cc translator's unit
tests. It does not rebuild LLVM on every PR. The final PR-tier run is
left for the orchestrator, as the Codex lane contract requires.

## 5. Native link boundary, image and handoff

The Linux-only `cc-lld.py` translates the driver's cc arguments for
ld.lld. With Alpine musl's binary libc/CRT and Rust's musl-target
libunwind, hello, loop and signal link as ET_EXEC, without a dynamic
section, and run successfully. Fork, task spawn and std witnesses also
link/run. The host/tree sample was not a parity run: its expected
working-tree fixture was absent, and its run returned 1.
`notes/px60/m2-linux.log` contains the exact link commands and twice-read
input digests. R-px60-1 option (a) is feasible and remains recommended;
no libc source was consulted.

In the checked-only CI variant, as root and pax (not the final full dev ISO):

```
wolf build --no-cache --emit=obj hello.lu -o hello.o
# status 0
wolf build --no-cache hello.lu -o hello
wolf build: cannot run `cc`: No such file or directory (os error 2)
# status 2, a failure, never a skip
wolf build --release --no-cache hello.lu -o release
wolf build: `clang` not found — the release tier requires clang >= 15 ...
# status 2
```

Alpine lld-dev supplies shared libraries only: no `liblld*.a` exists,
and its attempted static link reports
`ld.lld: error: attempted static link of dynamic object /usr/lib/liblldELF.so`.
Alpine's executable is dynamic ET_DYN. Rustup's musl-host 1.99.1
rust-lld is ET_EXEC **but dynamic**, with PT_INTERP
`/lib/ld-musl-x86_64.so.1` and dependencies `libgcc_s.so.1`, `libc.so`.
Neither is a static executable PAX can load.

The authorized source build then succeeded in about 50 minutes, inside
its original one-hour limit. LLVM 17.0.6 archive SHA256:
`58a8818c60e6627064f312dbf46c02d9949956558340938b71cf731ad8bc0813`.
`build-lld.sh` selects X86, static linking, clang, libc++/libc++abi and
LLVM libunwind; no GNU linker is supplied to PAX. The first host link
needed explicit libc++abi linkage; the repaired build completed.
The static `ld.lld` is 66,247,008 bytes,
`1217ca75f9df70439294844b2aba14895adc557e2514c6cdc76c4c6676a3757b`,
ET_EXEC, no PT_INTERP or dynamic section, and it starts on PAX.

The first full link failed on both OSes because Alpine's CRT/libc had
compressed debug sections and this lld was built without zlib:
`is compressed with ELFCOMPRESS_ZLIB, but lld is not built with zlib support`.
This was a packaging error, not an OS wall. `decompress.sh` uses packaged
LLVM objcopy to decompress binary metadata, preserving the code and debug
content; no libc source is read. Alpine musl/musl-dev are 1.2.5-r4.
The cc shim is Rust 1.97.1 musl-static, 499,760 bytes,
`3161aea27abb8beeb669cc6499fa9dc162014b69eecc6fb0d169eed5def25b11`.
It preserves argument boundaries and output filenames, translates the
wolf driver's link flags, and uses one lld thread and read/write output.
It is not a C compiler. All seven native inputs are pinned in
`user/wolf-link.sums`; `build-m2.sh` records their build/staging recipe.

With that stack, **PAX built hello, loop and signal on PAX as uid 1000,
and ran each with status 0**. The entire normalized native session is
byte-identical to the same binaries and keys on Linux:
`2a2f7b1364869ddd123d0d4c67c75571f50ceaed2692b03e8d5d1206ab30b777`.
`native-pax.log`, `native-linux.tty` and `native-compare.log` retain the
proof. The independent checker requires three successful links, three
successful executions, their actual output, uid 1000, and clean kernel
exit; matching failures do not pass.

PAX logs `a file-backed mapping ... -19` and `MAP_SHARED ... -22` from
lld. Its fallback works: these are unserved operations, not failed links.
The raw logs retain those words; only kernel narration is removed for
terminal comparison. No kernel mapping implementation was added.
`--release` still stops at the named missing-clang requirement.

The copied assembly scripts are `notes/px60/build.sh` and `assemble.sh`.
The base tools were reused from the existing px59 build, the kernel was
rebuilt from the rebased tree, and only the dev additions were assembled.
The typed dev-image session (`dev.keys`, `dev-iso.sh`) switches to pax,
writes hello.lu, formats and typechecks it, runs the checked machine,
emits an object, builds and runs it natively, and names the remaining clang wall. The base ISO was
not replaced. The first canonical, M1-only image was 145,086,464 bytes,
`2b8e6073e1f47ffb8dbb8a37e5fc48457dd771ec5ff48bf01766c7f89148b82d`.
The final native-capable `pax-dev.iso` is 223,012,864 bytes,
`9af2565afda15312fee8c463203d746995d86cab613bb81feed71f0e705e9bb7`.
Each was read twice on kasumi. The final image is copied to
`/Users/mfwolffe/pax-playground/pax-dev.iso` and read twice there too.
Its identity-checked session is in `dev-session.log`;
`check-dev-session.py` requires uid 1000, `whoami` answering pax, successful
checked execution, format/object status 0, **`wolf build hello.lu` and
`./hello` status 0**, the remaining release-tier status-2 clang error,
and clean init exit. The final image includes the M2 stack under
R-px60-1 (a), recommended and built.

To repeat the useful part after booting `pax-dev.iso` with 2 GiB RAM:

```
su pax
cd
cat > hello.lu
fn main() { print("hello from PAX") }
# Ctrl-D
wolf fmt hello.lu
wolf conform-run --json --phase=typecheck hello.lu
wolf conform-run --json --checked hello.lu
wolf build hello.lu
./hello
```

Issues to file, none filed here:

- wolf-lang: the two musl portability failures, with `user/wolf-musl.patch`
  attached (the locale-mask sites and the opaque pthread handle).
- wolf-lang: a musl-static release archive, the twin of wolf-interp#283.
- PAX: mremap/MREMAP_MAYMOVE, its measured sizes and working allocator fallback.
- PAX: file-backed mmap and MAP_SHARED, reached by static lld; the measured
  read/write fallback succeeds. No existing issue was returned by the lane's
  mmap/mremap search; check any broader VM umbrella before filing.

No issue to close. R-px60-1 (musl libc/CRT for M2): recommend (a), Linux
link feasibility and native PAX execution measured; the final dev ISO carries the binary inputs.
The accepted mremap scope decision leaves the kernel unchanged. px61
owns the base std pin/stager and base shrc; the second lane to land must
reuse the other's staging mechanism rather than retain duplicate tools.

Footprint: cross-cutting (CI and a user compiler pin, despite no kernel edit).

### Cleanup

Only px60's completed LLVM download/build trees and Rust target/build
directories were pruned, using literal paths and `podman unshare` for
container-owned files. The two px60 build-image tags were removed; the
shared px13-ubuntu and px57-rust images were left alone. Canonical binaries,
link inputs, the ISO, logs and the final probe inputs remain available.
`prune.log` records the space check. No other lane's files were removed.

## R-px60-2: the credential user-soak deadline

The orchestrator took R-px60-2 after labelled run 39819870030 failed
`mpx5-users` alone: **1200 seconds for `soak-user` only**, every other
session still 900 seconds. Both root/user runs retain 100,000 rounds,
one million id calls and 10,000 children. No guest code or image payload
was changed by this remedy.

The failed leg was not silent: its retained serial log contains 9,653
successful child exits and is an exact 464,114-byte prefix of the green
PR run's log. Only the final summary was absent. The merge base itself
(`e988ce72`, trunk run 39787335307) already hit the same 900-second cap
in native BIOS, leaving 9,720 logged successful exits. Its kernel ELF
and soak-user initramfs match px60's exactly. This credentials image
contains only as/cred/ident/ident-setid/ids and its accounts/runlist,
not the dev compiler, std, linker or libc additions.

Successful CI intervals were **879.57 s** for px60's native BIOS PR run
39817250352 and **878.17 s** for the base's native UEFI leg. These are
log-boundary wall intervals including harness bookkeeping. The former
used the exact ISO (`a865de20…`) that the labelled native BIOS run cut
at 900 s. ISO dates differ between base and head because `mkimage`
defaults SOURCE_DATE_EPOCH to the commit time, not because payloads moved.

The controlled kasumi comparison rebuilt base and head at identical
container paths with SOURCE_DATE_EPOCH=0. Kernel, initramfs and complete
ISO are byte-identical; the ISO SHA256 is
`863d92da016e15e09a04d47937d42750337dbd877232d29586105bcca2591745`.
Sequential full-count boots under QEMU 11.1.1 TCG, `taskset -c 0-3`,
256 MiB, completed in **650.62 s base** and **566.21 s head**. Both
reported zero wrong answers and MemFree 246980 kB before and at every
quarter. Head was 84.41 s (12.97%) faster in this pair;
that is host-time variation, not a code speedup, since the images match.
There is no measured head slowdown or hang. The 900-second cap was
inside the runner's observed variance.

Evidence and reproducer: `notes/px60/users-audit/`. The diagnostic
reproducer uses a 1500-second ceiling to measure completion; the actual
suite's selected ceiling is 1200. `tests/mpx5-users.d/deadline.py` runs
the real two-line selection for ten session classes, checks its qemu
argument and unchanged counts, and rejects the old source. CI runs it
before the credentials suite. The change is deliberately not a shorter
soak or a global timeout increase.
