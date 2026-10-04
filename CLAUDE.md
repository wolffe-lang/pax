# PAX — agent guidance

## The clean-room rule (read before writing a line)

**Never read, copy or translate Linux kernel source** (`.c`, `.S`, `.h` outside the uapi trees, Kconfig, Makefiles). PAX implements Linux's userspace ABI; it is not a port.

Allowed sources:
- the uapi headers (`include/uapi/`, `arch/*/include/uapi/`), GPL-2.0 WITH Linux-syscall-note;
- the syscall tables (`arch/x86/entry/syscalls/*.tbl`);
- `Documentation/`, the man-pages project, POSIX.1-2024, the x86-64 psABI;
- the Intel and AMD manuals, the UEFI, ACPI and virtio specifications;
- black-box behaviour of a real Linux under QEMU.

Permissively licensed kernels (the BSDs, seL4, Redox, Asterinas, Maestro, Kerla) are design references only, never copied. Record in `docs/SOURCES.md` what each change consulted.

The planning repo's refs clone (`wolf/refs/repos/linux`) is a sparse checkout of the allowed paths only.

## Where the plan is

`sprints/pax/index.md` in the planning repo (`wolffe-lang/wolf`). Contracts there are binding. When this file and the wolf spec disagree, the spec wins.

## The repository

- **Layout**: `kernel/` (wolf, from px01), `boot/` (the Limine pin and config; the kernel's assembly ring — `start.S`, the Limine entry and requests, and `io.S`, `cpu.S` and `isr.S` (the interrupt trampolines and the descriptor tables' storage, kw10), listed under `asm` in `kernel/wolf.pkg` — and `boot/stub/`, the harness's assembly proof, retired by px01; assembly is whole routines reached through `extern "c" fn`, never more), `tools/` (the harness), `tests/` (scripted QEMU tests), `docs/` (`BOOT.md`, `SOURCES.md`, ABI notes), `notes/` (one note per lane: contract and evidence).
- **The boot protocol is Limine**, base revision 6 (`docs/BOOT.md`, ruled by px00). Limine is fetched from its release BY DIGEST (`boot/limine.pin`, `tools/fetch-limine`), never vendored and never built from source. Bump the pin's three lines together.
- **Every behaviour claim is a QEMU test** run by CI: `tools/qemu-run` boots, `tools/expect-serial` asserts the serial log, QEMU's exit status carries the kernel's verdict through `isa-debug-exit` (status `(v << 1) | 1`). Where the behaviour is Linux's, the test is differential against a real Linux under QEMU.
- **A test is seen red before it is trusted**: plant the break in a commit and CI run of its own, then fix it. `tests/expect-serial-selftest` is the harness's own proof that it can fail.

## Hard rules

- Commits chunked, terse, imperative. Never `git add -A`. No commit or PR trailers of any kind.
- Branch per lane, PR left unmerged; the orchestrator audits and fast-forwards.
- Nothing is made public: the repository is private until the maintainer says otherwise.
- The harness never installs packages; lanes never install on the pool.
- A gap in wolf is filed upstream (wolf-lang) with a witness, and the track index names it as a blocker.

