# Contributing to PAX

PAX is a Linux-compatible operating system written in
[wolf](https://github.com/wolffe-lang/wolf-lang): a kernel that runs Linux's
x86-64 userspace unmodified, and a userspace built in wolf. The README says what
works today and how each part is tested; this file says what a change needs.

## The clean-room rule

PAX implements Linux's userspace ABI; it is not a port. **Never read, copy or
translate Linux kernel source**: no `.c`, `.S` or `.h` file outside the uapi
trees, no Kconfig, no Makefile. Work from:

- the uapi headers (`include/uapi/`, `arch/*/include/uapi/`), GPL-2.0 WITH
  Linux-syscall-note;
- the syscall tables (`arch/x86/entry/syscalls/*.tbl`);
- `Documentation/`, the man-pages project, POSIX.1-2024 and the x86-64 psABI;
- the Intel and AMD manuals and the UEFI, ACPI and virtio specifications;
- the black-box behaviour of a real Linux under QEMU.

Permissively licensed kernels (the BSDs, seL4, Redox, Asterinas, Maestro,
Kerla) are design references only, never copied. Every change records in
`docs/SOURCES.md` what it consulted, at which version, for which file, and how:
read, run as a black box, or known already with no text copied.

## The toolchain

`kernel/wolf.pin` pins the wolf compiler release the kernel is built with and
the lupin interpreter beside it, by sha256 digest; `boot/limine.pin` pins the
Limine bootloader the same way. Nothing is vendored or built from source:

```sh
tools/fetch-wolf      # stages the pinned wolf, prints its path
tools/fetch-lupin     # the same for lupin
tools/fetch-limine    # the pinned Limine, into .pax-cache/
```

A pin moves in a commit of its own, all of its lines together.

Building images needs a Linux x86-64 host with binutils, cc, make, curl, xorriso
and `qemu-system-x86_64` (and OVMF for the UEFI leg); the README's Hosts section
says what other hosts can do. The harness never installs anything: a missing
tool is named and the script stops.

## Building and running the checks

```sh
tests/proof                                 # the harness's own proof, BIOS and UEFI
tests/ci-plan                               # CI's planner (python3 and bash, no QEMU)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx1     # one suite; every tests/NAME runs this way
PAX_WOLF=$(tools/fetch-wolf) tests/mpx1 --tier native --firmware bios   # one leg
```

Each suite builds its images, boots them under QEMU and asserts the serial log
and the exit status; the README's Tests section lists them. A suite that needs
root, docker or podman, or KVM says so and stops.

## What a change must bring

- **Every behaviour claim is a QEMU test that CI runs.** `tools/qemu-run` boots
  an image, `tools/expect-serial` asserts the serial log, and the kernel's
  verdict reaches QEMU's exit status through `isa-debug-exit` (status
  `(v << 1) | 1`). Where the behaviour is Linux's, the test is differential
  against a real Linux booted the same way.
- **A test is seen red before it is trusted.** Plant the break in a commit of
  its own, let CI show it red, then fix it. `tests/expect-serial-selftest` is
  the harness's own proof that it can fail.
- A new suite gets a job in `.github/workflows/ci.yml` wired like the others
  (`tests/ci-plan` checks the wiring); a new path a suite reads gets a line in
  `tools/ci-tiers.map`.
- `docs/SOURCES.md` gets the change's entry. A user-visible change gets a
  paragraph under `## Unreleased` in `CHANGELOG.md`.
- A bug or a missing feature in wolf is filed upstream at
  [wolffe-lang/wolf-lang](https://github.com/wolffe-lang/wolf-lang) with a
  small program that shows it, and named in the code where a reader meets it.

The repository is public: no secret or credential goes in it.

## Commits

- Small and chunked: one file or one coherent change a commit, so the history
  tells how the work was done. Never `git add -A`; stage what you mean.
- A terse, imperative subject, usually led by the path it touches
  (`tools/ci-plan: ...`).
- No trailers of any kind: no co-author, sign-off or "generated with" lines.

## Pull requests

Open a pull request from a branch against `trunk`. CI runs in tiers:

- a pull request's push runs the suites its change can affect
  (`tools/ci-plan` reads `tools/ci-tiers.map`) on one leg, native BIOS; a
  change to the kernel's core or to CI runs every suite on that leg, and a
  change to the pins, the harness or the kernel's entry runs every leg;
- **merging needs a green `tier full` run at the head**: every suite on native
  BIOS, started by the `full-matrix` label. Ask for the label when the head is
  the one to merge, not when the pull request opens. A green `tier all` run
  (every suite on every leg) counts too.

The description says what changed and why, what was consulted (the
`docs/SOURCES.md` entry), and which runs show it: the planted red and the
green at the head, by link. Pull requests are merged by fast-forward after
review.
